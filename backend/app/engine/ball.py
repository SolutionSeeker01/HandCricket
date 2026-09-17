"""Single ball resolution engine for Hand Cricket.

This module implements the pure domain logic for resolving an individual ball
in a Hand Cricket match. It has zero external dependencies and does not perform I/O.
"""

from dataclasses import dataclass
from typing import Tuple

VALID_BALL_CHOICES: Tuple[int, ...] = (1, 2, 3, 4, 6)
MIN_BALL_CHOICE: int = 1
MAX_BALL_CHOICE: int = 6


class InvalidBallChoiceError(ValueError):
    """Raised when a player's choice is not a valid integer in (1, 2, 3, 4, 6)."""
    pass


def validate_choice(choice: int, role: str = "player") -> int:
    """Validate that a choice is strictly an integer in (1, 2, 3, 4, 6).

    Args:
        choice: The choice value to validate.
        role: Identifier for error messages ('batsman' or 'bowler').

    Returns:
        The validated integer choice.

    Raises:
        InvalidBallChoiceError: If choice is not an integer or not in VALID_BALL_CHOICES.
    """
    # Reject booleans explicitly, since in Python bool is a subclass of int
    if isinstance(choice, bool) or not isinstance(choice, int):
        raise InvalidBallChoiceError(
            f"Invalid {role} choice {choice!r}: choice must be an integer, got {type(choice).__name__}."
        )

    if choice not in VALID_BALL_CHOICES:
        raise InvalidBallChoiceError(
            f"Invalid {role} choice {choice}: choice must be one of {list(VALID_BALL_CHOICES)}."
        )

    return choice


@dataclass(frozen=True)
class BallResult:
    """Immutable representation of the outcome of a single ball.

    Invariants:
        - batsman_choice and bowler_choice must be integers in (1, 2, 3, 4, 6).
        - If batsman_choice == bowler_choice:
            is_wicket must be True, runs must be 0.
        - If batsman_choice != bowler_choice:
            is_wicket must be False, runs must equal batsman_choice.

    Attributes:
        batsman_choice: The integer chosen by the batsman (1, 2, 3, 4, 6).
        bowler_choice: The integer chosen by the bowler (1, 2, 3, 4, 6).
        runs: Number of runs scored on this ball (0 if wicket).
        is_wicket: True if the batsman was dismissed, False otherwise.
    """
    batsman_choice: int
    bowler_choice: int
    runs: int
    is_wicket: bool

    def __post_init__(self) -> None:
        """Enforce domain invariants upon construction."""
        validate_choice(self.batsman_choice, "batsman")
        validate_choice(self.bowler_choice, "bowler")

        if isinstance(self.runs, bool) or not isinstance(self.runs, int):
            raise InvalidBallChoiceError(
                f"Invalid runs {self.runs!r}: runs must be an integer, got {type(self.runs).__name__}."
            )

        if not isinstance(self.is_wicket, bool):
            raise InvalidBallChoiceError(
                f"Invalid is_wicket {self.is_wicket!r}: is_wicket must be a boolean, got {type(self.is_wicket).__name__}."
            )

        if self.batsman_choice == self.bowler_choice:
            if not self.is_wicket or self.runs != 0:
                raise InvalidBallChoiceError(
                    f"Inconsistent BallResult: identical choices ({self.batsman_choice} vs {self.bowler_choice}) "
                    f"must produce a wicket (is_wicket=True, runs=0), got is_wicket={self.is_wicket}, runs={self.runs}."
                )
        else:
            if self.is_wicket or self.runs != self.batsman_choice:
                raise InvalidBallChoiceError(
                    f"Inconsistent BallResult: unequal choices ({self.batsman_choice} vs {self.bowler_choice}) "
                    f"must produce runs equal to batsman choice with is_wicket=False "
                    f"(is_wicket=False, runs={self.batsman_choice}), got is_wicket={self.is_wicket}, runs={self.runs}."
                )


def resolve_ball(batsman_choice: int, bowler_choice: int) -> BallResult:
    """Resolve a single ball between batsman and bowler.

    Core Hand Cricket Rules:
    - If batsman_choice == bowler_choice: Wicket (0 runs scored).
    - If batsman_choice != bowler_choice: Batsman scores runs equal to batsman_choice.

    Args:
        batsman_choice: An integer from (1, 2, 3, 4, 6) chosen by the batsman.
        bowler_choice: An integer from (1, 2, 3, 4, 6) chosen by the bowler.

    Returns:
        BallResult containing the ball resolution details.

    Raises:
        InvalidBallChoiceError: If either choice is invalid.
    """
    valid_bat = validate_choice(batsman_choice, "batsman")
    valid_bowl = validate_choice(bowler_choice, "bowler")

    if valid_bat == valid_bowl:
        return BallResult(
            batsman_choice=valid_bat,
            bowler_choice=valid_bowl,
            runs=0,
            is_wicket=True,
        )

    return BallResult(
        batsman_choice=valid_bat,
        bowler_choice=valid_bowl,
        runs=valid_bat,
        is_wicket=False,
    )
