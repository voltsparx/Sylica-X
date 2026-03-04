"""Entity-only fusion engine for correlation and graph synthesis."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from core.domain import BaseEntity
from core.fusion.confidence_engine import aggregate_confidence_score
from core.fusion.correlator import correlate_entities
from core.fusion.deduplicator import deduplicate_entities
from core.fusion.graph_builder import build_relationship_graph


class FusionEngine:
    """Fuse entities into a confidence-scored graph payload."""

    def fuse(self, entities: Sequence[BaseEntity]) -> dict[str, Any]:
        """Fuse entities into summary, anomalies, and relationship graph."""

        items = deduplicate_entities(entities)
        relation_map = correlate_entities(items)
        graph = build_relationship_graph(items, relation_map)
        anomalies = self.detect_anomalies(items)
        confidence = aggregate_confidence_score(items, relation_map)

        entity_counts: dict[str, int] = defaultdict(int)
        for entity in items:
            entity_counts[entity.entity_type] += 1

        return {
            "entity_count": len(items),
            "entity_counts": dict(entity_counts),
            "confidence_score": confidence,
            "anomalies": anomalies,
            "graph": graph,
            "relationship_map": relation_map,
        }

    def calculate_confidence(self, entities: Sequence[BaseEntity]) -> float:
        """Calculate weighted confidence score in 0-100 scale."""

        rows = deduplicate_entities(entities)
        relation_map = correlate_entities(rows)
        return aggregate_confidence_score(rows, relation_map)

    def detect_anomalies(self, entities: Sequence[BaseEntity]) -> list[dict[str, Any]]:
        """Extract anomaly signals from entities and metadata."""

        anomalies: list[dict[str, Any]] = []
        for entity in entities:
            attributes = dict(entity.attributes)
            status = str(attributes.get("status", "")).upper()
            if entity.entity_type == "asset" and attributes.get("reason"):
                anomalies.append(
                    {
                        "entity_id": entity.id,
                        "reason": str(attributes.get("reason")),
                        "source": entity.source,
                    }
                )
                continue

            if entity.confidence < 0.3 or status in {"ERROR", "BLOCKED"}:
                reason = "low_confidence"
                if status in {"ERROR", "BLOCKED"}:
                    reason = f"status_{status.lower()}"
                anomalies.append(
                    {
                        "entity_id": entity.id,
                        "reason": reason,
                        "source": entity.source,
                    }
                )
        return anomalies

    def build_relationship_graph(self, entities: Sequence[BaseEntity]) -> dict[str, list[dict[str, Any]]]:
        """Build relationship graph from correlation map."""

        rows = deduplicate_entities(entities)
        relation_map = correlate_entities(rows)
        return build_relationship_graph(rows, relation_map)
