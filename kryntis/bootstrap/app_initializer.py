"""Application Initializer for Kryntis system startup."""

from typing import Dict, Any
from kryntis.utils.config import load_config
from kryntis.repositories.document_repository import SQLiteDocumentRepository
from kryntis.repositories.session_repository import SQLiteSessionRepository

class AppInitializer:
    """Bootstraps storage, models, and repositories."""
    @staticmethod
    def initialize(config_path: str = "config/default.yaml") -> Dict[str, Any]:
        config = load_config(config_path)
        doc_repo = SQLiteDocumentRepository()
        session_repo = SQLiteSessionRepository()
        return {
            "status": "initialized",
            "config": config,
            "doc_repo": doc_repo,
            "session_repo": session_repo
        }
