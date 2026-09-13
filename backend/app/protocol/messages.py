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

# Slice 13 Pre-Match message types
TYPE_PRE_MATCH_STATE: str = "pre_match_state"
TYPE_SELECT_TEAM: str = "select_team"
TYPE_CHOOSE_TOSS: str = "choose_toss"
TYPE_SELECT_BOWLER: str = "select_bowler"
TYPE_BOWLER_SELECTION_REQUIRED: str = "bowler_selection_required"
TYPE_RESET_PRE_MATCH: str = "reset_pre_match"
TYPE_START_INNINGS_2: str = "start_innings_2"
TYPE_NEW_GAME: str = "new_game"


class TurnProtocolError(Exception):
    """Domain exception raised when a protocol or turn validation rule is violated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def serialize_turn_started(timeout_seconds: float = 10.0) -> Dict[str, Any]:
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


def serialize_pre_match_state(
    stage: str,
    available_teams: list,
    user_team: Optional[Dict[str, Any]] = None,
    opponent_team: Optional[Dict[str, Any]] = None,
    toss_winner: Optional[str] = None,
    toss_decision: Optional[str] = None,
    batting_first: Optional[str] = None,
    bowling_first: Optional[str] = None,
    first_bowler_selector: Optional[str] = None,
    current_over: Optional[int] = None,
    eligible_bowlers: Optional[list] = None,
    used_bowlers: Optional[list] = None,
) -> Dict[str, Any]:
    """Build the authoritative 'pre_match_state' message payload."""
    return {
        "type": TYPE_PRE_MATCH_STATE,
        "stage": stage,
        "available_teams": available_teams,
        "user_team": user_team,
        "opponent_team": opponent_team,
        "toss_winner": toss_winner,
        "toss_decision": toss_decision,
        "batting_first": batting_first,
        "bowling_first": bowling_first,
        "first_bowler_selector": first_bowler_selector,
        "current_over": current_over,
        "eligible_bowlers": eligible_bowlers,
        "used_bowlers": used_bowlers,
    }


def serialize_bowler_selection_required(
    current_over: int,
    eligible_bowlers: list,
    used_bowlers: list,
    match_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the 'bowler_selection_required' message payload."""
    res: Dict[str, Any] = {
        "type": TYPE_BOWLER_SELECTION_REQUIRED,
        "current_over": current_over,
        "eligible_bowlers": eligible_bowlers,
        "used_bowlers": used_bowlers,
    }
    if match_state is not None:
        res["match_state"] = match_state
    return res


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

    if msg_type == TYPE_SUBMIT_NUMBER:
        if "number" not in data:
            raise TurnProtocolError("missing_number", "Field 'number' is required for submit_number.")

        number = data["number"]
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

        res: Dict[str, Any] = {
            "type": TYPE_SUBMIT_NUMBER,
            "number": number,
        }
        if "turn_id" in data:
            turn_id = data["turn_id"]
            if isinstance(turn_id, bool) or not isinstance(turn_id, int) or turn_id < 1:
                raise TurnProtocolError(
                    "invalid_turn_id",
                    f"Invalid turn_id {turn_id!r}: must be a positive integer.",
                )
            res["turn_id"] = turn_id
        return res

    elif msg_type == TYPE_SELECT_TEAM:
        if "team_id" not in data:
            raise TurnProtocolError("missing_team_id", "Field 'team_id' is required for select_team.")
        team_id = data["team_id"]
        if not isinstance(team_id, str) or not team_id.strip():
            raise TurnProtocolError("invalid_team_id", "Field 'team_id' must be a non-empty string.")
        return {
            "type": TYPE_SELECT_TEAM,
            "team_id": team_id.strip().upper(),
        }

    elif msg_type == TYPE_CHOOSE_TOSS:
        if "decision" not in data:
            raise TurnProtocolError("missing_decision", "Field 'decision' is required for choose_toss.")
        decision = data["decision"]
        if not isinstance(decision, str) or decision.strip().upper() not in ("BAT", "BOWL"):
            raise TurnProtocolError("invalid_decision", "Field 'decision' must be 'BAT' or 'BOWL'.")
        return {
            "type": TYPE_CHOOSE_TOSS,
            "decision": decision.strip().upper(),
        }

    elif msg_type == TYPE_SELECT_BOWLER:
        if "bowler_id" not in data:
            raise TurnProtocolError("missing_bowler_id", "Field 'bowler_id' is required for select_bowler.")
        bowler_id = data["bowler_id"]
        if isinstance(bowler_id, bool) or not isinstance(bowler_id, int) or bowler_id < 1 or bowler_id > 11:
            raise TurnProtocolError("invalid_bowler_id", "Field 'bowler_id' must be an integer between 1 and 11.")
        return {
            "type": TYPE_SELECT_BOWLER,
            "bowler_id": bowler_id,
        }

    elif msg_type == TYPE_RESET_PRE_MATCH:
        return {"type": TYPE_RESET_PRE_MATCH}

    elif msg_type in (TYPE_START_INNINGS_2, TYPE_NEW_GAME):
        return {"type": msg_type}

    else:
        raise TurnProtocolError(
            "unknown_message_type", f"Unknown message type: {msg_type!r}."
        )
