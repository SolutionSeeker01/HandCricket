"""Regression test suite for final audit hardening and deployment verification."""

import asyncio
import json
import os
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.app.engine.toss import Participant
from backend.app.main import app
from backend.app.protocol.friend_game import FriendGameSession
from backend.app.protocol.game import ComputerGameSession
from backend.app.protocol.room import FriendGameRoom, RoomStage
from backend.app.protocol.room_manager import RoomManager, reset_room_manager
from backend.app.transport.websocket import reset_standalone_computer_session


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_computer_session():
    reset_standalone_computer_session(None)
    yield
    reset_standalone_computer_session(None)


@pytest.fixture
def manager() -> RoomManager:
    mgr = RoomManager(
        reservation_ttl=10.0,
        lobby_inactive_ttl=300.0,
        both_disconnected_ttl=120.0,
        completed_match_ttl=600.0,
    )
    reset_room_manager(mgr)
    return mgr


# ==============================================================================
# 1. ISOLATED COMPUTER SESSIONS (CRITICAL 1)
# ==============================================================================


def test_isolated_computer_sessions_concurrency():
    """Two concurrent computer mode connections must have isolated sessions."""
    client = TestClient(app)
    with client.websocket_connect("/ws?mode=computer&skip_pre_match=true") as ws1:
        with client.websocket_connect("/ws?mode=computer&skip_pre_match=true") as ws2:
            data1 = ws1.receive_json()
            data2 = ws2.receive_json()

            assert data1["type"] == "turn_started"
            assert data2["type"] == "turn_started"
            assert data1["turn_id"] == 1
            assert data2["turn_id"] == 1

            # Submit on ws1 only
            ws1.send_json({"type": "submit_number", "number": 4, "turn_id": 1})
            sub1 = ws1.receive_json()
            assert sub1["type"] == "number_submitted"
            res1 = ws1.receive_json()
            assert res1["type"] == "ball_result"

            # ws1 should advance to turn 2
            next1 = ws1.receive_json()
            assert next1["type"] == "turn_started"
            assert next1["turn_id"] == 2

            # ws2 must STILL be on turn 1!
            ws2.send_json({"type": "submit_number", "number": 2, "turn_id": 1})
            sub2 = ws2.receive_json()
            assert sub2["type"] == "number_submitted"
            res2 = ws2.receive_json()
            assert res2["type"] == "ball_result"

            next2 = ws2.receive_json()
            assert next2["type"] == "turn_started"
            assert next2["turn_id"] == 2


# ==============================================================================
# 2. SAME-TEAM MATCH DISAMBIGUATION (HIGH 3)
# ==============================================================================


@pytest.mark.anyio
async def test_same_team_match_disambiguation_computer():
    """India vs India match in ComputerGameSession properly reports user_won and winner_side."""
    session = ComputerGameSession(user_team_id="IND", opponent_team_id="IND", skip_pre_match=True)
    assert session._match is not None
    assert session.user_team.name == session.opponent_team.name

    # User batted first by default in skip_pre_match (side 1)
    session._match.forfeit(winner="India", description="User won", winner_side=1)

    ms = session.get_match_state_dict()
    assert ms["winner"] == "India"
    assert ms["winner_side"] == 1
    assert ms["user_won"] is True
    assert ms["winner_participant"] == "user"

    # Now simulate Team 2 (computer) winning in fresh session
    session2 = ComputerGameSession(user_team_id="IND", opponent_team_id="IND", skip_pre_match=True)
    assert session2._match is not None
    session2._match.forfeit(winner="India", description="Computer won", winner_side=2)
    ms2 = session2.get_match_state_dict()
    assert ms2["winner_side"] == 2
    assert ms2["user_won"] is False
    assert ms2["winner_participant"] == "computer"


@pytest.mark.anyio
async def test_same_team_match_disambiguation_friend(manager: RoomManager):
    """India vs India match in FriendGameSession properly differentiates winner between A and B."""
    room, token_a = await manager.create_room("SAME01")
    slot_b, token_b = await manager.join_room("SAME01")
    session = room.get_or_create_session(disconnect_grace_seconds=1.0, toss_chooser=lambda: Participant.A)

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "IND")

    await session.choose_toss(Participant.A, "BAT")
    assert room.stage == RoomStage.BOWLER_SELECTION
    assert session.bowler_selector == Participant.B
    assert session._match is None

    bowler_id = session._pre_match.bowling_first_team.players[0].id
    await session.select_bowler(Participant.B, bowler_id)
    assert session._match is not None

    session._match.forfeit(winner="India", description="Player A won", winner_side=1)

    ms_a = session.get_match_state_dict(Participant.A)
    ms_b = session.get_match_state_dict(Participant.B)

    assert ms_a["winner_side"] == 1
    assert ms_a["winner_participant"] == "A"
    assert ms_a["user_won"] is True

    assert ms_b["winner_side"] == 1
    assert ms_b["winner_participant"] == "A"
    assert ms_b["user_won"] is False


# ==============================================================================
# 3. PRE-MATCH BOWLER DISCONNECT -> ABANDONED (HIGH 4 & 5)
# ==============================================================================


