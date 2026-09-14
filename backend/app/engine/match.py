"""Full match and target chasing domain engine for Hand Cricket.

This module coordinates a complete two-innings Hand Cricket match:
- Manages the match lifecycle: NOT_STARTED -> INNINGS_1 -> INNINGS_2 -> COMPLETED.
- Composes pure domain components: Innings (over/batting progression) and
  BowlingState (bowler quota enforcement).
- Calculates Innings 2 target (Innings 1 score + 1).
- Enforces target chasing in Innings 2 with immediate match completion upon
  reaching or exceeding the target.
- Enforces bowler selection before every over and coordinates over completion.
- Exposes read-only views for state inspection without mutation escape hatches.
"""

from enum import Enum
from typing import Optional

from backend.app.engine.ball import BallResult, resolve_ball
from backend.app.engine.batting import BattingStateView
from backend.app.engine.bowling import (
    DEFAULT_MAX_OVERS,
    DEFAULT_TEAM_SIZE,
    BowlingState,
    BowlingStateView,
)
from backend.app.engine.innings import (
    DEFAULT_BALLS_PER_OVER,
    Innings,
)


class MatchStatus(str, Enum):
    """Lifecycle states for a Hand Cricket match."""

    NOT_STARTED = "NOT_STARTED"
    INNINGS_1 = "INNINGS_1"
    INNINGS_2 = "INNINGS_2"
    COMPLETED = "COMPLETED"


class MatchError(ValueError):
    """Base domain exception for match orchestration errors."""

    pass


class MatchLifecycleError(MatchError):
    """Raised when an operation is invalid for the current match lifecycle state."""

    pass


class InningsTransitionError(MatchError):
    """Raised on invalid innings transition attempts (e.g. starting innings 2 prematurely)."""

    pass


class BowlerSelectionError(MatchError):
    """Raised when bowling requirements are not met (e.g. attempting to bowl without selecting a bowler)."""

    pass


class InningsView:
    """Read-only query view over an Innings instance.

    Exposes match progression and batting statistics without permitting
    direct mutation outside the Match coordinator.
    """

    def __init__(self, innings: Innings) -> None:
        self._innings = innings

    @property
    def current_over(self) -> int:
        """Current over number (1-indexed)."""
        return self._innings.current_over

    @property
    def balls_in_current_over(self) -> int:
        """Number of legal balls completed in the current over (0 to balls_per_over - 1)."""
        return self._innings.balls_in_current_over

    @property
    def total_balls(self) -> int:
        """Total legal balls completed in the innings."""
        return self._innings.total_balls

    @property
    def max_overs(self) -> int:
        """Maximum overs allowed for this innings."""
        return self._innings.max_overs

    @property
    def balls_per_over(self) -> int:
        """Number of balls per over."""
        return self._innings.balls_per_over

    @property
    def max_balls(self) -> int:
        """Maximum legal balls allowed in the innings."""
        return self._innings.max_balls

    @property
    def innings_complete(self) -> bool:
        """True if the innings has finished (all-out or ball limit reached)."""
        return self._innings.innings_complete

    @property
    def is_completed(self) -> bool:
        """Alias for innings_complete."""
        return self._innings.is_completed

    @property
    def over_complete(self) -> bool:
        """True if the most recently recorded ball completed an over."""
        return self._innings.over_complete

    @property
    def is_over_complete(self) -> bool:
        """Alias for over_complete."""
        return self._innings.is_over_complete

    @property
    def batting_state(self) -> BattingStateView:
        """Read-only query view of the underlying BattingState."""
        return self._innings.batting_state

    @property
    def striker(self) -> Optional[int]:
        """Current batsman facing strike, or None if all out."""
        return self._innings.striker

    @property
    def non_striker(self) -> Optional[int]:
        """Current batsman at the non-striker end."""
        return self._innings.non_striker

    @property
    def total_runs(self) -> int:
        """Total cumulative runs scored in this innings."""
        return self._innings.total_runs

    @property
    def wickets(self) -> int:
        """Total wickets lost in this innings."""
        return self._innings.wickets

    def __repr__(self) -> str:
        return f"InningsView({repr(self._innings)})"


