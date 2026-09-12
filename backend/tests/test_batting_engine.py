"""Automated tests for the batsman lifecycle and score tracking engine."""

from dataclasses import FrozenInstanceError
import pytest

from backend.app.engine.ball import BallResult, resolve_ball
from backend.app.engine.batting import (
    BattingLifecycleError,
    BattingState,
    BattingStateView,
    InvalidBatsmanError,
    NoAvailableBatsmanError,
)


# ---------------------------------------------------------------------------
# 1. Initial State Verification
# ---------------------------------------------------------------------------


def test_initial_batting_state():
    """Verify clean starting state for a batting innings."""
    state = BattingState()

    assert state.team_size == 11
    assert state.striker == 1
    assert state.non_striker == 2
    assert state.next_batsman_id == 3
    assert state.total_runs == 0
    assert state.wickets == 0
    assert state.balls_processed == 0
    assert len(state.dismissed_batsmen) == 0

    # All 11 batsmen should have 0 runs and 0 balls faced
    scores = state.individual_scores
    balls = state.balls_faced
    assert len(scores) == 11
    for b_id in range(1, 12):
        assert scores[b_id] == 0
        assert balls[b_id] == 0
        assert state.is_dismissed(b_id) is False


# ---------------------------------------------------------------------------
# 2. Scoring & Individual Stats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("runs", [1, 2, 4, 6])
def test_scoring_updates_striker_and_total(runs: int):
    """Verify that runs update both the individual striker's score and total runs."""
    state = BattingState()
    ball = BallResult(batsman_choice=runs, bowler_choice=runs % 6 + 1, runs=runs, is_wicket=False)

    initial_striker = state.striker
    state.record_ball(ball)

    assert state.total_runs == runs
    assert state.get_batsman_score(initial_striker) == runs
    assert state.get_batsman_balls(initial_striker) == 1
    assert state.balls_processed == 1
    assert state.wickets == 0


# ---------------------------------------------------------------------------
# 3. Odd-Run Swapping (1, 3, 5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("odd_runs", [1, 3, 5])
def test_odd_runs_swap_striker_and_non_striker(odd_runs: int):
    """Odd runs (1, 3, 5) must swap the striker and non-striker."""
    state = BattingState()
    assert state.striker == 1
    assert state.non_striker == 2

    ball = BallResult(batsman_choice=odd_runs, bowler_choice=odd_runs % 6 + 1, runs=odd_runs, is_wicket=False)
    state.record_ball(ball)

    # Ends must be swapped
    assert state.striker == 2
    assert state.non_striker == 1
    # Batsman 1 scored the runs
    assert state.get_batsman_score(1) == odd_runs
    assert state.get_batsman_score(2) == 0


# ---------------------------------------------------------------------------
# 4. Even-Run Behavior (2, 4, 6)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("even_runs", [2, 4, 6])
def test_even_runs_do_not_swap_striker(even_runs: int):
    """Even runs (2, 4, 6) must NOT swap striker and non-striker."""
    state = BattingState()
    assert state.striker == 1
    assert state.non_striker == 2

    ball = BallResult(batsman_choice=even_runs, bowler_choice=even_runs % 6 + 1, runs=even_runs, is_wicket=False)
    state.record_ball(ball)

    # Striker remains the same
    assert state.striker == 1
    assert state.non_striker == 2
    assert state.get_batsman_score(1) == even_runs
    assert state.get_batsman_score(2) == 0


# ---------------------------------------------------------------------------
# 5. Wicket Lifecycle
# ---------------------------------------------------------------------------


