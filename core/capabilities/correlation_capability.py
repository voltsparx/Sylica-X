"""Correlation capability for cross-entity relationship enrichment."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from core.capabilities.base import Capability
from core.domain import AssetEntity, BaseEntity, EmailEntity, ProfileEntity, make_entity_id


class CorrelationCapability(Capability):
    """Generate relation entities from pre-collected entity sets."""

    capability_id = "correlation"

    async def execute(self, target: str, context: Mapping[str, Any]) -> list[BaseEntity]:
        mode = str(context.get("mode", "profile")).strip().lower()
        if mode not in {"profile", "surface", "fusion"}:
            return []

        existing_entities = context.get("existing_entities", [])
        if not isinstance(existing_entities, list):
            return []

        profiles = [entity for entity in existing_entities if isinstance(entity, ProfileEntity)]
        emails = [entity for entity in existing_entities if isinstance(entity, EmailEntity)]
        if not profiles or not emails:
            return []

        timestamp = datetime.now(tz=timezone.utc)
        generated: list[AssetEntity] = []
        for profile in profiles:
            for email in emails:
                if profile.value.strip().lower() != target.strip().lower():
                    continue
                relationship_value = f"{profile.platform}:{email.value}"
                generated.append(
                    AssetEntity(
                        id=make_entity_id("asset", "correlation", relationship_value),
                        value=relationship_value,
                        source="correlation",
                        timestamp=timestamp,
                        confidence=min(1.0, (profile.confidence + email.confidence) / 2.0),
                        attributes={
                            "profile_id": profile.id,
                            "email_id": email.id,
                            "relation": "profile_contact_link",
                        },
                        asset_kind="correlation",
                    )
                )

        return generated

    def supported_entities(self) -> tuple[type[BaseEntity], ...]:
        return (AssetEntity,)
