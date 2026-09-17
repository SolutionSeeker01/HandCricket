"""TurnSession coordinator for Hand Cricket WebSocket game protocol (Slice 10).

This module coordinates two connected participants (Participant A and Participant B),
manages the 5-second server-authoritative turn timer with timeout fallbacks,
broadcasts messages without choice leakage, and ensures race-free ball resolution.

AUTHORITY & LIFECYCLE BOUNDARY:
- Participant identity in Slice 10 is managed as server-bound session context
  (e.g., via the test harness or route dependency). It is NOT an authentication
  mechanism. Real authenticated player accounts belong to later slices.
- Client messages cannot override or dictate participant identity.
- Duplicate connections for an already-connected participant are explicitly rejected.
- Direct mutation of Turn is prevented by exposing only a read-only TurnView.
"""

import asyncio
from typing import Any, Callable, Dict, Optional, Union

from fastapi import WebSocket

from backend.app.engine.computer import ComputerPlayer
from backend.app.engine.toss import Participant
from backend.app.protocol.messages import (
    TurnProtocolError,
    serialize_ball_result,
    serialize_error,
    serialize_number_submitted,
    serialize_turn_started,
)
from backend.app.protocol.turn import Turn, TurnView


def normalize_participant(participant: Union[Participant, str]) -> Participant:
    """Normalize a participant to the canonical Participant enum."""
    if isinstance(participant, Participant):
        return participant
    if isinstance(participant, str):
        norm = participant.strip().upper()
        if norm == "A":
            return Participant.A
        if norm == "B":
            return Participant.B
    raise TurnProtocolError(
        "invalid_participant",
        f"Invalid participant {participant!r}. Must be 'A' or 'B'.",
    )


