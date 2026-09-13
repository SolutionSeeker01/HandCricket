"""Game turn model for Hand Cricket WebSocket protocol (Slice 10).

This module manages the state and resolution of a single two-participant ball turn.
It enforces single-submission, hidden choice tracking, timeout fallback via ComputerPlayer,
and delegates ball outcome resolution directly to ball.py's resolve_ball.
"""

from enum import Enum
from typing import Optional

from backend.app.engine.ball import (
    BallResult,
    InvalidBallChoiceError,
    resolve_ball,
    validate_choice,
)
from backend.app.engine.computer import ComputerPlayer
from backend.app.engine.toss import Participant
from backend.app.protocol.messages import TurnProtocolError


class TurnStatus(str, Enum):
    """Lifecycle states of a single ball turn."""

    WAITING = "WAITING"
    ONE_SUBMITTED = "ONE_SUBMITTED"
    COMPLETED = "COMPLETED"


class Turn:
    """Manages the state and simultaneous resolution of one ball turn.

    Invariants:
        - Exactly two participants: Participant.A and Participant.B.
        - Each participant may submit at most once per turn.
        - Choices must be valid integers in [1, 6].
        - Choices remain hidden until both choices exist and resolution completes.
        - Resolution occurs exactly once.
        - Timeout generates random fallback choices for unsubmitted participants only.
    """

    def __init__(self, batting_participant: Participant = Participant.A) -> None:
        if not isinstance(batting_participant, Participant):
            raise TypeError(
                f"batting_participant must be Participant, got {type(batting_participant).__name__}."
            )

        self._batting_participant: Participant = batting_participant
        self._bowling_participant: Participant = batting_participant.other()

        self._status: TurnStatus = TurnStatus.WAITING
        self._choice_a: Optional[int] = None
        self._choice_b: Optional[int] = None
        self._a_timed_out: bool = False
        self._b_timed_out: bool = False
        self._ball_result: Optional[BallResult] = None

    @property
    def status(self) -> TurnStatus:
        """Current status of the turn."""
        return self._status

    @property
    def is_completed(self) -> bool:
        """True if the turn has resolved and ball result is available."""
        return self._status == TurnStatus.COMPLETED

    @property
    def batting_participant(self) -> Participant:
        """Participant currently on strike (batting)."""
        return self._batting_participant

    @property
    def bowling_participant(self) -> Participant:
        """Participant currently bowling."""
        return self._bowling_participant

    @property
    def choice_a(self) -> Optional[int]:
        """Internal choice for Participant A."""
        return self._choice_a

    @property
    def choice_b(self) -> Optional[int]:
        """Internal choice for Participant B."""
        return self._choice_b

    @property
    def a_submitted(self) -> bool:
        """True if Participant A submitted a choice."""
        return self._choice_a is not None and not self._a_timed_out

    @property
    def b_submitted(self) -> bool:
        """True if Participant B submitted a choice."""
        return self._choice_b is not None and not self._b_timed_out

    @property
    def a_timed_out(self) -> bool:
        """True if Participant A's choice was server-generated via timeout."""
        return self._a_timed_out

    @property
    def b_timed_out(self) -> bool:
        """True if Participant B's choice was server-generated via timeout."""
        return self._b_timed_out

    @property
    def ball_result(self) -> Optional[BallResult]:
        """The authoritative BallResult once resolved, or None."""
        return self._ball_result

    def has_choice(self, participant: Participant) -> bool:
        """Check if a participant already has a recorded choice (submitted or fallback)."""
        if participant == Participant.A:
            return self._choice_a is not None
        return self._choice_b is not None

    def submit_choice(self, participant: Participant, number: int) -> bool:
        """Submit a 1-6 number choice for a participant.

        Args:
            participant: Participant.A or Participant.B.
            number: Integer between 1 and 6.

        Returns:
            True if this submission completed the turn, False otherwise.

        Raises:
            TurnProtocolError: If turn is already completed, duplicate submission,
                or number is invalid.
        """
        if self._status == TurnStatus.COMPLETED:
            raise TurnProtocolError("turn_completed", "Cannot submit: turn is already completed.")

        if not isinstance(participant, Participant):
            raise TurnProtocolError(
                "invalid_participant", f"Invalid participant: {participant!r}."
            )

        if self.has_choice(participant):
            raise TurnProtocolError(
                "duplicate_submission",
                f"Participant {participant.value} has already submitted a choice for this turn.",
            )

        # Validate number choice using existing ball.py validation rules
        try:
            valid_number = validate_choice(number, role=f"participant_{participant.value}")
        except InvalidBallChoiceError as e:
            raise TurnProtocolError("invalid_number", str(e))

        if participant == Participant.A:
            self._choice_a = valid_number
        else:
            self._choice_b = valid_number

        if self._choice_a is not None and self._choice_b is not None:
            self.resolve()
            return True

        self._status = TurnStatus.ONE_SUBMITTED
        return False

    def handle_timeout(
        self,
        computer_a: Optional[ComputerPlayer] = None,
        computer_b: Optional[ComputerPlayer] = None,
    ) -> BallResult:
        """Resolve missing participant choices via server-generated fallback.

        If a participant has already submitted, their choice is preserved.
        Only missing participants receive a random 1-6 choice.

        Args:
            computer_a: Optional ComputerPlayer for generating A's fallback choice.
            computer_b: Optional ComputerPlayer for generating B's fallback choice.

        Returns:
            The resolved BallResult.
        """
        if self._status == TurnStatus.COMPLETED:
            assert self._ball_result is not None
            return self._ball_result

        if self._choice_a is None:
            bot_a = computer_a if computer_a is not None else ComputerPlayer()
            self._choice_a = bot_a.choose_number()
            self._a_timed_out = True

        if self._choice_b is None:
            bot_b = computer_b if computer_b is not None else ComputerPlayer()
            self._choice_b = bot_b.choose_number()
            self._b_timed_out = True

        return self.resolve()

    def resolve(self) -> BallResult:
        """Resolve the ball outcome between Participant A and B.

        Uses existing resolve_ball() domain logic based on assigned batting/bowling roles.

        Returns:
            The authoritative BallResult.

        Raises:
            TurnProtocolError: If called before both choices are set.
        """
        if self._ball_result is not None:
            return self._ball_result

        if self._choice_a is None or self._choice_b is None:
            raise TurnProtocolError(
                "incomplete_turn", "Cannot resolve: both participants must have choices."
            )

        if self._batting_participant == Participant.A:
            batsman_choice = self._choice_a
            bowler_choice = self._choice_b
        else:
            batsman_choice = self._choice_b
            bowler_choice = self._choice_a

        result = resolve_ball(batsman_choice=batsman_choice, bowler_choice=bowler_choice)
        self._ball_result = result
        self._status = TurnStatus.COMPLETED
        return result

    def as_view(self) -> "TurnView":
        """Return a read-only inspecting view over this Turn."""
        return TurnView(self)

    def __repr__(self) -> str:
        return (
            f"Turn(status={self._status.value}, "
            f"batting={self._batting_participant.value}, "
            f"a_choice={self._choice_a if self.is_completed else ('set' if self._choice_a else None)}, "
            f"b_choice={self._choice_b if self.is_completed else ('set' if self._choice_b else None)})"
        )


