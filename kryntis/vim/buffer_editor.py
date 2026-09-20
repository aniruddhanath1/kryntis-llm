"""In-memory Text Buffer editor."""

from typing import List

class BufferEditor:
    """Manages line-by-line in-memory text editing buffer."""
    def __init__(self, initial_text: str = "") -> None:
        self.lines: List[str] = initial_text.splitlines() if initial_text else [""]

    def insert_line(self, line_idx: int, text: str) -> None:
        self.lines.insert(line_idx, text)

    def delete_line(self, line_idx: int) -> None:
        if 0 <= line_idx < len(self.lines):
            self.lines.pop(line_idx)

    def get_content(self) -> str:
        return "\n".join(self.lines)
