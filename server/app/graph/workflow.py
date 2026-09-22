"""
Jubi Multi-Agent Harness - Workflow Definition

This module defines the LangGraph workflow that orchestrates
the multi-agent system using DeepAgents pattern.
"""

from typing import Optional, Dict, Any
from langgraph.graph import StateGraph, END
from app.graph.state import DeepAgentState, create_state_graph
from app.core.config import settings


def build_agent_workflow(checkpointer=None) -> Any:
    """
    Build and compile the multi-agent workflow.
    
    This function creates a LangGraph workflow that:
    1. Initializes with an orchestrator node
    2. Routes to specialized subagents (coder, researcher)
    3. Aggregates results and returns responses
    
    Args:
        checkpointer: Optional checkpoint for persistence
        
    Returns:
        Compiled StateGraph ready for invocation
    """
    # Import here to avoid circular dependencies
    from app.graph import graph as graph_module
    from deepagents import create_deep_agent
    
    # Create the state graph
    workflow = create_state_graph()
    
    # Build the agent using existing graph module (maintains compatibility)
    agent = graph_module.build_agent(checkpointer=checkpointer)
    
    # Configure the workflow with entry point and edges
    try:
        # Set orchestrator as entry point
        workflow.set_entry_point("orchestrator")
        
        # Add edges for subagent routing (handled by DeepAgents internally)
        # The actual routing is managed by the orchestrator's tool spawning
        
        return agent
        
    except Exception as e:
        print(f"Error building workflow: {e}")
        raise


def create_simple_workflow() -> Any:
    """
    Create a simple fallback workflow for testing.
    
    Returns:
        Compiled simple StateGraph
    """
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage, AIMessage
    
    class SimpleState(DeepAgentState):
        pass
    
    def echo_node(state: SimpleState) -> dict:
        """Echo node for simple testing."""
        if state.get('messages'):
            last_msg = state['messages'][-1]
            return {"messages": [AIMessage(content=f"Echo: {last_msg.get('content', '')}")]}
        return {"messages": []}
    
    graph = StateGraph(SimpleState)
    graph.add_node("echo", echo_node)
    graph.set_entry_point("echo")
    workflow = graph.compile()
    
    return workflow


# Export functions
__all__ = ["build_agent_workflow", "create_simple_workflow"]
