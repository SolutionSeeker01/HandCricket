"""Over and innings progression domain engine for Hand Cricket.

This module coordinates the progression of a single innings, managing over
numbering, balls bowled per over, total balls limit (30 balls / 5 overs),
and termination conditions (all-out or ball limit reached).

It encapsulates a BattingState instance and delegates single-ball batting
consequences to it.
"""

from typing import Optional

from backend.app.engine.ball import BallResult
from backend.app.engine.batting import DEFAULT_TEAM_SIZE, BattingState

DEFAULT_MAX_OVERS: int = 5
DEFAULT_BALLS_PER_OVER: int = 6


class InningsError(ValueError):
    """Base domain exception for innings progression errors."""
    pass


class InningsCompleteError(InningsError):
    """Raised when an action is attempted on an already completed innings."""
    pass


class Innings:
    """Manages the progression of a single innings in Hand Cricket.

    Attributes:
        current_over: The 1-indexed over currently being bowled (1..5).
        balls_in_current_over: Number of balls completed in the current over (0..5).
        total_balls: Total number of balls completed in this innings (0..30).
        max_overs: Maximum overs in this innings (default 5).
        balls_per_over: Number of legal balls per over (default 6).
        max_balls: Maximum balls in this innings (max_overs * balls_per_over = 30).
        innings_complete: Whether the innings has completed (ball limit or all-out).
        is_completed: Alias for innings_complete.
        over_complete: True if the most recently recorded ball completed an over.
        is_over_complete: Alias for over_complete.
        batting_state: The underlying BattingState tracking scores and wickets.
    """

    def __init__(
        self,
        team_size: int = DEFAULT_TEAM_SIZE,
        max_overs: int = DEFAULT_MAX_OVERS,
        balls_per_over: int = DEFAULT_BALLS_PER_OVER,
        batting_state: Optional[BattingState] = None,
    ) -> None:
        if isinstance(max_overs, bool) or not isinstance(max_overs, int) or max_overs < 1:
            raise InningsError(
                f"Invalid max_overs {max_overs!r}: max_overs must be an integer >= 1."
            )

        if isinstance(balls_per_over, bool) or not isinstance(balls_per_over, int) or balls_per_over < 1:
            raise InningsError(
                f"Invalid balls_per_over {balls_per_over!r}: balls_per_over must be an integer >= 1."
            )

        if batting_state is not None:
            if not isinstance(batting_state, BattingState):
                raise TypeError(
                    f"Expected BattingState instance, got {type(batting_state).__name__}."
                )
            self._batting_state: BattingState = batting_state
        else:
            self._batting_state = BattingState(team_size=team_size)

        self._max_overs: int = max_overs
        self._balls_per_over: int = balls_per_over
        self._max_balls: int = max_overs * balls_per_over

        self._current_over: int = 1
        self._balls_in_current_over: int = 0
        self._total_balls: int = 0
        self._is_completed: bool = (self._batting_state.striker is None)

    @property
    def current_over(self) -> int:
        """Current over number (1-indexed)."""
        return self._current_over

    @property
    def balls_in_current_over(self) -> int:
        """Number of legal balls completed in the current over (0 to balls_per_over - 1)."""
        return self._balls_in_current_over

    @property
    def total_balls(self) -> int:
        """Total legal balls completed in the innings."""
        return self._total_balls

    @property
    def max_overs(self) -> int:
        """Maximum overs allowed for this innings."""
        return self._max_overs

    @property
    def balls_per_over(self) -> int:
        """Number of balls per over."""
        return self._balls_per_over

    @property
    def max_balls(self) -> int:
        """Maximum legal balls allowed in the innings."""
        return self._max_balls

    @property
    def innings_complete(self) -> bool:
        """True if the innings has finished (all-out or ball limit reached)."""
        return self._is_completed

    @property
    def is_completed(self) -> bool:
        """Alias for innings_complete."""
        return self._is_completed

    @property
    def over_complete(self) -> bool:
        """True if the most recently recorded ball completed an over, False otherwise.

        Semantics:
        This indicates that the ball just bowled was the final (6th) ball of an over.
        It means 'the most recently recorded ball completed an over', NOT 'the currently
        active over is complete'. Once an over completes, the innings immediately transitions
        to the next over with 0 balls bowled (unless the innings is complete).
        """
        return self._total_balls > 0 and self._balls_in_current_over == 0

    @property
    def is_over_complete(self) -> bool:
        """Alias for over_complete: True if the most recently recorded ball completed an over."""
        return self.over_complete

    @property
    def batting_state(self) -> BattingState:
        """The underlying BattingState instance."""
        return self._batting_state

    # Convenience delegating properties to BattingState
    @property
    def striker(self) -> Optional[int]:
        """Current batsman facing strike, or None if all out."""
        return self._batting_state.striker

    @property
    def non_striker(self) -> Optional[int]:
        """Current batsman at the non-striker end."""
        return self._batting_state.non_striker

    @property
    def total_runs(self) -> int:
        """Total cumulative runs scored in this innings."""
        return self._batting_state.total_runs

    @property
    def wickets(self) -> int:
        """Total wickets lost in this innings."""
        return self._batting_state.wickets

    def record_ball(self, ball_result: BallResult) -> None:
        """Process a completed ball within this innings.

        Execution flow:
        1. Guard against recording a ball when innings is already complete.
        2. Validate that ball_result is a BallResult instance.
        3. Pass ball_result to BattingState.record_ball().
        4. Increment ball counters.
        5. Check innings completion (max balls reached OR batting side all out).
        6. Check over completion (reset balls_in_current_over, advance current_over if not complete).

        Args:
            ball_result: The resolved BallResult from ball engine.

        Raises:
            InningsCompleteError: If the innings has already finished.
            TypeError: If ball_result is not a BallResult.
        """
        if self._is_completed:
            raise InningsCompleteError("Cannot record ball: innings is already complete.")

        if not isinstance(ball_result, BallResult):
            raise TypeError(
                f"Expected BallResult instance, got {type(ball_result).__name__}."
            )

        # 1. Forward to batting engine to update scores, wickets, and striker
        self._batting_state.record_ball(ball_result)

        # 2. Advance ball counters
        self._balls_in_current_over += 1
        self._total_balls += 1

        # 3. Check innings completion
        if self._total_balls == self._max_balls or self._batting_state.striker is None:
            self._is_completed = True

        # 4. Check over completion
        if self._balls_in_current_over == self._balls_per_over:
            self._balls_in_current_over = 0
            if not self._is_completed:
                self._current_over += 1

    def __repr__(self) -> str:
        return (
            f"Innings(over={self._current_over}/{self._max_overs}, "
            f"ball={self._balls_in_current_over}/{self._balls_per_over}, "
            f"total_balls={self._total_balls}/{self._max_balls}, "
            f"runs={self.total_runs}, wickets={self.wickets}, "
            f"complete={self._is_completed})"
        )
