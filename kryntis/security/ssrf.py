"""
SSRF Protection Utility — validates URLs and rejects private, loopback, link-local, and reserved IP addresses.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class SSRFValidationError(ValueError):
    """Raised when a URL targets a restricted, private, or prohibited address."""
    pass


def is_prohibited_ip(ip_str: str) -> bool:
    """Check whether an IP address belongs to a private, loopback, or reserved subnet."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return True


def validate_safe_url(url: str) -> str:
    """
    Validate that a given URL uses HTTP/HTTPS and resolves only to non-private, public IP addresses.

    Args:
        url: The URL string to validate.

    Returns:
        The normalized URL string if safe.

    Raises:
        SSRFValidationError: If the URL scheme is unsupported or points to private/internal networks.
    """
    if not url or not isinstance(url, str):
        raise SSRFValidationError("URL must be a non-empty string.")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFValidationError(f"Prohibited URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL does not contain a valid hostname.")

    # Check known local aliases
    lowered_host = hostname.lower().strip(".")
    if lowered_host in ("localhost", "0.0.0.0", "127.0.0.1", "::1", "metadata.google.internal"):
        raise SSRFValidationError(f"Targeting local/internal host '{hostname}' is prohibited.")

    # Resolve IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as e:
        raise SSRFValidationError(f"Unable to resolve host '{hostname}': {e}")

    for info in addr_info:
        ip_addr = info[4][0]
        if is_prohibited_ip(ip_addr):
            raise SSRFValidationError(f"Host '{hostname}' resolves to restricted IP address '{ip_addr}'. Request blocked for security.")

    return url
