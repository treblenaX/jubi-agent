"""
Jubi Multi-Agent Harness - Pytest Configuration

This module provides pytest fixtures and configuration for testing.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """Create a test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers with valid token."""
    # Login to get token
    response = client.post("/api/v1/auth/login", data={
        "username": "testuser",
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_message():
    """Sample user message for testing."""
    return "Hello, who are you?"


@pytest.fixture
def thread_config():
    """Thread configuration for agent invocation."""
    import time
    return {
        "configurable": {
            "thread_id": f"test-thread-{int(time.time())}",
            "thread_ts": time.time(),
        },
        "recursion_limit": 200,
    }
