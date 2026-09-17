"""Automated tests for the Pre-Match Setup and Participant Coordination engine (Slice 7)."""

import pytest

from backend.app.engine.match import Match
from backend.app.engine.pre_match import (
    PreMatchError,
    PreMatchSetup,
)
from backend.app.engine.teams import (
    Team,
    TeamNotFoundError,
    get_team,
)
from backend.app.engine.toss import (
    InvalidParticipantError,
    Participant,
    TossDecision,
    TossStatus,
)


# ===========================================================================
# 1. Participant Team Selection (Requirements 8, 9, 10, 11, 12, 13, 27, 28)
# ===========================================================================


def test_participant_a_can_select_any_valid_team():
    """Requirement 9: Participant A can select any of the 4 predefined teams."""
    for team_id in ["IND", "AUS", "ENG", "SA"]:
        setup = PreMatchSetup()
        selected = setup.select_team(Participant.A, team_id)
        assert isinstance(selected, Team)
        assert setup.team_a == selected
        assert setup.get_team_for_participant(Participant.A) == selected


def test_participant_b_can_select_any_valid_team():
    """Requirement 10: Participant B can select any of the 4 predefined teams."""
    for team_id in ["IND", "AUS", "ENG", "SA"]:
        setup = PreMatchSetup()
        selected = setup.select_team(Participant.B, team_id)
        assert isinstance(selected, Team)
        assert setup.team_b == selected
        assert setup.get_team_for_participant(Participant.B) == selected


def test_duplicate_team_selection_is_prohibited():
    """Cleanup #2: Participant A and B cannot select the same team."""
    setup = PreMatchSetup()
    team_a = setup.select_team(Participant.A, "IND")
    assert setup.team_a.id == "IND"

    with pytest.raises(PreMatchError) as exc_info:
        setup.select_team(Participant.B, "IND")
    assert "has already been selected" in str(exc_info.value)


def test_all_four_teams_can_be_selected_successfully():
    """Requirement 28: All 4 predefined teams are successfully selectable."""
    setup_1 = PreMatchSetup(team_a="IND", team_b="AUS")
    assert setup_1.team_a.id == "IND"
    assert setup_1.team_b.id == "AUS"

    setup_2 = PreMatchSetup(team_a="ENG", team_b="SA")
    assert setup_2.team_a.id == "ENG"
    assert setup_2.team_b.id == "SA"


@pytest.mark.parametrize("invalid_team", ["NZ", "PAK", "", "123", None, 99])
def test_invalid_team_selection_fails(invalid_team):
    """Requirement 11: Selecting an invalid or unknown team raises TeamNotFoundError."""
    setup = PreMatchSetup()
    with pytest.raises(TeamNotFoundError):
        setup.select_team(Participant.A, invalid_team)  # type: ignore


@pytest.mark.parametrize("invalid_participant", ["C", "X", "", None, 1, True])
def test_invalid_participant_identity_fails(invalid_participant):
    """Requirement 13: Attempting to assign or query unsupported participant raises InvalidParticipantError."""
    setup = PreMatchSetup()
    with pytest.raises(InvalidParticipantError):
        setup.select_team(invalid_participant, "IND")  # type: ignore

    with pytest.raises(InvalidParticipantError):
        setup.get_team_for_participant(invalid_participant)  # type: ignore


def test_select_team_accepts_team_object_or_string():
    """select_team accepts either a Team dataclass instance or a string team ID."""
    ind_team = get_team("IND")
    setup = PreMatchSetup()
    setup.select_team("A", ind_team)
    setup.select_team("B", "aus")

    assert setup.team_a.name == "India"
    assert setup.team_b.name == "Australia"


def test_team_selection_and_reselection_before_toss_works():
    """Teams can be selected and changed freely before the toss starts."""
    setup = PreMatchSetup()
    setup.select_team(Participant.A, "IND")
    assert setup.team_a.id == "IND"

    # Changing team before toss is permitted
    setup.select_team(Participant.A, "SA")
    assert setup.team_a.id == "SA"


def test_public_api_does_not_expose_mutable_toss():
    """Regression test: PreMatchSetup does NOT expose the mutable Toss instance."""
    setup = PreMatchSetup()
    assert not hasattr(setup, "toss")
    assert not hasattr(PreMatchSetup, "toss")


def test_cannot_change_team_a_after_flip_toss():
    """Attempting to change Participant A's team after toss flip raises PreMatchError."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.A,
    )
    setup.flip_toss()

    with pytest.raises(PreMatchError, match="toss is already in state AWAITING_DECISION"):
        setup.select_team(Participant.A, "SA")


def test_cannot_change_team_b_after_flip_toss():
    """Attempting to change Participant B's team after toss flip raises PreMatchError."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.A,
    )
    setup.flip_toss()

    with pytest.raises(PreMatchError, match="toss is already in state AWAITING_DECISION"):
        setup.select_team(Participant.B, "ENG")


