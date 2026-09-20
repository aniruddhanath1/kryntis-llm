"""Vim Modal Editing Engine."""

from enum import Enum
from typing import List

class VimMode(Enum):
    NORMAL = "NORMAL"
    INSERT = "INSERT"
    VISUAL = "VISUAL"
    COMMAND = "COMMAND"

class VimEngine:
    """Simulates modal Vim buffer editing in terminal."""
    def __init__(self) -> None:
        self.mode = VimMode.NORMAL
        self.cursor_row = 0
        self.cursor_col = 0

    def set_mode(self, mode: VimMode) -> None:
        self.mode = mode

    def handle_command(self, cmd: str) -> str:
        if cmd == ":w":
            return "Buffer written to disk"
        elif cmd == ":q":
            return "Exiting vim session"
        return f"Unknown command {cmd}"
