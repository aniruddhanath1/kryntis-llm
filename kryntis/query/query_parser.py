"""Query Parser for intent and filter extraction."""

from typing import Dict, Any

class QueryParser:
    """Extracts explicit search filters, tags, and domain intents."""
    @staticmethod
    def parse_query(raw_query: str) -> Dict[str, Any]:
        filters = {}
        cleaned = raw_query
        if "domain:" in raw_query:
            parts = raw_query.split("domain:")
            cleaned = parts[0].strip()
            domain_part = parts[1].split()[0]
            filters["domain"] = domain_part
        return {
            "query": cleaned,
            "filters": filters
        }
