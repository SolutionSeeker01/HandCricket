"""Automated tests for the Headless Computer Player domain engine (Slice 8)."""

import pytest

from backend.app.engine.ball import (
    VALID_BALL_CHOICES,
    InvalidBallChoiceError,
    resolve_ball,
)
from backend.app.engine.computer import (
    ComputerPlayer,
    Difficulty,
    MatchContext,
    MAX_HISTORY_LENGTH,
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


# ===========================================================================
# 6. Difficulty.EASY Specifications (Phase 1)
# ===========================================================================


def test_default_difficulty_is_easy():
    """ComputerPlayer defaults to Difficulty.EASY when no difficulty is specified."""
    bot = ComputerPlayer()
    assert bot.difficulty == Difficulty.EASY


def test_explicit_easy_difficulty_construction():
    """ComputerPlayer can be explicitly created with Difficulty.EASY or 'easy' string."""
    bot_enum = ComputerPlayer(difficulty=Difficulty.EASY)
    assert bot_enum.difficulty == Difficulty.EASY

    bot_str = ComputerPlayer(difficulty="easy")
    assert bot_str.difficulty == Difficulty.EASY

    bot_case_insensitive = ComputerPlayer(difficulty="EASY")
    assert bot_case_insensitive.difficulty == Difficulty.EASY


def test_easy_mode_always_returns_valid_choices():
    """Easy mode choose_number() strictly returns valid choices in (1, 2, 3, 4, 6)."""
    bot = ComputerPlayer(difficulty=Difficulty.EASY)
    for _ in range(200):
        choice = bot.choose_number()
        assert choice in VALID_BALL_CHOICES
        assert choice != 5


def test_easy_mode_does_not_require_context_or_history():
    """Easy mode requires no arguments, history, or context to produce choices."""
    bot = ComputerPlayer(difficulty=Difficulty.EASY)
    choice = bot.choose_number()
    assert choice in VALID_BALL_CHOICES
    # Verify no tracking attributes exist on bot
    assert not hasattr(bot, "history")
    assert not hasattr(bot, "transition_matrix")
    assert not hasattr(bot, "frequency_table")


def test_easy_mode_samples_span_all_valid_choices():
    """Over 1,000 rolls, Easy mode produces all valid choices (1, 2, 3, 4, 6) and never 5."""
    bot = ComputerPlayer(difficulty=Difficulty.EASY)
    observed = {bot.choose_number() for _ in range(1000)}
    assert 5 not in observed
    assert observed == set(VALID_BALL_CHOICES)


def test_invalid_difficulty_string_raises_value_error():
    """Passing an unknown difficulty string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid difficulty 'super_hard'"):
        ComputerPlayer(difficulty="super_hard")


def test_invalid_difficulty_type_raises_type_error():
    """Passing a non-string and non-Difficulty type raises TypeError."""
    with pytest.raises(TypeError, match="Expected Difficulty enum or str"):
        ComputerPlayer(difficulty=123)  # type: ignore[arg-type]


def test_all_difficulty_modes_construct_without_chooser():
    """All difficulty modes (EASY, MEDIUM, HARD) construct and report their difficulty."""
    for diff in [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]:
        bot = ComputerPlayer(difficulty=diff)
        assert bot.difficulty == diff


def test_deterministic_chooser_with_any_difficulty():
    """When an explicit deterministic chooser is injected, it overrides the difficulty generator."""
    bot = ComputerPlayer(chooser=lambda: 6, difficulty=Difficulty.EASY)
    assert bot.choose_number() == 6
    assert bot.difficulty == Difficulty.EASY

    bot_med = ComputerPlayer(chooser=lambda: 4, difficulty=Difficulty.MEDIUM)
    assert bot_med.choose_number() == 4
    assert bot_med.difficulty == Difficulty.MEDIUM

    bot_hard = ComputerPlayer(chooser=lambda: 2, difficulty=Difficulty.HARD)
    assert bot_hard.choose_number() == 2
    assert bot_hard.difficulty == Difficulty.HARD


# ===========================================================================
# 7. Difficulty.MEDIUM Specifications (Phase 2)
# ===========================================================================


def test_medium_difficulty_construction():
    """ComputerPlayer can be initialized with Difficulty.MEDIUM or 'medium' string."""
    bot_enum = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    assert bot_enum.difficulty == Difficulty.MEDIUM

    bot_str = ComputerPlayer(difficulty="medium")
    assert bot_str.difficulty == Difficulty.MEDIUM

    bot_case = ComputerPlayer(difficulty="MEDIUM")
    assert bot_case.difficulty == Difficulty.MEDIUM


def test_medium_always_returns_valid_choices():
    """Medium mode choose_number() strictly returns valid choices in (1, 2, 3, 4, 6)."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    for _ in range(300):
        choice = bot.choose_number()
        assert choice in VALID_BALL_CHOICES
        assert choice != 5


def test_medium_empty_history_weights_are_uniform():
    """With no history, Medium bowling weights are uniform across all choices (20% each)."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    weights = bot.calculate_weights(MatchContext(role="bowl"))
    assert weights == {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 6: 1.0}

    total_weight = sum(weights.values())
    for c in VALID_BALL_CHOICES:
        prob = weights[c] / total_weight
        assert prob == pytest.approx(0.20, abs=1e-3)


def test_medium_bowling_detects_repeated_number_bias():
    """When human repeats a choice, Medium bowler boosts that choice to ~32% probability."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    bot.record_opponent_choice(4, role="bat")
    bot.record_opponent_choice(4, role="bat")

    weights = bot.calculate_weights(MatchContext(role="bowl"))
    # Choice 4 should receive repetition boost (+0.9)
    assert weights[4] == pytest.approx(1.9)
    assert weights[1] == 1.0
    assert weights[2] == 1.0
    assert weights[3] == 1.0
    assert weights[6] == 1.0

    total_weight = sum(weights.values())
    prob_4 = weights[4] / total_weight
    # Target range: 25% - 35% influence
    assert 0.25 <= prob_4 <= 0.35
    assert prob_4 == pytest.approx(1.9 / 5.9, abs=1e-3)  # ~32.2%


def test_medium_bowling_detects_favored_frequency_bias():
    """When human favors a choice without immediate repetition, bowler boosts it to ~29.8%."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    for c in [6, 1, 6, 2, 6]:
        bot.record_opponent_choice(c, role="bat")

    weights = bot.calculate_weights(MatchContext(role="bowl"))
    # Choice 6 is favored (count=3 >= 2), receives +0.7 boost
    assert weights[6] == pytest.approx(1.7)
    assert weights[1] == 1.0
    assert weights[2] == 1.0
    assert weights[3] == 1.0
    assert weights[4] == 1.0

    total_weight = sum(weights.values())
    prob_6 = weights[6] / total_weight
    # Target range: 25% - 35% influence
    assert 0.25 <= prob_6 <= 0.35
    assert prob_6 == pytest.approx(1.7 / 5.7, abs=1e-3)  # ~29.8%


def test_medium_bowling_diverse_history_remains_uniform():
    """When human plays all different numbers (no count >= 2, no repeats), weights remain uniform."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    for c in [1, 2, 3, 4, 6]:
        bot.record_opponent_choice(c, role="bat")

    weights = bot.calculate_weights(MatchContext(role="bowl"))
    assert weights == {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 6: 1.0}


def test_medium_batting_low_runs_needed_favors_singles_and_doubles():
    """When chasing a tiny target (runs_needed <= 2), Medium batter favors safe 1 and 2."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    ctx = MatchContext(role="bat", runs_needed=2, balls_remaining=10, target=25, innings=2)
    weights = bot.calculate_weights(ctx)

    assert weights[1] == pytest.approx(2.0)
    assert weights[2] == pytest.approx(2.0)
    assert weights[4] == pytest.approx(0.5)
    assert weights[6] == pytest.approx(0.5)

    total_weight = sum(weights.values())
    prob_safe = (weights[1] + weights[2]) / total_weight
    prob_boundary = (weights[4] + weights[6]) / total_weight

    assert prob_safe > 0.65  # ~69% safe choices
    assert prob_boundary < 0.20  # ~17% boundary choices


def test_medium_batting_high_rrr_favors_boundaries():
    """When required run rate is high (RRR >= 2.0), Medium batter heavily favors 4 and 6."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    # Needs 15 runs off 5 balls -> RRR = 3.0
    ctx = MatchContext(role="bat", runs_needed=15, balls_remaining=5, target=35, innings=2)
    weights = bot.calculate_weights(ctx)

    assert weights[4] == pytest.approx(1.8)
    assert weights[6] == pytest.approx(2.0)
    assert weights[1] == pytest.approx(0.5)

    total_weight = sum(weights.values())
    prob_boundary = (weights[4] + weights[6]) / total_weight
    assert prob_boundary > 0.60  # ~66.7% boundary choices


def test_medium_batting_evades_frequently_bowled_delivery():
    """Medium batter down-weights the delivery the human frequently bowls."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    # Human bowls 6 repeatedly
    for _ in range(4):
        bot.record_opponent_choice(6, role="bowl")

    # In regular batting (Innings 1)
    ctx = MatchContext(role="bat", innings=1)
    weights = bot.calculate_weights(ctx)

    # Base weight for 6 in early batting is 0.7; with evasion (-0.7) it hits the 0.2 floor
    assert weights[6] == pytest.approx(0.2)
    assert weights[4] == pytest.approx(0.9)  # 4 remains unaffected
    assert weights[1] > weights[6]
    assert weights[2] > weights[6]


def test_medium_batting_first_plays_safe_only_till_over_2():
    """Medium plays safe (preserves wickets) only in overs 1-2, then accelerates."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)

    # 1. Overs 1-2 (balls_remaining = 24, e.g. Over 1): safe platform building
    ctx_early = MatchContext(role="bat", innings=1, balls_remaining=24)
    w_early = bot.calculate_weights(ctx_early)
    # Safe numbers (1, 2, 3) must be higher than high-risk boundaries (4, 6)
    assert w_early[1] > w_early[4]
    assert w_early[2] > w_early[4]
    assert w_early[1] > w_early[6]
    assert w_early[2] > w_early[6]

    # 2. Overs 3-4 (balls_remaining = 14, e.g. Over 3): middle-overs acceleration
    ctx_mid = MatchContext(role="bat", innings=1, balls_remaining=14)
    w_mid = bot.calculate_weights(ctx_mid)
    # Boundaries (4, 6) now overtake singles (1)
    assert w_mid[4] > w_mid[1]
    assert w_mid[6] > w_mid[1]

    # 3. Over 5 (balls_remaining = 4, e.g. Over 5): death overs surge
    ctx_death = MatchContext(role="bat", innings=1, balls_remaining=4)
    w_death = bot.calculate_weights(ctx_death)
    assert w_death[4] >= 2.0
    assert w_death[6] >= 2.0
    assert w_death[4] > w_death[1]


def test_medium_statistical_sampling_demonstrates_probabilistic_bias():
    """Sampling 2,000 deliveries against a repeated opponent choice confirms ~32% bias, not 100%."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    bot.record_opponent_choice(4, role="bat")
    bot.record_opponent_choice(4, role="bat")

    samples = [bot.choose_number(MatchContext(role="bowl")) for _ in range(2000)]
    count_4 = samples.count(4)
    proportion_4 = count_4 / len(samples)

    # Should be around 32.2%, strictly between 26% and 38%
    assert 0.26 <= proportion_4 <= 0.38
    # Confirms it is not deterministic: other choices also appear
    assert set(samples) == set(VALID_BALL_CHOICES)


def test_medium_with_injected_rng_is_deterministic():
    """Injecting a seeded random.Random instance produces completely reproducible choices."""
    import random

    bot1 = ComputerPlayer(difficulty=Difficulty.MEDIUM, rng=random.Random(42))
    bot2 = ComputerPlayer(difficulty=Difficulty.MEDIUM, rng=random.Random(42))

    bot1.record_opponent_choice(3, role="bat")
    bot2.record_opponent_choice(3, role="bat")

    seq1 = [bot1.choose_number() for _ in range(20)]
    seq2 = [bot2.choose_number() for _ in range(20)]
    assert seq1 == seq2


def test_medium_history_reset():
    """Calling reset_history() clears recorded opponent choices and returns weights to baseline."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)
    bot.record_opponent_choice(4, role="bat")
    bot.record_opponent_choice(4, role="bat")

    assert bot.calculate_weights(MatchContext(role="bowl"))[4] > 1.0
    bot.reset_history()
    assert bot.calculate_weights(MatchContext(role="bowl"))[4] == 1.0


def test_record_opponent_choice_validation():
    """record_opponent_choice validates choice bounds and role strings."""
    bot = ComputerPlayer(difficulty=Difficulty.MEDIUM)

    with pytest.raises(InvalidBallChoiceError):
        bot.record_opponent_choice(5)  # 5 is illegal

    with pytest.raises(InvalidBallChoiceError):
        bot.record_opponent_choice(0)

    with pytest.raises(ValueError, match="Invalid role 'keeper'"):
        bot.record_opponent_choice(1, role="keeper")


# ===========================================================================
# 8. Difficulty.HARD Specifications (Phase 3)
# ===========================================================================


def test_hard_difficulty_construction():
    """ComputerPlayer can be initialized with Difficulty.HARD or 'hard' string."""
    bot_enum = ComputerPlayer(difficulty=Difficulty.HARD)
    assert bot_enum.difficulty == Difficulty.HARD

    bot_str = ComputerPlayer(difficulty="hard")
    assert bot_str.difficulty == Difficulty.HARD

    bot_case = ComputerPlayer(difficulty="HARD")
    assert bot_case.difficulty == Difficulty.HARD


def test_hard_always_returns_valid_choices():
    """Hard mode choose_number() strictly returns valid choices in (1, 2, 3, 4, 6)."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    for _ in range(300):
        choice = bot.choose_number()
        assert choice in VALID_BALL_CHOICES
        assert choice != 5


def test_hard_cold_start_sparse_history_remains_uniform():
    """With 0 to 1 observation, Hard bowling weights remain completely uniform."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    # 0 observations
    w0 = bot.calculate_weights(MatchContext(role="bowl"))
    assert w0 == {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 6: 1.0}

    # 1 observation (e.g. choice 4)
    bot.record_opponent_choice(4, role="bat")
    w1 = bot.calculate_weights(MatchContext(role="bowl"))
    assert w1 == {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 6: 1.0}


def test_hard_bowling_transition_prediction():
    """Hard bowler tracks transitions and predicts the successor of the last revealed choice."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    # Opponent sequence: 1 -> 6 -> 4 -> 6 -> 4
    # Transitions from 4: [6]
    for c in [1, 6, 4, 6, 4]:
        bot.record_opponent_choice(c, role="bat")

    weights = bot.calculate_weights(MatchContext(role="bowl"))
    # Opponent's last choice was 4; previous transition from 4 was 6.
    # Choice 6 must receive significant transition boost.
    assert weights[6] > weights[1]
    assert weights[6] > weights[2]
    assert weights[6] > weights[3]
    assert weights[6] > weights[4]


def test_hard_bowling_repeated_streak_prediction():
    """When human repeats a choice 2+ times, Hard bowler applies streak pressure."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    for c in [2, 3, 4, 4]:
        bot.record_opponent_choice(c, role="bat")

    weights = bot.calculate_weights(MatchContext(role="bowl"))
    # 4 is repeated at the tail
    assert weights[4] > 2.0
    assert weights[4] > weights[1]
    assert weights[4] > weights[2]
    assert weights[4] > weights[3]
    assert weights[4] > weights[6]


def test_hard_bowling_situational_must_hit_boundary():
    """When human needs high runs on final balls (e.g. 6 off 1), Hard anticipates 6."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    ctx = MatchContext(role="bowl", runs_needed=6, balls_remaining=1, target=20, innings=2)
    weights = bot.calculate_weights(ctx)

    assert weights[6] > weights[4]
    assert weights[6] > weights[1]
    assert weights[6] > 3.0


def test_hard_bowling_situational_small_runs_needed():
    """When human only needs 1 or 2 runs to win, Hard defends 1 and 2."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    ctx = MatchContext(role="bowl", runs_needed=2, balls_remaining=6, target=20, innings=2)
    weights = bot.calculate_weights(ctx)

    assert weights[1] > weights[4]
    assert weights[1] > weights[6]
    assert weights[2] > weights[4]
    assert weights[2] > weights[6]


def test_hard_bowling_death_overs_pressure():
    """In the final 3 balls of an innings, Hard anticipates aggressive boundary hitting."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    ctx = MatchContext(role="bowl", balls_remaining=2, innings=1)
    weights = bot.calculate_weights(ctx)

    assert weights[6] > weights[1]
    assert weights[4] > weights[1]


def test_hard_batting_active_evasion_of_human_delivery():
    """Hard batter identifies human's bowling pattern and heavily slashes that choice."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    # Human bowls 6 repeatedly
    for _ in range(4):
        bot.record_opponent_choice(6, role="bowl")

    weights = bot.calculate_weights(MatchContext(role="bat", innings=1))
    # Choice 6 should be aggressively slashed
    assert weights[6] < 0.5
    assert weights[4] > weights[6]
    assert weights[1] > weights[6]
    assert weights[2] > weights[6]


def test_hard_batting_chase_needs_one_run():
    """When needing 1 run to win, Hard batter heavily favors safe single 1."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    ctx = MatchContext(role="bat", runs_needed=1, balls_remaining=8, target=25, innings=2)
    weights = bot.calculate_weights(ctx)

    assert weights[1] > weights[2]
    assert weights[1] > weights[4]
    assert weights[1] > weights[6]
    assert weights[1] >= 3.5


def test_hard_batting_chase_high_rrr():
    """When RRR >= 2.0 per ball, Hard batter shifts heavily into boundary choices (4 and 6)."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    ctx = MatchContext(role="bat", runs_needed=14, balls_remaining=4, target=35, innings=2)
    weights = bot.calculate_weights(ctx)

    total_weight = sum(weights.values())
    prob_boundary = (weights[4] + weights[6]) / total_weight
    assert prob_boundary > 0.65


def test_hard_history_bounded_to_max_history_length():
    """Opponent history never exceeds MAX_HISTORY_LENGTH (30 deliveries)."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    for i in range(45):
        bot.record_opponent_choice((i % 4) + 1, role="bat")
        bot.record_opponent_choice(6, role="bowl")

    assert len(bot._opponent_batting_history) == MAX_HISTORY_LENGTH
    assert len(bot._opponent_bowling_history) == MAX_HISTORY_LENGTH


def test_hard_is_probabilistic_not_deterministic():
    """Sampling 2,000 deliveries against a predictable pattern confirms non-deterministic variety."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    # Repeated pattern
    for _ in range(5):
        bot.record_opponent_choice(4, role="bat")

    samples = [bot.choose_number(MatchContext(role="bowl")) for _ in range(2000)]
    # Choice 4 dominates heavily (~60%), while all legal choices still appear
    assert set(samples) == set(VALID_BALL_CHOICES)
    prop_4 = samples.count(4) / len(samples)
    assert 0.50 <= prop_4 <= 0.70
    assert samples.count(1) > 0
    assert samples.count(6) > 0


def test_hard_with_injected_rng_is_reproducible():
    """Two Hard bots initialized with the same RNG seed produce identical choice sequences."""
    import random

    bot1 = ComputerPlayer(difficulty=Difficulty.HARD, rng=random.Random(999))
    bot2 = ComputerPlayer(difficulty=Difficulty.HARD, rng=random.Random(999))

    for c in [1, 6, 4, 6]:
        bot1.record_opponent_choice(c, role="bat")
        bot2.record_opponent_choice(c, role="bat")

    seq1 = [bot1.choose_number() for _ in range(25)]
    seq2 = [bot2.choose_number() for _ in range(25)]
    assert seq1 == seq2


def test_hard_batting_first_anti_bait_counter_strike():
    """When human bowler hunts with 6 or 4 in Innings 1, Hard slashes the hunted number and counter-attacks."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)

    # 1. Bowler hunts with 6 repeatedly
    for _ in range(3):
        bot.record_opponent_choice(6, role="bowl")

    ctx = MatchContext(role="bat", innings=1, balls_remaining=20)
    w_against_6 = bot.calculate_weights(ctx)

    # 6 is slashed; 3 and 4 receive +1.0 counter-attack boost
    assert w_against_6[6] <= 0.4
    assert w_against_6[4] == pytest.approx(3.0)  # 2.0 + 1.0
    assert w_against_6[3] == pytest.approx(2.8)  # 1.8 + 1.0
    assert w_against_6[4] > w_against_6[6]
    assert w_against_6[3] > w_against_6[6]

    # 2. Bowler hunts with 4 repeatedly
    bot.reset_history()
    for _ in range(3):
        bot.record_opponent_choice(4, role="bowl")

    w_against_4 = bot.calculate_weights(ctx)
    # 4 is slashed; 6 and 3 receive +1.0 counter-attack boost
    assert w_against_4[4] <= 0.4
    assert w_against_4[6] == pytest.approx(2.8)  # 1.8 + 1.0
    assert w_against_4[3] == pytest.approx(2.8)  # 1.8 + 1.0
    assert w_against_4[6] > w_against_4[4]
    assert w_against_4[3] > w_against_4[4]


def test_hard_batting_first_punishes_defensive_bowling():
    """When human bowler bowls defensively (1 or 2) in Innings 1, Hard slashes defense and punishes with 4 & 6."""
    bot = ComputerPlayer(difficulty=Difficulty.HARD)
    for _ in range(3):
        bot.record_opponent_choice(1, role="bowl")

    # Regular overs (Overs 1-4)
    ctx_mid = MatchContext(role="bat", innings=1, balls_remaining=18)
    w_mid = bot.calculate_weights(ctx_mid)

    # 1 is slashed; boundaries 4 and 6 receive +0.8 boost
    assert w_mid[1] <= 0.2
    assert w_mid[4] == pytest.approx(2.8)  # 2.0 + 0.8
    assert w_mid[6] == pytest.approx(2.6)  # 1.8 + 0.8
    assert w_mid[4] > w_mid[1]
    assert w_mid[6] > w_mid[1]

    # Death over (Over 5)
    ctx_death = MatchContext(role="bat", innings=1, balls_remaining=5)
    w_death = bot.calculate_weights(ctx_death)
    # Boundaries dominate at maximum level
    assert w_death[4] == pytest.approx(3.2)  # 2.4 + 0.8
    assert w_death[6] == pytest.approx(3.4)  # 2.6 + 0.8
    assert w_death[1] <= 0.2




