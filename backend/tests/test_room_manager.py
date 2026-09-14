"""Tests for RoomManager, FriendGameRoom, and room HTTP endpoints (Slice 15A)."""

import asyncio
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.engine.toss import Participant
from backend.app.main import app
from backend.app.protocol.room import FriendGameRoom, PlayerSlot, RoomStage
from backend.app.protocol.room_manager import (
    ROOM_CODE_ALPHABET,
    RoomClosedError,
    RoomError,
    RoomFullError,
    RoomManager,
    RoomNotFoundError,
    reset_room_manager,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def manager() -> RoomManager:
    """Fresh isolated RoomManager for each test."""
    mgr = RoomManager(
        reservation_ttl=1.0,
        lobby_inactive_ttl=5.0,
        both_disconnected_ttl=2.0,
        completed_match_ttl=10.0,
    )
    reset_room_manager(mgr)
    return mgr


@pytest.fixture
def client(manager: RoomManager) -> TestClient:
    """FastAPI TestClient with isolated RoomManager."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Unit Tests: FriendGameRoom & PlayerSlot
# ---------------------------------------------------------------------------

def test_player_slot_creation_and_expiration():
    """Verify slot reservation TTL and expiration semantics."""
    slot = PlayerSlot(
        participant=Participant.B,
        token="test_token",
        reservation_ttl=2.0,
        reserved_at=100.0,
    )
    assert slot.participant == Participant.B
    assert slot.token == "test_token"
    assert slot.is_connected is False
    # Not expired at 101.5s
    assert slot.is_reservation_expired(now=101.5) is False
    # Expired at 102.1s
    assert slot.is_reservation_expired(now=102.1) is True

    # Once connected, never expired regardless of elapsed time
    slot.websocket = object()
    assert slot.is_connected is True
    assert slot.is_reservation_expired(now=200.0) is False


def test_friend_game_room_initialization():
    """Verify room creation initializes Slot A and leaves Slot B open."""
    room = FriendGameRoom(room_code="CRIC88", token_a="tok_a")
    assert room.room_code == "CRIC88"
    assert room.stage == RoomStage.WAITING_FOR_PLAYER
    assert room.is_closed is False
    assert room.slot_a.participant == Participant.A
    assert room.slot_a.token == "tok_a"
    assert room.slot_b is None
    assert room.is_full is False
    assert room.open_slots == 1

    assert room.get_slot_by_token("tok_a") == room.slot_a
    assert room.get_participant_by_token("tok_a") == Participant.A
    assert room.get_slot_by_token("unknown") is None


def test_friend_game_room_close():
    """Verify room close transitions stage and marks closed."""
    room = FriendGameRoom(room_code="CRIC88", token_a="tok_a")
    room.close()
    assert room.is_closed is True
    assert room.stage == RoomStage.CLOSED


# ---------------------------------------------------------------------------
# Unit Tests: RoomManager
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_room_manager_create_and_get(manager: RoomManager):
    """Verify room creation generates Crockford Base32 6-char code and registers room."""
    room, token_a = await manager.create_room()
    assert len(room.room_code) == 6
    assert all(c in ROOM_CODE_ALPHABET for c in room.room_code)
    assert token_a == room.slot_a.token
    assert manager.active_room_count == 1

    fetched = await manager.get_room(room.room_code)
    assert fetched == room

    # Case insensitive lookup
    fetched_lower = await manager.get_room(room.room_code.lower())
    assert fetched_lower == room


@pytest.mark.anyio
async def test_room_manager_custom_code_and_collision(manager: RoomManager):
    """Verify custom code support and rejection of duplicates."""
    room, token_a = await manager.create_room(custom_code="TEST99")
    assert room.room_code == "TEST99"

    with pytest.raises(RoomError, match="already exists"):
        await manager.create_room(custom_code="TEST99")


@pytest.mark.anyio
async def test_room_manager_join_success(manager: RoomManager):
    """Verify atomic join claims Slot B and returns token_b."""
    room, token_a = await manager.create_room(custom_code="ROOM01")
    assert room.open_slots == 1

    joined_room, token_b = await manager.join_room("ROOM01")
    assert joined_room == room
    assert joined_room.slot_b is not None
    assert joined_room.slot_b.token == token_b
    assert joined_room.slot_b.participant == Participant.B
    assert joined_room.is_full is True
    assert joined_room.open_slots == 0

    # Token mapping
    assert room.get_participant_by_token(token_a) == Participant.A
    assert room.get_participant_by_token(token_b) == Participant.B
    assert token_a != token_b


@pytest.mark.anyio
async def test_room_manager_join_invalid_room(manager: RoomManager):
    """Verify joining non-existent room raises RoomNotFoundError."""
    with pytest.raises(RoomNotFoundError, match="does not exist"):
        await manager.join_room("NOPE99")


@pytest.mark.anyio
async def test_room_manager_join_full_room_rejection(manager: RoomManager):
    """Verify attempting to join when both slots are occupied raises RoomFullError."""
    await manager.create_room(custom_code="FULL99")
    await manager.join_room("FULL99")

    with pytest.raises(RoomFullError, match="already full"):
        await manager.join_room("FULL99")


@pytest.mark.anyio
async def test_room_manager_stale_reservation_reclaimed(manager: RoomManager):
    """Verify expired Slot B reservation allows a new joiner to claim the slot."""
    # Manager has 1.0s reservation TTL
    room, token_a = await manager.create_room(custom_code="EXPIRE")
    _, token_b1 = await manager.join_room("EXPIRE")

    assert room.is_full is True

    # Simulate time passing beyond 1.0s without WebSocket connection
    room.slot_b.reserved_at -= 2.0
    assert room.slot_b.is_reservation_expired() is True
    assert room.is_full is False

    # Second joiner can now claim slot B
    _, token_b2 = await manager.join_room("EXPIRE")
    assert token_b2 != token_b1
    assert room.slot_b.token == token_b2
    assert room.is_full is True


@pytest.mark.anyio
async def test_room_manager_concurrent_join_attempts(manager: RoomManager):
    """Verify that when 10 clients attempt to join the last seat concurrently, exactly ONE succeeds."""
    room, _ = await manager.create_room(custom_code="RACE99")

    results = []
    errors = []

    async def _attempt_join(idx: int):
        try:
            res = await manager.join_room("RACE99")
            results.append((idx, res))
        except RoomFullError as e:
            errors.append((idx, e))

    # Launch 10 concurrent join tasks
    await asyncio.gather(*[_attempt_join(i) for i in range(10)])

    assert len(results) == 1, "Exactly one client must claim slot B"
    assert len(errors) == 9, "All 9 other clients must receive RoomFullError"
    assert room.is_full is True


@pytest.mark.anyio
async def test_room_manager_eviction_and_closed_room_race(manager: RoomManager):
    """Guardrail 1: join_room() must not reserve a slot on an evicted or closed room."""
    room, _ = await manager.create_room(custom_code="EVICT1")
    await manager.evict_room("EVICT1")

    # After eviction, room is not in manager
    assert await manager.get_room("EVICT1") is None
    assert room.is_closed is True

    # Attempting to join evicted room raises RoomNotFoundError
    with pytest.raises(RoomNotFoundError):
        await manager.join_room("EVICT1")

    # If an existing closed room reference somehow remained in registry:
    closed_room = FriendGameRoom(room_code="CLOSED", token_a="tok_c")
    closed_room.close()
    manager._rooms["CLOSED"] = closed_room

    with pytest.raises(RoomClosedError):
        await manager.join_room("CLOSED")


@pytest.mark.anyio
async def test_room_manager_cleanup_stale_rooms(manager: RoomManager):
    """Verify background TTL janitor evicts stale unjoined lobbies."""
    room, _ = await manager.create_room(custom_code="STALE1")
    # Advance time beyond lobby TTL (5s in fixture)
    room._created_at -= 10.0

    evicted = await manager.cleanup_stale_rooms()
    assert "STALE1" in evicted
    assert manager.active_room_count == 0
    assert room.is_closed is True


@pytest.mark.anyio
async def test_room_isolation(manager: RoomManager):
    """Verify multiple rooms operate with completely independent state and tokens."""
    room_1, tok_a1 = await manager.create_room(custom_code="ROOM01")
    room_2, tok_a2 = await manager.create_room(custom_code="ROOM02")

    _, tok_b1 = await manager.join_room("ROOM01")
    _, tok_b2 = await manager.join_room("ROOM02")

    tokens = {tok_a1, tok_a2, tok_b1, tok_b2}
    assert len(tokens) == 4, "All 4 tokens must be completely unique"

    assert room_1.get_participant_by_token(tok_a1) == Participant.A
    assert room_1.get_participant_by_token(tok_a2) is None
    assert room_2.get_participant_by_token(tok_a2) == Participant.A
    assert room_2.get_participant_by_token(tok_a1) is None


# ---------------------------------------------------------------------------
# HTTP API Tests (FastAPI TestClient)
# ---------------------------------------------------------------------------

def test_api_create_room(client: TestClient):
    """Verify POST /api/rooms returns 201 Created with code, token, and participant A."""
    resp = client.post("/api/rooms")
    assert resp.status_code == 201
    data = resp.json()
    assert "room_code" in data
    assert len(data["room_code"]) == 6
    assert "player_token" in data
    assert len(data["player_token"]) >= 16
    assert data["participant"] == "A"


def test_api_join_room_success(client: TestClient):
    """Verify POST /api/rooms/{code}/join claims seat B."""
    create_resp = client.post("/api/rooms")
    code = create_resp.json()["room_code"]

    join_resp = client.post(f"/api/rooms/{code}/join")
    assert join_resp.status_code == 200
    join_data = join_resp.json()
    assert join_data["room_code"] == code
    assert "player_token" in join_data
    assert join_data["participant"] == "B"


def test_api_join_room_full(client: TestClient):
    """Verify POST /api/rooms/{code}/join returns 409 Conflict when already full."""
    create_resp = client.post("/api/rooms")
    code = create_resp.json()["room_code"]

    # First joiner succeeds
    join1_resp = client.post(f"/api/rooms/{code}/join")
    assert join1_resp.status_code == 200

    # Second joiner gets 409
    join2_resp = client.post(f"/api/rooms/{code}/join")
    assert join2_resp.status_code == 409
    err = join2_resp.json()["detail"]
    assert err["code"] == "room_full"


def test_api_join_room_not_found(client: TestClient):
    """Verify POST /api/rooms/{code}/join returns 404 Not Found for non-existent room."""
    resp = client.post("/api/rooms/NONEXIST/join")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "room_not_found"


def test_api_get_room_info(client: TestClient):
    """Verify GET /api/rooms/{code} returns room stage and open slots."""
    create_resp = client.post("/api/rooms")
    code = create_resp.json()["room_code"]

    info_resp = client.get(f"/api/rooms/{code}")
    assert info_resp.status_code == 200
    data = info_resp.json()
    assert data["room_code"] == code
    assert data["stage"] == "WAITING_FOR_PLAYER"
    assert data["open_slots"] == 1
    assert data["is_available"] is True

    # After join, open_slots becomes 0
    client.post(f"/api/rooms/{code}/join")
    info_resp_after = client.get(f"/api/rooms/{code}")
    assert info_resp_after.status_code == 200
    assert info_resp_after.json()["open_slots"] == 0
    assert info_resp_after.json()["is_available"] is False


def test_api_get_room_info_not_found(client: TestClient):
    """Verify GET /api/rooms/{code} returns 404 for unknown code."""
    resp = client.get("/api/rooms/UNKNOWN")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "room_not_found"
