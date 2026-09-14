"""Tests for Friend Mode WebSocket lifecycle and pre-match synchronization (Slice 15B)."""

import pytest
from fastapi.testclient import TestClient

from backend.app.engine.toss import Participant
from backend.app.main import app
from backend.app.protocol.friend_game import FriendGameSession
from backend.app.protocol.room import RoomStage
from backend.app.protocol.room_manager import RoomManager, reset_room_manager


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def manager() -> RoomManager:
    """Isolated RoomManager for each test."""
    mgr = RoomManager(
        reservation_ttl=10.0,
        lobby_inactive_ttl=300.0,
        both_disconnected_ttl=120.0,
        completed_match_ttl=600.0,
    )
    reset_room_manager(mgr)
    return mgr


@pytest.fixture
def client(manager: RoomManager) -> TestClient:
    return TestClient(app)


def test_friend_game_websocket_connect_lifecycle(client: TestClient):
    """Verify player A and B connection handshake, identity receipt, and stage change."""
    # 1. Create room and join B
    create_resp = client.post("/api/rooms")
    assert create_resp.status_code == 201
    room_code = create_resp.json()["room_code"]
    token_a = create_resp.json()["player_token"]

    join_resp = client.post(f"/api/rooms/{room_code}/join")
    assert join_resp.status_code == 200
    token_b = join_resp.json()["player_token"]

    # 2. Player A connects first
    with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_a}") as ws_a:
        msg_a = ws_a.receive_json()
        assert msg_a["type"] == "room_joined"
        assert msg_a["participant"] == "A"
        assert msg_a["stage"] == "WAITING_FOR_PLAYER"

        # 3. Player B connects
        with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_b}") as ws_b:
            msg_b = ws_b.receive_json()
            assert msg_b["type"] == "room_joined"
            assert msg_b["participant"] == "B"

            # Both receive player_joined
            joined_broadcast_a = ws_a.receive_json()
            assert joined_broadcast_a["type"] == "player_joined"
            assert joined_broadcast_a["participant"] == "B"
            assert joined_broadcast_a["stage"] == "TEAM_SELECTION"

            joined_broadcast_b = ws_b.receive_json()
            assert joined_broadcast_b["type"] == "player_joined"
            assert joined_broadcast_b["participant"] == "B"
            assert joined_broadcast_b["stage"] == "TEAM_SELECTION"

            # Both receive stage_changed
            stage_a = ws_a.receive_json()
            assert stage_a["type"] == "stage_changed"
            assert stage_a["stage"] == "TEAM_SELECTION"

            stage_b = ws_b.receive_json()
            assert stage_b["type"] == "stage_changed"
            assert stage_b["stage"] == "TEAM_SELECTION"


def test_friend_game_invalid_room_and_token(client: TestClient):
    """Verify rejected connections for invalid room code or invalid token."""
    # Invalid room code
    with client.websocket_connect("/ws/friend?room=INVALID&token=fake_token") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "room_not_found"

    # Valid room, invalid token
    create_resp = client.post("/api/rooms")
    room_code = create_resp.json()["room_code"]

    with client.websocket_connect(f"/ws/friend?room={room_code}&token=bad_token") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "invalid_token"


def test_friend_game_independent_team_selection_and_toss(client: TestClient):
    """Verify both players select teams independently and server flips toss upon completion."""
    create_resp = client.post("/api/rooms")
    room_code = create_resp.json()["room_code"]
    token_a = create_resp.json()["player_token"]

    join_resp = client.post(f"/api/rooms/{room_code}/join")
    token_b = join_resp.json()["player_token"]

    with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_a}") as ws_a:
        ws_a.receive_json()  # room_joined A

        with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_b}") as ws_b:
            ws_b.receive_json()  # room_joined B
            ws_a.receive_json()  # player_joined
            ws_b.receive_json()  # player_joined
            ws_a.receive_json()  # stage_changed
            ws_b.receive_json()  # stage_changed

            # 1. Player A selects invalid team
            ws_a.send_json({"type": "select_team", "team_id": "INVALID_TEAM"})
            err_a = ws_a.receive_json()
            assert err_a["type"] == "error"
            assert err_a["code"] == "invalid_team"

            # 2. Player A selects IND
            ws_a.send_json({"type": "select_team", "team_id": "IND"})
            t_sel_a = ws_a.receive_json()
            assert t_sel_a["type"] == "team_selected"
            assert t_sel_a["participant"] == "A"
            assert t_sel_a["team_id"] == "IND"

            t_sel_b = ws_b.receive_json()
            assert t_sel_b["type"] == "team_selected"
            assert t_sel_b["participant"] == "A"
            assert t_sel_b["team_id"] == "IND"

            # 3. Player B selects AUS
            ws_b.send_json({"type": "select_team", "team_id": "AUS"})
            b_sel_a = ws_a.receive_json()
            assert b_sel_a["type"] == "team_selected"
            assert b_sel_a["participant"] == "B"
            assert b_sel_a["team_id"] == "AUS"

            b_sel_b = ws_b.receive_json()
            assert b_sel_b["type"] == "team_selected"
            assert b_sel_b["participant"] == "B"

            # Both now receive toss_result
            toss_a = ws_a.receive_json()
            assert toss_a["type"] == "toss_result"
            assert toss_a["winner"] in ("A", "B")
            assert toss_a["stage"] == "TOSS_DECISION"

            toss_b = ws_b.receive_json()
            assert toss_b["type"] == "toss_result"
            assert toss_b["winner"] == toss_a["winner"]
            assert toss_b["stage"] == "TOSS_DECISION"


