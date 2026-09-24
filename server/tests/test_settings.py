"""
Settings API tests — runtime settings store + GET/PUT endpoints.
"""

import json
import pytest
from unittest.mock import patch

from app.core import runtime


@pytest.fixture(autouse=True)
def tmp_runtime_file(tmp_path, monkeypatch):
    """Point the runtime settings file at a temp path for every test."""
    f = tmp_path / "runtime_settings.json"
    monkeypatch.setattr(runtime, "_path", lambda: str(f))
    return f


@pytest.fixture
def no_rebuild(monkeypatch):
    """Stub agent rebuild (heavy); count calls instead."""
    calls = []
    monkeypatch.setattr("app.api.v1.settings.rebuild_agent", lambda: calls.append(1))
    return calls


def test_get_returns_defaults(client):
    r = client.get("/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["model"] == "qwen3.5:9b"
    assert data["num_ctx"] == 16384
    assert data["compaction_enabled"] is True
    assert data["compaction_mode"] == "state_doc"
    assert data["compaction_trigger_fraction"] == 0.85
    assert data["compaction_keep_messages"] == 20


def test_put_persists_and_rebuilds(client, tmp_runtime_file, no_rebuild):
    r = client.put("/settings", json={"num_ctx": 32768, "compaction_enabled": False})
    assert r.status_code == 200
    data = r.json()
    assert data["num_ctx"] == 32768
    assert data["compaction_enabled"] is False
    assert data["rebuilt"] is True
    assert len(no_rebuild) == 1  # exactly one rebuild per PUT

    # Persisted to disk
    on_disk = json.loads(tmp_runtime_file.read_text())
    assert on_disk["num_ctx"] == 32768

    # GET reflects the change
    assert client.get("/settings").json()["num_ctx"] == 32768


def test_put_rejects_bad_values(client, no_rebuild):
    for patch in (
        {"num_ctx": 100},                          # below minimum
        {"num_ctx": "big"},                        # not an int
        {"compaction_trigger_fraction": 1.5},      # out of range
        {"compaction_keep_messages": 0},           # below minimum
        {"model": ""},                             # empty
        {"compaction_enabled": "yes"},             # not a bool
        {"compaction_mode": "bogus"},              # unknown strategy
    ):
        r = client.put("/settings", json=patch)
        assert r.status_code == 422, f"{patch} should be rejected"
    assert no_rebuild == []  # nothing rebuilt on failed validation


def test_put_unknown_model_rejected_when_ollama_reachable(client, no_rebuild, monkeypatch):
    """Model existence is enforced when the Ollama server answers."""
    from app.core.config import settings as cfg

    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"models": [{"name": "qwen3.5:9b"}, {"name": "qwen2.5-coder:7b"}]}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): return FakeResp()

    monkeypatch.setattr(cfg, "OLLAMA_BASE_URL", "http://fake:11434")
    monkeypatch.setattr("app.api.v1.settings.httpx.AsyncClient", FakeClient)

    r = client.put("/settings", json={"model": "not-installed:1b"})
    assert r.status_code == 422
    assert "not available" in r.json()["detail"]

    r = client.put("/settings", json={"model": "qwen2.5-coder:7b"})
    assert r.status_code == 200
    assert r.json()["model"] == "qwen2.5-coder:7b"


def test_build_agent_wires_compaction_from_runtime(tmp_runtime_file, monkeypatch):
    """Compaction middleware is constructed with runtime-derived params."""
    import app.graph.graph as g

    runtime.update(
        {
            "compaction_enabled": True,
            "compaction_mode": "summary",
            "compaction_trigger_fraction": 0.6,
            "compaction_keep_messages": 20,
            "num_ctx": 32768,
        }
    )
    with patch("app.graph.graph.SummarizationMiddleware", wraps=g.SummarizationMiddleware) as spy:
        g.build_agent()
        assert spy.called, "SummarizationMiddleware not constructed"
        kwargs = spy.call_args.kwargs
        # % of num_ctx converted to absolute tokens (fraction triggers need
        # model profile metadata ChatOllama lacks)
        assert kwargs["trigger"] == ("tokens", int(0.6 * 32768))
        assert kwargs["keep"] == ("messages", 20)

    # Disabled -> middleware not constructed at all
    runtime.update({"compaction_enabled": False})
    with patch("app.graph.graph.SummarizationMiddleware", wraps=g.SummarizationMiddleware) as spy:
        g.build_agent()
        assert not spy.called


def test_models_endpoint_proxies_ollama(client, monkeypatch):
    from app.core.config import settings as cfg

    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"models": [{"name": "zeta:1b"}, {"name": "alpha:2b"}]}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): return FakeResp()

    monkeypatch.setattr("app.api.v1.settings.httpx.AsyncClient", FakeClient)
    r = client.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert data["connected"] is True
    assert data["models"] == ["alpha:2b", "zeta:1b"]  # sorted
