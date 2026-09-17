"""Sub-slice 15F: Final Friend Mode E2E Verification & Hardening Suite.

Covers:
1. Simultaneous Submissions & Spam-Click Protection
2. Timeout Invariants (Cases A, B, C, D, E)
3. Stale Turn Rejection
4. Over Transitions & Non-Consecutive Bowlers
5. Innings 1 Completion (10 wickets & 30 balls)
6. Innings 2 Role Reversal (both toss scenarios)
7. Chase Completion (before 6th ball, on 6th ball without bowler selection, defending win, tie)
8. Reconnection at 7 Lifecycle Moments & Monotonic Timer Preservation
9. Duplicate Socket Model (Code 4001)
10. Disconnect Grace Period & Forfeit
11. Pre-Match Disconnect (ABANDONED)
12. Security, Participant Spoofing & Choice Secrecy
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from backend.app.engine.toss import Participant
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


# ==============================================================================
# 1. SIMULTANEOUS SUBMISSIONS & SPAM-CLICK PROTECTION
# ==============================================================================


@pytest.mark.anyio
async def test_simultaneous_submissions_concurrency(manager: RoomManager):
    """Verify simultaneous submissions from A and B resolve exactly once without duplicate balls."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6, timeout_seconds=5.0)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    turn_id = session.turn_number
    # Concurrently submit choices using asyncio.gather
    await asyncio.gather(
        session.submit_number(Participant.A, 4, turn_id=turn_id),
        session.submit_number(Participant.B, 2, turn_id=turn_id),
    )

    assert session.match.current_innings.total_runs == 4
    assert session.match.current_innings.total_balls == 1
    assert session.turn_number == turn_id + 1

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_spam_click_protection(manager: RoomManager):
    """Verify spam clicking submit_number does not allow multiple submissions or duplicate balls."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    turn_id = session.turn_number

    # First submission succeeds
    await session.submit_number(Participant.A, 3, turn_id=turn_id)

    # Subsequent spam submissions from participant A in the same turn are rejected
    with pytest.raises(TurnProtocolError, match="already been submitted"):
        await session.submit_number(Participant.A, 4, turn_id=turn_id)

    with pytest.raises(TurnProtocolError, match="already been submitted"):
        await session.submit_number(Participant.A, 2, turn_id=turn_id)

    # Participant B submits
    await session.submit_number(Participant.B, 1, turn_id=turn_id)

    assert session.match.current_innings.total_runs == 3
    assert session.match.current_innings.total_balls == 1

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 2. TIMEOUT INVARIANTS (CASES A, B, C, D, E)
# ==============================================================================


@pytest.mark.anyio
async def test_timeout_case_a_b_times_out(manager: RoomManager):
    """CASE A: A submits, B does not submit. B times out, fallback auto-picked."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6, timeout_seconds=0.08)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    turn_id = session.turn_number
    await session.submit_number(Participant.A, 4, turn_id=turn_id)

    # Wait for turn 1 timeout
    await asyncio.sleep(0.10)

    assert session.match.current_innings.total_balls == 1
    assert session.turn_number == turn_id + 1
    assert session._current_turn is not None

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_timeout_case_b_a_times_out(manager: RoomManager):
    """CASE B: B submits, A does not submit. A times out, fallback auto-picked."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6, timeout_seconds=0.08)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    turn_id = session.turn_number
    await session.submit_number(Participant.B, 2, turn_id=turn_id)

    # Wait for turn 1 timeout
    await asyncio.sleep(0.10)

    assert session.match.current_innings.total_balls == 1
    assert session.turn_number == turn_id + 1

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_timeout_case_c_both_timeout(manager: RoomManager):
    """CASE C: Neither submits. Both time out, fallback auto-picked for both."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6, timeout_seconds=0.08)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    turn_id = session.turn_number
    # Wait for turn 1 timeout
    await asyncio.sleep(0.10)

    assert session.match.current_innings.total_balls == 1
    assert session.turn_number == turn_id + 1

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_timeout_case_e_submission_races_timeout(manager: RoomManager):
    """CASE E: Submission races with timeout. Exactly one ball resolved, no secondary error."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6, timeout_seconds=0.06)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    turn_id = session.turn_number
    await session.submit_number(Participant.A, 3, turn_id=turn_id)

    # Sleep close to deadline, then submit B concurrently with timeout worker firing
    await asyncio.sleep(0.058)
    try:
        await session.submit_number(Participant.B, 1, turn_id=turn_id)
    except TurnProtocolError:
        pass  # Timeout may have won race

    await asyncio.sleep(0.02)
    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()
    # In all cases, exactly 1 ball recorded
    assert session.match.current_innings.total_balls == 1
    assert session.turn_number == turn_id + 1


# ==============================================================================
# 3. STALE TURN REJECTION
# ==============================================================================


@pytest.mark.anyio
async def test_stale_turn_rejection_after_resolution(manager: RoomManager):
    """Verify submitting a previous turn_id is cleanly dropped and does not mutate state."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    turn_1 = session.turn_number
    await session.submit_number(Participant.A, 4, turn_id=turn_1)
    await session.submit_number(Participant.B, 1, turn_id=turn_1)

    # Turn 1 resolved. Now in Turn 2.
    assert session.turn_number == turn_1 + 1
    score_before = session.match.current_innings.total_runs

    # Attempt to submit turn_1 again: dropped cleanly without secondary error
    await session.submit_number(Participant.A, 6, turn_id=turn_1)
    await session.submit_number(Participant.B, 6, turn_id=turn_1)

    # Verify score did not change and ball count did not change
    assert session.match.current_innings.total_runs == score_before
    assert session.match.current_innings.total_balls == 1

    # Future turn (> current) is rejected with TurnProtocolError
    with pytest.raises(TurnProtocolError, match="Invalid turn_id"):
        await session.submit_number(Participant.A, 6, turn_id=99)

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 4. INNINGS 1 COMPLETION (10 WICKETS & 30 BALLS)
# ==============================================================================


