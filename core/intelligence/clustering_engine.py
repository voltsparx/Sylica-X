"""Entity clustering derived from relationship links."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from core.intelligence.correlation_engine import CorrelationLink


class _DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        if item not in self.parent:
            self.parent[item] = item

    def find(self, item: str) -> str:
        parent = self.parent.get(item, item)
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent.get(item, item)

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


class ClusteringEngine:
    """Build structural clusters using strong relationship links."""

    def build_clusters(
        self,
        entities: Sequence[Mapping[str, Any]],
        relationships: Sequence[CorrelationLink],
        confidence_by_entity: Mapping[str, float],
    ) -> list[dict[str, Any]]:
        """Return cluster payloads from correlated entity graph."""

        dsu = _DisjointSet()
        entity_ids = [str(row.get("id", "")).strip() for row in entities if str(row.get("id", "")).strip()]
        for entity_id in entity_ids:
            dsu.add(entity_id)

        relationship_reasons: dict[tuple[str, str], str] = {}
        for link in relationships:
            if link.strength_score < 0.55:
                continue
            dsu.add(link.source_entity_id)
            dsu.add(link.target_entity_id)
            dsu.union(link.source_entity_id, link.target_entity_id)
            left_id, right_id = sorted((link.source_entity_id, link.target_entity_id))
            key = (left_id, right_id)
            relationship_reasons[key] = link.reason

        groups: dict[str, list[str]] = {}
        for entity_id in entity_ids:
            root = dsu.find(entity_id)
            groups.setdefault(root, []).append(entity_id)

        clusters: list[dict[str, Any]] = []
        cluster_index = 1
        for members in sorted(groups.values(), key=lambda row: (-len(row), row[0])):
            if len(members) <= 1:
                continue
            confidences = [float(confidence_by_entity.get(entity_id, 0.0)) for entity_id in members]
            average_confidence = sum(confidences) / float(len(confidences)) if confidences else 0.0
            if average_confidence >= 0.8:
                confidence_level = "high"
            elif average_confidence >= 0.5:
                confidence_level = "medium"
            else:
                confidence_level = "low"

            reason_counter: Counter[str] = Counter()
            for left in members:
                for right in members:
                    if left >= right:
                        continue
                    left_id, right_id = sorted((left, right))
                    key = (left_id, right_id)
                    reason = relationship_reasons.get(key)
                    if reason:
                        reason_counter[reason] += 1
            cluster_reason = reason_counter.most_common(1)[0][0] if reason_counter else "shared_entities"

            clusters.append(
                {
                    "cluster_id": f"cluster-{cluster_index:03d}",
                    "members": sorted(members),
                    "confidence_level": confidence_level,
                    "cluster_reason": cluster_reason,
                }
            )
            cluster_index += 1

        return clusters
