"""
Project context middleware.

If the request's thread belongs to a project (configurable.project_context,
set by chat.py from the projects table), pin the project title + description
into the system prompt on every model call — orchestrator and subagents alike
(parent configurable propagates into subagent invokes). This is how a
project's stored metadata becomes durable context for the AI agents.
"""

from __future__ import annotations

from typing import Any, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langgraph.config import get_config
from deepagents.middleware._utils import append_to_system_message


class ProjectContextMiddleware(AgentMiddleware):
    """Append the active project's metadata to the system prompt (every call)."""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        try:
            cfg = get_config()
            ctx = (cfg.get("configurable") or {}).get("project_context")
        except Exception:
            ctx = None
        if ctx:
            request = request.override(
                system_message=append_to_system_message(request.system_message, str(ctx))
            )
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> Any:
        return self.wrap_model_call(request, handler)
