"""JSON export helpers for orchestrator payloads."""

from __future__ import annotations

from typing import Any


def build_json_payload(
    target: str,
    mode: str,
    fused_data: dict[str, Any],
    advisory: dict[str, Any],
    lifecycle: dict[str, Any],
) -> dict[str, Any]:
    """Build export payload without mutating source dictionaries."""

    fused = dict(fused_data)
    plugin_count = len(fused.get("plugins", [])) if isinstance(fused.get("plugins"), list) else 0
    filter_count = len(fused.get("filters", [])) if isinstance(fused.get("filters"), list) else 0
    issue_count = len(fused.get("issues", [])) if isinstance(fused.get("issues"), list) else 0
    summary = {
        "entity_count": int(fused.get("entity_count", 0) or 0),
        "anomaly_count": len(fused.get("anomalies", [])) if isinstance(fused.get("anomalies"), list) else 0,
        "confidence_score": float(fused.get("confidence_score", 0.0) or 0.0),
        "issue_count": issue_count,
        "plugin_count": plugin_count,
        "filter_count": filter_count,
    }

    return {
        "target": target,
        "mode": mode,
        "summary": summary,
        "fused": fused,
        "advisory": dict(advisory),
        "lifecycle": dict(lifecycle),
    }