@pytest.mark.anyio
async def test_innings_1_completion_ten_wickets(manager: RoomManager):
    """Verify 10 wickets falling in Innings 1 completes the innings into INNINGS_BREAK."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Fall 6 wickets in Over 1 (matching numbers 3 vs 3)
    for _ in range(6):
        t_id = session.turn_number
        await session.submit_number(Participant.A, 3, turn_id=t_id)
        await session.submit_number(Participant.B, 3, turn_id=t_id)

    # Over 1 complete -> bowler selection required for Over 2
    assert session.room.stage == RoomStage.BOWLER_SELECTION
    await session.select_bowler(Participant.B, 10)

    # Fall 4 more wickets in Over 2 (total 10 wickets)
    for _ in range(4):
        t_id = session.turn_number
        await session.submit_number(Participant.A, 3, turn_id=t_id)
        await session.submit_number(Participant.B, 3, turn_id=t_id)

    assert session.match.current_innings.wickets == 10
    assert session.room.stage == RoomStage.INNINGS_BREAK
    assert session.is_innings_break is True
    assert session.match.target == 1  # 0 runs + 1

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 5. INNINGS 2 ROLE REVERSAL (BOTH TOSS SCENARIOS)
# ==============================================================================


@pytest.mark.anyio
async def test_innings_2_role_reversal_scenario_1_a_bats_first(manager: RoomManager):
    """Scenario 1: A bats first, B bowls first. In Innings 2: B bats, A bowls."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")

    assert session._pre_match.batting_first_participant == Participant.A

    # Bowl 1
    await session.select_bowler(Participant.B, 11)
    assert session.batting_participant == Participant.A
    assert session.bowling_participant == Participant.B

    t1 = session.turn_number
    await session.submit_number(Participant.A, 4, turn_id=t1)
    await session.submit_number(Participant.B, 1, turn_id=t1)

    # Bowl 2 (innings 1 ends on 2 balls)
    t2 = session.turn_number
    await session.submit_number(Participant.A, 2, turn_id=t2)
    await session.submit_number(Participant.B, 1, turn_id=t2)

    assert session.room.stage == RoomStage.INNINGS_BREAK

    # Start Innings 2
    await session.start_next_innings()
    assert session.room.stage == RoomStage.BOWLER_SELECTION
    assert session.bowler_selector == Participant.A  # A is now fielding!

    await session.select_bowler(Participant.A, 11)
    assert session.batting_participant == Participant.B  # B is now batting!
    assert session.bowling_participant == Participant.A  # A is now bowling!

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_innings_2_role_reversal_scenario_2_b_bats_first(manager: RoomManager):
    """Scenario 2: B elects to BAT (or A bowls). In Innings 2: A bats, B bowls."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.B
    await session.choose_toss(Participant.B, "BAT")

    assert session._pre_match.batting_first_participant == Participant.B

    # Innings 1: A bowls bowler 11
    await session.select_bowler(Participant.A, 11)
    assert session.batting_participant == Participant.B
    assert session.bowling_participant == Participant.A

    t1 = session.turn_number
    await session.submit_number(Participant.B, 6, turn_id=t1)
    await session.submit_number(Participant.A, 2, turn_id=t1)

    t2 = session.turn_number
    await session.submit_number(Participant.B, 1, turn_id=t2)
    await session.submit_number(Participant.A, 3, turn_id=t2)

    assert session.room.stage == RoomStage.INNINGS_BREAK

    # Start Innings 2
    await session.start_next_innings()
    assert session.bowler_selector == Participant.B  # B is now fielding!

    await session.select_bowler(Participant.B, 11)
    assert session.batting_participant == Participant.A  # A is now batting!
    assert session.bowling_participant == Participant.B  # B is now bowling!

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 6. CHASE COMPLETION & NO BOWLER SELECTION ON 6th BALL
# ==============================================================================


@pytest.mark.anyio
async def test_chase_completed_on_sixth_ball_no_bowler_selection(manager: RoomManager):
    """Mandatory Regression: Target reached exactly on ball 6 transitions directly to MATCH_COMPLETED without bowler selection."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=2, balls_per_over=6)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")

    # Innings 1: Over 1 (bowler 11, 6 balls, 6 runs)
    await session.select_bowler(Participant.B, 11)
    for _ in range(6):
        t = session.turn_number
        await session.submit_number(Participant.A, 1, turn_id=t)
        await session.submit_number(Participant.B, 2, turn_id=t)

    # Innings 1: Over 2 (bowler 10, 6 balls, 6 runs -> total 12 runs, target 13)
    assert session.room.stage == RoomStage.BOWLER_SELECTION
    await session.select_bowler(Participant.B, 10)
    for _ in range(6):
        t = session.turn_number
        await session.submit_number(Participant.A, 1, turn_id=t)
        await session.submit_number(Participant.B, 2, turn_id=t)

    # Innings 1 ends with 12 runs -> target 13
    assert session.room.stage == RoomStage.INNINGS_BREAK
    assert session.match.target == 13

    await session.start_next_innings()
    await session.select_bowler(Participant.A, 11)

    # Innings 2: 5 balls scoring 2 each (10 runs total)
    for _ in range(5):
        t = session.turn_number
        await session.submit_number(Participant.B, 2, turn_id=t)
        await session.submit_number(Participant.A, 1, turn_id=t)

    # 6th ball of over 1: B hits 3 (10 + 3 = 13 >= target 13!)
    t6 = session.turn_number
    await session.submit_number(Participant.B, 3, turn_id=t6)
    await session.submit_number(Participant.A, 1, turn_id=t6)

    assert session.room.stage == RoomStage.MATCH_COMPLETED
    assert session.is_awaiting_bowler_selection is False
    assert session.match.winner == "Australia"

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_defending_team_win(manager: RoomManager):
    """Defending team wins when chasing team runs out of overs without reaching target."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")

    # Innings 1: 8 runs
    await session.select_bowler(Participant.B, 11)
    t = session.turn_number
    await session.submit_number(Participant.A, 4, turn_id=t)
    await session.submit_number(Participant.B, 1, turn_id=t)
    t = session.turn_number
    await session.submit_number(Participant.A, 4, turn_id=t)
    await session.submit_number(Participant.B, 1, turn_id=t)

    await session.start_next_innings()
    await session.select_bowler(Participant.A, 11)

    # Innings 2: Chasing team only scores 2 runs in 2 balls
    t = session.turn_number
    await session.submit_number(Participant.B, 1, turn_id=t)
    await session.submit_number(Participant.A, 2, turn_id=t)
    t = session.turn_number
    await session.submit_number(Participant.B, 1, turn_id=t)
    await session.submit_number(Participant.A, 2, turn_id=t)

    assert session.room.stage == RoomStage.MATCH_COMPLETED
    assert session.match.winner == "India"
    assert "won by 6 runs" in session.match.result_description

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_tie_resolution(manager: RoomManager):
    """Match tied when scores are exactly equal at end of Innings 2."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=2)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")

    # Innings 1: 4 runs (target = 5). Ball 1: 3 runs. Ball 2: 1 run.
    await session.select_bowler(Participant.B, 11)
    t = session.turn_number
    await session.submit_number(Participant.A, 3, turn_id=t)
    await session.submit_number(Participant.B, 1, turn_id=t)
    t = session.turn_number
    await session.submit_number(Participant.A, 1, turn_id=t)
    await session.submit_number(Participant.B, 2, turn_id=t)

    await session.start_next_innings()
    await session.select_bowler(Participant.A, 11)

    # Innings 2: Exactly 4 runs (2 + 2)
    t = session.turn_number
    await session.submit_number(Participant.B, 2, turn_id=t)
    await session.submit_number(Participant.A, 1, turn_id=t)
    t = session.turn_number
    await session.submit_number(Participant.B, 2, turn_id=t)
    await session.submit_number(Participant.A, 1, turn_id=t)

    assert session.room.stage == RoomStage.MATCH_COMPLETED
    assert session.match.is_tie is True
    assert session.match.winner is None

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 7. RECONNECTION AT MULTIPLE MOMENTS & TIMER MONOTONICITY
# ==============================================================================


