"""FastAPI main application entrypoint for Hand Cricket."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import os
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.protocol.messages import serialize_error
from backend.app.protocol.room_manager import (
    RoomClosedError,
    RoomFullError,
    RoomNotFoundError,
    get_room_manager,
)
from backend.app.transport.websocket import (
    create_computer_session,
    get_standalone_computer_session,
    get_standalone_turn_session,
    handle_computer_game_websocket,
    handle_friend_game_websocket,
    handle_turn_websocket,
    websocket_smoke_test,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan, including periodic background cleanup of stale rooms."""
    async def periodic_cleanup() -> None:
        while True:
            try:
                await asyncio.sleep(60)
                await get_room_manager().cleanup_stale_rooms()
            except asyncio.CancelledError:
                break
            except Exception:
                # Keep cleanup loop resilient
                pass

    cleanup_task = asyncio.create_task(periodic_cleanup())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Hand Cricket API",
    description="Backend API for Hand Cricket Web Game",
    version="0.1.0",
    lifespan=lifespan,
)


class CreateRoomResponse(BaseModel):
    room_code: str
    player_token: str
    participant: str


class JoinRoomResponse(BaseModel):
    room_code: str
    player_token: str
    participant: str


class RoomInfoResponse(BaseModel):
    room_code: str
    stage: str
    open_slots: int
    is_available: bool


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint to verify backend service availability."""
    return {"status": "ok", "app": "hand-cricket"}


@app.get("/teams")
def get_predefined_teams() -> list:
    """Retrieve the 4 predefined teams with complete 11-player rosters."""
    from backend.app.engine.teams import get_teams
    return [
        {
            "id": team.id,
            "name": team.name,
            "players": [{"id": p.id, "name": p.name} for p in team.players],
        }
        for team in get_teams()
    ]


@app.post("/api/rooms", status_code=201, response_model=CreateRoomResponse)
async def create_room_endpoint() -> CreateRoomResponse:
    """Create a new Friend Mode room and allocate Participant A seat for host."""
    room_manager = get_room_manager()
    room, token_a = await room_manager.create_room()
    return CreateRoomResponse(
        room_code=room.room_code,
        player_token=token_a,
        participant="A",
    )


@app.post("/api/rooms/{code}/join", status_code=200, response_model=JoinRoomResponse)
async def join_room_endpoint(code: str) -> JoinRoomResponse:
    """Atomically claim Participant B seat for joining player."""
    room_manager = get_room_manager()
    try:
        room, token_b = await room_manager.join_room(code)
        return JoinRoomResponse(
            room_code=room.room_code,
            player_token=token_b,
            participant="B",
        )
    except RoomNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "room_not_found", "message": f"Room {code.upper()} not found."},
        )
    except RoomClosedError:
        raise HTTPException(
            status_code=404,
            detail={"code": "room_closed", "message": f"Room {code.upper()} is closed."},
        )
    except RoomFullError:
        raise HTTPException(
            status_code=409,
            detail={"code": "room_full", "message": f"Room {code.upper()} is already full."},
        )


@app.get("/api/rooms/{code}", status_code=200, response_model=RoomInfoResponse)
async def get_room_info_endpoint(code: str) -> RoomInfoResponse:
    """Retrieve room availability information for pre-join verification."""
    room_manager = get_room_manager()
    room = await room_manager.get_room(code)
    if room is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "room_not_found", "message": f"Room {code.upper()} not found."},
        )
    return RoomInfoResponse(
        room_code=room.room_code,
        stage=room.stage.value,
        open_slots=room.open_slots,
        is_available=not room.is_full,
    )


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    participant: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    user_team: Optional[str] = Query("IND"),
    opponent_team: Optional[str] = Query("AUS"),
    skip_pre_match: Optional[bool] = Query(False),
    room: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
) -> None:
    """WebSocket endpoint supporting Computer Mode, Friend Mode, protocol turns, and smoke testing."""
    if mode == "computer":
        selected_difficulty = "easy"
        if difficulty is not None and difficulty.strip():
            norm_difficulty = difficulty.strip().lower()
            if norm_difficulty not in ("easy", "medium", "hard"):
                await websocket.accept()
                await websocket.send_json(
                    serialize_error(
                        "invalid_difficulty",
                        f"Invalid difficulty: {difficulty!r}. Must be one of ['easy', 'medium', 'hard'].",
                    )
                )
                await websocket.close(code=4000)
                return
            selected_difficulty = norm_difficulty

        session = create_computer_session(
            user_team=user_team or "IND",
            opponent_team=opponent_team or "AUS",
            skip_pre_match=bool(skip_pre_match),
            difficulty=selected_difficulty,
        )
        await handle_computer_game_websocket(websocket, session)
        return

    if mode == "friend":
        if not room or not token:
            await websocket.accept()
            await websocket.send_json(
                serialize_error(
                    "missing_parameters",
                    "Query parameters 'room' and 'token' are required for mode=friend.",
                )
            )
            await websocket.close(code=4000)
            return
        await handle_friend_game_websocket(websocket, room_code=room, token=token)
        return

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


@app.websocket("/ws/friend")
async def websocket_friend_endpoint(
    websocket: WebSocket,
    room: str = Query(...),
    token: str = Query(...),
) -> None:
    """Dedicated WebSocket endpoint for Friend Mode."""
    await handle_friend_game_websocket(websocket, room_code=room, token=token)


# ---------------------------------------------------------------------------
# Static Frontend SPA Serving (Slice 12 / Production Hardening)
# ---------------------------------------------------------------------------
dist_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
)
if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    audio_dir = os.path.join(dist_dir, "audio")
    if os.path.exists(audio_dir):
        app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return {"status": "ok", "app": "hand-cricket"}

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path in ("health", "teams", "ws", "ws/friend"):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = os.path.join(dist_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend build not found")


