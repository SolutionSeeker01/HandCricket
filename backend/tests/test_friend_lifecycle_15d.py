"""Comprehensive tests for Friend Mode Sub-slice 15D:
Match Progression, Reconnection & Room Lifecycle.
"""

import asyncio
from unittest.mock import AsyncMock

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


# ==============================================================================
# 1. MULTI-OVER PROGRESSION & BOWLER ROTATION (5 overs, 5 unique bowlers)
# ==============================================================================


@pytest.mark.anyio
async def test_multi_over_progression_five_overs(manager: RoomManager):
    """Verify 5-over match progresses through 5 distinct bowlers with no consecutive overs."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6)
    room.session = session

    # Setup: A is IND (batting), B is AUS (bowling)
    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")

    # Australia squad bowlers: 7, 8, 9, 10, 11
    # Over 1: B selects Bowler 11
    await session.select_bowler(Participant.B, 11)
    assert session.stage == RoomStage.IN_MATCH
    assert session.current_bowler_id == 11

    # Over 1: 6 balls
    for b in range(1, 7):
        turn_id = b
        await session.submit_number(Participant.A, 2, turn_id=turn_id)
        await session.submit_number(Participant.B, 4, turn_id=turn_id)

    # Over 1 completes: transitions to BOWLER_SELECTION
    assert session.stage == RoomStage.BOWLER_SELECTION
    prompt = session.get_bowler_selection_prompt()
    assert prompt is not None
    assert prompt["current_over"] == 2
    eligible_ids = [b["id"] for b in prompt["eligible_bowlers"]]
    assert 11 not in eligible_ids  # Cannot bowl consecutive over

    # Cannot re-select Bowler 11
    with pytest.raises(TurnProtocolError, match="already bowled"):
        await session.select_bowler(Participant.B, 11)

    # Over 2: B selects Bowler 10
    await session.select_bowler(Participant.B, 10)
    assert session.stage == RoomStage.IN_MATCH
    assert session.current_bowler_id == 10

    for b in range(1, 7):
        turn_id = 6 + b
        await session.submit_number(Participant.A, 1, turn_id=turn_id)  # Odd run: strike rotates
        await session.submit_number(Participant.B, 3, turn_id=turn_id)

    # Over 2 completes
    assert session.stage == RoomStage.BOWLER_SELECTION

    # Over 3: B selects Bowler 9
    await session.select_bowler(Participant.B, 9)
    for b in range(1, 7):
        turn_id = 12 + b
        await session.submit_number(Participant.A, 4, turn_id=turn_id)
        await session.submit_number(Participant.B, 2, turn_id=turn_id)

    # Over 3 completes
    assert session.stage == RoomStage.BOWLER_SELECTION

    # Over 4: B selects Bowler 8
    await session.select_bowler(Participant.B, 8)
    for b in range(1, 7):
        turn_id = 18 + b
        await session.submit_number(Participant.A, 2, turn_id=turn_id)
        await session.submit_number(Participant.B, 6, turn_id=turn_id)

    # Over 4 completes
    assert session.stage == RoomStage.BOWLER_SELECTION

    # Over 5: B selects Bowler 7 (last remaining bowler)
    await session.select_bowler(Participant.B, 7)
    for b in range(1, 7):
        turn_id = 24 + b
        await session.submit_number(Participant.A, 1, turn_id=turn_id)
        await session.submit_number(Participant.B, 4, turn_id=turn_id)

    # Over 5 complete (all 30 balls bowled) -> Innings 1 completes -> INNINGS_BREAK
    assert session.stage == RoomStage.INNINGS_BREAK
    assert session.is_innings_break is True
    assert session.match.current_innings_number == 1
    assert session.match.target is not None

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 2. INNINGS 1 COMPLETION BY 10 WICKETS
# ==============================================================================


@pytest.mark.anyio
async def test_innings_1_completion_ten_wickets(manager: RoomManager):
    """Verify innings 1 terminates immediately upon 10 wickets falling across overs and sets target."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")

    # Over 1: Bowler 11 bowls, 6 wickets fall on balls 1..6
    await session.select_bowler(Participant.B, 11)
    for w in range(1, 7):
        turn_id = w
        await session.submit_number(Participant.A, 6, turn_id=turn_id)
        await session.submit_number(Participant.B, 6, turn_id=turn_id)

    # Over 1 complete (6 balls bowled): transition to BOWLER_SELECTION
    assert session.stage == RoomStage.BOWLER_SELECTION
    assert session.match.innings_1_wickets == 6

    # Over 2: Bowler 10 bowls, next 4 wickets fall (total 10 wickets)
    await session.select_bowler(Participant.B, 10)
    for w in range(1, 5):
        turn_id = 6 + w
        await session.submit_number(Participant.A, 6, turn_id=turn_id)
        await session.submit_number(Participant.B, 6, turn_id=turn_id)

    # 10 wickets lost: All Out!
    assert session.stage == RoomStage.INNINGS_BREAK
    assert session.is_innings_break is True
    assert session.match.innings_1_wickets == 10
    assert session.match.innings_1_score == 0
    assert session.match.target == 1  # 0 + 1

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 3. INNINGS BREAK & IDEMPOTENT START INNINGS 2 (ROLE REVERSAL)
# ==============================================================================