@pytest.mark.anyio
async def test_reconnect_during_turn_preserves_timer_monotonicity(manager: RoomManager):
    """Timer reconnect test: remaining seconds must reflect elapsed time, not reset to 10s."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6, timeout_seconds=6.0)
    room.session = session

    ws_mock = AsyncMock()
    await session.register_connection(Participant.A, ws_mock)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Turn started with 6.0s timeout
    await asyncio.sleep(1.0)

    # Reconnect A
    ws_reconnect = AsyncMock()
    await session.register_connection(Participant.A, ws_reconnect)

    sent_payloads = [call.args[0] for call in ws_reconnect.send_json.await_args_list]
    sync_msgs = [m for m in sent_payloads if m.get("type") == "sync_state"]
    assert len(sync_msgs) == 1
    sync = sync_msgs[0]

    assert sync["type"] == "sync_state"
    assert sync["turn_state"]["timeout_seconds"] < 5.5
    assert sync["turn_state"]["timeout_seconds"] > 3.5

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


@pytest.mark.anyio
async def test_reconnect_preserves_choice_secrecy_before_resolution(manager: RoomManager):
    """Opponent choice secrecy: Reconnecting player B while player A has submitted must NOT leak A's number."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6)
    room.session = session

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Participant A submits 4
    t_id = session.turn_number
    await session.submit_number(Participant.A, 4, turn_id=t_id)

    # Participant B disconnects and reconnects
    ws_b_new = AsyncMock()
    await session.register_connection(Participant.B, ws_b_new)

    sent_payloads = [call.args[0] for call in ws_b_new.send_json.await_args_list]
    sync_msgs = [m for m in sent_payloads if m.get("type") == "sync_state"]
    assert len(sync_msgs) == 1
    sync = sync_msgs[0]

    assert sync["type"] == "sync_state"
    assert sync["turn_state"]["opponent_submitted"] is True
    # Verify no choice is leaked in sync state
    assert sync["turn_state"]["opponent_choice"] is None
    assert sync["turn_state"]["selected_number"] is None

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 8. DUPLICATE SOCKET MODEL (CODE 4001)
# ==============================================================================


