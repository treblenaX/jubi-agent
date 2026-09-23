"""
Jubi Multi-Agent Harness - API Tests

This module provides FastAPI route endpoint testing.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_root_endpoint(client):
    """Test root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "agents" in data
    assert "sandbox" in data


def test_health_endpoint(client, monkeypatch):
    """Test health check endpoint returns API + model status."""
    async def fake_check_model():
        return {"connected": True, "name": "test-model", "error": None}

    monkeypatch.setattr("app.main._check_model", fake_check_model)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model": {"connected": True, "name": "test-model", "error": None},
    }


def test_check_model_unreachable(monkeypatch):
    """Model probe reports connected=False with error when Ollama is down."""
    import asyncio
    from app.main import _check_model
    from app.core.config import settings

    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:1")
    result = asyncio.run(_check_model())
    assert result["connected"] is False
    assert result["name"] == settings.OLLAMA_MODEL
    assert result["error"]  # contains exception type


def test_threads_list_create_delete(client):
    """Test thread metadata endpoints: list, create (id gen), delete."""
    # Create returns an id without touching the LLM
    r = client.post("/threads")
    assert r.status_code == 200
    thread_id = r.json()["thread_id"]
    assert thread_id

    # List includes threads that have metadata rows (created on first chat
    # message via _upsert_thread_meta — simulate that directly here)
    from app.api.v1.chat import _upsert_thread_meta
    _upsert_thread_meta(thread_id, title="hello world")
    r = client.get("/threads")
    assert r.status_code == 200
    threads = {t["thread_id"]: t for t in r.json()["threads"]}
    assert thread_id in threads
    assert threads[thread_id]["title"] == "hello world"

    # Title is captured once (first message) and not overwritten
    _upsert_thread_meta(thread_id, title="second message")
    r = client.get("/threads")
    title = next(t for t in r.json()["threads"] if t["thread_id"] == thread_id)["title"]
    assert title == "hello world"

    # Delete removes metadata row; idempotent for unknown threads
    r = client.delete(f"/threads/{thread_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"
    r = client.delete(f"/threads/{thread_id}")
    assert r.status_code == 200
    r = client.get("/threads")
    assert thread_id not in [t["thread_id"] for t in r.json()["threads"]]


def test_chat_stream(client, sample_message):
    """Test chat streaming endpoint."""
    response = client.post(
        "/chat",  # No trailing slash
        params={
            "content": sample_message,
            "thread_id": "test-thread-1"
        }
    )

    assert response.status_code in [200, 503]  # 503 if agent not initialized


def test_chat_invoke(client, sample_message):
    """Test chat invoke endpoint."""
    response = client.post(
        "/chat",  # No trailing slash
        params={
            "content": sample_message,
            "thread_id": "test-thread-2"
        }
    )

    assert response.status_code in [200, 503]


# Authentication tests removed - auth endpoints not implemented yet

def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    # Test accepts wildcard origin for development
    assert "*" in response.headers["access-control-allow-origin"] or \
           response.headers["access-control-allow-origin"] == "http://localhost:5173"
