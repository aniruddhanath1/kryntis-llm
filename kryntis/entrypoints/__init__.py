"""Kryntis Entrypoints module."""

from kryntis.entrypoints.cli_entrypoint import main_cli
from kryntis.entrypoints.server_entrypoint import main_server

__all__ = ["main_cli", "main_server"]
