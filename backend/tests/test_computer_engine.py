"""Automated tests for the Headless Computer Player domain engine (Slice 8)."""

import pytest

from backend.app.engine.ball import (
    VALID_BALL_CHOICES,
    InvalidBallChoiceError,
    resolve_ball,
)
from backend.app.engine.computer import (
    ComputerPlayer,
    default_number_chooser,
)


# ===========================================================================
# 1. Deterministic Chooser Injection (Testing Behavior)
# ===========================================================================


def test_deterministic_injected_minimum_value():
    """ComputerPlayer returns exact injected value 1."""
    bot = ComputerPlayer(chooser=lambda: 1)
    assert bot.choose_number() == 1


def test_deterministic_injected_maximum_value():
    """ComputerPlayer returns exact injected value 6."""
    bot = ComputerPlayer(chooser=lambda: 6)
    assert bot.choose_number() == 6


@pytest.mark.parametrize("expected_val", VALID_BALL_CHOICES)
def test_deterministic_injected_all_valid_values(expected_val):
    """ComputerPlayer returns each valid choice 1, 2, 3, 4, 6 when injected."""
    bot = ComputerPlayer(chooser=lambda: expected_val)
    assert bot.choose_number() == expected_val


def test_sequential_injected_values():
    """ComputerPlayer correctly yields a sequence of pre-determined choices."""
    sequence = iter([3, 1, 4, 6, 2, 4])
    bot = ComputerPlayer(chooser=lambda: next(sequence))

    assert bot.choose_number() == 3
    assert bot.choose_number() == 1
    assert bot.choose_number() == 4
    assert bot.choose_number() == 6
    assert bot.choose_number() == 2
    assert bot.choose_number() == 4


def test_repeated_calls_work_independently():
    """Multiple calls to choose_number() execute the chooser independently each time."""
    call_count = 0
    choices = [2, 3, 4]

    def counting_chooser() -> int:
        nonlocal call_count
        val = choices[call_count % len(choices)]
        call_count += 1
        return val

    bot = ComputerPlayer(chooser=counting_chooser)
    assert bot.choose_number() == 2
    assert bot.choose_number() == 3
    assert bot.choose_number() == 4
    assert call_count == 3


# ===========================================================================
# 2. Production Randomness Behavior (Default Chooser)
# ===========================================================================


def test_default_number_chooser_produces_legal_value():
    """default_number_chooser() returns an integer in (1, 2, 3, 4, 6)."""
    val = default_number_chooser()
    assert isinstance(val, int)
    assert not isinstance(val, bool)
    assert val in VALID_BALL_CHOICES
    assert val != 5


def test_default_chooser_repeated_calls_always_valid():
    """Default ComputerPlayer produces valid choices in (1, 2, 3, 4, 6) over repeated calls."""
    bot = ComputerPlayer()
    for _ in range(100):
        choice = bot.choose_number()
        assert isinstance(choice, int)
        assert not isinstance(choice, bool)
        assert choice in VALID_BALL_CHOICES
        assert choice != 5


# ===========================================================================
# 3. Boundary Validation & Error Rejections
# ===========================================================================


@pytest.mark.parametrize("out_of_bounds", [0, 5, 7, -1, -100, 8, 99])
def test_rejects_out_of_bounds_injected_values(out_of_bounds):
    """Injected values outside VALID_BALL_CHOICES raise InvalidBallChoiceError."""
    bot = ComputerPlayer(chooser=lambda: out_of_bounds)
    with pytest.raises(InvalidBallChoiceError, match="choice must be one of"):
        bot.choose_number()


@pytest.mark.parametrize("bad_bool", [True, False])
def test_rejects_boolean_injected_values(bad_bool):
    """Booleans are explicitly rejected since bool is a subclass of int in Python."""
    bot = ComputerPlayer(chooser=lambda: bad_bool)  # type: ignore
    with pytest.raises(InvalidBallChoiceError, match="choice must be an integer, got bool"):
        bot.choose_number()