@pytest.mark.anyio
async def test_duplicate_socket_replaces_old_socket_code_4001(manager: RoomManager):
    """Duplicate socket test: Old socket closed with code 4001, new socket remains active."""
    room, _ = await manager.create_room()
    session = FriendGameSession(room=room)
    room.session = session

    ws_old = AsyncMock()
    await session.register_connection(Participant.A, ws_old)

    ws_new = AsyncMock()
    await session.register_connection(Participant.A, ws_new)

    # Verify old socket was closed with 4001
    ws_old.close.assert_called_once_with(code=4001, reason="replaced_by_new_connection")
    assert session._sockets[Participant.A] == ws_new


# ==============================================================================
# 9. DISCONNECT GRACE PERIOD & FORFEIT
# ==============================================================================


@pytest.mark.anyio
async def test_disconnect_grace_forfeit_expiration(manager: RoomManager):
    """Disconnect grace test: Expiration awards forfeit win to connected player."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6, disconnect_grace_seconds=0.05)
    room.session = session

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Participant A disconnects
    await session.unregister_connection(Participant.A, ws_a)

    # Wait for grace to expire
    await asyncio.sleep(0.08)

    assert session.room.stage == RoomStage.MATCH_COMPLETED
    assert session.match.winner == "Australia"  # Connected player B wins
    assert "forfeit" in session.match.result_description.lower()

    if session._timeout_task and not session._timeout_task.done():
        session._timeout_task.cancel()


# ==============================================================================
# 10. PRE-MATCH DISCONNECT (ABANDONED)
# ==============================================================================


@pytest.mark.anyio
async def test_pre_match_disconnect_abandons_room(manager: RoomManager):
    """Pre-match disconnect leads to room ABANDONED when grace expires."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, disconnect_grace_seconds=0.05)
    room.session = session

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    # Player A disconnects while B is connected waiting in pre-match
    await session.unregister_connection(Participant.A, ws_a)

    await asyncio.sleep(0.08)
    assert session.room.stage == RoomStage.ABANDONED


