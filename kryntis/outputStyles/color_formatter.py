"""Terminal and UI output styling."""

class ColorFormatter:
    """Color formatter for rich terminal styles."""
    @staticmethod
    def format_code(code_str: str) -> str:
        return f"\033[93m{code_str}\033[0m"

    @staticmethod
    def format_highlight(text: str) -> str:
        return f"\033[96m{text}\033[0m"
