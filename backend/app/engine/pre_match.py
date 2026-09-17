"""Pre-match setup and participant coordination domain engine for Hand Cricket.

This module coordinates participant team selection (Participant A and B) and
toss execution, deterministically deriving the first-innings batting and bowling
teams and preparing the match for execution.
"""

from typing import Optional, Union

from backend.app.engine.match import Match
from backend.app.engine.teams import (
    Team,
    TeamNotFoundError,
    get_team,
    is_valid_team_id,
)
from backend.app.engine.toss import (
    InvalidParticipantError,
    Participant,
    Toss,
    TossChooser,
    TossDecision,
    TossResult,
    TossStatus,
)


class PreMatchError(ValueError):
    """Base domain exception for pre-match setup errors."""

    pass


class PreMatchSetup:
    """Coordinates team selection and toss mechanics prior to match execution.

    Invariants:
    - Participants are strictly Participant.A and Participant.B.
    - Each participant selects a valid predefined team.
    - Participant A and Participant B must select distinct teams (duplicate selection is prohibited).
    - Toss is managed via Toss engine.
    - Match cannot be started until both teams are selected and toss is completed.
    - All exposed team and toss objects are immutable.
    """

    def __init__(
        self,
        team_a: Optional[Union[Team, str]] = None,
        team_b: Optional[Union[Team, str]] = None,
        toss_chooser: Optional[TossChooser] = None,
    ) -> None:
        self._team_a: Optional[Team] = None
        self._team_b: Optional[Team] = None
        self._toss: Toss = Toss(chooser=toss_chooser)

        if team_a is not None:
            self.select_team(Participant.A, team_a)
        if team_b is not None:
            self.select_team(Participant.B, team_b)

    @property
    def team_a(self) -> Optional[Team]:
        """The team selected by Participant A, or None."""
        return self._team_a

    @property
    def team_b(self) -> Optional[Team]:
        """The team selected by Participant B, or None."""
        return self._team_b

    @property
    def toss_status(self) -> TossStatus:
        """Current status of the toss."""
        return self._toss.status

    @property
    def toss_winner(self) -> Optional[Participant]:
        """The winning participant of the toss, or None."""
        return self._toss.winner

    @property
    def toss_result(self) -> Optional[TossResult]:
        """Finalized immutable TossResult, or None."""
        return self._toss.result

    @property
    def is_teams_selected(self) -> bool:
        """True if both Participant A and B have selected teams."""
        return self._team_a is not None and self._team_b is not None

    @property
    def is_ready_for_match(self) -> bool:
        """True if both teams are selected and the toss decision is finalized."""
        return self.is_teams_selected and self._toss.is_completed

    def select_team(
        self, participant: Union[Participant, str], team: Union[Team, str]
    ) -> Team:
        """Assign a predefined team to Participant A or B.

        Args:
            participant: Participant.A or Participant.B (or string 'A' / 'B').
            team: Team instance or string team ID (e.g. 'IND', 'aus').

        Returns:
            The resolved Team instance.

        Raises:
            PreMatchError: If toss is already in progress or completed (team selection is locked),
                or if the team has already been selected by the other participant.
            InvalidParticipantError: If participant is invalid.
            TeamNotFoundError: If team is unknown or invalid.
        """
        if self._toss.status != TossStatus.NOT_STARTED:
            raise PreMatchError(
                f"Cannot select or change team: toss is already in state {self._toss.status.value}. "
                f"Team selection is locked."
            )

        # Normalize participant
        if isinstance(participant, str):
            try:
                participant = Participant(participant.strip().upper())
            except ValueError:
                raise InvalidParticipantError(
                    f"Invalid participant {participant!r}. Must be 'A' or 'B'."
                )
        elif not isinstance(participant, Participant):
            raise InvalidParticipantError(
                f"Expected Participant, got {type(participant).__name__}."
            )

        # Normalize team
        resolved_team: Team
        if isinstance(team, str):
            resolved_team = get_team(team)
        elif isinstance(team, Team):
            if not is_valid_team_id(team.id):
                raise TeamNotFoundError(
                    f"Team {team.id!r} is not a valid predefined team."
                )
            resolved_team = team
        else:
            raise TeamNotFoundError(
                f"Invalid team parameter {team!r}: must be Team instance or team ID string."
            )

        other_part = Participant.B if participant == Participant.A else Participant.A
        other_team = self._team_b if participant == Participant.A else self._team_a
        if other_team is not None and other_team.id == resolved_team.id:
            raise PreMatchError(
                f"Team '{resolved_team.name}' has already been selected by Participant {other_part.value}."
            )

        if participant == Participant.A:
            self._team_a = resolved_team
        else:
            self._team_b = resolved_team

        return resolved_team

    def get_team_for_participant(
        self, participant: Union[Participant, str]
    ) -> Optional[Team]:
        """Retrieve the team selected by a given participant."""
        if isinstance(participant, str):
            try:
                participant = Participant(participant.strip().upper())
            except ValueError:
                raise InvalidParticipantError(
                    f"Invalid participant {participant!r}."
                )
        elif not isinstance(participant, Participant):
            raise InvalidParticipantError(
                f"Expected Participant, got {type(participant).__name__}."
            )

        return self._team_a if participant == Participant.A else self._team_b

    def flip_toss(self) -> Participant:
        """Perform coin toss between Participant A and B."""
        return self._toss.flip()

    def choose_toss(
        self, decision: Union[TossDecision, str], by: Union[Participant, str]
    ) -> TossResult:
        """Record the toss winner's decision (BAT or BOWL)."""
        return self._toss.choose(decision=decision, by=by)

    @property
    def batting_first_participant(self) -> Optional[Participant]:
        """Participant batting in Innings 1, or None if toss not completed."""
        if self._toss.result is None:
            return None
        return self._toss.result.batting_first

    @property
    def bowling_first_participant(self) -> Optional[Participant]:
        """Participant bowling in Innings 1, or None if toss not completed."""
        if self._toss.result is None:
            return None
        return self._toss.result.bowling_first

    @property
    def first_bowler_selector_participant(self) -> Optional[Participant]:
        """Participant who chooses the first bowler, or None if toss not completed."""
        if self._toss.result is None:
            return None
        return self._toss.result.first_bowler_selector

    @property
    def batting_first_team(self) -> Optional[Team]:
        """Team batting in Innings 1, or None if toss or team selection incomplete."""
        p = self.batting_first_participant
        if p is None:
            return None
        return self.get_team_for_participant(p)

    @property
    def bowling_first_team(self) -> Optional[Team]:
        """Team bowling in Innings 1, or None if toss or team selection incomplete."""
        p = self.bowling_first_participant
        if p is None:
            return None
        return self.get_team_for_participant(p)

    @property
    def first_bowler_selector_team(self) -> Optional[Team]:
        """Team that selects the first bowler, or None if toss or team selection incomplete."""
        p = self.first_bowler_selector_participant
        if p is None:
            return None
        return self.get_team_for_participant(p)

    def create_match(
        self,
        max_overs: int = 5,
        balls_per_over: int = 6,
    ) -> Match:
        """Create an initialized Match instance based on team selection and toss outcome.

        In the Match engine:
        - team_1 is the team batting first in Innings 1.
        - team_2 is the team bowling first in Innings 1 (and chasing in Innings 2).

        Args:
            max_overs: Maximum overs per innings (default 5).
            balls_per_over: Balls per over (default 6).

        Returns:
            Configured Match instance ready to start.

        Raises:
            PreMatchError: If teams have not been selected or toss is not completed.
        """
        if not self.is_teams_selected:
            raise PreMatchError(
                "Cannot create match: both teams must be selected first."
            )
        if not self._toss.is_completed:
            raise PreMatchError(
                "Cannot create match: toss decision must be completed first."
            )

        assert self._team_a is not None
        assert self._team_b is not None
        assert self.batting_first_team is not None
        assert self.bowling_first_team is not None

        return Match(
            team_1=self.batting_first_team.name,
            team_2=self.bowling_first_team.name,
            team_size=len(self.batting_first_team.players),
            max_overs=max_overs,
            balls_per_over=balls_per_over,
        )

    def __repr__(self) -> str:
        return (
            f"PreMatchSetup(team_a={self._team_a.id if self._team_a else None}, "
            f"team_b={self._team_b.id if self._team_b else None}, "
            f"toss_status={self._toss.status.value})"
        )
