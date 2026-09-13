"""Automated unit tests for Turn and Protocol message handling (Slice 10)."""

import pytest

from backend.app.engine.computer import ComputerPlayer
from backend.app.engine.toss import Participant
from backend.app.protocol.messages import (
    TYPE_BALL_RESULT,
    TYPE_ERROR,
    TYPE_NUMBER_SUBMITTED,
    TYPE_SUBMIT_NUMBER,
    TYPE_TURN_STARTED,
    TurnProtocolError,
    parse_client_message,
    serialize_ball_result,
    serialize_error,
    serialize_number_submitted,
    serialize_turn_started,
)
from backend.app.protocol.session import TurnSession
from backend.app.protocol.turn import Turn, TurnStatus


# ===========================================================================
# 1. Turn Model Basics & Lifecycle
# ===========================================================================


def test_turn_initial_state():
    """Turn starts in WAITING state with no choices and not completed."""
    turn = Turn(batting_participant=Participant.A)
    assert turn.status == TurnStatus.WAITING
    assert turn.is_completed is False
    assert turn.choice_a is None
    assert turn.choice_b is None
    assert turn.a_submitted is False
    assert turn.b_submitted is False
    assert turn.ball_result is None
    assert turn.batting_participant == Participant.A
    assert turn.bowling_participant == Participant.B


def test_first_submission_transitions_to_one_submitted():
    """First submission by A sets status to ONE_SUBMITTED and does not complete."""
    turn = Turn(batting_participant=Participant.A)
    completed = turn.submit_choice(Participant.A, 4)

    assert completed is False
    assert turn.status == TurnStatus.ONE_SUBMITTED
    assert turn.is_completed is False
    assert turn.choice_a == 4
    assert turn.a_submitted is True
    assert turn.choice_b is None
    assert turn.b_submitted is False


def test_second_submission_completes_and_resolves_turn():
    """Second submission completes turn and resolves authoritative ball result."""
    turn = Turn(batting_participant=Participant.A)
    turn.submit_choice(Participant.A, 4)
    completed = turn.submit_choice(Participant.B, 2)

    assert completed is True
    assert turn.status == TurnStatus.COMPLETED
    assert turn.is_completed is True
    assert turn.ball_result is not None
    assert turn.ball_result.runs == 4
    assert turn.ball_result.is_wicket is False
    assert turn.ball_result.batsman_choice == 4
    assert turn.ball_result.bowler_choice == 2


def test_ball_resolution_when_b_is_batsman():
    """Ball resolution correctly maps choices when Participant B is batsman."""
    turn = Turn(batting_participant=Participant.B)
    turn.submit_choice(Participant.A, 3)  # Bowler choice
    completed = turn.submit_choice(Participant.B, 5)  # Batsman choice

    assert completed is True
    assert turn.ball_result is not None
    assert turn.ball_result.batsman_choice == 5
    assert turn.ball_result.bowler_choice == 3
    assert turn.ball_result.runs == 5
    assert turn.ball_result.is_wicket is False


def test_ball_resolution_wicket_on_matching_numbers():
    """Matching choices result in a wicket and 0 runs."""
    turn = Turn(batting_participant=Participant.A)
    turn.submit_choice(Participant.A, 6)
    turn.submit_choice(Participant.B, 6)

    assert turn.is_completed is True
    assert turn.ball_result is not None
    assert turn.ball_result.runs == 0
    assert turn.ball_result.is_wicket is True


# ===========================================================================
# 2. Rejection of Invalid Submissions
# ===========================================================================


def test_rejects_duplicate_submission_same_participant():
    """A participant cannot submit twice in the same turn."""
    turn = Turn()
    turn.submit_choice(Participant.A, 3)

    with pytest.raises(TurnProtocolError) as exc_info:
        turn.submit_choice(Participant.A, 5)
    assert exc_info.value.code == "duplicate_submission"


def test_rejects_submission_after_turn_completed():
    """Submissions after turn completion are rejected with turn_completed."""
    turn = Turn()
    turn.submit_choice(Participant.A, 3)
    turn.submit_choice(Participant.B, 4)
    assert turn.is_completed is True

    with pytest.raises(TurnProtocolError) as exc_info:
        turn.submit_choice(Participant.A, 1)
    assert exc_info.value.code == "turn_completed"


