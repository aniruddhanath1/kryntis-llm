"""SSH Tunnel Handler for port forwarding."""

class TunnelHandler:
    """Manages local and remote SSH port tunnels."""
    def __init__(self, local_port: int = 8000, remote_port: int = 8000) -> None:
        self.local_port = local_port
        self.remote_port = remote_port
        self.is_active = False

    def open_tunnel(self) -> None:
        self.is_active = True

    def close_tunnel(self) -> None:
        self.is_active = False