@pytest.mark.parametrize("non_int", ["4", None, 3.14, [1], {"a": 1}])
def test_rejects_non_integer_injected_values(non_int):
    """Non-integer types raise InvalidBallChoiceError."""
    bot = ComputerPlayer(chooser=lambda: non_int)  # type: ignore
    with pytest.raises(InvalidBallChoiceError, match="choice must be an integer"):
        bot.choose_number()


@pytest.mark.parametrize("invalid_chooser", ["not_callable", 123, [1, 2], None, False])
def test_constructor_rejects_non_callable_chooser(invalid_chooser):
    """Passing a non-callable to ComputerPlayer constructor raises TypeError."""
    if invalid_chooser is None:
        # None is the default and allowed
        return
    with pytest.raises(TypeError, match="Expected callable for chooser"):
        ComputerPlayer(chooser=invalid_chooser)  # type: ignore


# ===========================================================================
# 4. Conceptual Roles (Batting & Bowling Usage)
# ===========================================================================


def test_usable_as_batsman_choice():
    """ComputerPlayer output can be directly passed as batsman choice in ball resolution."""
    bot = ComputerPlayer(chooser=lambda: 4)
    # Bowler bowls 2, batsman chooses 4 -> 4 runs
    res = resolve_ball(batsman_choice=bot.choose_number(), bowler_choice=2)
    assert res.runs == 4
    assert res.is_wicket is False
    assert res.batsman_choice == 4
    assert res.bowler_choice == 2


def test_usable_as_bowler_choice():
    """ComputerPlayer output can be directly passed as bowler choice in ball resolution."""
    bot = ComputerPlayer(chooser=lambda: 4)
    # Batsman chooses 4, bowler chooses 4 -> Wicket
    res = resolve_ball(batsman_choice=4, bowler_choice=bot.choose_number())
    assert res.runs == 0
    assert res.is_wicket is True
    assert res.batsman_choice == 4
    assert res.bowler_choice == 4


def test_bot_vs_bot_interaction():
    """Two independent ComputerPlayer instances can interact in ball resolution."""
    bat_bot = ComputerPlayer(chooser=lambda: 3)
    bowl_bot = ComputerPlayer(chooser=lambda: 6)

    res = resolve_ball(bat_bot.choose_number(), bowl_bot.choose_number())
    assert res.runs == 3
    assert res.is_wicket is False


# ===========================================================================
# 5. Encapsulation & Isolation
# ===========================================================================


def test_instances_are_isolated():
    """Multiple ComputerPlayer instances maintain their own choosers independently."""
    bot_a = ComputerPlayer(chooser=lambda: 1)
    bot_b = ComputerPlayer(chooser=lambda: 6)

    assert bot_a.choose_number() == 1
    assert bot_b.choose_number() == 6


def test_no_mutable_game_state():
    """ComputerPlayer encapsulates no mutable match or game state."""
    bot = ComputerPlayer()
    forbidden_attributes = [
        "score",
        "wickets",
        "innings",
        "overs",
        "target",
        "opponent",
        "team",
        "player",
        "match",
    ]
    for attr in forbidden_attributes:
        assert not hasattr(bot, attr)


def test_repr_string_formatting():
    """ComputerPlayer __repr__ returns a readable representation."""
    bot_default = ComputerPlayer()
    assert "ComputerPlayer" in repr(bot_default)
    assert "default_number_chooser" in repr(bot_default)

    bot_custom = ComputerPlayer(chooser=lambda: 2)
    assert "ComputerPlayer" in repr(bot_custom)


def test_default_number_chooser_never_returns_5():
    """Sample default chooser 1,000 times to verify 5 is never chosen and all valid choices appear."""
    samples = {default_number_chooser() for _ in range(1000)}
    assert 5 not in samples
    assert samples == set(VALID_BALL_CHOICES)
