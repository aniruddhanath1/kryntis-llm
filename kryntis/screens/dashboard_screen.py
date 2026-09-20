"""Dashboard Screen terminal view."""

class DashboardScreen:
    """Operations and telemetry status dashboard."""
    @staticmethod
    def render(active_models: int = 1, memory_usage_mb: float = 450.0, total_requests: int = 100) -> str:
        return (
            "================= KRYNTIS METRICS DASHBOARD =================\n"
            f"Active Models: {active_models}\n"
            f"Memory In Use: {memory_usage_mb:.1f} MB\n"
            f"Total Queries: {total_requests}\n"
            "=============================================================="
        )
