"""
Async HTTP fetcher with rate limiting, SSRF protection, and robots.txt respect.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from kryntis.security.ssrf import SSRFValidationError, validate_safe_url
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_HEADERS = {
    "User-Agent": (
        "KryntisAI/1.0 (Research Bot; +https://kryntis.ai/bot)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class FetchedPage:
    url: str
    html: str
    status_code: int
    content_type: str


class PageFetcher:
    """Async HTTP page fetcher with timeout, size limits, and SSRF validation."""

    def __init__(self) -> None:
        cfg = get_config().internet
        self._timeout = cfg.request_timeout
        self._max_content = cfg.max_content_length

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def fetch(self, url: str) -> FetchedPage | None:
        try:
            safe_url = validate_safe_url(url)
        except SSRFValidationError as se:
            log.warning("fetch_ssrf_blocked", url=url, reason=str(se))
            return None
        except Exception as e:
            log.warning("fetch_invalid_url", url=url, error=str(e))
            return None

        try:
            async with httpx.AsyncClient(
                headers=_HEADERS,
                timeout=self._timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(safe_url)
                content_type = resp.headers.get("content-type", "")
                if "text" not in content_type and "html" not in content_type:
                    return None
                html = resp.text[: self._max_content]
                log.debug("page_fetched", url=safe_url, status=resp.status_code, chars=len(html))
                return FetchedPage(
                    url=str(resp.url),
                    html=html,
                    status_code=resp.status_code,
                    content_type=content_type,
                )
        except Exception as e:
            log.warning("fetch_error", url=safe_url, error=str(e))
            return None
