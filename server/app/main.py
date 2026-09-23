"""
Jubi Multi-Agent Harness - FastAPI Application

This is the main application entry point that:
- Sets up middleware (CORS, logging, etc.)
- Registers API routes
- Configures health checks
- Starts the uvicorn server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import sys
import os

# Add server directory to path if needed
if '/home/ec/.nanobot/workspace/jubi/server' not in sys.path:
    sys.path.insert(0, '/home/ec/.nanobot/workspace/jubi/server')

from app.api.v1.chat import router as chat_router
from app.api.v1.files import router as files_router
from app.core.config import settings


async def _check_model() -> dict:
    """Best-effort Ollama probe. Never raises; reports model connectivity."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            names = [m.get("name", "") for m in resp.json().get("models", [])]
        if settings.OLLAMA_MODEL in names:
            return {"connected": True, "name": settings.OLLAMA_MODEL, "error": None}
        return {
            "connected": False,
            "name": settings.OLLAMA_MODEL,
            "error": f"model not available on Ollama server ({len(names)} models installed)",
        }
    except Exception as exc:
        return {
            "connected": False,
            "name": settings.OLLAMA_MODEL,
            "error": f"{type(exc).__name__}: {exc}",
        }


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="LangGraph-based multi-agent development harness",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["access-control-allow-origin"]
    )

    # Include API routes (no /v1 prefix - routes at /chat and /files)
    app.include_router(chat_router)  # Routes will be at /chat/*
    app.include_router(files_router)  # Routes will be at /files/*
    
    # Add custom middleware for logging
    @app.middleware("http")
    async def log_requests(request, call_next):
        import time
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Log request (customize format as needed)
        if settings.DEBUG:
            print(f"{request.method} {request.url.path} - {duration:.3f}s")
        
        return response
    
    # Health check endpoint: API status + model connectivity
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "model": await _check_model()}

    # Root endpoint with service info
    @app.get("/")
    async def root():
        """Root endpoint with service info."""
        return {
            "service": settings.APP_NAME,
            "status": "running",
            "agents": ["orchestrator", "coder", "researcher"],
            "sandbox": settings.SANDBOX_ROOT,
            "docs": "/docs"
        }
    
    # Error handlers
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)}
        )
    
    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    """Run the server directly."""
    import uvicorn
    
    # Build agent on startup (from graph module)
    from app.graph.graph import agent
    
    print(f"✓ Agent built and ready.")
    
    # Run server
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info",
        reload=settings.DEBUG
    )
