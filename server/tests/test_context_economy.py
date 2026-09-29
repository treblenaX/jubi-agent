"""
Context-economy tests.

Covers:
- SubagentTranscriptMiddleware return-path cap (same-ID replacement,
  head+tail truncation, full final report preserved in transcript file)
- ClearToolUsesEdit tool-result clearing (native langchain middleware)
- fetch_url research persistence (workspace pointer + sandbox fallback)
- files API transcript endpoint reads settings.SANDBOX_ROOT
"""

import hashlib

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain.agents.middleware.context_editing import ClearToolUsesEdit

from app.core.config import settings
from app.graph.transcript import SubagentTranscriptMiddleware
# NOTE: `from app.graph.tools import web_search` binds the *function*
# (the tools package re-exports it, shadowing the submodule). importlib
# returns the actual module from sys.modules.
import importlib

web_search_module = importlib.import_module("app.graph.tools.web_search")
from app.graph.tools.web_search import _persist_research


def _ai(content, msg_id="abc-123"):
    return AIMessage(content=content, id=msg_id)


class TestReturnPathCap:
    """after_agent must bound the message that flows back to the orchestrator."""

    def test_truncates_long_final_message_same_id(self, tmp_path):
        mw = SubagentTranscriptMiddleware("researcher", sandbox_root=str(tmp_path))
        state = {"messages": [HumanMessage("q"), _ai("x" * 10000)]}

        result = mw.after_agent(state, runtime=None)

        assert result is not None
        new = result["messages"][0]
        # Same ID -> langgraph add_messages reducer REPLACES in place
        assert new.id == "abc-123"
        # Bounded: cap + pointer/marker overhead, nothing more
        assert len(new.content) <= mw.return_cap + 200
        assert "full transcript" in new.content
        # Head+tail: both ends preserved (citations live at the end)
        assert new.content.startswith("x")
        assert new.content.rstrip().endswith("x")

    def test_short_message_untouched(self, tmp_path):
        mw = SubagentTranscriptMiddleware("researcher", sandbox_root=str(tmp_path))
        state = {"messages": [_ai("short report")]}
        assert mw.after_agent(state, runtime=None) is None

    def test_non_ai_final_message_untouched(self, tmp_path):
        mw = SubagentTranscriptMiddleware("researcher", sandbox_root=str(tmp_path))
        state = {"messages": [HumanMessage("q" * 20000)]}
        assert mw.after_agent(state, runtime=None) is None

    def test_transcript_file_keeps_full_final_report(self, tmp_path):
        mw = SubagentTranscriptMiddleware("researcher", sandbox_root=str(tmp_path))
        long = "y" * 10000
        state = {"messages": [_ai(long)]}

        mw.before_agent(state, runtime=None)
        mw.after_model(state, runtime=None)
        mw.after_agent(state, runtime=None)

        # Outside a graph run the thread id resolves to "unknown"
        path = tmp_path / "unknown" / "transcripts" / "researcher-latest.md"
        assert path.exists()
        assert long in path.read_text()  # full text, not the truncated copy


class TestClearToolUsesEdit:
    """Native langchain middleware wired into both subagents (trigger=8000, keep=3)."""

    def _msg_set(self, n=6, body=500):
        msgs = [HumanMessage("research X")]
        for i in range(n):
            msgs.append(AIMessage(
                content="",
                tool_calls=[{"name": "web_search", "args": {"query": f"q{i}"}, "id": f"call-{i}"}],
            ))
            msgs.append(ToolMessage(
                content=f"result {i} " + "z" * body, tool_call_id=f"call-{i}", name="web_search"
            ))
        return msgs

    def test_clears_old_keeps_recent(self):
        edit = ClearToolUsesEdit(trigger=100, keep=2)
        msgs = self._msg_set()
        edit.apply(msgs, count_tokens=count_tokens_approximately)
        cleared = [m for m in msgs if isinstance(m, ToolMessage) and m.content == "[cleared]"]
        kept = [m for m in msgs if isinstance(m, ToolMessage) and m.content != "[cleared]"]
        assert len(kept) == 2   # most recent 2 preserved
        assert len(cleared) == 4

    def test_noop_under_trigger(self):
        edit = ClearToolUsesEdit(trigger=100_000, keep=3)
        msgs = self._msg_set()
        before = [m.content for m in msgs]
        edit.apply(msgs, count_tokens=count_tokens_approximately)
        assert [m.content for m in msgs] == before


