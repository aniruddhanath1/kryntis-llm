"""Terminal UI Status Bar component."""

class StatusBar:
    """Renders real-time model and hardware telemetry status in terminal."""
    @staticmethod
    def render(model_name: str = "Kryntis-4.0", ram_usage_mb: float = 450.0, tokens_per_sec: float = 42.5) -> str:
        return f"[Status] Model: {model_name} | RAM: {ram_usage_mb:.1f} MB | Speed: {tokens_per_sec:.1f} tok/s"
