"""Ink ANSI Renderer."""

import sys

class InkRenderer:
    """Renders virtual component tree to stdout with cursor repositioning."""
    @staticmethod
    def render(view_text: str) -> None:
        sys.stdout.write(view_text + "\n")
        sys.stdout.flush()
