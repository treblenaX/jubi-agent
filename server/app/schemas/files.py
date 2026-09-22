"""Pydantic Models for Files API - Jubi Multi-Agent Harness"""

from pydantic import BaseModel, Field
from typing import Optional


class FileMetadataSchema(BaseModel):
    """File metadata schema."""
    name: str = Field(..., description="Filename")
    size: int = Field(..., description="File size in bytes")
    created: Optional[str] = Field(None, description="Creation timestamp")
    modified: Optional[str] = Field(None, description="Last modification timestamp")
    type: str = Field(..., description="file or directory")
