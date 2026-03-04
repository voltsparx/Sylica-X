"""Username intelligence capability backed by scanner adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.adapters import ProfileScannerAdapter
from core.capabilities.base import Capability
from core.domain import AssetEntity, BaseEntity, EmailEntity, ProfileEntity


class UsernameLookupCapability(Capability):
    """Collect profile + email entities from username signals."""

    capability_id = "username_lookup"

    def __init__(self, adapter: ProfileScannerAdapter | None = None) -> None:
        self._adapter = adapter or ProfileScannerAdapter()

    async def execute(self, target: str, context: Mapping[str, Any]) -> list[BaseEntity]:
        mode = str(context.get("mode", "profile")).strip().lower()
        if mode not in {"profile", "fusion"}:
            return []

        timeout_seconds = max(5, int(context.get("timeout", 20)))
        max_workers = max(1, int(context.get("max_workers", 20)))
        source_profile = str(context.get("source_profile", "balanced"))
        max_platforms_value = context.get("max_platforms")
        max_platforms = int(max_platforms_value) if isinstance(max_platforms_value, int) else None
        proxy_url = context.get("proxy_url") if isinstance(context.get("proxy_url"), str) else None

        entities = await self._adapter.collect(
            username=target,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_workers,
            source_profile=source_profile,
            max_platforms=max_platforms,
            proxy_url=proxy_url,
        )
        return list(entities)

    def supported_entities(self) -> tuple[type[BaseEntity], ...]:
        return (ProfileEntity, EmailEntity, AssetEntity)
