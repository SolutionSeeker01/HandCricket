"""Automated tests for Full Match & Target Chasing domain engine (Slice 6)."""

import pytest

from backend.app.engine.ball import BallResult, resolve_ball
from backend.app.engine.bowling import (
    BowlerAlreadyBowledError,
    BowlingLifecycleError,
    BowlingStateView,
    InvalidBowlerError,
)
from backend.app.engine.match import (
    BowlerSelectionError,
    InningsTransitionError,
    InningsView,
    Match,
    MatchError,
    MatchLifecycleError,
    MatchStatus,
    MatchView,
)


def _score_runs(match: Match, runs_needed: int) -> None:
    """Helper to score a specific number of runs in the active innings without wickets.

    Handles bowler selection across over boundaries automatically using available bowlers.
    """
    runs_remaining = runs_needed
    while runs_remaining > 0 and not match.is_completed:
        # Check if bowler needs to be selected for this over
        current_bowling = match.current_bowling_state
        assert current_bowling is not None
        if not current_bowling.is_over_active:
            eligible = current_bowling.eligible_bowlers
            if not eligible:
                break
            match.select_bowler(eligible[0])

        if runs_remaining >= 6:
            step = 6
        elif runs_remaining == 5:
            step = 4
        else:
            step = runs_remaining

        # Bowl choice is always in (1, 2) and different from step
        bowl = 2 if step != 2 else 1
        match.resolve_and_record_ball(step, bowl)
        runs_remaining -= step


def _bowl_wickets(match: Match, wickets_needed: int) -> None:
    """Helper to take wickets in the active innings.

    Handles bowler selection across over boundaries automatically.
    """
    wickets_taken = 0
    while wickets_taken < wickets_needed and not match.is_completed:
        current_bowling = match.current_bowling_state
        assert current_bowling is not None
        if not current_bowling.is_over_active:
            eligible = current_bowling.eligible_bowlers
            if not eligible:
                break
            match.select_bowler(eligible[0])

        # Matching choices generate a wicket with 0 runs
        match.resolve_and_record_ball(1, 1)
        wickets_taken += 1


# ===========================================================================
# Section 1: Initial State & Constructor Validation (Requirement A & Config)
# ===========================================================================


def test_initial_match_state():
    """Requirement A: Verify clean initial state of a Match instance before starting."""
    match = Match(team_1="India", team_2="Australia")

    assert match.status == MatchStatus.NOT_STARTED
    assert match.is_completed is False
    assert match.team_1 == "India"
    assert match.team_2 == "Australia"
    assert match.team_size == 11
    assert match.max_overs == 5
    assert match.balls_per_over == 6
    assert match.max_balls == 30

    assert match.current_innings_number is None
    assert match.current_innings is None
    assert match.current_bowling_state is None
    assert match.innings_1 is None
    assert match.innings_2 is None
    assert match.bowling_1 is None
    assert match.bowling_2 is None

    assert match.innings_1_score is None
    assert match.innings_1_wickets is None
    assert match.innings_2_score is None
    assert match.innings_2_wickets is None
    assert match.target is None
    assert match.winner is None
    assert match.is_tie is False
    assert match.result_description is None
    assert match.batting_team is None
    assert match.bowling_team is None


@pytest.mark.parametrize(
    "t1,t2,size,overs,balls",
    [
        ("", "Team B", 11, 5, 6),
        ("Team A", "   ", 11, 5, 6),
        (None, "Team B", 11, 5, 6),
        ("Team A", None, 11, 5, 6),
        ("Team A", "Team B", 11, 0, 6),
        ("Team A", "Team B", 11, -1, 6),
        ("Team A", "Team B", 11, 5, 0),
        ("Team A", "Team B", 11, 5, -2),
        ("Team A", "Team B", 4, 5, 6),  # team_size < max_overs violates quota
        ("Team A", "Team B", True, 5, 6),
        ("Team A", "Team B", 11, True, 6),
        ("Team A", "Team B", 11, 5, True),
        ("Team A", "Team A", 11, 5, 6),
        ("India", "india", 11, 5, 6),
        ("India", " INDIA ", 11, 5, 6),
    ],
)
def test_constructor_argument_validation(t1, t2, size, overs, balls):
    """Constructor validates team names, over limits, ball limits, and quota viability."""
    with pytest.raises(MatchError):
        Match(team_1=t1, team_2=t2, team_size=size, max_overs=overs, balls_per_over=balls)  # type: ignore


