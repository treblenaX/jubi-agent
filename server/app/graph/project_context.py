"""
Project context middleware.

If the request's thread belongs to a project (configurable.project_context,
set by chat.py from the projects table), pin the project title + description
into the system prompt on every model call — orchestrator and subagents alike
(parent configurable propagates into subagent invokes). This is how a
project's stored metadata becomes durable context for the AI agents.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain.tools.tool_node import ToolCallRequest
from langgraph.config import get_config
from deepagents.middleware._utils import append_to_system_message


# Custom project tools whose workspace_path kwarg is force-set from the
# request's configurable (chat.py puts the project's workspace_path there).
# Injecting it server-side means the model cannot widen or bypass the jail.
_WORKSPACE_TOOLS = frozenset(
    {
        "read_project_file",
        "write_project_file",
        "edit_project_file",
        "list_project",
        "run_shell",
        "run_tests",
    }
)


class WorkspaceSandboxMiddleware(AgentMiddleware):
    """Force the project's workspace_path into every filesystem tool call.

    When the thread's project pins a workspace_path (configurable.workspace_path,
    set by chat.py), any tool call to a project filesystem tool gets that path
    injected as its workspace_path argument — overriding whatever the model
    passed. Tools then resolve/validate paths against the workspace, so all
    tool actions stay inside the project's directory.
    """

    def _workspace(self) -> str | None:
        try:
            cfg = get_config()
            return (cfg.get("configurable") or {}).get("workspace_path")
        except Exception:
            return None

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        workspace = self._workspace()
        if workspace and request.tool_call.get("name") in _WORKSPACE_TOOLS:
            args = dict(request.tool_call.get("args") or {})
            args["workspace_path"] = workspace
            request = replace(request, tool_call={**request.tool_call, "args": args})
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        return self.wrap_tool_call(request, handler)


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
