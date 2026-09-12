"""Comprehensive test suite for the Hand Cricket innings and over progression engine (Slice 4)."""

import pytest

from backend.app.engine.ball import BallResult, resolve_ball
from backend.app.engine.batting import BattingState
from backend.app.engine.innings import (
    DEFAULT_BALLS_PER_OVER,
    DEFAULT_MAX_OVERS,
    Innings,
    InningsCompleteError,
    InningsError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_run_ball(runs: int) -> BallResult:
    """Helper to produce a non-wicket BallResult for scoring runs."""
    return BallResult(batsman_choice=runs, bowler_choice=(runs % 6) + 1, runs=runs, is_wicket=False)


def make_wicket_ball() -> BallResult:
    """Helper to produce a wicket BallResult."""
    return BallResult(batsman_choice=3, bowler_choice=3, runs=0, is_wicket=True)


# ---------------------------------------------------------------------------
# 1. Initial State
# ---------------------------------------------------------------------------


def test_initial_innings_state():
    """Verify clean initial state of an innings."""
    innings = Innings()

    # Over & ball counters
    assert innings.current_over == 1
    assert innings.balls_in_current_over == 0
    assert innings.total_balls == 0
    assert innings.max_overs == DEFAULT_MAX_OVERS
    assert innings.balls_per_over == DEFAULT_BALLS_PER_OVER
    assert innings.max_balls == 30

    # Completion indicators
    assert innings.innings_complete is False
    assert innings.is_completed is False
    assert innings.over_complete is False
    assert innings.is_over_complete is False

    # Batting state delegation
    assert innings.striker == 1
    assert innings.non_striker == 2
    assert innings.total_runs == 0
    assert innings.wickets == 0
    assert isinstance(innings.batting_state, BattingState)


# ---------------------------------------------------------------------------
# 2. Single Ball Progression
# ---------------------------------------------------------------------------


def test_single_ball_progression():
    """Processing a single valid ball updates counters and underlying batting state."""
    innings = Innings()
    ball = resolve_ball(4, 2)  # 4 runs

    innings.record_ball(ball)

    assert innings.balls_in_current_over == 1
    assert innings.total_balls == 1
    assert innings.current_over == 1
    assert innings.innings_complete is False
    assert innings.over_complete is False

    # Verify underlying batting state updated correctly
    assert innings.total_runs == 4
    assert innings.wickets == 0
    assert innings.striker == 1
    assert innings.non_striker == 2
    assert innings.batting_state.get_batsman_score(1) == 4
    assert innings.batting_state.get_batsman_balls(1) == 1


# ---------------------------------------------------------------------------
# 3. Six-Ball Over
# ---------------------------------------------------------------------------


def test_six_ball_over():
    """Process six valid balls and verify transition to next over."""
    innings = Innings()

    for _ in range(6):
        innings.record_ball(make_run_ball(2))

    assert innings.total_balls == 6
    assert innings.balls_in_current_over == 0
    assert innings.current_over == 2
    assert innings.innings_complete is False
    assert innings.over_complete is True
    assert innings.total_runs == 12


def test_seventh_ball_starts_second_over():
    """Seventh ball must be recorded as ball 1 of over 2, not part of over 1."""
    innings = Innings()

    for _ in range(6):
        innings.record_ball(make_run_ball(2))

    # Ball 7
    innings.record_ball(make_run_ball(1))

    assert innings.total_balls == 7
    assert innings.balls_in_current_over == 1
    assert innings.current_over == 2
    assert innings.innings_complete is False
    assert innings.over_complete is False


# ---------------------------------------------------------------------------
# 4. Multiple Overs & Partial Overs
# ---------------------------------------------------------------------------


def test_twelve_balls_reaches_over_three():
    """Processing 12 balls completes 2 overs and enters over 3 with 0 balls."""
    innings = Innings()

    for _ in range(12):
        innings.record_ball(make_run_ball(2))

    assert innings.current_over == 3
    assert innings.balls_in_current_over == 0
    assert innings.total_balls == 12
    assert innings.innings_complete is False
    assert innings.over_complete is True


def test_fourteen_balls_partial_over():
    """Processing 14 balls lands on over 3 with 2 balls completed."""
    innings = Innings()

    for _ in range(14):
        innings.record_ball(make_run_ball(2))

    assert innings.current_over == 3
    assert innings.balls_in_current_over == 2
    assert innings.total_balls == 14
    assert innings.innings_complete is False
    assert innings.over_complete is False


# ---------------------------------------------------------------------------
# 5. Thirty-Ball Innings & Termination
# ---------------------------------------------------------------------------


def test_thirty_ball_innings_completion():
    """Process exactly 30 valid balls: completes innings, stays in over 5, no over 6."""
    innings = Innings()

    for _ in range(30):
        innings.record_ball(make_run_ball(2))

    assert innings.current_over == 5
    assert innings.total_balls == 30
    assert innings.balls_in_current_over == 0
    assert innings.innings_complete is True
    assert innings.is_completed is True
    assert innings.over_complete is True


# ---------------------------------------------------------------------------
# 6. Wicket Ball Counting
# ---------------------------------------------------------------------------


def test_wicket_ball_counts_towards_over_and_total():
    """A wicket ball must count as a completed ball and advance counters normally."""
    innings = Innings()

    # Ball 1: Wicket!
    wicket_ball = resolve_ball(5, 5)
    innings.record_ball(wicket_ball)

    assert innings.balls_in_current_over == 1
    assert innings.total_balls == 1
    assert innings.current_over == 1
    assert innings.wickets == 1
    assert innings.striker == 3  # Next batsman arrives
    assert innings.non_striker == 2
    assert innings.innings_complete is False


def test_over_completes_when_sixth_ball_is_a_wicket():
    """Wicket on the 6th ball still completes the over normally."""
    innings = Innings()

    for _ in range(5):
        innings.record_ball(make_run_ball(2))

    # Ball 6: Wicket
    innings.record_ball(make_wicket_ball())

    assert innings.total_balls == 6
    assert innings.balls_in_current_over == 0
    assert innings.current_over == 2
    assert innings.wickets == 1
    assert innings.innings_complete is False
    assert innings.over_complete is True


# ---------------------------------------------------------------------------
# 7. All-Out Completion
# ---------------------------------------------------------------------------


def test_all_out_completes_innings_with_small_team():
    """When all available batsmen are exhausted, innings completes immediately."""
    # Team of 3: striker 1, non-striker 2, waiting 3.
    # Wicket 1: striker 1 out -> 3 enters.
    # Wicket 2: striker 3 out -> no batsmen left, striker is None -> all out!
    innings = Innings(team_size=3)

    # Ball 1: 4 runs scored
    innings.record_ball(make_run_ball(4))
    assert innings.total_balls == 1
    assert innings.innings_complete is False

    # Ball 2: Wicket 1 (batsman 1 out, batsman 3 enters)
    innings.record_ball(make_wicket_ball())
    assert innings.wickets == 1
    assert innings.striker == 3
    assert innings.non_striker == 2
    assert innings.innings_complete is False

    # Ball 3: Wicket 2 (batsman 3 out, no batsman waiting -> all out!)
    innings.record_ball(make_wicket_ball())
    assert innings.wickets == 2
    assert innings.striker is None
    assert innings.innings_complete is True
    assert innings.is_completed is True
    assert innings.total_balls == 3
    assert innings.balls_in_current_over == 3
    assert innings.current_over == 1
    assert innings.over_complete is False


def test_all_out_on_over_boundary():
    """If all-out occurs on exactly the 6th ball, over is complete and innings is complete."""
    innings = Innings(team_size=3)

    # 4 scoring balls
    for _ in range(4):
        innings.record_ball(make_run_ball(2))

    # Ball 5: Wicket 1
    innings.record_ball(make_wicket_ball())
    assert innings.innings_complete is False

    # Ball 6: Wicket 2 (All out!)
    innings.record_ball(make_wicket_ball())
    assert innings.striker is None
    assert innings.innings_complete is True
    assert innings.total_balls == 6
    assert innings.balls_in_current_over == 0
    assert innings.current_over == 1  # Does not advance to over 2 because innings is complete
    assert innings.over_complete is True


# ---------------------------------------------------------------------------
# 8. Ball Rejection After Innings Completion
# ---------------------------------------------------------------------------


def test_ball_rejected_after_thirty_balls():
    """Attempting to record a ball after 30 balls must raise InningsCompleteError."""
    innings = Innings()
    for _ in range(30):
        innings.record_ball(make_run_ball(2))

    assert innings.innings_complete is True
    assert innings.total_balls == 30
    runs_before = innings.total_runs

    with pytest.raises(InningsCompleteError, match="innings is already complete"):
        innings.record_ball(make_run_ball(4))

    # Invariants unchanged
    assert innings.total_balls == 30
    assert innings.total_runs == runs_before
    assert innings.batting_state.balls_processed == 30


def test_ball_rejected_after_all_out():
    """Attempting to record a ball after all-out must raise InningsCompleteError."""
    innings = Innings(team_size=3)
    innings.record_ball(make_wicket_ball())  # Wicket 1
    innings.record_ball(make_wicket_ball())  # Wicket 2 -> All out!

    assert innings.innings_complete is True
    assert innings.total_balls == 2
    runs_before = innings.total_runs

    with pytest.raises(InningsCompleteError, match="innings is already complete"):
        innings.record_ball(make_run_ball(4))

    # Invariants unchanged
    assert innings.total_balls == 2
    assert innings.total_runs == runs_before
    assert innings.batting_state.balls_processed == 2


# ---------------------------------------------------------------------------
# 9. Sequential Integration: Innings -> BattingState Consistency
# ---------------------------------------------------------------------------


def test_realistic_sequential_innings_progression():
    """Verify consistency between Innings counters and BattingState lifecycle across 6 balls."""
    innings = Innings()

    # Initial: striker=1, non_striker=2
    # Ball 1: Batsman 1 scores 4 runs (even -> no swap)
    innings.record_ball(resolve_ball(4, 2))
    assert innings.total_balls == 1
    assert innings.balls_in_current_over == 1
    assert innings.current_over == 1
    assert innings.total_runs == 4
    assert innings.striker == 1
    assert innings.non_striker == 2

    # Ball 2: Batsman 1 scores 1 run (odd -> swap!)
    innings.record_ball(resolve_ball(1, 2))
    assert innings.total_balls == 2
    assert innings.balls_in_current_over == 2
    assert innings.current_over == 1
    assert innings.total_runs == 5
    assert innings.striker == 2
    assert innings.non_striker == 1

    # Ball 3: Batsman 2 scores 6 runs (even -> no swap)
    innings.record_ball(resolve_ball(6, 4))
    assert innings.total_balls == 3
    assert innings.balls_in_current_over == 3
    assert innings.current_over == 1
    assert innings.total_runs == 11
    assert innings.striker == 2
    assert innings.non_striker == 1

    # Ball 4: Batsman 2 scores 3 runs (odd -> swap!)
    innings.record_ball(resolve_ball(3, 1))
    assert innings.total_balls == 4
    assert innings.balls_in_current_over == 4
    assert innings.current_over == 1
    assert innings.total_runs == 14
    assert innings.striker == 1
    assert innings.non_striker == 2

    # Ball 5: Batsman 1 gets OUT (5 vs 5)! Batsman 3 enters as striker
    innings.record_ball(resolve_ball(5, 5))
    assert innings.total_balls == 5
    assert innings.balls_in_current_over == 5
    assert innings.current_over == 1
    assert innings.wickets == 1
    assert innings.striker == 3
    assert innings.non_striker == 2

    # Ball 6: Batsman 3 scores 2 runs (even -> no swap)
    innings.record_ball(resolve_ball(2, 4))
    assert innings.total_balls == 6
    assert innings.balls_in_current_over == 0
    assert innings.current_over == 2
    assert innings.total_runs == 16
    assert innings.striker == 3
    assert innings.non_striker == 2
    assert innings.over_complete is True
    assert innings.innings_complete is False

    # Detailed batsman score checks
    assert innings.batting_state.get_batsman_score(1) == 5  # 4 + 1
    assert innings.batting_state.get_batsman_balls(1) == 3  # faced balls 1, 2, 5
    assert innings.batting_state.get_batsman_score(2) == 9  # 6 + 3
    assert innings.batting_state.get_batsman_balls(2) == 2  # faced balls 3, 4
    assert innings.batting_state.get_batsman_score(3) == 2  # 2
    assert innings.batting_state.get_batsman_balls(3) == 1  # faced ball 6


# ---------------------------------------------------------------------------
# 10. Boundary Tests (Over 5, Ball 30, No Over 6)
# ---------------------------------------------------------------------------


def test_fifth_over_progression_boundaries():
    """Balls 1-5 of over 5 leave innings incomplete; ball 6 completes it."""
    innings = Innings()

    # Bowl 4 complete overs (24 balls)
    for _ in range(24):
        innings.record_ball(make_run_ball(2))

    assert innings.current_over == 5
    assert innings.balls_in_current_over == 0
    assert innings.total_balls == 24
    assert innings.innings_complete is False

    # Balls 25 through 29 (Balls 1 to 5 of Over 5)
    for b in range(1, 6):
        innings.record_ball(make_run_ball(2))
        assert innings.current_over == 5
        assert innings.balls_in_current_over == b
        assert innings.total_balls == 24 + b
        assert innings.innings_complete is False
        assert innings.over_complete is False

    # Ball 30 (Ball 6 of Over 5): Completes innings!
    innings.record_ball(make_run_ball(2))
    assert innings.current_over == 5  # Stays 5, no over 6!
    assert innings.balls_in_current_over == 0
    assert innings.total_balls == 30
    assert innings.innings_complete is True
    assert innings.over_complete is True


def test_wicket_on_thirtieth_ball_counts_and_completes_innings():
    """Wicket on ball 30 counts as ball 30, increments wickets, and completes innings."""
    innings = Innings()

    for _ in range(29):
        innings.record_ball(make_run_ball(2))

    assert innings.total_balls == 29
    assert innings.wickets == 0
    assert innings.innings_complete is False

    # Ball 30: Wicket!
    innings.record_ball(make_wicket_ball())

    assert innings.total_balls == 30
    assert innings.balls_in_current_over == 0
    assert innings.current_over == 5
    assert innings.wickets == 1
    assert innings.innings_complete is True
    assert innings.over_complete is True


# ---------------------------------------------------------------------------
# 11. Strict Rule: No Automatic Striker Change at Over End
# ---------------------------------------------------------------------------


def test_no_automatic_striker_change_at_over_end():
    """Over completion must NOT automatically swap striker and non-striker."""
    innings = Innings()

    # Bowl 6 balls with 2 runs each (even runs -> no odd-run swap occurs)
    for _ in range(6):
        innings.record_ball(make_run_ball(2))

    assert innings.total_balls == 6
    assert innings.current_over == 2
    assert innings.over_complete is True

    # Batsman 1 should STILL be striker, and Batsman 2 should STILL be non-striker
    assert innings.striker == 1
    assert innings.non_striker == 2


# ---------------------------------------------------------------------------
# 12. State Isolation
# ---------------------------------------------------------------------------


def test_independent_innings_instances():
    """Two innings instances must maintain completely isolated states."""
    innings1 = Innings()
    innings2 = Innings()

    # Bowl 6 balls in innings 1
    for _ in range(6):
        innings1.record_ball(make_run_ball(4))

    # Innings 1 updated
    assert innings1.total_balls == 6
    assert innings1.current_over == 2
    assert innings1.total_runs == 24

    # Innings 2 completely pristine
    assert innings2.total_balls == 0
    assert innings2.current_over == 1
    assert innings2.balls_in_current_over == 0
    assert innings2.total_runs == 0
    assert innings2.innings_complete is False


# ---------------------------------------------------------------------------
# 13. Validation & Type Safety
# ---------------------------------------------------------------------------


def test_rejects_non_ball_result():
    """Passing a non-BallResult to record_ball must raise TypeError."""
    innings = Innings()
    with pytest.raises(TypeError, match="Expected BallResult"):
        innings.record_ball("not a ball result")  # type: ignore

    with pytest.raises(TypeError, match="Expected BallResult"):
        innings.record_ball(1)  # type: ignore

    with pytest.raises(TypeError, match="Expected BallResult"):
        innings.record_ball({"runs": 4})  # type: ignore


@pytest.mark.parametrize("invalid_overs", [0, -1, -5, True, False, "5", 5.0])
def test_rejects_invalid_max_overs(invalid_overs):
    """Invalid max_overs must raise InningsError."""
    with pytest.raises(InningsError):
        Innings(max_overs=invalid_overs)


@pytest.mark.parametrize("invalid_balls", [0, -1, -6, True, False, "6", 6.0])
def test_rejects_invalid_balls_per_over(invalid_balls):
    """Invalid balls_per_over must raise InningsError."""
    with pytest.raises(InningsError):
        Innings(balls_per_over=invalid_balls)


def test_custom_batting_state_injection():
    """Innings accepts a custom pre-instantiated BattingState."""
    custom_state = BattingState(team_size=5)
    innings = Innings(batting_state=custom_state)
    assert innings.batting_state is custom_state
    assert innings.striker == 1


def test_rejects_invalid_batting_state_type():
    """Passing an invalid object as batting_state must raise TypeError."""
    with pytest.raises(TypeError, match="Expected BattingState"):
        Innings(batting_state="not a batting state")  # type: ignore


def test_repr_representation():
    """Verify clean string representation for debugging."""
    innings = Innings()
    innings.record_ball(make_run_ball(4))
    repr_str = repr(innings)
    assert "over=1/5" in repr_str
    assert "ball=1/6" in repr_str
    assert "total_balls=1/30" in repr_str
    assert "runs=4" in repr_str
    assert "complete=False" in repr_str


def test_over_complete_semantics_clarification():
    """Verify that over_complete means 'the most recently recorded ball completed an over',
    NOT 'the currently active over is complete'.
    """
    innings = Innings()

    # Initial state: active over 1 is underway with 0 balls bowled.
    # No ball has been recorded yet, so the previous ball did NOT complete an over.
    assert innings.current_over == 1
    assert innings.balls_in_current_over == 0
    assert innings.over_complete is False
    assert innings.is_over_complete is False

    # Balls 1 to 5: actively bowling over 1.
    for ball_num in range(1, 6):
        innings.record_ball(make_run_ball(2))
        assert innings.current_over == 1
        assert innings.balls_in_current_over == ball_num
        assert innings.over_complete is False
        assert innings.is_over_complete is False

    # Ball 6: This ball completes over 1!
    innings.record_ball(make_run_ball(2))
    assert innings.total_balls == 6
    assert innings.balls_in_current_over == 0
    assert innings.current_over == 2
    # over_complete is True because the 6th ball just completed over 1.
    # It does NOT mean active over 2 is complete.
    assert innings.over_complete is True
    assert innings.is_over_complete is True

    # Ball 7 (Ball 1 of Over 2):
    innings.record_ball(make_run_ball(2))
    assert innings.total_balls == 7
    assert innings.current_over == 2
    assert innings.balls_in_current_over == 1
    # Now over_complete returns False again because ball 7 was not an over-ending ball.
    assert innings.over_complete is False
    assert innings.is_over_complete is False

