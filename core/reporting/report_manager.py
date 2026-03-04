"""Report manager orchestrating all reporting formats."""

from __future__ import annotations

from typing import Any

from core.reporting.graph_exporter import export_graph_json, export_graphml
from core.reporting.html_reporter import render_html_reporter
from core.reporting.json_export import build_json_payload
from core.reporting.json_reporter import render_json_report
from core.reporting.txt_reporter import render_txt_report


class ReportManager:
    """Aggregate reporting generation for text/html/json/graph outputs."""

    def generate(
        self,
        *,
        target: str,
        mode: str,
        fused_data: dict[str, Any],
        advisory: dict[str, Any],
        lifecycle: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate multi-format reporting payload."""

        json_payload = build_json_payload(
            target=target,
            mode=mode,
            fused_data=fused_data,
            advisory=advisory,
            lifecycle=lifecycle,
        )

        txt_report = render_txt_report(fused_data=fused_data, advisory=advisory)
        html_report = render_html_reporter(target=target, mode=mode, fused_data=fused_data, advisory=advisory)
        graph_payload = fused_data.get("graph", {}) if isinstance(fused_data.get("graph"), dict) else {}

        return {
            "target": target,
            "mode": mode,
            "fused": json_payload["fused"],
            "advisory": json_payload["advisory"],
            "lifecycle": json_payload["lifecycle"],
            "cli_summary": txt_report,
            "txt_report": txt_report,
            "html_report": html_report,
            "json_payload": json_payload,
            "json_report": render_json_report(json_payload),
            "graph": graph_payload,
            "graph_json": export_graph_json(graph_payload),
            "graph_graphml": export_graphml(graph_payload),
        }
