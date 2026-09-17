"""Friend Mode WebSocket protocol session and match coordination (Slice 15C).

This module coordinates dual WebSocket client connections for Participant A and B,
synchronizing room joining, independent team selection, coin toss, toss decision,
bowler selection, authoritative turns, ball resolution, and match completion.
"""

import asyncio
import logging
import secrets
import time
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

from backend.app.engine.ball import resolve_ball, validate_choice
from backend.app.engine.match import Match, MatchStatus
from backend.app.engine.pre_match import PreMatchError, PreMatchSetup
from backend.app.engine.teams import TeamNotFoundError, get_team
from backend.app.engine.toss import Participant, TossDecision
from backend.app.protocol.friend_turn import FriendTurn, FriendTurnView
from backend.app.protocol.messages import TurnProtocolError
from backend.app.protocol.room import FriendGameRoom, RoomStage

logger = logging.getLogger(__name__)


class FriendGameSession:
    """Coordinates dual WebSocket connections, turns, and authoritative cricket engine."""

    def __init__(
        self,
        room: FriendGameRoom,
        toss_chooser: Optional[Any] = None,
        max_overs: int = 5,
        balls_per_over: int = 6,
        timeout_seconds: float = 10.0,
        disconnect_grace_seconds: float = 60.0,
    ) -> None:
        self._room: FriendGameRoom = room
        self._pre_match: PreMatchSetup = PreMatchSetup(toss_chooser=toss_chooser)
        self._match: Optional[Match] = None
        self._max_overs: int = max_overs
        self._balls_per_over: int = balls_per_over
        self._timeout_seconds: float = timeout_seconds
        self._disconnect_grace_seconds: float = disconnect_grace_seconds
        self._disconnect_grace_tasks: Dict[Participant, asyncio.Task] = {}

        self._lock: asyncio.Lock = asyncio.Lock()
        self._sockets: Dict[Participant, WebSocket] = {}

        self._selected_bowler_id: Optional[int] = None
        self._last_bowler_id: Optional[int] = None
        self._innings_1_bowler_stats: Dict[int, Dict[str, Any]] = {}
        self._innings_2_bowler_stats: Dict[int, Dict[str, Any]] = {}

        # Turn and match progression state
        self._turn_number: int = 0
        self._current_turn: Optional[FriendTurn] = None
        self._timeout_task: Optional[asyncio.Task] = None
        self._current_over_balls: list = []
        self._last_ball_info: Optional[Dict[str, Any]] = None
        self._awaiting_bowler_selection: bool = False
        self._is_innings_break: bool = False
        self._innings_break_ready: Set[Participant] = set()
        self._rematch_ready: Set[Participant] = set()

    @property
    def room(self) -> FriendGameRoom:
        """Reference to the parent FriendGameRoom."""
        return self._room

    @property
    def stage(self) -> RoomStage:
        """Current room lifecycle stage."""
        return self._room.stage

    @property
    def pre_match(self) -> PreMatchSetup:
        """The underlying PreMatchSetup domain coordinator."""
        return self._pre_match

    @property
    def match(self) -> Optional[Match]:
        """The authoritative Match instance, or None if pre-match in progress."""
        return self._match

    @property
    def turn_number(self) -> int:
        """Current turn counter."""
        return self._turn_number

    @property
    def current_turn(self) -> Optional[FriendTurnView]:
        """Read-only view of the active turn."""
        return self._current_turn.as_view() if self._current_turn else None

    @property
    def is_awaiting_bowler_selection(self) -> bool:
        """True if the fielding participant must select a bowler before play continues."""
        return self._awaiting_bowler_selection

    @property
    def current_bowler_id(self) -> Optional[int]:
        """The currently active bowler player ID, or None."""
        return self._selected_bowler_id

    @property
    def bowler_selector(self) -> Optional[Participant]:
        """The participant responsible for selecting the bowler, or None."""
        if self._room.stage != RoomStage.BOWLER_SELECTION:
            return None
        if self._match is None:
            return self._pre_match.first_bowler_selector_participant
        innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
        a_bats_first = self._pre_match.batting_first_participant == Participant.A
        return (
            Participant.B
            if (innings_num == 1 and a_bats_first)
            or (innings_num == 2 and not a_bats_first)
            else Participant.A
        )

    @property
    def batting_participant(self) -> Optional[Participant]:
        """The currently batting participant, or None if pre-match."""
        if not self._match:
            return None
        innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
        a_bats_first = self._pre_match.batting_first_participant == Participant.A
        return (
            Participant.A
            if ((innings_num == 1 and a_bats_first) or (innings_num == 2 and not a_bats_first))
            else Participant.B
        )

    @property
    def bowling_participant(self) -> Optional[Participant]:
        """The currently bowling participant, or None if pre-match."""
        if not self._match:
            return None
        innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
        a_bats_first = self._pre_match.batting_first_participant == Participant.A
        return (
            Participant.B
            if ((innings_num == 1 and a_bats_first) or (innings_num == 2 and not a_bats_first))
            else Participant.A
        )

    @property
    def is_innings_break(self) -> bool:
        """True if Innings 1 is completed and awaiting start of Innings 2."""
        return self._is_innings_break

    # ---------------------------------------------------------------------------
    # WebSocket Connection Lifecycle & Reconnection
    # ---------------------------------------------------------------------------

    async def register_connection(
        self, participant: Participant, websocket: WebSocket
    ) -> None:
        """Register an accepted WebSocket connection for Participant A or B.

        Enforces 'NEW SOCKET REPLACES OLD SOCKET' and sends immediate authoritative sync_state.
        """
        async with self._lock:
            # 1. Duplicate Sockets: New socket replaces old socket cleanly
            old_ws = self._sockets.get(participant)
            if old_ws is not None and old_ws != websocket:
                try:
                    await old_ws.close(code=4001, reason="replaced_by_new_connection")
                except Exception as e:
                    logger.debug(f"Error closing replaced socket: {e}")

            # 2. Cancel any pending disconnect grace task for this participant
            if participant in self._disconnect_grace_tasks:
                task = self._disconnect_grace_tasks.pop(participant)
                if not task.done():
                    task.cancel()

            slot = (
                self._room.slot_a
                if participant == Participant.A
                else self._room.slot_b
            )
            is_reconnect = (
                old_ws is not None
                or (slot is not None and slot.connected_at is not None)
                or self._room.stage in (
                    RoomStage.IN_MATCH,
                    RoomStage.BOWLER_SELECTION,
                    RoomStage.INNINGS_BREAK,
                    RoomStage.MATCH_COMPLETED,
                )
            )

            now = time.monotonic()
            if slot is not None:
                slot.websocket = websocket
                if slot.connected_at is None:
                    slot.connected_at = now
                slot.last_seen_at = now

            self._sockets[participant] = websocket
            self._room.last_activity_at = now

            # 3. Send room_joined identity frame
            await websocket.send_json(
                {
                    "type": "room_joined",
                    "room_code": self._room.room_code,
                    "participant": participant.value,
                    "stage": self._room.stage.value,
                }
            )

            # 4. Check if both players newly connected to start match from WAITING_FOR_PLAYER
            a_connected = self._room.slot_a.is_connected
            b_connected = (
                self._room.slot_b is not None and self._room.slot_b.is_connected
            )

            if (
                a_connected
                and b_connected
                and self._room.stage == RoomStage.WAITING_FOR_PLAYER
            ):
                self._room.stage = RoomStage.TEAM_SELECTION
                await self.broadcast_locked(
                    {
                        "type": "player_joined",
                        "room_code": self._room.room_code,
                        "participant": participant.value,
                        "stage": self._room.stage.value,
                    }
                )
                await self.broadcast_locked(
                    {
                        "type": "stage_changed",
                        "room_code": self._room.room_code,
                        "stage": self._room.stage.value,
                    }
                )

            # 5. On reconnection: send authoritative sync_state & notify opponent
            if is_reconnect:
                sync_payload = self.get_sync_state_dict(participant)
                await websocket.send_json(sync_payload)

                opponent = Participant.B if participant == Participant.A else Participant.A
                if opponent in self._sockets and self._room.stage != RoomStage.WAITING_FOR_PLAYER:
                    await self.send_personal_locked(
                        opponent,
                        {
                            "type": "player_reconnected",
                            "room_code": self._room.room_code,
                            "participant": participant.value,
                        },
                    )

    async def unregister_connection(
        self, participant: Participant, websocket: WebSocket
    ) -> None:
        """Unregister a disconnected WebSocket connection cleanly with 60s grace period."""
        async with self._lock:
            # If the current registered socket is not this websocket (e.g. replaced by newer connection), ignore
            if self._sockets.get(participant) != websocket:
                return

            self._sockets.pop(participant, None)

            slot = (
                self._room.slot_a
                if participant == Participant.A
                else self._room.slot_b
            )
            if slot is not None and slot.websocket == websocket:
                slot.websocket = None
                slot.last_seen_at = time.monotonic()

            self._room.last_activity_at = time.monotonic()

            # Disconnect grace policy:
            # If room is closed or match completed or abandoned, no grace needed
            if (
                self._room.is_closed
                or self._room.stage in (RoomStage.MATCH_COMPLETED, RoomStage.ABANDONED, RoomStage.CLOSED)
            ):
                return

            opponent = Participant.B if participant == Participant.A else Participant.A
            opponent_connected = (
                opponent in self._sockets and self._sockets[opponent] is not None
            )

            if opponent_connected:
                # Notify opponent of disconnect and grace period
                await self.send_personal_locked(
                    opponent,
                    {
                        "type": "player_disconnected",
                        "room_code": self._room.room_code,
                        "participant": participant.value,
                        "grace_seconds": self._disconnect_grace_seconds,
                    },
                )

                # Launch background disconnect grace worker
                if participant in self._disconnect_grace_tasks:
                    old_task = self._disconnect_grace_tasks.pop(participant)
                    if not old_task.done():
                        old_task.cancel()

                self._disconnect_grace_tasks[participant] = asyncio.create_task(
                    self._disconnect_grace_worker(
                        participant, self._disconnect_grace_seconds
                    )
                )

    async def _disconnect_grace_worker(
        self, participant: Participant, grace_seconds: float
    ) -> None:
        """Wait for reconnect grace period; declare forfeit if grace expires."""
        try:
            await asyncio.sleep(grace_seconds)
        except asyncio.CancelledError:
            return

        async with self._lock:
            self._disconnect_grace_tasks.pop(participant, None)

            # If participant already reconnected, nothing to do
            if participant in self._sockets and self._sockets[participant] is not None:
                return

            # If room already closed or completed, nothing to do
            if (
                self._room.is_closed
                or self._room.stage in (RoomStage.MATCH_COMPLETED, RoomStage.ABANDONED, RoomStage.CLOSED)
            ):
                return

            opponent = Participant.B if participant == Participant.A else Participant.A
            opponent_connected = (
                opponent in self._sockets and self._sockets[opponent] is not None
            )

            # Cancel active turn timeout if running
            if self._timeout_task and not self._timeout_task.done():
                self._timeout_task.cancel()

            if self._room.stage in (
                RoomStage.IN_MATCH,
                RoomStage.BOWLER_SELECTION,
                RoomStage.INNINGS_BREAK,
            ):
                # Forfeit win for the remaining player!
                opponent_team = (
                    self._pre_match.team_b
                    if opponent == Participant.B
                    else self._pre_match.team_a
                )
                winner_name = (
                    opponent_team.name if opponent_team else f"Player {opponent.value}"
                )
                description = (
                    f"Player {participant.value} disconnected. Player {opponent.value} won by forfeit."
                )

                if self._match:
                    self._match._status = MatchStatus.COMPLETED
                    self._match._winner = winner_name
                    self._match._is_tie = False
                    self._match._result_description = description

                self._room.stage = RoomStage.MATCH_COMPLETED

                if opponent_connected:
                    await self.send_personal_locked(
                        opponent,
                        {
                            "type": "match_completed",
                            "room_code": self._room.room_code,
                            "stage": "MATCH_COMPLETED",
                            "winner": winner_name,
                            "is_tie": False,
                            "result_description": description,
                            "match_state": self.get_match_state_dict(opponent),
                        },
                    )
            elif self._room.stage in (
                RoomStage.TEAM_SELECTION,
                RoomStage.TOSS_DECISION,
                RoomStage.TOSS,
            ):
                self._room.stage = RoomStage.ABANDONED
                if opponent_connected:
                    await self.send_personal_locked(
                        opponent,
                        {
                            "type": "room_abandoned",
                            "room_code": self._room.room_code,
                            "stage": "ABANDONED",
                            "reason": f"Player {participant.value} disconnected and did not return.",
                        },
                    )

    async def broadcast_locked(self, message: Dict[str, Any]) -> None:
        """Broadcast a JSON message to all currently connected players (under lock)."""
        for part, ws in list(self._sockets.items()):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Failed to send to participant {part} in room {self._room.room_code}: {e}"
                )

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a JSON message to all currently connected players."""
        async with self._lock:
            await self.broadcast_locked(message)

    async def send_personal_locked(
        self, participant: Participant, message: Dict[str, Any]
    ) -> None:
        """Send a JSON message to a specific participant (under lock)."""
        ws = self._sockets.get(participant)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Failed to send to participant {participant} in room {self._room.room_code}: {e}"
                )

    async def send_personal(
        self, participant: Participant, message: Dict[str, Any]
    ) -> None:
        """Send a JSON message to a specific participant."""
        async with self._lock:
            await self.send_personal_locked(participant, message)

    # ---------------------------------------------------------------------------
    # Pre-Match Coordination
    # ---------------------------------------------------------------------------

    async def select_team(self, participant: Participant, team_id: str) -> None:
        """Process independent team selection for Participant A or B."""
        async with self._lock:
            self._check_room_active_locked()
            if self._room.stage != RoomStage.TEAM_SELECTION:
                raise TurnProtocolError(
                    "invalid_stage",
                    f"Cannot select team in stage {self._room.stage.value}.",
                )

            other_part = (
                Participant.B if participant == Participant.A else Participant.A
            )
            other_team = self._pre_match.get_team_for_participant(other_part)
            if (
                other_team is not None
                and other_team.id.upper() == team_id.strip().upper()
            ):
                raise TurnProtocolError(
                    "team_already_selected",
                    f"Team '{other_team.name}' has already been selected by your opponent. Please choose a different team.",
                )

            try:
                team = self._pre_match.select_team(participant, team_id)
            except TeamNotFoundError as err:
                raise TurnProtocolError("invalid_team", str(err))
            except PreMatchError as err:
                raise TurnProtocolError("team_already_selected", str(err))

            self._room.last_activity_at = time.monotonic()

            # Broadcast team selection update to both players
            await self.broadcast_locked(
                {
                    "type": "team_selected",
                    "participant": participant.value,
                    "team_id": team.id,
                    "team_name": team.name,
                }
            )

            # If both players have selected their teams, advance to toss automatically
            if self._pre_match.is_teams_selected:
                winner = self._pre_match.flip_toss()
                self._room.stage = RoomStage.TOSS_DECISION
                await self.broadcast_locked(
                    {
                        "type": "toss_result",
                        "winner": winner.value,
                        "stage": self._room.stage.value,
                    }
                )

    async def choose_toss(
        self, participant: Participant, decision_str: str
    ) -> None:
        """Process toss decision (BAT or BOWL) from the toss winner."""
        async with self._lock:
            self._check_room_active_locked()
            if self._room.stage != RoomStage.TOSS_DECISION:
                raise TurnProtocolError(
                    "invalid_stage",
                    f"Cannot choose toss in stage {self._room.stage.value}.",
                )

            if participant != self._pre_match.toss_winner:
                raise TurnProtocolError(
                    "not_toss_winner",
                    "Only the toss winning participant can choose bat or bowl.",
                )

            norm_decision = decision_str.strip().upper()
            if norm_decision not in ("BAT", "BOWL"):
                raise TurnProtocolError(
                    "invalid_toss_decision",
                    f"Decision must be 'BAT' or 'BOWL', got {decision_str!r}.",
                )

            toss_res = self._pre_match.choose_toss(
                decision=TossDecision(norm_decision),
                by=participant,
            )
            self._room.stage = RoomStage.BOWLER_SELECTION
            self._room.last_activity_at = time.monotonic()

            bowling_first_team = self._pre_match.bowling_first_team
            eligible_list = [
                {"id": p.id, "name": p.name}
                for p in bowling_first_team.players
            ] if bowling_first_team else []

            await self.broadcast_locked(
                {
                    "type": "toss_decision_result",
                    "decision": norm_decision,
                    "batting_first": toss_res.batting_first.value,
                    "bowling_first": toss_res.bowling_first.value,
                    "bowler_selector": toss_res.first_bowler_selector.value,
                    "stage": self._room.stage.value,
                    "current_over": 1,
                    "eligible_bowlers": eligible_list,
                    "used_bowlers": [],
                }
            )

    async def select_bowler(
        self, participant: Participant, bowler_id: int
    ) -> None:
        """Process opening bowler or mid-innings bowler selection."""
        async with self._lock:
            self._check_room_active_locked()
            if self._room.stage != RoomStage.BOWLER_SELECTION:
                raise TurnProtocolError(
                    "invalid_stage",
                    f"Cannot select bowler in stage {self._room.stage.value}.",
                )

            # Case A: Opening bowler selection (pre-match)
            if self._match is None:
                if participant != self._pre_match.first_bowler_selector_participant:
                    raise TurnProtocolError(
                        "not_bowler_selector",
                        "Only the bowling participant can select the first bowler.",
                    )

                bowling_team = self._pre_match.bowling_first_team
                if bowling_team is None:
                    raise TurnProtocolError(
                        "internal_error", "Bowling team is not configured."
                    )

                bowler = next(
                    (p for p in bowling_team.players if p.id == bowler_id), None
                )
                if not bowler:
                    raise TurnProtocolError(
                        "invalid_bowler_id",
                        f"Bowler ID {bowler_id} is not valid for {bowling_team.name}.",
                    )

                self._selected_bowler_id = bowler_id
                self._last_bowler_id = bowler_id

                # Initialize and start match
                self._match = self._pre_match.create_match(
                    max_overs=self._max_overs,
                    balls_per_over=self._balls_per_over,
                )
                self._match.start_innings_1()
                self._match.select_bowler(bowler_id)

                self._innings_1_bowler_stats[bowler_id] = {
                    "runs": 0,
                    "balls": 0,
                    "wickets": 0,
                }

                self._room.stage = RoomStage.IN_MATCH
                self._room.last_activity_at = time.monotonic()

                batting_first_part = self._pre_match.batting_first_participant
                bowling_first_part = self._pre_match.bowling_first_participant
                batting_team = self._pre_match.batting_first_team
                bowling_team = self._pre_match.bowling_first_team

                match_state = self.get_match_state_dict()

                await self.broadcast_locked(
                    {
                        "type": "match_started",
                        "room_code": self._room.room_code,
                        "stage": self._room.stage.value,
                        "batting_participant": (
                            batting_first_part.value if batting_first_part else "A"
                        ),
                        "bowling_participant": (
                            bowling_first_part.value if bowling_first_part else "B"
                        ),
                        "batting_team": {
                            "id": batting_team.id,
                            "name": batting_team.name,
                            "players": [{"id": p.id, "name": p.name} for p in batting_team.players],
                        } if batting_team else {},
                        "bowling_team": {
                            "id": bowling_team.id,
                            "name": bowling_team.name,
                            "players": [{"id": p.id, "name": p.name} for p in bowling_team.players],
                        } if bowling_team else {},
                        "current_bowler": {
                            "id": bowler.id,
                            "name": bowler.name,
                        },
                        "match_state": match_state,
                    }
                )

                # Launch turn 1!
                await self._start_turn_locked()
                return

            # Case B: Mid-innings or Innings 2 opening bowler selection
            innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
            a_bats_first = (
                self._pre_match.batting_first_participant == Participant.A
            )
            bowler_part = (
                Participant.B
                if (innings_num == 1 and a_bats_first) or (innings_num == 2 and not a_bats_first)
                else Participant.A
            )

            if participant != bowler_part:
                raise TurnProtocolError(
                    "not_bowler_selector",
                    "Only the fielding participant can select the bowler.",
                )

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
            self._selected_bowler_id = bowler_id
            self._last_bowler_id = bowler_id
            stats_dict = (
                self._innings_1_bowler_stats
                if innings_num == 1
                else self._innings_2_bowler_stats
            )
            if bowler_id not in stats_dict:
                stats_dict[bowler_id] = {"runs": 0, "balls": 0, "wickets": 0}
            self._awaiting_bowler_selection = False
            self._room.stage = RoomStage.IN_MATCH
            self._room.last_activity_at = time.monotonic()

            # Advance to next turn
            await self._start_turn_locked()

    def _check_room_active_locked(self) -> None:
        """Verify room is not closed or abandoned."""
        if self._room.is_closed:
            raise TurnProtocolError("room_closed", f"Room {self._room.room_code} is closed.")
        if self._room.stage == RoomStage.ABANDONED:
            raise TurnProtocolError("room_abandoned", f"Room {self._room.room_code} has been abandoned.")

    async def start_next_innings(
        self, participant: Optional[Participant] = None
    ) -> None:
        """Start Innings 2 after Innings 1 break (requires both players to confirm)."""
        async with self._lock:
            self._check_room_active_locked()

            # Idempotent: if already transitioned to Innings 2, return cleanly
            if self._match is not None and self._match.status == MatchStatus.INNINGS_2:
                return

            if self._match is not None and self._match.is_completed:
                raise TurnProtocolError("match_completed", "Match is already completed.")

            if not self._is_innings_break:
                raise TurnProtocolError(
                    "not_innings_break", "Innings 1 is not complete."
                )

            if participant is not None:
                self._innings_break_ready.add(participant)
                await self.broadcast_locked(
                    {
                        "type": "innings_break_acknowledged",
                        "participant": participant.value,
                        "ready_participants": [p.value for p in self._innings_break_ready],
                    }
                )
                if len(self._innings_break_ready) < 2:
                    return

            self._innings_break_ready.clear()
            self._is_innings_break = False
            self._match.start_innings_2()
            self._current_over_balls = []

            a_bats_first = (
                self._pre_match.batting_first_participant == Participant.A
            )
            innings_2_bowling_part = (
                Participant.A if a_bats_first else Participant.B
            )
            bowling_team = self._pre_match.batting_first_team
            active_bowling = self._match.bowling_2

            self._awaiting_bowler_selection = True
            self._room.stage = RoomStage.BOWLER_SELECTION

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
            await self.broadcast_locked(
                {
                    "type": "bowler_selection_required",
                    "room_code": self._room.room_code,
                    "current_over": 1,
                    "bowler_selector": innings_2_bowling_part.value,
                    "eligible_bowlers": eligible_list,
                    "used_bowlers": used_list,
                    "match_state": self.get_match_state_dict(),
                }
            )

    async def request_rematch(self, participant: Participant) -> None:
        """Request a rematch after match completion (requires both players to agree)."""
        async with self._lock:
            self._check_room_active_locked()

            if self._room.stage != RoomStage.MATCH_COMPLETED:
                raise TurnProtocolError("not_match_completed", "Match is not completed.")

            self._rematch_ready.add(participant)

            await self.broadcast_locked(
                {
                    "type": "rematch_requested",
                    "participant": participant.value,
                    "ready_participants": [p.value for p in self._rematch_ready],
                }
            )

            # Both players must agree before rematch starts
            if len(self._rematch_ready) < 2:
                return

            # Both agreed -> execute rematch reset
            self._rematch_ready.clear()
            self._innings_break_ready.clear()

            # Preserve team selections from pre_match
            team_a = self._pre_match.team_a
            team_b = self._pre_match.team_b

            # Cancel any lingering timeout task
            if self._timeout_task and not self._timeout_task.done():
                self._timeout_task.cancel()
                self._timeout_task = None

            # Reset match-specific state
            self._match = None
            self._turn_number = 0
            self._current_turn = None
            self._selected_bowler_id = None
            self._last_bowler_id = None
            self._innings_1_bowler_stats = {}
            self._innings_2_bowler_stats = {}
            self._current_over_balls = []
            self._last_ball_info = None
            self._awaiting_bowler_selection = False
            self._is_innings_break = False

            # Create fresh PreMatchSetup domain coordinator preserving teams
            self._pre_match = PreMatchSetup()
            if team_a:
                self._pre_match.select_team(Participant.A, team_a.id)
            if team_b:
                self._pre_match.select_team(Participant.B, team_b.id)

            # Fresh server-authoritative toss
            winner = self._pre_match.flip_toss()
            self._room.stage = RoomStage.TOSS_DECISION

            await self.broadcast_locked(
                {
                    "type": "toss_result",
                    "room_code": self._room.room_code,
                    "winner": winner.value,
                    "stage": "TOSS_DECISION",
                    "rematch": True,
                }
            )

    async def leave_room(self, participant: Participant) -> None:
        """Handle participant voluntarily leaving the room (e.g. from match result or settings)."""
        async with self._lock:
            if self._room.is_closed or self._room.stage == RoomStage.ABANDONED:
                return

            self._room.stage = RoomStage.ABANDONED
            self._rematch_ready.clear()
            self._innings_break_ready.clear()

            await self.broadcast_locked(
                {
                    "type": "room_abandoned",
                    "room_code": self._room.room_code,
                    "reason": f"Player {participant.value} left the match.",
                    "stage": "ABANDONED",
                }
            )

    # ---------------------------------------------------------------------------
    # Turn Lifecycle & Submission Coordination
    # ---------------------------------------------------------------------------

    async def _start_turn_locked(self) -> None:
        """Initialize and broadcast the next delivery turn."""
        if (
            self._match is None
            or self._match.is_completed
            or self._is_innings_break
            or self._awaiting_bowler_selection
        ):
            return

        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()

        self._turn_number += 1
        now = time.monotonic()
        deadline = now + self._timeout_seconds

        self._current_turn = FriendTurn(
            turn_id=self._turn_number,
            started_at=now,
            deadline=deadline,
        )

        turn_id = self._turn_number
        self._timeout_task = asyncio.create_task(
            self._turn_timeout_worker(turn_id, deadline)
        )

        await self.broadcast_locked(
            {
                "type": "turn_started",
                "turn_id": turn_id,
                "timeout_seconds": self._timeout_seconds,
                "match_state": self.get_match_state_dict(),
            }
        )

    async def _turn_timeout_worker(self, turn_id: int, deadline: float) -> None:
        """Server background worker enforcing authoritative 10-second deadline."""
        try:
            wait_seconds = max(0.0, deadline - time.monotonic())
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            async with self._lock:
                if (
                    self._current_turn is None
                    or self._current_turn.turn_id != turn_id
                    or self._current_turn.is_resolved
                ):
                    return

                # Deadline reached: mark unsubmitted participants and generate random fallback
                if self._current_turn.choice_a is None:
                    self._current_turn.a_timed_out = True
                    self._current_turn.choice_a = secrets.randbelow(6) + 1
                if self._current_turn.choice_b is None:
                    self._current_turn.b_timed_out = True
                    self._current_turn.choice_b = secrets.randbelow(6) + 1

                await self._resolve_turn_locked()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(
                f"Unexpected error in turn timeout worker for turn {turn_id}: {e}"
            )

    async def submit_number(
        self,
        participant: Participant,
        number: int,
        turn_id: Optional[int] = None,
    ) -> None:
        """Process a participant's number submission with strict secrecy and concurrency guards."""
        async with self._lock:
            self._check_room_active_locked()
            if self._room.stage != RoomStage.IN_MATCH:
                raise TurnProtocolError(
                    "not_in_match",
                    f"Cannot submit number in stage {self._room.stage.value}.",
                )

            if self._match is None or self._match.is_completed:
                raise TurnProtocolError(
                    "match_completed", "Match is already completed."
                )

            if self._is_innings_break:
                raise TurnProtocolError(
                    "innings_break", "Innings 1 complete. Start innings 2."
                )

            if self._awaiting_bowler_selection:
                raise TurnProtocolError(
                    "awaiting_bowler",
                    "Must select bowler before submitting number.",
                )

            if self._current_turn is None:
                raise TurnProtocolError(
                    "invalid_turn", "No turn is currently active."
                )

            # Stale / future turn check
            if turn_id is not None:
                if turn_id < self._current_turn.turn_id:
                    # Stale submission for prior turn: drop cleanly without second error
                    return
                if turn_id > self._current_turn.turn_id:
                    raise TurnProtocolError(
                        "invalid_turn",
                        f"Invalid turn_id {turn_id}. Current turn is {self._current_turn.turn_id}.",
                    )

            # Turn already resolved: drop cleanly (race with resolution)
            if self._current_turn.is_resolved:
                return

            # Check duplicate submission
            if self._current_turn.has_submitted(participant):
                raise TurnProtocolError(
                    "already_submitted",
                    "Choice has already been submitted for this turn.",
                )

            # Validate number choice (1..6)
            try:
                valid_number = validate_choice(number)
            except Exception as e:
                raise TurnProtocolError("invalid_number", str(e))

            now = time.monotonic()
            if self._current_turn.is_expired(now):
                # Late submission after deadline: mark timed out with fallback choice
                fallback = secrets.randbelow(6) + 1
                if participant == Participant.A:
                    self._current_turn.choice_a = fallback
                    self._current_turn.a_timed_out = True
                else:
                    self._current_turn.choice_b = fallback
                    self._current_turn.b_timed_out = True
            else:
                if participant == Participant.A:
                    self._current_turn.choice_a = valid_number
                    self._current_turn.a_submitted_at = now
                else:
                    self._current_turn.choice_b = valid_number
                    self._current_turn.b_submitted_at = now

            # Broadcast acknowledgment WITHOUT revealing the number (NON-NEGOTIABLE SECRECY)
            await self.broadcast_locked(
                {
                    "type": "number_submitted",
                    "turn_id": self._current_turn.turn_id,
                    "participant": participant.value,
                }
            )

            # If both choices ready, cancel timer and resolve delivery!
            if self._current_turn.is_ready_to_resolve:
                if self._timeout_task and not self._timeout_task.done():
                    self._timeout_task.cancel()
                await self._resolve_turn_locked()

    async def _resolve_turn_locked(self) -> None:
        """Authoritatively resolve the delivery using Ball Engine and Match Engine."""
        turn = self._current_turn
        if turn is None or turn.is_resolved:
            return

        turn.is_resolved = True

        innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
        a_bats_first = (
            self._pre_match.batting_first_participant == Participant.A
        )

        if innings_num == 1:
            batter_part = Participant.A if a_bats_first else Participant.B
            bowler_part = Participant.B if a_bats_first else Participant.A
        else:
            batter_part = Participant.B if a_bats_first else Participant.A
            bowler_part = Participant.A if a_bats_first else Participant.B

        batter_choice = (
            turn.choice_a if batter_part == Participant.A else turn.choice_b
        )
        bowler_choice = (
            turn.choice_b if batter_part == Participant.A else turn.choice_a
        )

        assert batter_choice is not None and bowler_choice is not None

        # Capture active bowler ID before recording ball
        active_bowling = (
            self._match.bowling_1 if innings_num == 1 else self._match.bowling_2
        )
        bowler_id = (
            active_bowling.active_bowler
            if (active_bowling and active_bowling.active_bowler is not None)
            else (self._last_bowler_id or 11)
        )
        self._last_bowler_id = bowler_id

        # Authoritative ball resolution using existing Ball Engine
        ball_result = resolve_ball(
            batsman_choice=batter_choice, bowler_choice=bowler_choice
        )

        # Record striker name before ball in case of wicket
        active_innings = (
            self._match.innings_1 if innings_num == 1 else self._match.innings_2
        )
        striker_id = active_innings.striker if active_innings else 1
        batting_team = (
            self._pre_match.batting_first_team
            if innings_num == 1
            else self._pre_match.bowling_first_team
        )
        out_player_name = (
            batting_team.get_player(striker_id).name
            if ball_result.is_wicket and batting_team and batting_team.get_player(striker_id)
            else None
        )

        # Record ball in pure match engine
        self._match.record_ball(ball_result)

        # Update bowler stats
        stats_dict = (
            self._innings_1_bowler_stats
            if innings_num == 1
            else self._innings_2_bowler_stats
        )
        if bowler_id not in stats_dict:
            stats_dict[bowler_id] = {"runs": 0, "balls": 0, "wickets": 0}
        stats_dict[bowler_id]["balls"] += 1
        stats_dict[bowler_id]["runs"] += ball_result.runs
        if ball_result.is_wicket:
            stats_dict[bowler_id]["wickets"] += 1

        # Update over ball list
        if ball_result.is_wicket:
            self._current_over_balls.append("W")
        else:
            self._current_over_balls.append(ball_result.runs)

        # Classify event
        if ball_result.is_wicket:
            event_type = "WICKET"
        elif ball_result.runs == 6:
            event_type = "SIX"
        elif ball_result.runs == 4:
            event_type = "FOUR"
        else:
            event_type = "NORMAL"

        self._last_ball_info = {
            "batsman_choice": batter_choice,
            "bowler_choice": bowler_choice,
            "runs": ball_result.runs,
            "is_wicket": ball_result.is_wicket,
            "event": event_type,
            "out_player": out_player_name,
        }

        active_innings = (
            self._match.innings_1 if innings_num == 1 else self._match.innings_2
        )

        # Check match and innings lifecycle completion
        match_just_completed = self._match.is_completed

        if match_just_completed:
            self._room.stage = RoomStage.MATCH_COMPLETED
        elif innings_num == 1 and active_innings and active_innings.is_completed:
            self._is_innings_break = True
            self._room.stage = RoomStage.INNINGS_BREAK
        elif active_innings and active_innings.over_complete:
            self._current_over_balls = []
            self._awaiting_bowler_selection = True
            self._room.stage = RoomStage.BOWLER_SELECTION

        # Broadcast ball_result with revealed choices and dismissed player info
        ball_msg = {
            "type": "ball_result",
            "turn_id": turn.turn_id,
            "batting_participant": batter_part.value,
            "bowling_participant": bowler_part.value,
            "batsman_choice": batter_choice,
            "bowler_choice": bowler_choice,
            "runs": ball_result.runs,
            "is_wicket": ball_result.is_wicket,
            "out_player": out_player_name,
            "choice_a": turn.choice_a,
            "choice_b": turn.choice_b,
            "a_timed_out": turn.a_timed_out,
            "b_timed_out": turn.b_timed_out,
            "match_state": self.get_match_state_dict(),
        }
        await self.broadcast_locked(ball_msg)

        # Post-ball progression:
        if match_just_completed:
            await self.broadcast_locked(
                {
                    "type": "match_completed",
                    "room_code": self._room.room_code,
                    "stage": "MATCH_COMPLETED",
                    "winner": self._match.winner,
                    "is_tie": self._match.is_tie,
                    "result_description": self._match.result_description,
                    "match_state": self.get_match_state_dict(),
                }
            )
            return

        if self._is_innings_break:
            await self.broadcast_locked(
                {
                    "type": "innings_break",
                    "room_code": self._room.room_code,
                    "stage": "INNINGS_BREAK",
                    "target": self._match.target,
                    "match_state": self.get_match_state_dict(),
                }
            )
            return

        if self._awaiting_bowler_selection:
            # Prompt fielding participant for the next bowler
            bowling_team = (
                self._pre_match.bowling_first_team
                if innings_num == 1
                else self._pre_match.batting_first_team
            )
            active_bowling = (
                self._match.bowling_1
                if innings_num == 1
                else self._match.bowling_2
            )
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
            await self.broadcast_locked(
                {
                    "type": "bowler_selection_required",
                    "room_code": self._room.room_code,
                    "current_over": active_innings.current_over,
                    "bowler_selector": bowler_part.value,
                    "eligible_bowlers": eligible_list,
                    "used_bowlers": used_list,
                    "match_state": self.get_match_state_dict(),
                }
            )
            return

        # Match continues: start next turn
        await self._start_turn_locked()

    # ---------------------------------------------------------------------------
    # State Serialization Helper
    # ---------------------------------------------------------------------------

    def get_match_state_dict(
        self, participant: Optional[Participant] = None
    ) -> Dict[str, Any]:
        """Build the authoritative match state payload."""
        if not self._match:
            return {}

        is_completed = self._match.is_completed
        innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
        active_innings = (
            self._match.innings_1 if innings_num == 1 else self._match.innings_2
        )

        a_bats_first = (
            self._pre_match.batting_first_participant == Participant.A
        )
        batting_part = (
            Participant.A
            if ((innings_num == 1 and a_bats_first) or (innings_num == 2 and not a_bats_first))
            else Participant.B
        )
        bowling_part = (
            Participant.B
            if ((innings_num == 1 and a_bats_first) or (innings_num == 2 and not a_bats_first))
            else Participant.A
        )

        batting_team = (
            self._pre_match.batting_first_team
            if innings_num == 1
            else self._pre_match.bowling_first_team
        )
        bowling_team = (
            self._pre_match.bowling_first_team
            if innings_num == 1
            else self._pre_match.batting_first_team
        )

        score = active_innings.total_runs if active_innings else 0
        wickets = active_innings.wickets if active_innings else 0
        total_balls = active_innings.total_balls if active_innings else 0
        bpo = active_innings.balls_per_over if active_innings else 6
        completed_overs = total_balls // bpo
        balls_in_over = total_balls % bpo
        overs_str = f"{completed_overs}.{balls_in_over}"

        striker_info: Dict[str, Any] = {"name": "", "runs": 0, "balls": 0}
        non_striker_info: Dict[str, Any] = {"name": "", "runs": 0, "balls": 0}

        if active_innings and not is_completed and batting_team:
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

        bowler_info: Dict[str, Any] = {
            "name": "",
            "overs": "0.0",
            "runs": 0,
            "wickets": 0,
            "figures": "0.0-0-0",
        }
        b_id = self._selected_bowler_id or self._last_bowler_id
        if b_id is not None and bowling_team:
            b_player = bowling_team.get_player(b_id)
            stats_dict = (
                self._innings_1_bowler_stats
                if innings_num == 1
                else self._innings_2_bowler_stats
            )
            b_stats = stats_dict.get(
                b_id, {"runs": 0, "balls": 0, "wickets": 0}
            )
            b_balls = b_stats["balls"]
            b_overs = f"{b_balls // 6}.{b_balls % 6}"
            bowler_info = {
                "id": b_id,
                "name": b_player.name if b_player else f"Player {b_id}",
                "overs": b_overs,
                "runs": b_stats["runs"],
                "wickets": b_stats["wickets"],
                "figures": f"{b_overs}-{b_stats['runs']}-{b_stats['wickets']}",
            }

        # Status string
        if is_completed:
            status_str = "COMPLETED"
        elif self._is_innings_break:
            status_str = "INNINGS_BREAK"
        elif innings_num == 1:
            status_str = "INNINGS_1"
        else:
            status_str = "INNINGS_2"

        # Participant-specific perspectives
        user_team_info = None
        opponent_team_info = None
        user_is_batting = False
        user_batted_first = False

        if participant is not None:
            u_t = self._pre_match.team_a if participant == Participant.A else self._pre_match.team_b
            o_t = self._pre_match.team_b if participant == Participant.A else self._pre_match.team_a
            if u_t:
                user_team_info = {"id": u_t.id, "name": u_t.name}
            if o_t:
                opponent_team_info = {"id": o_t.id, "name": o_t.name}
            user_is_batting = (batting_part == participant)
            user_batted_first = (self._pre_match.batting_first_participant == participant)

        return {
            "status": status_str,
            "innings": innings_num,
            "current_innings": innings_num,
            "batting_team": batting_team.name if batting_team else "",
            "bowling_team": bowling_team.name if bowling_team else "",
            "user_team": user_team_info,
            "opponent_team": opponent_team_info,
            "user_is_batting": user_is_batting,
            "user_batted_first": user_batted_first,
            "score": score,
            "wickets": wickets,
            "overs": overs_str,
            "max_overs": getattr(self._match, "max_overs", 5),
            "striker": striker_info,
            "non_striker": non_striker_info,
            "bowler": bowler_info,
            "current_over_balls": list(self._current_over_balls),
            "innings_1_score": self._match.innings_1_score,
            "innings_1_wickets": self._match.innings_1_wickets,
            "innings_2_score": self._match.innings_2_score,
            "innings_2_wickets": self._match.innings_2_wickets,
            "target": self._match.target,
            "is_completed": is_completed,
            "winner": self._match.winner,
            "is_tie": self._match.is_tie,
            "result_description": self._match.result_description,
            "batting_participant": batting_part.value,
            "bowling_participant": bowling_part.value,
            "batting_team_id": batting_team.id if batting_team else None,
            "bowling_team_id": bowling_team.id if bowling_team else None,
            "last_ball": getattr(self, "_last_ball_info", None),
            "turn_id": self._current_turn.turn_id if self._current_turn else 0,
        }

    def get_bowler_selection_prompt(self) -> Optional[Dict[str, Any]]:
        """Get bowler selection prompt details if room is awaiting bowler selection."""
        if self._room.stage != RoomStage.BOWLER_SELECTION:
            return None

        if self._match is None:
            selector = self._pre_match.first_bowler_selector_participant
            bowling_team = self._pre_match.bowling_first_team
            eligible_players = (
                [{"id": p.id, "name": p.name} for p in bowling_team.players]
                if bowling_team
                else []
            )
            used_players = []
            curr_over = 1
        else:
            innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2
            a_bats_first = (
                self._pre_match.batting_first_participant == Participant.A
            )
            bowler_part = (
                Participant.B
                if (innings_num == 1 and a_bats_first)
                or (innings_num == 2 and not a_bats_first)
                else Participant.A
            )
            selector = bowler_part
            bowling_team = (
                self._pre_match.bowling_first_team
                if innings_num == 1
                else self._pre_match.batting_first_team
            )
            active_bowling = (
                self._match.bowling_1 if innings_num == 1 else self._match.bowling_2
            )
            eligible_players = (
                [
                    {"id": pid, "name": bowling_team.get_player(pid).name}
                    for pid in active_bowling.eligible_bowlers
                    if bowling_team.get_player(pid)
                ]
                if bowling_team and active_bowling
                else []
            )
            used_players = (
                [
                    {"id": pid, "name": bowling_team.get_player(pid).name}
                    for pid in active_bowling.used_bowlers
                    if bowling_team.get_player(pid)
                ]
                if bowling_team and active_bowling
                else []
            )
            curr_over = (
                self._match.innings_1.current_over
                if innings_num == 1
                else self._match.innings_2.current_over
            ) if self._match else 1

        return {
            "bowler_selector": selector.value if selector else None,
            "current_over": curr_over,
            "eligible_bowlers": eligible_players,
            "used_bowlers": used_players,
        }

    def get_sync_state_dict(self, participant: Participant) -> Dict[str, Any]:
        """Build the authoritative state synchronization payload for a connecting/reconnecting participant."""
        now = time.monotonic()
        opponent = Participant.B if participant == Participant.A else Participant.A
        opponent_connected = (
            opponent in self._sockets and self._sockets[opponent] is not None
        )

        turn_id = None
        turn_remaining_seconds = 0.0
        has_submitted = False
        opponent_submitted = False

        if (
            self._room.stage == RoomStage.IN_MATCH
            and self._current_turn is not None
            and not self._current_turn.is_resolved
        ):
            turn = self._current_turn
            turn_id = turn.turn_id
            turn_remaining_seconds = max(0.0, turn.deadline - now)
            has_submitted = turn.has_submitted(participant)
            opponent_submitted = turn.has_submitted(opponent)

        bowler_prompt_data = self.get_bowler_selection_prompt()

        ms_dict = self.get_match_state_dict(participant)

        u_t = (
            self._pre_match.team_a
            if participant == Participant.A
            else self._pre_match.team_b
        )
        o_t = (
            self._pre_match.team_b
            if participant == Participant.A
            else self._pre_match.team_a
        )
        user_team_info = {"id": u_t.id, "name": u_t.name} if u_t else None
        opponent_team_info = {"id": o_t.id, "name": o_t.name} if o_t else None

        if not ms_dict and (user_team_info or opponent_team_info):
            ms_dict = {
                "user_team": user_team_info,
                "opponent_team": opponent_team_info,
            }

        innings_num = 1
        if self._match:
            innings_num = 1 if self._match.status == MatchStatus.INNINGS_1 else 2

        a_bats_first = self._pre_match.batting_first_participant == Participant.A
        batting_part = (
            Participant.A
            if ((innings_num == 1 and a_bats_first) or (innings_num == 2 and not a_bats_first))
            else Participant.B
        )
        bowling_part = (
            Participant.B
            if ((innings_num == 1 and a_bats_first) or (innings_num == 2 and not a_bats_first))
            else Participant.A
        )

        selected_num = None
        if self._current_turn and has_submitted:
            selected_num = (
                self._current_turn.choice_a
                if participant == Participant.A
                else self._current_turn.choice_b
            )

        turn_state = {
            "turn_id": turn_id,
            "timeout_seconds": turn_remaining_seconds,
            "has_submitted": has_submitted,
            "opponent_submitted": opponent_submitted,
            "selected_number": selected_num,
            "opponent_choice": None,  # SECRECY: Never leak unrevealed opponent pick
        }

        return {
            "type": "sync_state",
            "room_code": self._room.room_code,
            "participant": participant.value,
            "opponent_connected": opponent_connected,
            "stage": self._room.stage.value,
            "user_team": user_team_info,
            "opponent_team": opponent_team_info,
            "match_state": ms_dict,
            "innings": innings_num,
            "batting_participant": batting_part.value,
            "bowling_participant": bowling_part.value,
            "current_bowler": ms_dict.get("bowler", {}),
            "current_striker": ms_dict.get("striker", {}),
            "current_non_striker": ms_dict.get("non_striker", {}),
            "score": ms_dict.get("score", 0),
            "wickets": ms_dict.get("wickets", 0),
            "overs": ms_dict.get("overs", "0.0"),
            "target": self._match.target if self._match else None,
            "current_turn_id": turn_id,
            "turn_remaining_seconds": turn_remaining_seconds,
            "has_submitted": has_submitted,
            "opponent_submitted": opponent_submitted,
            "turn_state": turn_state,
            "bowler_selection_prompt": bowler_prompt_data,
            # Pre-match context
            "team_a": self._pre_match.team_a.id if self._pre_match.team_a else None,
            "team_b": self._pre_match.team_b.id if self._pre_match.team_b else None,
            "toss_winner": self._pre_match.toss_winner.value if self._pre_match.toss_winner else None,
            "toss_decision": (
                self._pre_match.toss_result.decision.value
                if self._pre_match.toss_result
                else None
            ),
            "innings_break_ready": [p.value for p in self._innings_break_ready],
            "rematch_ready": [p.value for p in self._rematch_ready],
        }
