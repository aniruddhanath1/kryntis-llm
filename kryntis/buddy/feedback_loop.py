"""Feedback loop for interactive buddy suggestions."""

from typing import List, Dict, Any

class BuddyFeedbackLoop:
    """Collects and stores developer feedback on buddy code suggestions."""
    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []

    def log_interaction(self, query: str, code: str, accepted: bool) -> None:
        self._history.append({"query": query, "code": code, "accepted": accepted})

    def get_accuracy_metric(self) -> float:
        if not self._history:
            return 1.0
        accepted_count = sum(1 for item in self._history if item["accepted"])
        return accepted_count / len(self._history)