@pytest.mark.parametrize("invalid_num", [0, 7, -1, 10, True, False, "4", None])
def test_rejects_invalid_number_choice(invalid_num):
    """Numbers outside [1, 6], booleans, and non-integers are rejected."""
    turn = Turn()
    with pytest.raises(TurnProtocolError) as exc_info:
        turn.submit_choice(Participant.A, invalid_num)  # type: ignore
    assert exc_info.value.code == "invalid_number"


# ===========================================================================
# 3. Timeout Fallback & Race Condition Protection
# ===========================================================================


def test_timeout_fallback_when_b_did_not_submit():
    """When A submits and B times out, A's choice is preserved and B gets fallback."""
    turn = Turn(batting_participant=Participant.A)
    turn.submit_choice(Participant.A, 4)

    # Injected computer returns 2 for B
    bot_b = ComputerPlayer(chooser=lambda: 2)
    result = turn.handle_timeout(computer_b=bot_b)

    assert turn.is_completed is True
    assert turn.choice_a == 4
    assert turn.a_timed_out is False
    assert turn.choice_b == 2
    assert turn.b_timed_out is True
    assert result.runs == 4


def test_timeout_fallback_when_a_did_not_submit():
    """When B submits and A times out, B's choice is preserved and A gets fallback."""
    turn = Turn(batting_participant=Participant.A)
    turn.submit_choice(Participant.B, 3)

    # Injected computer returns 3 for A (matching -> wicket)
    bot_a = ComputerPlayer(chooser=lambda: 3)
    result = turn.handle_timeout(computer_a=bot_a)

    assert turn.is_completed is True
    assert turn.choice_a == 3
    assert turn.a_timed_out is True
    assert turn.choice_b == 3
    assert turn.b_timed_out is False
    assert result.is_wicket is True


def test_timeout_fallback_when_neither_submitted():
    """When both time out, both receive server-generated choices."""
    turn = Turn(batting_participant=Participant.A)
    bot_a = ComputerPlayer(chooser=lambda: 5)
    bot_b = ComputerPlayer(chooser=lambda: 1)

    result = turn.handle_timeout(computer_a=bot_a, computer_b=bot_b)
    assert turn.is_completed is True
    assert turn.choice_a == 5
    assert turn.a_timed_out is True
    assert turn.choice_b == 1
    assert turn.b_timed_out is True
    assert result.runs == 5


def test_timeout_on_already_completed_turn_is_idempotent():
    """handle_timeout does not modify an already-completed turn."""
    turn = Turn()
    turn.submit_choice(Participant.A, 4)
    turn.submit_choice(Participant.B, 2)
    initial_res = turn.ball_result

    # Calling handle_timeout now must not overwrite choices or re-resolve
    bot = ComputerPlayer(chooser=lambda: 6)
    res_after = turn.handle_timeout(computer_a=bot, computer_b=bot)

    assert res_after == initial_res
    assert turn.choice_a == 4
    assert turn.choice_b == 2
    assert turn.a_timed_out is False
    assert turn.b_timed_out is False


# ===========================================================================
# 4. Protocol Message Serialization & Parsing
# ===========================================================================


def test_serialize_turn_started():
    """serialize_turn_started contains type and timeout_seconds."""
    payload = serialize_turn_started(5.0)
    assert payload == {"type": TYPE_TURN_STARTED, "timeout_seconds": 5.0}


def test_serialize_number_submitted_does_not_leak_number():
    """serialize_number_submitted contains only type, strictly hiding choices."""
    payload = serialize_number_submitted()
    assert payload == {"type": TYPE_NUMBER_SUBMITTED}
    assert "number" not in payload
    assert "choice" not in payload


def test_serialize_ball_result():
    """serialize_ball_result includes all required result details."""
    payload = serialize_ball_result(
        batsman_choice=4,
        bowler_choice=2,
        runs=4,
        is_wicket=False,
        batting_participant="A",
        bowling_participant="B",
        choice_a=4,
        choice_b=2,
    )
    assert payload["type"] == TYPE_BALL_RESULT
    assert payload["runs"] == 4
    assert payload["is_wicket"] is False
    assert payload["batsman_choice"] == 4
    assert payload["bowler_choice"] == 2
    assert payload["choice_a"] == 4
    assert payload["choice_b"] == 2


def test_serialize_error():
    """serialize_error includes code and message."""
    payload = serialize_error("invalid_number", "Number must be 1-6")
    assert payload == {
        "type": TYPE_ERROR,
        "code": "invalid_number",
        "message": "Number must be 1-6",
    }


