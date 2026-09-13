"""Automated tests for the Bowler Quota Enforcement domain engine (Slice 5)."""

import pytest

from backend.app.engine.bowling import (
    DEFAULT_MAX_OVERS,
    DEFAULT_TEAM_SIZE,
    BowlerAlreadyBowledError,
    BowlingError,
    BowlingLifecycleError,
    BowlingState,
    BowlingStateView,
    InvalidBowlerError,
)


# ---------------------------------------------------------------------------
# 1. Initial State Verification
# ---------------------------------------------------------------------------


def test_initial_bowling_state():
    """Verify clean initial state of a bowling innings."""
    state = BowlingState()

    assert state.team_size == DEFAULT_TEAM_SIZE
    assert state.max_overs == DEFAULT_MAX_OVERS
    assert state.current_over == 1
    assert state.completed_overs == 0
    assert state.active_bowler is None
    assert state.current_bowler is None
    assert state.is_over_active is False
    assert state.is_innings_bowling_complete is False

    assert state.used_bowlers == []
    assert state.eligible_bowlers == list(range(1, 12))
    assert state.over_bowlers == {}

    for bowler_id in range(1, 12):
        assert state.is_eligible(bowler_id) is True
        assert state.has_bowled(bowler_id) is False


# ---------------------------------------------------------------------------
# 2. Valid Bowler Selection & Over Assignment
# ---------------------------------------------------------------------------


def test_select_valid_bowler_assigns_to_current_over():
    """Selecting an eligible bowler assigns them as active and marks them used."""
    state = BowlingState()

    selected = state.select_bowler(5)

    assert selected == 5
    assert state.active_bowler == 5
    assert state.current_bowler == 5
    assert state.is_over_active is True
    assert state.current_over == 1
    assert state.completed_overs == 0

    # Invariants: bowler 5 is now in used_bowlers and removed from eligible_bowlers
    assert state.used_bowlers == [5]
    assert 5 not in state.eligible_bowlers
    assert len(state.eligible_bowlers) == 10
    assert state.is_eligible(5) is False
    assert state.has_bowled(5) is True

    # Over mapping reflects assignment
    assert state.over_bowlers == {1: 5}
    assert state.bowler_for_over(1) == 5
    assert state.bowler_for_over(2) is None


# ---------------------------------------------------------------------------
# 3. Duplicate Bowler Selection Rejection (Quota Enforcement)
# ---------------------------------------------------------------------------


def test_cannot_select_same_bowler_again_after_over_completes():
    """A bowler who bowled an over cannot bowl any subsequent over in the innings."""
    state = BowlingState()

    # Over 1 bowled by bowler 3
    state.select_bowler(3)
    state.complete_over()

    assert state.completed_overs == 1
    assert state.current_over == 2
    assert state.active_bowler is None

    # Attempting to select bowler 3 again for Over 2 must raise BowlerAlreadyBowledError
    with pytest.raises(BowlerAlreadyBowledError, match="Bowler 3 has already bowled"):
        state.select_bowler(3)

    # Invariants unchanged after rejected attempt
    assert state.active_bowler is None
    assert state.completed_overs == 1
    assert state.current_over == 2
    assert state.used_bowlers == [3]


# ---------------------------------------------------------------------------
# 4. Over Concurrency & Lifecycle Violations
# ---------------------------------------------------------------------------


def test_cannot_select_new_bowler_while_over_is_already_active():
    """Attempting to select a bowler while an over is already underway must fail."""
    state = BowlingState()
    state.select_bowler(4)

    with pytest.raises(BowlingLifecycleError, match="already in progress with bowler 4"):
        state.select_bowler(7)

    assert state.active_bowler == 4
    assert state.used_bowlers == [4]
    assert 7 in state.eligible_bowlers


def test_cannot_complete_over_when_no_over_is_in_progress():
    """Calling complete_over without an active bowler must raise BowlingLifecycleError."""
    state = BowlingState()
    assert state.active_bowler is None

    with pytest.raises(BowlingLifecycleError, match="no over is currently in progress"):
        state.complete_over()


def test_over_completion_advances_over_and_clears_active_bowler():
    """Completing an over clears active bowler and advances over counters."""
    state = BowlingState()
    state.select_bowler(2)
    assert state.is_over_active is True

    state.complete_over()

    assert state.active_bowler is None
    assert state.is_over_active is False
    assert state.completed_overs == 1
    assert state.current_over == 2
    assert state.used_bowlers == [2]