@pytest.mark.anyio
async def test_idempotent_start_innings_2_and_role_reversal(manager: RoomManager):
    """Verify start_innings_2 is idempotent and accurately reverses batting/bowling roles."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Play 2 balls in Innings 1
    await session.submit_number(Participant.A, 4, turn_id=1)
    await session.submit_number(Participant.B, 2, turn_id=1)
    await session.submit_number(Participant.A, 6, turn_id=2)
    await session.submit_number(Participant.B, 2, turn_id=2)

    assert session.stage == RoomStage.INNINGS_BREAK
    assert session.match.innings_1_score == 10
    assert session.match.target == 11

    # Call start_next_innings
    await session.start_next_innings()
    assert session.stage == RoomStage.BOWLER_SELECTION
    assert session.is_awaiting_bowler_selection is True
    assert session.bowler_selector == Participant.A  # Role reversal: Team A is bowling now!

    # Idempotence check: second call does not raise or mutate
    await session.start_next_innings()
    assert session.stage == RoomStage.BOWLER_SELECTION
    assert session.bowler_selector == Participant.A

    # Team A selects opening bowler 11
    await session.select_bowler(Participant.A, 11)
    assert session.stage == RoomStage.IN_MATCH
    assert session.batting_participant == Participant.B  # Team B is batting now!
    assert session.bowling_participant == Participant.A

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 4. CHASE COMPLETION ON 6TH BALL (NO ERRONEOUS BOWLER SELECTION)
# ==============================================================================


@pytest.mark.anyio
async def test_target_chase_on_sixth_ball_bypasses_bowler_selection(manager: RoomManager):
    """When target is reached on ball 6 of an over, match must complete immediately without over boundary."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=6)
    room.session = session

    # A (IND) bats, B (AUS) bowls
    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Innings 1: 6 balls, total score 6 runs -> Target is 7
    for b in range(1, 7):
        await session.submit_number(Participant.A, 1, turn_id=b)
        await session.submit_number(Participant.B, 2, turn_id=b)

    assert session.stage == RoomStage.INNINGS_BREAK
    assert session.match.target == 7  # 6 + 1

    # Start Innings 2: Australia (B) chases 7
    await session.start_next_innings()
    await session.select_bowler(Participant.A, 11)

    # Innings 2: Balls 1 to 5: B scores 1 run each (5 runs total)
    base_turn = session.turn_number
    for b in range(5):
        turn_id = base_turn + b
        await session.submit_number(Participant.A, 2, turn_id=turn_id)
        await session.submit_number(Participant.B, 1, turn_id=turn_id)
        assert session.stage == RoomStage.IN_MATCH

    assert session.match.innings_2_score == 5

    # Ball 6: B scores 4 runs -> total 9 runs >= target 7
    # This is the 6th ball of the over. Crucial: must complete MATCH, NOT transition to BOWLER_SELECTION!
    turn_id = base_turn + 5
    await session.submit_number(Participant.A, 2, turn_id=turn_id)
    await session.submit_number(Participant.B, 4, turn_id=turn_id)

    assert session.stage == RoomStage.MATCH_COMPLETED
    assert session.is_awaiting_bowler_selection is False
    assert session.match.is_completed is True
    assert session.match.winner == "Australia"

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 5. RECONNECTION: NEW SOCKET REPLACES OLD SOCKET & STATE SYNC SECRECY
# ==============================================================================