class TurnSession:
    """Coordinates a single two-participant simultaneous turn over WebSocket connections.

    Invariants:
        - Server owns participant identity (Participant A and B).
        - Rejects duplicate connections for an already-connected participant.
        - Exposes only read-only TurnView to callers.
        - Turn timer is server-authoritative (5 seconds by default).
        - Timer task is immediately cancelled when both choices are submitted.
        - Timeout resolution is idempotent and protected against concurrent submissions.
        - Player choices remain completely hidden until ball resolution.
        - Result is broadcast to all active participants.
    """

    def __init__(
        self,
        turn: Optional[Turn] = None,
        timeout_seconds: float = 5.0,
        computer_a: Optional[ComputerPlayer] = None,
        computer_b: Optional[ComputerPlayer] = None,
        auto_start: bool = True,
    ) -> None:
        self._turn: Turn = turn if turn is not None else Turn()
        self._timeout_seconds: float = timeout_seconds
        self._computer_a: Optional[ComputerPlayer] = computer_a
        self._computer_b: Optional[ComputerPlayer] = computer_b
        self._auto_start: bool = auto_start

        self._connections: Dict[Participant, WebSocket] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._timer_task: Optional[asyncio.Task] = None
        self._turn_started: bool = False

    @property
    def turn(self) -> TurnView:
        """Read-only view over the underlying Turn domain object."""
        return self._turn.as_view()

    @property
    def is_completed(self) -> bool:
        """True if the turn has resolved."""
        return self._turn.is_completed

    @property
    def timeout_seconds(self) -> float:
        """Timeout duration in seconds."""
        return self._timeout_seconds

    @property
    def turn_started(self) -> bool:
        """True if turn_started has been broadcast."""
        return self._turn_started

    def get_connection(self, participant: Union[Participant, str]) -> Optional[WebSocket]:
        """Retrieve the active WebSocket for a participant, or None."""
        p_enum = normalize_participant(participant)
        return self._connections.get(p_enum)

    async def register_connection(
        self, participant: Union[Participant, str], websocket: WebSocket
    ) -> None:
        """Register a connected participant's WebSocket.

        If a live connection already exists for this participant, rejects with
        TurnProtocolError('participant_already_connected').

        If both Participant A and B are connected and auto_start is True,
        initiates the turn automatically.
        """
        p_enum = normalize_participant(participant)
        async with self._lock:
            if p_enum in self._connections:
                raise TurnProtocolError(
                    "participant_already_connected",
                    f"Participant {p_enum.value} is already connected to this session.",
                )

            self._connections[p_enum] = websocket
            # If both participants are present, start turn
            if (
                self._auto_start
                and not self._turn_started
                and Participant.A in self._connections
                and Participant.B in self._connections
            ):
                await self._start_turn_locked()

    async def unregister_connection(
        self,
        participant: Union[Participant, str],
        websocket: Optional[WebSocket] = None,
    ) -> None:
        """Remove a participant's WebSocket connection upon disconnect.

        If websocket is provided, only removes if the socket matches the current
        authoritative connection for that participant (preventing a rejected duplicate
        from unregistering the original connection).
        """
        p_enum = normalize_participant(participant)
        async with self._lock:
            if websocket is None or self._connections.get(p_enum) == websocket:
                self._connections.pop(p_enum, None)

    async def start_turn(self) -> None:
        """Explicitly start the turn, broadcast turn_started, and launch timer."""
        async with self._lock:
            await self._start_turn_locked()

    async def _start_turn_locked(self) -> None:
        """Internal helper to broadcast turn_started and launch timer under lock."""
        if self._turn_started or self._turn.is_completed:
            return

        self._turn_started = True
        msg = serialize_turn_started(self._timeout_seconds)
        await self._broadcast_locked(msg)

        # Launch background timer task if timeout > 0
        if self._timeout_seconds > 0:
            self._timer_task = asyncio.create_task(self._run_timer())

    async def _run_timer(self) -> None:
        """Asyncio background timer worker."""
        try:
            await asyncio.sleep(self._timeout_seconds)
            async with self._lock:
                if not self._turn.is_completed:
                    self._turn.handle_timeout(
                        computer_a=self._computer_a,
                        computer_b=self._computer_b,
                    )
                    await self._broadcast_result_locked()
        except asyncio.CancelledError:
            # Timer was cancelled because all choices were submitted in time
            pass

    async def trigger_timeout(self) -> None:
        """Manually and deterministically trigger timeout resolution (for testing)."""
        async with self._lock:
            if not self._turn.is_completed:
                if self._timer_task and not self._timer_task.done():
                    self._timer_task.cancel()
                self._turn.handle_timeout(
                    computer_a=self._computer_a,
                    computer_b=self._computer_b,
                )
                await self._broadcast_result_locked()

    async def submit_number(self, participant: Union[Participant, str], number: int) -> None:
        """Process a number submission from a participant.

        Args:
            participant: Server-owned Participant (A or B, enum or string).
            number: Integer choice in (1, 2, 3, 4, 6).

        Raises:
            TurnProtocolError: If turn completed, duplicate, or number invalid.
        """
        p_enum = normalize_participant(participant)
        async with self._lock:
            if self._turn.is_completed:
                raise TurnProtocolError("turn_completed", "Cannot submit: turn is already completed.")

            completed = self._turn.submit_choice(p_enum, number)

            # Broadcast acknowledgment WITHOUT revealing choice
            await self._broadcast_locked(serialize_number_submitted())

            if completed:
                # Cancel the timer immediately
                if self._timer_task and not self._timer_task.done():
                    self._timer_task.cancel()
                await self._broadcast_result_locked()

    async def _broadcast_result_locked(self) -> None:
        """Broadcast the resolved ball_result message to all connected participants."""
        assert self._turn.ball_result is not None
        assert self._turn.choice_a is not None
        assert self._turn.choice_b is not None

        msg = serialize_ball_result(
            batsman_choice=self._turn.ball_result.batsman_choice,
            bowler_choice=self._turn.ball_result.bowler_choice,
            runs=self._turn.ball_result.runs,
            is_wicket=self._turn.ball_result.is_wicket,
            batting_participant=self._turn.batting_participant.value,
            bowling_participant=self._turn.bowling_participant.value,
            choice_a=self._turn.choice_a,
            choice_b=self._turn.choice_b,
            a_timed_out=self._turn.a_timed_out,
            b_timed_out=self._turn.b_timed_out,
        )
        await self._broadcast_locked(msg)

    async def _broadcast_locked(self, msg: Dict[str, Any]) -> None:
        """Send JSON message to all connected active WebSockets."""
        for ws in list(self._connections.values()):
            try:
                await ws.send_json(msg)
            except Exception:
                # Sockets that have disconnected are handled safely
                pass

    async def broadcast(self, msg: Dict[str, Any]) -> None:
        """Public thread-safe broadcast method."""
        async with self._lock:
            await self._broadcast_locked(msg)
