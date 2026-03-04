"""Strategic intelligence helpers for fused orchestration outputs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class StrategicAdvisor:
    """Produce strategic recommendations from fused intelligence payloads."""

    def recommend_next_steps(self, fused_data: dict[str, Any]) -> list[str]:
        """Suggest next analyst actions based on fused output."""

        recommendations: list[str] = []
        confidence = float(fused_data.get("confidence_score", 0.0))
        anomalies = fused_data.get("anomalies") if isinstance(fused_data.get("anomalies"), list) else []
        entity_count = int(fused_data.get("entity_count", 0))
        intelligence_bundle = fused_data.get("intelligence_bundle", {})
        if not isinstance(intelligence_bundle, dict):
            intelligence_bundle = {}
        guidance_raw = intelligence_bundle.get("execution_guidance")
        guidance = guidance_raw if isinstance(guidance_raw, dict) else {}
        actions_raw = guidance.get("actions")
        actions = actions_raw if isinstance(actions_raw, list) else []

        if confidence < 50:
            recommendations.append("Increase scan depth and rerun with balanced or deep profile.")
        if anomalies:
            recommendations.append("Validate anomalies manually before escalation.")
        if entity_count == 0:
            recommendations.append("Broaden target scope or verify input normalization.")
        for action in actions[:3]:
            if not isinstance(action, dict):
                continue
            title = str(action.get("title", "")).strip()
            hint = str(action.get("command_hint", "")).strip()
            if title:
                recommendations.append(f"{title} ({hint})" if hint else title)
        if not recommendations:
            recommendations.append("Export report and proceed with timeline correlation review.")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in recommendations:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def estimate_overall_confidence(self, fused_data: dict[str, Any]) -> float:
        """Return bounded overall confidence score."""

        value = float(fused_data.get("confidence_score", 0.0))
        intelligence_bundle = fused_data.get("intelligence_bundle", {})
        if isinstance(intelligence_bundle, dict):
            distribution = intelligence_bundle.get("confidence_distribution", {})
            if isinstance(distribution, dict):
                high = float(distribution.get("high", 0) or 0)
                medium = float(distribution.get("medium", 0) or 0)
                low = float(distribution.get("low", 0) or 0)
                total = high + medium + low
                if total > 0:
                    blend = ((high * 1.0) + (medium * 0.6) + (low * 0.2)) / total
                    value = max(value, blend * 100.0)
        return max(0.0, min(100.0, value))

    def prioritize_findings(self, fused_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Prioritize anomalies and graph-heavy findings for analyst review."""

        anomalies = fused_data.get("anomalies") if isinstance(fused_data.get("anomalies"), list) else []
        graph = fused_data.get("graph") if isinstance(fused_data.get("graph"), dict) else {}
        edges_raw = graph.get("edges") if isinstance(graph, dict) else []
        edge_count = len(edges_raw) if isinstance(edges_raw, list) else 0
        intelligence_bundle = fused_data.get("intelligence_bundle", {})
        risk_summary_raw = intelligence_bundle.get("risk_summary") if isinstance(intelligence_bundle, dict) else {}
        risk_summary = risk_summary_raw if isinstance(risk_summary_raw, dict) else {}
        critical_count = int(risk_summary.get("CRITICAL", 0) or 0)
        high_count = int(risk_summary.get("HIGH", 0) or 0)

        priorities: list[dict[str, Any]] = []
        if critical_count:
            priorities.append({"priority": "critical", "reason": "critical_risk_entities", "count": critical_count})
        if high_count:
            priorities.append({"priority": "high", "reason": "high_risk_entities", "count": high_count})
        if anomalies:
            priorities.append({"priority": "high", "reason": "anomaly_signals", "count": len(anomalies)})
        if edge_count > 20:
            priorities.append({"priority": "medium", "reason": "dense_relationship_graph", "count": edge_count})
        if not priorities:
            priorities.append({"priority": "low", "reason": "normal_signal_density", "count": 0})
        return priorities

    def summarize_history(self, history: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Summarize historical runs for advisory context."""

        records = list(history)
        if not records:
            return {"runs": 0, "avg_confidence": 0.0}

        confidences = [float(item.get("confidence_score", 0.0)) for item in records]
        average = sum(confidences) / len(confidences)
        return {"runs": len(records), "avg_confidence": round(average, 2)}