@pytest.mark.anyio
async def test_reconnection_duplicate_socket_and_state_sync(manager: RoomManager):
    """Verify that a new connection replaces the old connection (code 4001) and sync_state preserves secrecy."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room)
    room.session = session

    # Setup mock sockets
    old_ws_a = AsyncMock()
    ws_b = AsyncMock()

    await session.register_connection(Participant.A, old_ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    assert session.stage == RoomStage.IN_MATCH
    assert session.turn_number == 1

    # Player A submits 4
    await session.submit_number(Participant.A, 4, turn_id=1)

    # Verify Player B reconnects: new socket replaces old
    new_ws_b = AsyncMock()
    await session.register_connection(Participant.B, new_ws_b)

    # Old socket B was closed with 4001
    ws_b.close.assert_awaited_with(code=4001, reason="replaced_by_new_connection")

    # When unregistering the old socket, active connection is NOT removed because it was replaced!
    await session.unregister_connection(Participant.B, ws_b)
    assert session._sockets[Participant.B] == new_ws_b

    # Verify sync_state sent to new_ws_b
    sent_messages = [call.args[0] for call in new_ws_b.send_json.await_args_list]
    sync_msgs = [m for m in sent_messages if m.get("type") == "sync_state"]
    assert len(sync_msgs) == 1
    sync_b = sync_msgs[0]

    assert sync_b["stage"] == "IN_MATCH"
    assert sync_b["participant"] == "B"
    assert sync_b["turn_state"]["has_submitted"] is False
    assert sync_b["turn_state"]["opponent_submitted"] is True
    # SECRECY: Opponent's choice 4 MUST NOT be in sync_state!
    assert "number" not in sync_b["turn_state"]
    assert sync_b["turn_state"]["selected_number"] is None
    assert sync_b["turn_state"]["opponent_choice"] is None
    # Monotonic deadline: remaining seconds should be <= 10.0
    assert 0.0 < sync_b["turn_state"]["timeout_seconds"] <= 10.0

    # Now verify Player A sync_state has their own selected_number
    sync_a = session.get_sync_state_dict(Participant.A)
    assert sync_a["turn_state"]["has_submitted"] is True
    assert sync_a["turn_state"]["selected_number"] == 4

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 6. DISCONNECT GRACE PERIOD & FORFEIT WIN
# ==============================================================================


@pytest.mark.anyio
async def test_disconnect_grace_period_and_forfeit(manager: RoomManager):
    """Verify that disconnected player exceeding grace period triggers forfeit win for opponent."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room)
    room.session = session
    session._disconnect_grace_seconds = 0.05  # Fast grace period for testing

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    assert session.stage == RoomStage.IN_MATCH

    # Player B disconnects
    await session.unregister_connection(Participant.B, ws_b)
    assert Participant.B not in session._sockets
    assert Participant.B in session._disconnect_grace_tasks

    # Wait for grace period to expire
    await asyncio.sleep(0.08)

    # Forfeit win awarded to Player A (India)!
    assert session.stage == RoomStage.MATCH_COMPLETED
    assert session.match.is_completed is True
    assert session.match.winner == "India"
    assert "forfeit" in session.match.result_description.lower()

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_reconnect_within_grace_cancels_forfeit(manager: RoomManager):
    """Verify that reconnecting within grace period cleanly resumes play without forfeit."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room)
    room.session = session
    session._disconnect_grace_seconds = 0.2  # 200ms grace period

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Player B disconnects
    await session.unregister_connection(Participant.B, ws_b)
    assert Participant.B in session._disconnect_grace_tasks

    # Reconnect quickly after 30ms (< 200ms)
    await asyncio.sleep(0.03)
    ws_b2 = AsyncMock()
    await session.register_connection(Participant.B, ws_b2)

    # Grace task cancelled
    assert Participant.B not in session._disconnect_grace_tasks

    # Wait past the original 200ms grace window
    await asyncio.sleep(0.2)

    # Match must still be active and NOT forfeited!
    assert session.stage == RoomStage.IN_MATCH
    assert session.match.is_completed is False

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 7. CLOSED & ABANDONED ROOM ACTION REJECTION
# ==============================================================================


@pytest.mark.anyio
async def test_closed_room_action_rejection(manager: RoomManager):
    """Verify actions on closed or abandoned rooms are rejected."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.ABANDONED
    session = FriendGameSession(room=room)
    room.session = session

    with pytest.raises(TurnProtocolError, match="abandoned|closed"):
        await session.select_team(Participant.A, "IND")

    with pytest.raises(TurnProtocolError, match="abandoned|closed"):
        await session.choose_toss(Participant.A, "BAT")

    with pytest.raises(TurnProtocolError, match="abandoned|closed"):
        await session.select_bowler(Participant.B, 11)

    with pytest.raises(TurnProtocolError, match="abandoned|closed"):
        await session.submit_number(Participant.A, 4, turn_id=1)

    with pytest.raises(TurnProtocolError, match="abandoned|closed"):
        await session.start_next_innings()


# ==============================================================================
# 8. TIE MATCH RESOLUTION & DEFENDING TEAM WIN
# ==============================================================================