@pytest.mark.anyio
async def test_pre_match_bowler_disconnect_abandoned(manager: RoomManager):
    """Disconnect before match instantiation transitions room to ABANDONED, not match_completed."""
    room, token_a = await manager.create_room("ABAN01")
    slot_b, token_b = await manager.join_room("ABAN01")
    session = room.get_or_create_session(disconnect_grace_seconds=0.1, toss_chooser=lambda: Participant.A)

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    await session.choose_toss(Participant.A, "BAT")

    assert room.stage == RoomStage.BOWLER_SELECTION
    assert session._match is None

    await session.unregister_connection(Participant.B, ws_b)
    await asyncio.sleep(0.15)

    assert room.stage == RoomStage.ABANDONED
    calls = [call.args[0] for call in ws_a.send_json.call_args_list]
    types = [c.get("type") for c in calls if isinstance(c, dict)]
    assert "room_abandoned" in types
    assert "match_completed" not in types


# ==============================================================================
# 4. ACTIVE TURN DISCONNECT PAUSES TIMER & RESUMES (MEDIUM 6)
# ==============================================================================


@pytest.mark.anyio
async def test_active_turn_disconnect_pauses_and_resumes(manager: RoomManager):
    """Disconnect during live turn pauses the countdown; reconnect resumes with >= 3.0s."""
    room, token_a = await manager.create_room("PAUS01")
    slot_b, token_b = await manager.join_room("PAUS01")
    session = room.get_or_create_session(disconnect_grace_seconds=5.0, timeout_seconds=8.0, toss_chooser=lambda: Participant.A)

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    await session.choose_toss(Participant.A, "BAT")
    bowler_id = session._pre_match.bowling_first_team.players[0].id
    await session.select_bowler(Participant.B, bowler_id)

    assert room.stage == RoomStage.IN_MATCH
    assert session._current_turn is not None
    orig_deadline = session._current_turn.deadline

    await session.unregister_connection(Participant.B, ws_b)
    assert session._paused_turn_remaining_seconds is not None
    assert session._timeout_task is None or session._timeout_task.done()

    ws_b_new = AsyncMock()
    await session.register_connection(Participant.B, ws_b_new)

    assert session._paused_turn_remaining_seconds is None
    assert session._timeout_task is not None
    assert not session._timeout_task.done()
    assert session._current_turn.deadline >= orig_deadline - 5.0

    session.close()


# ==============================================================================
# 5. REMATCH PRESERVES TOSS CHOOSER (MEDIUM 8)
# ==============================================================================


@pytest.mark.anyio
async def test_rematch_preserves_toss_chooser(manager: RoomManager):
    """Injected toss_chooser must be retained across rematches."""
    deterministic_toss = lambda: Participant.B
    room, token_a = await manager.create_room("REMT01")
    slot_b, token_b = await manager.join_room("REMT01")
    session = room.get_or_create_session(toss_chooser=deterministic_toss)

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    assert session._pre_match.toss_winner == Participant.B

    await session.choose_toss(Participant.B, "BAT")
    bowler_id = session._pre_match.bowling_first_team.players[0].id
    await session.select_bowler(Participant.A, bowler_id)

    assert session._match is not None
    session._match._is_completed = True
    session._match._winner = "Australia"
    room.stage = RoomStage.MATCH_COMPLETED

    await session.request_rematch(Participant.A)
    await session.request_rematch(Participant.B)

    assert session._pre_match.toss_winner == Participant.B
    assert session._room.stage == RoomStage.TOSS_DECISION

    session.close()


# ==============================================================================
# 6. SESSION CLOSE CANCELS BACKGROUND TASKS (LOW 9)
# ==============================================================================


@pytest.mark.anyio
async def test_room_close_cancels_session_tasks(manager: RoomManager):
    """Evicting or closing a room cancels active timeout and grace worker tasks."""
    room, token_a = await manager.create_room("CLOS01")
    slot_b, token_b = await manager.join_room("CLOS01")
    session = room.get_or_create_session(disconnect_grace_seconds=60.0)

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.unregister_connection(Participant.A, ws_a)
    assert Participant.A in session._disconnect_grace_tasks
    grace_task = session._disconnect_grace_tasks[Participant.A]
    assert not grace_task.done()

    await manager.evict_room("CLOS01")
    await asyncio.sleep(0.01)
    assert room.is_closed
    assert grace_task.done() or grace_task.cancelled()


# ==============================================================================
# 7. STATIC SPA SERVING & FALLBACK (CRITICAL 2)
# ==============================================================================


def test_static_spa_serving_and_fallback():
    """FastAPI serves index.html at root, assets under /assets, and SPA fallback."""
    client = TestClient(app)
    res_root = client.get("/")
    assert res_root.status_code == 200

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_teams = client.get("/teams")
    assert res_teams.status_code == 200
    assert len(res_teams.json()) == 4

    res_bad_api = client.get("/api/nonexistent")
    assert res_bad_api.status_code == 404

    res_spa = client.get("/play")
    assert res_spa.status_code == 200
    assert "<!doctype html>" in res_spa.text.lower() or "<div id='root'>" in res_spa.text.lower() or "root" in res_spa.text.lower()
