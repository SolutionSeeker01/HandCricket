"""Automated tests for Backend HTTP & WebSocket Foundation (Slice 9)."""

import sys
import pytest
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


# ===========================================================================
# 4. Computer Mode Difficulty Parameter Verification (Phase 5)
# ===========================================================================


def test_websocket_computer_mode_defaults_to_easy(monkeypatch):
    """Requirement: /ws?mode=computer without difficulty parameter defaults to easy."""
    import backend.app.main as main_mod
    from backend.app.transport.websocket import reset_standalone_computer_session

    reset_standalone_computer_session(None)
    captured_sessions = []
    original_create = main_mod.create_computer_session

    def spy_create(*args, **kwargs):
        session = original_create(*args, **kwargs)
        captured_sessions.append(session)
        return session

    monkeypatch.setattr(main_mod, "create_computer_session", spy_create)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=true") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "turn_started"

    assert len(captured_sessions) == 1
    assert captured_sessions[0].difficulty.value == "easy"


@pytest.mark.parametrize("diff_str", ["easy", "medium", "hard"])
def test_websocket_computer_mode_explicit_difficulties(monkeypatch, diff_str):
    """Requirement: /ws?mode=computer passes valid difficulty (easy/medium/hard) to session."""
    import backend.app.main as main_mod
    from backend.app.transport.websocket import reset_standalone_computer_session

    reset_standalone_computer_session(None)
    captured_sessions = []
    original_create = main_mod.create_computer_session

    def spy_create(*args, **kwargs):
        session = original_create(*args, **kwargs)
        captured_sessions.append(session)
        return session

    monkeypatch.setattr(main_mod, "create_computer_session", spy_create)

    with client.websocket_connect(f"/ws?mode=computer&difficulty={diff_str}&skip_pre_match=true") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "turn_started"

    assert len(captured_sessions) == 1
    assert captured_sessions[0].difficulty.value == diff_str



def test_websocket_computer_mode_case_and_whitespace_insensitivity(monkeypatch):
    """Requirement: difficulty parameter is normalized (trimmed and case-folded)."""
    import backend.app.main as main_mod
    from backend.app.transport.websocket import reset_standalone_computer_session

    reset_standalone_computer_session(None)
    captured_sessions = []
    original_create = main_mod.create_computer_session

    def spy_create(*args, **kwargs):
        session = original_create(*args, **kwargs)
        captured_sessions.append(session)
        return session

    monkeypatch.setattr(main_mod, "create_computer_session", spy_create)

    with client.websocket_connect("/ws?mode=computer&difficulty=%20%20MEDIUM%20%20&skip_pre_match=true") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "turn_started"

    assert len(captured_sessions) == 1
    assert captured_sessions[0].difficulty.value == "medium"


def test_websocket_computer_mode_invalid_difficulty_rejected():
    """Requirement: invalid difficulty value returns structured error and closes cleanly."""
    from backend.app.transport.websocket import reset_standalone_computer_session

    reset_standalone_computer_session(None)

    with client.websocket_connect("/ws?mode=computer&difficulty=impossible") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "invalid_difficulty"
        assert "Must be one of ['easy', 'medium', 'hard']" in msg["message"]


def test_websocket_friend_mode_ignores_difficulty():
    """Requirement: Friend Mode connection ignores difficulty parameter."""
    # When connecting to friend mode with missing room/token, it fails with missing_parameters,
    # NOT invalid_difficulty, proving difficulty does not break friend mode routing.
    with client.websocket_connect("/ws?mode=friend&difficulty=hard") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "missing_parameters"
