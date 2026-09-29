"""
FastAPI to LangGraph bridge - Streaming chat endpoint.

This module:
- Streams agent responses via SSE (StreamingResponse)
- Handles user messages and returns structured responses
- Persists thread state via the agent's SQLite checkpointer
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any
import sqlite3
import time
import uuid
import json

from app.graph.graph import get_agent  # LangGraph agent instance (rebuilt on settings change)
from app.core.config import settings
from app.core import runtime

router = APIRouter()

# LangChain message type -> API role
_ROLE_MAP = {"human": "user", "ai": "assistant", "tool": "tool"}

# Thread metadata lives in the same SQLite file as the checkpointer, in a
# separate lightweight table (checkpoints is a serde blob — not queryable
# for sidebar listings). Rows are created lazily on the first chat message.
_META_DB = "harness.db"

# Append-only dispatch log: one JSON line per tool call observed in the
# stream. Ground truth for "did the orchestrator actually delegate": a
# `task` tool call naming a subagent is a dispatch; its absence means the
# orchestrator acted alone. Also captures per-call token usage.
_DISPATCH_LOG = Path(__file__).resolve().parents[3] / "logs" / "dispatch.jsonl"


class ThreadCreate(BaseModel):
    """Optional body for POST /threads (create a thread inside a project)."""
    project_id: Optional[str] = None


@contextmanager
def _meta_conn():
    conn = sqlite3.connect(_META_DB, timeout=10)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS message_stamps (
                thread_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (thread_id, message_id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                workspace_path TEXT
            )"""
        )
        # Migration: threads may belong to a project (nullable link)
        try:
            conn.execute("ALTER TABLE threads ADD COLUMN project_id TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists
        # Migration: projects may pin a workspace path (tool-action jail)
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN workspace_path TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists
        with conn:
            yield conn
    finally:
        conn.close()


def _upsert_thread_meta(thread_id: str, title: Optional[str] = None) -> None:
    """Create or touch a thread's metadata row.

    Title is captured from the first user message and never overwritten.
    """
    now = datetime.now(timezone.utc).isoformat()
    with _meta_conn() as conn:
        row = conn.execute(
            "SELECT title FROM threads WHERE thread_id = ?", (thread_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO threads (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (thread_id, title or "", now, now),
            )
        elif title and not row[0]:
            conn.execute(
                "UPDATE threads SET title = ?, updated_at = ? WHERE thread_id = ?",
                (title, now, thread_id),
            )
        else:
            conn.execute(
                "UPDATE threads SET updated_at = ? WHERE thread_id = ?",
                (now, thread_id),
            )


def _stamp_messages(thread_id: str, messages: list) -> None:
    """Record server time for message ids (first stamp wins).

    LangChain messages carry no timestamps, so we persist one per id as
    messages are produced — this is what makes history timestamps real.
    """
    ids = [m.get("id") for m in messages if isinstance(m, dict) and m.get("id")]
    if not ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    with _meta_conn() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO message_stamps (thread_id, message_id, created_at)
               VALUES (?, ?, ?)""",
            [(thread_id, mid, now) for mid in ids],
        )


def _get_message_stamps(thread_id: str) -> dict:
    """Return {message_id: created_at} for a thread."""
    with _meta_conn() as conn:
        rows = conn.execute(
            "SELECT message_id, created_at FROM message_stamps WHERE thread_id = ?",
            (thread_id,),
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def _serialize_message(m: Any, timestamp: Optional[str] = None,
                       include_thinking: bool = True) -> dict:
    """Convert a LangChain message (or dict) to a JSON-safe dict."""
    if isinstance(m, dict):
        return m
    m_type = getattr(m, "type", "unknown")
    content = getattr(m, "content", "")
    if not isinstance(content, str):
        # Content blocks (list of dicts) -> join text parts
        try:
            content = "".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            ) or str(content)
        except Exception:
            content = str(content)
    out = {
        "type": m_type,
        "role": _ROLE_MAP.get(m_type, m_type),
        "content": content,
        "id": getattr(m, "id", None) or str(uuid.uuid4()),
    }
    if timestamp:
        out["timestamp"] = timestamp
    ak = getattr(m, "additional_kwargs", None)
    thinking = ak.get("reasoning_content") if isinstance(ak, dict) else None
    if thinking and include_thinking:
        out["thinking"] = thinking
    tool_calls = getattr(m, "tool_calls", None)
    if tool_calls:
        out["tool_calls"] = [
            {"name": tc.get("name", ""), "args": tc.get("args", {})}
            for tc in tool_calls
        ]
    um = getattr(m, "usage_metadata", None)
    if um:
        try:
            out["usage"] = dict(um)
        except (TypeError, ValueError):
            pass
    return out


def _context_usage(config: dict) -> Optional[dict]:
    """Orchestrator context usage: tokens used vs OLLAMA_NUM_CTX.

    Prefers the last AI message's real usage_metadata.input_tokens (prompt size
    of the final LLM call ≈ full context); falls back to a chars/4 estimate.
    """
    try:
        agent = get_agent()
        state = agent.get_state(config=config)
        msgs = (state.values or {}).get("messages", []) if state else []
        if not msgs:
            return None
        last_ai = next(
            (m for m in reversed(msgs) if getattr(m, "type", "") == "ai"), None
        )
        um = getattr(last_ai, "usage_metadata", None) if last_ai else None
        used = (um or {}).get("input_tokens")
        if not used:
            used = sum(len(str(getattr(m, "content", ""))) for m in msgs) // 4
        return {"used": used, "limit": runtime.get()["num_ctx"]}
    except Exception:
        return None


def _log_dispatch(thread_id: str, payload: dict) -> None:
    """Append every tool call in a stream update to logs/dispatch.jsonl.

    Best-effort: logging must never break chat. Args are truncated — the
    log answers "was tool X called on node Y", not full replay.
    """
    try:
        rows = []
        for node, p in payload.items():
            if not isinstance(p, dict):
                continue
            for m in p.get("messages", []):
                if not isinstance(m, dict):
                    continue
                usage = m.get("usage") or {}
                for tc in m.get("tool_calls") or []:
                    rows.append({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "thread_id": thread_id,
                        "node": node,
                        "tool": tc.get("name"),
                        "args": json.dumps(tc.get("args", {}), default=str)[:300],
                        "input_tokens": usage.get("input_tokens"),
                    })
        if not rows:
            return
        _DISPATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _DISPATCH_LOG.open("a") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def _serialize_update(update: dict) -> dict:
    """Convert a LangGraph stream update ({node: state_delta}) to JSON-safe."""
    out = {}
    for node, payload in update.items():
        if not payload:
            continue
        node_out = {}
        for key, value in payload.items():
            if key == "messages" and isinstance(value, list):
                # Stream updates strip thinking: live thoughts arrive as
                # token-level deltas via the "messages" stream mode instead.
                node_out["messages"] = [
                    _serialize_message(m, include_thinking=False) for m in value
                ]
            else:
                try:
                    json.dumps(value)
                    node_out[key] = value
                except (TypeError, ValueError):
                    node_out[key] = str(value)
        out[node] = node_out
    return out


@router.post("/chat")
async def add_message(
    request: Request,
    content: str = None,
    thread_id: Optional[str] = None,
    timeout: int = 60
):
    """POST endpoint for streaming chat (primary). Accepts JSON body or query params."""
    # Try to get content/thread_id from JSON body if not in query params
    if content is None or thread_id is None:
        try:
            body = await request.json()
            if content is None:
                content = body.get("content")
            if thread_id is None:
                thread_id = body.get("thread_id")
        except Exception:
            pass
    return await _stream_chat(content, thread_id, timeout)


@router.get("/chat/stream")
async def stream_chat_get(
    content: str,
    thread_id: Optional[str] = None,
    timeout: int = 60
):
    """GET alias for SSE streaming (EventSource compat)."""
    return await _stream_chat(content, thread_id, timeout)


async def _stream_chat(
    content: str,
    thread_id: Optional[str] = None,
    timeout: int = 60
):
    """
    Add a user message and stream the agent response.

    Args:
        content: User message content (required)
        thread_id: Optional thread ID (creates new if not provided)
        timeout: Unused (kept for API compat); recursion_limit guards runtime

    Returns:
        StreamingResponse with SSE events
    """
    if not content:
        raise HTTPException(status_code=422, detail="content is required")

    if not thread_id:
        thread_id = f"thread-{int(time.time())}"

    # Sidebar metadata: create/touch row, title = first user message.
    # Best-effort — chat must not break if metadata fails.
    try:
        _upsert_thread_meta(thread_id, title=content[:80])
    except Exception:
        pass

    # Pre-assign the user message id so it can be stamped with the real send
    # time (LangChain would otherwise generate one mid-stream).
    user_msg = {"role": "user", "content": content, "id": f"user-{uuid.uuid4()}"}
    try:
        _stamp_messages(thread_id, [user_msg])
    except Exception:
        pass

    config = {
        "configurable": {
            "thread_id": thread_id,
            "thread_ts": time.time(),
        },
        "recursion_limit": 200,
    }

    # Project context: if the thread belongs to a project, pin its title +
    # description into every agent's system prompt (ProjectContextMiddleware).
    # A project workspace_path (when set) is enforced by
    # WorkspaceSandboxMiddleware: filesystem/shell tool calls are forced inside it.
    try:
        from app.api.v1.projects import get_project_for_thread

        project = get_project_for_thread(thread_id)
        if project and (project.get("description") or project.get("title")):
            ctx = (
                f"## Active project: {project.get('title', 'Untitled')}\n"
                f"{project.get('description', '')}".strip()
            )
            workspace = project.get("workspace_path")
            if workspace:
                ctx += (
                    "\n\n## Project workspace\n"
                    f"All file reads/writes/edits and shell commands MUST stay inside: {workspace}\n"
                    "Tool paths are resolved relative to this workspace. Never touch files outside it."
                )
                config["configurable"]["workspace_path"] = workspace
            config["configurable"]["project_context"] = ctx
    except Exception:
        pass  # context injection must never break chat

    # Stream response from LangGraph.
    # Sync generator on purpose: Starlette iterates it in a threadpool, which
    # keeps the event loop free AND is compatible with the sync SqliteSaver.
    def stream_generator():
        try:
            agent = get_agent()
            for mode, data in agent.stream(
                {"messages": [user_msg]},
                config=config,
                stream_mode=["updates", "messages"],
            ):
                if mode == "messages":
                    # Token-level reasoning deltas -> live thoughts above the bubble
                    chunk = data[0] if isinstance(data, tuple) else data
                    rc = (getattr(chunk, "additional_kwargs", None) or {}).get("reasoning_content")
                    if rc:
                        yield f"data: {json.dumps({'thinking': rc})}\n\n"
                    continue
                payload = _serialize_update(data)
                _log_dispatch(thread_id, payload)
                # Stamp assistant messages as they are emitted (best-effort)
                try:
                    _stamp_messages(thread_id, [
                        m for p in payload.values() if isinstance(p, dict)
                        for m in p.get("messages", [])
                    ])
                except Exception:
                    pass
                yield f"data: {json.dumps(payload)}\n\n"
            # Sweep: stamp anything updates missed (e.g. the input user message)
            try:
                state = get_agent().get_state(config=config)
                if state and state.values:
                    _stamp_messages(thread_id, [
                        _serialize_message(m) for m in state.values.get("messages", [])
                    ])
            except Exception:
                pass
            ctx = _context_usage(config)
            if ctx:
                yield f"data: {json.dumps({'context': ctx})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/chat")
async def get_messages(thread_id: Optional[str] = None):
    """
    Get all messages for a thread.

    Args:
        thread_id: Thread ID (creates a new empty thread ID if not provided)

    Returns:
        List of serialized messages in the thread
    """
    config = {
        "configurable": {"thread_id": thread_id or f"thread-{int(time.time())}"},
        "recursion_limit": 200
    }

    try:
        state = get_agent().get_state(config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if state is None or not state.values:
        return {
            "messages": [],
            "status": "no_messages"
        }

    stamps = _get_message_stamps(config["configurable"]["thread_id"])
    messages = [
        _serialize_message(m, stamps.get(getattr(m, "id", None)))
        for m in state.values.get("messages", [])
    ]

    return {
        "messages": messages,
        "status": "success",
        "context": _context_usage(config),
    }


@router.post("/threads")
async def create_thread(body: Optional[ThreadCreate] = None):
    """
    Create a new conversation thread, optionally inside a project.

    Returns:
        Thread ID and status
    """
    thread_id = f"thread-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    project_id = body.project_id if body else None
    if project_id:
        from app.api.v1.projects import get_project

        if get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            with _meta_conn() as conn:
                # The threads row is otherwise created lazily on first message
                # (_upsert_thread_meta); insert eagerly so the project link
                # lands before any chat happens.
                conn.execute(
                    "INSERT OR IGNORE INTO threads (thread_id, title, created_at, updated_at, project_id)"
                    " VALUES (?, '', ?, ?, ?)",
                    (thread_id, datetime.now(timezone.utc).isoformat(),
                     datetime.now(timezone.utc).isoformat(), project_id),
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {
        "thread_id": thread_id,
        "project_id": project_id,
        "status": "created"
    }


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """
    Delete a conversation thread (checkpoints + writes + metadata row).

    Idempotent: deleting an unknown thread still returns 200.
    """
    try:
        checkpointer = getattr(get_agent(), "checkpointer", None)
        if checkpointer is not None:
            checkpointer.delete_thread(thread_id)
        with _meta_conn() as conn:
            conn.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
            conn.execute("DELETE FROM message_stamps WHERE thread_id = ?", (thread_id,))
        return {"thread_id": thread_id, "status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threads")
async def list_threads(project_id: Optional[str] = None):
    """
    List conversation threads (most recently updated first).

    Args:
        project_id: Optional filter to only threads belonging to a project.
    """
    try:
        with _meta_conn() as conn:
            if project_id:
                rows = conn.execute(
                    """SELECT thread_id, title, created_at, updated_at, project_id
                       FROM threads WHERE project_id = ? ORDER BY updated_at DESC""",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT thread_id, title, created_at, updated_at, project_id
                       FROM threads ORDER BY updated_at DESC"""
                ).fetchall()
        return {
            "threads": [
                {
                    "thread_id": r[0],
                    "title": r[1],
                    "created_at": r[2],
                    "updated_at": r[3],
                    "project_id": r[4],
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
