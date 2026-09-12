"""Bowler quota enforcement domain engine for Hand Cricket.

This module implements the pure domain logic for enforcing the bowler quota
in an innings: each bowler may bowl at most one over per innings.
Across a 5-over innings, exactly 5 distinct bowlers are required.

It tracks which bowlers have already bowled, which are currently eligible,
and manages the active bowler lifecycle across over assignments.
"""

from typing import Dict, List, Optional

DEFAULT_TEAM_SIZE: int = 11
DEFAULT_MAX_OVERS: int = 5


class BowlingError(ValueError):
    """Base domain exception for bowling quota and lifecycle operations."""
    pass


class InvalidBowlerError(BowlingError):
    """Raised when a bowler identifier is invalid, outside roster boundaries, or has an invalid type."""
    pass


class BowlerAlreadyBowledError(BowlingError):
    """Raised when an attempt is made to select a bowler who has already bowled in this innings."""
    pass


class BowlingLifecycleError(BowlingError):
    """Raised on invalid over assignment, duplicate active over, or premature completion."""
    pass


class BowlingState:
    """Manages bowler quota, eligibility, and over-to-bowler assignments in an innings.

    Invariants:
        - used_bowlers ⊆ valid_bowlers (1..team_size)
        - used_bowlers contains no duplicates
        - eligible_bowlers = valid_bowlers - used_bowlers
        - A bowler becomes used immediately upon selection for an over
        - At most one over per bowler per innings

    Attributes:
        team_size: Total number of players on the bowling team (default 11).
        max_overs: Maximum overs in this innings (default 5).
        current_over: 1-indexed over currently being assigned or bowled (1..5).
        completed_overs: Number of completed overs (0..5).
        active_bowler: ID of the bowler currently bowling, or None if awaiting selection.
        current_bowler: Alias for active_bowler.
        used_bowlers: List of bowler IDs that have bowled or are currently bowling.
        eligible_bowlers: List of bowler IDs still eligible to bowl.
        over_bowlers: Mapping of over number (1..5) to assigned bowler ID.
        is_innings_bowling_complete: True if all max_overs have been completed.
        is_over_active: True if an over is currently in progress with an assigned bowler.
    """

    def __init__(
        self,
        team_size: int = DEFAULT_TEAM_SIZE,
        max_overs: int = DEFAULT_MAX_OVERS,
    ) -> None:
        if isinstance(max_overs, bool) or not isinstance(max_overs, int) or max_overs < 1:
            raise BowlingError(
                f"Invalid max_overs {max_overs!r}: max_overs must be an integer >= 1."
            )

        if isinstance(team_size, bool) or not isinstance(team_size, int) or team_size < max_overs:
            raise BowlingError(
                f"Invalid team_size {team_size!r}: team_size must be an integer >= max_overs ({max_overs}) "
                f"to satisfy the one-over-per-bowler quota rule."
            )

        self._team_size: int = team_size
        self._max_overs: int = max_overs

        self._completed_overs: int = 0
        self._active_bowler: Optional[int] = None
        self._used_bowlers: List[int] = []
        self._over_bowlers: Dict[int, int] = {}

    @property
    def team_size(self) -> int:
        """Total number of players on the bowling team."""
        return self._team_size

    @property
    def max_overs(self) -> int:
        """Maximum number of overs allowed in this innings."""
        return self._max_overs

    @property
    def current_over(self) -> int:
        """The 1-indexed over currently being assigned or bowled (1..max_overs)."""
        if self._completed_overs < self._max_overs:
            return self._completed_overs + 1
        return self._max_overs

    @property
    def completed_overs(self) -> int:
        """Number of fully completed overs."""
        return self._completed_overs

    @property
    def active_bowler(self) -> Optional[int]:
        """The bowler ID currently bowling the active over, or None if awaiting selection."""
        return self._active_bowler

    @property
    def current_bowler(self) -> Optional[int]:
        """Alias for active_bowler."""
        return self._active_bowler

    @property
    def used_bowlers(self) -> List[int]:
        """Defensive copy of bowler IDs that have been assigned/bowled in order."""
        return list(self._used_bowlers)

    @property
    def eligible_bowlers(self) -> List[int]:
        """Defensive copy of bowler IDs that remain eligible to bowl."""
        return [b for b in range(1, self._team_size + 1) if b not in self._used_bowlers]

    @property
    def over_bowlers(self) -> Dict[int, int]:
        """Defensive copy of mapping from over number to assigned bowler ID."""
        return dict(self._over_bowlers)

    @property
    def is_innings_bowling_complete(self) -> bool:
        """True if all overs have been completed."""
        return self._completed_overs == self._max_overs

    @property
    def is_over_active(self) -> bool:
        """True if an over is currently active with an assigned bowler."""
        return self._active_bowler is not None

    def _validate_bowler_id(self, bowler_id: int) -> int:
        """Validate that a bowler ID is an integer within team boundaries."""
        if isinstance(bowler_id, bool) or not isinstance(bowler_id, int):
            raise InvalidBowlerError(
                f"Invalid bowler ID {bowler_id!r}: bowler ID must be an integer, got {type(bowler_id).__name__}."
            )

        if bowler_id < 1 or bowler_id > self._team_size:
            raise InvalidBowlerError(
                f"Invalid bowler ID {bowler_id}: bowler ID must be between 1 and {self._team_size}."
            )

        return bowler_id

    def is_eligible(self, bowler_id: int) -> bool:
        """Check whether a specific bowler ID is eligible to bowl the next over."""
        if isinstance(bowler_id, bool) or not isinstance(bowler_id, int):
            return False
        if bowler_id < 1 or bowler_id > self._team_size:
            return False
        return bowler_id not in self._used_bowlers

    def has_bowled(self, bowler_id: int) -> bool:
        """Check whether a specific bowler ID has already bowled or is currently bowling."""
        valid_id = self._validate_bowler_id(bowler_id)
        return valid_id in self._used_bowlers

    def bowler_for_over(self, over_number: int) -> Optional[int]:
        """Retrieve the bowler assigned to a specific 1-indexed over number."""
        if isinstance(over_number, bool) or not isinstance(over_number, int):
            raise BowlingError(
                f"Invalid over_number {over_number!r}: over_number must be an integer, got {type(over_number).__name__}."
            )
        if over_number < 1 or over_number > self._max_overs:
            raise BowlingError(
                f"Invalid over_number {over_number}: over_number must be between 1 and {self._max_overs}."
            )
        return self._over_bowlers.get(over_number)

    def select_bowler(self, bowler_id: int) -> int:
        """Assign an eligible bowler to the current over.

        Lifecycle semantics:
        - A bowler becomes 'used' immediately upon selection, ensuring they cannot
          be re-selected in this innings even if the over terminates early (e.g. all-out).
        - The selected bowler remains the active_bowler until complete_over() is called.

        Args:
            bowler_id: Integer identifier of the bowler (1..team_size).

        Returns:
            The validated and assigned bowler ID.

        Raises:
            BowlingLifecycleError: If all overs are complete, or an over is already in progress.
            InvalidBowlerError: If bowler_id is invalid in type or range.
            BowlerAlreadyBowledError: If bowler_id has already been used in this innings.
        """
        if self.is_innings_bowling_complete:
            raise BowlingLifecycleError(
                f"Cannot select bowler: all {self._max_overs} overs have already been completed."
            )

        if self._active_bowler is not None:
            raise BowlingLifecycleError(
                f"Cannot select bowler: Over {self.current_over} is already in progress with bowler "
                f"{self._active_bowler}. Complete the current over before selecting the next bowler."
            )

        valid_id = self._validate_bowler_id(bowler_id)

        if valid_id in self._used_bowlers:
            raise BowlerAlreadyBowledError(
                f"Bowler {valid_id} has already bowled in this innings and cannot bowl again."
            )

        target_over = self.current_over
        self._active_bowler = valid_id
        self._used_bowlers.append(valid_id)
        self._over_bowlers[target_over] = valid_id

        return valid_id

    def complete_over(self) -> None:
        """Mark the active over as completed and advance innings progression.

        Raises:
            BowlingLifecycleError: If no over is currently in progress.
        """
        if self._active_bowler is None:
            raise BowlingLifecycleError(
                "Cannot complete over: no over is currently in progress."
            )

        self._active_bowler = None
        self._completed_overs += 1

    def as_view(self) -> "BowlingStateView":
        """Return a read-only query view of this bowling state."""
        return BowlingStateView(self)

    def __repr__(self) -> str:
        return (
            f"BowlingState(over={self.current_over}/{self._max_overs}, "
            f"completed={self._completed_overs}, active_bowler={self._active_bowler}, "
            f"used={self._used_bowlers}, eligible_count={len(self.eligible_bowlers)})"
        )


