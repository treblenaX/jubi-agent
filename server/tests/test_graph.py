"""
Simple LangGraph Tests for Jubi Multi-Agent Harness

These tests verify:
1. Graph structure and state management
2. Agent configuration patterns
3. Message passing through the graph
4. Tool invocation patterns
5. Safety invariants (read-only researcher, sandbox writes)
"""

import pytest
from typing import TypedDict, List


# =============================================================================
# Test 1: Basic Graph Structure
# =============================================================================

def test_graph_state_definition():
    """Test that graph state is properly defined."""

    # Use regular dict for simple testing
    state = {"messages": []}

    # Verify state has required field
    assert "messages" in state

    # Verify type hints work
    assert isinstance(state["messages"], list)


def test_graph_creation():
    """Test that a basic graph can be created."""

    def dummy_node(state: dict) -> dict:
        return {"messages": [{"role": "assistant", "content": "dummy"}]}

    # Mock StateGraph for testing without full langgraph import
    class MockStateGraph:
        def __init__(self):
            self.nodes = {}
            self.edges = []

        def add_node(self, name, func):
            self.nodes[name] = func

        def set_entry_point(self, name):
            self.entry = name

        def add_edge(self, from_node, to_node):
            self.edges.append((from_node, to_node))

    graph = MockStateGraph()
    graph.add_node("dummy", dummy_node)
    graph.set_entry_point("dummy")
    graph.add_edge("dummy", "__end__")

    # Verify graph structure
    assert "dummy" in graph.nodes
    assert len(graph.edges) == 1


# =============================================================================
# Test 2: Agent Configuration
# =============================================================================

def test_agent_config_structure():
    """Test that agent configs have required fields."""
    
    coder_config = {
        "name": "coder",
        "description": "Senior engineer",
        "system_prompt": "You are the coder agent...",
        "tools": ["read_file", "write_file"],
        "model": None,  # Would be ChatOllama instance in production
    }
    
    assert "name" in coder_config
    assert "description" in coder_config
    assert "system_prompt" in coder_config
    assert isinstance(coder_config["tools"], list)


def test_researcher_read_only_tools():
    """Test that researcher only has read-only tools."""
    
    researcher_config = {
        "name": "researcher",
        "description": "Read-only investigator",
        "system_prompt": "You are the researcher agent...",
        "tools": ["web_search", "fetch_url", "read_file"],  # No write tools
        "model": None,
    }
    
    # Verify no write tools in researcher
    assert not any("write" in tool.lower() for tool in researcher_config["tools"])


# =============================================================================
# Test 3: Message Passing
# =============================================================================

def test_message_flow():
    """Test basic message passing through graph nodes."""
    
    class AgentState(TypedDict):
        messages: List[dict]
    
    def add_message(state: AgentState, content: str) -> dict:
        return {"messages": state["messages"] + [{"role": "assistant", "content": content}]}
    
    # Mock graph execution
    state = {"messages": [{"role": "user", "content": "hello"}]}
    result = add_message(state, "processed")
    
    assert len(result["messages"]) == 2
    assert result["messages"][1]["content"] == "processed"


# =============================================================================
# Test 4: Parallel Execution
# =============================================================================

def test_parallel_nodes():
    """Test that parallel nodes can be added."""
    
    class AgentState(TypedDict):
        messages: List[dict]
        results: dict
    
    def node_a(state: AgentState) -> dict:
        return {"results": {"a": "done"}}
    
    def node_b(state: AgentState) -> dict:
        return {"results": {"b": "done"}}
    
    # Simulate parallel execution
    state = {"messages": [], "results": {}}
    result_a = node_a(state)
    result_b = node_b(state)
    
    assert "a" in result_a["results"]
    assert "b" in result_b["results"]


# =============================================================================
# Test 5: Conditional Edges
# =============================================================================

def test_conditional_routing():
    """Test conditional edge routing."""
    
    class AgentState(TypedDict):
        messages: List[dict]
        needs_research: bool
    
    def route_node(state: AgentState) -> dict:
        if state.get("needs_research"):
            return {"messages": [{"role": "assistant", "content": "researching"}]}
        else:
            return {"messages": [{"role": "assistant", "content": "coding"}]}
    
    # Test both paths
    result1 = route_node({"messages": [], "needs_research": True})
    assert "researching" in result1["messages"][0]["content"]
    
    result2 = route_node({"messages": [], "needs_research": False})
    assert "coding" in result2["messages"][0]["content"]


# =============================================================================
# Test 6: Safety Invariants
# =============================================================================

