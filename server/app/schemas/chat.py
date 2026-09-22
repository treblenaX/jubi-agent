"""Pydantic Models for Chat API - Jubi Multi-Agent Harness"""

from pydantic import BaseModel, Field
from typing import Optional, List


class UserInput(BaseModel):
    """User message input model."""
    content: str = Field(..., description="User message content")
    thread_id: Optional[str] = Field(None, description="Optional thread ID")
    timeout: int = Field(60, description="Request timeout in seconds")


class StreamResponse(BaseModel):
    """Streaming response model."""
    messages: List[dict] = Field(default_factory=list)
    status: str = Field(..., description="Response status")
    thread_id: Optional[str] = Field(None, description="Thread ID")


class ThreadSchema(BaseModel):
    """Thread schema for API responses."""
    thread_id: str
    status: str
    messages: Optional[List[dict]] = None
