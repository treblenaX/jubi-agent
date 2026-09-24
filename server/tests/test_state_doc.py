"""
State-Document Separation tests — StateDocMiddleware lifecycle.

Covers: pin-only below trigger, compaction (doc write + eviction + safe
boundary), event bookkeeping across chained compactions, compile-failure
fallback, and graph wiring.
"""

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from deepagents.backends import FilesystemBackend
from app.graph.state_doc import EVENT_KEY, SESSION_KEY, StateDocMiddleware

TRIGGER = 100  # tokens — tiny so tests cross it easily
KEEP = 4


@pytest.fixture
def backend(tmp_path):
    return FilesystemBackend(root_dir=str(tmp_path))


@pytest.fixture
def mw(backend):
    return StateDocMiddleware(
        model=FakeListChatModel(responses=["# State\n- merged decision"]),
        backend=backend,
        trigger_tokens=TRIGGER,
        keep_messages=KEEP,
    )


def history(n_pairs, chars=200):
    """n_pairs of human/ai exchanges; pair 1 contains an AI tool_call + ToolMessage."""
    msgs = []
    for i in range(n_pairs):
        msgs.append(HumanMessage(content=f"q{i}: " + "x" * chars, id=f"h{i}"))
        if i == 1:
            msgs.append(AIMessage(
                content="",
                tool_calls=[{"name": "t", "args": {}, "id": "c1", "type": "tool_call"}],
                id="ai-tool",
            ))
            msgs.append(ToolMessage(content="tool output " + "z" * chars, tool_call_id="c1", id="t1"))
        msgs.append(AIMessage(content=f"a{i}: " + "y" * chars, id=f"a{i}"))
    return msgs


def run(mw, messages, state=None):
    captured = {}

    def handler(req):
        captured["request"] = req
        return "RESPONSE"

    req = ModelRequest(
        model=mw._model,
        messages=messages,
        system_message=SystemMessage(content="You are Jubi."),
        state=state if state is not None else {"messages": []},
        tools=[],
    )
    resp = mw.wrap_model_call(req, handler)
    return resp, captured["request"]


def test_below_trigger_is_noop(mw):
    resp, req = run(mw, history(2, chars=20))
    assert resp == "RESPONSE"  # plain response, no state update
    assert len(req.messages) == 6  # 2 pairs + tool pair
    assert req.system_message.text == "You are Jubi."  # nothing pinned


def test_pin_only_with_existing_doc(mw, backend):
    backend.write("/state_docs/s1.md", "# Decisions\n- JWT 15min expiry")
    state = {"messages": [], SESSION_KEY: "s1"}
    resp, req = run(mw, history(2, chars=20), state)
    assert resp == "RESPONSE"  # no compaction below trigger
    assert len(req.messages) == 6  # messages untouched
    assert "session_state_document" in req.system_message.text
    assert "JWT 15min" in req.system_message.text  # doc pinned in header


def test_compaction_writes_doc_and_evicts_middle(mw, backend):
    resp, req = run(mw, history(8))
    # ExtendedModelResponse with state update
    update = resp.command.update
    session = update[SESSION_KEY]
    assert session.startswith("session_")
    event = update[EVENT_KEY]
    assert event["cutoff_index"] == 14  # 18 msgs, keep 4, cut lands on h6 (Human)
    # Effective view: marker + tail starting at a HumanMessage
    assert len(req.messages) == 5
    marker = req.messages[0]
    assert isinstance(marker, HumanMessage)
    assert marker.additional_kwargs["lc_source"] == "state_doc"
    assert "Conversation compacted" in marker.text
    assert isinstance(req.messages[1], HumanMessage)  # tail starts clean
    # Doc written to backend and pinned into the system prompt
    saved = backend.download_files([f"/state_docs/{update[SESSION_KEY]}.md"])
    assert "merged decision" in saved[0].content.decode()
    assert "merged decision" in req.system_message.text


def test_chained_compaction_cutoff_math(mw, backend):
    old_marker = HumanMessage(content="old marker", additional_kwargs={"lc_source": "state_doc"})
    raw = history(10)  # 22 msgs; humans at even indices
    state = {"messages": [], SESSION_KEY: "s1", EVENT_KEY: {"cutoff_index": 10, "marker": old_marker}}
    resp, req = run(mw, raw, state)
    event = resp.command.update[EVENT_KEY]
    # effective = [old_marker] + raw[10:] (13 msgs) -> cut = 13-4 = 9 -> raw[10+9-1=18] (h9, Human)
    assert event["cutoff_index"] == 18
    assert req.messages[0] is event["marker"]
    assert req.messages[0] is not old_marker  # old marker replaced
    assert req.messages[1] is raw[18]
    # old marker filtered from the compile transcript (doc got merged output)
    saved = backend.download_files(["/state_docs/s1.md"])
    assert "merged decision" in saved[0].content.decode()


def test_compile_failure_falls_back(tmp_path):
    class Boom:
        def invoke(self, prompt):
            raise RuntimeError("boom")

    from app.graph.state_doc import StateDocMiddleware as M
    backend = FilesystemBackend(root_dir=str(tmp_path))
    m = M(model=Boom(), backend=backend, trigger_tokens=TRIGGER, keep_messages=KEEP)
    resp, req = run(m, history(8))
    update = resp.command.update  # compaction still happened
    saved = backend.download_files([f"/state_docs/{update[SESSION_KEY]}.md"])
    text = saved[0].content.decode()
    assert "## Evicted (compile failed)" in text
    assert "q0:" in text  # original user request preserved


def test_boundary_never_orphans_tool_message(backend):
    from app.graph.state_doc import StateDocMiddleware as M
    m = M(model=FakeListChatModel(responses=["doc"]), backend=backend,
          trigger_tokens=TRIGGER, keep_messages=5)
    _, req = run(m, history(8))
    tail = req.messages[1:]
    assert isinstance(tail[0], HumanMessage)  # cut extended past the tool pair
    for i, msg in enumerate(tail):  # every ToolMessage preceded by its AIMessage
        if isinstance(msg, ToolMessage):
            prev = tail[i - 1]
            assert isinstance(prev, AIMessage) and prev.tool_calls


def test_wiring_state_doc_mode(monkeypatch, tmp_path):
    import app.core.runtime as runtime
    import app.graph.graph as g

    monkeypatch.setattr(runtime, "_path", lambda: str(tmp_path / "rt.json"))
    calls = {}

    class Spy(StateDocMiddleware):
        def __init__(self, *a, **k):
            calls.update(k)
            super().__init__(*a, **k)

    monkeypatch.setattr(g, "StateDocMiddleware", Spy)
    g.build_agent()
    assert calls["trigger_tokens"] == int(0.85 * 16384)
    assert calls["keep_messages"] == 20


def test_wiring_summary_mode(monkeypatch, tmp_path):
    import app.core.runtime as runtime
    import app.graph.graph as g
    from deepagents.middleware.summarization import SummarizationMiddleware

    f = tmp_path / "rt.json"
    f.write_text('{"compaction_mode": "summary"}')
    monkeypatch.setattr(runtime, "_path", lambda: str(f))
    calls = {}

    class Spy(SummarizationMiddleware):
        def __init__(self, *a, **k):
            calls.update(k)
            super().__init__(*a, **k)

    monkeypatch.setattr(g, "SummarizationMiddleware", Spy)
    g.build_agent()
    assert calls["trigger"] == ("tokens", int(0.85 * 16384))
