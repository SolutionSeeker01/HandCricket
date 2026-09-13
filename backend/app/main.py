"""FastAPI main application entrypoint for Hand Cricket."""

from typing import Optional

from fastapi import FastAPI, Query, WebSocket

from backend.app.protocol.messages import serialize_error
from backend.app.transport.websocket import (
    get_standalone_turn_session,
    handle_turn_websocket,
    websocket_smoke_test,
)

app = FastAPI(
    title="Hand Cricket API",
    description="Backend API for Hand Cricket Web Game",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint to verify backend service availability."""
    return {"status": "ok", "app": "hand-cricket"}


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    participant: Optional[str] = Query(None),
) -> None:
    """WebSocket endpoint supporting both protocol turns and transport smoke testing.

    If query parameter 'participant' is provided (e.g. /ws?participant=A), connects the
    client to the standalone TurnSession under the Slice 10 WebSocket game protocol.
    If 'participant' is omitted, preserves Slice 9 transport smoke testing behavior.
    """
    if participant is not None:
        normalized = participant.strip().upper()
        if normalized not in ("A", "B"):
            await websocket.accept()
            await websocket.send_json(
                serialize_error(
                    "invalid_participant",
                    f"Invalid participant: {participant!r}. Must be 'A' or 'B'.",
                )
            )
            await websocket.close()
            return

        session = get_standalone_turn_session()
        await handle_turn_websocket(websocket, session, normalized)
    else:
        await websocket_smoke_test(websocket)
