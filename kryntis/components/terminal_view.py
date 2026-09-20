"""Terminal View Component."""

class TerminalView:
    """Manages scrollable terminal viewports and message formatting."""
    @staticmethod
    def render_message(role: str, content: str) -> str:
        prefix = "[User]" if role == "user" else "[Kryntis AI]"
        return f"{prefix} {content}"
