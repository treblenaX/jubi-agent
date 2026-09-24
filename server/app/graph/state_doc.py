"""
State-Document Separation middleware (.md lifecycle protocol).

When token pressure crosses the trigger, durable state (architecture
decisions, requirements, unresolved bugs, next steps) is compiled into a
per-thread markdown state document, the middle of the chat history is
evicted, and the document is pinned into the system prompt on every model
call. The agent keeps exact architectural memory while the token-heavy
conversation history is wiped.

Mechanics (mirrors deepagents SummarizationMiddleware patterns):
- Raw history is never mutated; a private `_state_doc_event` tracks the
  cutoff so the effective view is [marker] + raw[cutoff:] each call.
- The state document lives on the agent's FilesystemBackend at
  /state_docs/{session}.md, so the agent can read/edit it with its file tools.
- Compaction = compile(old doc + evicted segment) -> rewritten doc, then
  evict. A failed compile falls back to old doc + first evicted user
  request; compaction itself never breaks the chat.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Annotated, Callable, NotRequired

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ExtendedModelResponse,
    ModelRequest,
    ModelResponse,
    PrivateStateAttr,
    TracePolicy,
    omit_payload,
)
from langchain_core.messages import AnyMessage, BaseMessage, HumanMessage, get_buffer_string
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.types import Command

from deepagents.middleware._utils import append_to_system_message

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from deepagents.backends.protocol import BackendProtocol
    from langchain.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

SESSION_KEY = "_state_doc_session"
EVENT_KEY = "_state_doc_event"


class StateDocState(AgentState):
    """Private state for StateDocMiddleware."""

    _state_doc_session: Annotated[NotRequired[str | None], PrivateStateAttr]
    """Id naming this thread's state document file."""
    _state_doc_event: Annotated[NotRequired[dict | None], PrivateStateAttr]
    """{"cutoff_index": int, "marker": HumanMessage} — eviction bookkeeping."""


COMPILE_PROMPT = """You are the state compiler for a long-running agent session. Merge the current state document with the evicted conversation segment into an UPDATED state document.

Rules:
- Preserve every still-relevant architecture decision, requirement, unresolved bug, and next step WITH its specifics. Do not paraphrase away details.
- Drop resolved items, transient chatter, tool output, and fixed errors.
- Use markdown sections: ## Architecture & Decisions, ## Requirements, ## Unresolved Bugs, ## Next Steps.
- Output ONLY the markdown document.

<current_state_document>
{doc}
</current_state_document>

<evicted_messages>
{transcript}
</evicted_messages>"""

MARKER_TEXT = (
    "[Conversation compacted] Earlier messages were removed to stay within the "
    "context window. Their durable state (architecture decisions, requirements, "
    "unresolved bugs, next steps) was merged into the session state document, "
    "which is injected in your system prompt and readable at {path}."
)

PIN_BLOCK = """<session_state_document path="{path}">
{doc}
</session_state_document>
The session state document above is the durable record of this conversation. Trust it for prior decisions and context. You can read or update it at "{path}" with your file tools when you learn something durable."""


def _is_state_doc_marker(msg: AnyMessage) -> bool:
    return isinstance(msg, HumanMessage) and msg.additional_kwargs.get("lc_source") == "state_doc"


