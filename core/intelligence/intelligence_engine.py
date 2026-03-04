"""Structured intelligence pipeline with evidence traceability."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from core.domain import BaseEntity
from core.intelligence.clustering_engine import ClusteringEngine
from core.intelligence.confidence_model import ConfidenceModel
from core.intelligence.correlation_engine import CorrelationEngine, CorrelationLink
from core.intelligence.evidence import Evidence, evidence_from_entity
from core.intelligence.expansion_engine import ExpansionEngine
from core.intelligence.heuristic_rules import HeuristicEngine
from core.intelligence.risk_engine import RiskEngine


def _confidence_bucket(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _normalize_anomaly_map(anomalies: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    mapped: dict[str, list[str]] = {}
    for anomaly in anomalies:
        entity_id = str(anomaly.get("entity_id", "")).strip()
        if not entity_id:
            continue
        reason = str(anomaly.get("reason", "anomaly")).strip().lower()
        mapped.setdefault(entity_id, []).append(reason)
    return mapped


def _normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if len(digits) < 7:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


def _risk_rank(level: str) -> int:
    table = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    return table.get(str(level).upper(), 0)


def _facet_values(row: Mapping[str, Any], kind: str) -> list[str]:
    values: list[str] = []
    value = str(row.get("value", "")).strip()
    entity_type = str(row.get("entity_type", "")).strip().lower()
    attributes = row.get("attributes", {})
    if not isinstance(attributes, Mapping):
        attributes = {}

    contacts = attributes.get("contacts", {})
    if not isinstance(contacts, Mapping):
        contacts = {}

    if kind == "email":
        if entity_type == "email" and "@" in value:
            values.append(value.lower())
        raw_emails = contacts.get("emails", [])
        if isinstance(raw_emails, Sequence):
            for item in raw_emails:
                token = str(item).strip().lower()
                if "@" in token:
                    values.append(token)
    elif kind == "phone":
        if entity_type == "asset":
            token = _normalize_phone(value)
            if token:
                values.append(token)
        raw_phones = contacts.get("phones", [])
        if isinstance(raw_phones, Sequence):
            for item in raw_phones:
                token = _normalize_phone(str(item))
                if token:
                    values.append(token)
    elif kind == "name":
        raw_names = attributes.get("identity_names", [])
        if isinstance(raw_names, Sequence):
            for item in raw_names:
                token = " ".join(str(item).strip().split())
                if token:
                    values.append(token)
        if entity_type == "asset" and str(attributes.get("asset_kind", "")).strip().lower() == "identity_name" and value:
            values.append(value)
    elif kind == "mention":
        raw_mentions = attributes.get("mentions", [])
        if isinstance(raw_mentions, Sequence):
            for item in raw_mentions:
                token = str(item).strip().lstrip("@").lower()
                if token:
                    values.append(token)
    elif kind == "domain":
        if entity_type == "domain" and "." in value:
            values.append(value.lower())
        raw_domain = str(attributes.get("domain", "")).strip().lower()
        if "." in raw_domain:
            values.append(raw_domain)
        raw_parent_domain = str(attributes.get("parent_domain", "")).strip().lower()
        if "." in raw_parent_domain:
            values.append(raw_parent_domain)
        raw_email_domain = str(attributes.get("email_domain", "")).strip().lower()
        if "." in raw_email_domain:
            values.append(raw_email_domain)

    seen: set[str] = set()
    deduped: list[str] = []
    for item in values:
        token = str(item).strip()
        if not token:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(token)
    return deduped


def _collect_entity_facets(snapshots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    facet_tables: dict[str, dict[str, dict[str, Any]]] = {
        "emails": {},
        "phones": {},
        "names": {},
        "mentions": {},
        "domains": {},
    }

    def add_facet(kind: str, token: str, row: Mapping[str, Any], score: float, risk_level: str) -> None:
        table = facet_tables[kind]
        key = token.lower()
        record = table.setdefault(
            key,
            {
                "value": token,
                "score": 0.0,
                "risk_level": risk_level,
                "supporting_entities": set(),
                "sources": set(),
            },
        )
        record["score"] = max(float(record["score"]), float(score))
        if _risk_rank(risk_level) > _risk_rank(str(record.get("risk_level", "LOW"))):
            record["risk_level"] = risk_level
        entity_id = str(row.get("id", "")).strip()
        if entity_id:
            record["supporting_entities"].add(entity_id)
        source = str(row.get("source", "")).strip()
        if source:
            record["sources"].add(source)

    for row in snapshots:
        score = max(0.0, min(1.0, float(row.get("confidence_score", row.get("confidence", 0.0)) or 0.0)))
        risk_level = str(row.get("risk_level", "LOW")).strip().upper() or "LOW"

        for token in _facet_values(row, "email"):
            add_facet("emails", token, row, score, risk_level)
        for token in _facet_values(row, "phone"):
            add_facet("phones", token, row, score, risk_level)
        for token in _facet_values(row, "name"):
            add_facet("names", token, row, score, risk_level)
        for token in _facet_values(row, "mention"):
            add_facet("mentions", token, row, score, risk_level)
        for token in _facet_values(row, "domain"):
            add_facet("domains", token, row, score, risk_level)

    def sorted_values(kind: str, *, limit: int = 120) -> list[str]:
        table = facet_tables[kind]
        rows = sorted(
            table.values(),
            key=lambda item: (
                -float(item["score"]),
                -len(item["supporting_entities"]),
                str(item["value"]).lower(),
            ),
        )
        return [str(item["value"]) for item in rows[:limit]]

    scored_contacts: list[dict[str, Any]] = []
    for kind in ("emails", "phones", "names"):
        for item in facet_tables[kind].values():
            scored_contacts.append(
                {
                    "kind": kind[:-1],
                    "value": item["value"],
                    "score": round(float(item["score"]), 4),
                    "score_percent": int(round(float(item["score"]) * 100)),
                    "risk_level": item["risk_level"],
                    "supporting_entities": len(item["supporting_entities"]),
                    "sources": sorted(item["sources"]),
                }
            )
    scored_contacts.sort(
        key=lambda item: (
            -float(item["score"]),
            -int(item["supporting_entities"]),
            str(item["value"]).lower(),
        )
    )

    return {
        "emails": sorted_values("emails"),
        "phones": sorted_values("phones"),
        "names": sorted_values("names"),
        "contacts": sorted_values("emails") + sorted_values("phones"),
        "mentions": sorted_values("mentions"),
        "domains": sorted_values("domains"),
        "scored_contacts": scored_contacts[:200],
    }


def _summarize_correlation_links(links: Sequence[CorrelationLink]) -> dict[str, Any]:
    if not links:
        return {
            "link_count": 0,
            "reason_breakdown": {},
            "strongest_links": [],
        }

    reason_counter = Counter(link.reason for link in links)
    strongest_rows: list[dict[str, Any]] = [
        {
            "source_entity_id": link.source_entity_id,
            "target_entity_id": link.target_entity_id,
            "reason": link.reason,
            "strength_score": round(float(link.strength_score), 4),
            "evidence_reference": link.evidence_reference,
        }
        for link in links
    ]
    strongest_rows.sort(
        key=lambda item: (
            -float(item.get("strength_score", 0.0) or 0.0),
            str(item.get("reason", "")),
            str(item.get("source_entity_id", "")),
        )
    )
    strongest = strongest_rows[:150]

    return {
        "link_count": len(links),
        "reason_breakdown": dict(sorted(reason_counter.items(), key=lambda item: (-int(item[1]), item[0]))),
        "strongest_links": strongest,
    }


def _build_scored_entities(snapshots: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranked_rows = sorted(
        snapshots,
        key=lambda row: (
            -float(row.get("confidence_score", row.get("confidence", 0.0)) or 0.0),
            -_risk_rank(str(row.get("risk_level", "LOW"))),
            str(row.get("entity_type", "")),
            str(row.get("value", "")),
        ),
    )

    scored: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked_rows[:500], start=1):
        confidence = float(row.get("confidence_score", row.get("confidence", 0.0)) or 0.0)
        scored.append(
            {
                "rank": rank,
                "entity_id": str(row.get("id", "")),
                "entity_type": str(row.get("entity_type", "")),
                "value": str(row.get("value", "")),
                "source": str(row.get("source", "")),
                "confidence_score": round(confidence, 4),
                "confidence_percent": int(round(confidence * 100)),
                "risk_level": str(row.get("risk_level", "LOW")),
                "relationship_count": len(row.get("relationships", []) or []),
                "heuristics": [item.get("rule") for item in (row.get("heuristics", []) or []) if isinstance(item, Mapping)],
                "evidence_count": len(row.get("evidence_ids", []) or []),
            }
        )
    return scored


def _build_execution_guidance(
    *,
    mode_name: str,
    target_name: str,
    risk_summary: Mapping[str, Any],
    confidence_distribution: Mapping[str, int],
    facets: Mapping[str, Any],
    correlation_summary: Mapping[str, Any],
    cluster_count: int,
) -> dict[str, Any]:
    actions: list[dict[str, str]] = []

    critical_count = int(risk_summary.get("CRITICAL", 0) or 0)
    high_count = int(risk_summary.get("HIGH", 0) or 0)
    low_confidence_count = int(confidence_distribution.get("low", 0) or 0)
    link_count = int(correlation_summary.get("link_count", 0) or 0)

    if critical_count or high_count:
        actions.append(
            {
                "priority": "P1",
                "title": "Escalate high-risk entities",
                "rationale": f"{critical_count} critical and {high_count} high-risk entities detected.",
                "command_hint": "review --risk high --risk critical",
            }
        )
    if low_confidence_count:
        actions.append(
            {
                "priority": "P2",
                "title": "Reduce low-confidence noise",
                "rationale": f"{low_confidence_count} entities remain low-confidence.",
                "command_hint": "rerun --profile deep --min-confidence 0.45",
            }
        )
    if facets.get("emails") or facets.get("phones"):
        actions.append(
            {
                "priority": "P2",
                "title": "Pivot on discovered contacts",
                "rationale": "Email/phone artifacts can unlock cross-platform and breach pivots.",
                "command_hint": "pivot --entity email --entity phone",
            }
        )
    if facets.get("names"):
        actions.append(
            {
                "priority": "P3",
                "title": "Validate identity-name candidates",
                "rationale": "Name candidates were extracted and scored from profile evidence.",
                "command_hint": "review --entity identity_name",
            }
        )
    if link_count > 0 and cluster_count > 0:
        actions.append(
            {
                "priority": "P2",
                "title": "Inspect fused relationship clusters",
                "rationale": f"{cluster_count} cluster(s) and {link_count} links identified for correlation review.",
                "command_hint": "graph --clusters --strong-links",
            }
        )

    if not actions:
        actions.append(
            {
                "priority": "P3",
                "title": "Proceed with baseline evidence validation",
                "rationale": "No urgent risk or conflict signals detected.",
                "command_hint": "export --report full",
            }
        )

    learning_track = [
        {
            "phase": "collect",
            "objective": "Capture broad public signals across profile and surface collectors.",
            "why": "Coverage breadth increases the reliability of later fusion scoring.",
        },
        {
            "phase": "normalize",
            "objective": "Standardize entities, contacts, and infrastructure artifacts.",
            "why": "Normalized evidence enables deterministic correlation and deduplication.",
        },
        {
            "phase": "correlate",
            "objective": "Link entities using shared domains, emails, phones, mentions, and names.",
            "why": "Cross-source overlap turns isolated artifacts into explainable intelligence paths.",
        },
        {
            "phase": "assess",
            "objective": "Score confidence and risk with transparent feature-level breakdowns.",
            "why": "Explainable scoring makes analyst decisions auditable and repeatable.",
        },
        {
            "phase": "act",
            "objective": "Apply guided pivots and export operational reports.",
            "why": "Actionable intelligence depends on prioritized next steps and reporting clarity.",
        },
    ]

    return {
        "mode": mode_name,
        "target": target_name or "target",
        "actions": actions,
        "learning_track": learning_track,
    }


class IntelligenceEngine:
    """Run evidence, heuristics, correlation, confidence, risk, and clustering stages."""

    def __init__(self) -> None:
        self._heuristics = HeuristicEngine()
        self._correlation = CorrelationEngine()
        self._confidence_model = ConfidenceModel()
        self._risk_engine = RiskEngine()
        self._clustering = ClusteringEngine()
        self._expansion = ExpansionEngine()

    def analyze(
        self,
        entities: Sequence[BaseEntity],
        *,
        mode: str,
        target: str,
        anomalies: Sequence[Mapping[str, Any]] | None = None,
        relation_map: Mapping[str, Sequence[str]] | None = None,
    ) -> dict[str, Any]:
        """Run full intelligence pipeline and return analysis-ready bundle."""

        started_at = datetime.now(tz=timezone.utc)
        mode_name = str(mode or "balanced").strip().lower()
        target_name = str(target or "").strip()

        snapshots: list[dict[str, Any]] = []
        evidence_rows: list[Evidence] = []
        entities_by_id: dict[str, dict[str, Any]] = {}

        trace_prefix = f"{mode_name}:{target_name or 'target'}"
        for entity in entities:
            evidence = evidence_from_entity(entity, trace_prefix=trace_prefix)
            evidence_rows.append(evidence)

            row = entity.as_dict()
            row["attributes"] = dict(entity.attributes)
            row["evidence_ids"] = [evidence.id]
            row["first_seen"] = entity.timestamp.isoformat()
            row["last_updated"] = entity.timestamp.isoformat()
            row["risk_level"] = "LOW"
            row["confidence_breakdown"] = {}
            row["heuristics"] = []
            snapshots.append(row)
            entities_by_id[row["id"]] = row

        links = self._correlation.correlate(snapshots)
        if relation_map:
            links.extend(self._correlation.from_relation_map(relation_map, entities_by_id))
        links = self._dedupe_links(links)

        links_by_entity: dict[str, list[CorrelationLink]] = defaultdict(list)
        for link in links:
            links_by_entity[link.source_entity_id].append(link)
            links_by_entity[link.target_entity_id].append(link)

        anomaly_map = _normalize_anomaly_map(list(anomalies or []))
        target_domains = self._target_domains(target_name)

        confidence_by_entity: dict[str, float] = {}
        risk_levels: list[str] = []
        bucket_counts = {"low": 0, "medium": 0, "high": 0}

        evidence_by_id = {row.id: row for row in evidence_rows}
        for row in snapshots:
            entity_id = str(row.get("id", "")).strip()
            attached_links = links_by_entity.get(entity_id, [])
            strengths = [float(link.strength_score) for link in attached_links]

            evidence_ids = row.get("evidence_ids", [])
            evidence_reliability = 0.5
            if isinstance(evidence_ids, Sequence) and evidence_ids:
                evidence_row = evidence_by_id.get(str(evidence_ids[0]))
                if evidence_row is not None:
                    evidence_reliability = float(evidence_row.reliability_score)

            heuristic_bonus, applied_heuristics = self._heuristics.evaluate(
                row,
                {
                    "mode": mode_name,
                    "target_domains": target_domains,
                    "evidence_count": len(evidence_ids) if isinstance(evidence_ids, Sequence) else 1,
                },
            )
            anomaly_reasons = anomaly_map.get(entity_id, [])
            contradiction_penalty = 0.1 if anomaly_reasons else 0.0

            score, breakdown = self._confidence_model.score(
                heuristic_bonus=heuristic_bonus,
                correlation_strengths=strengths,
                evidence_reliability=evidence_reliability,
                contradiction_penalty=contradiction_penalty,
                base_score=float(row.get("confidence", 0.3) or 0.3),
            )

            risk_level = self._risk_engine.assess(
                row,
                confidence_score=score,
                anomaly_reasons=anomaly_reasons,
            )

            related_ids = {
                link.target_entity_id if link.source_entity_id == entity_id else link.source_entity_id
                for link in attached_links
            }

            row["confidence"] = round(score, 4)
            row["confidence_score"] = round(score, 4)
            row["confidence_breakdown"] = breakdown
            row["heuristics"] = applied_heuristics
            row["risk_level"] = risk_level
            row["relationships"] = sorted(related_ids)
            confidence_by_entity[entity_id] = score
            risk_levels.append(risk_level)
            bucket_counts[_confidence_bucket(score)] += 1

        snapshots = self._expansion.annotate(
            snapshots,
            target=target_name,
            mode=mode_name,
        )
        clusters = self._clustering.build_clusters(snapshots, links, confidence_by_entity)
        risk_summary = self._risk_engine.summarize(risk_levels)
        entity_facets = _collect_entity_facets(snapshots)
        correlation_summary = _summarize_correlation_links(links)
        scored_entities = _build_scored_entities(snapshots)
        execution_guidance = _build_execution_guidance(
            mode_name=mode_name,
            target_name=target_name,
            risk_summary=risk_summary,
            confidence_distribution=bucket_counts,
            facets=entity_facets,
            correlation_summary=correlation_summary,
            cluster_count=len(clusters),
        )
        finished_at = datetime.now(tz=timezone.utc)

        return {
            "metadata": {
                "scan_mode": mode_name,
                "start_time": started_at.isoformat(),
                "end_time": finished_at.isoformat(),
                "entity_count": len(snapshots),
                "evidence_count": len(evidence_rows),
            },
            "entities": snapshots,
            "scored_entities": scored_entities,
            "entity_facets": entity_facets,
            "evidence": [row.as_dict() for row in evidence_rows],
            "relationships": [link.as_dict() for link in links],
            "correlation_summary": correlation_summary,
            "clusters": clusters,
            "risk_summary": risk_summary,
            "confidence_distribution": bucket_counts,
            "execution_guidance": execution_guidance,
            "analysis_ready": True,
        }

    def _target_domains(self, target: str) -> set[str]:
        values: set[str] = set()
        normalized = str(target or "").strip().lower()
        if not normalized:
            return values
        if "@" in normalized:
            values.add(normalized.split("@", maxsplit=1)[1])
        if "." in normalized:
            values.add(normalized)
        return values

    def _dedupe_links(self, links: Sequence[CorrelationLink]) -> list[CorrelationLink]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[CorrelationLink] = []
        for link in links:
            source, target = sorted((link.source_entity_id, link.target_entity_id))
            key = (source, target, link.reason)
            if key in seen:
                continue
            seen.add(key)
            unique.append(
                CorrelationLink(
                    source_entity_id=source,
                    target_entity_id=target,
                    reason=link.reason,
                    evidence_reference=link.evidence_reference,
                    strength_score=link.strength_score,
                )
            )
        return unique
