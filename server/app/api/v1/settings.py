"""
Settings API — GET/PUT runtime settings + model list for the settings menu.

PUT persists the patch and rebuilds the agent (model, num_ctx, and the
compaction middleware are baked in at build time).
"""

from fastapi import APIRouter, HTTPException, Request
import httpx

from app.core import runtime
from app.core.config import settings
from app.graph.graph import rebuild_agent

router = APIRouter()


@router.get("/settings")
async def get_settings():
    """Current runtime settings."""
    return runtime.get()


@router.get("/models")
async def list_models():
    """Models available on the Ollama server (for the model dropdown)."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
        return {"models": sorted(n for n in models if n), "connected": True}
    except Exception as exc:
        return {"models": [], "connected": False, "error": f"{type(exc).__name__}: {exc}"}


@router.put("/settings")
async def put_settings(request: Request):
    """Validate + persist a settings patch, then rebuild the agent."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="body must be JSON")

    # Best-effort model existence check (skipped when Ollama is unreachable)
    if isinstance(body, dict) and "model" in body:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                names = [m.get("name", "") for m in resp.json().get("models", [])]
            if body["model"] not in names:
                raise HTTPException(
                    status_code=422,
                    detail=f"model '{body['model']}' not available on Ollama server",
                )
        except HTTPException:
            raise
        except Exception:
            pass  # offline: allow, health dot will report connectivity

    try:
        current = runtime.update(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    rebuild_agent()
    return {**current, "rebuilt": True}