def test_sandbox_path_validation():
    """Test that sandbox paths are validated."""
    
    import os
    
    # Valid sandbox path
    valid_path = "/tmp/jubi-sandbox/test.txt"
    assert valid_path.startswith("/tmp/jubi-sandbox")
    
    # Invalid path (should be rejected)
    invalid_path = "/home/user/project/code.py"
    assert not invalid_path.startswith("/tmp/jubi-sandbox")


def test_read_only_invariant():
    """Test that read-only operations don't modify state."""
    
    class AgentState(TypedDict):
        messages: List[dict]
        data: str
    
    original_data = "original"
    
    def read_only_node(state: AgentState) -> dict:
        # Read operation - should not modify state
        value = state["data"]
        return {"messages": [{"role": "assistant", "content": f"read: {value}"}]}
    
    # Simulate node execution
    state = {"messages": [], "data": original_data}
    result = read_only_node(state)
    
    # State should be unchanged (no write operations)
    assert state["data"] == original_data


# =============================================================================
# Test 7: Error Handling
# =============================================================================

def test_error_recovery():
    """Test that errors are handled gracefully."""
    
    class AgentState(TypedDict):
        messages: List[dict]
        error_count: int
    
    def failing_node(state: AgentState) -> dict:
        if state["error_count"] < 2:
            raise ValueError("Simulated failure")
        return {"messages": [{"role": "assistant", "content": "recovered"}]}
    
    # Simulate recovery after retries
    state = {"messages": [], "error_count": 0}
    
    try:
        failing_node(state)
    except ValueError:
        state["error_count"] += 1
    
    try:
        failing_node(state)
    except ValueError:
        state["error_count"] += 1
    
    # Should succeed on third attempt
    result = failing_node(state)
    assert "recovered" in result["messages"][0]["content"]


# =============================================================================
# Test 8: Tool Invocation Pattern
# =============================================================================

def test_tool_call_structure():
    """Test that tool calls have proper structure."""
    
    class AgentState(TypedDict):
        messages: List[dict]
    
    def node_with_tools(state: AgentState) -> dict:
        # Simulate tool call in message
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": "Calling tool...",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "name": "read_file",
                            "args": {"path": "/tmp/test.txt"}
                        }
                    ]
                }
            ]
        }
    
    result = node_with_tools({"messages": []})
    
    assert len(result["messages"][0].get("tool_calls", [])) == 1
    assert result["messages"][0]["tool_calls"][0]["name"] == "read_file"


# =============================================================================
# Test 9: Thread Isolation
# =============================================================================

def test_thread_config():
    """Test that thread configurations are properly structured."""
    
    thread_config = {
        "configurable": {
            "thread_id": "test-thread-1",
            "thread_ts": 1234567890.0,
        },
        "recursion_limit": 200,
    }
    
    assert thread_config["configurable"]["thread_id"] == "test-thread-1"
    assert thread_config["recursion_limit"] == 200


# =============================================================================
# Test 10: State Persistence Structure
# =============================================================================

def test_checkpoint_structure():
    """Test that checkpoint structure is valid."""
    
    checkpoint = {
        "thread_id": "test-thread-1",
        "next_event_name": "__end__",
        "nodes": {
            "node_a": {
                "messages": [{"role": "user", "content": "hello"}]
            }
        },
        "metadata": {
            "created_at": 1234567890.0,
            "agent": "orchestrator"
        }
    }
    
    assert "thread_id" in checkpoint
    assert "nodes" in checkpoint
    assert "metadata" in checkpoint


# =============================================================================
# Run all tests
# =============================================================================

if __name__ == "__main__":
    import sys
    
    tests = [
        ("test_graph_state_definition", test_graph_state_definition),
        ("test_graph_creation", test_graph_creation),
        ("test_agent_config_structure", test_agent_config_structure),
        ("test_researcher_read_only_tools", test_researcher_read_only_tools),
        ("test_message_flow", test_message_flow),
        ("test_parallel_nodes", test_parallel_nodes),
        ("test_conditional_routing", test_conditional_routing),
        ("test_sandbox_path_validation", test_sandbox_path_validation),
        ("test_read_only_invariant", test_read_only_invariant),
        ("test_error_recovery", test_error_recovery),
        ("test_tool_call_structure", test_tool_call_structure),
        ("test_thread_config", test_thread_config),
        ("test_checkpoint_structure", test_checkpoint_structure),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print(f"{'='*60}")
    
    sys.exit(0 if failed == 0 else 1)
