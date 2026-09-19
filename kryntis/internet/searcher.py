"""
Web Searcher — DuckDuckGo (free) with optional Brave Search API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearcher:
    """
    Search the web using DuckDuckGo (default, no API key needed)
    or Brave Search API (optional, better quality).
    """

    def __init__(self) -> None:
        cfg = get_config().internet
        self._engine = cfg.search_engine
        self._brave_key = os.getenv("BRAVE_SEARCH_API_KEY", "")

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        if self._engine == "brave" and self._brave_key:
            return await self._brave_search(query, max_results)
        return await self._ddg_search(query, max_results)

    async def _ddg_search(self, query: str, max_results: int) -> list[SearchResult]:
        import asyncio
        try:
            from duckduckgo_search import DDGS
            results: list[SearchResult] = []
            loop = asyncio.get_event_loop()

            def _sync():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))

            raw = await loop.run_in_executor(None, _sync)
            for r in raw:
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                ))
            log.info("ddg_search", query=query, results=len(results))
            return results
        except Exception as e:
            log.error("ddg_search_error", error=str(e))
            return []

    async def _brave_search(self, query: str, max_results: int) -> list[SearchResult]:
        import httpx
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": self._brave_key}
        params = {"q": query, "count": max_results}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("description", ""),
                )
                for r in data.get("web", {}).get("results", [])
            ]
            log.info("brave_search", query=query, results=len(results))
            return results
        except Exception as e:
            log.error("brave_search_error", error=str(e))
            return await self._ddg_search(query, max_results)
