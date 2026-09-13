"""Automated tests for the Toss Mechanics domain engine (Slice 7)."""

from dataclasses import FrozenInstanceError
import pytest

from backend.app.engine.toss import (
    InvalidParticipantError,
    InvalidTossDecisionError,
    Participant,
    Toss,
    TossDecision,
    TossLifecycleError,
    TossResult,
    TossStatus,
    derive_first_innings,
)


# ===========================================================================
# 1. Participant Basics
# ===========================================================================


def test_participant_enum_values():
    """Participant enum has exactly A and B."""
    assert Participant.A.value == "A"
    assert Participant.B.value == "B"
    assert len(Participant) == 2


def test_participant_other():
    """Participant.other returns opposing participant."""
    assert Participant.A.other() == Participant.B
    assert Participant.B.other() == Participant.A


# ===========================================================================
# 2. First-Innings Derivation (Requirements 21 - 24)
# ===========================================================================


def test_derive_first_innings_a_wins_bat():
    """Requirement 21: A wins toss and chooses BAT -> A bats, B bowls, B chooses bowler."""
    batting, bowling, selector = derive_first_innings(Participant.A, TossDecision.BAT)
    assert batting == Participant.A
    assert bowling == Participant.B
    assert selector == Participant.B


def test_derive_first_innings_a_wins_bowl():
    """Requirement 22: A wins toss and chooses BOWL -> B bats, A bowls, A chooses bowler."""
    batting, bowling, selector = derive_first_innings(Participant.A, TossDecision.BOWL)
    assert batting == Participant.B
    assert bowling == Participant.A
    assert selector == Participant.A


def test_derive_first_innings_b_wins_bat():
    """Requirement 23: B wins toss and chooses BAT -> B bats, A bowls, A chooses bowler."""
    batting, bowling, selector = derive_first_innings(Participant.B, TossDecision.BAT)
    assert batting == Participant.B
    assert bowling == Participant.A
    assert selector == Participant.A


def test_derive_first_innings_b_wins_bowl():
    """Requirement 24: B wins toss and chooses BOWL -> A bats, B bowls, B chooses bowler."""
    batting, bowling, selector = derive_first_innings(Participant.B, TossDecision.BOWL)
    assert batting == Participant.A
    assert bowling == Participant.B
    assert selector == Participant.B


# ===========================================================================
# 3. Deterministic Toss with Injected Randomness (Requirements 14, 15, 16, 20)
# ===========================================================================


def test_toss_with_injected_chooser_participant_a():
    """Requirements 14, 15, 20: Injected chooser returning A makes A the winner."""
    toss = Toss(chooser=lambda: Participant.A)
    assert toss.status == TossStatus.NOT_STARTED
    assert toss.is_completed is False
    assert toss.winner is None

    winner = toss.flip()
    assert winner == Participant.A
    assert toss.winner == Participant.A
    assert toss.status == TossStatus.AWAITING_DECISION

    # Toss winner chooses BAT
    result = toss.choose(TossDecision.BAT, by=Participant.A)
    assert isinstance(result, TossResult)
    assert result.winner == Participant.A
    assert result.decision == TossDecision.BAT
    assert result.batting_first == Participant.A
    assert result.bowling_first == Participant.B
    assert result.first_bowler_selector == Participant.B
    assert toss.status == TossStatus.COMPLETED
    assert toss.is_completed is True


def test_toss_with_injected_chooser_participant_b():
    """Requirements 14, 16, 20: Injected chooser returning B makes B the winner."""
    toss = Toss(chooser=lambda: Participant.B)
    winner = toss.flip()
    assert winner == Participant.B

    # Winner B chooses BOWL
    result = toss.choose(TossDecision.BOWL, by=Participant.B)
    assert result.winner == Participant.B
    assert result.decision == TossDecision.BOWL
    assert result.batting_first == Participant.A
    assert result.bowling_first == Participant.B
    assert result.first_bowler_selector == Participant.B


def test_toss_accepts_string_inputs():
    """choose method accepts valid case-insensitive string values for decision and participant."""
    toss = Toss(chooser=lambda: Participant.A)
    toss.flip()

    result = toss.choose("bat", by="a")
    assert result.decision == TossDecision.BAT
    assert result.winner == Participant.A


