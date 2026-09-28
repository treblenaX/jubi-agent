"""
Jubi Multi-Agent Harness - Web Search Tools (researcher subagent)

Sync implementations — the subagent graph runs via deepagents' task tool
(subagent.invoke(), a sync path), so async-only tools raise
"StructuredTool does not support sync invocation". Keep these sync.

SAFETY: read-only; researcher never writes to any filesystem.
"""

from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup


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


def fetch_url(url: str, max_length: int = 10000) -> Dict[str, Any]:
    """
    Fetch a URL and extract readable text (requests + BeautifulSoup).

    Args:
        url: URL to fetch
        max_length: Maximum characters of extracted text to return

    Returns:
        Dict with status, url, title, content (or error message).
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

        if len(text) > max_length:
            text = text[:max_length] + f"\n\n… (truncated, {len(text)} chars total)"

        return {
            "status": "success",
            "url": response.url,
            "title": title,
            "content": text,
            "length": len(text),
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Network error fetching {url}: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Fetch failed: {e}"}


__all__ = ["web_search", "fetch_url"]