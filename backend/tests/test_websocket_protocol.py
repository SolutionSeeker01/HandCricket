"""Automated integration tests for WebSocket Game Protocol & Turn Timer (Slice 10)."""

import json
import pytest
from fastapi.testclient import TestClient

from backend.app.engine.computer import ComputerPlayer
from backend.app.main import app
from backend.app.protocol.session import TurnSession
from backend.app.transport.websocket import reset_standalone_turn_session

client = TestClient(app)


# ===========================================================================
# 1. Multi-Connection Ball Turn (Happy Path)
# ===========================================================================


def test_two_clients_full_turn_round_trip():
    """Requirement: Two independent clients connect, receive turn_started,
    submit choices, receive hidden acks, and both receive identical ball_result.
    """
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            # 1. Both receive turn_started when both are connected
            msg_a = ws_a.receive_json()
            msg_b = ws_b.receive_json()

            assert msg_a["type"] == "turn_started"
            assert msg_a["timeout_seconds"] == 5.0
            assert msg_b["type"] == "turn_started"

            # 2. Player A submits 4
            ws_a.send_json({"type": "submit_number", "number": 4})

            # 3. Both receive number_submitted (WITHOUT choice value!)
            ack_a = ws_a.receive_json()
            ack_b = ws_b.receive_json()

            assert ack_a["type"] == "number_submitted"
            assert ack_b["type"] == "number_submitted"
            # Hidden Choice Requirement: Neither ack contains the number
            assert "number" not in ack_a
            assert "number" not in ack_b

            # 4. Player B submits 2
            ws_b.send_json({"type": "submit_number", "number": 2})

            # 5. Both receive number_submitted for B's submission
            ack_b2_for_a = ws_a.receive_json()
            ack_b2_for_b = ws_b.receive_json()
            assert ack_b2_for_a["type"] == "number_submitted"
            assert ack_b2_for_b["type"] == "number_submitted"

            # 6. Both receive identical ball_result
            res_a = ws_a.receive_json()
            res_b = ws_b.receive_json()

            assert res_a == res_b
            assert res_a["type"] == "ball_result"
            assert res_a["batsman_choice"] == 4
            assert res_a["bowler_choice"] == 2
            assert res_a["runs"] == 4
            assert res_a["is_wicket"] is False
            assert res_a["choice_a"] == 4
            assert res_a["choice_b"] == 2
            assert res_a["a_timed_out"] is False
            assert res_a["b_timed_out"] is False


def test_hidden_choice_is_not_revealed_to_opponent():
    """Requirement: Neither player receives opponent's number before resolution."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()  # turn_started
            ws_b.receive_json()  # turn_started

            # A submits secret number 6
            ws_a.send_json({"type": "submit_number", "number": 6})

            # B receives number_submitted
            b_received = ws_b.receive_json()
            assert b_received["type"] == "number_submitted"
            # Explicitly verify 6 is not in the message
            assert 6 not in b_received.values()
            assert "number" not in b_received


# ===========================================================================
# 2. Timeout Fallback Over WebSocket
# ===========================================================================


def test_timeout_fallback_when_b_does_not_submit():
    """Requirement: A submits, B times out -> A's choice preserved, B gets fallback."""
    bot_b = ComputerPlayer(chooser=lambda: 2)
    session = TurnSession(
        timeout_seconds=0.05,
        computer_b=bot_b,
    )
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()  # turn_started
            ws_b.receive_json()  # turn_started

            # A submits 4
            ws_a.send_json({"type": "submit_number", "number": 4})
            ws_a.receive_json()  # number_submitted
            ws_b.receive_json()  # number_submitted

            # B does not submit; timer triggers fallback
            res_a = ws_a.receive_json()
            res_b = ws_b.receive_json()

            assert res_a == res_b
            assert res_a["type"] == "ball_result"
            assert res_a["choice_a"] == 4
            assert res_a["a_timed_out"] is False
            assert res_a["choice_b"] == 2
            assert res_a["b_timed_out"] is True
            assert res_a["runs"] == 4
            assert res_a["is_wicket"] is False


def test_timeout_fallback_when_a_does_not_submit():
    """Requirement: B submits, A times out -> B's choice preserved, A gets fallback."""
    bot_a = ComputerPlayer(chooser=lambda: 6)
    session = TurnSession(
        timeout_seconds=0.05,
        computer_a=bot_a,
    )
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()  # turn_started
            ws_b.receive_json()  # turn_started

            # B submits 6 (matching bot_a choice 6 -> wicket)
            ws_b.send_json({"type": "submit_number", "number": 6})
            ws_a.receive_json()  # number_submitted
            ws_b.receive_json()  # number_submitted

            # A does not submit; timer triggers
            res_a = ws_a.receive_json()
            res_b = ws_b.receive_json()

            assert res_a == res_b
            assert res_a["type"] == "ball_result"
            assert res_a["choice_a"] == 6
            assert res_a["a_timed_out"] is True
            assert res_a["choice_b"] == 6
            assert res_a["b_timed_out"] is False
            assert res_a["is_wicket"] is True
            assert res_a["runs"] == 0


