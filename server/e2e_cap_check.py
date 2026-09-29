"""E2E: verify the return-path cap applies through the real deepagents stack.

Dispatches a researcher task that produces a long final report, then inspects
the orchestrator's resulting messages: the ToolMessage returned by the task
tool must be bounded (~return_cap), while the transcript file keeps full text.
"""
import os
import sys
import tempfile
import time
import sqlite3
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langgraph.checkpoint.sqlite import SqliteSaver
from app.graph.graph import build_agent
from app.core.config import settings

tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
conn = sqlite3.connect(tmpdb, check_same_thread=False)
agent = build_agent(checkpointer=SqliteSaver(conn))

tid = f"e2e-cap-{int(time.time())}"
cfg = {"configurable": {"thread_id": tid}, "recursion_limit": 80}

t0 = time.time()
out = agent.invoke(
    {"messages": [{"role": "user", "content": (
        "spawn:researcher Write a comprehensive report on the history of the "
        "Internet. It MUST be at least 6000 characters long. Do not use any "
        "tools — write from your own knowledge. End with a ## Sources section."
    )}]},
    config=cfg,
)
elapsed = time.time() - t0

print(f"\n=== elapsed {elapsed:.1f}s ===")
for i, m in enumerate(out["messages"]):
    kind = type(m).__name__
    c = m.content if isinstance(m.content, str) else str(m.content)
    marker = ""
    if kind == "ToolMessage":
        marker = "  <-- task-tool return (must be bounded)"
    print(f"[{i}] {kind}: {len(c)} chars{marker} | {c[:100]!r}")

# Transcript check: full final report should be on disk
paths = glob.glob(os.path.join(settings.SANDBOX_ROOT, tid, "transcripts", "*.md"))
for p in paths:
    body = open(p).read()
    print(f"\ntranscript {p}: {len(body)} chars, has-full-report-section: {'[full final report]' in body}")

tool_msgs = [m for m in out["messages"] if type(m).__name__ == "ToolMessage"]
if tool_msgs:
    # The task-tool return is the FIRST ToolMessage (immediately after the
    # dispatch); later ToolMessages are the orchestrator's own voluntary
    # file reads (just-in-time retrieval) and are intentionally unbounded.
    first = tool_msgs[0]
    size = len(first.content if isinstance(first.content, str) else str(first.content))
    print(f"\nVERDICT: task-tool return = {size} chars -> {'BOUNDED ✓' if size <= 4200 else 'NOT BOUNDED ✗'}")
else:
    print("\nVERDICT: no ToolMessage found — dispatch may not have happened")