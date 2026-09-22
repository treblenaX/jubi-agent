"""
Web fetch and search tools for researcher agent.

SAFETY INVARIANTS:
- Researcher MUST NOT write to any filesystem
- Researcher MUST only use read-only tools (web_fetch, search)
- Researcher MUST cite all sources in results
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import time


@dataclass
class Source:
    """Represents a research source."""
    url: str
    title: str
    summary: str
    excerpt: str


def web_search(query: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web for relevant results.
    
    Args:
        query: Search query string
        count: Number of results (1-10)
        
    Returns:
        List of search result dicts with title, url, snippet
    """
    try:
        from urllib.parse import quote
        
        # Use duckduckgo for privacy-friendly searches
        url = f"https://duckduckgo.com/html/?q={quote(query)}&ia=web"
        
        response = web_fetch(url)
        
        if not response:
            return []
        
        # Parse search results from DuckDuckGo HTML
        results = []
        
        # Simple regex-based parsing for DuckDuckGo results
        import re
        
        # Find result links (href="...")
        link_pattern = r'href=["\']([^"\']*duckduckgo.com[^"\']*)["\']'
        links = re.findall(link_pattern, response)
        
        for link in links[:count]:
            if "q=" in link:
                # Extract query from URL
                query_part = link.split("q=")[1].split("&")[0]
                
                results.append({
                    "title": f"DuckDuckGo Search Result",
                    "url": link,
                    "snippet": f"Search results for: {query}",
                    "source_type": "search_engine"
                })
                break
        
        if not results:
            # Try Google as fallback
            url = f"https://www.google.com/search?q={quote(query)}&num={count}"
            response = web_fetch(url)
            
            if response:
                # Parse Google results
                result_pattern = r'<a href=["\']([^"\']*url=)[^"\']*">([^<]*)</a>'
                matches = re.findall(result_pattern, response)
                
                for url_match, title in matches[:count]:
                    full_url = f"{url_match}?url={quote(query)}"
                    results.append({
                        "title": title.strip(),
                        "url": full_url,
                        "snippet": "",
                        "source_type": "google_search"
                    })
        
        return results
        
    except Exception as e:
        # Return empty list on error, not a dict - maintain list type contract
        return []


def fetch_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch and summarize content from a URL.
    
    SAFETY: Read-only operation - never writes to filesystem
    
    Args:
        url: URL to fetch
        
    Returns:
        Dict with title, summary, excerpt, or error message
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Fetch the URL
        headers = {
            "User-Agent": "Jubi Multi-Agent Harness (researcher)"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"HTTP {response.status_code}: {url}"
            }
        
        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract title
        title_tag = soup.find("title") or soup.find("h1") or soup.find("h2")
        title = title_tag.get_text().strip() if title_tag else url
        
        # Remove nav, footer, ads
        for tag in ["nav", "footer", "aside", "script", "style"]:
            for elem in soup.find_all(tag):
                elem.decompose()
        
        # Extract main content
        main = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"})
        if not main:
            main = soup.find(lambda tag: tag.name in ["p", "h1", "h2", "h3"])
        
        # Get text content
        text = main.get_text(separator="\n", strip=True) if main else response.text
        
        # Limit length
        if len(text) > 5000:
            text = text[:5000] + "\n\n... (truncated)"
        
        # Create summary (first paragraph or first sentence)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        summary = paragraphs[0] if paragraphs else text[:200] + "..."
        
        return {
            "status": "success",
            "url": url,
            "title": title,
            "summary": summary,
            "excerpt": text[:500],
            "word_count": len(text.split()),
            "source_type": "web_page"
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Network error fetching {url}: {e}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Fetch failed: {e}"
        }
