"""Predefined teams and player rosters domain engine for Hand Cricket.

This module defines the immutable data models for cricket teams and players,
provides the 4 frozen, predefined teams (11 players each), and exposes lookup
and validation functions.
"""

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


class TeamError(ValueError):
    """Base domain exception for team and player errors."""

    pass


class TeamNotFoundError(TeamError):
    """Raised when an unknown team identifier is requested."""

    pass


class InvalidTeamError(TeamError):
    """Raised when team data violates structural invariants."""

    pass


@dataclass(frozen=True)
class Player:
    """Immutable representation of a cricket player.

    Attributes:
        id: Integer identifier (1-indexed within team roster, 1..11).
        name: Full name of the player.
    """

    id: int
    name: str

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id < 1:
            raise InvalidTeamError(
                f"Invalid player id {self.id!r}: player ID must be an integer >= 1."
            )
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidTeamError(
                f"Invalid player name {self.name!r}: player name must be a non-empty string."
            )


@dataclass(frozen=True)
class Team:
    """Immutable representation of a predefined cricket team.

    Attributes:
        id: Stable unique uppercase identifier (e.g. 'IND', 'AUS').
        name: Full display name of the team (e.g. 'India', 'Australia').
        players: Tuple of exactly 11 Player instances.
    """

    id: str
    name: str
    players: Tuple[Player, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise InvalidTeamError(
                f"Invalid team id {self.id!r}: team ID must be a non-empty string."
            )
        if not isinstance(self.name, str) or not self.name.strip():
            raise InvalidTeamError(
                f"Invalid team name {self.name!r}: team name must be a non-empty string."
            )
        if not isinstance(self.players, tuple):
            raise InvalidTeamError(
                f"Invalid players collection {type(self.players).__name__}: must be an immutable tuple."
            )
        if len(self.players) != 11:
            raise InvalidTeamError(
                f"Team {self.id} must have exactly 11 players, got {len(self.players)}."
            )

        # Validate unique player IDs
        seen_ids = set()
        for player in self.players:
            if not isinstance(player, Player):
                raise InvalidTeamError(
                    f"Expected Player instance in roster, got {type(player).__name__}."
                )
            if player.id in seen_ids:
                raise InvalidTeamError(
                    f"Duplicate player ID {player.id} found in team {self.id}."
                )
            seen_ids.add(player.id)

    def get_player(self, player_id: int) -> Optional[Player]:
        """Retrieve a player by 1-indexed ID, or None if not found."""
        for player in self.players:
            if player.id == player_id:
                return player
        return None


# ---------------------------------------------------------------------------
# Predefined Immutable Team Rosters (Exactly 4 teams, exactly 11 players each)
# ---------------------------------------------------------------------------

_PREDEFINED_TEAMS: Tuple[Team, ...] = (
    Team(
        id="IND",
        name="India",
        players=(
            Player(1, "Rohit Sharma"),
            Player(2, "Shubman Gill"),
            Player(3, "Virat Kohli"),
            Player(4, "Shreyas Iyer"),
            Player(5, "KL Rahul"),
            Player(6, "Hardik Pandya"),
            Player(7, "Ravindra Jadeja"),
            Player(8, "Kuldeep Yadav"),
            Player(9, "Jasprit Bumrah"),
            Player(10, "Mohammed Shami"),
            Player(11, "Mohammed Siraj"),
        ),
    ),
    Team(
        id="AUS",
        name="Australia",
        players=(
            Player(1, "David Warner"),
            Player(2, "Travis Head"),
            Player(3, "Mitchell Marsh"),
            Player(4, "Steven Smith"),
            Player(5, "Marnus Labuschagne"),
            Player(6, "Glenn Maxwell"),
            Player(7, "Josh Inglis"),
            Player(8, "Pat Cummins"),
            Player(9, "Mitchell Starc"),
            Player(10, "Adam Zampa"),
            Player(11, "Josh Hazlewood"),
        ),
    ),
    Team(
        id="ENG",
        name="England",
        players=(
            Player(1, "Jonny Bairstow"),
            Player(2, "Dawid Malan"),
            Player(3, "Joe Root"),
            Player(4, "Ben Stokes"),
            Player(5, "Jos Buttler"),
            Player(6, "Liam Livingstone"),
            Player(7, "Moeen Ali"),
            Player(8, "Chris Woakes"),
            Player(9, "David Willey"),
            Player(10, "Adil Rashid"),
            Player(11, "Mark Wood"),
        ),
    ),
    Team(
        id="SA",
        name="South Africa",
        players=(
            Player(1, "Quinton de Kock"),
            Player(2, "Temba Bavuma"),
            Player(3, "Rassie van der Dussen"),
            Player(4, "Aiden Markram"),
            Player(5, "Heinrich Klaasen"),
            Player(6, "David Miller"),
            Player(7, "Marco Jansen"),
            Player(8, "Gerald Coetzee"),
            Player(9, "Keshav Maharaj"),
            Player(10, "Kagiso Rabada"),
            Player(11, "Lungi Ngidi"),
        ),
    ),
)


def get_teams() -> List[Team]:
    """Return a defensive copy list of the 4 predefined teams."""
    return list(_PREDEFINED_TEAMS)


def get_team(team_id: str) -> Team:
    """Retrieve a predefined team by ID (case-insensitive).

    Args:
        team_id: String team identifier (e.g. 'IND', 'aus').

    Returns:
        The matched immutable Team instance.

    Raises:
        TeamNotFoundError: If team_id is not recognized or not a string.
    """
    if not isinstance(team_id, str):
        raise TeamNotFoundError(
            f"Invalid team identifier {team_id!r}: must be a string."
        )

    normalized = team_id.strip().upper()
    for team in _PREDEFINED_TEAMS:
        if team.id == normalized:
            return team

    valid_ids = [t.id for t in _PREDEFINED_TEAMS]
    raise TeamNotFoundError(
        f"Unknown team ID {team_id!r}. Available teams: {valid_ids}."
    )


def is_valid_team_id(team_id: Any) -> bool:
    """Check whether team_id matches one of the 4 predefined teams."""
    if not isinstance(team_id, str):
        return False
    normalized = team_id.strip().upper()
    return any(t.id == normalized for t in _PREDEFINED_TEAMS)