def test_constructor_rejects_identical_team_names():
    """Cleanup #4: Match constructor raises MatchError if team_1 and team_2 are identical."""
    with pytest.raises(MatchError) as exc_info:
        Match(team_1="India", team_2="India")
    assert "must be distinct" in str(exc_info.value)


# ===========================================================================
# Section 2: Valid Match Start (Requirement B)
# ===========================================================================


def test_valid_match_start():
    """Requirement B: Starting match initializes Innings 1 and BowlingState 1."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    assert match.status == MatchStatus.INNINGS_1
    assert match.is_completed is False
    assert match.current_innings_number == 1
    assert match.batting_team == "India"
    assert match.bowling_team == "Australia"

    assert match.innings_1 is not None
    assert isinstance(match.innings_1, InningsView)
    assert match.innings_1.total_runs == 0
    assert match.innings_1.wickets == 0
    assert match.innings_1.current_over == 1
    assert match.innings_1.balls_in_current_over == 0
    assert match.innings_1.total_balls == 0
    assert match.innings_1.is_completed is False

    assert match.bowling_1 is not None
    assert isinstance(match.bowling_1, BowlingStateView)
    assert match.bowling_1.completed_overs == 0
    assert match.bowling_1.active_bowler is None
    assert len(match.bowling_1.eligible_bowlers) == 11

    assert match.current_innings is match.innings_1
    assert match.current_bowling_state is match.bowling_1
    assert match.innings_1_score == 0
    assert match.innings_1_wickets == 0

    assert match.innings_2 is None
    assert match.bowling_2 is None
    assert match.target is None


# ===========================================================================
# Section 3: Invalid Lifecycle Operations (Requirement C)
# ===========================================================================


def test_cannot_process_ball_before_match_starts():
    """Requirement C: Processing a ball before match start raises MatchLifecycleError."""
    match = Match()
    ball = resolve_ball(4, 2)
    with pytest.raises(MatchLifecycleError, match="match has not started"):
        match.record_ball(ball)

    with pytest.raises(MatchLifecycleError, match="match has not started"):
        match.resolve_and_record_ball(4, 2)


def test_cannot_select_bowler_before_match_starts():
    """Requirement C: Selecting a bowler before match start raises MatchLifecycleError."""
    match = Match()
    with pytest.raises(MatchLifecycleError, match="match has not started"):
        match.select_bowler(1)


def test_cannot_start_innings_2_before_match_starts():
    """Requirement C: Starting innings 2 before match start raises MatchLifecycleError."""
    match = Match()
    with pytest.raises(MatchLifecycleError, match="match has not started"):
        match.start_innings_2()


def test_cannot_start_innings_1_twice():
    """Requirement C: Starting innings 1 when already in progress raises MatchLifecycleError."""
    match = Match()
    match.start_match()
    with pytest.raises(MatchLifecycleError, match="already in state INNINGS_1"):
        match.start_innings_1()


def test_cannot_record_non_ball_result():
    """Type safety: record_ball rejects non-BallResult instances."""
    match = Match()
    match.start_match()
    match.select_bowler(1)
    with pytest.raises(TypeError, match="Expected BallResult instance"):
        match.record_ball("4")  # type: ignore


# ===========================================================================
# Section 4: Bowler Selection & Over Coordination (Requirements I, J, K, L, M, N)
# ===========================================================================


def test_bowler_must_be_selected_before_processing_ball():
    """Requirement I: Processing a ball without an active bowler raises BowlerSelectionError."""
    match = Match()
    match.start_match()

    assert match.current_bowling_state.is_over_active is False

    with pytest.raises(BowlerSelectionError, match="no bowler has been selected for Over 1"):
        match.resolve_and_record_ball(4, 2)


def test_ball_processing_delegates_correctly_to_innings():
    """Requirement J: Runs, balls, and wickets delegate to Innings."""
    match = Match()
    match.start_match()
    match.select_bowler(5)

    res = match.resolve_and_record_ball(4, 2)
    assert res.runs == 4
    assert res.is_wicket is False

    assert match.innings_1_score == 4
    assert match.innings_1_wickets == 0
    assert match.innings_1.balls_in_current_over == 1
    assert match.innings_1.total_balls == 1


def test_over_transition_requires_new_bowler():
    """Requirement K: Over completion clears bowler and requires new selection for next over."""
    match = Match()
    match.start_match()
    match.select_bowler(1)

    # Bowl 6 balls to complete Over 1
    for _ in range(6):
        match.resolve_and_record_ball(2, 4)

    assert match.innings_1.current_over == 2
    assert match.innings_1.balls_in_current_over == 0
    assert match.bowling_1.completed_overs == 1
    assert match.bowling_1.active_bowler is None
    assert match.bowling_1.is_over_active is False

    # Ball 7 without selecting a bowler must raise BowlerSelectionError
    with pytest.raises(BowlerSelectionError, match="no bowler has been selected for Over 2"):
        match.resolve_and_record_ball(1, 3)


def test_used_bowler_cannot_bowl_again():
    """Requirement L: A bowler who already bowled cannot bowl another over."""
    match = Match()
    match.start_match()
    match.select_bowler(3)

    for _ in range(6):
        match.resolve_and_record_ball(1, 2)

    assert match.bowling_1.has_bowled(3) is True
    assert match.bowling_1.is_eligible(3) is False

    # Selecting bowler 3 again raises BowlerAlreadyBowledError from bowling domain
    with pytest.raises(BowlerAlreadyBowledError, match="Bowler 3 has already bowled"):
        match.select_bowler(3)


def test_five_unique_bowlers_complete_five_overs():
    """Requirement M & N: 5 distinct bowlers complete 5 overs; 6th over is rejected."""
    match = Match()
    match.start_match()

    bowlers = [1, 2, 3, 4, 5]
    for over_idx, bowler_id in enumerate(bowlers, start=1):
        match.select_bowler(bowler_id)
        assert match.bowling_1.active_bowler == bowler_id

        for _ in range(6):
            match.resolve_and_record_ball(1, 3)

        assert match.bowling_1.completed_overs == over_idx

    # Innings 1 is now complete after 30 balls
    assert match.innings_1.total_balls == 30
    assert match.innings_1.is_completed is True
    assert match.bowling_1.is_innings_bowling_complete is True

    # Cannot select a 6th bowler
    with pytest.raises(MatchLifecycleError, match="innings 1 is already complete"):
        match.select_bowler(6)


# ===========================================================================
# Section 5: Innings 1 Completion & Target (Requirements D, E, F, G, H, O, P)
# ===========================================================================


def test_innings_1_completion_by_30_balls_and_target_calculation():
    """Requirements D, E, F, P: 30-ball completion establishes target (runs + 1)."""
    match = Match()
    match.start_match()

    for bowler_id in range(1, 6):
        match.select_bowler(bowler_id)
        for _ in range(6):
            match.resolve_and_record_ball(2, 4)  # 2 runs * 30 = 60 runs

    assert match.innings_1.total_balls == 30
    assert match.innings_1.total_runs == 60
    assert match.innings_1.is_completed is True
    assert match.target == 61  # Target is strictly Innings 1 score + 1

    # Cannot process further balls in innings 1
    with pytest.raises(MatchLifecycleError, match="innings 1 is already complete. Start innings 2"):
        match.resolve_and_record_ball(1, 2)


def test_innings_1_completion_by_all_out():
    """Requirement O: All-out dismissal (10 wickets) completes Innings 1 early."""
    match = Match()
    match.start_match()
    match.select_bowler(1)

    # 10 wickets in a row (all 10 dismissable batsmen out)
    for _ in range(6):
        match.resolve_and_record_ball(1, 1)

    # Need 4 more wickets in Over 2
    match.select_bowler(2)
    for _ in range(4):
        match.resolve_and_record_ball(1, 1)

    assert match.innings_1.wickets == 10
    assert match.innings_1.is_completed is True
    assert match.innings_1.total_balls == 10
    assert match.innings_1.total_runs == 0
    assert match.target == 1  # 0 + 1 = 1

    # Bowling state terminal / inactive assertions
    assert match.bowling_1.active_bowler is None
    assert match.bowling_1.is_over_active is False
    assert match.bowling_1.completed_overs == 1  # Over 1 completed; partial Over 2 NOT completed
    assert match.bowling_1.has_bowled(1) is True
    assert match.bowling_1.has_bowled(2) is True


def test_cannot_start_innings_2_before_innings_1_completes():
    """Requirement G: Calling start_innings_2 while Innings 1 is in progress raises InningsTransitionError."""
    match = Match()
    match.start_match()
    match.select_bowler(1)
    match.resolve_and_record_ball(4, 2)

    assert match.innings_1.is_completed is False

    with pytest.raises(InningsTransitionError, match="innings 1 is still in progress"):
        match.start_innings_2()


def test_starting_innings_2_creates_independent_fresh_state():
    """Requirement H: Innings 2 has fresh Innings and BowlingState independent of Innings 1."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    # Score 20 runs in Innings 1
    _score_runs(match, 20)
    _bowl_wickets(match, 10)  # All out at 20 runs

    assert match.innings_1.is_completed is True
    assert match.target == 21

    # Transition to Innings 2
    match.start_innings_2()

    assert match.status == MatchStatus.INNINGS_2
    assert match.current_innings_number == 2
    assert match.batting_team == "Australia"
    assert match.bowling_team == "India"

    assert match.innings_2 is not None
    assert match.innings_2.total_runs == 0
    assert match.innings_2.wickets == 0
    assert match.innings_2.total_balls == 0
    assert match.innings_2.is_completed is False

    assert match.bowling_2 is not None
    assert match.bowling_2.completed_overs == 0
    assert len(match.bowling_2.eligible_bowlers) == 11
    # Bowler 1 is eligible again because this is Australia bowling now!
    assert match.bowling_2.is_eligible(1) is True

    # Innings 1 state is preserved and unaltered
    assert match.innings_1.total_runs == 20
    assert match.innings_1.wickets == 10

    # Cannot start innings 2 twice
    with pytest.raises(MatchLifecycleError, match="innings 2 has already started"):
        match.start_innings_2()


