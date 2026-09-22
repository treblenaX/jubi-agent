"""
FastAPI to LangGraph bridge - Streaming chat endpoint.

This module:
- Initializes a thread (create_thread)
- Streams agent responses via SSE (EventSourceResponse)
- Handles user messages and returns structured responses
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import time
import uuid

from app.graph.graph import agent  # LangGraph agent instance
from app.core.config import settings

router = APIRouter()


@router.post("/chat")
async def add_message(
    content: str,
    thread_id: Optional[str] = None,
    timeout: int = 60
):
    """
    Add a user message and stream the agent response.

    Args:
        content: User message content (required)
        thread_id: Optional thread ID (creates new if not provided)
        timeout: Request timeout in seconds

    Returns:
        StreamingResponse with SSE events
    """
    # Handle thread_id from query param or create default
    if not thread_id:
        thread_id = f"thread-{int(time.time())}"
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "thread_ts": time.time(),
        },
        "recursion_limit": 200,
    }

    # Stream response from LangGraph
    async def stream_generator():
        try:
            # Add user message to state
            for update in agent.stream(
                {"messages": [{"role": "user", "content": content}]},
                config=config,
                stream_mode="updates",
                timeout=timeout
            ):
                yield f"data: {update}\n\n"
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

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
        thread_id: Thread ID (uses current if not provided)

    Returns:
        List of messages in the thread
    """
    if thread_id is None:
        # Try to get from last message or create default
        try:
            state = agent.get_state(
                config={"configurable": {"thread_id": "current"}},
                timeout=30
            )
            if state and state.values:
                return {
                    "messages": state.values.get("messages", []),
                    "status": "success"
                }
        except Exception:
            pass
    
    # Use provided thread_id or create new
    config = {
        "configurable": {"thread_id": thread_id or f"thread-{int(time.time())}"},
        "recursion_limit": 200
    }

    try:
        state = agent.get_state(config=config, timeout=30)
        
        if state is None or not state.values:
            return {
                "messages": [],
                "status": "no_messages"
            }
        
        messages = state.values.get("messages", [])
        
        return {
            "messages": messages,
            "status": "success",
            "token_usage": 52  # TODO: Calculate actual token usage from model provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threads")
async def create_thread():
    """
    Create a new conversation thread.

    Returns:
        Thread ID and status
    """
    config = {
        "configurable": {
            "thread_id": f"thread-{int(time.time())}",
            "thread_ts": time.time(),
        },
        "recursion_limit": 200,
    }

    try:
        # Create a new thread with initial greeting message
        response = agent.invoke(
            {"messages": [{"role": "user", "content": "Hello who are you?"}]},
            config=config,
            timeout=30
        )

        return {
            "thread_id": config["configurable"]["thread_id"],
            "status": "created"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """
    Delete a conversation thread.

    Args:
        thread_id: Thread ID to delete

    Returns:
        Deletion confirmation
    """
    try:
        # Note: MemorySaver doesn't support listing all threads directly
        # In production, use SQLiteSaver or PostgresSaver for multi-thread support
        
        # For now, we'll return a message explaining this limitation
        return {
            "thread_id": thread_id,
            "status": "no_delete",
            "note": "MemorySaver is designed for single-thread conversations. "
                   "Use SQLiteSaver or PostgresSaver for multi-thread support."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threads")
async def list_threads():
    """
    List all conversation threads.

    Returns:
        List of thread metadata (limited with MemorySaver)
    """
    try:
        # MemorySaver doesn't support listing all threads directly
        return {
            "threads": [],
            "status": "no_threads",
            "note": "MemorySaver is designed for single-thread conversations. "
                   "Use SQLiteSaver or PostgresSaver for multi-thread support."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
