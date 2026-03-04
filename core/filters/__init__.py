"""Filter pipeline exports and registry helpers."""

from core.filters.base_filter import BaseFilter
from core.filters.builtins import AnomalyFilter, ConfidenceFilter, DuplicateFilter, RelevanceFilter
from core.filters.pipeline import FilterPipeline


def build_filter_registry() -> dict[str, BaseFilter]:
    """Build default filter registry for policy-driven selection."""

    filters: list[BaseFilter] = [
        DuplicateFilter(),
        ConfidenceFilter(),
        RelevanceFilter(),
        AnomalyFilter(),
    ]
    return {filter_item.filter_id: filter_item for filter_item in filters}


__all__ = [
    "AnomalyFilter",
    "BaseFilter",
    "ConfidenceFilter",
    "DuplicateFilter",
    "FilterPipeline",
    "RelevanceFilter",
    "build_filter_registry",
]