class Match:
    """Orchestrates a complete two-innings Hand Cricket match with target chasing.

    Invariants:
        - Exactly two innings per match.
        - Innings 2 cannot begin until Innings 1 is complete.
        - Each over requires exactly one eligible bowler before balls can be bowled.
        - Each bowler can bowl at most one over per innings.
        - Target in Innings 2 is strictly (Innings 1 score + 1).
        - In Innings 2, if total_runs >= target, the match terminates immediately.
        - Mutation occurs strictly through match methods: start_innings_1, start_innings_2,
          select_bowler, and record_ball.
    """

    def __init__(
        self,
        team_1: str = "Team 1",
        team_2: str = "Team 2",
        team_size: int = DEFAULT_TEAM_SIZE,
        max_overs: int = DEFAULT_MAX_OVERS,
        balls_per_over: int = DEFAULT_BALLS_PER_OVER,
    ) -> None:
        if not isinstance(team_1, str) or not team_1.strip():
            raise MatchError(f"Invalid team_1 {team_1!r}: must be a non-empty string.")
        if not isinstance(team_2, str) or not team_2.strip():
            raise MatchError(f"Invalid team_2 {team_2!r}: must be a non-empty string.")
        if isinstance(max_overs, bool) or not isinstance(max_overs, int) or max_overs < 1:
            raise MatchError(f"Invalid max_overs {max_overs!r}: must be an integer >= 1.")
        if isinstance(balls_per_over, bool) or not isinstance(balls_per_over, int) or balls_per_over < 1:
            raise MatchError(f"Invalid balls_per_over {balls_per_over!r}: must be an integer >= 1.")
        if isinstance(team_size, bool) or not isinstance(team_size, int) or team_size < max_overs:
            raise MatchError(
                f"Invalid team_size {team_size!r}: must be an integer >= max_overs ({max_overs}) "
                f"to satisfy the one-over-per-bowler quota rule."
            )

        self._team_1: str = team_1
        self._team_2: str = team_2
        self._team_size: int = team_size
        self._max_overs: int = max_overs
        self._balls_per_over: int = balls_per_over
        self._max_balls: int = max_overs * balls_per_over

        self._status: MatchStatus = MatchStatus.NOT_STARTED

        self._innings_1: Optional[Innings] = None
        self._bowling_1: Optional[BowlingState] = None
        self._innings_1_view: Optional[InningsView] = None
        self._bowling_1_view: Optional[BowlingStateView] = None

        self._innings_2: Optional[Innings] = None
        self._bowling_2: Optional[BowlingState] = None
        self._innings_2_view: Optional[InningsView] = None
        self._bowling_2_view: Optional[BowlingStateView] = None

        self._target: Optional[int] = None
        self._winner: Optional[str] = None
        self._is_tie: bool = False
        self._result_description: Optional[str] = None

    @property
    def status(self) -> MatchStatus:
        """Current lifecycle status of the match."""
        return self._status

    @property
    def is_completed(self) -> bool:
        """True if the match has completed."""
        return self._status == MatchStatus.COMPLETED

    @property
    def team_1(self) -> str:
        """Name of Team 1 (bats first in Innings 1)."""
        return self._team_1

    @property
    def team_2(self) -> str:
        """Name of Team 2 (bowls first in Innings 1, chases in Innings 2)."""
        return self._team_2

    @property
    def team_size(self) -> int:
        """Number of players per team."""
        return self._team_size

    @property
    def max_overs(self) -> int:
        """Maximum overs per innings."""
        return self._max_overs

    @property
    def balls_per_over(self) -> int:
        """Number of balls per over."""
        return self._balls_per_over

    @property
    def max_balls(self) -> int:
        """Maximum legal balls per innings."""
        return self._max_balls

    @property
    def current_innings_number(self) -> Optional[int]:
        """The 1-indexed number of the current or final innings (1, 2, or None if not started)."""
        if self._status == MatchStatus.NOT_STARTED:
            return None
        if self._status == MatchStatus.INNINGS_1 or self._innings_2 is None:
            return 1
        return 2

    @property
    def current_innings(self) -> Optional[InningsView]:
        """Read-only view of the currently active or final innings."""
        if self._status == MatchStatus.NOT_STARTED:
            return None
        if self._status == MatchStatus.INNINGS_1 or self._innings_2 is None:
            return self._innings_1_view
        return self._innings_2_view

    @property
    def current_bowling_state(self) -> Optional[BowlingStateView]:
        """Read-only view of the currently active or final bowling state."""
        if self._status == MatchStatus.NOT_STARTED:
            return None
        if self._status == MatchStatus.INNINGS_1 or self._bowling_2 is None:
            return self._bowling_1_view
        return self._bowling_2_view

    @property
    def innings_1(self) -> Optional[InningsView]:
        """Read-only view of Innings 1, or None if not started."""
        return self._innings_1_view

    @property
    def innings_2(self) -> Optional[InningsView]:
        """Read-only view of Innings 2, or None if not started."""
        return self._innings_2_view

    @property
    def bowling_1(self) -> Optional[BowlingStateView]:
        """Read-only view of Innings 1 bowling state, or None if not started."""
        return self._bowling_1_view

    @property
    def bowling_2(self) -> Optional[BowlingStateView]:
        """Read-only view of Innings 2 bowling state, or None if not started."""
        return self._bowling_2_view

    @property
    def innings_1_score(self) -> Optional[int]:
        """Total runs scored in Innings 1, or None if Innings 1 has not started."""
        if self._innings_1 is None:
            return None
        return self._innings_1.total_runs

    @property
    def innings_1_wickets(self) -> Optional[int]:
        """Wickets lost in Innings 1, or None if Innings 1 has not started."""
        if self._innings_1 is None:
            return None
        return self._innings_1.wickets

    @property
    def innings_2_score(self) -> Optional[int]:
        """Total runs scored in Innings 2, or None if Innings 2 has not started."""
        if self._innings_2 is None:
            return None
        return self._innings_2.total_runs

    @property
    def innings_2_wickets(self) -> Optional[int]:
        """Wickets lost in Innings 2, or None if Innings 2 has not started."""
        if self._innings_2 is None:
            return None
        return self._innings_2.wickets

    @property
    def target(self) -> Optional[int]:
        """Target runs for Innings 2 (Innings 1 runs + 1), or None if Innings 1 not complete."""
        return self._target

    @property
    def winner(self) -> Optional[str]:
        """Winning team name, or None if match is tied or still in progress."""
        return self._winner

    @property
    def is_tie(self) -> bool:
        """True if the completed match ended in a tie."""
        return self._is_tie

    @property
    def result_description(self) -> Optional[str]:
        """Human-readable summary of the match result, or None if in progress."""
        return self._result_description

    @property
    def batting_team(self) -> Optional[str]:
        """Name of the team currently batting, or None if match not active."""
        if self._status == MatchStatus.INNINGS_1 or (self._status == MatchStatus.COMPLETED and self._innings_2 is None):
            return self._team_1
        if self._status == MatchStatus.INNINGS_2 or (self._status == MatchStatus.COMPLETED and self._innings_2 is not None):
            return self._team_2
        return None

    @property
    def bowling_team(self) -> Optional[str]:
        """Name of the team currently bowling, or None if match not active."""
        if self._status == MatchStatus.INNINGS_1 or (self._status == MatchStatus.COMPLETED and self._innings_2 is None):
            return self._team_2
        if self._status == MatchStatus.INNINGS_2 or (self._status == MatchStatus.COMPLETED and self._innings_2 is not None):
            return self._team_1
        return None

    def start_innings_1(self) -> None:
        """Start Innings 1 of the match.

        Raises:
            MatchLifecycleError: If match is already started or completed.
        """
        if self._status != MatchStatus.NOT_STARTED:
            raise MatchLifecycleError(
                f"Cannot start innings 1: match is already in state {self._status.value}."
            )
        self._status = MatchStatus.INNINGS_1
        self._innings_1 = Innings(
            team_size=self._team_size,
            max_overs=self._max_overs,
            balls_per_over=self._balls_per_over,
        )
        self._bowling_1 = BowlingState(
            team_size=self._team_size,
            max_overs=self._max_overs,
        )
        self._innings_1_view = InningsView(self._innings_1)
        self._bowling_1_view = self._bowling_1.as_view()

    def start_match(self) -> None:
        """Convenience alias for start_innings_1."""
        self.start_innings_1()

    def start_innings_2(self) -> None:
        """Start Innings 2 of the match after Innings 1 has completed.

        Raises:
            MatchLifecycleError: If match has not started, innings 2 is already active,
                or match is completed.
            InningsTransitionError: If innings 1 is still in progress.
        """
        if self._status == MatchStatus.NOT_STARTED:
            raise MatchLifecycleError("Cannot start innings 2: match has not started.")
        if self._status == MatchStatus.INNINGS_2:
            raise MatchLifecycleError("Cannot start innings 2: innings 2 has already started.")
        if self._status == MatchStatus.COMPLETED:
            raise MatchLifecycleError("Cannot start innings 2: match is already completed.")

        if self._innings_1 is None or not self._innings_1.is_completed:
            raise InningsTransitionError(
                "Cannot start innings 2: innings 1 is still in progress."
            )

        self._status = MatchStatus.INNINGS_2
        self._target = self._innings_1.total_runs + 1
        self._innings_2 = Innings(
            team_size=self._team_size,
            max_overs=self._max_overs,
            balls_per_over=self._balls_per_over,
        )
        self._bowling_2 = BowlingState(
            team_size=self._team_size,
            max_overs=self._max_overs,
        )
        self._innings_2_view = InningsView(self._innings_2)
        self._bowling_2_view = self._bowling_2.as_view()

    def select_bowler(self, bowler_id: int) -> int:
        """Assign an eligible bowler for the current over in the active innings.

        Args:
            bowler_id: Integer identifier of the bowler (1..team_size).

        Returns:
            The validated and assigned bowler ID.

        Raises:
            MatchLifecycleError: If match is not started, is completed, or active innings is complete.
            BowlingError subclasses: If bowler selection violates quota or lifecycle rules.
        """
        if self._status == MatchStatus.NOT_STARTED:
            raise MatchLifecycleError("Cannot select bowler: match has not started.")
        if self._status == MatchStatus.COMPLETED:
            raise MatchLifecycleError("Cannot select bowler: match is already completed.")

        if self._status == MatchStatus.INNINGS_1:
            if self._innings_1 is not None and self._innings_1.is_completed:
                raise MatchLifecycleError(
                    "Cannot select bowler: innings 1 is already complete. Start innings 2."
                )
            assert self._bowling_1 is not None
            return self._bowling_1.select_bowler(bowler_id)

        elif self._status == MatchStatus.INNINGS_2:
            if self._innings_2 is not None and self._innings_2.is_completed:
                raise MatchLifecycleError(
                    "Cannot select bowler: innings 2 is already complete."
                )
            assert self._bowling_2 is not None
            return self._bowling_2.select_bowler(bowler_id)

        raise MatchLifecycleError(f"Unexpected match state: {self._status}")

    def record_ball(self, ball_result: BallResult) -> None:
        """Process a single completed ball in the active innings.

        Coordinates single-ball consequences across Innings and BowlingState,
        handling over completion, target chasing, and match completion.

        Args:
            ball_result: The resolved BallResult from ball engine.

        Raises:
            MatchLifecycleError: If match is not started, completed, or active innings complete.
            BowlerSelectionError: If no bowler is active for the current over.
            TypeError: If ball_result is not a BallResult instance.
        """
        if self._status == MatchStatus.NOT_STARTED:
            raise MatchLifecycleError("Cannot process ball: match has not started.")
        if self._status == MatchStatus.COMPLETED:
            raise MatchLifecycleError("Cannot process ball: match is already completed.")

        if not isinstance(ball_result, BallResult):
            raise TypeError(
                f"Expected BallResult instance, got {type(ball_result).__name__}."
            )

        if self._status == MatchStatus.INNINGS_1:
            self._record_ball_innings_1(ball_result)
        elif self._status == MatchStatus.INNINGS_2:
            self._record_ball_innings_2(ball_result)
        else:
            raise MatchLifecycleError(f"Unexpected match state: {self._status}")

    def resolve_and_record_ball(self, bat_choice: int, bowl_choice: int) -> BallResult:
        """Resolve a single ball choice pair and record the result in the active innings.

        Convenience orchestration method composing ball resolution with match progression.

        Args:
            bat_choice: Batsman's number choice (1..6).
            bowl_choice: Bowler's number choice (1..6).

        Returns:
            The resolved BallResult.
        """
        ball_result = resolve_ball(bat_choice, bowl_choice)
        self.record_ball(ball_result)
        return ball_result

    def _record_ball_innings_1(self, ball_result: BallResult) -> None:
        """Process a ball within Innings 1."""
        assert self._innings_1 is not None
        assert self._bowling_1 is not None

        if self._innings_1.is_completed:
            raise MatchLifecycleError(
                "Cannot process ball: innings 1 is already complete. Start innings 2."
            )

        if not self._bowling_1.is_over_active:
            raise BowlerSelectionError(
                f"Cannot process ball: no bowler has been selected for Over {self._innings_1.current_over}."
            )

        # 1. Forward to Innings engine
        self._innings_1.record_ball(ball_result)

        # 2. Coordinate over completion with BowlingState
        if self._innings_1.over_complete:
            self._bowling_1.complete_over()

        # 3. Handle innings completion (deactivate bowling and set target)
        if self._innings_1.is_completed:
            self._bowling_1.end_innings()
            self._target = self._innings_1.total_runs + 1

    def _record_ball_innings_2(self, ball_result: BallResult) -> None:
        """Process a ball within Innings 2 with target chasing."""
        assert self._innings_2 is not None
        assert self._bowling_2 is not None
        assert self._target is not None
        assert self._innings_1 is not None

        if self._innings_2.is_completed:
            raise MatchLifecycleError(
                "Cannot process ball: innings 2 is already complete."
            )

        if not self._bowling_2.is_over_active:
            raise BowlerSelectionError(
                f"Cannot process ball: no bowler has been selected for Over {self._innings_2.current_over}."
            )

        # 1. Forward to Innings engine
        self._innings_2.record_ball(ball_result)

        # 2. Coordinate over completion with BowlingState
        if self._innings_2.over_complete:
            self._bowling_2.complete_over()

        # 3. Target chasing resolution
        if self._innings_2.total_runs >= self._target:
            # Target reached: Team 2 immediately wins!
            self._bowling_2.end_innings()
            wickets_in_hand = (self._team_size - 1) - self._innings_2.wickets
            self._complete_match(
                winner=self._team_2,
                is_tie=False,
                description=f"{self._team_2} won by {wickets_in_hand} wickets.",
            )
        elif self._innings_2.is_completed:
            # Innings 2 ended (all-out or max balls reached) without reaching target
            self._bowling_2.end_innings()
            if self._innings_2.total_runs < self._innings_1.total_runs:
                runs_diff = self._innings_1.total_runs - self._innings_2.total_runs
                self._complete_match(
                    winner=self._team_1,
                    is_tie=False,
                    description=f"{self._team_1} won by {runs_diff} runs.",
                )
            else:
                # Exactly equal scores: Tie
                self._complete_match(
                    winner=None,
                    is_tie=True,
                    description=f"Match tied ({self._innings_1.total_runs} - {self._innings_2.total_runs}).",
                )

    def forfeit(self, winner: str, description: str) -> None:
        """Terminate the match immediately due to forfeit.

        Safely cleans up any active over in BowlingState and transitions
        the match to COMPLETED state.
        """
        if self._status == MatchStatus.COMPLETED:
            return
        if self._bowling_1 and self._bowling_1.is_over_active:
            self._bowling_1.end_innings()
        if self._bowling_2 and self._bowling_2.is_over_active:
            self._bowling_2.end_innings()
        self._complete_match(winner=winner, is_tie=False, description=description)

    def _complete_match(
        self,
        winner: Optional[str],
        is_tie: bool,
        description: str,
    ) -> None:
        """Transition match to COMPLETED state and record final outcome."""
        self._status = MatchStatus.COMPLETED
        self._winner = winner
        self._is_tie = is_tie
        self._result_description = description

    def as_view(self) -> "MatchView":
        """Return a read-only query view of this match instance."""
        return MatchView(self)

    def __repr__(self) -> str:
        return (
            f"Match(status={self._status.value}, "
            f"team_1={self._team_1!r}, team_2={self._team_2!r}, "
            f"target={self._target}, winner={self._winner!r}, tie={self._is_tie})"
        )


