"""
Subagent transcript capture middleware.

Each subagent writes an append-only markdown transcript of its run to the
thread sandbox at /tmp/jubi-sandbox/<thread_id>/transcripts/<name>-latest.md.
The file grows as the run progresses (after_model appends unseen messages),
so the client can poll it via the files API while a dispatch is in flight
and render a near-live "subagent chat" panel.

Why not live streaming: deepagents' task tool runs subagents via
subagent.invoke() — a non-streaming black box; get_stream_writer() inside a
subagent middleware is a silent no-op on the parent custom stream (verified
against deepagents 0.7.15). Transcript capture + polling is the Jubi-owned
alternative with zero deepagents surgery.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.config import get_config

from app.core.config import settings

logger = logging.getLogger(__name__)

# Content cap per transcript entry — these files are for humans scanning progress
_MAX_CONTENT = 1500


def _shorten(text: str, limit: int = _MAX_CONTENT) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f" …(+{len(text) - limit} chars)"


class SubagentTranscriptMiddleware(AgentMiddleware):
    """Append the subagent's messages (thinking, replies, tool traffic) to a
    per-thread transcript file the client can poll while the dispatch runs.

    The middleware instance is shared across threads (built once per subagent
    in build_agent), so the seen-message count is keyed by thread_id.
    """

    def __init__(
        self,
        name: str,
        sandbox_root: str | None = None,
        return_cap: int = 4000,
    ) -> None:
        self.agent_name = name
        # Sandbox root defaults to settings.SANDBOX_ROOT so the jail root is
        # configured in one place instead of hardcoded per module.
        self.sandbox_root = sandbox_root or settings.SANDBOX_ROOT
        # Max chars of the final AI message returned to the orchestrator.
        # Anthropic's subagent-return guidance is ~1-2k tokens; 4000 chars
        # ~ 1k tokens — tight enough for a 16k orchestrator window.
        self.return_cap = return_cap
        self._seen: dict[str, int] = {}

    # -- paths ---------------------------------------------------------------
    def _path(self, thread_id: str) -> str:
        tid = thread_id if re.fullmatch(r"[A-Za-z0-9_-]+", str(thread_id)) else "unknown"
        d = os.path.join(self.sandbox_root, tid, "transcripts")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{self.agent_name}-latest.md")

    def _thread_id(self) -> str:
        try:
            cfg = get_config()
            return str((cfg.get("configurable") or {}).get("thread_id") or "unknown")
        except Exception:
            return "unknown"

    def _append(self, text: str) -> None:
        try:
            with open(self._path(self._thread_id()), "a", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            logger.warning("transcript append failed (%s)", self.agent_name, exc_info=True)

    # -- hooks ---------------------------------------------------------------
    def before_agent(self, state: dict, runtime: Any) -> None:
        tid = self._thread_id()
        self._seen[tid] = 0
        self._append(f"\n\n---\n## dispatch @ {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    def after_model(self, state: dict, runtime: Any) -> None:
        tid = self._thread_id()
        msgs = state.get("messages", []) or []
        seen = self._seen.get(tid, 0)
        if len(msgs) < seen:
            # History was evicted/rewritten (compaction) — everything up to the
            # new head was already logged; don't re-append it.
            seen = len(msgs)
        for m in msgs[seen:]:
            self._append(self._format(m))
        self._seen[tid] = len(msgs)

    def after_agent(self, state: dict, runtime: Any) -> dict | None:
        msgs = state.get("messages") or []
        last = msgs[-1] if msgs else None
        if isinstance(last, AIMessage):
            text = last.text
            if isinstance(text, str) and len(text) > _MAX_CONTENT:
                # The progress view caps entries at _MAX_CONTENT; persist the
                # full final report so the return-path pointer is truthful.
                self._append(f"\n### [full final report]\n{text}\n")
        self._append("")
        return self._cap_return_message(state)

    # -- return-path cap -----------------------------------------------------
    def _cap_return_message(self, state: dict) -> dict | None:
        """Bound what flows back to the orchestrator.

        deepagents' task tool returns the subagent's last non-empty AIMessage
        verbatim as a ToolMessage (it walks back over result["messages"]).
        Returning a same-ID truncated copy makes langgraph's add_messages
        reducer REPLACE the message in place, so the orchestrator receives a
        bounded report while the transcript file keeps the full text.
        """
        msgs = state.get("messages") or []
        if not msgs:
            return None
        last = msgs[-1]
        if not isinstance(last, AIMessage):
            return None
        text = last.text
        if not isinstance(text, str) or len(text) <= self.return_cap:
            return None
        return {"messages": [last.model_copy(update={"content": self._truncate(text)})]}

    def _truncate(self, text: str) -> str:
        """Head+tail truncation — citations usually live at the end."""
        head = int(self.return_cap * 0.6)
        tail = self.return_cap - head
        omitted = len(text) - self.return_cap
        pointer = f"full transcript: {self._path(self._thread_id())}"
        return (
            text[:head]
            + f"\n\n[… {omitted} chars omitted — {pointer}]\n\n"
            + text[-tail:]
        )

    # -- formatting ----------------------------------------------------------
    def _format(self, m: Any) -> str:
        ts = time.strftime("%H:%M:%S")
        if isinstance(m, AIMessage):
            parts = [f"### [{ts}] assistant"]
            thinking = (m.additional_kwargs or {}).get("reasoning_content")
            if thinking:
                parts.append(f"*thinking:* {_shorten(str(thinking))}")
            content = m.content if isinstance(m.content, str) else str(m.content)
            if content.strip():
                parts.append(_shorten(content))
            for tc in getattr(m, "tool_calls", None) or []:
                args = tc.get("args", {})
                parts.append(f"→ tool `{tc.get('name', '?')}` {_shorten(str(args), 300)}")
            return "\n".join(parts) + "\n"
        if isinstance(m, ToolMessage):
            name = getattr(m, "name", None) or "tool"
            return f"### [{ts}] tool `{name}`\n{_shorten(str(m.content))}\n"
        mtype = getattr(m, "type", None) or type(m).__name__
        content = getattr(m, "content", "")
        content = content if isinstance(content, str) else str(content)
        return f"### [{ts}] {mtype}\n{_shorten(content)}\n"