class BowlingStateView:
    """Read-only query view over a BowlingState instance.

    Exposes query properties and helper inspection methods while strictly omitting
    mutator methods (`select_bowler`, `complete_over`) to prevent state corruption.
    """

    def __init__(self, state: BowlingState) -> None:
        self._state = state

    @property
    def team_size(self) -> int:
        """Total number of players on the bowling team."""
        return self._state.team_size

    @property
    def max_overs(self) -> int:
        """Maximum number of overs allowed in this innings."""
        return self._state.max_overs

    @property
    def current_over(self) -> int:
        """The 1-indexed over currently being assigned or bowled."""
        return self._state.current_over

    @property
    def completed_overs(self) -> int:
        """Number of fully completed overs."""
        return self._state.completed_overs

    @property
    def active_bowler(self) -> Optional[int]:
        """The bowler ID currently bowling, or None."""
        return self._state.active_bowler

    @property
    def current_bowler(self) -> Optional[int]:
        """Alias for active_bowler."""
        return self._state.current_bowler

    @property
    def used_bowlers(self) -> List[int]:
        """Defensive copy of bowler IDs that have been assigned/bowled."""
        return self._state.used_bowlers

    @property
    def eligible_bowlers(self) -> List[int]:
        """Defensive copy of bowler IDs still eligible to bowl."""
        return self._state.eligible_bowlers

    @property
    def over_bowlers(self) -> Dict[int, int]:
        """Defensive copy of mapping from over number to assigned bowler ID."""
        return self._state.over_bowlers

    @property
    def is_innings_bowling_complete(self) -> bool:
        """True if all overs have been completed."""
        return self._state.is_innings_bowling_complete

    @property
    def is_over_active(self) -> bool:
        """True if an over is currently active with an assigned bowler."""
        return self._state.is_over_active

    def is_eligible(self, bowler_id: int) -> bool:
        """Check whether a specific bowler ID is eligible to bowl the next over."""
        return self._state.is_eligible(bowler_id)

    def has_bowled(self, bowler_id: int) -> bool:
        """Check whether a specific bowler ID has already bowled or is currently bowling."""
        return self._state.has_bowled(bowler_id)

    def bowler_for_over(self, over_number: int) -> Optional[int]:
        """Retrieve the bowler assigned to a specific 1-indexed over number."""
        return self._state.bowler_for_over(over_number)

    def __repr__(self) -> str:
        return (
            f"BowlingStateView(over={self.current_over}/{self.max_overs}, "
            f"completed={self.completed_overs}, active_bowler={self.active_bowler}, "
            f"used={self.used_bowlers})"
        )