# ---------------------------------------------------------------------------
# 5. Full Five-Over Sequence (Five Distinct Bowlers)
# ---------------------------------------------------------------------------


def test_full_five_over_legal_sequence():
    """Verify complete innings with 5 overs bowled by 5 unique bowlers."""
    state = BowlingState()
    bowler_sequence = [5, 2, 8, 1, 11]

    for over_idx, bowler_id in enumerate(bowler_sequence, start=1):
        assert state.current_over == over_idx
        assert state.completed_overs == over_idx - 1
        assert state.is_innings_bowling_complete is False

        # Select bowler for this over
        assert state.is_eligible(bowler_id) is True
        state.select_bowler(bowler_id)

        assert state.active_bowler == bowler_id
        assert state.bowler_for_over(over_idx) == bowler_id
        assert state.has_bowled(bowler_id) is True
        assert state.is_eligible(bowler_id) is False

        # Complete this over
        state.complete_over()
        assert state.completed_overs == over_idx

    # After Over 5 completes:
    assert state.completed_overs == 5
    assert state.current_over == 5  # stays at 5, does not advance to 6
    assert state.active_bowler is None
    assert state.is_innings_bowling_complete is True

    # Quota verification: exactly 5 unique bowlers used
    assert state.used_bowlers == bowler_sequence
    assert len(set(state.used_bowlers)) == 5
    assert len(state.eligible_bowlers) == 6  # 11 - 5 = 6 unused
    assert state.over_bowlers == {1: 5, 2: 2, 3: 8, 4: 1, 5: 11}

    # Attempting to select a 6th bowler must be rejected
    with pytest.raises(BowlingLifecycleError, match="all 5 overs have already been completed"):
        state.select_bowler(4)


# ---------------------------------------------------------------------------
# 6. Input Validation & Type Safety
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("invalid_id", [0, -1, -99, 12, 13, 100])
def test_rejects_out_of_range_bowler_ids(invalid_id: int):
    """Bowler IDs below 1 or above team_size must raise InvalidBowlerError."""
    state = BowlingState()
    with pytest.raises(InvalidBowlerError, match="must be between 1 and 11"):
        state.select_bowler(invalid_id)

    with pytest.raises(InvalidBowlerError, match="must be between 1 and 11"):
        state.has_bowled(invalid_id)

    assert state.is_eligible(invalid_id) is False


@pytest.mark.parametrize(
    "invalid_type",
    [
        True,          # bool subclass of int
        False,         # bool subclass of int
        None,
        "5",
        5.0,
        [1],
        {"id": 1},
    ],
)
def test_rejects_non_integer_bowler_types(invalid_type):
    """Non-integer types and booleans must raise InvalidBowlerError."""
    state = BowlingState()
    with pytest.raises(InvalidBowlerError, match="must be an integer"):
        state.select_bowler(invalid_type)

    with pytest.raises(InvalidBowlerError, match="must be an integer"):
        state.has_bowled(invalid_type)

    assert state.is_eligible(invalid_type) is False


@pytest.mark.parametrize("invalid_over", [0, -1, 6, 7, True, False, "1", 1.0])
def test_bowler_for_over_rejects_invalid_over_numbers(invalid_over):
    """Querying bowler_for_over with out-of-bounds over numbers must raise BowlingError."""
    state = BowlingState()
    with pytest.raises(BowlingError):
        state.bowler_for_over(invalid_over)


# ---------------------------------------------------------------------------
# 7. Constructor Configuration Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("invalid_overs", [0, -1, -5, True, False, "5", 5.0])
def test_rejects_invalid_max_overs(invalid_overs):
    """Invalid max_overs must raise BowlingError."""
    with pytest.raises(BowlingError):
        BowlingState(max_overs=invalid_overs)


@pytest.mark.parametrize(
    "team_size,max_overs",
    [
        (4, 5),   # team_size < max_overs cannot satisfy 1-over-per-bowler quota
        (2, 3),   # team_size < max_overs
        (0, 1),   # 0 players
        (-1, 5),  # negative
        (True, 5),# boolean
        (11, True),
    ],
)
def test_rejects_insufficient_or_invalid_team_size(team_size, max_overs):
    """Team size smaller than max_overs violates quota feasibility and must raise BowlingError."""
    with pytest.raises(BowlingError):
        BowlingState(team_size=team_size, max_overs=max_overs)