# ===========================================================================
# 4. Production Randomness & Distribution (Requirement 29)
# ===========================================================================


def test_default_production_toss():
    """Requirement 29: Production default random toss generates valid Participant A or B."""
    observed = set()
    for _ in range(50):
        toss = Toss()
        winner = toss.flip()
        assert winner in (Participant.A, Participant.B)
        observed.add(winner)

    # In 50 coin flips, both A and B should be observed with overwhelming probability (1 - 2^-49)
    assert observed == {Participant.A, Participant.B}


# ===========================================================================
# 5. Invalid Lifecycle Transitions & Rejections (Requirements 17, 18, 19)
# ===========================================================================


def test_decision_cannot_be_made_before_toss():
    """Requirement 18: Calling choose before flip raises TossLifecycleError."""
    toss = Toss()
    assert toss.status == TossStatus.NOT_STARTED

    with pytest.raises(TossLifecycleError, match="toss has not been flipped yet"):
        toss.choose(TossDecision.BAT, by=Participant.A)


def test_cannot_flip_toss_twice():
    """Calling flip when already flipped raises TossLifecycleError."""
    toss = Toss(chooser=lambda: Participant.A)
    toss.flip()

    with pytest.raises(TossLifecycleError, match="already in state AWAITING_DECISION"):
        toss.flip()


def test_non_winner_cannot_make_toss_decision():
    """Requirement 17: Participant other than the toss winner cannot choose."""
    toss = Toss(chooser=lambda: Participant.A)
    toss.flip()

    with pytest.raises(InvalidParticipantError, match="toss was won by Participant A"):
        toss.choose(TossDecision.BAT, by=Participant.B)


def test_decision_cannot_be_changed_after_finalized():
    """Requirement 19: Calling choose after completion raises TossLifecycleError."""
    toss = Toss(chooser=lambda: Participant.A)
    toss.flip()
    toss.choose(TossDecision.BAT, by=Participant.A)

    assert toss.status == TossStatus.COMPLETED

    with pytest.raises(TossLifecycleError, match="decision has already been finalized"):
        toss.choose(TossDecision.BOWL, by=Participant.A)


@pytest.mark.parametrize("bad_decision", ["FIELD", "RUNS", "", "   ", None, 123, True])
def test_rejects_invalid_decision_values(bad_decision):
    """Invalid decision values raise InvalidTossDecisionError."""
    toss = Toss(chooser=lambda: Participant.A)
    toss.flip()

    with pytest.raises(InvalidTossDecisionError):
        toss.choose(bad_decision, by=Participant.A)  # type: ignore


@pytest.mark.parametrize("bad_by", ["C", "X", "", None, 1, True])
def test_rejects_invalid_participant_in_choose(bad_by):
    """Invalid participant identifiers raise InvalidParticipantError."""
    toss = Toss(chooser=lambda: Participant.A)
    toss.flip()

    with pytest.raises(InvalidParticipantError):
        toss.choose(TossDecision.BAT, by=bad_by)  # type: ignore


def test_rejects_invalid_chooser_return_value():
    """If a custom chooser returns an invalid value, flip raises InvalidParticipantError."""
    toss = Toss(chooser=lambda: "INVALID")  # type: ignore
    with pytest.raises(InvalidParticipantError):
        toss.flip()


# ===========================================================================
# 6. TossResult Immutability (Requirement 25)
# ===========================================================================


def test_toss_result_is_frozen():
    """Requirement 25: TossResult dataclass fields cannot be modified."""
    toss = Toss(chooser=lambda: Participant.A)
    toss.flip()
    result = toss.choose(TossDecision.BAT, by=Participant.A)

    with pytest.raises(FrozenInstanceError):
        result.decision = TossDecision.BOWL  # type: ignore

    with pytest.raises(FrozenInstanceError):
        result.winner = Participant.B  # type: ignore

    with pytest.raises(FrozenInstanceError):
        result.batting_first = Participant.B  # type: ignore
