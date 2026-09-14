"""Comprehensive tests for Friend Mode turn resolution and Match Engine integration (Slice 15C)."""

import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.app.engine.toss import Participant
from backend.app.main import app
from backend.app.protocol.friend_game import FriendGameSession
from backend.app.protocol.messages import TurnProtocolError
from backend.app.protocol.room import RoomStage
from backend.app.protocol.room_manager import RoomManager, reset_room_manager


@pytest.fixture
def anyio_backend():
    return "asyncio"


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


@pytest.fixture
def client(manager: RoomManager) -> TestClient:
    return TestClient(app)


def _setup_active_match(client: TestClient):
    """Helper that runs pre-match setup so room reaches IN_MATCH with turn 1 started."""
    create_resp = client.post("/api/rooms")
    room_code = create_resp.json()["room_code"]
    token_a = create_resp.json()["player_token"]

    join_resp = client.post(f"/api/rooms/{room_code}/join")
    token_b = join_resp.json()["player_token"]

    return room_code, token_a, token_b


def test_turn_creation_secrecy_and_resolution(client: TestClient):
    """Verify turn creation, non-negotiable secrecy of number_submitted, and ball resolution."""
    room_code, token_a, token_b = _setup_active_match(client)

    with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_a}") as ws_a:
        ws_a.receive_json()  # room_joined

        with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_b}") as ws_b:
            ws_b.receive_json()  # room_joined
            ws_a.receive_json()  # player_joined
            ws_b.receive_json()  # player_joined
            ws_a.receive_json()  # stage_changed
            ws_b.receive_json()  # stage_changed

            # Teams: A is IND, B is AUS
            ws_a.send_json({"type": "select_team", "team_id": "IND"})
            ws_a.receive_json()
            ws_b.receive_json()

            ws_b.send_json({"type": "select_team", "team_id": "AUS"})
            ws_a.receive_json()
            ws_b.receive_json()

            # Toss
            toss_a = ws_a.receive_json()
            ws_b.receive_json()
            winner = toss_a["winner"]
            loser = "B" if winner == "A" else "A"
            ws_winner = ws_a if winner == "A" else ws_b
            ws_loser = ws_b if winner == "A" else ws_a

            # Winner chooses BAT
            ws_winner.send_json({"type": "choose_toss", "decision": "BAT"})
            ws_a.receive_json()
            ws_b.receive_json()

            # Loser chooses opening bowler 11
            ws_loser.send_json({"type": "select_bowler", "bowler_id": 11})
            ws_a.receive_json()  # match_started
            ws_b.receive_json()  # match_started

            # 1. Turn 1 starts: both receive turn_started
            turn_start_a = ws_a.receive_json()
            turn_start_b = ws_b.receive_json()
            assert turn_start_a["type"] == "turn_started"
            assert turn_start_a["turn_id"] == 1
            assert turn_start_a["timeout_seconds"] == 10.0
            assert turn_start_b["type"] == "turn_started"
            assert turn_start_b["turn_id"] == 1

            # 2. Player A submits 4: SECRECY CHECK
            ws_a.send_json({"type": "submit_number", "turn_id": 1, "number": 4})
            ack_a_to_a = ws_a.receive_json()
            ack_a_to_b = ws_b.receive_json()

            # Number_submitted MUST NOT contain the numeric choice!
            assert ack_a_to_a["type"] == "number_submitted"
            assert ack_a_to_a["participant"] == "A"
            assert ack_a_to_a["turn_id"] == 1
            assert "number" not in ack_a_to_a
            assert "choice" not in ack_a_to_a

            assert ack_a_to_b["type"] == "number_submitted"
            assert ack_a_to_b["participant"] == "A"
            assert "number" not in ack_a_to_b
            assert "choice" not in ack_a_to_b

            # 3. Duplicate submission by Player A rejected
            ws_a.send_json({"type": "submit_number", "turn_id": 1, "number": 4})
            err_dup = ws_a.receive_json()
            assert err_dup["type"] == "error"
            assert err_dup["code"] == "already_submitted"

            # 4. Player B submits 2: completes turn 1!
            ws_b.send_json({"type": "submit_number", "turn_id": 1, "number": 2})
            ack_b_to_a = ws_a.receive_json()
            ack_b_to_b = ws_b.receive_json()
            assert ack_b_to_a["type"] == "number_submitted"
            assert "number" not in ack_b_to_a
            assert ack_b_to_b["type"] == "number_submitted"

            # 5. Authoritative ball_result broadcast with revealed choices
            ball_a = ws_a.receive_json()
            ball_b = ws_b.receive_json()
            assert ball_a["type"] == "ball_result"
            assert ball_a["turn_id"] == 1
            assert ball_a["choice_a"] == 4
            assert ball_a["choice_b"] == 2
            assert ball_a["is_wicket"] is False

            # If winner A is batting: runs=4; if winner B is batting: runs=2
            expected_runs = 4 if winner == "A" else 2
            assert ball_a["runs"] == expected_runs
            assert ball_a["match_state"]["score"] == expected_runs
            assert ball_b["type"] == "ball_result"
            assert ball_b["match_state"]["score"] == expected_runs

            # 6. Next turn (turn 2) starts automatically!
            turn2_a = ws_a.receive_json()
            turn2_b = ws_b.receive_json()
            assert turn2_a["type"] == "turn_started"
            assert turn2_a["turn_id"] == 2
            assert turn2_b["type"] == "turn_started"
            assert turn2_b["turn_id"] == 2


