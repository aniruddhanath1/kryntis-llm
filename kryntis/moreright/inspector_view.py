"""Inspector View Component."""

from typing import Dict, Any

class InspectorView:
    """Detailed token, tensor, and grounding inspector."""
    @staticmethod
    def inspect_tokens(tokens: list) -> Dict[str, Any]:
        return {
            "token_count": len(tokens),
            "preview": tokens[:10]
        }