@pytest.mark.anyio
async def test_tie_match_resolution(manager: RoomManager):
    """Verify that match ends in a tie when innings 2 finishes with exact same score as innings 1."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Innings 1: 2 balls, 4 + 2 = 6 runs. Target = 7
    await session.submit_number(Participant.A, 4, turn_id=1)
    await session.submit_number(Participant.B, 1, turn_id=1)
    await session.submit_number(Participant.A, 2, turn_id=2)
    await session.submit_number(Participant.B, 1, turn_id=2)

    assert session.stage == RoomStage.INNINGS_BREAK
    assert session.match.target == 7

    # Start Innings 2: Australia (B) chases
    await session.start_next_innings()
    await session.select_bowler(Participant.A, 11)

    # Ball 1: B scores 4 runs (total 4)
    await session.submit_number(Participant.A, 1, turn_id=3)
    await session.submit_number(Participant.B, 4, turn_id=3)

    # Ball 2: B scores 2 runs (total 6 == Innings 1 total 6) -> End of 2 balls -> TIE!
    await session.submit_number(Participant.A, 1, turn_id=4)
    await session.submit_number(Participant.B, 2, turn_id=4)

    assert session.stage == RoomStage.MATCH_COMPLETED
    assert session.match.is_completed is True
    assert session.match.is_tie is True
    assert session.match.winner is None
    assert "tie" in session.match.result_description.lower()

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_defending_team_win(manager: RoomManager):
    """Verify defending team wins when chasing team is bowled out or runs out of deliveries."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Innings 1: 2 balls, scores 6 runs. Target = 7
    await session.submit_number(Participant.A, 6, turn_id=1)
    await session.submit_number(Participant.B, 1, turn_id=1)
    await session.submit_number(Participant.A, 6, turn_id=2)
    await session.submit_number(Participant.B, 2, turn_id=2)

    assert session.stage == RoomStage.INNINGS_BREAK
    assert session.match.target == 13

    # Start Innings 2: Australia (B) chases 13
    await session.start_next_innings()
    await session.select_bowler(Participant.A, 11)

    # Ball 1: B scores 2 runs
    await session.submit_number(Participant.A, 1, turn_id=3)
    await session.submit_number(Participant.B, 2, turn_id=3)

    # Ball 2: B is dismissed (matching 4)
    await session.submit_number(Participant.A, 4, turn_id=4)
    await session.submit_number(Participant.B, 4, turn_id=4)

    # Innings 2 complete: B scored 2 runs, target was 13 -> India (A) wins defending!
    assert session.stage == RoomStage.MATCH_COMPLETED
    assert session.match.is_completed is True
    assert session.match.winner == "India"
    assert "india won" in session.match.result_description.lower()

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 9. STRIKE ROTATION & OVER BOUNDARY SWAP
# ==============================================================================


@pytest.mark.anyio
async def test_strike_rotation_odd_runs_and_over_boundary(manager: RoomManager):
    """Verify odd runs rotate strike and over boundary swaps striker/non-striker."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=2, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Initial batsmen: Striker 1, Non-striker 2
    ms1 = session.get_match_state_dict()
    striker_start = ms1["striker"]["id"]
    non_striker_start = ms1["non_striker"]["id"]
    assert striker_start == 1
    assert non_striker_start == 2

    # Ball 1: A scores 1 (odd run) -> strike rotates!
    await session.submit_number(Participant.A, 1, turn_id=1)
    await session.submit_number(Participant.B, 3, turn_id=1)

    ms2 = session.get_match_state_dict()
    assert ms2["striker"]["id"] == 2
    assert ms2["non_striker"]["id"] == 1

    # Ball 2: A scores 2 (even run) -> no strike rotation during ball, BUT over ends so boundary swap happens!
    await session.submit_number(Participant.A, 2, turn_id=2)
    await session.submit_number(Participant.B, 4, turn_id=2)

    # Over 1 complete -> boundary swap puts Striker back to 1
    ms3 = session.get_match_state_dict()
    assert ms3["striker"]["id"] == 1
    assert ms3["non_striker"]["id"] == 2

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 10. PRE-MATCH DISCONNECT ABANDONMENT
# ==============================================================================


@pytest.mark.anyio
async def test_abandon_in_pre_match_lobby_on_disconnect(manager: RoomManager):
    """Verify disconnect during pre-match lobby abandons room when grace expires."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    session = FriendGameSession(room=room)
    room.session = session
    session._disconnect_grace_seconds = 0.05

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    assert session.stage == RoomStage.TEAM_SELECTION

    # Player B disconnects during TEAM_SELECTION
    await session.unregister_connection(Participant.B, ws_b)

    # Wait for grace period to expire
    await asyncio.sleep(0.08)

    # Room must transition to ABANDONED (not MATCH_COMPLETED because match never started)
    assert session.stage == RoomStage.ABANDONED
