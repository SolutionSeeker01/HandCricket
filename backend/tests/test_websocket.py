"""Automated tests for Backend HTTP & WebSocket Foundation (Slice 9)."""

import sys
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


# ===========================================================================
# 1. HTTP Health Endpoint Verification
# ===========================================================================


def test_health_endpoint_status_and_payload():
    """Requirement: GET /health returns 200 with expected JSON response."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "hand-cricket"}


# ===========================================================================
# 2. WebSocket Transport Smoke Test Verification
# ===========================================================================


def test_websocket_accepts_connection_and_clean_disconnect():
    """Requirement: Endpoint accepts connection and disconnects cleanly."""
    with client.websocket_connect("/ws") as ws:
        # Connection established successfully
        assert ws is not None


def test_websocket_ping_pong():
    """Requirement: Client sends 'ping', server acknowledges with 'pong'."""
    with client.websocket_connect("/ws") as ws:
        ws.send_text("ping")
        response = ws.receive_text()
        assert response == "pong"


def test_websocket_multiple_sequential_pings():
    """Requirement: Sequential messages on the same connection work independently."""
    with client.websocket_connect("/ws") as ws:
        for _ in range(5):
            ws.send_text("ping")
            response = ws.receive_text()
            assert response == "pong"


def test_websocket_unrecognized_text_is_explicitly_handled():
    """Requirement: Unexpected text receives an explicit unrecognized response."""
    with client.websocket_connect("/ws") as ws:
        ws.send_text("hello")
        response = ws.receive_text()
        assert response == "unrecognized: hello"

        ws.send_text("action:play")
        response = ws.receive_text()
        assert response == "unrecognized: action:play"


def test_websocket_explicit_client_close():
    """Requirement: Normal client close does not raise unhandled exceptions."""
    with client.websocket_connect("/ws") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"
        ws.close()


# ===========================================================================
# 3. Transport and Domain Separation Verification
# ===========================================================================


def test_transport_module_has_zero_domain_imports():
    """Requirement: Transport code must not import or couple to domain engine."""
    import backend.app.transport.websocket as ws_mod

    # Inspect module globals and imported symbols
    for name, val in vars(ws_mod).items():
        if hasattr(val, "__module__") and val.__module__:
            assert not val.__module__.startswith("backend.app.engine"), (
                f"Transport module imports domain engine symbol: {name} from {val.__module__}"
            )
