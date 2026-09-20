"""Sidebar Panel UI component for auxiliary inspector views."""

from typing import Dict, Any

class SidebarPanel:
    """Renders right-hand inspection metadata pane."""
    @staticmethod
    def render_panel(telemetry: Dict[str, Any]) -> str:
        lines = ["=== TELEMETRY & ATTRIBUTES ==="]
        for k, v in telemetry.items():
            lines.append(f"{k}: {v}")
        return "\n".join(lines)