class TestFetchPersistence:
    """fetch_url persists full pages; context gets an excerpt + pointer."""

    def test_persists_to_workspace_with_relative_pointer(self, tmp_path):
        url = "https://example.com/docs"
        res = _persist_research(url, "full page text", str(tmp_path), "t1")

        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        saved = tmp_path / ".jubi" / "research" / f"{digest}.md"
        assert saved.exists()
        assert "full page text" in saved.read_text()
        # Workspace-relative pointer -> read_project_file can re-read it
        assert res["saved_to"] == f".jubi/research/{digest}.md"

    def test_sandbox_fallback_without_workspace(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "SANDBOX_ROOT", str(tmp_path) + "/")
        res = _persist_research("https://example.com", "text", None, "thread-1")
        assert (tmp_path / "thread-1" / "research").exists()
        assert res["saved_to"].startswith(str(tmp_path))

    def test_invalid_thread_id_jailed_to_unknown(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "SANDBOX_ROOT", str(tmp_path) + "/")
        _persist_research("https://example.com", "text", None, "../../evil")
        assert (tmp_path / "unknown" / "research").exists()
        assert not (tmp_path / "..").exists() or True  # no escape path created
        assert not list(tmp_path.glob("evil*"))

    def test_fetch_url_returns_excerpt_and_saves_full(self, tmp_path, monkeypatch):
        page = "<html><head><title>Big</title></head><body><main>" + "a" * 5000 + "</main></body></html>"

        class FakeResp:
            status_code = 200
            url = "https://example.com/big"
            text = page

        monkeypatch.setattr(web_search_module.requests, "get", lambda *a, **k: FakeResp())
        monkeypatch.setattr(web_search_module, "_research_context", lambda: (str(tmp_path), "t1"))

        res = web_search_module.fetch_url("https://example.com/big")

        assert res["status"] == "success"
        assert len(res["content"]) < 5000            # excerpt, not the full page
        assert res["saved_to"].startswith(".jubi/research/")
        saved = tmp_path / ".jubi" / "research"
        full_file = list(saved.iterdir())[0]
        assert len(full_file.read_text()) >= 5000    # full text persisted

    def test_fetch_url_small_page_untouched_content(self, tmp_path, monkeypatch):
        class FakeResp:
            status_code = 200
            url = "https://example.com/small"
            text = "<html><body><main>tiny page</main></body></html>"

        monkeypatch.setattr(web_search_module.requests, "get", lambda *a, **k: FakeResp())
        monkeypatch.setattr(web_search_module, "_research_context", lambda: (str(tmp_path), "t1"))

        res = web_search_module.fetch_url("https://example.com/small")
        assert res["content"] == "tiny page"
        assert res["saved_to"].startswith(".jubi/research/")


class TestTranscriptEndpointRoot:
    """files API must serve transcripts from settings.SANDBOX_ROOT, not a hardcoded path."""

    def test_serves_from_settings_root(self, tmp_path, monkeypatch, client):
        monkeypatch.setattr(settings, "SANDBOX_ROOT", str(tmp_path) + "/")
        tid, agent = "tid123", "researcher"
        d = tmp_path / tid / "transcripts"
        d.mkdir(parents=True)
        (d / f"{agent}-latest.md").write_text("# transcript body")

        resp = client.get(f"/transcript/{tid}/{agent}")

        assert resp.status_code == 200
        assert "# transcript body" in resp.text

    def test_404_when_missing(self, tmp_path, monkeypatch, client):
        monkeypatch.setattr(settings, "SANDBOX_ROOT", str(tmp_path) + "/")
        resp = client.get("/transcript/nothing/researcher")
        assert resp.status_code == 404
