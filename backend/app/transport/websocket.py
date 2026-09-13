"""WebSocket transport smoke test handler for Hand Cricket.

This module provides the baseline WebSocket connection handler used to verify
network transport connectivity in Slice 9. It explicitly avoids game-specific logic,
room coordination, timers, or domain engine mutation.
"""

from fastapi import WebSocket, WebSocketDisconnect


async def websocket_smoke_test(websocket: WebSocket) -> None:
    """Handle a basic WebSocket transport smoke-test connection.

    Accepts the client connection, responds to a standard transport-level
    'ping' message with 'pong', responds explicitly to unrecognized text,
    and cleanly handles normal client disconnects without raising unhandled exceptions.

    Args:
        websocket: The active FastAPI WebSocket connection instance.
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
        # Normal client disconnect cleanly handled without leaking exceptions
        pass
