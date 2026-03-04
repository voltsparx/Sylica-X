"""Network routing settings for scan HTTP clients."""

from __future__ import annotations

import os
from urllib.parse import urlsplit


ALLOWED_PROXY_SCHEMES = {"http", "https", "socks5", "socks5h"}


def _validate_proxy_url(proxy_url: str, source: str) -> str:
    value = proxy_url.strip()
    if not value:
        raise RuntimeError(f"{source} is set but empty.")

    parsed = urlsplit(value)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_PROXY_SCHEMES:
        allowed = ", ".join(sorted(ALLOWED_PROXY_SCHEMES))
        raise RuntimeError(
            f"{source} uses unsupported proxy scheme '{parsed.scheme}'. "
            f"Supported schemes: {allowed}."
        )

    if not parsed.hostname:
        raise RuntimeError(f"{source} must include a proxy host.")

    return value


def get_network_settings(use_proxy: bool, use_tor: bool) -> str | None:
    """Resolve proxy URL based on Tor or HTTP_PROXY settings."""

    if use_tor:
        # socks5h keeps DNS resolution inside Tor.
        return "socks5h://127.0.0.1:9050"

    if use_proxy:
        proxy = os.environ.get("HTTP_PROXY")
        source = "HTTP_PROXY"
        if not proxy:
            proxy = os.environ.get("HTTPS_PROXY")
            source = "HTTPS_PROXY"
        if not proxy:
            raise RuntimeError("Proxy requested but neither HTTP_PROXY nor HTTPS_PROXY is set.")
        return _validate_proxy_url(proxy, source)

    return None