class MatchView:
    """Read-only query view over a Match instance.

    Exposes match properties and inspection helpers while strictly omitting
    mutator methods (`start_match`, `start_innings_1`, `start_innings_2`,
    `select_bowler`, `record_ball`, `resolve_and_record_ball`) to prevent state corruption.
    """

    def __init__(self, match: Match) -> None:
        self._match = match

    @property
    def status(self) -> MatchStatus:
        """Current lifecycle status of the match."""
        return self._match.status

    @property
    def is_completed(self) -> bool:
        """True if the match has completed."""
        return self._match.is_completed

    @property
    def team_1(self) -> str:
        """Name of Team 1."""
        return self._match.team_1

    @property
    def team_2(self) -> str:
        """Name of Team 2."""
        return self._match.team_2

    @property
    def team_size(self) -> int:
        """Number of players per team."""
        return self._match.team_size

    @property
    def max_overs(self) -> int:
        """Maximum overs per innings."""
        return self._match.max_overs

    @property
    def balls_per_over(self) -> int:
        """Number of balls per over."""
        return self._match.balls_per_over

    @property
    def max_balls(self) -> int:
        """Maximum legal balls per innings."""
        return self._match.max_balls

    @property
    def current_innings_number(self) -> Optional[int]:
        """The 1-indexed number of the current or final innings (1, 2, or None)."""
        return self._match.current_innings_number

    @property
    def current_innings(self) -> Optional[InningsView]:
        """Read-only view of the currently active or final innings."""
        return self._match.current_innings

    @property
    def current_bowling_state(self) -> Optional[BowlingStateView]:
        """Read-only view of the currently active or final bowling state."""
        return self._match.current_bowling_state

    @property
    def innings_1(self) -> Optional[InningsView]:
        """Read-only view of Innings 1, or None if not started."""
        return self._match.innings_1

    @property
    def innings_2(self) -> Optional[InningsView]:
        """Read-only view of Innings 2, or None if not started."""
        return self._match.innings_2

    @property
    def bowling_1(self) -> Optional[BowlingStateView]:
        """Read-only view of Innings 1 bowling state, or None if not started."""
        return self._match.bowling_1

    @property
    def bowling_2(self) -> Optional[BowlingStateView]:
        """Read-only view of Innings 2 bowling state, or None if not started."""
        return self._match.bowling_2

    @property
    def innings_1_score(self) -> Optional[int]:
        """Total runs scored in Innings 1, or None."""
        return self._match.innings_1_score

    @property
    def innings_1_wickets(self) -> Optional[int]:
        """Wickets lost in Innings 1, or None."""
        return self._match.innings_1_wickets

    @property
    def innings_2_score(self) -> Optional[int]:
        """Total runs scored in Innings 2, or None."""
        return self._match.innings_2_score

    @property
    def innings_2_wickets(self) -> Optional[int]:
        """Wickets lost in Innings 2, or None."""
        return self._match.innings_2_wickets

    @property
    def target(self) -> Optional[int]:
        """Target runs for Innings 2, or None."""
        return self._match.target

    @property
    def winner(self) -> Optional[str]:
        """Winning team name, or None."""
        return self._match.winner

    @property
    def is_tie(self) -> bool:
        """True if the match ended in a tie."""
        return self._match.is_tie

    @property
    def result_description(self) -> Optional[str]:
        """Human-readable summary of the match result, or None."""
        return self._match.result_description

    @property
    def batting_team(self) -> Optional[str]:
        """Name of the team currently batting, or None."""
        return self._match.batting_team

    @property
    def bowling_team(self) -> Optional[str]:
        """Name of the team currently bowling, or None."""
        return self._match.bowling_team

    def __repr__(self) -> str:
        return f"MatchView({repr(self._match)})"
