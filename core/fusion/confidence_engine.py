"""Confidence scoring utilities for fused entity sets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from core.domain import BaseEntity


SOURCE_RELIABILITY: dict[str, float] = {
    "github": 0.9,
    "gitlab": 0.86,
    "dns": 0.88,
    "surface": 0.85,
    "certificate_transparency": 0.82,
    "http_probe": 0.8,
    "correlation": 0.78,
    "anomaly_filter": 0.75,
}


def score_entity_confidence(entity: BaseEntity, related_count: int) -> float:
    """Score one entity confidence in 0.0-1.0 range."""

    base = max(0.0, min(1.0, float(entity.confidence)))
    reliability = SOURCE_RELIABILITY.get(entity.source.strip().lower(), 0.72)
    relation_bonus = min(0.18, float(related_count) * 0.03)
    blended = (base * 0.6) + (reliability * 0.35) + relation_bonus
    return max(0.0, min(1.0, blended))


def aggregate_confidence_score(
    entities: Sequence[BaseEntity],
    relation_map: Mapping[str, Sequence[str]],
) -> float:
    """Compute aggregate confidence on 0-100 scale."""

    rows = list(entities)
    if not rows:
        return 0.0

    scores = [
        score_entity_confidence(entity, len(relation_map.get(entity.id, [])))
        for entity in rows
    ]
    return round((sum(scores) / len(scores)) * 100.0, 2)
