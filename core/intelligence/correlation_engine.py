"""Relationship correlation with explainable evidence traces."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


@dataclass(frozen=True)
class CorrelationLink:
    """Directed correlation link between two entities."""

    source_entity_id: str
    target_entity_id: str
    reason: str
    evidence_reference: str
    strength_score: float

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-friendly link payload."""

        return {
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "reason": self.reason,
            "evidence_reference": self.evidence_reference,
            "strength_score": round(max(0.0, min(1.0, float(self.strength_score))), 4),
        }


_PHONE_DIGITS = set("0123456789")
_MAX_SOURCE_CLUSTER = 18
_MAX_WEAK_ARTIFACT_CLUSTER = 30
_MAX_PAIR_COUNT = 25000


def _first_evidence_id(entity: Mapping[str, Any]) -> str:
    evidence_ids = entity.get("evidence_ids", [])
    if isinstance(evidence_ids, Sequence) and evidence_ids:
        return str(evidence_ids[0])
    return ""


def _normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in str(raw or "") if ch in _PHONE_DIGITS)
    if len(digits) < 7:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


def _extract_domains(entity: Mapping[str, Any]) -> set[str]:
    domains: set[str] = set()
    value = str(entity.get("value", "")).strip().lower()
    entity_type = str(entity.get("entity_type", "")).strip().lower()
    if entity_type == "email" and "@" in value:
        domains.add(value.split("@", maxsplit=1)[1])
    if entity_type == "domain" and "." in value:
        domains.add(value)

    attributes = entity.get("attributes", {})
    if isinstance(attributes, Mapping):
        for key in ("domain", "root_domain", "email_domain", "registrar_domain", "parent_domain"):
            raw = str(attributes.get(key, "")).strip().lower()
            if raw and "." in raw:
                domains.add(raw)
    domains.update(_extract_link_domains(entity))
    return domains


def _extract_emails(entity: Mapping[str, Any]) -> set[str]:
    emails: set[str] = set()
    value = str(entity.get("value", "")).strip().lower()
    if "@" in value:
        emails.add(value)
    attributes = entity.get("attributes", {})
    if isinstance(attributes, Mapping):
        contacts = attributes.get("contacts", {})
        if isinstance(contacts, Mapping):
            raw_emails = contacts.get("emails", [])
            if isinstance(raw_emails, Sequence):
                for item in raw_emails:
                    token = str(item).strip().lower()
                    if "@" in token:
                        emails.add(token)
    return emails


def _extract_phones(entity: Mapping[str, Any]) -> set[str]:
    phones: set[str] = set()
    attributes = entity.get("attributes", {})
    if isinstance(attributes, Mapping):
        contacts = attributes.get("contacts", {})
        if isinstance(contacts, Mapping):
            raw_phones = contacts.get("phones", [])
            if isinstance(raw_phones, Sequence):
                for item in raw_phones:
                    token = _normalize_phone(str(item))
                    if token:
                        phones.add(token)
    value = str(entity.get("value", "")).strip()
    if value:
        token = _normalize_phone(value)
        if token:
            phones.add(token)
    return phones


def _extract_mentions(entity: Mapping[str, Any]) -> set[str]:
    mentions: set[str] = set()
    attributes = entity.get("attributes", {})
    if isinstance(attributes, Mapping):
        raw_mentions = attributes.get("mentions", [])
        if isinstance(raw_mentions, Sequence):
            for item in raw_mentions:
                token = str(item).strip().lower()
                if token:
                    mentions.add(token.lstrip("@"))
    value = str(entity.get("value", "")).strip().lower()
    if value.startswith("@"):
        mentions.add(value.lstrip("@"))
    return mentions


def _extract_link_domains(entity: Mapping[str, Any]) -> set[str]:
    hosts: set[str] = set()
    attributes = entity.get("attributes", {})
    if isinstance(attributes, Mapping):
        raw_links = attributes.get("links", [])
        if isinstance(raw_links, Sequence):
            for item in raw_links:
                try:
                    parsed = urlparse(str(item))
                except ValueError:
                    continue
                host = str(parsed.netloc or "").strip().lower()
                if host.startswith("www."):
                    host = host[4:]
                if host:
                    hosts.add(host)
    value = str(entity.get("value", "")).strip().lower()
    if value.startswith("http://") or value.startswith("https://"):
        try:
            parsed = urlparse(value)
        except ValueError:
            return hosts
        host = str(parsed.netloc or "").strip().lower()
        if host.startswith("www."):
            host = host[4:]
        if host:
            hosts.add(host)
    return hosts


def _extract_owner(entity: Mapping[str, Any]) -> str:
    attributes = entity.get("attributes", {})
    if not isinstance(attributes, Mapping):
        return ""
    return str(attributes.get("owner", "")).strip().lower()


