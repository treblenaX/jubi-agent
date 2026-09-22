#!/usr/bin/env python3
"""
Jubi Multi-Agent Harness - Server Entry Point

This script starts the FastAPI server using the new modular architecture.
Run with: python server.py
Or use: uvicorn app.main:app --host 127.0.0.1 --port 2024
"""

import sys
import os

# Add server directory to path
sys.path.insert(0, '/home/ec/.nanobot/workspace/jubi/server')

from app.main import app


def main():
    """Start the server."""
    import uvicorn
    
    # Load settings
    from app.core.config import settings
    
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Sandbox: {settings.SANDBOX_ROOT}")
    print(f"Ollama: {settings.OLLAMA_BASE_URL}/{settings.OLLAMA_MODEL}")
    
    # Build agent (lazy initialization)
    from app.graph.graph import agent
    print("✓ Agent built and ready.")
    
    # Run server
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info",
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()
