"""Toss mechanics domain engine for Hand Cricket.

This module models coin toss resolution, decision making (BAT / BOWL),
and first-innings role assignment.

Invariants:
- Exactly two participants: Participant.A and Participant.B.
- Toss produces a single winner via a pluggable random chooser.
- The toss winner makes the decision (BAT or BOWL).
- First innings roles (batting first, bowling first, first bowler selector)
  are deterministically derived from the toss outcome.
- TossResult is frozen and immutable.
"""

from dataclasses import dataclass
from enum import Enum
import random
from typing import Callable, Optional, Tuple, Union


class Participant(str, Enum):
    """Identifier for match participants / sides."""

    A = "A"
    B = "B"

    def other(self) -> "Participant":
        """Return the opposing participant."""
        return Participant.B if self == Participant.A else Participant.A


class TossDecision(str, Enum):
    """The decision made by the toss winner."""

    BAT = "BAT"
    BOWL = "BOWL"


class TossStatus(str, Enum):
    """Lifecycle states of the toss."""

    NOT_STARTED = "NOT_STARTED"
    AWAITING_DECISION = "AWAITING_DECISION"
    COMPLETED = "COMPLETED"


class TossError(ValueError):
    """Base domain exception for toss errors."""

    pass


class TossLifecycleError(TossError):
    """Raised on invalid lifecycle transitions in the toss."""

    pass


class InvalidTossDecisionError(TossError):
    """Raised on invalid toss decision values."""

    pass


class InvalidParticipantError(TossError):
    """Raised on unknown or invalid participant identifiers."""

    pass


@dataclass(frozen=True)
class TossResult:
    """Immutable outcome of a coin toss and the resulting first-innings sides.

    Attributes:
        winner: Participant who won the coin toss.
        decision: TossDecision (BAT or BOWL) chosen by the winner.
        batting_first: Participant batting in Innings 1.
        bowling_first: Participant bowling in Innings 1.
        first_bowler_selector: Participant responsible for selecting the first bowler.
    """

    winner: Participant
    decision: TossDecision
    batting_first: Participant
    bowling_first: Participant
    first_bowler_selector: Participant


def derive_first_innings(
    winner: Participant, decision: TossDecision
) -> Tuple[Participant, Participant, Participant]:
    """Derive (batting_first, bowling_first, first_bowler_selector) from toss outcome.

    Rules:
    - Winner chooses BAT:
        winner bats first, opponent bowls first, opponent chooses first bowler.
    - Winner chooses BOWL:
        opponent bats first, winner bowls first, winner chooses first bowler.

    Args:
        winner: The participant who won the toss.
        decision: The winner's decision (BAT or BOWL).

    Returns:
        Tuple of (batting_first, bowling_first, first_bowler_selector).
    """
    if not isinstance(winner, Participant):
        raise InvalidParticipantError(f"Invalid toss winner: {winner!r}.")
    if not isinstance(decision, TossDecision):
        raise InvalidTossDecisionError(f"Invalid toss decision: {decision!r}.")

    if decision == TossDecision.BAT:
        batting_first = winner
        bowling_first = winner.other()
    else:
        batting_first = winner.other()
        bowling_first = winner

    first_bowler_selector = bowling_first
    return batting_first, bowling_first, first_bowler_selector


TossChooser = Callable[[], Participant]


def default_toss_chooser() -> Participant:
    """Production default random chooser between Participant A and Participant B."""
    return random.choice([Participant.A, Participant.B])


