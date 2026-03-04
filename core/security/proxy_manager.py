"""Proxy and anonymity runtime manager for orchestrated scans."""

from __future__ import annotations

from dataclasses import dataclass

from core.collect.network import get_network_settings


@dataclass(frozen=True)
class ProxySettings:
    """Resolved network routing settings for scan execution."""

    use_proxy: bool = False
    use_tor: bool = False

    def resolve_proxy_url(self) -> str | None:
        """Resolve runtime proxy URL or raise runtime errors from network layer."""

        return get_network_settings(self.use_proxy, self.use_tor)


def build_proxy_settings(config: dict[str, object]) -> ProxySettings:
    """Build immutable proxy settings from generic config map."""

    return ProxySettings(
        use_proxy=bool(config.get("use_proxy", False)),
        use_tor=bool(config.get("use_tor", False)),
    )
