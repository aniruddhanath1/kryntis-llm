"""Vim Keybinding definitions."""

from typing import Dict

VIM_NORMAL_MODE_BINDINGS: Dict[str, str] = {
    "h": "cursor_left",
    "j": "cursor_down",
    "k": "cursor_up",
    "l": "cursor_right",
    "i": "enter_insert_mode",
    ":w": "save_session",
    ":q": "exit_session"
}
