"""Friend Mode room and player slot domain models (Slice 15A).

This module defines the room stages, player seat slots, and the FriendGameRoom
entity that coordinates seat ownership, tokens, and room-level lifecycle.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Optional

from backend.app.engine.toss import Participant


class RoomStage(str, Enum):
    """Lifecycle stages for a Friend Mode room."""

    WAITING_FOR_PLAYER = "WAITING_FOR_PLAYER"  # Player A waiting for Player B
    TEAM_SELECTION = "TEAM_SELECTION"          # Both players selecting their teams
    TOSS = "TOSS"                              # Server-authoritative coin toss in progress
    TOSS_DECISION = "TOSS_DECISION"            # Toss winner choosing BAT or BOWL
    BOWLER_SELECTION = "BOWLER_SELECTION"      # Fielding player selecting bowler
    IN_MATCH = "IN_MATCH"                      # Active live match play
    INNINGS_BREAK = "INNINGS_BREAK"            # Halftime break between innings
    MATCH_COMPLETED = "MATCH_COMPLETED"        # Match completed, modal open
    ABANDONED = "ABANDONED"                    # Opponent left permanently / timed out
    CLOSED = "CLOSED"                          # Room evicted / memory freed


@dataclass
class PlayerSlot:
    """Represents an assigned seat (Participant A or B) in a FriendGameRoom."""

    participant: Participant
    token: str
    websocket: Optional[Any] = None
    connected_at: Optional[float] = None
    last_seen_at: float = field(default_factory=time.monotonic)
    reserved_at: float = field(default_factory=time.monotonic)
    reservation_ttl: float = 30.0

    def is_reservation_expired(self, now: Optional[float] = None) -> bool:
        """True if the slot was reserved via HTTP join but no WebSocket connected within reservation_ttl."""
        if self.websocket is not None:
            return False
        current = now if now is not None else time.monotonic()
        return (current - self.reserved_at) > self.reservation_ttl

    @property
    def is_connected(self) -> bool:
        """True if an active live WebSocket is bound to this slot."""
        return self.websocket is not None


class FriendGameRoom:
    """Coordinates room-level ownership, seat slots, and lifecycle state."""

    def __init__(
        self,
        room_code: str,
        token_a: str,
        reservation_ttl: float = 30.0,
    ) -> None:
        self._room_code: str = room_code.upper()
        self._stage: RoomStage = RoomStage.WAITING_FOR_PLAYER
        self._reservation_ttl: float = reservation_ttl
        now = time.monotonic()
        self._created_at: float = now
        self._last_activity_at: float = now
        self._is_closed: bool = False

        self._slot_a: PlayerSlot = PlayerSlot(
            participant=Participant.A,
            token=token_a,
            reserved_at=now,
            reservation_ttl=self._reservation_ttl,
        )
        self._slot_b: Optional[PlayerSlot] = None
        self._session: Optional[Any] = None

    @property
    def session(self) -> Optional[Any]:
        """Active FriendGameSession coordinating this room."""
        return self._session

    @session.setter
    def session(self, value: Any) -> None:
        self._session = value

    def get_or_create_session(self, **kwargs: Any) -> Any:
        """Retrieve existing or initialize new FriendGameSession."""
        if self._session is None:
            from backend.app.protocol.friend_game import FriendGameSession
            self._session = FriendGameSession(room=self, **kwargs)
        return self._session

    @property
    def room_code(self) -> str:
        """Unique 6-character room code."""
        return self._room_code

    @property
    def stage(self) -> RoomStage:
        """Current room lifecycle stage."""
        return self._stage

    @stage.setter
    def stage(self, value: RoomStage) -> None:
        self._stage = value
        self._last_activity_at = time.monotonic()

    @property
    def is_closed(self) -> bool:
        """True if the room has been closed / evicted."""
        return self._is_closed

    @property
    def created_at(self) -> float:
        """Monotonic epoch timestamp when room was created."""
        return self._created_at

    @property
    def last_activity_at(self) -> float:
        """Monotonic epoch timestamp of most recent room activity."""
        return self._last_activity_at

    @last_activity_at.setter
    def last_activity_at(self, value: float) -> None:
        self._last_activity_at = value

    @property
    def slot_a(self) -> PlayerSlot:
        """Participant A (Room Host) slot."""
        return self._slot_a

    @property
    def slot_b(self) -> Optional[PlayerSlot]:
        """Participant B (Guest) slot, or None if not yet joined."""
        return self._slot_b

    @slot_b.setter
    def slot_b(self, slot: Optional[PlayerSlot]) -> None:
        self._slot_b = slot
        self._last_activity_at = time.monotonic()

    @property
    def is_full(self) -> bool:
        """True if both slots are claimed and active (not expired)."""
        if self._slot_b is None:
            return False
        return not self._slot_b.is_reservation_expired()

    @property
    def open_slots(self) -> int:
        """Number of open participant seats (0 or 1)."""
        return 0 if self.is_full else 1

    def get_slot_by_token(self, token: str) -> Optional[PlayerSlot]:
        """Find the PlayerSlot matching a secret session token."""
        if self._slot_a.token == token:
            return self._slot_a
        if self._slot_b is not None and self._slot_b.token == token:
            return self._slot_b
        return None

    def get_participant_by_token(self, token: str) -> Optional[Participant]:
        """Map a secret session token to its server-authoritative Participant seat."""
        slot = self.get_slot_by_token(token)
        return slot.participant if slot is not None else None

    def close(self) -> None:
        """Mark room as closed and transition stage to CLOSED."""
        self._is_closed = True
        self._stage = RoomStage.CLOSED
        self._last_activity_at = time.monotonic()
        if self._session is not None and hasattr(self._session, "close"):
            self._session.close()