class Toss:
    """Coordinates the coin toss and subsequent batting/bowling decision.

    Lifecycle:
        NOT_STARTED -> flip() -> AWAITING_DECISION -> choose() -> COMPLETED

    Invariants:
        - Random toss is performed once.
        - Only the toss winner can make the decision.
        - Decision can only be BAT or BOWL.
        - Decision cannot be made before the toss is flipped.
        - Decision cannot be modified once made.
        - Resulting TossResult is completely immutable.
        - Supports dependency injection of random chooser for deterministic testing.
    """

    def __init__(self, chooser: Optional[TossChooser] = None) -> None:
        self._chooser: TossChooser = (
            chooser if chooser is not None else default_toss_chooser
        )
        self._status: TossStatus = TossStatus.NOT_STARTED
        self._winner: Optional[Participant] = None
        self._decision: Optional[TossDecision] = None
        self._result: Optional[TossResult] = None

    @property
    def status(self) -> TossStatus:
        """Current lifecycle status of the toss."""
        return self._status

    @property
    def is_completed(self) -> bool:
        """True if the toss decision has been finalized."""
        return self._status == TossStatus.COMPLETED

    @property
    def winner(self) -> Optional[Participant]:
        """The winning participant, or None if toss has not been flipped."""
        return self._winner

    @property
    def decision(self) -> Optional[TossDecision]:
        """The decision made, or None if not decided yet."""
        return self._decision

    @property
    def result(self) -> Optional[TossResult]:
        """The finalized immutable TossResult, or None if not completed."""
        return self._result

    def flip(self) -> Participant:
        """Perform the coin toss.

        Returns:
            The winning Participant (A or B).

        Raises:
            TossLifecycleError: If toss has already been flipped.
            InvalidParticipantError: If chooser returns an invalid value.
        """
        if self._status != TossStatus.NOT_STARTED:
            raise TossLifecycleError(
                f"Cannot flip toss: toss is already in state {self._status.value}."
            )

        chosen = self._chooser()

        # Normalization in case chooser returns string or enum
        if isinstance(chosen, str):
            try:
                chosen = Participant(chosen.strip().upper())
            except ValueError:
                raise InvalidParticipantError(
                    f"Chooser returned invalid participant {chosen!r}."
                )
        elif not isinstance(chosen, Participant):
            raise InvalidParticipantError(
                f"Chooser returned invalid participant type {type(chosen).__name__}."
            )

        self._winner = chosen
        self._status = TossStatus.AWAITING_DECISION
        return self._winner

    def choose(
        self, decision: Union[TossDecision, str], by: Union[Participant, str]
    ) -> TossResult:
        """Record the toss winner's decision (BAT or BOWL).

        Args:
            decision: TossDecision.BAT or TossDecision.BOWL (or string "BAT" / "BOWL").
            by: The participant making the decision (must match the toss winner).

        Returns:
            The immutable TossResult.

        Raises:
            TossLifecycleError: If toss is not flipped or decision was already finalized.
            InvalidParticipantError: If `by` is not a valid participant or not the winner.
            InvalidTossDecisionError: If `decision` is not BAT or BOWL.
        """
        if self._status == TossStatus.NOT_STARTED:
            raise TossLifecycleError(
                "Cannot make toss decision: toss has not been flipped yet."
            )

        if self._status == TossStatus.COMPLETED:
            raise TossLifecycleError(
                "Cannot make toss decision: decision has already been finalized."
            )

        # Normalize by
        if isinstance(by, str):
            try:
                by = Participant(by.strip().upper())
            except ValueError:
                raise InvalidParticipantError(f"Invalid participant {by!r}.")
        elif not isinstance(by, Participant):
            raise InvalidParticipantError(
                f"Expected Participant, got {type(by).__name__}."
            )

        assert self._winner is not None
        if by != self._winner:
            raise InvalidParticipantError(
                f"Participant {by.value} cannot make toss decision: "
                f"toss was won by Participant {self._winner.value}."
            )

        # Normalize decision
        if isinstance(decision, str):
            try:
                decision = TossDecision(decision.strip().upper())
            except ValueError:
                raise InvalidTossDecisionError(
                    f"Invalid toss decision {decision!r}. Must be 'BAT' or 'BOWL'."
                )
        elif not isinstance(decision, TossDecision):
            raise InvalidTossDecisionError(
                f"Expected TossDecision, got {type(decision).__name__}."
            )

        batting_first, bowling_first, first_bowler_selector = derive_first_innings(
            self._winner, decision
        )

        self._decision = decision
        self._result = TossResult(
            winner=self._winner,
            decision=decision,
            batting_first=batting_first,
            bowling_first=bowling_first,
            first_bowler_selector=first_bowler_selector,
        )
        self._status = TossStatus.COMPLETED
        return self._result

    def __repr__(self) -> str:
        return (
            f"Toss(status={self._status.value}, "
            f"winner={self._winner.value if self._winner else None}, "
            f"decision={self._decision.value if self._decision else None})"
        )
