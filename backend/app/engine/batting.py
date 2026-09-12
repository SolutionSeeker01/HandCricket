"""Batsman lifecycle and score tracking domain engine for Hand Cricket.

This module manages the batting state across balls in an innings, including
individual batsman scores, total team runs, wicket tallies, striker / non-striker
rotations, and new batsman arrivals upon dismissals.
"""

from typing import Dict, List, Optional

from backend.app.engine.ball import BallResult

DEFAULT_TEAM_SIZE: int = 11


class BattingLifecycleError(ValueError):
    """Base domain exception for invalid batting lifecycle operations."""
    pass


class NoAvailableBatsmanError(BattingLifecycleError):
    """Raised when an action requires an active striker or new batsman, but none is available."""
    pass


class InvalidBatsmanError(BattingLifecycleError):
    """Raised when a batsman identifier is invalid or outside the team roster."""
    pass


class BattingState:
    """Manages the state and lifecycle of the batting side in an innings.

    Attributes:
        team_size: Total number of batsmen on the team (default 11).
        striker: The ID (1..team_size) of the active batsman on strike.
        non_striker: The ID (1..team_size) of the active batsman at the non-striker's end.
        next_batsman_id: The ID of the next batsman waiting to enter from the pavilion.
        total_runs: Total cumulative runs scored in this batting innings.
        wickets: Total number of wickets lost in this batting innings.
        balls_processed: Total number of balls processed in this batting state.
        individual_scores: Mapping of batsman ID to runs scored.
        balls_faced: Mapping of batsman ID to balls faced.
        dismissed_batsmen: Ordered list of dismissed batsman IDs.
    """

    def __init__(self, team_size: int = DEFAULT_TEAM_SIZE) -> None:
        if isinstance(team_size, bool) or not isinstance(team_size, int) or team_size < 2:
            raise BattingLifecycleError(
                f"Invalid team size {team_size!r}: team size must be an integer >= 2."
            )

        self._team_size: int = team_size
        self._striker: Optional[int] = 1
        self._non_striker: Optional[int] = 2
        self._next_batsman_id: int = 3
        self._total_runs: int = 0
        self._wickets: int = 0
        self._balls_processed: int = 0

        # Initialize all batsmen in roster with 0 runs and 0 balls faced
        self._individual_scores: Dict[int, int] = {i: 0 for i in range(1, team_size + 1)}
        self._balls_faced: Dict[int, int] = {i: 0 for i in range(1, team_size + 1)}
        self._dismissed_batsmen: List[int] = []

    @property
    def team_size(self) -> int:
        """Total number of players in the batting lineup."""
        return self._team_size

    @property
    def striker(self) -> Optional[int]:
        """ID of the current active batsman facing the ball, or None if all out."""
        return self._striker

    @property
    def non_striker(self) -> Optional[int]:
        """ID of the current active batsman at the non-striker end."""
        return self._non_striker

    @property
    def next_batsman_id(self) -> int:
        """ID of the next batsman waiting to enter."""
        return self._next_batsman_id

    @property
    def total_runs(self) -> int:
        """Total cumulative runs scored by the batting team."""
        return self._total_runs

    @property
    def wickets(self) -> int:
        """Total number of wickets lost."""
        return self._wickets

    @property
    def balls_processed(self) -> int:
        """Total number of balls recorded in this batting innings."""
        return self._balls_processed

    @property
    def individual_scores(self) -> Dict[int, int]:
        """Copy of individual scores for all batsmen."""
        return dict(self._individual_scores)

    @property
    def balls_faced(self) -> Dict[int, int]:
        """Copy of balls faced by each batsman."""
        return dict(self._balls_faced)

    @property
    def dismissed_batsmen(self) -> List[int]:
        """Copy of the list of dismissed batsmen in order of dismissal."""
        return list(self._dismissed_batsmen)

    def is_dismissed(self, batsman_id: int) -> bool:
        """Check if a specific batsman has been dismissed."""
        self._validate_batsman_id(batsman_id)
        return batsman_id in self._dismissed_batsmen

    def get_batsman_score(self, batsman_id: int) -> int:
        """Get the current runs scored by a specific batsman."""
        self._validate_batsman_id(batsman_id)
        return self._individual_scores[batsman_id]

    def get_batsman_balls(self, batsman_id: int) -> int:
        """Get the number of balls faced by a specific batsman."""
        self._validate_batsman_id(batsman_id)
        return self._balls_faced[batsman_id]

    def _validate_batsman_id(self, batsman_id: int) -> None:
        """Validate that a batsman ID is an integer within the roster boundaries."""
        if isinstance(batsman_id, bool) or not isinstance(batsman_id, int):
            raise InvalidBatsmanError(
                f"Invalid batsman ID {batsman_id!r}: ID must be an integer, got {type(batsman_id).__name__}."
            )
        if batsman_id < 1 or batsman_id > self._team_size:
            raise InvalidBatsmanError(
                f"Invalid batsman ID {batsman_id}: ID must be between 1 and {self._team_size}."
            )

    def record_ball(self, ball_result: BallResult) -> None:
        """Update batting state based on the result of a single ball.

        Rules:
        - When runs are scored:
            * Runs added to striker's individual score.
            * Runs added to team total.
            * Odd runs (1, 3, 5): striker and non-striker swap ends.
            * Even runs (2, 4, 6): striker and non-striker remain in place.
        - When a wicket falls:
            * Current striker is dismissed and added to dismissed list.
            * Wicket count increments by 1.
            * The next available batsman enters as the new active striker.
            * Non-striker remains in place.

        Args:
            ball_result: An immutable BallResult instance.

        Raises:
            TypeError: If ball_result is not a BallResult.
            NoAvailableBatsmanError: If there is no active striker to face the ball.
            BattingLifecycleError: If internal state detects an already-dismissed striker.
        """
        if not isinstance(ball_result, BallResult):
            raise TypeError(
                f"Expected BallResult instance, got {type(ball_result).__name__}."
            )

        if self._striker is None:
            raise NoAvailableBatsmanError(
                "Cannot record ball: no active striker is available on the pitch."
            )

        current_striker = self._striker

        if current_striker in self._dismissed_batsmen:
            raise BattingLifecycleError(
                f"Cannot record ball: active striker {current_striker} has already been dismissed."
            )

        self._balls_processed += 1
        self._balls_faced[current_striker] += 1

        if ball_result.is_wicket:
            # 1. Dismiss the striker
            self._wickets += 1
            self._dismissed_batsmen.append(current_striker)
            self._striker = None

            # 2. Next available batsman enters as new striker
            if self._next_batsman_id <= self._team_size:
                self._striker = self._next_batsman_id
                self._next_batsman_id += 1
        else:
            # 1. Accumulate runs
            runs = ball_result.runs
            self._individual_scores[current_striker] += runs
            self._total_runs += runs

            # 2. Odd-run striker swap
            if runs % 2 != 0:
                if self._non_striker is not None:
                    self._striker, self._non_striker = self._non_striker, self._striker