def _extract_identity_names(entity: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    attributes = entity.get("attributes", {})
    if isinstance(attributes, Mapping):
        raw_names = attributes.get("identity_names", [])
        if isinstance(raw_names, Sequence):
            for item in raw_names:
                token = " ".join(part for part in str(item).split() if part).strip().lower()
                if token:
                    names.add(token)

    entity_type = str(entity.get("entity_type", "")).strip().lower()
    if entity_type == "asset" and str(entity.get("value", "")).strip():
        kind = str((attributes or {}).get("asset_kind", "")).strip().lower() if isinstance(attributes, Mapping) else ""
        if kind in {"identity_name", "name"}:
            names.add(str(entity.get("value", "")).strip().lower())
    return names


def _iter_limited_pairs(entity_ids: Sequence[str], *, limit: int) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for left, right in combinations(entity_ids, 2):
        pairs.append((left, right))
        if len(pairs) >= limit:
            break
    return pairs


class CorrelationEngine:
    """Build explainable entity relationships from normalized snapshots."""

    def correlate(self, entities: Sequence[Mapping[str, Any]]) -> list[CorrelationLink]:
        """Generate indexed links with reasons and strength scores."""

        items = [item for item in entities if str(item.get("id", "")).strip()]
        if len(items) <= 1:
            return []

        entities_by_id = {str(item.get("id", "")).strip(): item for item in items}
        link_index: dict[tuple[str, str, str], CorrelationLink] = {}
        pair_counter = 0

        def record(source_id: str, target_id: str, reason: str, strength: float) -> None:
            nonlocal pair_counter
            if source_id == target_id or pair_counter >= _MAX_PAIR_COUNT:
                return
            left, right = sorted((source_id, target_id))
            evidence_reference = _first_evidence_id(entities_by_id.get(left, {})) or _first_evidence_id(
                entities_by_id.get(right, {})
            )
            key = (left, right, reason)
            existing = link_index.get(key)
            bounded_strength = max(0.0, min(1.0, float(strength)))
            if existing and existing.strength_score >= bounded_strength:
                return
            link_index[key] = CorrelationLink(
                source_entity_id=left,
                target_entity_id=right,
                reason=reason,
                evidence_reference=evidence_reference,
                strength_score=bounded_strength,
            )
            pair_counter += 1

        artifact_rules = (
            ("exact_value_match", 0.9, _MAX_WEAK_ARTIFACT_CLUSTER, lambda row: {str(row.get("value", "")).strip().lower()}),
            ("shared_domain", 0.7, _MAX_WEAK_ARTIFACT_CLUSTER, _extract_domains),
            ("shared_email", 0.8, _MAX_WEAK_ARTIFACT_CLUSTER, _extract_emails),
            ("shared_phone", 0.76, _MAX_WEAK_ARTIFACT_CLUSTER, _extract_phones),
            ("shared_owner", 0.66, _MAX_SOURCE_CLUSTER, lambda row: {_extract_owner(row)} if _extract_owner(row) else set()),
            ("shared_identity_name", 0.61, _MAX_SOURCE_CLUSTER, _extract_identity_names),
            ("shared_link_domain", 0.58, _MAX_WEAK_ARTIFACT_CLUSTER, _extract_link_domains),
            ("shared_mention", 0.48, _MAX_WEAK_ARTIFACT_CLUSTER, _extract_mentions),
        )

        for reason, strength, max_cluster, extractor in artifact_rules:
            buckets: dict[str, list[str]] = defaultdict(list)
            for row in items:
                entity_id = str(row.get("id", "")).strip()
                if not entity_id:
                    continue
                artifacts = extractor(row)
                for artifact in artifacts:
                    token = str(artifact).strip().lower()
                    if not token:
                        continue
                    buckets[token].append(entity_id)

            for _, entity_ids in buckets.items():
                deduped_ids = sorted(set(entity_ids))
                if len(deduped_ids) < 2:
                    continue
                scoped_ids = deduped_ids[:max_cluster]
                for source_id, target_id in _iter_limited_pairs(scoped_ids, limit=max(1, _MAX_PAIR_COUNT - pair_counter)):
                    record(source_id, target_id, reason, strength)
                    if pair_counter >= _MAX_PAIR_COUNT:
                        break
                if pair_counter >= _MAX_PAIR_COUNT:
                    break
            if pair_counter >= _MAX_PAIR_COUNT:
                break

        source_buckets: dict[str, list[str]] = defaultdict(list)
        for row in items:
            source = str(row.get("source", "")).strip().lower()
            entity_id = str(row.get("id", "")).strip()
            if source and entity_id:
                source_buckets[source].append(entity_id)

        for _, entity_ids in source_buckets.items():
            if len(entity_ids) < 2:
                continue
            scoped_ids = sorted(set(entity_ids))[:_MAX_SOURCE_CLUSTER]
            for source_id, target_id in _iter_limited_pairs(scoped_ids, limit=max(1, _MAX_PAIR_COUNT - pair_counter)):
                record(source_id, target_id, "shared_source", 0.35)
                if pair_counter >= _MAX_PAIR_COUNT:
                    break
            if pair_counter >= _MAX_PAIR_COUNT:
                break

        return sorted(
            link_index.values(),
            key=lambda item: (item.source_entity_id, item.target_entity_id, item.reason),
        )

    def from_relation_map(
        self,
        relation_map: Mapping[str, Sequence[str]],
        entities_by_id: Mapping[str, Mapping[str, Any]],
    ) -> list[CorrelationLink]:
        """Convert relationship-map payloads into structured links."""

        links: list[CorrelationLink] = []
        for source_id, targets in relation_map.items():
            if not isinstance(targets, Sequence):
                continue
            source_key = str(source_id).strip()
            if not source_key:
                continue
            source_entity = entities_by_id.get(source_key, {})
            evidence_reference = _first_evidence_id(source_entity)
            for target_id in targets:
                target_key = str(target_id).strip()
                if not target_key or target_key == source_key:
                    continue
                left, right = sorted((source_key, target_key))
                links.append(
                    CorrelationLink(
                        source_entity_id=left,
                        target_entity_id=right,
                        reason="existing_relationship_map",
                        evidence_reference=evidence_reference,
                        strength_score=0.5,
                    )
                )
        return links
