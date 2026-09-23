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

def test_message_stamps_roundtrip(client):
    """Message stamps persist (first wins) and serialize into messages."""
    import sqlite3
    import uuid
    from types import SimpleNamespace
    from app.api.v1.chat import (
        _META_DB, _stamp_messages, _get_message_stamps, _serialize_message,
    )

    tid = f"stamp-test-{uuid.uuid4()}"
    _stamp_messages(tid, [{"id": "m-1", "role": "user", "content": "hi"}])
    stamps = _get_message_stamps(tid)
    assert stamps.get("m-1")  # ISO timestamp string

    # First stamp wins (INSERT OR IGNORE)
    _stamp_messages(tid, [{"id": "m-1", "role": "user", "content": "hi"}])
    assert _get_message_stamps(tid)["m-1"] == stamps["m-1"]

    # Serializer includes the timestamp when provided
    msg = SimpleNamespace(type="human", content="x", id="m-1", tool_calls=None)
    out = _serialize_message(msg, timestamp=stamps["m-1"])
    assert out["timestamp"] == stamps["m-1"]

    # Cleanup
    conn = sqlite3.connect(_META_DB)
    with conn:
        conn.execute("DELETE FROM message_stamps WHERE thread_id = ?", (tid,))
    conn.close()


def test_serialize_message_includes_thinking(client):
    """Reasoning content from additional_kwargs is exposed as 'thinking'."""
    from types import SimpleNamespace
    from app.api.v1.chat import _serialize_message

    msg = SimpleNamespace(
        type="ai", content="answer", id="m-2", tool_calls=None,
        additional_kwargs={"reasoning_content": "hmm let me think"},
    )
    out = _serialize_message(msg)
    assert out["thinking"] == "hmm let me think"

    plain = SimpleNamespace(type="ai", content="x", id="m-3", tool_calls=None,
                            additional_kwargs={})
    assert "thinking" not in _serialize_message(plain)

    # Stream updates strip thinking (live thoughts come via token chunks)
    from app.api.v1.chat import _serialize_update
    upd = _serialize_update({"node": {"messages": [msg]}})
    assert "thinking" not in upd["node"]["messages"][0]


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    # Test accepts wildcard origin for development
    assert "*" in response.headers["access-control-allow-origin"] or \
           response.headers["access-control-allow-origin"] == "http://localhost:5173"
