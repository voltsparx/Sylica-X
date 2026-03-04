"""Filter pipeline exports and registry helpers."""

from core.filters.base_filter import BaseFilter
from core.filters.builtins import AnomalyFilter, ConfidenceFilter, DuplicateFilter, RelevanceFilter
from core.filters.depth_filter import DepthFilter
from core.filters.keyword_filter import KeywordFilter
from core.filters.pipeline import FilterPipeline
from core.filters.risk_filter import RiskFilter
from core.filters.scope_filter import ScopeFilter


def build_filter_registry() -> dict[str, BaseFilter]:
    """Build default filter registry for policy-driven selection."""

    filters: list[BaseFilter] = [
        DuplicateFilter(),
        ConfidenceFilter(),
        RelevanceFilter(),
        AnomalyFilter(),
        ScopeFilter(),
        KeywordFilter(),
        RiskFilter(),
        DepthFilter(),
    ]
    return {filter_item.filter_id: filter_item for filter_item in filters}


__all__ = [
    "AnomalyFilter",
    "BaseFilter",
    "ConfidenceFilter",
    "DuplicateFilter",
    "FilterPipeline",
    "DepthFilter",
    "KeywordFilter",
    "RelevanceFilter",
    "RiskFilter",
    "ScopeFilter",
    "build_filter_registry",
]