# ===========================================================================
# Section 6: Target Chasing & Immediate Match Termination (Requirements Q, R, V)
# ===========================================================================


def test_target_chase_ends_immediately_when_target_reached():
    """Requirements Q & V: Innings 2 terminates immediately upon reaching target."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    # Innings 1 scores 17 runs
    _score_runs(match, 17)
    _bowl_wickets(match, 10)

    assert match.innings_1_score == 17
    assert match.target == 18

    match.start_innings_2()
    match.select_bowler(1)

    # Ball 1: 6 runs (score = 6)
    match.resolve_and_record_ball(6, 2)
    assert match.status == MatchStatus.INNINGS_2
    assert match.is_completed is False

    # Ball 2: 6 runs (score = 12)
    match.resolve_and_record_ball(6, 2)
    assert match.status == MatchStatus.INNINGS_2
    assert match.is_completed is False

    # Ball 3: 6 runs (score = 18 >= target 18) -> IMMEDIATE COMPLETION
    match.resolve_and_record_ball(6, 2)

    assert match.status == MatchStatus.COMPLETED
    assert match.is_completed is True
    assert match.innings_2_score == 18
    assert match.innings_2.total_balls == 3  # Match ended on ball 3!
    assert match.winner == "Australia"
    assert match.is_tie is False
    assert "Australia won by 10 wickets" in match.result_description


def test_target_chase_does_not_continue_after_target():
    """Requirements R & X: Cannot process ball after match completed."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()
    _score_runs(match, 5)
    _bowl_wickets(match, 10)

    match.start_innings_2()
    match.select_bowler(1)
    match.resolve_and_record_ball(6, 1)  # 6 runs >= target 6 -> Completed!

    assert match.is_completed is True

    with pytest.raises(MatchLifecycleError, match="match is already completed"):
        match.resolve_and_record_ball(2, 3)

    with pytest.raises(MatchLifecycleError, match="match is already completed"):
        match.select_bowler(2)