def test_wicket_ball_resolution(client: TestClient):
    """Verify that matching numbers produce a wicket and strike/wicket update."""
    room_code, token_a, token_b = _setup_active_match(client)

    with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_a}") as ws_a:
        ws_a.receive_json()
        with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_b}") as ws_b:
            ws_b.receive_json()
            ws_a.receive_json()
            ws_b.receive_json()
            ws_a.receive_json()
            ws_b.receive_json()

            # Teams
            ws_a.send_json({"type": "select_team", "team_id": "IND"})
            ws_a.receive_json()
            ws_b.receive_json()
            ws_b.send_json({"type": "select_team", "team_id": "AUS"})
            ws_a.receive_json()
            ws_b.receive_json()

            # Toss
            toss = ws_a.receive_json()
            ws_b.receive_json()
            winner = toss["winner"]
            ws_winner = ws_a if winner == "A" else ws_b
            ws_loser = ws_b if winner == "A" else ws_a

            ws_winner.send_json({"type": "choose_toss", "decision": "BAT"})
            ws_a.receive_json()
            ws_b.receive_json()

            ws_loser.send_json({"type": "select_bowler", "bowler_id": 11})
            ws_a.receive_json()
            ws_b.receive_json()
            ws_a.receive_json()  # turn_started
            ws_b.receive_json()  # turn_started

            # Both submit 5 (matching numbers = WICKET!)
            ws_a.send_json({"type": "submit_number", "turn_id": 1, "number": 5})
            ws_a.receive_json()  # ack A
            ws_b.receive_json()  # ack A

            ws_b.send_json({"type": "submit_number", "turn_id": 1, "number": 5})
            ws_a.receive_json()  # ack B
            ws_b.receive_json()  # ack B

            ball = ws_a.receive_json()
            ws_b.receive_json()
            assert ball["type"] == "ball_result"
            assert ball["is_wicket"] is True
            assert ball["runs"] == 0
            assert ball["match_state"]["wickets"] == 1


