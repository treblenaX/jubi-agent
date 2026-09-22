"""FastAPI v1 API Router - Jubi Multi-Agent Harness"""

from .chat import router as chat_router
from .files import router as files_router

__all__ = ["router"]

# Combine routers (no /v1 prefix - routes at /chat and /files)
from fastapi import APIRouter

router = APIRouter()  # No prefix
router.include_router(chat_router, prefix="/chat")
router.include_router(files_router, prefix="/files")