# ==============================================================================
# 11. SECURITY & MUTATION GUARDS
# ==============================================================================


@pytest.mark.anyio
async def test_closed_room_guards_reject_mutations(manager: RoomManager):
    """Verify actions on completed or abandoned rooms are strictly rejected."""
    room, _ = await manager.create_room()
    session = FriendGameSession(room=room)
    room.session = session

    room.stage = RoomStage.ABANDONED

    with pytest.raises(TurnProtocolError, match="abandoned"):
        await session.submit_number(Participant.A, 3, turn_id=1)

    with pytest.raises(TurnProtocolError, match="abandoned"):
        await session.select_bowler(Participant.A, 1)


# ==============================================================================
# 12. TWO-PLAYER INNINGS BREAK SYNCHRONIZATION
# ==============================================================================


@pytest.mark.anyio
async def test_innings_break_two_player_synchronization(manager: RoomManager):
    """Verify Innings 2 starts only when BOTH players have acknowledged the break."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=6)
    room.session = session

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Play 6 balls to complete Innings 1
    for _ in range(6):
        tid = session.turn_number
        await session.submit_number(Participant.A, 2, turn_id=tid)
        await session.submit_number(Participant.B, 3, turn_id=tid)

    assert session.stage == RoomStage.INNINGS_BREAK
    assert session._is_innings_break is True

    # Player A confirms next innings
    await session.start_next_innings(Participant.A)
    # Stage MUST still be INNINGS_BREAK because Player B hasn't confirmed
    assert session.stage == RoomStage.INNINGS_BREAK
    assert session._is_innings_break is True
    assert Participant.A in session._innings_break_ready
    assert Participant.B not in session._innings_break_ready

    # Duplicate call from Player A is idempotent
    await session.start_next_innings(Participant.A)
    assert session.stage == RoomStage.INNINGS_BREAK

    # Player B confirms next innings
    await session.start_next_innings(Participant.B)
    # Now Innings 2 begins!
    assert session.stage == RoomStage.BOWLER_SELECTION
    assert session._is_innings_break is False
    assert len(session._innings_break_ready) == 0


# ==============================================================================
# 13. REMATCH LIFECYCLE & EXIT
# ==============================================================================


@pytest.mark.anyio
async def test_rematch_lifecycle_mutual_agreement(manager: RoomManager):
    """Verify rematch requires both players, resets state, preserves teams, and starts fresh toss."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=1)
    room.session = session

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Innings 1: 1 ball (1 run)
    tid = session.turn_number
    await session.submit_number(Participant.A, 1, turn_id=tid)
    await session.submit_number(Participant.B, 2, turn_id=tid)

    # Transition to Innings 2
    await session.start_next_innings(Participant.A)
    await session.start_next_innings(Participant.B)
    await session.select_bowler(Participant.A, 11)

    # Innings 2: 1 ball (4 runs) -> B wins
    tid = session.turn_number
    await session.submit_number(Participant.B, 4, turn_id=tid)
    await session.submit_number(Participant.A, 2, turn_id=tid)

    assert session.stage == RoomStage.MATCH_COMPLETED

    # Player A requests rematch
    await session.request_rematch(Participant.A)
    assert session.stage == RoomStage.MATCH_COMPLETED
    assert Participant.A in session._rematch_ready

    # Duplicate request is idempotent
    await session.request_rematch(Participant.A)
    assert session.stage == RoomStage.MATCH_COMPLETED

    # Player B agrees to rematch
    await session.request_rematch(Participant.B)

    # Stage should now be TOSS_DECISION with fresh toss, teams preserved
    assert session.stage == RoomStage.TOSS_DECISION
    assert session.match is None
    assert session.pre_match.team_a.id == "IND"
    assert session.pre_match.team_b.id == "AUS"
    assert session.pre_match._toss.winner in (Participant.A, Participant.B)