class StateDocMiddleware(AgentMiddleware):
    """Compiles durable state into a pinned markdown document at pressure time.

    Args:
        model: Model used for the compile (merge) call.
        backend: Backend where the state document is stored (agent-readable).
        trigger_tokens: Effective-view token count that triggers compaction.
        keep_messages: Recent messages always kept verbatim after eviction.
    """

    trace_policy = TracePolicy(process_inputs=omit_payload)
    state_schema = StateDocState

    def __init__(
        self,
        model: BaseChatModel,
        *,
        backend: BackendProtocol,
        trigger_tokens: int,
        keep_messages: int,
    ) -> None:
        self._model = model
        self._backend = backend
        self._trigger_tokens = max(1, int(trigger_tokens))
        self._keep = max(1, int(keep_messages))

    # -- document I/O ---------------------------------------------------------

    def _doc_path(self, session: str) -> str:
        return f"/state_docs/{session}.md"

    def _read_doc(self, path: str) -> str:
        try:
            responses = self._backend.download_files([path])
            if responses and responses[0].error is None and responses[0].content is not None:
                return responses[0].content.decode("utf-8")
        except Exception as e:  # noqa: BLE001
            logger.warning("State doc read failed (%s): %s: %s", path, type(e).__name__, e)
        return ""

    def _write_doc(self, path: str, text: str) -> bool:
        try:
            result = self._backend.write(path, text)
            if result is None or result.error:
                logger.warning("State doc write failed (%s): %s", path, result.error if result else "no result")
                return False
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning("State doc write failed (%s): %s: %s", path, type(e).__name__, e)
            return False

    def _compile(self, old_doc: str, evicted: list[AnyMessage]) -> str:
        """Merge old doc + evicted segment into the updated state document."""
        transcript = get_buffer_string(evicted, format="xml")
        try:
            prompt = COMPILE_PROMPT.format(doc=old_doc or "(empty — create it)", transcript=transcript)
            text = (self._model.invoke(prompt).text or "").strip()
            if text:
                return text
            logger.warning("State doc compile returned empty output; using fallback")
        except Exception as e:  # noqa: BLE001
            logger.warning("State doc compile failed: %s: %s", type(e).__name__, e)
        # Fallback: keep the old doc and at least the original user request.
        first = next((m for m in evicted if isinstance(m, HumanMessage)), None)
        if first is not None:
            return (old_doc + f"\n\n## Evicted (compile failed)\n{first.text[:2000]}").strip()
        return old_doc

    # -- eviction planning ----------------------------------------------------

    def _cutoff(self, effective: list[AnyMessage]) -> int | None:
        """Index where eviction starts, or None if unsafe/nothing to evict.

        The cut is extended right to the next HumanMessage so the kept tail
        never starts with an orphan ToolMessage.
        """
        cut = len(effective) - self._keep
        if cut <= 0:
            return None
        while cut < len(effective) and not isinstance(effective[cut], HumanMessage):
            cut += 1
        if cut >= len(effective):
            return None
        return cut

    # -- core -----------------------------------------------------------------

    def _prepare(self, request: ModelRequest) -> tuple[ModelRequest, dict | None]:
        """Build the effective request; return it plus a state update (if compacted)."""
        state = request.state
        session = state.get(SESSION_KEY)
        event = state.get(EVENT_KEY)

        if isinstance(event, dict) and isinstance(event.get("marker"), BaseMessage):
            marker, cutoff = event["marker"], event["cutoff_index"]
            if not isinstance(cutoff, int) or cutoff > len(request.messages):
                cutoff = len(request.messages)
            effective = [marker, *request.messages[cutoff:]]
        else:
            effective = list(request.messages)

        doc = self._read_doc(self._doc_path(session)) if session else ""

        # Compaction when the effective view crosses the trigger. Pressure
        # counts the full prompt (system message + tool schemas + messages),
        # matching the context bar's usage numbers.
        new_event = None
        counted = ([request.system_message] if request.system_message is not None else []) + effective
        if count_tokens_approximately(counted, tools=request.tools or None) >= self._trigger_tokens and len(effective) > self._keep + 2:
            cut = self._cutoff(effective)
            if cut is not None:
                if not session:
                    session = f"session_{uuid.uuid4().hex}"
                path = self._doc_path(session)
                evicted = [m for m in effective[:cut] if not _is_state_doc_marker(m)]
                doc = self._compile(doc, evicted)
                self._write_doc(path, doc)
                marker = HumanMessage(
                    content=MARKER_TEXT.format(path=path),
                    additional_kwargs={"lc_source": "state_doc"},
                )
                prev_cutoff = event["cutoff_index"] if isinstance(event, dict) and isinstance(event.get("cutoff_index"), int) else 0
                state_cutoff = prev_cutoff + cut - 1 if event else cut
                new_event = {"cutoff_index": state_cutoff, "marker": marker}
                effective = [marker, *effective[cut:]]

        # Pin the state document into the prompt header (every call).
        system_message = request.system_message
        if doc and session:
            system_message = append_to_system_message(
                system_message, PIN_BLOCK.format(path=self._doc_path(session), doc=doc)
            )

        modified = request.override(messages=effective, system_message=system_message)
        update = {SESSION_KEY: session, EVENT_KEY: new_event} if new_event else None
        return modified, update

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse | ExtendedModelResponse:
        modified, update = self._prepare(request)
        response = handler(modified)
        if update is not None:
            return ExtendedModelResponse(model_response=response, command=Command(update=update))
        return response

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | ExtendedModelResponse:
        import asyncio

        # _prepare includes the blocking compile model call; keep it off the loop.
        modified, update = await asyncio.to_thread(self._prepare, request)
        response = await handler(modified)
        if update is not None:
            return ExtendedModelResponse(model_response=response, command=Command(update=update))
        return response