def test_cannot_change_either_team_after_choose_toss():
    """Attempting to change either team after toss decision is finalized raises PreMatchError."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.A,
    )
    setup.flip_toss()
    setup.choose_toss(TossDecision.BAT, by=Participant.A)

    with pytest.raises(PreMatchError, match="toss is already in state COMPLETED"):
        setup.select_team(Participant.A, "SA")

    with pytest.raises(PreMatchError, match="toss is already in state COMPLETED"):
        setup.select_team(Participant.B, "ENG")


# ===========================================================================
# 2. Toss Workflow through PreMatchSetup
# ===========================================================================


def test_toss_coordination_through_setup():
    """PreMatchSetup coordinates toss flip and decision making cleanly."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.A,
    )
    assert setup.toss_status == TossStatus.NOT_STARTED
    assert setup.is_ready_for_match is False

    winner = setup.flip_toss()
    assert winner == Participant.A
    assert setup.toss_winner == Participant.A
    assert setup.toss_status == TossStatus.AWAITING_DECISION
    assert setup.is_ready_for_match is False

    # Participant A chooses BAT
    result = setup.choose_toss(TossDecision.BAT, by=Participant.A)
    assert result.decision == TossDecision.BAT
    assert setup.toss_status == TossStatus.COMPLETED
    assert setup.is_ready_for_match is True


# ===========================================================================
# 3. First-Innings Team Derivation
# ===========================================================================


def test_first_innings_teams_when_a_wins_and_bats():
    """A (India) wins toss and chooses BAT -> India bats first, Australia bowls first."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.A,
    )
    setup.flip_toss()
    setup.choose_toss("BAT", by="A")

    assert setup.batting_first_participant == Participant.A
    assert setup.bowling_first_participant == Participant.B
    assert setup.first_bowler_selector_participant == Participant.B

    assert setup.batting_first_team.name == "India"
    assert setup.bowling_first_team.name == "Australia"
    assert setup.first_bowler_selector_team.name == "Australia"


def test_first_innings_teams_when_a_wins_and_bowls():
    """A (India) wins toss and chooses BOWL -> Australia bats first, India bowls first."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.A,
    )
    setup.flip_toss()
    setup.choose_toss("BOWL", by="A")

    assert setup.batting_first_participant == Participant.B
    assert setup.bowling_first_participant == Participant.A
    assert setup.first_bowler_selector_participant == Participant.A

    assert setup.batting_first_team.name == "Australia"
    assert setup.bowling_first_team.name == "India"
    assert setup.first_bowler_selector_team.name == "India"


def test_first_innings_teams_when_b_wins_and_bats():
    """B (Australia) wins toss and chooses BAT -> Australia bats first, India bowls first."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.B,
    )
    setup.flip_toss()
    setup.choose_toss("BAT", by="B")

    assert setup.batting_first_participant == Participant.B
    assert setup.bowling_first_participant == Participant.A
    assert setup.first_bowler_selector_participant == Participant.A

    assert setup.batting_first_team.name == "Australia"
    assert setup.bowling_first_team.name == "India"


def test_first_innings_teams_when_b_wins_and_bowls():
    """B (Australia) wins toss and chooses BOWL -> India bats first, Australia bowls first."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.B,
    )
    setup.flip_toss()
    setup.choose_toss("BOWL", by="B")

    assert setup.batting_first_participant == Participant.A
    assert setup.bowling_first_participant == Participant.B
    assert setup.first_bowler_selector_participant == Participant.B

    assert setup.batting_first_team.name == "India"
    assert setup.bowling_first_team.name == "Australia"


# ===========================================================================
# 4. Match Integration & Handover to Match Engine
# ===========================================================================


def test_create_match_premature_rejections():
    """create_match raises PreMatchError if teams or toss are incomplete."""
    # Case 1: No teams selected
    setup = PreMatchSetup()
    with pytest.raises(PreMatchError, match="both teams must be selected"):
        setup.create_match()

    # Case 2: Only one team selected
    setup.select_team("A", "IND")
    with pytest.raises(PreMatchError, match="both teams must be selected"):
        setup.create_match()

    # Case 3: Both teams selected, but toss not completed
    setup.select_team("B", "AUS")
    with pytest.raises(PreMatchError, match="toss decision must be completed"):
        setup.create_match()

    setup.flip_toss()
    with pytest.raises(PreMatchError, match="toss decision must be completed"):
        setup.create_match()


def test_create_match_produces_fully_configured_match():
    """create_match produces an initialized Match instance ready for execution."""
    setup = PreMatchSetup(
        team_a="IND",
        team_b="AUS",
        toss_chooser=lambda: Participant.A,
    )
    setup.flip_toss()
    setup.choose_toss("BAT", by="A")

    match = setup.create_match(max_overs=5, balls_per_over=6)
    assert isinstance(match, Match)

    # In Match engine, team_1 is batting first, team_2 is bowling first
    assert match.team_1 == "India"
    assert match.team_2 == "Australia"
    assert match.team_size == 11
    assert match.max_overs == 5
    assert match.balls_per_over == 6

    # Verify that the created match can execute normally
    match.start_match()
    assert match.batting_team == "India"
    assert match.bowling_team == "Australia"

    match.select_bowler(1)
    res = match.resolve_and_record_ball(4, 2)
    assert res.runs == 4
    assert match.innings_1_score == 4


def test_pre_match_constructor_rejects_same_teams():
    """Cleanup #2: PreMatchSetup constructor raises PreMatchError if same team passed."""
    with pytest.raises(PreMatchError) as exc_info:
        PreMatchSetup(
            team_a="IND",
            team_b="IND",
            toss_chooser=lambda: Participant.A,
        )
    assert "has already been selected" in str(exc_info.value)


def test_direct_match_engine_supports_same_team_names_until_cleanup_4():
    """Verify Match domain engine still handles same team names directly until Cleanup #4."""
    match = Match(team_1="India", team_2="India")
    assert match.team_1 == "India"
    assert match.team_2 == "India"
    match.start_match()
    assert match.batting_team == "India"
    assert match.bowling_team == "India"
