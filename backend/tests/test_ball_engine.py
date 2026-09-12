"""Automated tests for the single ball resolution engine."""

from dataclasses import FrozenInstanceError
import pytest

from backend.app.engine.ball import (
    BallResult,
    InvalidBallChoiceError,
    resolve_ball,
    validate_choice,
)


# ---------------------------------------------------------------------------
# 1. Comprehensive Matrix Test (All 36 Combinations)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bat", range(1, 7))
@pytest.mark.parametrize("bowl", range(1, 7))
def test_all_36_ball_combinations(bat: int, bowl: int):
    """Verify all 36 valid choice combinations (1..6 vs 1..6).

    - If bat == bowl: must be a wicket with 0 runs.
    - If bat != bowl: must not be a wicket with runs equal to bat.
    """
    result = resolve_ball(bat, bowl)

    assert result.batsman_choice == bat
    assert result.bowler_choice == bowl

    if bat == bowl:
        assert result.is_wicket is True
        assert result.runs == 0
    else:
        assert result.is_wicket is False
        assert result.runs == bat


# ---------------------------------------------------------------------------
# 2. Canonical Specification Examples
# ---------------------------------------------------------------------------


def test_runs_unequal_choices():
    """Verify specific examples of unequal choices resulting in runs."""
    # 1 vs 2 -> 1 run
    res1 = resolve_ball(1, 2)
    assert res1.runs == 1
    assert res1.is_wicket is False

    # 4 vs 2 -> 4 runs
    res2 = resolve_ball(4, 2)
    assert res2.runs == 4
    assert res2.is_wicket is False

    # 6 vs 1 -> 6 runs
    res3 = resolve_ball(6, 1)
    assert res3.runs == 6
    assert res3.is_wicket is False


def test_wickets_equal_choices():
    """Verify specific examples of matching choices resulting in a wicket."""
    # 5 vs 5 -> wicket
    res1 = resolve_ball(5, 5)
    assert res1.runs == 0
    assert res1.is_wicket is True

    # 3 vs 3 -> wicket
    res2 = resolve_ball(3, 3)
    assert res2.runs == 0
    assert res2.is_wicket is True

    # 1 vs 1 -> wicket
    res3 = resolve_ball(1, 1)
    assert res3.runs == 0
    assert res3.is_wicket is True

    # 6 vs 6 -> wicket
    res4 = resolve_ball(6, 6)
    assert res4.runs == 0
    assert res4.is_wicket is True


# ---------------------------------------------------------------------------
# 3. Input Validation & Boundary Testing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("invalid_val", [0, -1, -99, 7, 8, 100])
def test_rejects_out_of_range_values(invalid_val: int):
    """Values below 1 or above 6 must raise InvalidBallChoiceError."""
    with pytest.raises(InvalidBallChoiceError, match="choice must be between 1 and 6"):
        resolve_ball(invalid_val, 3)

    with pytest.raises(InvalidBallChoiceError, match="choice must be between 1 and 6"):
        resolve_ball(3, invalid_val)


@pytest.mark.parametrize(
    "invalid_type",
    [
        "4",         # string
        4.0,         # float
        3.5,         # float
        None,        # NoneType
        True,        # bool (must not pass as 1)
        False,       # bool (must not pass as 0)
        [1],         # list
        {"choice": 1},  # dict
    ],
)
def test_rejects_non_integer_types(invalid_type):
    """Non-integer types must raise InvalidBallChoiceError."""
    with pytest.raises(InvalidBallChoiceError, match="choice must be an integer"):
        resolve_ball(invalid_type, 3)

    with pytest.raises(InvalidBallChoiceError, match="choice must be an integer"):
        resolve_ball(3, invalid_type)


def test_validation_error_identifies_role():
    """Error message should identify whether the invalid choice came from batsman or bowler."""
    with pytest.raises(InvalidBallChoiceError, match="Invalid batsman choice"):
        validate_choice(0, role="batsman")

    with pytest.raises(InvalidBallChoiceError, match="Invalid bowler choice"):
        validate_choice(7, role="bowler")


# ---------------------------------------------------------------------------
# 4. Determinism & Immutability
# ---------------------------------------------------------------------------


def test_determinism():
    """Repeated calls with identical inputs must produce identical outputs."""
    res_a = resolve_ball(4, 2)
    res_b = resolve_ball(4, 2)
    assert res_a == res_b

    res_w1 = resolve_ball(5, 5)
    res_w2 = resolve_ball(5, 5)
    assert res_w1 == res_w2


def test_ball_result_immutability():
    """BallResult must be immutable (frozen dataclass)."""
    result = resolve_ball(4, 2)
    with pytest.raises(FrozenInstanceError):
        result.runs = 6  # type: ignore