def test_target_exceeded_by_boundary():
    """Target is exceeded on a single scoring shot (e.g. 16 runs chases target 18 with a 6 -> 22 runs)."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()
    _score_runs(match, 17)
    _bowl_wickets(match, 10)
    assert match.target == 18

    match.start_innings_2()
    match.select_bowler(1)
    # Score 16 runs (two 6s and a 4)
    match.resolve_and_record_ball(6, 1)
    match.resolve_and_record_ball(6, 1)
    match.resolve_and_record_ball(4, 1)
    assert match.innings_2_score == 16

    # Hit 6 -> score becomes 22 >= 18
    match.resolve_and_record_ball(6, 1)

    assert match.is_completed is True
    assert match.innings_2_score == 22
    assert match.winner == "Australia"


# ===========================================================================
# Section 7: Innings 2 Failure Scenarios & Winners (Requirements S, T, U, W, Y)
# ===========================================================================


def test_innings_2_all_out_under_target_team_1_wins():
    """Requirements T & U: Innings 2 is all out before reaching target; Team 1 wins."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    _score_runs(match, 30)
    _bowl_wickets(match, 10)
    assert match.target == 31

    match.start_innings_2()
    # Score 15 runs then lose 10 wickets
    _score_runs(match, 15)
    _bowl_wickets(match, 10)

    assert match.is_completed is True
    assert match.status == MatchStatus.COMPLETED
    assert match.innings_2_score == 15
    assert match.winner == "India"
    assert match.is_tie is False
    assert "India won by 15 runs" in match.result_description


