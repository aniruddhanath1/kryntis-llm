"""Internet sub-package."""
from kryntis.internet.searcher import WebSearcher, SearchResult
from kryntis.internet.fetcher import PageFetcher, FetchedPage
from kryntis.internet.validator import URLValidator
from kryntis.internet.extractor import ContentExtractor
from kryntis.internet.citation_builder import CitationBuilder, Citation
from kryntis.internet.research_pipeline import InternetResearchPipeline, ResearchResult

__all__ = [
    "WebSearcher", "SearchResult",
    "PageFetcher", "FetchedPage",
    "URLValidator",
    "ContentExtractor",
    "CitationBuilder", "Citation",
    "InternetResearchPipeline", "ResearchResult",
]
