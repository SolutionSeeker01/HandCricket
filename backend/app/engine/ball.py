"""Single ball resolution engine for Hand Cricket.

This module implements the pure domain logic for resolving an individual ball
in a Hand Cricket match. It has zero external dependencies and does not perform I/O.
"""

from dataclasses import dataclass

MIN_BALL_CHOICE: int = 1
MAX_BALL_CHOICE: int = 6


class InvalidBallChoiceError(ValueError):
    """Raised when a player's choice is not a valid integer between 1 and 6."""
    pass


@dataclass(frozen=True)
class BallResult:
    """Immutable representation of the outcome of a single ball.

    Attributes:
        batsman_choice: The integer chosen by the batsman (1-6).
        bowler_choice: The integer chosen by the bowler (1-6).
        runs: Number of runs scored on this ball (0 if wicket).
        is_wicket: True if the batsman was dismissed, False otherwise.
    """
    batsman_choice: int
    bowler_choice: int
    runs: int
    is_wicket: bool


def validate_choice(choice: int, role: str = "player") -> int:
    """Validate that a choice is strictly an integer between 1 and 6.

    Args:
        choice: The choice value to validate.
        role: Identifier for error messages ('batsman' or 'bowler').

    Returns:
        The validated integer choice.

    Raises:
        InvalidBallChoiceError: If choice is not an integer or outside [1, 6].
    """
    # Reject booleans explicitly, since in Python bool is a subclass of int
    if isinstance(choice, bool) or not isinstance(choice, int):
        raise InvalidBallChoiceError(
            f"Invalid {role} choice {choice!r}: choice must be an integer, got {type(choice).__name__}."
        )

    if choice < MIN_BALL_CHOICE or choice > MAX_BALL_CHOICE:
        raise InvalidBallChoiceError(
            f"Invalid {role} choice {choice}: choice must be between {MIN_BALL_CHOICE} and {MAX_BALL_CHOICE}."
        )

    return choice


def resolve_ball(batsman_choice: int, bowler_choice: int) -> BallResult:
    """Resolve a single ball between batsman and bowler.

    Core Hand Cricket Rules:
    - If batsman_choice == bowler_choice: Wicket (0 runs scored).
    - If batsman_choice != bowler_choice: Batsman scores runs equal to batsman_choice.

    Args:
        batsman_choice: An integer from 1 to 6 chosen by the batsman.
        bowler_choice: An integer from 1 to 6 chosen by the bowler.

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
