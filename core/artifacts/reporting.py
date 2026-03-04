"""Reporting and visualization helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from core.artifacts.html_report import generate_html
from core.artifacts.storage import ensure_output_tree, sanitize_target


def _fused_target(value: dict[str, Any]) -> str:
    target = value.get("target")
    if isinstance(target, dict):
        username = str(target.get("username") or "").strip()
        domain = str(target.get("domain") or "").strip()
        token = f"{username}_{domain}".strip("_")
        return sanitize_target(token or "fused-target")
    return sanitize_target(str(target or "fused-target"))


@dataclass
class ReportGenerator:
    """High-level reporting entrypoint for fused intelligence payloads."""

    output_dir: str = "output/"

    def _output_path(self) -> Path:
        ensure_output_tree()
        return Path(self.output_dir)

    def generate_html_dashboard(self, fused_data: dict[str, Any]) -> str:
        """Generate HTML dashboard path for fused payload."""

        target = _fused_target(fused_data)
        return generate_html(
            target=target,
            results=list(fused_data.get("results", []) or []),
            correlation=dict(fused_data.get("correlation", {}) or {}),
            issues=list(fused_data.get("issues", []) or []),
            issue_summary=dict(fused_data.get("issue_summary", {}) or {}),
            narrative=str(fused_data.get("narrative") or ""),
            domain_result=fused_data.get("domain_result") if isinstance(fused_data.get("domain_result"), dict) else None,
            mode=str(fused_data.get("mode") or "fusion"),
            plugin_results=list(fused_data.get("plugins", []) or []),
            plugin_errors=list(fused_data.get("plugin_errors", []) or []),
            filter_results=list(fused_data.get("filters", []) or []),
            filter_errors=list(fused_data.get("filter_errors", []) or []),
        )

    def export_pdf_excel(self, fused_data: dict[str, Any], format: str = "pdf") -> str:
        """Export a serialized snapshot for downstream PDF/Excel conversion.

        The framework currently writes structured export payloads with extension
        placeholders (`.pdf`, `.xlsx`) so external tooling can post-process.
        """

        normalized = format.strip().lower()
        if normalized == "excel":
            normalized = "xlsx"
        if normalized not in {"pdf", "xlsx", "json"}:
            raise ValueError("Supported formats: pdf, excel/xlsx, json")

        target = _fused_target(fused_data)
        out_dir = self._output_path() / "data" / target
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"report.{normalized}"

        payload = {
            "target": target,
            "generated_from": "ReportGenerator.export_pdf_excel",
            "format_hint": normalized,
            "data": fused_data,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(out_path)

    def cli_viewer(self, fused_data: dict[str, Any]) -> str:
        """Render compact CLI summary string."""

        target = _fused_target(fused_data)
        confidence = fused_data.get("confidence_score", "-")
        risk_score = (fused_data.get("risk") or {}).get("risk_score", "-")
        anomalies = ", ".join(fused_data.get("anomalies", []) or []) or "none"
        summary = (
            f"Target={target}\n"
            f"Confidence={confidence}\n"
            f"Risk={risk_score}\n"
            f"Anomalies={anomalies}\n"
        )
        return summary

