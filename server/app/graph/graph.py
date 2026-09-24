"""
Jubi Multi-Agent Graph Definition

This module defines the LangGraph state machine for the multi-agent harness.
Uses deepagents with Ollama models for local inference.
Follows the new architecture with separated subagents and tools.
"""

from typing import TypedDict, List, Optional, Dict, Any
import operator
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from deepagents import create_deep_agent
from deepagents.middleware.summarization import SummarizationMiddleware
from deepagents.backends import FilesystemBackend
from app.core.config import settings
from app.core import runtime
from app.graph.state_doc import StateDocMiddleware


# Define graph state
class AgentState(TypedDict):
    """Shared state across all agents."""
    messages: List[dict]


# Create shared model (single model for all agents)
def make_model(name=None, temp=settings.OLLAMA_TEMPERATURE,
               base_url=settings.OLLAMA_BASE_URL):
    """
    Create a shared Ollama model instance from current runtime settings.

    Start with ONE shared model (no VRAM swap thrash). Split per-role later.

    Args:
        name: Model name (default: runtime settings model)
        temp: Temperature for generation
        base_url: Ollama server URL (default: your network host)

    Returns:
        Configured ChatOllama instance
    """
    rs = runtime.get()
    return ChatOllama(
        model=name or rs["model"],
        temperature=temp,
        num_ctx=rs["num_ctx"],
        keep_alive=settings.OLLAMA_KEEP_ALIVE,
        reasoning=True,  # surface model thoughts in additional_kwargs['reasoning_content']
        base_url=base_url
    )


# System prompts for each agent role
ORCHESTRATOR_PROMPT = """You are the orchestrator agent in a multi-agent development harness.

Your responsibilities:
1. Parse user intent from messages
2. Validate safety invariants before dispatch
3. Dispatch tasks to coder or researcher subagents
4. Aggregate results and stream responses
5. Manage token budget per session

Safety rules:
- NEVER write outside /tmp/jubi-sandbox/
- NEVER bypass safety checks
- ALWAYS cite sources for research findings

Dispatch format: "spawn:{agent_name} {task}"
Valid agents: coder, researcher
"""

CODER_PROMPT = """You are the coder agent, a senior engineer.

Your responsibilities:
1. Generate code in memory first
2. Write ONLY to /tmp/jubi-sandbox/
3. Run tests within sandbox
4. Report success/failure with details

Safety rules:
- NEVER write outside /tmp/jubi-sandbox/
- ALWAYS validate file paths before writing
- NEVER read/write outside sandbox

Workflow:
1. Parse task requirements
2. Generate code in memory
3. Write to sandbox path
4. Run tests if specified
5. Return results
"""

RESEARCHER_PROMPT = """You are the researcher agent, a read-only investigator.

Your responsibilities:
1. Fetch URLs via web_fetch tool
2. Extract and summarize content
3. NEVER write to filesystem
4. Return structured findings with citations

Safety rules:
- NEVER write to any filesystem
- NEVER modify project code
- ONLY use read-only tools (web_search, fetch_url)
- ALWAYS cite all sources in results

Workflow:
1. Parse research query
2. Fetch relevant URLs via web_search or fetch_url
3. Extract and summarize content
4. Return structured findings with citations
"""


def build_agent(checkpointer=None):
    """
    Build the orchestrator agent with subagents.
    
    Args:
        checkpointer: Optional SQLite checkpointer for persistence
        
    Returns:
        Configured deepagent ready for langgraph
    """
    # Import tools from new location
    import sys
    sys.path.insert(0, '/home/ec/.nanobot/workspace/jubi/server')
    
    from app.graph.tools import (
        read_project_file, write_project_file, edit_project_file,
        list_project, run_shell, run_tests, web_search, fetch_url
    )
    
    # Shared model built from current runtime settings (rebuild picks up changes)
    shared = make_model()

    # Define subagent configs (plain dicts - the deepagents contract)
    coder = {
        "name": "coder",
        "description": ("Senior engineer. Writes, edits, and tests code in the "
                        "project sandbox. Send a full work order: goal, paths, "
                        "constraints, definition of done."),
        "system_prompt": CODER_PROMPT,
        "tools": [read_project_file, write_project_file, edit_project_file,
                  list_project, run_shell, run_tests],
        "model": shared,  # or make_model("qwen2.5-coder:14b")
    }

    researcher = {
        "name": "researcher",
        "description": ("Read-only investigator (web + project files). Saves "
                        "detailed findings to findings/<topic>.md and returns a "
                        "short summary. Use before coding unfamiliar things."),
        "system_prompt": RESEARCHER_PROMPT,
        "tools": [web_search, fetch_url, read_project_file, list_project],
        "model": shared,  # or make_model("qwen3:8b", temp=0.3)
    }

    # Compaction middleware (SPEC-02). Two strategies behind one trigger/keep:
    # - state_doc: StateDocMiddleware compiles durable state (architecture
    #   decisions, requirements, unresolved bugs, next steps) into a per-thread
    #   markdown doc on the sandbox backend, evicts the middle of the history,
    #   and pins the doc into the system prompt every call.
    # - summary: deepagents SummarizationMiddleware (LLM summary + offload).
    # Trigger stored as % of num_ctx in settings, sent as absolute tokens —
    # fractional triggers require model profile metadata ChatOllama lacks.
    rs = runtime.get()
    backend = FilesystemBackend(root_dir=settings.SANDBOX_ROOT)
    middleware = ()
    if rs["compaction_enabled"]:
        trigger_tokens = int(rs["compaction_trigger_fraction"] * rs["num_ctx"])
        if rs.get("compaction_mode", "state_doc") == "summary":
            middleware = (
                SummarizationMiddleware(
                    model=shared,
                    backend=backend,
                    trigger=("tokens", trigger_tokens),
                    keep=("messages", rs["compaction_keep_messages"]),
                ),
            )
        else:
            middleware = (
                StateDocMiddleware(
                    model=shared,
                    backend=backend,
                    trigger_tokens=trigger_tokens,
                    keep_messages=rs["compaction_keep_messages"],
                ),
            )

    return create_deep_agent(
        model=shared,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[list_project, read_project_file],  # read-only peek; NO writes
        subagents=[coder, researcher],
        middleware=middleware,
        backend=backend,  # agent FS tools share the sandbox: state docs +
        # offloaded conversation history become readable via read_file/ls
        checkpointer=checkpointer,
    )


