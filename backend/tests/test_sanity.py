"""Baseline test harness verifying backend environment and health endpoint."""

import sys
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_python_environment_sanity():
    """Verify that Python environment meets minimum version requirement (3.11+)."""
    assert sys.version_info >= (3, 11), f"Python version must be >= 3.11, found: {sys.version}"


def test_app_instance_valid():
    """Verify that FastAPI application instance is properly configured."""
    assert app is not None
    assert app.title == "Hand Cricket API"


def test_health_check_endpoint():
    """Verify that /health endpoint is operational and returns expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "hand-cricket"}
