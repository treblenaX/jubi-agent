"""FastAPI Routing Layer - Jubi Multi-Agent Harness API"""

from .v1 import router as v1_router

# Export the v1 router as the main router
router = v1_router

__all__ = ["router"]
