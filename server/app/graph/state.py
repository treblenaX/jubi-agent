"""
Jubi Multi-Agent Harness - Graph State Definition

This module defines the custom state extensions for DeepAgents,
following LangGraph best practices for state management.
"""

from typing import TypedDict, List, Optional, Any, Dict
from langgraph.graph import StateGraph


class MessageState(TypedDict):
    """Individual message in the conversation."""
    role: str  # "user", "assistant", "system", or "tool"
    content: str
    name: Optional[str] = None  # Optional tool call name
    tool_call_id: Optional[str] = None  # For tool responses


class AgentState(TypedDict):
    """
    Shared state across all agents in the multi-agent harness.
    
    This state is used by LangGraph to maintain conversation context
    and pass data between nodes in the graph.
    """
    messages: List[MessageState]  # Conversation history
    task: Optional[str] = None  # Current task being worked on
    subtasks: List[str] = []  # Breakdown of main task
    status: str = "idle"  # "planning", "executing", "completed", "error"
    current_subagent: Optional[str] = None  # Currently active subagent
    tool_usage: Dict[str, int] = {}  # Track tool calls per node
    token_budget: Optional[int] = None  # Token budget for this session
    findings: List[Dict[str, Any]] = []  # Research findings
    code_artifacts: List[Dict[str, str]] = []  # Generated code files
    error_messages: List[str] = []  # Errors encountered


class DeepAgentState(AgentState):
    """
    Extended state for DeepAgents with additional metadata.
    
    This extends the base AgentState with DeepAgents-specific fields
    for tool execution, file operations, and sub-agent coordination.
    """
    sandbox_path: Optional[str] = None  # Current sandbox directory
    file_operations: List[Dict[str, Any]] = []  # File read/write logs
    shell_commands: List[Dict[str, Any]] = []  # Executed shell commands
    web_results: List[Dict[str, Any]] = []  # Web search results
    research_findings: Dict[str, str] = {}  # Topic -> summary mapping


# Create the state graph with our custom state
def create_state_graph() -> StateGraph:
    """
    Create a LangGraph StateGraph with DeepAgentState.
    
    Returns:
        Configured but uncompiled StateGraph
    """
    # Define the graph with our custom state
    graph = StateGraph(DeepAgentState)
    
    # Set entry point (will be configured in workflow.py)
    # graph.set_entry_point("planner")
    
    return graph


# Export types for use in other modules
__all__ = ["MessageState", "AgentState", "DeepAgentState", "create_state_graph"]