def test_innings_2_exhausts_30_balls_under_target_team_1_wins():
    """Requirement S & U: Innings 2 bowls 30 balls without reaching target; Team 1 wins."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    _score_runs(match, 50)
    _bowl_wickets(match, 10)
    assert match.target == 51

    match.start_innings_2()
    # Bowl 30 balls scoring 1 run each = 30 runs < 50
    for bowler_id in range(1, 6):
        match.select_bowler(bowler_id)
        for _ in range(6):
            match.resolve_and_record_ball(1, 2)

    assert match.innings_2.total_balls == 30
    assert match.innings_2_score == 30
    assert match.is_completed is True
    assert match.winner == "India"
    assert match.is_tie is False
    assert "India won by 20 runs" in match.result_description


def test_tie_when_innings_2_equals_innings_1_on_all_out():
    """Requirement W: Innings 2 gets all out with score exactly equal to Innings 1 -> Tie."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    _score_runs(match, 20)
    _bowl_wickets(match, 10)
    assert match.innings_1_score == 20
    assert match.target == 21

    match.start_innings_2()
    _score_runs(match, 20)  # Equals Innings 1 score
    _bowl_wickets(match, 10)  # All out

    assert match.is_completed is True
    assert match.winner is None
    assert match.is_tie is True
    assert "Match tied (20 - 20)" in match.result_description


def test_tie_when_innings_2_equals_innings_1_on_ball_30():
    """Requirement W: Innings 2 reaches 30 balls with score exactly equal to Innings 1 -> Tie."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    # Innings 1 scores 30 runs (1 run per ball * 30 balls)
    for b in range(1, 6):
        match.select_bowler(b)
        for _ in range(6):
            match.resolve_and_record_ball(1, 2)

    assert match.innings_1_score == 30
    assert match.target == 31

    match.start_innings_2()
    # Innings 2 also scores 30 runs in 30 balls
    for b in range(1, 6):
        match.select_bowler(b)
        for _ in range(6):
            match.resolve_and_record_ball(1, 2)

    assert match.innings_2.total_balls == 30
    assert match.innings_2_score == 30
    assert match.is_completed is True
    assert match.winner is None
    assert match.is_tie is True
    assert "Match tied (30 - 30)" in match.result_description


# ===========================================================================
# Section 8: Specific Edge Cases
# ===========================================================================


def test_target_equals_one_edge_case():
    """Edge case: Target is 1 (Innings 1 all-out for 0); chase finishes on Ball 1."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    # 10 wickets in a row with 0 runs
    _bowl_wickets(match, 10)
    assert match.innings_1_score == 0
    assert match.target == 1

    match.start_innings_2()
    match.select_bowler(1)

    # Ball 1 scores 1 run -> immediate match completion!
    match.resolve_and_record_ball(1, 2)

    assert match.is_completed is True
    assert match.innings_2.total_balls == 1
    assert match.innings_2_score == 1
    assert match.winner == "Australia"


