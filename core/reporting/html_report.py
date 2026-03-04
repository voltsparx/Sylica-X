"""Minimal HTML report rendering for orchestrator outputs."""

from __future__ import annotations

import html
from typing import Any


def render_html_report(target: str, mode: str, fused_data: dict[str, Any], advisory: dict[str, Any]) -> str:
    """Render HTML text from fused and advisory outputs."""

    anomalies = fused_data.get("anomalies") if isinstance(fused_data.get("anomalies"), list) else []
    recommendations = advisory.get("next_steps") if isinstance(advisory.get("next_steps"), list) else []
    anomaly_items = "".join(
        f"<li>{html.escape(str(item.get('entity_id', '-')))}: {html.escape(str(item.get('reason', '-')))}</li>"
        for item in anomalies[:20]
        if isinstance(item, dict)
    )
    recommendation_items = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in recommendations[:10]
    )

    return f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Silica-X Orchestrator Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    .card {{ border: 1px solid #ccc; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
  </style>
</head>
<body>
  <h1>Silica-X Orchestrator Report</h1>
  <div class=\"card\"><strong>Target:</strong> {html.escape(target)}</div>
  <div class=\"card\"><strong>Mode:</strong> {html.escape(mode)}</div>
  <div class=\"card\"><strong>Entity Count:</strong> {int(fused_data.get('entity_count', 0))}</div>
  <div class=\"card\"><strong>Confidence:</strong> {float(fused_data.get('confidence_score', 0.0)):.2f}</div>
  <div class=\"card\"><h3>Anomalies</h3><ul>{anomaly_items or '<li>None</li>'}</ul></div>
  <div class=\"card\"><h3>Recommendations</h3><ul>{recommendation_items or '<li>None</li>'}</ul></div>
</body>
</html>
""".strip()
