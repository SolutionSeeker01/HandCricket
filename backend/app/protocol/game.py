"""Computer game coordinator for Hand Cricket (Slice 12 & Slice 13).

This module coordinates an end-to-end match between a human user (connected via
WebSocket) and the headless ComputerPlayer, composing the pure domain Match engine,
predefined Teams, PreMatchSetup, Toss, and protocol messaging.
"""

import asyncio
import random
from typing import Any, Callable, Dict, List, Optional

from fastapi import WebSocket

from backend.app.engine.ball import BallResult, resolve_ball, validate_choice
from backend.app.engine.computer import ComputerPlayer
from backend.app.engine.match import Match, MatchStatus
from backend.app.engine.pre_match import PreMatchSetup
from backend.app.engine.teams import Team, get_team, get_teams, is_valid_team_id
from backend.app.engine.toss import (
    Participant,
    TossChooser,
    TossDecision,
)
from backend.app.protocol.messages import (
    TYPE_BALL_RESULT,
    TYPE_BOWLER_SELECTION_REQUIRED,
    TYPE_ERROR,
    TYPE_NUMBER_SUBMITTED,
    TYPE_PRE_MATCH_STATE,
    TYPE_TURN_STARTED,
    TurnProtocolError,
    serialize_ball_result,
    serialize_bowler_selection_required,
    serialize_number_submitted,
    serialize_pre_match_state,
    serialize_turn_started,
)