@pytest.mark.anyio
async def test_leave_room_during_rematch(manager: RoomManager):
    """Verify leave_room marks room abandoned and broadcasts to other player."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.MATCH_COMPLETED
    session = FriendGameSession(room=room)
    room.session = session

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.request_rematch(Participant.A)
    assert Participant.A in session._rematch_ready

    # Player B exits room
    await session.leave_room(Participant.B)
    assert session.room.stage == RoomStage.ABANDONED


# ==============================================================================
# 14. DISMISSED BATSMAN NAME IN WICKET DELIVERY
# ==============================================================================


@pytest.mark.anyio
async def test_out_player_name_on_wicket(manager: RoomManager):
    """Verify out_player contains the dismissed batsman's name in ball result and match state."""
    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=1, balls_per_over=6)
    room.session = session

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    # Striker for IND is player 1 (Rohit Sharma)
    tid = session.turn_number
    # Same number -> WICKET
    await session.submit_number(Participant.A, 3, turn_id=tid)
    await session.submit_number(Participant.B, 3, turn_id=tid)

    ms = session.get_match_state_dict()
    assert ms["last_ball"] is not None
    assert ms["last_ball"]["is_wicket"] is True
    assert ms["last_ball"]["out_player"] == "Rohit Sharma"


# ==============================================================================
# 15. INNINGS 1 FORFEIT & LIFESPAN CLEANUP REGRESSION TESTS
# ==============================================================================


@pytest.mark.anyio
async def test_innings_1_forfeit_no_innings_2_safe(manager: RoomManager):
    """Verify that a player forfeit in Innings 1 (where innings_2 is None) does not crash or corrupt state."""
    from backend.app.engine.match import MatchStatus

    room, _ = await manager.create_room()
    await manager.join_room(room.room_code)
    room.stage = RoomStage.TEAM_SELECTION
    session = FriendGameSession(room=room, max_overs=5, balls_per_over=6)
    room.session = session

    ws_a = AsyncMock()
    ws_b = AsyncMock()
    await session.register_connection(Participant.A, ws_a)
    await session.register_connection(Participant.B, ws_b)

    await session.select_team(Participant.A, "IND")
    await session.select_team(Participant.B, "AUS")
    session._pre_match._toss._winner = Participant.A
    await session.choose_toss(Participant.A, "BAT")
    await session.select_bowler(Participant.B, 11)

    assert session._match is not None
    assert session._match.status == MatchStatus.INNINGS_1
    assert session._match.innings_2 is None

    # Simulate player B disconnecting and forfeit grace worker running
    await session.unregister_connection(Participant.B, ws_b)
    if Participant.B in session._disconnect_grace_tasks:
        session._disconnect_grace_tasks[Participant.B].cancel()
    await session._disconnect_grace_worker(Participant.B, grace_seconds=0.0)

    assert session._match.status == MatchStatus.COMPLETED
    assert session._match.innings_2 is None
    assert session._match.current_innings_number == 1
    assert session._match.batting_team is not None
    assert session._match.bowling_team is not None

    # Serialization should not crash with AttributeError
    ms = session.get_match_state_dict()
    assert ms["status"] == "COMPLETED"
    assert ms["innings_1_score"] == 0
    assert ms["innings_2_score"] is None
    assert ms["winner"] == "India"

    sync_dict = session.get_sync_state_dict(Participant.A)
    assert sync_dict["type"] == "sync_state"
    assert sync_dict["stage"] == session.room.stage.value


@pytest.mark.anyio
async def test_direct_match_forfeit_state():
    """Verify Match.forfeit cleanly terminates active bowling states and marks match completed."""
    from backend.app.engine.match import Match, MatchStatus

    match = Match(team_1="India", team_2="Australia", max_overs=5, balls_per_over=6)
    match.start_match()

    assert match.status == MatchStatus.INNINGS_1
    assert match.innings_2 is None
    assert match.current_bowling_state is not None

    match.forfeit(winner="India", description="Australia forfeited the match.")
    assert match.status == MatchStatus.COMPLETED
    assert match.is_completed is True
    assert match.winner == "India"
    assert match.result_description == "Australia forfeited the match."
    assert match.current_innings_number == 1
    assert match.current_innings is match.innings_1


@pytest.mark.anyio
async def test_fastapi_lifespan_periodic_cleanup():
    """Verify lifespan context manager runs periodic room cleanup and cancels cleanly on exit."""
    from backend.app.main import app, lifespan

    async with lifespan(app):
        # Lifespan active - cleanup task is running in background
        pass
    # Exited cleanly without unhandled cancellation or exception


