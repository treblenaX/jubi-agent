"""
Jubi Multi-Agent Harness - Web Search Tools (researcher subagent)

Sync implementations — the subagent graph runs via deepagents' task tool
(subagent.invoke(), a sync path), so async-only tools raise
"StructuredTool does not support sync invocation". Keep these sync.

SAFETY: read-only on project code. fetch_url persists fetched pages to the
project's .jubi/research/ folder (or the thread sandbox when no project
workspace is active) so full content is re-readable without re-fetching;
it never writes anywhere else.
"""

import hashlib
import os
import re
from typing import List, Dict, Any, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from langgraph.config import get_config

from app.core.config import settings

# Chars of fetched content returned into the subagent's context; the full
# text is persisted for just-in-time re-reads (keep identifiers in context,
# load detail on demand).
_RETURN_CHARS = 1000


def _research_context() -> Tuple[Optional[str], str]:
    """Resolve (workspace_path, thread_id) from the langgraph config.

    Server-side resolution: the model never passes a path, so it cannot aim
    or widen the persistence location.
    """
    try:
        conf = get_config().get("configurable") or {}
        return conf.get("workspace_path"), str(conf.get("thread_id") or "unknown")
    except Exception:
        return None, "unknown"


def _persist_research(
    url: str, text: str, workspace_path: Optional[str], thread_id: str
) -> Dict[str, Any]:
    """Persist full fetched content; return pointer info. Best-effort.

    With a project workspace: <workspace>/.jubi/research/<hash>.md and a
    workspace-relative pointer (read_project_file resolves relative paths
    against the workspace). Without: <SANDBOX_ROOT>/<tid>/research/.
    Persistence failure never breaks the fetch.
    """
    try:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        if workspace_path:
            base = os.path.join(workspace_path, ".jubi", "research")
            pointer = f".jubi/research/{digest}.md"
        else:
            tid = thread_id if re.fullmatch(r"[A-Za-z0-9_-]+", str(thread_id)) else "unknown"
            base = os.path.join(settings.SANDBOX_ROOT, tid, "research")
            pointer = os.path.join(base, f"{digest}.md")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{digest}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {url}\n\n{text}")
        return {"saved_to": pointer, "saved_path": path, "full_length": len(text)}
    except Exception:
        return {}


def web_search(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web via the ddgs package (DuckDuckGo).

    Args:
        query: Search query string
        num_results: Number of results to return

    Returns:
        List of dicts with title, url, snippet. Empty list on failure —
        maintain the list type contract so callers can iterate safely.
    """
    try:
        from ddgs import DDGS

        raw = DDGS().text(query, max_results=max(1, min(num_results, 10)))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw
        ]
    except Exception as e:
        print(f"web_search failed: {type(e).__name__}: {e}")
        return []


def fetch_url(url: str, max_length: int = _RETURN_CHARS) -> Dict[str, Any]:
    """
    Fetch a URL and extract readable text (requests + BeautifulSoup).

    The full extracted text is persisted (best-effort) to the project's
    .jubi/research/ folder — or the thread sandbox when no project workspace
    is active — and only the first `max_length` chars return into context,
    with the saved path for just-in-time re-reads.

    Args:
        url: URL to fetch
        max_length: Maximum characters of extracted text to return

    Returns:
        Dict with status, url, title, content (excerpt), length, and
        saved_to (path of the persisted full text) — or error message.
    """
    try:
        headers = {"User-Agent": "Jubi Multi-Agent Harness (researcher)"}
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)

        if response.status_code != 200:
            return {"status": "error", "message": f"HTTP {response.status_code}: {url}"}

        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("title") or soup.find("h1")
        title = title_tag.get_text().strip() if title_tag else url

        # Strip chrome; keep content
        for tag in ["nav", "footer", "aside", "script", "style", "noscript"]:
            for elem in soup.find_all(tag):
                elem.decompose()

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"id": "content"})
            or soup.body
            or soup
        )
        text = main.get_text(separator="\n", strip=True)

        persisted = _persist_research(url, text, *_research_context())

        if len(text) > max_length:
            pointer = persisted.get("saved_to", "research file")
            text = text[:max_length] + (
                f"\n\n… (truncated, {len(text)} chars total — full text saved to {pointer})"
            )

        result = {
            "status": "success",
            "url": response.url,
            "title": title,
            "content": text,
            "length": len(text),
        }
        if persisted.get("saved_to"):
            result["saved_to"] = persisted["saved_to"]
        return result
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Network error fetching {url}: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Fetch failed: {e}"}


__all__ = ["web_search", "fetch_url"]