def test_timeout_fallback_when_neither_submits():
    """Requirement: Neither submits -> both receive server-generated fallbacks."""
    bot_a = ComputerPlayer(chooser=lambda: 3)
    bot_b = ComputerPlayer(chooser=lambda: 1)
    session = TurnSession(
        timeout_seconds=0.05,
        computer_a=bot_a,
        computer_b=bot_b,
    )
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()  # turn_started
            ws_b.receive_json()  # turn_started

            # Neither submits; timer fires
            res_a = ws_a.receive_json()
            res_b = ws_b.receive_json()

            assert res_a == res_b
            assert res_a["type"] == "ball_result"
            assert res_a["choice_a"] == 3
            assert res_a["a_timed_out"] is True
            assert res_a["choice_b"] == 1
            assert res_a["b_timed_out"] is True
            assert res_a["runs"] == 3


def test_timer_cancelled_when_both_submit_in_time():
    """Requirement: Both submit before timeout -> timer is cancelled, no fallback."""
    session = TurnSession(timeout_seconds=1.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()
            ws_b.receive_json()

            ws_a.send_json({"type": "submit_number", "number": 1})
            ws_a.receive_json()
            ws_b.receive_json()

            ws_b.send_json({"type": "submit_number", "number": 6})
            ws_a.receive_json()
            ws_b.receive_json()

            res_a = ws_a.receive_json()
            res_b = ws_b.receive_json()

            assert res_a["type"] == "ball_result"
            assert res_a["a_timed_out"] is False
            assert res_a["b_timed_out"] is False


# ===========================================================================
# 3. Message Validation & Error Handling Over WebSocket
# ===========================================================================


@pytest.mark.parametrize(
    "bad_payload,expected_code",
    [
        ("not json", "malformed_json"),
        ("123", "non_object_json"),
        (json.dumps(["test"]), "non_object_json"),
        (json.dumps({"number": 4}), "missing_type"),
        (json.dumps({"type": "invalid_type"}), "unknown_message_type"),
        (json.dumps({"type": "submit_number"}), "missing_number"),
        (json.dumps({"type": "submit_number", "number": True}), "invalid_number"),
        (json.dumps({"type": "submit_number", "number": False}), "invalid_number"),
        (json.dumps({"type": "submit_number", "number": "4"}), "invalid_number"),
        (json.dumps({"type": "submit_number", "number": 0}), "invalid_number"),
        (json.dumps({"type": "submit_number", "number": 5}), "invalid_number"),
        (json.dumps({"type": "submit_number", "number": 7}), "invalid_number"),
        (json.dumps({"type": "submit_number", "number": -1}), "invalid_number"),
    ],
)
def test_websocket_message_validation_errors(bad_payload, expected_code):
    """Invalid client messages produce structured errors without crashing the connection."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()  # turn_started
            ws_b.receive_json()  # turn_started

            # Send invalid payload
            ws_a.send_text(bad_payload)
            err = ws_a.receive_json()

            assert err["type"] == "error"
            assert err["code"] == expected_code

            # Connection remains active; client can recover and submit a valid number
            ws_a.send_json({"type": "submit_number", "number": 4})
            ack = ws_a.receive_json()
            assert ack["type"] == "number_submitted"


def test_rejects_duplicate_submission_over_websocket():
    """Participant cannot submit twice; second submission receives error."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()
            ws_b.receive_json()

            # First submission succeeds
            ws_a.send_json({"type": "submit_number", "number": 3})
            assert ws_a.receive_json()["type"] == "number_submitted"
            ws_b.receive_json()

            # Second submission by A is rejected
            ws_a.send_json({"type": "submit_number", "number": 4})
            err = ws_a.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "duplicate_submission"


def test_rejects_submission_after_turn_completed_over_websocket():
    """Submissions after resolution receive turn_completed error."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()
            ws_b.receive_json()

            ws_a.send_json({"type": "submit_number", "number": 3})
            ws_a.receive_json()
            ws_b.receive_json()

            ws_b.send_json({"type": "submit_number", "number": 4})
            ws_a.receive_json()
            ws_b.receive_json()

            # Turn resolves
            ws_a.receive_json()  # ball_result
            ws_b.receive_json()  # ball_result

            # Further submission after completion is rejected
            ws_a.send_json({"type": "submit_number", "number": 2})
            err = ws_a.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "turn_completed"


# ===========================================================================
# 4. Security & Server Authority Tests
# ===========================================================================


def test_client_cannot_impersonate_other_participant():
    """Client cannot submit for the other participant through payload claims."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()
            ws_b.receive_json()

            # Client A tries to claim it is submitting for B
            ws_a.send_json({"type": "submit_number", "number": 4, "player": "B"})
            ws_a.receive_json()  # number_submitted
            ws_b.receive_json()

            # The server records this for A, NOT for B
            assert session.turn.choice_a == 4
            assert session.turn.choice_b is None


def test_invalid_participant_connection_rejected():
    """Connecting with an invalid participant query param receives error and closes."""
    with client.websocket_connect("/ws?participant=X") as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "invalid_participant"


def test_client_disconnect_handled_cleanly_without_server_error():
    """A client disconnecting during a session is handled cleanly without exceptions."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()
            ws_b.receive_json()
            ws_a.close()

        # Session unregisters A without crashing
        assert session.get_connection("A") is None


# ===========================================================================
# 5. Slice 10 Hardening Regression Tests (Duplicate Connections & Identity)
# ===========================================================================


def test_duplicate_participant_a_connection_rejected():
    """Requirement: Second connection for Participant A is rejected with structured error."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a1:
        # A second connection attempting to claim Participant A
        with client.websocket_connect("/ws?participant=A") as ws_a2:
            err = ws_a2.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "participant_already_connected"

        # The original connection A1 remains the authoritative connection
        assert session.get_connection("A") is not None


def test_duplicate_participant_b_connection_rejected():
    """Requirement: Second connection for Participant B is rejected with structured error."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b1:
            ws_a.receive_json()  # turn_started
            ws_b1.receive_json()  # turn_started

            # A second connection attempting to claim Participant B
            with client.websocket_connect("/ws?participant=B") as ws_b2:
                err = ws_b2.receive_json()
                assert err["type"] == "error"
                assert err["code"] == "participant_already_connected"

            # The original connection B1 remains the authoritative connection
            assert session.get_connection("B") is not None


def test_duplicate_disconnect_does_not_unregister_original_connection():
    """Requirement: When a rejected duplicate connection closes, it must not unregister
    the valid, original participant connection.
    """
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a1:
        # Open and immediately close a duplicate connection
        with client.websocket_connect("/ws?participant=A") as ws_a2:
            ws_a2.receive_json()  # participant_already_connected error

        # ws_a2 context has exited / closed.
        # ws_a1 MUST still be registered in the session!
        assert session.get_connection("A") is not None


def test_normal_interaction_succeeds_after_duplicate_rejection():
    """Requirement: A and B can complete a normal turn even after a duplicate attempt."""
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        # Duplicate A connection rejected
        with client.websocket_connect("/ws?participant=A") as ws_a_dup:
            assert ws_a_dup.receive_json()["code"] == "participant_already_connected"

        # Valid B connection connects
        with client.websocket_connect("/ws?participant=B") as ws_b:
            # Both receive turn_started
            assert ws_a.receive_json()["type"] == "turn_started"
            assert ws_b.receive_json()["type"] == "turn_started"

            # A submits 4
            ws_a.send_json({"type": "submit_number", "number": 4})
            assert ws_a.receive_json()["type"] == "number_submitted"
            assert ws_b.receive_json()["type"] == "number_submitted"

            # B submits 2
            ws_b.send_json({"type": "submit_number", "number": 2})
            assert ws_a.receive_json()["type"] == "number_submitted"
            assert ws_b.receive_json()["type"] == "number_submitted"

            # Both receive ball_result
            res_a = ws_a.receive_json()
            res_b = ws_b.receive_json()
            assert res_a == res_b
            assert res_a["type"] == "ball_result"
            assert res_a["choice_a"] == 4
            assert res_a["choice_b"] == 2
            assert res_a["runs"] == 4


def test_client_payload_participant_field_cannot_override_server_bound_identity():
    """Requirement: Payload field {"participant": "B"} on socket A does NOT change
    the server-bound participant identity.
    """
    session = TurnSession(timeout_seconds=5.0)
    reset_standalone_turn_session(session)

    with client.websocket_connect("/ws?participant=A") as ws_a:
        with client.websocket_connect("/ws?participant=B") as ws_b:
            ws_a.receive_json()
            ws_b.receive_json()

            # Socket A attempts to submit claiming {"participant": "B"}
            ws_a.send_json({"type": "submit_number", "number": 4, "participant": "B"})
            ws_a.receive_json()  # number_submitted
            ws_b.receive_json()  # number_submitted

            # Server recorded choice for A, NOT B
            assert session.turn.choice_a == 4
            assert session.turn.choice_b is None

            # Socket B can still submit its own choice
            ws_b.send_json({"type": "submit_number", "number": 1})
            ws_a.receive_json()
            ws_b.receive_json()

            res = ws_a.receive_json()
            assert res["choice_a"] == 4
            assert res["choice_b"] == 1

