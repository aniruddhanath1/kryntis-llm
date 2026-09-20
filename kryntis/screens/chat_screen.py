"""Chat Screen terminal view."""

class ChatScreen:
    """Full-screen interactive chat view."""
    @staticmethod
    def render(session_id: str, message_count: int) -> str:
        return f"=== Chat Session: {session_id} | Total turns: {message_count} ==="
