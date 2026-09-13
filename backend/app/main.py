"""FastAPI main application entrypoint for Hand Cricket."""

from fastapi import FastAPI, WebSocket

from backend.app.transport.websocket import websocket_smoke_test

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
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Basic WebSocket transport smoke test endpoint."""
    await websocket_smoke_test(websocket)
