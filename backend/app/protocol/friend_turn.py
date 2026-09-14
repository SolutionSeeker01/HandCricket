"""Friend Mode turn representation and lifecycle models (Slice 15C).

This module defines the server-authoritative turn state, monotonic deadline tracking,
and immutable view for a single delivery turn in Friend Mode.
"""

from dataclasses import dataclass
from typing import Optional

from backend.app.engine.toss import Participant


@dataclass
class FriendTurn:
    """Server-authoritative mutable turn container managed under session lock."""

    turn_id: int
    started_at: float
    deadline: float
    choice_a: Optional[int] = None
    choice_b: Optional[int] = None
    a_submitted_at: Optional[float] = None
    b_submitted_at: Optional[float] = None
    a_timed_out: bool = False
    b_timed_out: bool = False
    is_resolved: bool = False

    def has_submitted(self, participant: Participant) -> bool:
        """True if the participant has submitted their number or timed out."""
        if participant == Participant.A:
            return self.choice_a is not None or self.a_timed_out
        return self.choice_b is not None or self.b_timed_out

    def is_expired(self, now: float) -> bool:
        """True if the monotonic deadline has strictly expired."""
        return now > self.deadline

    @property
    def is_ready_to_resolve(self) -> bool:
        """True when both participants have either submitted or timed out."""
        has_a = self.choice_a is not None or self.a_timed_out
        has_b = self.choice_b is not None or self.b_timed_out
        return has_a and has_b

    def as_view(self) -> "FriendTurnView":
        """Produce an immutable read-only view of this turn."""
        return FriendTurnView(
            turn_id=self.turn_id,
            started_at=self.started_at,
            deadline=self.deadline,
            has_a_submitted=self.choice_a is not None,
            has_b_submitted=self.choice_b is not None,
            a_timed_out=self.a_timed_out,
            b_timed_out=self.b_timed_out,
            is_resolved=self.is_resolved,
        )


@dataclass(frozen=True)
class FriendTurnView:
    """Read-only view of a Friend Mode turn.

    Notice: Does NOT expose unrevealed choices to ensure complete secrecy.
    """

    turn_id: int
    started_at: float
    deadline: float
    has_a_submitted: bool
    has_b_submitted: bool
    a_timed_out: bool
    b_timed_out: bool
    is_resolved: bool