def test_target_reached_on_ball_30_final_ball():
    """Edge case: Target reached on the very last ball of Innings 2 (Ball 30)."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()
    _score_runs(match, 30)
    _bowl_wickets(match, 10)
    assert match.target == 31

    match.start_innings_2()
    # Bowl 29 balls scoring 1 run each = 29 runs
    for b in range(1, 5):
        match.select_bowler(b)
        for _ in range(6):
            match.resolve_and_record_ball(1, 2)

    # Over 5: bowl 5 balls (balls 25 to 29)
    match.select_bowler(5)
    for _ in range(5):
        match.resolve_and_record_ball(1, 2)

    assert match.innings_2.total_balls == 29
    assert match.innings_2_score == 29
    assert match.is_completed is False

    # Ball 30: score 2 runs -> 31 runs >= target 31!
    match.resolve_and_record_ball(2, 4)

    assert match.innings_2.total_balls == 30
    assert match.innings_2_score == 31
    assert match.is_completed is True
    assert match.winner == "Australia"


def test_wicket_on_ball_30_ends_innings_1():
    """Edge case: Wicket falls on Ball 30 of Innings 1 (over 5 ball 6)."""
    match = Match()
    match.start_match()

    for b in range(1, 5):
        match.select_bowler(b)
        for _ in range(6):
            match.resolve_and_record_ball(2, 4)

    match.select_bowler(5)
    for _ in range(5):
        match.resolve_and_record_ball(2, 4)

    # Ball 30 is a wicket
    match.resolve_and_record_ball(3, 3)

    assert match.innings_1.total_balls == 30
    assert match.innings_1.wickets == 1
    assert match.innings_1.is_completed is True
    assert match.bowling_1.is_innings_bowling_complete is True


def test_target_reached_on_over_boundary():
    """Edge case: Target reached exactly on the 6th ball of an over."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()
    _score_runs(match, 11)
    _bowl_wickets(match, 10)
    assert match.target == 12

    match.start_innings_2()
    match.select_bowler(1)
    for _ in range(6):
        match.resolve_and_record_ball(2, 4)  # 6 balls * 2 runs = 12 runs

    assert match.innings_2.total_balls == 6
    assert match.innings_2_score == 12
    assert match.is_completed is True
    assert match.winner == "Australia"
    # Over was completed in bowling state
    assert match.bowling_2.completed_overs == 1


# ===========================================================================
# Section 9: Encapsulation & Read-Only Protection (Requirement Z)
# ===========================================================================


def test_innings_view_mutation_protection():
    """Requirement Z: InningsView omits record_ball to prevent mutation bypass."""
    match = Match()
    match.start_match()

    view = match.innings_1
    assert isinstance(view, InningsView)
    assert not hasattr(view, "record_ball")

    with pytest.raises(AttributeError):
        view.record_ball(resolve_ball(1, 2))  # type: ignore