def test_wicket_dismisses_striker_and_brings_next_batsman():
    """Verify that a wicket dismisses striker, increments wickets, and brings next batsman."""
    state = BattingState()
    wicket_ball = BallResult(batsman_choice=3, bowler_choice=3, runs=0, is_wicket=True)

    state.record_ball(wicket_ball)

    # Wickets incremented
    assert state.wickets == 1
    assert state.total_runs == 0
    # Batsman 1 was dismissed
    assert state.is_dismissed(1) is True
    assert state.dismissed_batsmen == [1]
    # Batsman 1 faced 1 ball and scored 0
    assert state.get_batsman_balls(1) == 1
    assert state.get_batsman_score(1) == 0
    # Next batsman (3) enters as the new striker
    assert state.striker == 3
    # Non-striker (2) remains in place
    assert state.non_striker == 2
    # Next waiting batsman is now 4
    assert state.next_batsman_id == 4
    # Arriving batsman (3) initial stats must be explicitly 0 (M4)
    assert state.get_batsman_score(3) == 0
    assert state.get_batsman_balls(3) == 0


def test_consecutive_wickets():
    """Verify state when multiple wickets fall in succession."""
    state = BattingState()
    wicket_ball = BallResult(batsman_choice=5, bowler_choice=5, runs=0, is_wicket=True)

    # Ball 1: Batsman 1 gets out -> Batsman 3 enters
    state.record_ball(wicket_ball)
    assert state.wickets == 1
    assert state.striker == 3
    assert state.non_striker == 2
    assert state.dismissed_batsmen == [1]

    # Ball 2: Batsman 3 gets out -> Batsman 4 enters
    state.record_ball(wicket_ball)
    assert state.wickets == 2
    assert state.striker == 4
    assert state.non_striker == 2
    assert state.dismissed_batsmen == [1, 3]


# ---------------------------------------------------------------------------
# 6. Realistic Sequential Lifecycle
# ---------------------------------------------------------------------------


def test_realistic_batting_sequence():
    """Test realistic match progression with runs, odd swaps, even retention, and wickets."""
    state = BattingState()

    # Initial: striker=1, non_striker=2
    # Ball 1: Batsman 1 scores 4 (even -> no swap)
    state.record_ball(resolve_ball(4, 2))
    assert state.total_runs == 4
    assert state.get_batsman_score(1) == 4
    assert state.striker == 1
    assert state.non_striker == 2

    # Ball 2: Batsman 1 scores 1 (odd -> swap!)
    state.record_ball(resolve_ball(1, 2))
    assert state.total_runs == 5
    assert state.get_batsman_score(1) == 5
    assert state.striker == 2
    assert state.non_striker == 1

    # Ball 3: Batsman 2 scores 2 (even -> no swap)
    state.record_ball(resolve_ball(2, 4))
    assert state.total_runs == 7
    assert state.get_batsman_score(2) == 2
    assert state.striker == 2
    assert state.non_striker == 1

    # Ball 4: Batsman 2 scores 3 (odd -> swap!)
    state.record_ball(resolve_ball(3, 1))
    assert state.total_runs == 10
    assert state.get_batsman_score(2) == 5
    assert state.striker == 1
    assert state.non_striker == 2

    # Ball 5: Batsman 1 gets OUT! (matched choice 5 vs 5)
    state.record_ball(resolve_ball(5, 5))
    assert state.wickets == 1
    assert state.total_runs == 10
    assert state.is_dismissed(1) is True
    # Batsman 3 enters as striker; batsman 2 remains non-striker
    assert state.striker == 3
    assert state.non_striker == 2

    # Ball 6: Batsman 3 scores 6 (even -> no swap)
    state.record_ball(resolve_ball(6, 1))
    assert state.total_runs == 16
    assert state.get_batsman_score(3) == 6
    assert state.striker == 3
    assert state.non_striker == 2
    assert state.balls_processed == 6


# ---------------------------------------------------------------------------
# 7. Exhaustion of Available Batsmen & NoAvailableBatsmanError
# ---------------------------------------------------------------------------


