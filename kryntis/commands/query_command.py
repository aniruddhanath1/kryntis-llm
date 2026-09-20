"""Query command executor."""

from typing import Dict, Any
from kryntis.QueryEngine import default_query_engine

class QueryCommand:
    """Dispatches standalone prompt query to engine."""
    @staticmethod
    def execute(prompt: str, session_id: str = "cmd-session") -> Dict[str, Any]:
        return default_query_engine.execute(query=prompt, session_id=session_id)
