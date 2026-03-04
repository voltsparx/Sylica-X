"""Built-in filter implementations for orchestration pipeline."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from core.domain import AssetEntity, BaseEntity, make_entity_id
from core.filters.base_filter import BaseFilter


class DuplicateFilter(BaseFilter):
    """Remove duplicate entities by stable semantic key."""

    filter_id = "duplicate"

    def apply(self, entities: Sequence[BaseEntity], context: Mapping[str, Any]) -> list[BaseEntity]:
        unique: list[BaseEntity] = []
        seen: set[tuple[str, str, str]] = set()
        for entity in entities:
            key = (entity.entity_type, entity.value.strip().lower(), entity.source.strip().lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(entity)
        return unique


class ConfidenceFilter(BaseFilter):
    """Retain entities meeting minimum confidence threshold."""

    filter_id = "confidence"

    def apply(self, entities: Sequence[BaseEntity], context: Mapping[str, Any]) -> list[BaseEntity]:
        threshold = float(context.get("min_confidence", 0.25))
        threshold = max(0.0, min(1.0, threshold))
        return [entity for entity in entities if entity.confidence >= threshold]


class RelevanceFilter(BaseFilter):
    """Retain entities relevant to target identity or domain."""

    filter_id = "relevance"

    def apply(self, entities: Sequence[BaseEntity], context: Mapping[str, Any]) -> list[BaseEntity]:
        raw_targets = context.get("targets")
        targets: list[str] = []
        if isinstance(raw_targets, list):
            targets.extend(
                str(item).strip().lower()
                for item in raw_targets
                if isinstance(item, str) and item.strip()
            )
        primary_target = str(context.get("target", "")).strip().lower()
        if primary_target:
            targets.append(primary_target)

        normalized_targets: list[str] = []
        seen: set[str] = set()
        for target in targets:
            if target in seen:
                continue
            seen.add(target)
            normalized_targets.append(target)

        if not normalized_targets:
            return list(entities)

        filtered: list[BaseEntity] = []
        for entity in entities:
            entity_value = entity.value.strip().lower()
            metadata_text = " ".join(str(value).lower() for value in dict(entity.attributes).values())
            if any(target in entity_value or target in metadata_text for target in normalized_targets):
                filtered.append(entity)
        return filtered


class AnomalyFilter(BaseFilter):
    """Append anomaly entities for suspicious low-confidence findings."""

    filter_id = "anomaly"

    def apply(self, entities: Sequence[BaseEntity], context: Mapping[str, Any]) -> list[BaseEntity]:
        target = str(context.get("target", "")).strip().lower()
        results = list(entities)
        now = datetime.now(tz=timezone.utc)

        for entity in entities:
            attributes = dict(entity.attributes)
            status = str(attributes.get("status", "")).upper()
            low_confidence = entity.confidence < 0.35
            flagged_status = status in {"ERROR", "BLOCKED"}
            if not low_confidence and not flagged_status:
                continue

            anomaly_value = f"anomaly::{entity.id}"
            results.append(
                AssetEntity(
                    id=make_entity_id("asset", "anomaly", anomaly_value),
                    value=anomaly_value,
                    source="anomaly_filter",
                    timestamp=now,
                    confidence=0.9,
                    attributes={
                        "target": target,
                        "entity_id": entity.id,
                        "reason": "low_confidence_or_blocked_status",
                        "status": status or "unknown",
                    },
                    asset_kind="anomaly",
                )
            )

        return results
