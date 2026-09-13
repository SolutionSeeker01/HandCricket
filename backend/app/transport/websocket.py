"""WebSocket transport handlers for Hand Cricket.

This module provides the WebSocket connection handlers:
1. `handle_turn_websocket`: Manages real-time client interaction for a TurnSession
   under the Slice 10 WebSocket game protocol.
2. `websocket_smoke_test`: Preserves baseline transport smoke test functionality.

In accordance with architectural layering, this module imports ONLY from
FastAPI and the protocol layer (`backend.app.protocol.*`), with ZERO direct
dependencies on `backend.app.engine.*`.
"""

from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from backend.app.protocol.game import ComputerGameSession
from backend.app.protocol.messages import (
    TYPE_SUBMIT_NUMBER,
    TurnProtocolError,
    parse_client_message,
    serialize_error,
)
from backend.app.protocol.session import TurnSession

# Module-level standalone session for single-endpoint testing without a room manager
_standalone_session: Optional[TurnSession] = None
_standalone_computer_session: Optional[ComputerGameSession] = None


def get_standalone_turn_session() -> TurnSession:
    """Retrieve or initialize the active standalone TurnSession."""
    global _standalone_session
    if _standalone_session is None or _standalone_session.is_completed:
        _standalone_session = TurnSession()
    return _standalone_session


def reset_standalone_turn_session(
    session: Optional[TurnSession] = None,
) -> TurnSession:
    """Reset the standalone TurnSession (useful for test harnesses)."""
    global _standalone_session
    _standalone_session = session if session is not None else TurnSession()
    return _standalone_session


def get_standalone_computer_session(
    user_team: str = "IND", opponent_team: str = "AUS"
) -> ComputerGameSession:
    """Retrieve or initialize the active ComputerGameSession."""
    global _standalone_computer_session
    if _standalone_computer_session is None or _standalone_computer_session.match.is_completed:
        _standalone_computer_session = ComputerGameSession(
            user_team_id=user_team, opponent_team_id=opponent_team
        )
    return _standalone_computer_session


def reset_standalone_computer_session(
    session: Optional[ComputerGameSession] = None,
) -> ComputerGameSession:
    """Reset the standalone ComputerGameSession (useful for test harnesses)."""
    global _standalone_computer_session
    _standalone_computer_session = session if session is not None else ComputerGameSession()
    return _standalone_computer_session


async def handle_turn_websocket(
    websocket: WebSocket,
    session: TurnSession,
    participant: str,
) -> None:
    """Handle a client connection bound to a specific participant in a TurnSession.

    Execution flow:
    1. Accepts the WebSocket connection.
    2. Registers the connection with the TurnSession. If a live connection already
       exists for this participant, sends 'participant_already_connected' error and closes.
    3. Listens for incoming JSON messages and processes number submissions.
    4. Handles protocol violations by sending structured error messages.
    5. Cleanly unregisters the socket upon disconnection without leaking exceptions
       or unregistering other live connections.

    Args:
        websocket: Active FastAPI WebSocket instance.
        session: Active TurnSession coordinating the turn.
        participant: Server-authoritative Participant identifier ('A' or 'B').
    """
    await websocket.accept()

    try:
        await session.register_connection(participant, websocket)
    except TurnProtocolError as err:
        await websocket.send_json(serialize_error(err.code, err.message))
        await websocket.close()
        return

    try:
        while True:
            raw_text = await websocket.receive_text()

            # Transport smoke ping backward compatibility
            if raw_text == "ping":
                await websocket.send_text("pong")
                continue

            try:
                msg = parse_client_message(raw_text)
                if msg["type"] == TYPE_SUBMIT_NUMBER:
                    await session.submit_number(participant, msg["number"])
            except TurnProtocolError as err:
                await websocket.send_json(serialize_error(err.code, err.message))

    except (WebSocketDisconnect, RuntimeError):
        # Normal client disconnect cleanly handled
        pass
    finally:
        await session.unregister_connection(participant, websocket)


async def websocket_smoke_test(websocket: WebSocket) -> None:
    """Handle a basic WebSocket transport smoke-test connection.

    Preserves Slice 9 transport smoke testing behavior.
    """
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
            else:
                await websocket.send_text(f"unrecognized: {message}")
    except WebSocketDisconnect:
        pass


async def handle_computer_game_websocket(
    websocket: WebSocket,
    session: ComputerGameSession,
) -> None:
    """Handle a client connection playing against the computer (Slice 12 Computer Mode).

    Execution flow:
    1. Accepts the WebSocket connection.
    2. Registers connection with the ComputerGameSession (which broadcasts initial turn_started).
    3. Listens for incoming client messages (submit_number, start_innings_2, new_game, ping).
    4. Handles protocol errors gracefully and cleanly unregisters upon disconnect.
    """
    import json

    await websocket.accept()

    try:
        await session.register_connection(websocket)
    except Exception as err:
        await websocket.send_json(serialize_error("session_error", str(err)))
        await websocket.close()
        return

    try:
        while True:
            raw_text = await websocket.receive_text()

            # Transport smoke ping backward compatibility
            if raw_text == "ping":
                await websocket.send_text("pong")
                continue

            try:
                try:
                    payload = json.loads(raw_text)
                except Exception:
                    raise TurnProtocolError("malformed_json", "Message must be valid JSON.")

                if not isinstance(payload, dict):
                    raise TurnProtocolError("non_object_json", "Payload must be a JSON object.")

                msg_type = payload.get("type")
                if msg_type == "submit_number":
                    msg = parse_client_message(raw_text)
                    await session.submit_number(msg["number"], turn_id=msg.get("turn_id"))
                elif msg_type == "start_innings_2":
                    await session.start_next_innings()
                elif msg_type == "new_game":
                    await session.reset_game()
                else:
                    raise TurnProtocolError(
                        "unknown_message_type", f"Unknown message type: {msg_type!r}."
                    )
            except TurnProtocolError as err:
                await websocket.send_json(serialize_error(err.code, err.message))
            except Exception as err:
                await websocket.send_json(serialize_error("internal_error", str(err)))

    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await session.unregister_connection(websocket)

