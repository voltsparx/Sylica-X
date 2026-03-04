"""CLI view rendering for fused orchestration payloads."""

from __future__ import annotations

from typing import Any

from core.interface.symbols import symbol


def render_cli_summary(fused_data: dict[str, Any], advisory: dict[str, Any]) -> str:
    """Render a concise plain-text summary for terminal output."""

    entity_count = int(fused_data.get("entity_count", 0))
    confidence = float(fused_data.get("confidence_score", 0.0))
    anomaly_count = len(fused_data.get("anomalies", [])) if isinstance(fused_data.get("anomalies"), list) else 0
    intelligence_bundle = fused_data.get("intelligence_bundle", {})
    if not isinstance(intelligence_bundle, dict):
        intelligence_bundle = {}
    facets = intelligence_bundle.get("entity_facets", {}) if isinstance(intelligence_bundle.get("entity_facets"), dict) else {}
    risk_summary = intelligence_bundle.get("risk_summary", {}) if isinstance(intelligence_bundle.get("risk_summary"), dict) else {}
    confidence_distribution = (
        intelligence_bundle.get("confidence_distribution", {})
        if isinstance(intelligence_bundle.get("confidence_distribution"), dict)
        else {}
    )
    plugin_rows = fused_data.get("plugins", []) if isinstance(fused_data.get("plugins"), list) else []
    filter_rows = fused_data.get("filters", []) if isinstance(fused_data.get("filters"), list) else []
    issue_rows = fused_data.get("issues", []) if isinstance(fused_data.get("issues"), list) else []

    lines = [
        f"{symbol('major')} Silica-X Orchestrator Summary",
        f"{symbol('bullet')} entities={entity_count}",
        f"{symbol('bullet')} confidence={confidence:.2f}",
        f"{symbol('bullet')} anomalies={anomaly_count}",
        f"{symbol('bullet')} issues={len(issue_rows)} plugins={len(plugin_rows)} filters={len(filter_rows)}",
    ]
    if intelligence_bundle:
        lines.append(f"{symbol('warn')} risk_summary={risk_summary}")
        lines.append(
            f"{symbol('bullet')} confidence_distribution="
            f"high:{confidence_distribution.get('high', 0)} "
            f"medium:{confidence_distribution.get('medium', 0)} "
            f"low:{confidence_distribution.get('low', 0)}"
        )
        lines.append(f"{symbol('bullet')} emails={', '.join((facets.get('emails', []) or [])[:6]) or '-'}")
        lines.append(f"{symbol('bullet')} phones={', '.join((facets.get('phones', []) or [])[:6]) or '-'}")
        lines.append(f"{symbol('bullet')} names={', '.join((facets.get('names', []) or [])[:6]) or '-'}")

    next_steps_raw = advisory.get("next_steps")
    next_steps = next_steps_raw if isinstance(next_steps_raw, list) else []
    for step in next_steps[:3]:
        lines.append(f"{symbol('action')} next: {step}")
    guidance_raw = intelligence_bundle.get("execution_guidance")
    guidance = guidance_raw if isinstance(guidance_raw, dict) else {}
    actions_raw = guidance.get("actions")
    actions = actions_raw if isinstance(actions_raw, list) else []
    for action in actions[:3]:
        if not isinstance(action, dict):
            continue
        lines.append(f"{symbol('tip')} guide: [{action.get('priority', 'P3')}] {action.get('title', 'Action')}")
    return "\n".join(lines)
