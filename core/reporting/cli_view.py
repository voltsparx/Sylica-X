"""CLI view rendering for fused orchestration payloads."""

from __future__ import annotations

from typing import Any


def render_cli_summary(fused_data: dict[str, Any], advisory: dict[str, Any]) -> str:
    """Render a concise plain-text summary for terminal output."""

    entity_count = int(fused_data.get("entity_count", 0))
    confidence = float(fused_data.get("confidence_score", 0.0))
    anomaly_count = len(fused_data.get("anomalies", [])) if isinstance(fused_data.get("anomalies"), list) else 0

    lines = [
        "[Silica-X Orchestrator Summary]",
        f"entities={entity_count}",
        f"confidence={confidence:.2f}",
        f"anomalies={anomaly_count}",
    ]

    next_steps = advisory.get("next_steps") if isinstance(advisory.get("next_steps"), list) else []
    for step in next_steps[:3]:
        lines.append(f"next: {step}")
    return "\n".join(lines)
