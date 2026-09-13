import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.app.engine.computer import ComputerPlayer
from backend.app.engine.toss import Participant
from backend.app.main import app
from backend.app.protocol.game import ComputerGameSession
from backend.app.protocol.messages import TurnProtocolError
from backend.app.transport.websocket import reset_standalone_computer_session

client = TestClient(app)


def test_computer_mode_connection_and_turn_started():
    """Client connecting with mode=computer receives turn_started with match state and 10s timeout."""
    session = ComputerGameSession()
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "turn_started"
        assert msg["timeout_seconds"] == 10.0
        assert "match_state" in msg

        state = msg["match_state"]
        assert state["status"] == "INNINGS_1"
        assert state["innings"] == 1
        assert state["score"] == 0
        assert state["wickets"] == 0
        assert state["user_team"]["id"] == "IND"
        assert state["opponent_team"]["id"] == "AUS"
        assert state["user_is_batting"] is True
        assert state["user_batted_first"] is True
        assert state["striker"]["name"] == "Rohit Sharma"
        assert state["striker"]["runs"] == 0
        assert state["non_striker"]["name"] == "Shubman Gill"
        assert state["bowler"]["name"] == "Josh Hazlewood"


def test_submit_number_resolves_ball_and_updates_score():
    """User submitting a number generates hidden ack and authoritative ball_result."""
    bot = ComputerPlayer(chooser=lambda: 2)
    session = ComputerGameSession(
        timeout_seconds=5.0,
        computer_bot=bot,
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer") as ws:
        init_msg = ws.receive_json()
        assert init_msg["type"] == "turn_started"

        # User submits 4 (user batting, bot bowling 2 -> 4 runs scored)
        ws.send_json({"type": "submit_number", "number": 4})

        ack = ws.receive_json()
        assert ack["type"] == "number_submitted"
        assert "number" not in ack

        result = ws.receive_json()
        assert result["type"] == "ball_result"
        assert result["runs"] == 4
        assert result["is_wicket"] is False
        assert result["batsman_choice"] == 4
        assert result["bowler_choice"] == 2

        state = result["match_state"]
        assert state["score"] == 4
        assert state["wickets"] == 0
        assert state["overs"] == "0.1"
        assert state["striker"]["runs"] == 4
        assert state["striker"]["balls"] == 1
        assert state["current_over_balls"] == [4]
        assert state["last_ball"]["event"] == "FOUR"

        # Next turn is automatically started
        next_turn = ws.receive_json()
        assert next_turn["type"] == "turn_started"


def test_wicket_event_on_matching_numbers():
    """Matching numbers result in wicket event and striker wicket increment."""
    bot = ComputerPlayer(chooser=lambda: 3)
    session = ComputerGameSession(
        timeout_seconds=5.0,
        computer_bot=bot,
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer") as ws:
        ws.receive_json()  # turn_started

        # User submits 3 -> bot chose 3 -> WICKET!
        ws.send_json({"type": "submit_number", "number": 3})
        ws.receive_json()  # number_submitted

        result = ws.receive_json()
        assert result["is_wicket"] is True
        assert result["runs"] == 0

        state = result["match_state"]
        assert state["wickets"] == 1
        assert state["score"] == 0
        assert state["current_over_balls"] == ["W"]
        assert state["last_ball"]["event"] == "WICKET"
        assert state["last_ball"]["out_player"] == "Rohit Sharma"


def test_six_boundary_event():
    """Choice 6 produces SIX event classification."""
    bot = ComputerPlayer(chooser=lambda: 1)
    session = ComputerGameSession(timeout_seconds=5.0, computer_bot=bot)
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer") as ws:
        ws.receive_json()  # turn_started
        ws.send_json({"type": "submit_number", "number": 6})
        ws.receive_json()  # number_submitted

        res = ws.receive_json()
        assert res["runs"] == 6
        assert res["match_state"]["last_ball"]["event"] == "SIX"


def test_innings_break_and_start_innings_2():
    """1-over innings completes to INNINGS_BREAK and transitions to INNINGS_2."""
    bot = ComputerPlayer(chooser=lambda: 2)
    session = ComputerGameSession(
        max_overs=1,
        balls_per_over=2,
        timeout_seconds=5.0,
        computer_bot=bot,
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer") as ws:
        ws.receive_json()  # turn_started

        # Ball 1
        ws.send_json({"type": "submit_number", "number": 4})
        ws.receive_json()  # ack
        ws.receive_json()  # result
        ws.receive_json()  # next turn

        # Ball 2 (Innings 1 finishes)
        ws.send_json({"type": "submit_number", "number": 4})
        ws.receive_json()  # ack
        res2 = ws.receive_json()  # result
        assert res2["match_state"]["status"] == "INNINGS_BREAK"
        assert res2["match_state"]["target"] == 9  # 8 runs + 1

        # Start Innings 2
        ws.send_json({"type": "start_innings_2"})
        in2_turn = ws.receive_json()
        assert in2_turn["type"] == "turn_started"
        assert in2_turn["match_state"]["status"] == "INNINGS_2"
        assert in2_turn["match_state"]["innings"] == 2
        assert in2_turn["match_state"]["user_is_batting"] is False
        assert in2_turn["match_state"]["score"] == 0
        assert in2_turn["match_state"]["target"] == 9


def test_new_game_resets_match():
    """Sending new_game resets the session back to fresh Innings 1."""
    session = ComputerGameSession(timeout_seconds=5.0)
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer") as ws:
        ws.receive_json()  # turn_started

        # Play a ball
        ws.send_json({"type": "submit_number", "number": 4})
        ws.receive_json()
        res = ws.receive_json()
        assert res["match_state"]["score"] >= 0
        ws.receive_json()  # next turn

        # Reset game
        ws.send_json({"type": "new_game"})
        reset_msg = ws.receive_json()
        assert reset_msg["type"] == "turn_started"
        assert reset_msg["match_state"]["status"] == "INNINGS_1"
        assert reset_msg["match_state"]["score"] == 0
        assert reset_msg["match_state"]["wickets"] == 0


def test_rapid_concurrent_submissions_records_one_ball_and_next_turn_playable():
    """Two rapid concurrent submissions for the same turn result in exactly one recorded ball,

    rejecting the duplicate submission with TurnProtocolError('already_submitted'), and leaving
    the next legitimate turn fully playable.
    """
    async def _run():
        bot = ComputerPlayer(chooser=lambda: 1)
        session = ComputerGameSession(timeout_seconds=5.0, computer_bot=bot)
        await session.start_turn()

        # Session initializes with turn 1 active (user batting, comp bowling)
        assert session.turn_number == 1
        assert session.is_turn_active is True

        # Launch two concurrent submissions for turn 1
        results = await asyncio.gather(
            session.submit_number(4),
            session.submit_number(4),
            return_exceptions=True,
        )

        # Exactly one succeeded and one raised TurnProtocolError("already_submitted")
        exceptions = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception)]

        assert len(successes) == 1
        assert len(exceptions) == 1
        assert isinstance(exceptions[0], TurnProtocolError)
        assert exceptions[0].code == "already_submitted"

        # Exactly one ball was recorded
        assert session.match.innings_1.total_balls == 1
        assert session.match.innings_1.total_runs == 4

        # Turn 2 is now active and playable
        assert session.turn_number == 2
        assert session.is_turn_active is True
        assert session.turn_submitted is False

        # Legitimate turn 2 submission succeeds and records ball 2
        await session.submit_number(6)
        assert session.match.innings_1.total_balls == 2
        assert session.match.innings_1.total_runs == 10
        assert session.turn_number == 3

    asyncio.run(_run())


def test_explicit_turn_id_duplicate_submission_rejected():
    """Submitting a choice with a stale or duplicate turn_id is rejected."""
    async def _run():
        bot = ComputerPlayer(chooser=lambda: 2)
        session = ComputerGameSession(timeout_seconds=5.0, computer_bot=bot)
        await session.start_turn()

        # Ball 1 for turn 1 succeeds
        await session.submit_number(3, turn_id=1)
        assert session.match.innings_1.total_balls == 1

        # Duplicate submission for turn 1 is rejected
        with pytest.raises(TurnProtocolError) as exc_info:
            await session.submit_number(3, turn_id=1)
        assert exc_info.value.code == "already_submitted"

        # Total balls remains 1
        assert session.match.innings_1.total_balls == 1
        assert session.turn_number == 2

        # Next turn with turn_id=2 succeeds
        await session.submit_number(3, turn_id=2)
        assert session.match.innings_1.total_balls == 2

    asyncio.run(_run())


def test_websocket_rapid_duplicate_submission_rejected_via_transport():
    """Two rapid submit_number messages over WebSocket produce one ball and an already_submitted error."""
    bot = ComputerPlayer(chooser=lambda: 1)
    session = ComputerGameSession(timeout_seconds=5.0, computer_bot=bot)
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer") as ws:
        init_turn = ws.receive_json()
        assert init_turn["type"] == "turn_started"
        turn_id = init_turn["turn_id"]

        # Send two submissions for turn 1
        ws.send_json({"type": "submit_number", "number": 4, "turn_id": turn_id})
        ws.send_json({"type": "submit_number", "number": 4, "turn_id": turn_id})

        # First submission generates ack + result + next turn_started
        ack = ws.receive_json()
        assert ack["type"] == "number_submitted"
        ball = ws.receive_json()
        assert ball["type"] == "ball_result"
        assert ball["match_state"]["score"] == 4
        next_turn = ws.receive_json()
        assert next_turn["type"] == "turn_started"

        # Second submission generates error
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "already_submitted"

        # Next turn is playable
        ws.send_json({"type": "submit_number", "number": 6, "turn_id": next_turn["turn_id"]})
        ack2 = ws.receive_json()
        assert ack2["type"] == "number_submitted"
        ball2 = ws.receive_json()
        assert ball2["type"] == "ball_result"
        assert ball2["match_state"]["score"] == 10


def test_websocket_stale_turn_id_rejected():
    """Transport-level stale turn_id rejection across turn boundary:

    Turn 1 starts
    -> submit turn_id=1
    -> Turn 2 starts
    -> send another message with stale turn_id=1
    -> must receive already_submitted error
    -> total balls remains 1
    -> submit turn_id=2
    -> exactly one additional ball (total balls = 2)
    """
    bot = ComputerPlayer(chooser=lambda: 1)
    session = ComputerGameSession(timeout_seconds=5.0, computer_bot=bot)
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer") as ws:
        # 1. Turn 1 starts
        turn1 = ws.receive_json()
        assert turn1["type"] == "turn_started"
        assert turn1["turn_id"] == 1

        # 2. Submit turn_id=1
        ws.send_json({"type": "submit_number", "number": 4, "turn_id": 1})
        ack1 = ws.receive_json()
        assert ack1["type"] == "number_submitted"
        res1 = ws.receive_json()
        assert res1["type"] == "ball_result"
        assert res1["match_state"]["score"] == 4
        assert session.match.innings_1.total_balls == 1

        # 3. Turn 2 starts
        turn2 = ws.receive_json()
        assert turn2["type"] == "turn_started"
        assert turn2["turn_id"] == 2

        # 4. Send delayed message with stale turn_id=1
        ws.send_json({"type": "submit_number", "number": 4, "turn_id": 1})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "already_submitted"

        # 5. Total balls remains 1
        assert session.match.innings_1.total_balls == 1

        # 6. Submit valid turn_id=2
        ws.send_json({"type": "submit_number", "number": 6, "turn_id": 2})
        ack2 = ws.receive_json()
        assert ack2["type"] == "number_submitted"
        res2 = ws.receive_json()
        assert res2["type"] == "ball_result"
        assert res2["match_state"]["score"] == 10

        # 7. Exactly one additional ball (total balls = 2)
        assert session.match.innings_1.total_balls == 2


def test_bowler_stats_sixth_ball_attribution_including_non_eleven_bowler():
    """Prove the 6th ball of an over is credited to that over's actual bowler,

    specifically testing Over 1 (bowler 11) and Over 2 (bowler 10, non-11 bowler).
    """
    async def _run():
        bot = ComputerPlayer(chooser=lambda: 1)
        session = ComputerGameSession(
            max_overs=2,
            balls_per_over=6,
            timeout_seconds=5.0,
            computer_bot=bot,
        )
        await session.start_turn()

        # Over 1: Australia bowler 11 (Josh Hazlewood)
        # Bowl 5 balls
        for _ in range(5):
            await session.submit_number(2)

        stats_11 = session.innings_1_bowler_stats[11]
        assert stats_11["balls"] == 5
        assert stats_11["runs"] == 10  # 5 * 2
        assert 10 not in session.innings_1_bowler_stats

        # Bowl ball 6 of Over 1
        await session.submit_number(2)
        assert stats_11["balls"] == 6
        assert stats_11["runs"] == 12
        # Over 1 completed, so match state reflects 6 balls
        assert session.match.innings_1.total_balls == 6

        # Over 2: Rotated to Australia bowler 10 (Pat Cummins, not ID 11!)
        # Bowl 5 balls in Over 2
        for _ in range(5):
            await session.submit_number(3)

        stats_10 = session.innings_1_bowler_stats[10]
        assert stats_10["balls"] == 5
        assert stats_10["runs"] == 15  # 5 * 3
        # Bowler 11 balls must remain exactly 6
        assert session.innings_1_bowler_stats[11]["balls"] == 6

        # Bowl ball 6 of Over 2 (sixth ball of a non-11 bowler's over!)
        await session.submit_number(3)

        # Bowler 10 must be credited with ball 6 (total 6 balls)
        assert session.innings_1_bowler_stats[10]["balls"] == 6
        assert session.innings_1_bowler_stats[10]["runs"] == 18
        # Bowler 11 must STILL have exactly 6 balls, NOT credited with bowler 10's 6th ball!
        assert session.innings_1_bowler_stats[11]["balls"] == 6
        assert session.innings_1_bowler_stats[11]["runs"] == 12

    asyncio.run(_run())


def test_computer_mode_default_timeout_is_10_seconds():
    """Verify ComputerGameSession defaults to a 10.0-second turn timeout."""
    session = ComputerGameSession()
    assert session._timeout_seconds == 10.0


def test_computer_mode_timeout_fallback_resolves_ball():
    """If user times out (tested with fast injected timeout), server generates random fallback choice and resolves ball."""
    async def _run():
        bot = ComputerPlayer(chooser=lambda: 3)
        session = ComputerGameSession(
            timeout_seconds=0.08,
            computer_bot=bot,
        )
        await session.start_turn()
        assert session.turn_number == 1
        assert session.is_turn_active is True

        # Wait for timer of turn 1 to expire (80ms < 110ms < 160ms)
        await asyncio.sleep(0.11)

        # Cancel pending timer for turn 2 so test leaves clean state
        if session._timer_task and not session._timer_task.done():
            session._timer_task.cancel()

        # Ball 1 was resolved via timeout fallback
        assert session.match.innings_1.total_balls == 1
        assert session.turn_number == 2
        assert session._last_ball_info is not None
        assert session._last_ball_info["user_timed_out"] is True

    asyncio.run(_run())


def test_chase_target_reached_on_sixth_ball_of_over_concludes_match_without_bowler_error():
    """Regression test for late-chase bug: Target reached on ball 6 of an over must conclude match without error.
    
    Exact user scenario:
    - Innings 2, user batting (IND), computer bowling (ENG).
    - Target: 95.
    - At Over 2.5, score is 90/1.
    - Ball 6 of Over 3 (Ball 18): user scores 6 (total: 96 >= 95).
    - Ball 6 completes the over (over_complete == True).
    - Must NOT raise MatchLifecycleError when trying to rotate bowler on completed match.
    - Must send ball_result with status COMPLETED and winner India.
    """
    class DummyWS:
        def __init__(self):
            self.messages = []
        async def send_json(self, msg):
            self.messages.append(msg)

    async def _run():
        session = ComputerGameSession(
            user_team_id="IND",
            opponent_team_id="ENG",
            skip_pre_match=False,
            timeout_seconds=0.0,
            toss_chooser=lambda: Participant.A,
        )
        ws = DummyWS()
        await session.register_connection(ws)

        # Pre-match: user chooses BOWL so ENG bats first
        await session.select_team("IND")
        if session.stage == "TOSS_DECISION":
            await session.choose_toss("BOWL")
        if session.stage == "BOWLER_SELECTION":
            await session.select_bowler(11)

        # Innings 1: Fast-forward 30 balls where ENG scores exactly 94 runs (Target = 95)
        # 10 fours (40) + 10 threes (30) + 1 six (6) + 9 twos (18) = 94 runs
        # User always bowls 1, so no wickets fall since computer never picks 1
        choices_innings_1 = [4]*10 + [3]*10 + [6]*1 + [2]*9
        session._bot = ComputerPlayer(chooser=lambda: choices_innings_1.pop(0) if choices_innings_1 else 2)
        for over in range(1, 6):
            if session._awaiting_bowler_selection:
                await session.select_bowler(session.match.bowling_1.eligible_bowlers[0])
            for _ in range(6):
                if session.is_innings_break:
                    break
                await session.submit_number(1)

        assert session.match.innings_1.total_runs == 94
        assert session.match.target == 95

        # Start Innings 2: User batting
        await session.start_next_innings()

        # Over 1: 36 runs (6 sixes)
        session._bot = ComputerPlayer(chooser=lambda: 1)
        for _ in range(6):
            await session.submit_number(6)

        # Over 2: 24 runs + 1 wicket (6, 6, 6, 4, 2, and wicket on ball 6) -> 60/1 in 2.0 overs
        await session.submit_number(6)
        await session.submit_number(6)
        await session.submit_number(6)
        await session.submit_number(4)
        await session.submit_number(2)
        session._bot = ComputerPlayer(chooser=lambda: 3)
        await session.submit_number(3) # Wicket!

        # Over 3: 5 balls of 6 = 30 runs -> 90/1 in 2.5 overs!
        session._bot = ComputerPlayer(chooser=lambda: 1)
        for _ in range(5):
            await session.submit_number(6)

        assert session.match.innings_2.total_runs == 90
        assert session.match.innings_2.wickets == 1
        assert session.match.innings_2.current_over == 3
        assert session.match.innings_2.balls_in_current_over == 5

        # BALL 6 OF OVER 3 (Ball 18): User submits 6 to reach target 95!
        # This ball BOTH completes the over (over_complete == True) AND reaches the target!
        await session.submit_number(6)

        # Match must be COMPLETED, not crashed!
        assert session.match.is_completed is True
        assert session.match.winner == "India"
        assert session.match.status.value == "COMPLETED"

        # Verify WebSocket received ball_result with COMPLETED status
        last_ball_msg = [m for m in ws.messages if m.get("type") == "ball_result"][-1]
        assert last_ball_msg["match_state"]["status"] == "COMPLETED"
        assert last_ball_msg["match_state"]["winner"] == "India"
        assert last_ball_msg["match_state"]["score"] == 96
        assert last_ball_msg["match_state"]["overs"] == "3.0"

        # Verify turn did NOT restart on completed match
        assert session.is_turn_active is False
        assert session._awaiting_bowler_selection is False

    asyncio.run(_run())


def test_chase_target_reached_before_over_end_concludes_match():
    """Boundary variant: Target reached on ball 3 of an over concludes match cleanly."""
    async def _run():
        session = ComputerGameSession(
            user_team_id="IND",
            opponent_team_id="ENG",
            skip_pre_match=False,
            timeout_seconds=0.0,
            toss_chooser=lambda: Participant.A,
        )
        await session.select_team("IND")
        await session.choose_toss("BOWL")
        await session.select_bowler(11)

        # Innings 1: 6 balls of 2 = 12 runs in Over 1
        session._bot = ComputerPlayer(chooser=lambda: 2)
        for _ in range(6):
            await session.submit_number(1)

        # Over 2 starts: select bowler
        if session._awaiting_bowler_selection:
            await session.select_bowler(session.match.bowling_1.eligible_bowlers[0])

        # 10 wickets in Over 2 (comp 1, user 1)
        session._bot = ComputerPlayer(chooser=lambda: 1)
        for _ in range(10):
            if session.is_innings_break:
                break
            if session._awaiting_bowler_selection:
                await session.select_bowler(session.match.bowling_1.eligible_bowlers[0])
            await session.submit_number(1)

        assert session.is_innings_break is True
        assert session.match.target == 13

        # Innings 2: User batting
        await session.start_next_innings()
        session._bot = ComputerPlayer(chooser=lambda: 1)
        # Ball 1: 6 runs
        await session.submit_number(6)
        # Ball 2: 6 runs (Total 12)
        await session.submit_number(6)
        assert session.match.is_completed is False
        assert session.match.innings_2.balls_in_current_over == 2

        # Ball 3: 4 runs (Total 16 >= 13) - Target reached BEFORE over ends!
        await session.submit_number(4)
        assert session.match.is_completed is True
        assert session.match.winner == "India"
        assert session.is_turn_active is False

    asyncio.run(_run())


def test_chase_target_not_reached_on_sixth_ball_rotates_bowler_normally():
    """Boundary variant: Target not reached on ball 6 rotates bowler and starts next turn."""
    async def _run():
        session = ComputerGameSession(
            user_team_id="IND",
            opponent_team_id="ENG",
            skip_pre_match=False,
            timeout_seconds=0.0,
            toss_chooser=lambda: Participant.A,
        )
        await session.select_team("IND")
        await session.choose_toss("BOWL")
        await session.select_bowler(11)

        # Innings 1: 30 balls of 2 = 60 runs (Target 61)
        session._bot = ComputerPlayer(chooser=lambda: 2)
        for over in range(1, 6):
            if session._awaiting_bowler_selection:
                await session.select_bowler(session.match.bowling_1.eligible_bowlers[0])
            for _ in range(6):
                if session.is_innings_break:
                    break
                await session.submit_number(1)

        assert session.match.target == 61
        await session.start_next_innings()

        # Innings 2: Over 1 (balls 1 to 5): 5 runs each (Total 25 < 61)
        session._bot = ComputerPlayer(chooser=lambda: 1)
        for _ in range(5):
            await session.submit_number(5)

        assert session.match.innings_2.balls_in_current_over == 5
        first_bowler = session._last_bowler_id

        # Ball 6: 4 runs (Total 29 < 61). Over completes, target NOT reached!
        await session.submit_number(4)

        assert session.match.is_completed is False
        assert session.match.innings_2.current_over == 2
        assert session.match.innings_2.balls_in_current_over == 0
        # Computer rotated bowler
        assert session._last_bowler_id != first_bowler
        # Next turn started
        assert session.is_turn_active is True

    asyncio.run(_run())


def test_chase_computer_batting_reaches_target_on_sixth_ball_no_bowler_prompt():
    """Boundary variant: Computer batting reaches target on ball 6, user is NOT prompted for bowler."""
    class DummyWS:
        def __init__(self):
            self.messages = []
        async def send_json(self, msg):
            self.messages.append(msg)

    async def _run():
        session = ComputerGameSession(
            user_team_id="IND",
            opponent_team_id="AUS",
            skip_pre_match=False,
            timeout_seconds=0.0,
            toss_chooser=lambda: Participant.A,
            computer_team_chooser=lambda: "AUS",
        )
        ws = DummyWS()
        await session.register_connection(ws)

        # User bats first, sets small target (10 runs, target 11)
        await session.select_team("IND")
        assert session.stage == "TOSS_DECISION"
        await session.choose_toss("BAT")

        # Innings 1: User scores 10 runs then gets out
        session._bot = ComputerPlayer(chooser=lambda: 1)
        await session.submit_number(6) # 6
        await session.submit_number(4) # 10
        session._bot = ComputerPlayer(chooser=lambda: 2)
        # 10 wickets to end innings
        for _ in range(10):
            if session.is_innings_break:
                break
            await session.submit_number(2)

        assert session.match.target == 11
        await session.start_next_innings()

        # Innings 2: Computer is batting, User is bowling
        # Need user to select first bowler for Over 1
        assert session._awaiting_bowler_selection is True
        await session.select_bowler(11)

        # 5 balls of 1 run (comp 1, user 2) -> Total 5 runs in 5 balls
        session._bot = ComputerPlayer(chooser=lambda: 1)
        for _ in range(5):
            await session.submit_number(2)

        assert session.match.innings_2.balls_in_current_over == 5
        assert session.match.innings_2.total_runs == 5

        # Ball 6: Computer hits 6! (comp 6, user 2) -> Total 11 >= 11 (TARGET REACHED on ball 6!)
        session._bot = ComputerPlayer(chooser=lambda: 6)
        await session.submit_number(2)

        # Match must be completed, winner Australia
        assert session.match.is_completed is True
        assert session.match.winner == "Australia"

        # User MUST NOT be prompted for bowler selection on completed match!
        assert session._awaiting_bowler_selection is False
        bowler_req_msgs = [m for m in ws.messages if m.get("type") == "bowler_selection_required"]
        # Only the initial Over 1 prompt, none after target reached
        assert len(bowler_req_msgs) == 1

    asyncio.run(_run())



