"""Terminal Layout engine inspired by React Ink."""

from typing import List

class TerminalLayout:
    """Computes box boundaries and layout splits for CLI UI."""
    @staticmethod
    def create_box(title: str, content: List[str], width: int = 60) -> str:
        border = "+" + "-" * (width - 2) + "+"
        lines = [border, f"| {title.center(width - 4)} |", border]
        for line in content:
            lines.append(f"| {line.ljust(width - 4)[:width - 4]} |")
        lines.append(border)
        return "\n".join(lines)