def test_friend_game_full_pre_match_flow_to_match_start(client: TestClient):
    """End-to-end pre-match flow: connect -> teams -> toss -> decision -> bowler -> match_started."""
    create_resp = client.post("/api/rooms")
    room_code = create_resp.json()["room_code"]
    token_a = create_resp.json()["player_token"]

    join_resp = client.post(f"/api/rooms/{room_code}/join")
    token_b = join_resp.json()["player_token"]

    with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_a}") as ws_a:
        ws_a.receive_json()  # room_joined A

        with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_b}") as ws_b:
            ws_b.receive_json()  # room_joined B
            ws_a.receive_json()  # player_joined
            ws_b.receive_json()  # player_joined
            ws_a.receive_json()  # stage_changed
            ws_b.receive_json()  # stage_changed

            # Select teams
            ws_a.send_json({"type": "select_team", "team_id": "IND"})
            ws_a.receive_json()
            ws_b.receive_json()

            ws_b.send_json({"type": "select_team", "team_id": "AUS"})
            ws_a.receive_json()
            ws_b.receive_json()

            # Toss result
            toss_a = ws_a.receive_json()
            toss_b = ws_b.receive_json()
            winner = toss_a["winner"]
            loser = "B" if winner == "A" else "A"

            ws_winner = ws_a if winner == "A" else ws_b
            ws_loser = ws_b if winner == "A" else ws_a

            # 1. Loser tries to make toss decision -> rejected
            ws_loser.send_json({"type": "choose_toss", "decision": "BAT"})
            err_loser = ws_loser.receive_json()
            assert err_loser["type"] == "error"
            assert err_loser["code"] == "not_toss_winner"

            # 2. Winner makes toss decision to BAT
            ws_winner.send_json({"type": "choose_toss", "decision": "BAT"})
            dec_a = ws_a.receive_json()
            dec_b = ws_b.receive_json()
            assert dec_a["type"] == "toss_decision_result"
            assert dec_a["decision"] == "BAT"
            assert dec_a["batting_first"] == winner
            assert dec_a["bowling_first"] == loser
            assert dec_a["bowler_selector"] == loser
            assert dec_a["stage"] == "BOWLER_SELECTION"
            assert dec_b["type"] == "toss_decision_result"

            # 3. Batting player tries to select bowler -> rejected
            ws_winner.send_json({"type": "select_bowler", "bowler_id": 11})
            err_bowler = ws_winner.receive_json()
            assert err_bowler["type"] == "error"
            assert err_bowler["code"] == "not_bowler_selector"

            # 4. Bowling player selects opening bowler (11)
            ws_loser.send_json({"type": "select_bowler", "bowler_id": 11})

            # 5. Synchronized match_started broadcast
            match_start_a = ws_a.receive_json()
            assert match_start_a["type"] == "match_started"
            assert match_start_a["room_code"] == room_code
            assert match_start_a["stage"] == "IN_MATCH"
            assert match_start_a["batting_participant"] == winner
            assert match_start_a["bowling_participant"] == loser
            assert match_start_a["current_bowler"]["id"] == 11
            assert match_start_a["match_state"]["score"] == 0
            assert match_start_a["match_state"]["wickets"] == 0
            assert match_start_a["match_state"]["overs"] == "0.0"

            match_start_b = ws_b.receive_json()
            assert match_start_b["type"] == "match_started"
            assert match_start_b["batting_participant"] == winner
            assert match_start_b["bowling_participant"] == loser
            assert match_start_b["current_bowler"]["id"] == 11
            assert match_start_b["match_state"]["score"] == 0


def test_friend_game_ping_and_query_mode(client: TestClient):
    """Verify ping-pong and /ws?mode=friend query route."""
    create_resp = client.post("/api/rooms")
    room_code = create_resp.json()["room_code"]
    token_a = create_resp.json()["player_token"]

    # Connect via /ws?mode=friend&room=...&token=...
    with client.websocket_connect(f"/ws?mode=friend&room={room_code}&token={token_a}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "room_joined"
        assert msg["participant"] == "A"

        # Ping
        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"