def test_exhaustion_of_batsmen_prevents_further_balls():
    """Verify that when all 10 wickets fall (all 11 batsmen used), processing further balls raises error."""
    state = BattingState(team_size=3)  # Miniature 3-player team for precise boundary testing
    # Initial: striker=1, non_striker=2, next=3
    wicket = BallResult(batsman_choice=1, bowler_choice=1, runs=0, is_wicket=True)

    # Wicket 1: Batsman 1 out -> Batsman 3 enters (striker=3, non_striker=2)
    state.record_ball(wicket)
    assert state.wickets == 1
    assert state.striker == 3
    assert state.non_striker == 2

    # Wicket 2: Batsman 3 out -> No more batsmen available! (next_id 4 > 3)
    state.record_ball(wicket)
    assert state.wickets == 2
    assert state.striker is None

    # Processing another ball with no striker must raise NoAvailableBatsmanError
    with pytest.raises(NoAvailableBatsmanError, match="no active striker"):
        state.record_ball(BallResult(batsman_choice=4, bowler_choice=2, runs=4, is_wicket=False))


# ---------------------------------------------------------------------------
# 8. Invalid Lifecycle Operations & Type Safety
# ---------------------------------------------------------------------------


def test_rejects_invalid_ball_result_type():
    """Passing a non-BallResult to record_ball must raise TypeError."""
    state = BattingState()
    with pytest.raises(TypeError, match="Expected BallResult"):
        state.record_ball({"runs": 4, "is_wicket": False})  # type: ignore


@pytest.mark.parametrize("invalid_id", [0, -1, 12, 99, True, False, "1", 3.0])
def test_invalid_batsman_id_validation(invalid_id):
    """Invalid batsman identifiers must raise InvalidBatsmanError."""
    state = BattingState()
    with pytest.raises(InvalidBatsmanError):
        state.get_batsman_score(invalid_id)

    with pytest.raises(InvalidBatsmanError):
        state.is_dismissed(invalid_id)


@pytest.mark.parametrize("invalid_team_size", [1, 0, -5, True, False, "11"])
def test_invalid_team_size(invalid_team_size):
    """Team sizes below 2 or non-integers must raise BattingLifecycleError."""
    with pytest.raises(BattingLifecycleError, match="team size must be an integer >= 2"):
        BattingState(team_size=invalid_team_size)


# ---------------------------------------------------------------------------
# 9. Immutability & State Isolation
# ---------------------------------------------------------------------------


def test_returned_properties_are_copies():
    """Mutating returned individual_scores or dismissed_batsmen must not alter internal state."""
    state = BattingState()
    state.record_ball(resolve_ball(4, 2))

    scores = state.individual_scores
    scores[1] = 999
    assert state.get_batsman_score(1) == 4

    dismissed = state.dismissed_batsmen
    dismissed.append(99)
    assert 99 not in state.dismissed_batsmen


def test_ball_result_cannot_be_corrupted():
    """Ensure BallResult passed into record_ball remains immutable."""
    ball = resolve_ball(4, 2)
    state = BattingState()
    state.record_ball(ball)

    with pytest.raises(FrozenInstanceError):
        ball.runs = 100  # type: ignore


def test_batting_state_view_read_only_protection():
    """BattingStateView provides read access but does not expose mutation methods like record_ball."""
    state = BattingState()
    state.record_ball(resolve_ball(4, 2))
    view = state.as_view()

    # Query properties match
    assert view.striker == 1
    assert view.non_striker == 2
    assert view.total_runs == 4
    assert view.wickets == 0
    assert view.team_size == 11
    assert view.next_batsman_id == 3
    assert view.balls_processed == 1
    assert view.get_batsman_score(1) == 4
    assert view.get_batsman_balls(1) == 1
    assert view.is_dismissed(1) is False
    assert len(view.individual_scores) == 11

    # View has NO record_ball method
    assert not hasattr(view, "record_ball")
    with pytest.raises(AttributeError):
        view.record_ball(resolve_ball(1, 2))  # type: ignore

