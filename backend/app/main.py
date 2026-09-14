"""FastAPI main application entrypoint for Hand Cricket."""

from typing import Optional

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, WebSocket

from backend.app.protocol.messages import serialize_error
from backend.app.protocol.room_manager import (
    RoomClosedError,
    RoomFullError,
    RoomNotFoundError,
    get_room_manager,
)
from backend.app.transport.websocket import (
    get_standalone_computer_session,
    get_standalone_turn_session,
    handle_computer_game_websocket,
    handle_friend_game_websocket,
    handle_turn_websocket,
    websocket_smoke_test,
)

app = FastAPI(
    title="Hand Cricket API",
    description="Backend API for Hand Cricket Web Game",
    version="0.1.0",
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
) -> None:
    """WebSocket endpoint supporting Computer Mode, Friend Mode, protocol turns, and smoke testing."""
    if mode == "computer":
        session = get_standalone_computer_session(
            user_team=user_team or "IND",
            opponent_team=opponent_team or "AUS",
            skip_pre_match=bool(skip_pre_match),
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


