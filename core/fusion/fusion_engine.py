"""Entity-only fusion engine for correlation and graph synthesis."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from core.domain import BaseEntity


class FusionEngine:
    """Fuse entities into a confidence-scored graph payload."""

    def fuse(self, entities: Sequence[BaseEntity]) -> dict[str, Any]:
        """Fuse entities into summary, anomalies, and relationship graph."""

        items = list(entities)
        graph = self.build_relationship_graph(items)
        anomalies = self.detect_anomalies(items)
        confidence = self.calculate_confidence(items)

        entity_counts: dict[str, int] = defaultdict(int)
        for entity in items:
            entity_counts[entity.entity_type] += 1

        return {
            "entity_count": len(items),
            "entity_counts": dict(entity_counts),
            "confidence_score": confidence,
            "anomalies": anomalies,
            "graph": graph,
        }

    def calculate_confidence(self, entities: Sequence[BaseEntity]) -> float:
        """Calculate weighted confidence score in 0-100 scale."""

        rows = list(entities)
        if not rows:
            return 0.0
        total = sum(item.confidence for item in rows)
        return round((total / len(rows)) * 100.0, 2)

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
        """Build a lightweight relationship graph from entity metadata."""

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        by_id = {entity.id: entity for entity in entities}
        for entity in entities:
            nodes.append(
                {
                    "id": entity.id,
                    "type": entity.entity_type,
                    "value": entity.value,
                    "source": entity.source,
                    "confidence": entity.confidence,
                }
            )

        # Relation: profile owner links to email artifacts.
        for entity in entities:
            if entity.entity_type != "email":
                continue
            owner = str(dict(entity.attributes).get("owner", "")).strip().lower()
            if not owner:
                continue
            for candidate in entities:
                if candidate.entity_type != "profile":
                    continue
                if candidate.value.strip().lower() != owner:
                    continue
                edges.append(
                    {
                        "source": candidate.id,
                        "target": entity.id,
                        "kind": "owns_email",
                    }
                )

        # Relation: subdomains map to parent domain.
        for entity in entities:
            attributes = dict(entity.attributes)
            parent_domain = str(attributes.get("parent_domain", "")).strip().lower()
            if not parent_domain:
                continue
            for candidate in entities:
                if candidate.entity_type != "domain":
                    continue
                if candidate.value.strip().lower() != parent_domain:
                    continue
                edges.append(
                    {
                        "source": candidate.id,
                        "target": entity.id,
                        "kind": "contains_asset",
                    }
                )

        # Relation: anomaly assets attach to source entity when entity_id exists.
        for entity in entities:
            linked_id = dict(entity.attributes).get("entity_id")
            if not isinstance(linked_id, str):
                continue
            if linked_id in by_id:
                edges.append(
                    {
                        "source": linked_id,
                        "target": entity.id,
                        "kind": "flagged_by",
                    }
                )

        return {"nodes": nodes, "edges": edges}