def test_match_view_mutation_protection():
    """Requirement Z: MatchView exposes query properties but omits mutators."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()
    match.select_bowler(1)

    view = match.as_view()
    assert isinstance(view, MatchView)

    assert view.status == MatchStatus.INNINGS_1
    assert view.team_1 == "India"
    assert view.team_2 == "Australia"
    assert view.current_innings_number == 1
    assert view.innings_1 is not None
    assert view.bowling_1 is not None

    # Mutator methods omitted from view
    assert not hasattr(view, "start_match")
    assert not hasattr(view, "start_innings_1")
    assert not hasattr(view, "start_innings_2")
    assert not hasattr(view, "select_bowler")
    assert not hasattr(view, "record_ball")
    assert not hasattr(view, "resolve_and_record_ball")

    with pytest.raises(AttributeError):
        view.select_bowler(2)  # type: ignore

    with pytest.raises(AttributeError):
        view.record_ball(resolve_ball(1, 2))  # type: ignore


def test_match_repr():
    """Verify clean repr strings on Match and MatchView."""
    match = Match(team_1="India", team_2="Australia")
    assert "Match(status=NOT_STARTED" in repr(match)

    view = match.as_view()
    assert "MatchView(Match(" in repr(view)


def test_post_completion_lifecycle_rejections():
    """Post-completion rejects all state mutations (start_innings_1, start_innings_2, select_bowler, record_ball)."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()
    _score_runs(match, 5)
    _bowl_wickets(match, 10)

    match.start_innings_2()
    match.select_bowler(1)
    match.resolve_and_record_ball(6, 1)  # 6 runs >= target 6 -> COMPLETED

    assert match.is_completed is True
    assert match.status == MatchStatus.COMPLETED

    with pytest.raises(MatchLifecycleError, match="already in state COMPLETED"):
        match.start_innings_1()

    with pytest.raises(MatchLifecycleError, match="match is already completed"):
        match.start_innings_2()

    with pytest.raises(MatchLifecycleError, match="match is already completed"):
        match.select_bowler(2)

    with pytest.raises(MatchLifecycleError, match="match is already completed"):
        match.record_ball(resolve_ball(1, 2))


def test_custom_configuration_match():
    """Verify match with custom configuration (e.g. 3 players, 2 overs, 4 balls/over)."""
    match = Match(
        team_1="Alpha",
        team_2="Beta",
        team_size=3,
        max_overs=2,
        balls_per_over=4,
    )
    assert match.team_size == 3
    assert match.max_overs == 2
    assert match.balls_per_over == 4
    assert match.max_balls == 8

    match.start_match()
    match.select_bowler(1)
    for _ in range(4):
        match.resolve_and_record_ball(2, 1)  # 8 runs

    match.select_bowler(2)
    for _ in range(4):
        match.resolve_and_record_ball(2, 1)  # 8 runs -> 16 runs total

    assert match.innings_1.total_balls == 8
    assert match.innings_1.is_completed is True
    assert match.innings_1_score == 16
    assert match.target == 17

    match.start_innings_2()
    match.select_bowler(3)
    for _ in range(4):
        match.resolve_and_record_ball(4, 1)  # 16 runs

    match.select_bowler(1)
    # Ball 5: 1 run -> 17 runs >= target 17 -> Beta wins!
    match.resolve_and_record_ball(1, 2)

    assert match.is_completed is True
    assert match.winner == "Beta"
    assert match.innings_2.total_balls == 5


# ===========================================================================
# Section 10: Bowling State Terminal / Inactive Synchronization (F1 Hardening)
# ===========================================================================


