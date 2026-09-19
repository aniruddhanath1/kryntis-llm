"""
Internet Research Pipeline — end-to-end web research.

Flow: Query → Search → Fetch → Validate → Extract → Chunk → Embed → Cite → (Optionally Learn)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from kryntis.internet.citation_builder import Citation, CitationBuilder
from kryntis.internet.extractor import ContentExtractor
from kryntis.internet.fetcher import PageFetcher
from kryntis.internet.searcher import SearchResult, WebSearcher
from kryntis.internet.validator import URLValidator
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class ResearchResult:
    """Output of the full internet research pipeline."""
    query: str
    citations: list[Citation] = field(default_factory=list)
    context_text: str = ""
    search_results_count: int = 0
    fetched_count: int = 0
    trusted_count: int = 0
    elapsed_seconds: float = 0.0


class InternetResearchPipeline:
    """
    Controlled internet research pipeline.

    Does NOT auto-trust web content. Each result goes through
    URL validation, domain authority scoring, and content trust checks
    before being added to the research context.
    """

    def __init__(self) -> None:
        cfg = get_config().internet
        self._searcher = WebSearcher()
        self._fetcher = PageFetcher()
        self._validator = URLValidator()
        self._extractor = ContentExtractor()
        self._citation_builder = CitationBuilder()
        self._max_fetches = cfg.max_concurrent_fetches
        self._min_trust = cfg.min_domain_trust_score

    async def research(
        self,
        query: str,
        max_results: int | None = None,
        learn: bool = False,
    ) -> ResearchResult:
        """
        Run the full research pipeline for a query.

        Args:
            query: The search query.
            max_results: Override for number of search results.
            learn: If True, validated high-confidence content is stored.

        Returns:
            ResearchResult with citations and context text.
        """
        cfg = get_config().internet
        n = max_results or cfg.max_results
        start = time.time()

        # ── 1. Search ────────────────────────────────────────────────────────
        search_results: list[SearchResult] = await self._searcher.search(query, n)
        log.info("research_search_done", query=query, results=len(search_results))

        # ── 2. Validate URLs ─────────────────────────────────────────────────
        valid_results = [
            r for r in search_results
            if self._validator.is_allowed(r.url)
        ]
        log.info("research_url_validation", valid=len(valid_results), total=len(search_results))

        # ── 3. Fetch concurrently (bounded) ──────────────────────────────────
        sem = asyncio.Semaphore(self._max_fetches)

        async def fetch_one(result: SearchResult):
            async with sem:
                return await self._fetcher.fetch(result.url)

        fetch_tasks = [fetch_one(r) for r in valid_results]
        fetched_pages = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # ── 4. Extract, score, and build citations ───────────────────────────
        context_parts: list[str] = []
        citations: list[Citation] = []
        fetched_count = 0
        trusted_count = 0

        for search_res, page in zip(valid_results, fetched_pages):
            if isinstance(page, Exception) or page is None:
                continue
            fetched_count += 1

            text = self._extractor.extract(page.html, url=page.url)
            if not text:
                continue

            trust = self._validator.trust_score(page.url, text)
            if trust < self._min_trust:
                log.debug("research_low_trust", url=page.url, score=trust)
                continue

            trusted_count += 1
            snippet = text[:2000]
            citation = self._citation_builder.build(
                url=page.url,
                title=search_res.title,
                snippet=snippet,
                trust_score=trust,
            )
            citations.append(citation)
            context_parts.append(f"[Source: {citation.title} | {citation.url}]\n{snippet}")

        context_text = "\n\n---\n\n".join(context_parts)

        result = ResearchResult(
            query=query,
            citations=citations,
            context_text=context_text,
            search_results_count=len(search_results),
            fetched_count=fetched_count,
            trusted_count=trusted_count,
            elapsed_seconds=round(time.time() - start, 2),
        )

        log.info(
            "research_done",
            query=query,
            citations=len(citations),
            trusted=trusted_count,
            elapsed=result.elapsed_seconds,
        )
        return result
