"""Readability-style content extractor."""

from __future__ import annotations

from bs4 import BeautifulSoup

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_REMOVE_TAGS = ["script", "style", "nav", "footer", "aside", "header", "form", "iframe"]


class ContentExtractor:
    """Extracts clean article text from raw HTML."""

    def extract(self, html: str, url: str = "") -> str:
        try:
            # Try readability first
            from readability import Document
            doc = Document(html)
            clean_html = doc.summary()
            soup = BeautifulSoup(clean_html, "lxml")
            text = soup.get_text(" ", strip=True)
            if len(text) > 200:
                return text
        except Exception:
            pass

        # Fallback: basic BS4 extraction
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(_REMOVE_TAGS):
            tag.decompose()
        return soup.get_text(" ", strip=True)
