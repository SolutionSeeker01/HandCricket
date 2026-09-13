"""Automated tests for the Predefined Teams & Players domain engine (Slice 7)."""

from dataclasses import FrozenInstanceError
import pytest

from backend.app.engine.teams import (
    InvalidTeamError,
    Player,
    Team,
    TeamNotFoundError,
    get_team,
    get_teams,
    is_valid_team_id,
)


# ===========================================================================
# 1. Predefined Teams Verification (Requirements 1 - 5)
# ===========================================================================


def test_exactly_four_predefined_teams_exist():
    """Requirement 1: System provides exactly 4 predefined teams."""
    teams = get_teams()
    assert len(teams) == 4


def test_every_team_has_exactly_eleven_players():
    """Requirement 2: Every predefined team has exactly 11 players."""
    for team in get_teams():
        assert len(team.players) == 11
        for p in team.players:
            assert isinstance(p, Player)
            assert isinstance(p.id, int)
            assert isinstance(p.name, str)
            assert len(p.name.strip()) > 0


def test_team_ids_are_unique():
    """Requirement 3: Predefined team IDs are distinct."""
    teams = get_teams()
    ids = [team.id for team in teams]
    assert len(ids) == len(set(ids))
    assert set(ids) == {"IND", "AUS", "ENG", "SA"}


def test_player_ids_are_unique_within_each_team():
    """Requirement 4: Player IDs within each team are 1..11 without duplicates."""
    for team in get_teams():
        player_ids = [p.id for p in team.players]
        assert len(player_ids) == 11
        assert sorted(player_ids) == list(range(1, 12))


def test_team_names_are_present_and_deterministic():
    """Requirement 5: Team names are non-empty strings and deterministic."""
    expected_names = {
        "IND": "India",
        "AUS": "Australia",
        "ENG": "England",
        "SA": "South Africa",
    }
    teams = get_teams()
    for team in teams:
        assert team.id in expected_names
        assert team.name == expected_names[team.id]


# ===========================================================================
# 2. Team Lookup & Query Verification (Requirement 6)
# ===========================================================================


@pytest.mark.parametrize(
    "team_id,expected_name",
    [
        ("IND", "India"),
        ("ind", "India"),
        ("  InD  ", "India"),
        ("AUS", "Australia"),
        ("aus", "Australia"),
        ("ENG", "England"),
        ("eng", "England"),
        ("SA", "South Africa"),
        ("sa", "South Africa"),
    ],
)
def test_valid_team_lookup_case_insensitive(team_id, expected_name):
    """get_team retrieves team by ID case-insensitively with whitespace stripped."""
    team = get_team(team_id)
    assert team.name == expected_name


@pytest.mark.parametrize("invalid_id", ["NZ", "PAK", "USA", "", "   ", "123", None, 12, True])
def test_unknown_team_lookup_raises_team_not_found(invalid_id):
    """Requirement 6: Unknown or invalid team identifiers raise TeamNotFoundError."""
    with pytest.raises(TeamNotFoundError):
        get_team(invalid_id)  # type: ignore


def test_is_valid_team_id():
    """is_valid_team_id returns True for valid team IDs and False otherwise."""
    assert is_valid_team_id("IND") is True
    assert is_valid_team_id("ind") is True
    assert is_valid_team_id("AUS") is True
    assert is_valid_team_id("ENG") is True
    assert is_valid_team_id("SA") is True

    assert is_valid_team_id("NZ") is False
    assert is_valid_team_id("") is False
    assert is_valid_team_id(None) is False
    assert is_valid_team_id(123) is False


def test_get_player_by_id():
    """Team.get_player retrieves a player by 1-indexed ID or returns None."""
    ind = get_team("IND")
    p1 = ind.get_player(1)
    assert p1 is not None
    assert p1.id == 1
    assert p1.name == "Rohit Sharma"

    p_none = ind.get_player(99)
    assert p_none is None


# ===========================================================================
# 3. Immutability & Mutation Protection (Requirements 7, 26)
# ===========================================================================


def test_returned_team_list_cannot_mutate_source():
    """Requirement 7: Mutating the list returned by get_teams does not affect source data."""
    teams_1 = get_teams()
    teams_1.clear()

    teams_2 = get_teams()
    assert len(teams_2) == 4


def test_player_dataclass_is_frozen():
    """Requirement 26: Mutating Player fields raises FrozenInstanceError."""
    player = Player(1, "Test Player")
    with pytest.raises(FrozenInstanceError):
        player.name = "Modified"  # type: ignore

    with pytest.raises(FrozenInstanceError):
        player.id = 2  # type: ignore


def test_team_dataclass_is_frozen():
    """Requirement 26: Mutating Team fields raises FrozenInstanceError."""
    team = get_team("IND")
    with pytest.raises(FrozenInstanceError):
        team.name = "Modified"  # type: ignore

    with pytest.raises(FrozenInstanceError):
        team.id = "XYZ"  # type: ignore

    with pytest.raises(FrozenInstanceError):
        team.players = ()  # type: ignore


# ===========================================================================
# 4. Data Model Structural Validation
# ===========================================================================


@pytest.mark.parametrize("bad_id", [0, -1, True, False, "1", None])
def test_player_rejects_invalid_id(bad_id):
    """Player rejects non-positive-integer IDs."""
    with pytest.raises(InvalidTeamError):
        Player(id=bad_id, name="Test")  # type: ignore


@pytest.mark.parametrize("bad_name", ["", "   ", None, 123])
def test_player_rejects_invalid_name(bad_name):
    """Player rejects empty or non-string names."""
    with pytest.raises(InvalidTeamError):
        Player(id=1, name=bad_name)  # type: ignore


def test_team_rejects_wrong_player_count():
    """Team rejects rosters with fewer or more than 11 players."""
    ten_players = tuple(Player(i, f"P{i}") for i in range(1, 11))
    with pytest.raises(InvalidTeamError, match="exactly 11 players"):
        Team(id="TEST", name="Test Team", players=ten_players)

    twelve_players = tuple(Player(i, f"P{i}") for i in range(1, 13))
    with pytest.raises(InvalidTeamError, match="exactly 11 players"):
        Team(id="TEST", name="Test Team", players=twelve_players)


def test_team_rejects_duplicate_player_ids():
    """Team rejects rosters with duplicate player IDs."""
    dup_players = tuple(Player(1, f"P{i}") for i in range(1, 12))  # all have id=1
    with pytest.raises(InvalidTeamError, match="Duplicate player ID"):
        Team(id="TEST", name="Test Team", players=dup_players)


def test_team_rejects_non_tuple_players():
    """Team rejects non-tuple player collections."""
    eleven_list = [Player(i, f"P{i}") for i in range(1, 12)]
    with pytest.raises(InvalidTeamError, match="immutable tuple"):
        Team(id="TEST", name="Test Team", players=eleven_list)  # type: ignore
