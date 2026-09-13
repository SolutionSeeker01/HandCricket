"""Headless Computer Player domain engine for Hand Cricket.

This module provides a headless ComputerPlayer abstraction responsible for
generating legal ball choices (1–6). In V1, the computer player is intentionally
minimal and un-opinionated: it produces a random integer between 1 and 6 for each turn.

Randomness is injectable to allow fully deterministic testing.
Validation of generated choices delegates directly to the ball engine to ensure
a single source of truth for legal ball choices.
"""

import random
from typing import Callable, Optional

from backend.app.engine.ball import (
    MAX_BALL_CHOICE,
    MIN_BALL_CHOICE,
    InvalidBallChoiceError,
    validate_choice,
)

NumberChooser = Callable[[], int]


def default_number_chooser() -> int:
    """Production default random chooser generating an integer in [1, 6]."""
    return random.randint(MIN_BALL_CHOICE, MAX_BALL_CHOICE)


class ComputerPlayer:
    """Headless Computer Player for Hand Cricket.

    Generates legal 1–6 number choices for batting or bowling turns.

    Invariants:
        - Returned choices are strictly integers in [1, 6].
        - Reuses ball.py's validate_choice() as the single source of truth.
        - Supports dependency injection of the chooser callable for deterministic testing.
        - Encapsulates no mutable match/game state.
    """

    def __init__(self, chooser: Optional[NumberChooser] = None) -> None:
        if chooser is not None and not callable(chooser):
            raise TypeError(
                f"Expected callable for chooser, got {type(chooser).__name__}."
            )
        self._chooser: NumberChooser = (
            chooser if chooser is not None else default_number_chooser
        )

    def choose_number(self) -> int:
        """Generate and validate a ball choice.

        Returns:
            An integer between 1 and 6.

        Raises:
            InvalidBallChoiceError: If the underlying chooser produces an invalid choice
                (out of bounds, non-integer, bool, etc.).
        """
        raw_choice = self._chooser()
        return validate_choice(raw_choice, role="computer")

    def __repr__(self) -> str:
        chooser_name = (
            self._chooser.__name__
            if hasattr(self._chooser, "__name__")
            else repr(self._chooser)
        )
        return f"ComputerPlayer(chooser={chooser_name})"
