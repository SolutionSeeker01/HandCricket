"""RoomManager for coordinating ephemeral in-memory Friend Mode rooms (Slice 15A).

This module manages room creation, atomic seat claiming for Player B,
room eviction, and stale room garbage collection under strict asyncio locking.
"""

import asyncio
import secrets
import time
from typing import Dict, List, Optional, Tuple

from backend.app.engine.toss import Participant
from backend.app.protocol.room import FriendGameRoom, PlayerSlot, RoomStage

# Crockford Base32 alphabet (excludes ambiguous chars: 0, O, 1, I, L)
ROOM_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"

# Authoritative TTL policies (documented in Section 3 of architecture spec)
RESERVATION_TTL: float = 30.0         # Slot B HTTP join reservation TTL before WS connect
LOBBY_INACTIVE_TTL: float = 300.0     # 5 minutes for unclaimed waiting lobby
BOTH_DISCONNECTED_TTL: float = 120.0  # 2 minutes if both players disconnect
COMPLETED_MATCH_TTL: float = 600.0    # 10 minutes to retain completed match stats


class RoomError(Exception):
    """Base exception for room coordination errors."""
    pass


class RoomNotFoundError(RoomError):
    """Raised when the requested room code does not exist in the registry."""
    pass


class RoomFullError(RoomError):
    """Raised when both player slots in the room are already occupied."""
    pass


class RoomClosedError(RoomError):
    """Raised when attempting to interact with a room that has been evicted or closed."""
    pass


class RoomManager:
    """Thread-safe and async-safe in-memory registry for Friend Mode game rooms."""

    def __init__(
        self,
        reservation_ttl: float = RESERVATION_TTL,
        lobby_inactive_ttl: float = LOBBY_INACTIVE_TTL,
        both_disconnected_ttl: float = BOTH_DISCONNECTED_TTL,
        completed_match_ttl: float = COMPLETED_MATCH_TTL,
    ) -> None:
        self._rooms: Dict[str, FriendGameRoom] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._reservation_ttl: float = reservation_ttl
        self._lobby_inactive_ttl: float = lobby_inactive_ttl
        self._both_disconnected_ttl: float = both_disconnected_ttl
        self._completed_match_ttl: float = completed_match_ttl

    @property
    def active_room_count(self) -> int:
        """Total number of active rooms currently registered."""
        return len(self._rooms)

    async def create_room(self, custom_code: Optional[str] = None) -> Tuple[FriendGameRoom, str]:
        """Create a new room and claim slot A for the host.

        Args:
            custom_code: Optional explicit room code (useful for deterministic tests).

        Returns:
            Tuple of (FriendGameRoom, token_a).

        Raises:
            RoomError: If code collision occurs or custom_code is already registered.
        """
        async with self._lock:
            code: Optional[str] = None
            if custom_code:
                norm = custom_code.strip().upper()
                if norm in self._rooms and not self._rooms[norm].is_closed:
                    raise RoomError(f"Room code {norm} already exists.")
                code = norm
            else:
                for _ in range(10):
                    candidate = "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(6))
                    if candidate not in self._rooms:
                        code = candidate
                        break
                if not code:
                    raise RoomError("Failed to allocate unique room code after 10 attempts.")

            token_a = secrets.token_urlsafe(16)
            room = FriendGameRoom(
                room_code=code,
                token_a=token_a,
                reservation_ttl=self._reservation_ttl,
            )
            self._rooms[code] = room
            return room, token_a

    async def join_room(self, code: str) -> Tuple[FriendGameRoom, str]:
        """Atomically claim Slot B for Player B.

        Synchronizes room lookup and slot reservation under manager lock,
        preventing any race between room eviction and slot reservation.

        Args:
            code: 6-character room code.

        Returns:
            Tuple of (FriendGameRoom, token_b).

        Raises:
            RoomNotFoundError: If room does not exist.
            RoomClosedError: If room is already closed/evicted.
            RoomFullError: If room is already full (both seats claimed and active).
        """
        async with self._lock:
            norm = code.strip().upper()
            room = self._rooms.get(norm)
            if room is None:
                raise RoomNotFoundError(f"Room {norm} does not exist.")
            if room.is_closed:
                raise RoomClosedError(f"Room {norm} is closed.")

            now = time.monotonic()
            if room.slot_b is not None and not room.slot_b.is_reservation_expired(now):
                raise RoomFullError(f"Room {norm} is already full.")

            token_b = secrets.token_urlsafe(16)
            room.slot_b = PlayerSlot(
                participant=Participant.B,
                token=token_b,
                reserved_at=now,
                reservation_ttl=self._reservation_ttl,
            )
            room.last_activity_at = now
            return room, token_b

    async def get_room(self, code: str) -> Optional[FriendGameRoom]:
        """Retrieve an active non-closed room, or None."""
        async with self._lock:
            norm = code.strip().upper()
            room = self._rooms.get(norm)
            if room is None or room.is_closed:
                return None
            return room

    async def evict_room(self, code: str) -> Optional[FriendGameRoom]:
        """Evict and close a room atomically.

        Guarantees that once eviction acquires the lock, no subsequent join_room
        can reserve a seat on this room.
        """
        async with self._lock:
            norm = code.strip().upper()
            room = self._rooms.pop(norm, None)
            if room is not None:
                room.close()
            return room

    async def cleanup_stale_rooms(self, now: Optional[float] = None) -> List[str]:
        """Evaluate TTL policies and evict stale/inactive rooms from memory."""
        async with self._lock:
            current = now if now is not None else time.monotonic()
            evicted: List[str] = []

            for code, room in list(self._rooms.items()):
                should_evict = False

                if room.is_closed:
                    should_evict = True
                elif (
                    room.stage == RoomStage.WAITING_FOR_PLAYER
                    and (current - room.created_at) > self._lobby_inactive_ttl
                ):
                    should_evict = True
                elif (
                    room.stage == RoomStage.MATCH_COMPLETED
                    and (current - room.last_activity_at) > self._completed_match_ttl
                ):
                    should_evict = True
                elif (
                    not room.slot_a.is_connected
                    and (room.slot_b is None or not room.slot_b.is_connected)
                    and (current - room.last_activity_at) > self._both_disconnected_ttl
                ):
                    should_evict = True

                if should_evict:
                    room.close()
                    self._rooms.pop(code, None)
                    evicted.append(code)

            return evicted


_global_room_manager: Optional[RoomManager] = None


def get_room_manager() -> RoomManager:
    """Retrieve or initialize the global RoomManager singleton."""
    global _global_room_manager
    if _global_room_manager is None:
        _global_room_manager = RoomManager()
    return _global_room_manager


def reset_room_manager(manager: Optional[RoomManager] = None) -> RoomManager:
    """Reset the global RoomManager singleton (used for test isolation)."""
    global _global_room_manager
    _global_room_manager = manager if manager is not None else RoomManager()
    return _global_room_manager
