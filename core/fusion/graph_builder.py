"""Graph builder for fused entities and relationship maps."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.domain import BaseEntity


def build_relationship_graph(
    entities: Sequence[BaseEntity],
    relation_map: Mapping[str, Sequence[str]],
) -> dict[str, list[dict[str, Any]]]:
    """Build graph nodes and edges from entities and relationship map."""

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

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

    seen_edges: set[tuple[str, str]] = set()
    for source_id, target_ids in relation_map.items():
        for target_id in target_ids:
            if source_id == target_id:
                continue
            edge_key = tuple(sorted((source_id, target_id)))
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append({"source": source_id, "target": target_id, "kind": "related"})

    return {"nodes": nodes, "edges": edges}
