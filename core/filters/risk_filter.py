"""Risk-oriented filter for sensitive content suppression."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.domain import BaseEntity
from core.filters.base_filter import BaseFilter


DEFAULT_BLOCKED_TERMS = ("password", "secret", "token", "apikey", "api_key")


class RiskFilter(BaseFilter):
    """Remove entities carrying explicitly sensitive terms."""

    filter_id = "risk"

    def apply(self, entities: Sequence[BaseEntity], context: Mapping[str, Any]) -> list[BaseEntity]:
        blocked_terms = context.get("blocked_terms")
        terms = DEFAULT_BLOCKED_TERMS
        if isinstance(blocked_terms, list):
            custom = [str(item).strip().lower() for item in blocked_terms if isinstance(item, str) and item.strip()]
            if custom:
                terms = tuple(custom)

        output: list[BaseEntity] = []
        for entity in entities:
            haystack = f"{entity.value} {' '.join(str(item) for item in dict(entity.attributes).values())}".lower()
            if any(term in haystack for term in terms):
                continue
            output.append(entity)
        return output