def test_custom_valid_configuration():
    """BowlingState accepts valid custom configuration (e.g. 6 players, 3 overs)."""
    state = BowlingState(team_size=6, max_overs=3)
    assert state.team_size == 6
    assert state.max_overs == 3
    assert len(state.eligible_bowlers) == 6

    state.select_bowler(6)
    state.complete_over()
    state.select_bowler(5)
    state.complete_over()
    state.select_bowler(4)
    state.complete_over()

    assert state.completed_overs == 3
    assert state.is_innings_bowling_complete is True


# ---------------------------------------------------------------------------
# 8. State Protection & Defensive Copies
# ---------------------------------------------------------------------------


def test_returned_properties_are_defensive_copies():
    """Mutating returned collections must not corrupt internal BowlingState."""
    state = BowlingState()
    state.select_bowler(1)

    used = state.used_bowlers
    used.append(99)
    assert 99 not in state.used_bowlers

    eligible = state.eligible_bowlers
    eligible.clear()
    assert len(state.eligible_bowlers) == 10

    overs = state.over_bowlers
    overs[1] = 999
    assert state.over_bowlers[1] == 1


def test_bowling_state_view_read_only_protection():
    """BowlingStateView exposes query properties but omits mutators."""
    state = BowlingState()
    state.select_bowler(4)
    view = state.as_view()

    assert isinstance(view, BowlingStateView)
    assert view.team_size == 11
    assert view.max_overs == 5
    assert view.current_over == 1
    assert view.completed_overs == 0
    assert view.active_bowler == 4
    assert view.current_bowler == 4
    assert view.used_bowlers == [4]
    assert view.is_over_active is True
    assert view.is_innings_bowling_complete is False
    assert view.is_eligible(4) is False
    assert view.is_eligible(1) is True
    assert view.has_bowled(4) is True
    assert view.bowler_for_over(1) == 4

    # View has NO select_bowler, complete_over, or end_innings methods
    assert not hasattr(view, "select_bowler")
    assert not hasattr(view, "complete_over")
    assert not hasattr(view, "end_innings")

    with pytest.raises(AttributeError):
        view.select_bowler(2)  # type: ignore

    with pytest.raises(AttributeError):
        view.complete_over()  # type: ignore

    with pytest.raises(AttributeError):
        view.end_innings()  # type: ignore


# ---------------------------------------------------------------------------
# 9. State Isolation
# ---------------------------------------------------------------------------


def test_independent_bowling_state_instances():
    """Two BowlingState instances maintain completely isolated states."""
    state1 = BowlingState()
    state2 = BowlingState()

    state1.select_bowler(2)
    state1.complete_over()

    assert state1.completed_overs == 1
    assert state1.used_bowlers == [2]

    assert state2.completed_overs == 0
    assert state2.used_bowlers == []
    assert state2.is_eligible(2) is True


def test_repr_representation():
    """Verify clean string representations for debugging."""
    state = BowlingState()
    state.select_bowler(3)
    repr_str = repr(state)
    assert "over=1/5" in repr_str
    assert "active_bowler=3" in repr_str
    assert "used=[3]" in repr_str

    view_repr = repr(state.as_view())
    assert "BowlingStateView" in view_repr
    assert "active_bowler=3" in view_repr


# ---------------------------------------------------------------------------
# 10. Premature / Terminal Innings Deactivation (end_innings)
# ---------------------------------------------------------------------------


def test_end_innings_clears_active_bowler_without_incrementing_completed_overs():
    """Calling end_innings deactivates the bowler without counting a partial over."""
    state = BowlingState()
    state.select_bowler(4)

    assert state.is_over_active is True
    assert state.active_bowler == 4
    assert state.completed_overs == 0

    state.end_innings()

    assert state.active_bowler is None
    assert state.current_bowler is None
    assert state.is_over_active is False
    assert state.completed_overs == 0  # Partial over is NOT completed
    assert state.has_bowled(4) is True  # Bowler remains used
    assert state.is_eligible(4) is False


def test_end_innings_when_no_active_over_is_safe_noop():
    """Calling end_innings when no over is active is a safe, idempotent operation."""
    state = BowlingState()
    state.end_innings()

    assert state.active_bowler is None
    assert state.is_over_active is False
    assert state.completed_overs == 0


def test_cannot_select_bowler_after_end_innings():
    """Selecting a bowler after end_innings raises BowlingLifecycleError."""
    state = BowlingState()
    state.select_bowler(1)
    state.end_innings()

    with pytest.raises(BowlingLifecycleError, match="bowling innings has already ended"):
        state.select_bowler(2)