# Load skills when module is imported (if not in REPL mode)
def load_researcher_skills():
    """
    Load and register researcher skills dynamically.

    This function:
    1. Loads sample skills from sample_research_skills.py
    2. Loads nanobot skills from /home/ec/.nanobot/workspace/skills/
    3. Registers them with the skill registry
    4. Attaches the registry to the researcher agent

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Import and load sample skills
        from app.graph.tools.researcher_skills import get_registry

        registry = get_registry()

        # Try to load sample skills if available
        try:
            from tools.sample_research_skills import (
                MultiPageScraperSkill,
                StructuredDataExtractorSkill,
                ContentComparisonSkill,
                PriceMonitorSkill,
                ExecutiveSummarySkill
            )

            skills_to_register = [
                MultiPageScraperSkill(),
                StructuredDataExtractorSkill(),
                ContentComparisonSkill(),
                PriceMonitorSkill(),
                ExecutiveSummarySkill()
            ]

            for skill in skills_to_register:
                registry.register(skill)

        except ImportError as e:
            # Sample skills not available, but core functionality still works
            print(f"Note: Sample skills not loaded ({e}). Core research tools available.")

        # Load nanobot skills from skills directory
        try:
            from app.graph.tools.nanobot_skill_loader import get_registry as get_nanobot_registry

            nanobot_registry = get_nanobot_registry()
            nanobot_registry.load_all_skills()

            # Merge nanobot skills into main registry
            for name, skill in nanobot_registry._skills.items():
                if name not in registry._skills:
                    registry.register(skill)

        except Exception as e:
            print(f"Note: Failed to load nanobot skills ({e}). Core research tools available.")

        # Attach registry to researcher agent (use the local researcher variable from build_agent scope)
        # Note: This function is called during module import when researcher is in local scope
        # For external calls, we need to pass the researcher config or use a different approach
        if 'researcher' in locals():
            researcher["skills"] = registry

        return True, f"Loaded {len(registry._skills)} researcher skills (including nanobot skills)"

    except Exception as e:
        print(f"Warning: Failed to load researcher skills: {e}")
        return False, f"Skills loading failed: {e}"


# Load skills when module is imported (if not in REPL mode)
if __name__ != "__main__":
    success, message = load_researcher_skills()
    print(f"Researcher skills: {message}")


# Import tool functions from tools module
from app.graph.tools.filesystem_tool import (
    read_project_file,
    write_project_file,
    edit_project_file,
    list_project,
    run_shell,
    run_tests,
)
from app.graph.tools.web_search import web_search, fetch_url
from app.graph.tools.search_tool import grep_project


# Module-level export for `langgraph dev` — langgraph.json points at this.
# Server persistence: SQLite checkpointer keyed by thread_id (§9.3).
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

_ckpt_conn = sqlite3.connect("harness.db", check_same_thread=False)
agent = build_agent(checkpointer=SqliteSaver(_ckpt_conn))


def get_agent():
    """Current agent instance (rebuild_agent swaps the module reference)."""
    return agent


def rebuild_agent():
    """Rebuild the agent from current runtime settings (settings PUT path).

    Reuses the module-level checkpointer connection so thread persistence
    survives the swap. Raises if the new agent fails to build (the old
    agent stays live in that case — the exception propagates to the API).
    """
    global agent
    agent = build_agent(checkpointer=SqliteSaver(_ckpt_conn))
    return agent


if __name__ == "__main__":
    """Debug REPL: python graph.py (build steps 1-6, §14)"""
    from langgraph.checkpoint.sqlite import SqliteSaver

    with SqliteSaver.from_conn_string("harness.db") as ckpt:
        repl = build_agent(checkpointer=ckpt)
        config = {"configurable": {"thread_id": "dev-session-1"},
                  "recursion_limit": 50}
        print("dev-harness REPL ready. Ctrl-C to exit.\n")
        while True:
            try:
                user = input("you> ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not user:
                continue
            
            for update in repl.stream(
                {"messages": [{"role": "user", "content": user}]},
                config=config, stream_mode="updates",
            ):
                for node, payload in update.items():
                    for m in (payload or {}).get("messages", []):
                        kind = getattr(m, "type", "?")
                        if kind == "ai" and getattr(m, "tool_calls", None):
                            for tc in m.tool_calls:
                                print(f"  [{node}] → tool {tc['name']}"
                                      f"({str(tc['args'])[:120]})")
                        elif kind == "ai" and m.content:
                            print(f"\nassistant> {m.content}\n")
                        elif kind == "tool":
                            print(f"  [{node}] ← {str(m.content)[:150]}")
