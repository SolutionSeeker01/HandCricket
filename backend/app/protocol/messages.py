"""Protocol message definitions, validation, and serialization for Hand Cricket.

This module defines the JSON message schemas and validation rules for the
server-authoritative WebSocket game protocol in Slice 10.
"""

import json
from typing import Any, Dict, Optional

# Protocol message types
TYPE_TURN_STARTED: str = "turn_started"
TYPE_SUBMIT_NUMBER: str = "submit_number"
TYPE_NUMBER_SUBMITTED: str = "number_submitted"
TYPE_BALL_RESULT: str = "ball_result"
TYPE_ERROR: str = "error"


class TurnProtocolError(Exception):
    """Domain exception raised when a protocol or turn validation rule is violated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def serialize_turn_started(timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """Build the 'turn_started' message payload."""
    return {
        "type": TYPE_TURN_STARTED,
        "timeout_seconds": timeout_seconds,
    }


def serialize_number_submitted() -> Dict[str, Any]:
    """Build the 'number_submitted' message payload.

    CRITICAL: Never includes the submitted number, keeping choices hidden
    from both players until turn resolution.
    """
    return {
        "type": TYPE_NUMBER_SUBMITTED,
    }


def serialize_ball_result(
    batsman_choice: int,
    bowler_choice: int,
    runs: int,
    is_wicket: bool,
    batting_participant: str,
    bowling_participant: str,
    choice_a: int,
    choice_b: int,
    a_timed_out: bool = False,
    b_timed_out: bool = False,
) -> Dict[str, Any]:
    """Build the authoritative 'ball_result' message payload."""
    return {
        "type": TYPE_BALL_RESULT,
        "batsman_choice": batsman_choice,
        "bowler_choice": bowler_choice,
        "runs": runs,
        "is_wicket": is_wicket,
        "batting_participant": batting_participant,
        "bowling_participant": bowling_participant,
        "choice_a": choice_a,
        "choice_b": choice_b,
        "a_timed_out": a_timed_out,
        "b_timed_out": b_timed_out,
    }


def serialize_error(code: str, message: str) -> Dict[str, Any]:
    """Build a structured 'error' protocol message payload."""
    return {
        "type": TYPE_ERROR,
        "code": code,
        "message": message,
    }


def parse_client_message(raw_text: str) -> Dict[str, Any]:
    """Parse and validate an incoming client JSON message.

    Args:
        raw_text: Raw string received over the WebSocket.

    Returns:
        Validated message dictionary containing 'type' and any required fields.

    Raises:
        TurnProtocolError: If JSON is malformed, not an object, missing 'type',
            unknown 'type', or contains invalid parameters.
    """
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        raise TurnProtocolError("malformed_json", "Message must be valid JSON.")

    if not isinstance(data, dict):
        raise TurnProtocolError("non_object_json", "Message payload must be a JSON object.")

    msg_type = data.get("type")
    if not isinstance(msg_type, str) or not msg_type.strip():
        raise TurnProtocolError("missing_type", "Message must contain a valid 'type' string.")

    if msg_type != TYPE_SUBMIT_NUMBER:
        raise TurnProtocolError(
            "unknown_message_type", f"Unknown message type: {msg_type!r}."
        )

    # Validate submit_number parameters
    if "number" not in data:
        raise TurnProtocolError("missing_number", "Field 'number' is required for submit_number.")

    number = data["number"]
    # Reject boolean explicitly (in Python, isinstance(True, int) is True)
    if isinstance(number, bool) or not isinstance(number, int):
        raise TurnProtocolError(
            "invalid_number",
            f"Invalid choice {number!r}: choice must be an integer, got {type(number).__name__}.",
        )

    if number < 1 or number > 6:
        raise TurnProtocolError(
            "invalid_number",
            f"Invalid choice {number}: choice must be between 1 and 6.",
        )

    return {
        "type": TYPE_SUBMIT_NUMBER,
        "number": number,
    }
