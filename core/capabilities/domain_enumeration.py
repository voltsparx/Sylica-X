"""Domain enumeration capability backed by domain adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.adapters import DomainSurfaceAdapter
from core.capabilities.base import Capability
from core.domain import AssetEntity, BaseEntity, DomainEntity, IpEntity


class DomainEnumerationCapability(Capability):
    """Collect domain, asset, and IP entities from surface scan signals."""

    capability_id = "domain_enumeration"

    def __init__(self, adapter: DomainSurfaceAdapter | None = None) -> None:
        self._adapter = adapter or DomainSurfaceAdapter()

    async def execute(self, target: str, context: Mapping[str, Any]) -> list[BaseEntity]:
        mode = str(context.get("mode", "surface")).strip().lower()
        if mode not in {"surface", "fusion"}:
            return []

        timeout_seconds = max(5, int(context.get("timeout", 20)))
        include_ct = bool(context.get("include_ct", True))
        include_rdap = bool(context.get("include_rdap", True))
        max_subdomains = max(10, int(context.get("max_subdomains", 250)))

        entities = await self._adapter.collect(
            domain=target,
            timeout_seconds=timeout_seconds,
            include_ct=include_ct,
            include_rdap=include_rdap,
            max_subdomains=max_subdomains,
        )
        return list(entities)

    def supported_entities(self) -> tuple[type[BaseEntity], ...]:
        return (DomainEntity, AssetEntity, IpEntity)
