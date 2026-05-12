import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


def validate_url(url):
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only http and https URLs are allowed")

    if not parsed.hostname:
        raise ValueError("URL must include a hostname")

    hostname = parsed.hostname

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip and _is_private_ip(ip):
        raise ValueError("Private, local, or reserved IP addresses are not allowed")

    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError("Could not resolve URL hostname") from exc

    for result in resolved_ips:
        resolved_ip = ipaddress.ip_address(result[4][0])
        if _is_private_ip(resolved_ip):
            raise ValueError("URL resolves to a private, local, or reserved IP address")


def _is_private_ip(ip):
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
