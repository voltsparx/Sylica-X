"""Filter entities by allowed scope rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.domain import BaseEntity
from core.filters.base_filter import BaseFilter


class ScopeFilter(BaseFilter):
    """Keep entities inside configured source/type scope."""

    filter_id = "scope"

    def apply(self, entities: Sequence[BaseEntity], context: Mapping[str, Any]) -> list[BaseEntity]:
        allowed_sources = context.get("allowed_sources", [])
        allowed_types = context.get("allowed_types", [])

        source_set = {
            str(item).strip().lower()
            for item in allowed_sources
            if isinstance(item, str) and item.strip()
        }
        type_set = {
            str(item).strip().lower()
            for item in allowed_types
            if isinstance(item, str) and item.strip()
        }

        if not source_set and not type_set:
            return list(entities)

        output: list[BaseEntity] = []
        for entity in entities:
            source_ok = not source_set or entity.source.strip().lower() in source_set
            type_ok = not type_set or entity.entity_type.strip().lower() in type_set
            if source_ok and type_ok:
                output.append(entity)
        return output
