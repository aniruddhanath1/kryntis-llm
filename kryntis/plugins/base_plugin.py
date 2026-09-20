"""Base plugin class for kryntis core."""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePlugin(ABC):
    name: str = "base"
    version: str = "1.0.0"

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    def on_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return payload

    def on_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return response