def test_stale_turn_and_invalid_number_handling(client: TestClient):
    """Verify validation: invalid numbers and stale turn submissions."""
    room_code, token_a, token_b = _setup_active_match(client)

    with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_a}") as ws_a:
        ws_a.receive_json()
        with client.websocket_connect(f"/ws/friend?room={room_code}&token={token_b}") as ws_b:
            ws_b.receive_json()
            ws_a.receive_json()
            ws_b.receive_json()
            ws_a.receive_json()
            ws_b.receive_json()

            ws_a.send_json({"type": "select_team", "team_id": "IND"})
            ws_a.receive_json()
            ws_b.receive_json()
            ws_b.send_json({"type": "select_team", "team_id": "AUS"})
            ws_a.receive_json()
            ws_b.receive_json()

            toss = ws_a.receive_json()
            ws_b.receive_json()
            winner = toss["winner"]
            ws_winner = ws_a if winner == "A" else ws_b
            ws_loser = ws_b if winner == "A" else ws_a

            ws_winner.send_json({"type": "choose_toss", "decision": "BAT"})
            ws_a.receive_json()
            ws_b.receive_json()

            ws_loser.send_json({"type": "select_bowler", "bowler_id": 11})
            ws_a.receive_json()
            ws_b.receive_json()
            ws_a.receive_json()  # turn 1 started
            ws_b.receive_json()

            # 1. Invalid numbers (0, 7, -1) rejected
            ws_a.send_json({"type": "submit_number", "turn_id": 1, "number": 7})
            err1 = ws_a.receive_json()
            assert err1["type"] == "error"
            assert err1["code"] == "invalid_number"

            ws_a.send_json({"type": "submit_number", "turn_id": 1, "number": 0})
            err2 = ws_a.receive_json()
            assert err2["type"] == "error"
            assert err2["code"] == "invalid_number"

            # 2. Future turn rejected
            ws_a.send_json({"type": "submit_number", "turn_id": 99, "number": 4})
            err_future = ws_a.receive_json()
            assert err_future["type"] == "error"
            assert err_future["code"] == "invalid_turn"

            # 3. Resolve Turn 1
            ws_a.send_json({"type": "submit_number", "turn_id": 1, "number": 1})
            ws_a.receive_json()
            ws_b.receive_json()
            ws_b.send_json({"type": "submit_number", "turn_id": 1, "number": 2})
            ws_a.receive_json()
            ws_b.receive_json()
            ws_a.receive_json()  # ball_result
            ws_b.receive_json()  # ball_result
            ws_a.receive_json()  # turn 2 started
            ws_b.receive_json()  # turn 2 started

            # 4. Stale turn_id=1 submission sent during turn 2 is dropped cleanly
            # without raising a second error frame that would break the UI!
            ws_a.send_json({"type": "submit_number", "turn_id": 1, "number": 3})
            # No error sent; Player A is still free to submit for turn 2
            ws_a.send_json({"type": "submit_number", "turn_id": 2, "number": 3})
            ack = ws_a.receive_json()
            assert ack["type"] == "number_submitted"
            assert ack["turn_id"] == 2


@pytest.mark.anyio
async def test_simultaneous_rapid_submissions_concurrency(manager: RoomManager):
    """Verify atomic concurrency when Player A and B submit simultaneously."""
    room, tok_a = await manager.create_room()
    _, tok_b = await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session: FriendGameSession = room.get_or_create_session()

    # Fast forward pre-match
    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    winner = session.pre_match.toss_winner
    await session.choose_toss(winner, "BAT")
    bowler_part = session.pre_match.first_bowler_selector_participant
    await session.select_bowler(bowler_part, 11)

    assert session.stage == RoomStage.IN_MATCH
    assert session.turn_number == 1

    # Launch concurrent submissions
    await asyncio.gather(
        session.submit_number(Participant.A, 4, turn_id=1),
        session.submit_number(Participant.B, 2, turn_id=1),
    )

    # Ball resolved, exactly 1 ball bowled
    assert session.match.innings_1.total_balls == 1
    # Turn advanced to 2
    assert session.turn_number == 2