def test_innings_1_all_out_mid_over_deactivates_bowler():
    """Innings 1 all-out mid-over clears active_bowler and leaves completed_overs un-incremented."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    # Over 1: Bowler 1 bowls full over, taking 6 wickets
    match.select_bowler(1)
    for _ in range(6):
        match.resolve_and_record_ball(1, 1)

    assert match.innings_1.wickets == 6
    assert match.bowling_1.completed_overs == 1
    assert match.bowling_1.active_bowler is None
    assert match.bowling_1.is_over_active is False

    # Over 2: Bowler 2 takes 4 wickets on balls 1..4 -> 10 wickets, all-out!
    match.select_bowler(2)
    assert match.bowling_1.is_over_active is True
    assert match.bowling_1.active_bowler == 2

    for _ in range(4):
        match.resolve_and_record_ball(1, 1)

    # Innings 1 is now completed by all-out on ball 4 of Over 2
    assert match.innings_1.is_completed is True
    assert match.innings_1.total_balls == 10
    assert match.innings_1.wickets == 10

    # BowlingState 1 MUST be inactive:
    assert match.bowling_1.active_bowler is None
    assert match.bowling_1.is_over_active is False
    # Partial over 2 is NOT counted as a completed over
    assert match.bowling_1.completed_overs == 1
    # Bowler 2 remains marked as used
    assert match.bowling_1.has_bowled(2) is True
    assert match.bowling_1.is_eligible(2) is False

    # Inactive state persists after transition to Innings 2
    match.start_innings_2()
    assert match.bowling_1.active_bowler is None
    assert match.bowling_1.is_over_active is False
    assert match.bowling_1.completed_overs == 1


def test_innings_2_all_out_mid_over_deactivates_bowler():
    """Innings 2 all-out mid-over clears active_bowler and leaves completed_overs un-incremented."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    # Score 50 runs in Innings 1, then all out
    _score_runs(match, 50)
    _bowl_wickets(match, 10)
    assert match.target == 51

    match.start_innings_2()

    # Over 1 in Innings 2: Bowler 1 bowls full over, taking 6 wickets
    match.select_bowler(1)
    for _ in range(6):
        match.resolve_and_record_ball(1, 1)

    assert match.innings_2.wickets == 6
    assert match.bowling_2.completed_overs == 1
    assert match.bowling_2.active_bowler is None
    assert match.bowling_2.is_over_active is False

    # Over 2 in Innings 2: Bowler 2 takes 4 wickets -> all out on ball 4!
    match.select_bowler(2)
    assert match.bowling_2.is_over_active is True
    assert match.bowling_2.active_bowler == 2

    for _ in range(4):
        match.resolve_and_record_ball(1, 1)

    # Match terminates with Team 1 winning
    assert match.is_completed is True
    assert match.status == MatchStatus.COMPLETED
    assert match.innings_2.is_completed is True
    assert match.innings_2.wickets == 10
    assert match.winner == "India"

    # BowlingState 2 MUST be inactive:
    assert match.bowling_2.active_bowler is None
    assert match.bowling_2.is_over_active is False
    # Partial over 2 is NOT counted as completed
    assert match.bowling_2.completed_overs == 1
    assert match.bowling_2.has_bowled(2) is True
    assert match.bowling_2.is_eligible(2) is False


def test_preserve_normal_over_behavior():
    """Normal 6-ball over increments completed_overs, deactivates bowler, and requires new selection."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    match.select_bowler(5)
    assert match.bowling_1.active_bowler == 5
    assert match.bowling_1.is_over_active is True
    assert match.bowling_1.completed_overs == 0

    # Bowl 6 normal balls
    for _ in range(6):
        match.resolve_and_record_ball(2, 4)

    # Over completes normally:
    assert match.innings_1.current_over == 2
    assert match.bowling_1.completed_overs == 1
    assert match.bowling_1.active_bowler is None
    assert match.bowling_1.is_over_active is False
    assert match.bowling_1.has_bowled(5) is True

    # Next ball strictly requires a new bowler selection
    with pytest.raises(BowlerSelectionError, match="no bowler has been selected for Over 2"):
        match.resolve_and_record_ball(1, 3)

    # Selecting eligible bowler succeeds and restores active over
    match.select_bowler(3)
    assert match.bowling_1.active_bowler == 3
    assert match.bowling_1.is_over_active is True


def test_target_reached_mid_over_clears_bowling_active_state():
    """Target reached mid-over terminates match and clears active_bowler without incrementing completed_overs."""
    match = Match(team_1="India", team_2="Australia")
    match.start_match()

    # Innings 1 all out for 5 runs (target = 6)
    _score_runs(match, 5)
    _bowl_wickets(match, 10)
    assert match.target == 6

    match.start_innings_2()
    match.select_bowler(1)

    # Ball 1 scores 6 runs -> immediate match completion on ball 1 of Over 1!
    match.resolve_and_record_ball(6, 2)

    assert match.is_completed is True
    assert match.status == MatchStatus.COMPLETED
    assert match.winner == "Australia"
    assert match.innings_2.total_balls == 1

    # BowlingState 2 is inactive and partial over is NOT completed:
    assert match.bowling_2.active_bowler is None
    assert match.bowling_2.is_over_active is False
    assert match.bowling_2.completed_overs == 0
    assert match.bowling_2.has_bowled(1) is True
    assert match.bowling_2.is_eligible(1) is False