class TurnView:
    """Read-only query view over a Turn instance.

    Guarantees encapsulation by exposing inspection properties while strictly
    omitting state-mutating methods (submit_choice, handle_timeout, resolve).
    The underlying mutable Turn is encapsulated via private name-mangled storage.
    """

    def __init__(self, turn: Turn) -> None:
        self.__turn: Turn = turn

    @property
    def status(self) -> TurnStatus:
        return self.__turn.status

    @property
    def is_completed(self) -> bool:
        return self.__turn.is_completed

    @property
    def batting_participant(self) -> Participant:
        return self.__turn.batting_participant

    @property
    def bowling_participant(self) -> Participant:
        return self.__turn.bowling_participant

    @property
    def choice_a(self) -> Optional[int]:
        return self.__turn.choice_a

    @property
    def choice_b(self) -> Optional[int]:
        return self.__turn.choice_b

    @property
    def a_submitted(self) -> bool:
        return self.__turn.a_submitted

    @property
    def b_submitted(self) -> bool:
        return self.__turn.b_submitted

    @property
    def a_timed_out(self) -> bool:
        return self.__turn.a_timed_out

    @property
    def b_timed_out(self) -> bool:
        return self.__turn.b_timed_out

    @property
    def ball_result(self) -> Optional[BallResult]:
        return self.__turn.ball_result

    def has_choice(self, participant: Participant) -> bool:
        return self.__turn.has_choice(participant)

    def __repr__(self) -> str:
        return f"TurnView({self.__turn!r})"