@pytest.mark.anyio
async def test_turn_timeout_fallback_resolution(manager: RoomManager):
    """Verify that when a player times out, server fallback resolves ball exactly once."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    # Configure fast timeout: 0.05 seconds
    session = FriendGameSession(room=room, timeout_seconds=0.05)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    winner = session.pre_match.toss_winner
    await session.choose_toss(winner, "BAT")
    bowler_part = session.pre_match.first_bowler_selector_participant
    await session.select_bowler(bowler_part, 11)

    assert session.turn_number == 1

    # Only Player A submits on time
    await session.submit_number(Participant.A, 4, turn_id=1)

    # Wait for turn 1 deadline to expire (50ms < 80ms)
    await asyncio.sleep(0.08)

    # Ball 1 was resolved via Player B timeout!
    assert session.match.innings_1.total_balls == 1
    assert session.turn_number == 2

    # Clean up pending timeout task for turn 2
    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_both_players_timeout(manager: RoomManager):
    """Verify that if neither player submits, server generates fallback choices for both."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, timeout_seconds=0.05)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    winner = session.pre_match.toss_winner
    await session.choose_toss(winner, "BAT")
    bowler_part = session.pre_match.first_bowler_selector_participant
    await session.select_bowler(bowler_part, 11)

    # Wait for deadline with zero submissions
    await asyncio.sleep(0.08)

    assert session.match.innings_1.total_balls == 1
    assert session.turn_number == 2

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_over_completion_and_bowler_selection_handoff(manager: RoomManager):
    """Verify 6th ball over completion prompts fielding participant for next bowler."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room)
    room.session = session

    # India (A) bats, Australia (B) bowls
    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    # Opening bowler: Australia bowler 11
    await session.select_bowler(Participant.B, 11)

    # Bowl 5 balls in Over 1
    for turn_id in range(1, 6):
        await session.submit_number(Participant.A, 4, turn_id=turn_id)
        await session.submit_number(Participant.B, 2, turn_id=turn_id)
        assert session.stage == RoomStage.IN_MATCH

    # Bowl Ball 6 of Over 1
    await session.submit_number(Participant.A, 4, turn_id=6)
    await session.submit_number(Participant.B, 2, turn_id=6)

    # Over 1 complete: room transitions to BOWLER_SELECTION
    assert session.stage == RoomStage.BOWLER_SELECTION
    assert session.is_awaiting_bowler_selection is True

    # Batting participant (A) cannot select bowler
    with pytest.raises(TurnProtocolError, match="Only the fielding participant"):
        await session.select_bowler(Participant.A, 10)

    # Bowler 11 already bowled in Over 1; cannot be selected again
    with pytest.raises(TurnProtocolError, match="already bowled"):
        await session.select_bowler(Participant.B, 11)

    # Fielding participant (B) selects bowler 10
    await session.select_bowler(Participant.B, 10)
    assert session.stage == RoomStage.IN_MATCH
    assert session.is_awaiting_bowler_selection is False
    assert session.turn_number == 7

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_innings_break_and_start_innings_2(manager: RoomManager):
    """Verify innings 1 completion transitions to INNINGS_BREAK and start_innings_2 reverses roles."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    # 1 over per innings, 2 balls per over for quick testing
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Ball 1: A scores 4
    await session.submit_number(Participant.A, 4, turn_id=1)
    await session.submit_number(Participant.B, 2, turn_id=1)

    # Ball 2: A scores 6 (Innings 1 complete: 10 runs)
    await session.submit_number(Participant.A, 6, turn_id=2)
    await session.submit_number(Participant.B, 2, turn_id=2)

    assert session.stage == RoomStage.INNINGS_BREAK
    assert session.is_innings_break is True
    assert session.match.target == 11

    # Start innings 2
    await session.start_next_innings()
    assert session.stage == RoomStage.BOWLER_SELECTION
    assert session.is_awaiting_bowler_selection is True

    # In Innings 2: Team A (India) is fielding; Player A selects opening bowler
    await session.select_bowler(Participant.A, 11)
    assert session.stage == RoomStage.IN_MATCH
    assert session.turn_number == 3

    # Ball 1 of Innings 2: Australia (B) bats! B submits 6 -> scores 6
    await session.submit_number(Participant.A, 2, turn_id=3)
    await session.submit_number(Participant.B, 6, turn_id=3)
    assert session.match.innings_2_score == 6

    # Ball 2 of Innings 2: B submits 6 -> scores 12 (Target was 11 -> Match Completed!)
    await session.submit_number(Participant.A, 2, turn_id=4)
    await session.submit_number(Participant.B, 6, turn_id=4)

    assert session.stage == RoomStage.MATCH_COMPLETED
    assert session.match.is_completed is True
    assert session.match.winner == "Australia"
    # No further turns created
    assert session.turn_number == 4

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()