def test_parse_valid_submit_number_message():
    """parse_client_message parses valid submit_number message."""
    msg = parse_client_message('{"type": "submit_number", "number": 4}')
    assert msg == {"type": TYPE_SUBMIT_NUMBER, "number": 4}


@pytest.mark.parametrize(
    "bad_json,expected_code",
    [
        ("{not valid json}", "malformed_json"),
        ("123", "non_object_json"),
        ('["submit_number"]', "non_object_json"),
        ('{"other": 1}', "missing_type"),
        ('{"type": ""}', "missing_type"),
        ('{"type": "unknown_action"}', "unknown_message_type"),
        ('{"type": "submit_number"}', "missing_number"),
        ('{"type": "submit_number", "number": true}', "invalid_number"),
        ('{"type": "submit_number", "number": false}', "invalid_number"),
        ('{"type": "submit_number", "number": "4"}', "invalid_number"),
        ('{"type": "submit_number", "number": 0}', "invalid_number"),
        ('{"type": "submit_number", "number": 7}', "invalid_number"),
        ('{"type": "submit_number", "number": -1}', "invalid_number"),
    ],
)
def test_parse_client_message_validation_errors(bad_json, expected_code):
    """parse_client_message raises structured TurnProtocolError for invalid input."""
    with pytest.raises(TurnProtocolError) as exc_info:
        parse_client_message(bad_json)
    assert exc_info.value.code == expected_code


# ===========================================================================
# 5. Encapsulation & Read-Only View (TurnView)
# ===========================================================================


def test_turn_view_exposes_read_only_properties():
    """TurnView exposes all 12 query properties matching Turn."""
    turn = Turn(batting_participant=Participant.A)
    turn.submit_choice(Participant.A, 4)
    turn.submit_choice(Participant.B, 2)
    view = turn.as_view()

    # 1. status
    assert view.status == TurnStatus.COMPLETED
    # 2. is_completed
    assert view.is_completed is True
    # 3. batting_participant
    assert view.batting_participant == Participant.A
    # 4. bowling_participant
    assert view.bowling_participant == Participant.B
    # 5. choice_a
    assert view.choice_a == 4
    # 6. choice_b
    assert view.choice_b == 2
    # 7. a_submitted
    assert view.a_submitted is True
    # 8. b_submitted
    assert view.b_submitted is True
    # 9. a_timed_out
    assert view.a_timed_out is False
    # 10. b_timed_out
    assert view.b_timed_out is False
    # 11. ball_result
    assert view.ball_result is not None
    assert view.ball_result.runs == 4
    assert view.ball_result.is_wicket is False
    # 12. has_choice()
    assert view.has_choice(Participant.A) is True
    assert view.has_choice(Participant.B) is True
    assert "TurnView" in repr(view)


def test_turn_view_prevents_mutations():
    """TurnView does not expose submit_choice, handle_timeout, or resolve."""
    turn = Turn(batting_participant=Participant.A)
    view = turn.as_view()

    assert not hasattr(view, "submit_choice")
    assert not hasattr(view, "handle_timeout")
    assert not hasattr(view, "resolve")


def test_turn_view_does_not_expose_underlying_turn():
    """TurnView does not expose the mutable Turn under the obvious _turn attribute."""
    turn = Turn(batting_participant=Participant.A)
    view = turn.as_view()

    assert not hasattr(view, "_turn")
    assert not hasattr(view, "turn")
    with pytest.raises(AttributeError):
        _ = view._turn  # type: ignore


def test_turn_session_turn_property_returns_read_only_view():
    """TurnSession.turn exposes TurnView, preventing external callers from mutating turn."""
    from backend.app.protocol.turn import TurnView

    session = TurnSession()
    assert isinstance(session.turn, TurnView)

    # Mutator methods unavailable
    assert not hasattr(session.turn, "submit_choice")
    assert not hasattr(session.turn, "handle_timeout")
    assert not hasattr(session.turn, "resolve")

    with pytest.raises(AttributeError):
        session.turn.submit_choice(Participant.A, 4)  # type: ignore

    with pytest.raises(AttributeError):
        session.turn.handle_timeout()  # type: ignore

    with pytest.raises(AttributeError):
        session.turn.resolve()  # type: ignore

    # Escape hatch _turn is unavailable
    assert not hasattr(session.turn, "_turn")
    assert not hasattr(session.turn, "turn")

    with pytest.raises(AttributeError):
        _ = session.turn._turn  # type: ignore


