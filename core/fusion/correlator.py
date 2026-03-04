"""Entity correlator for cross-domain relationship mapping."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from core.domain import BaseEntity


def correlate_entities(entities: Sequence[BaseEntity]) -> dict[str, list[str]]:
    """Build bidirectional entity relationship map."""

    rows = list(entities)
    by_id = {entity.id: entity for entity in rows}
    relation_map: dict[str, set[str]] = defaultdict(set)

    domain_ids_by_value = {
        entity.value.strip().lower(): entity.id for entity in rows if entity.entity_type == "domain"
    }
    profile_ids_by_username = {
        entity.value.strip().lower(): entity.id for entity in rows if entity.entity_type == "profile"
    }

    for entity in rows:
        for related_id in entity.relationships:
            if related_id in by_id and related_id != entity.id:
                relation_map[entity.id].add(related_id)
                relation_map[related_id].add(entity.id)

        metadata = dict(entity.attributes)
        owner = str(metadata.get("owner", "")).strip().lower()
        if owner and owner in profile_ids_by_username:
            profile_id = profile_ids_by_username[owner]
            relation_map[entity.id].add(profile_id)
            relation_map[profile_id].add(entity.id)

        parent_domain = str(metadata.get("parent_domain", "")).strip().lower()
        if parent_domain and parent_domain in domain_ids_by_value:
            domain_id = domain_ids_by_value[parent_domain]
            relation_map[entity.id].add(domain_id)
            relation_map[domain_id].add(entity.id)

        linked_id = metadata.get("entity_id")
        if isinstance(linked_id, str) and linked_id in by_id and linked_id != entity.id:
            relation_map[entity.id].add(linked_id)
            relation_map[linked_id].add(entity.id)

    return {entity_id: sorted(related_ids) for entity_id, related_ids in relation_map.items()}