class ComputerGameSession:
    """Coordinates a complete match against the Computer including pre-match setup.

    Invariants:
        - Server-authoritative: all team selection, toss, role derivation, scoring,
          wickets, bowler quota, and match rules are computed by backend domain engine.
        - The human player connects via WebSocket.
        - The computer player runs server-side via ComputerPlayer and deterministic choosers.
        - Timer is 10 seconds per turn during gameplay.
        - Supports pre-match flow (Slice 13) or direct-match play (skip_pre_match=True).
    """

    def __init__(
        self,
        user_team_id: str = "IND",
        opponent_team_id: str = "AUS",
        timeout_seconds: float = 10.0,
        max_overs: int = 5,
        balls_per_over: int = 6,
        computer_bot: Optional[ComputerPlayer] = None,
        auto_start: bool = True,
        skip_pre_match: bool = True,
        toss_chooser: Optional[TossChooser] = None,
        computer_team_chooser: Optional[Callable[[], str]] = None,
        computer_decision_chooser: Optional[Callable[[], TossDecision]] = None,
        computer_bowler_chooser: Optional[Callable[[List[int]], int]] = None,
    ) -> None:
        self._user_team: Team = get_team(user_team_id)
        self._opponent_team: Team = get_team(opponent_team_id)
        self._timeout_seconds: float = timeout_seconds
        self._max_overs: int = max_overs
        self._balls_per_over: int = balls_per_over
        self._bot: ComputerPlayer = computer_bot if computer_bot is not None else ComputerPlayer()
        self._auto_start: bool = auto_start
        self._skip_pre_match: bool = skip_pre_match

        self._toss_chooser: Optional[TossChooser] = toss_chooser
        self._computer_team_chooser: Optional[Callable[[], str]] = computer_team_chooser
        self._computer_decision_chooser: Optional[Callable[[], TossDecision]] = computer_decision_chooser
        self._computer_bowler_chooser: Optional[Callable[[List[int]], int]] = computer_bowler_chooser

        self._websocket: Optional[WebSocket] = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self._timer_task: Optional[asyncio.Task] = None

        self._pre_match: Optional[PreMatchSetup] = None
        self._stage: str = "IN_MATCH" if skip_pre_match else "TEAM_SELECTION"
        self._awaiting_bowler_selection: bool = False
        self._user_is_batting_first: bool = True

        if skip_pre_match:
            self._init_match()
        else:
            self._init_pre_match()

    def _init_pre_match(self) -> None:
        """Initialize or reset pre-match coordination state."""
        self._pre_match = PreMatchSetup(toss_chooser=self._toss_chooser)
        self._stage = "TEAM_SELECTION"
        self._awaiting_bowler_selection = False
        self._user_is_batting_first = True
        self._match = None
        self._last_bowler_id = None
        self._innings_1_bowler_stats = {}
        self._innings_2_bowler_stats = {}
        self._current_over_balls = []
        self._last_ball_info = None
        self._turn_number = 1
        self._turn_active = False
        self._turn_submitted = False
        self._user_choice = None
        self._is_innings_break = False

    def _init_match(self) -> None:
        """Initialize or reset match engine and state tracking for direct play."""
        self._stage = "IN_MATCH"
        self._awaiting_bowler_selection = False
        self._user_is_batting_first = True

        self._match: Match = Match(
            team_1=self._user_team.name,
            team_2=self._opponent_team.name,
            team_size=11,
            max_overs=self._max_overs,
            balls_per_over=self._balls_per_over,
        )
        self._match.start_innings_1()

        # Default bowlers for direct mode testing
        self._comp_bowler_order: List[int] = [11, 10, 9, 8, 7]
        self._comp_bowler_idx: int = 0
        first_bowler = self._comp_bowler_order[self._comp_bowler_idx]
        self._match.select_bowler(first_bowler)
        self._last_bowler_id: Optional[int] = first_bowler

        self._user_bowler_order: List[int] = [11, 10, 9, 8, 7]
        self._user_bowler_idx: int = 0

        self._innings_1_bowler_stats: Dict[int, Dict[str, int]] = {}
        self._innings_2_bowler_stats: Dict[int, Dict[str, int]] = {}
        self._current_over_balls: List[Any] = []
        self._last_ball_info: Optional[Dict[str, Any]] = None

        self._turn_number: int = 1
        self._turn_active: bool = False
        self._turn_submitted: bool = False
        self._user_choice: Optional[int] = None
        self._is_innings_break: bool = False

    @property
    def stage(self) -> str:
        return self._stage

    @property
    def pre_match(self) -> Optional[PreMatchSetup]:
        return self._pre_match

    @property
    def match(self) -> Optional[Match]:
        return self._match

    @property
    def user_team(self) -> Team:
        return self._user_team

    @property
    def opponent_team(self) -> Team:
        return self._opponent_team

    @property
    def is_innings_break(self) -> bool:
        return self._is_innings_break

    @property
    def awaiting_bowler_selection(self) -> bool:
        return self._awaiting_bowler_selection

    @property
    def turn_number(self) -> int:
        return self._turn_number

    @property
    def turn_submitted(self) -> bool:
        return self._turn_submitted

    @property
    def is_turn_active(self) -> bool:
        return self._turn_active and not self._turn_submitted

    @property
    def innings_1_bowler_stats(self) -> Dict[int, Dict[str, int]]:
        return self._innings_1_bowler_stats

    @property
    def innings_2_bowler_stats(self) -> Dict[int, Dict[str, int]]:
        return self._innings_2_bowler_stats

    def _choose_computer_bowler(self, eligible_bowlers: List[int]) -> int:
        """Select an eligible bowler for the computer side."""
        if not eligible_bowlers:
            raise TurnProtocolError("no_eligible_bowlers", "No eligible bowlers remaining.")
        if self._computer_bowler_chooser is not None:
            return self._computer_bowler_chooser(eligible_bowlers)
        return random.choice(eligible_bowlers)

    def _choose_computer_toss_decision(self) -> TossDecision:
        """Generate a toss decision for the computer."""
        if self._computer_decision_chooser is not None:
            return self._computer_decision_chooser()
        return random.choice([TossDecision.BAT, TossDecision.BOWL])

    def _choose_computer_team(self) -> str:
        """Select a predefined team for the computer."""
        if self._computer_team_chooser is not None:
            return self._computer_team_chooser()
        teams = get_teams()
        return random.choice(teams).id

    # ---------------------------------------------------------------------------
    # Pre-Match Flow Methods
    # ---------------------------------------------------------------------------

    async def select_team(self, user_team_id: str) -> None:
        """User selects their team. Server assigns computer team and flips toss."""
        async with self._lock:
            if self._stage != "TEAM_SELECTION":
                raise TurnProtocolError(
                    "invalid_stage",
                    f"Cannot select team in stage {self._stage!r}. Team selection is locked.",
                )

            if not is_valid_team_id(user_team_id):
                raise TurnProtocolError(
                    "invalid_team_id",
                    f"Team ID {user_team_id!r} is not a valid predefined team.",
                )

            # Assign user team to Participant A
            self._pre_match.select_team(Participant.A, user_team_id)
            self._user_team = self._pre_match.team_a

            # Server chooses computer team and assigns to Participant B
            comp_team_id = self._choose_computer_team()
            self._pre_match.select_team(Participant.B, comp_team_id)
            self._opponent_team = self._pre_match.team_b

            # Authoritative coin toss
            toss_winner = self._pre_match.flip_toss()

            if toss_winner == Participant.A:
                # User won the toss: await user's BAT / BOWL decision
                self._stage = "TOSS_DECISION"
                await self._send_json_locked(self.get_pre_match_state_dict())
            else:
                # Computer won the toss: computer decides automatically
                comp_decision = self._choose_computer_toss_decision()
                self._pre_match.choose_toss(comp_decision, by=Participant.B)

                # Check who selects first bowler
                if self._pre_match.first_bowler_selector_participant == Participant.A:
                    # User is bowling first: prompt bowler selection
                    self._stage = "BOWLER_SELECTION"
                    await self._send_json_locked(self.get_pre_match_state_dict())
                else:
                    # Computer is bowling first: computer picks bowler automatically
                    comp_bowler = self._choose_computer_bowler(list(range(1, 12)))
                    await self._start_match_from_pre_match_locked(first_bowler_id=comp_bowler)

    async def choose_toss(self, decision: str) -> None:
        """User records toss decision (BAT or BOWL)."""
        async with self._lock:
            if self._stage != "TOSS_DECISION":
                raise TurnProtocolError(
                    "invalid_stage",
                    f"Cannot choose toss in stage {self._stage!r}.",
                )

            if self._pre_match.toss_winner != Participant.A:
                raise TurnProtocolError(
                    "not_toss_winner",
                    "Only the toss winner can make the toss decision.",
                )

            norm_decision = decision.strip().upper()
            if norm_decision not in ("BAT", "BOWL"):
                raise TurnProtocolError(
                    "invalid_toss_decision",
                    f"Invalid decision {decision!r}: must be 'BAT' or 'BOWL'.",
                )

            self._pre_match.choose_toss(norm_decision, by=Participant.A)

            if norm_decision == "BAT":
                # User chose BAT: User bats first, Computer bowls first
                comp_bowler = self._choose_computer_bowler(list(range(1, 12)))
                await self._start_match_from_pre_match_locked(first_bowler_id=comp_bowler)
            else:
                # User chose BOWL: Computer bats first, User bowls first
                self._stage = "BOWLER_SELECTION"
                await self._send_json_locked(self.get_pre_match_state_dict())

    async def select_bowler(self, bowler_id: int) -> None:
        """Fielding participant selects a bowler for the active or next over."""
        async with self._lock:
            if self._stage == "BOWLER_SELECTION":
                # Pre-match Over 1 bowler selection
                if self._pre_match.first_bowler_selector_participant != Participant.A:
                    raise TurnProtocolError(
                        "not_bowler_selector",
                        "User is not responsible for selecting the first bowler.",
                    )

                if isinstance(bowler_id, bool) or not isinstance(bowler_id, int) or bowler_id < 1 or bowler_id > 11:
                    raise TurnProtocolError(
                        "invalid_bowler_id",
                        f"Invalid bowler ID {bowler_id}: must be between 1 and 11.",
                    )

                await self._start_match_from_pre_match_locked(first_bowler_id=bowler_id)

            elif self._stage == "IN_MATCH":
                # Mid-match bowler selection between overs
                if not self._awaiting_bowler_selection:
                    raise TurnProtocolError(
                        "not_awaiting_bowler",
                        "Not currently awaiting bowler selection.",
                    )

                innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
                active_bowling = (
                    self._match.bowling_1 if innings_num == 1 else self._match.bowling_2
                )

                if not active_bowling.is_eligible(bowler_id):
                    if active_bowling.has_bowled(bowler_id):
                        raise TurnProtocolError(
                            "bowler_already_bowled",
                            f"Bowler {bowler_id} has already bowled in this innings.",
                        )
                    raise TurnProtocolError(
                        "invalid_bowler",
                        f"Bowler {bowler_id} is not eligible to bowl.",
                    )

                self._match.select_bowler(bowler_id)
                self._last_bowler_id = bowler_id
                self._awaiting_bowler_selection = False

                # Over is assigned, start the next ball turn!
                await self._start_turn_locked()

            else:
                raise TurnProtocolError(
                    "invalid_stage",
                    f"Cannot select bowler in stage {self._stage!r}.",
                )

    async def _start_match_from_pre_match_locked(self, first_bowler_id: int) -> None:
        """Create and start the authoritative match after pre-match completion."""
        self._user_team = self._pre_match.get_team_for_participant(Participant.A)
        self._opponent_team = self._pre_match.get_team_for_participant(Participant.B)
        self._user_is_batting_first = (
            self._pre_match.batting_first_participant == Participant.A
        )

        self._match = self._pre_match.create_match(
            max_overs=self._max_overs,
            balls_per_over=self._balls_per_over,
        )
        self._match.start_innings_1()
        self._match.select_bowler(first_bowler_id)
        self._last_bowler_id = first_bowler_id

        self._innings_1_bowler_stats = {}
        self._innings_2_bowler_stats = {}
        self._current_over_balls = []
        self._last_ball_info = None
        self._turn_number = 1
        self._turn_active = False
        self._turn_submitted = False
        self._user_choice = None
        self._is_innings_break = False
        self._awaiting_bowler_selection = False
        self._stage = "IN_MATCH"

        await self._start_turn_locked()

    async def reset_pre_match(self) -> None:
        """Reset the pre-match session back to team selection."""
        async with self._lock:
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
            self._init_pre_match()
            await self._send_json_locked(self.get_pre_match_state_dict())

    def get_pre_match_state_dict(self) -> Dict[str, Any]:
        """Build the authoritative pre-match state payload."""
        available_teams = [
            {
                "id": team.id,
                "name": team.name,
                "players": [{"id": p.id, "name": p.name} for p in team.players],
            }
            for team in get_teams()
        ]

        user_team_info = (
            {"id": self._user_team.id, "name": self._user_team.name}
            if self._pre_match and self._pre_match.team_a
            else None
        )
        opponent_team_info = (
            {"id": self._opponent_team.id, "name": self._opponent_team.name}
            if self._pre_match and self._pre_match.team_b
            else None
        )

        toss_winner_str = None
        if self._pre_match and self._pre_match.toss_winner:
            toss_winner_str = (
                "user" if self._pre_match.toss_winner == Participant.A else "computer"
            )

        toss_decision_str = None
        batting_first_str = None
        bowling_first_str = None
        first_bowler_selector_str = None
        if self._pre_match and self._pre_match.toss_result:
            toss_decision_str = self._pre_match.toss_result.decision.value
            batting_first_str = (
                "user"
                if self._pre_match.toss_result.batting_first == Participant.A
                else "computer"
            )
            bowling_first_str = (
                "user"
                if self._pre_match.toss_result.bowling_first == Participant.A
                else "computer"
            )
            first_bowler_selector_str = (
                "user"
                if self._pre_match.toss_result.first_bowler_selector == Participant.A
                else "computer"
            )

        eligible_bowlers = None
        used_bowlers = None
        if self._stage == "BOWLER_SELECTION" and self._user_team:
            eligible_bowlers = [
                {"id": p.id, "name": p.name} for p in self._user_team.players
            ]
            used_bowlers = []

        return serialize_pre_match_state(
            stage=self._stage,
            available_teams=available_teams,
            user_team=user_team_info,
            opponent_team=opponent_team_info,
            toss_winner=toss_winner_str,
            toss_decision=toss_decision_str,
            batting_first=batting_first_str,
            bowling_first=bowling_first_str,
            first_bowler_selector=first_bowler_selector_str,
            current_over=1 if self._stage == "BOWLER_SELECTION" else None,
            eligible_bowlers=eligible_bowlers,
            used_bowlers=used_bowlers,
        )

    # ---------------------------------------------------------------------------
    # Gameplay Match State & Resolutions
    # ---------------------------------------------------------------------------

    def get_match_state_dict(self) -> Dict[str, Any]:
        """Build the authoritative match state payload for the UI."""
        if not self._match:
            return {}

        is_completed = self._match.is_completed
        innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
        active_innings = (
            self._match.innings_1 if innings_num == 1 else self._match.innings_2
        )

        user_is_batting = (
            self._user_is_batting_first if innings_num == 1 else not self._user_is_batting_first
        )

        # Current score & wickets
        score = active_innings.total_runs if active_innings else 0
        wickets = active_innings.wickets if active_innings else 0
        balls_in_over = active_innings.balls_in_current_over if active_innings else 0
        completed_overs = (
            active_innings.current_over - 1 if active_innings else 0
        )
        overs_str = f"{completed_overs}.{balls_in_over}"

        # Batters (Striker and Non-Striker)
        striker_info: Dict[str, Any] = {"name": "", "runs": 0, "balls": 0}
        non_striker_info: Dict[str, Any] = {"name": "", "runs": 0, "balls": 0}

        batting_team = self._user_team if user_is_batting else self._opponent_team
        bowling_team = self._opponent_team if user_is_batting else self._user_team

        if active_innings and not is_completed:
            bs = active_innings.batting_state
            st_id = active_innings.striker
            nst_id = active_innings.non_striker

            if st_id:
                p = batting_team.get_player(st_id)
                striker_info = {
                    "id": st_id,
                    "name": p.name if p else f"Player {st_id}",
                    "runs": bs.get_batsman_score(st_id),
                    "balls": bs.get_batsman_balls(st_id),
                }

            if nst_id:
                p = batting_team.get_player(nst_id)
                non_striker_info = {
                    "id": nst_id,
                    "name": p.name if p else f"Player {nst_id}",
                    "runs": bs.get_batsman_score(nst_id),
                    "balls": bs.get_batsman_balls(nst_id),
                }

        # Bowler
        bowler_info: Dict[str, Any] = {
            "name": "",
            "overs": "0.0",
            "runs": 0,
            "wickets": 0,
            "figures": "0.0-0-0",
        }
        active_bowling = (
            self._match.bowling_1 if innings_num == 1 else self._match.bowling_2
        )
        b_id = None
        if active_bowling and active_bowling.active_bowler:
            b_id = active_bowling.active_bowler
        elif self._last_bowler_id:
            b_id = self._last_bowler_id

        if b_id is not None:
            b_player = bowling_team.get_player(b_id)
            stats_dict = (
                self._innings_1_bowler_stats
                if innings_num == 1
                else self._innings_2_bowler_stats
            )
            b_stats = stats_dict.get(b_id, {"runs": 0, "balls": 0, "wickets": 0})
            b_overs_str = f"{b_stats['balls'] // 6}.{b_stats['balls'] % 6}"
            bowler_info = {
                "id": b_id,
                "name": b_player.name if b_player else f"Player {b_id}",
                "overs": b_overs_str,
                "runs": b_stats["runs"],
                "wickets": b_stats["wickets"],
                "figures": f"{b_overs_str}-{b_stats['runs']}-{b_stats['wickets']}",
            }

        # Status text for client
        if is_completed:
            status_str = "COMPLETED"
        elif self._is_innings_break:
            status_str = "INNINGS_BREAK"
        elif innings_num == 1:
            status_str = "INNINGS_1"
        else:
            status_str = "INNINGS_2"

        return {
            "status": status_str,
            "innings": innings_num,
            "user_team": {"id": self._user_team.id, "name": self._user_team.name},
            "opponent_team": {
                "id": self._opponent_team.id,
                "name": self._opponent_team.name,
            },
            "batting_team": batting_team.name,
            "bowling_team": bowling_team.name,
            "user_is_batting": user_is_batting,
            "score": score,
            "wickets": wickets,
            "overs": overs_str,
            "max_overs": self._max_overs,
            "target": self._match.target,
            "striker": striker_info,
            "non_striker": non_striker_info,
            "bowler": bowler_info,
            "current_over_balls": list(self._current_over_balls),
            "innings_1_score": self._match.innings_1_score,
            "innings_1_wickets": self._match.innings_1_wickets,
            "innings_2_score": self._match.innings_2_score,
            "innings_2_wickets": self._match.innings_2_wickets,
            "last_ball": self._last_ball_info,
            "winner": self._match.winner,
            "is_tie": self._match.is_tie,
            "result_description": self._match.result_description,
            "turn_id": self._turn_number,
        }

    async def register_connection(self, websocket: WebSocket) -> None:
        """Register the client WebSocket and ensure client has current state."""
        async with self._lock:
            self._websocket = websocket

            if self._stage != "IN_MATCH":
                await self._send_json_locked(self.get_pre_match_state_dict())
                return

            if self._awaiting_bowler_selection:
                innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
                active_bowling = (
                    self._match.bowling_1 if innings_num == 1 else self._match.bowling_2
                )
                active_innings = (
                    self._match.innings_1 if innings_num == 1 else self._match.innings_2
                )
                bowling_team = self._user_team
                eligible_list = [
                    {"id": pid, "name": bowling_team.get_player(pid).name}
                    for pid in active_bowling.eligible_bowlers
                    if bowling_team.get_player(pid)
                ]
                used_list = [
                    {"id": pid, "name": bowling_team.get_player(pid).name}
                    for pid in active_bowling.used_bowlers
                    if bowling_team.get_player(pid)
                ]
                over_num = active_innings.current_over if active_innings else 1
                bowler_req_msg = serialize_bowler_selection_required(
                    current_over=over_num,
                    eligible_bowlers=eligible_list,
                    used_bowlers=used_list,
                    match_state=self.get_match_state_dict(),
                )
                await self._send_json_locked(bowler_req_msg)
                return

            if not self._match.is_completed and not self._is_innings_break:
                if not self._turn_active and self._auto_start:
                    await self._start_turn_locked()
                elif self._turn_active:
                    # Supply current state to reconnecting or mounting client
                    msg = serialize_turn_started(self._timeout_seconds)
                    msg["match_state"] = self.get_match_state_dict()
                    msg["turn_id"] = self._turn_number
                    await self._send_json_locked(msg)
            elif self._is_innings_break:
                msg = serialize_turn_started(0.0)
                msg["match_state"] = self.get_match_state_dict()
                msg["turn_id"] = self._turn_number
                await self._send_json_locked(msg)
            elif self._match.is_completed:
                msg = serialize_turn_started(0.0)
                msg["match_state"] = self.get_match_state_dict()
                msg["turn_id"] = self._turn_number
                await self._send_json_locked(msg)
            elif self._match.is_completed:
                msg = serialize_turn_started(0.0)
                msg["match_state"] = self.get_match_state_dict()
                msg["turn_id"] = self._turn_number
                await self._send_json_locked(msg)

    async def unregister_connection(self, websocket: WebSocket) -> None:
        """Unregister the client WebSocket and cancel any pending timer."""
        async with self._lock:
            if self._websocket == websocket:
                self._websocket = None
                self._turn_active = False
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()

    async def start_turn(self) -> None:
        """Explicitly start the turn and launch the timer."""
        async with self._lock:
            await self._start_turn_locked()

    async def _start_turn_locked(self) -> None:
        """Broadcast turn_started and launch the 5-second timer."""
        if self._match.is_completed or self._is_innings_break:
            return

        self._turn_active = True
        self._turn_submitted = False
        self._user_choice = None
        msg = serialize_turn_started(self._timeout_seconds)
        msg["match_state"] = self.get_match_state_dict()
        msg["turn_id"] = self._turn_number
        await self._send_json_locked(msg)

        if self._timeout_seconds > 0:
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
            self._timer_task = asyncio.create_task(self._run_timer())

    async def _run_timer(self) -> None:
        """10-second server-authoritative timer for Computer Mode."""
        try:
            await asyncio.sleep(self._timeout_seconds)
            async with self._lock:
                if (
                    self._turn_active
                    and not self._turn_submitted
                    and not self._match.is_completed
                    and not self._is_innings_break
                ):
                    self._turn_submitted = True
                    # User timed out: generate random fallback choice for user
                    fallback_choice = self._bot.choose_number()
                    await self._resolve_ball_locked(fallback_choice, user_timed_out=True)
        except asyncio.CancelledError:
            pass

    def submit_number(self, user_number: int, turn_id: Optional[int] = None):
        """Process user number submission (1..6).

        Captures active turn ID synchronously at invocation time so concurrent calls
        for the active turn are bound to the current turn before any execution begins.
        """
        target_turn = turn_id if turn_id is not None else self._turn_number
        return self._submit_number_impl(user_number, target_turn)

    async def _submit_number_impl(self, user_number: int, target_turn: int) -> None:
        """Internal implementation of submit_number under session lock."""
        async with self._lock:
            if not self._match:
                raise TurnProtocolError("match_not_started", "Match has not started yet.")
            if self._match.is_completed:
                raise TurnProtocolError("match_completed", "Match is already completed.")
            if self._is_innings_break:
                raise TurnProtocolError("innings_break", "Innings 1 complete. Start innings 2.")
            if self._awaiting_bowler_selection:
                raise TurnProtocolError("awaiting_bowler", "Must select bowler before submitting number.")
            if not self._turn_active:
                raise TurnProtocolError("turn_inactive", "Turn is not currently active.")
            if self._turn_submitted or target_turn != self._turn_number:
                raise TurnProtocolError("already_submitted", "Choice has already been submitted for this turn.")

            # Validate number choice
            valid_number = validate_choice(user_number, role="user")

            # Mark turn as submitted immediately under lock
            self._turn_submitted = True

            # Cancel timer immediately
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()

            # Send hidden submission acknowledgment
            await self._send_json_locked(serialize_number_submitted())

            # Resolve ball
            await self._resolve_ball_locked(valid_number, user_timed_out=False)

    async def _resolve_ball_locked(self, user_choice: int, user_timed_out: bool = False) -> None:
        """Resolve ball outcome using domain engine and broadcast updated state."""
        self._turn_active = False

        innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
        user_is_batting = (
            self._user_is_batting_first if innings_num == 1 else not self._user_is_batting_first
        )

        # Capture active bowler ID before recording ball
        active_bowling = self._match.bowling_1 if innings_num == 1 else self._match.bowling_2
        bowler_id = (
            active_bowling.active_bowler
            if (active_bowling and active_bowling.active_bowler is not None)
            else (self._last_bowler_id or 11)
        )
        self._last_bowler_id = bowler_id

        # Computer generates its choice
        comp_choice = self._bot.choose_number()

        if user_is_batting:
            bat_choice = user_choice
            bowl_choice = comp_choice
        else:
            bat_choice = comp_choice
            bowl_choice = user_choice

        # Pure domain ball resolution
        ball_result = resolve_ball(batsman_choice=bat_choice, bowler_choice=bowl_choice)

        # Record striker name before ball in case of wicket
        active_innings = self._match.innings_1 if innings_num == 1 else self._match.innings_2
        striker_id = active_innings.striker if active_innings else 1
        batting_team = self._user_team if user_is_batting else self._opponent_team
        out_player_name = (
            batting_team.get_player(striker_id).name
            if ball_result.is_wicket and batting_team.get_player(striker_id)
            else None
        )

        # Record ball in pure match engine
        self._match.record_ball(ball_result)

        # Update bowler stats using the captured bowler ID
        stats_dict = (
            self._innings_1_bowler_stats if innings_num == 1 else self._innings_2_bowler_stats
        )
        if bowler_id not in stats_dict:
            stats_dict[bowler_id] = {"runs": 0, "balls": 0, "wickets": 0}
        stats_dict[bowler_id]["balls"] += 1
        stats_dict[bowler_id]["runs"] += ball_result.runs
        if ball_result.is_wicket:
            stats_dict[bowler_id]["wickets"] += 1

        # Update current over ball list
        if ball_result.is_wicket:
            self._current_over_balls.append("W")
        else:
            self._current_over_balls.append(ball_result.runs)

        # Classify event for UI animations
        if ball_result.is_wicket:
            event_type = "WICKET"
        elif ball_result.runs == 6:
            event_type = "SIX"
        elif ball_result.runs == 4:
            event_type = "FOUR"
        else:
            event_type = "NORMAL"

        self._last_ball_info = {
            "batsman_choice": bat_choice,
            "bowler_choice": bowl_choice,
            "runs": ball_result.runs,
            "is_wicket": ball_result.is_wicket,
            "user_choice": user_choice,
            "computer_choice": comp_choice,
            "user_timed_out": user_timed_out,
            "event": event_type,
            "out_player": out_player_name,
        }

        # Check over completion
        if active_innings and active_innings.over_complete:
            self._current_over_balls = []
            # Rotate bowler if innings is not complete
            if not active_innings.is_completed:
                active_bowling = (
                    self._match.bowling_1 if innings_num == 1 else self._match.bowling_2
                )
                if user_is_batting:
                    # Computer is bowling: select automatically
                    if self._skip_pre_match:
                        self._comp_bowler_idx = (self._comp_bowler_idx + 1) % len(self._comp_bowler_order)
                        next_bowler = self._comp_bowler_order[self._comp_bowler_idx]
                    else:
                        next_bowler = self._choose_computer_bowler(active_bowling.eligible_bowlers)
                    self._match.select_bowler(next_bowler)
                    self._last_bowler_id = next_bowler
                else:
                    # User is bowling: prompt bowler selection
                    if self._skip_pre_match:
                        self._user_bowler_idx = (self._user_bowler_idx + 1) % len(self._user_bowler_order)
                        next_bowler = self._user_bowler_order[self._user_bowler_idx]
                        self._match.select_bowler(next_bowler)
                        self._last_bowler_id = next_bowler
                    else:
                        self._awaiting_bowler_selection = True

        # Check innings 1 completion
        if innings_num == 1 and self._match.innings_1 and self._match.innings_1.is_completed:
            self._is_innings_break = True

        # Build ball result message
        result_msg = serialize_ball_result(
            batsman_choice=bat_choice,
            bowler_choice=bowl_choice,
            runs=ball_result.runs,
            is_wicket=ball_result.is_wicket,
            batting_participant="A" if user_is_batting else "B",
            bowling_participant="B" if user_is_batting else "A",
            choice_a=user_choice,
            choice_b=comp_choice,
            a_timed_out=user_timed_out,
            b_timed_out=False,
        )
        result_msg["match_state"] = self.get_match_state_dict()
        await self._send_json_locked(result_msg)

        # Advance turn number for next turn
        self._turn_number += 1

        if self._awaiting_bowler_selection:
            # Broadcast bowler selection required to user
            active_bowling = (
                self._match.bowling_1 if innings_num == 1 else self._match.bowling_2
            )
            bowling_team = self._user_team
            eligible_list = [
                {"id": pid, "name": bowling_team.get_player(pid).name}
                for pid in active_bowling.eligible_bowlers
                if bowling_team.get_player(pid)
            ]
            used_list = [
                {"id": pid, "name": bowling_team.get_player(pid).name}
                for pid in active_bowling.used_bowlers
                if bowling_team.get_player(pid)
            ]
            bowler_req_msg = serialize_bowler_selection_required(
                current_over=active_innings.current_over,
                eligible_bowlers=eligible_list,
                used_bowlers=used_list,
                match_state=self.get_match_state_dict(),
            )
            await self._send_json_locked(bowler_req_msg)
            return

        # If match is not complete and not innings break, start next turn automatically
        if not self._match.is_completed and not self._is_innings_break:
            await self._start_turn_locked()

    async def start_next_innings(self) -> None:
        """Start Innings 2 after Innings 1 break."""
        async with self._lock:
            if not self._is_innings_break:
                raise TurnProtocolError("not_innings_break", "Innings 1 is not complete.")

            self._is_innings_break = False
            self._match.start_innings_2()
            self._current_over_balls = []

            # In Innings 2, who is bowling?
            user_is_bowling = self._user_is_batting_first

            if user_is_bowling:
                if self._skip_pre_match:
                    self._user_bowler_idx = 0
                    first_bowler = self._user_bowler_order[self._user_bowler_idx]
                    self._match.select_bowler(first_bowler)
                    self._last_bowler_id = first_bowler
                    await self._start_turn_locked()
                else:
                    self._awaiting_bowler_selection = True
                    active_bowling = self._match.bowling_2
                    bowling_team = self._user_team
                    eligible_list = [
                        {"id": pid, "name": bowling_team.get_player(pid).name}
                        for pid in active_bowling.eligible_bowlers
                        if bowling_team.get_player(pid)
                    ]
                    bowler_req_msg = serialize_bowler_selection_required(
                        current_over=1,
                        eligible_bowlers=eligible_list,
                        used_bowlers=[],
                        match_state=self.get_match_state_dict(),
                    )
                    await self._send_json_locked(bowler_req_msg)
            else:
                if self._skip_pre_match:
                    self._comp_bowler_idx = 0
                    first_bowler = self._comp_bowler_order[self._comp_bowler_idx]
                else:
                    first_bowler = self._choose_computer_bowler(list(range(1, 12)))
                self._match.select_bowler(first_bowler)
                self._last_bowler_id = first_bowler
                await self._start_turn_locked()

    async def reset_game(self) -> None:
        """Reset the match to start a fresh game."""
        async with self._lock:
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
            if self._skip_pre_match:
                self._init_match()
                await self._start_turn_locked()
            else:
                self._init_pre_match()
                await self._send_json_locked(self.get_pre_match_state_dict())

    async def _send_json_locked(self, msg: Dict[str, Any]) -> None:
        """Send JSON message to the connected WebSocket."""
        if self._websocket is not None:
            try:
                await self._websocket.send_json(msg)
            except Exception:
                pass
