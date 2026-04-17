# ──────────────────────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
# ──────────────────────────────────────────────────────────────────────────────

"""Portable DOCX report generation for Silica-X payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.artifacts.charts import build_chart_images


def _safe_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def generate_docx_report(path: Path, payload: dict[str, Any]) -> str:
    """Write a DOCX case report for a full payload."""

    try:
        from docx import Document
        from docx.shared import Inches, Pt
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("python-docx is required for DOCX report output.") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    document.core_properties.title = f"Silica-X Reporter - {payload.get('target', 'target')}"
    document.add_heading("Silica-X Reporter", 0)
    document.add_paragraph(
        f"Target: {payload.get('target', '-')}\n"
        f"Mode: {(payload.get('metadata') or {}).get('mode', '-')}\n"
        f"Generated: {(payload.get('metadata') or {}).get('generated_at_utc', '-')}"
    )

    brief = str(payload.get("narrative") or "No Reporter Brief was generated.")
    p = document.add_paragraph()
    run = p.add_run("Reporter Brief\n")
    run.bold = True
    run.font.size = Pt(12)
    p.add_run(brief)

    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    document.add_heading("Summary", level=1)
    for key, value in summary.items():
        document.add_paragraph(f"{key}: {value}", style="List Bullet")

    chart_dir, charts = build_chart_images(payload)
    try:
        if charts:
            document.add_heading("Visuals", level=1)
            for title, key in (
                ("Result Status Distribution", "status_bar"),
                ("Issue Severity Mix", "severity_pie"),
                ("Response Time Trend", "response_line"),
                ("Confidence Histogram", "confidence_hist"),
            ):
                chart_path = charts.get(key)
                if chart_path is None:
                    continue
                document.add_paragraph(title)
                document.add_picture(str(chart_path), width=Inches(6.3))

        document.add_heading("Results", level=1)
        for row in _safe_rows(payload.get("results"))[:40]:
            document.add_paragraph(
                f"{row.get('platform', 'platform')} | status={row.get('status', '-')} | "
                f"confidence={row.get('confidence', '-')} | url={row.get('url', '-')}",
                style="List Bullet",
            )

        document.add_heading("Vulnerabilities", level=1)
        issues = _safe_rows(payload.get("issues"))
        if not issues:
            document.add_paragraph("No exposure findings were reported.")
        for row in issues[:40]:
            document.add_paragraph(
                f"[{row.get('severity', 'INFO')}] {row.get('title', 'Issue')} | "
                f"scope={row.get('scope', '-')} | evidence={row.get('evidence', '-')}",
                style="List Bullet",
            )

        document.add_heading("Plugin Intelligence", level=1)
        plugins = _safe_rows(payload.get("plugins"))
        if not plugins:
            document.add_paragraph("No plugin outputs were recorded.")
        for row in plugins[:30]:
            document.add_paragraph(
                f"{row.get('title', row.get('id', 'plugin'))} | "
                f"severity={row.get('severity', 'INFO')} | summary={row.get('summary', '-')}",
                style="List Bullet",
            )

        document.add_heading("Filter Intelligence", level=1)
        filters = _safe_rows(payload.get("filters"))
        if not filters:
            document.add_paragraph("No filter outputs were recorded.")
        for row in filters[:30]:
            document.add_paragraph(
                f"{row.get('title', row.get('id', 'filter'))} | "
                f"severity={row.get('severity', 'INFO')} | summary={row.get('summary', '-')}",
                style="List Bullet",
            )

        attached_modules = _safe_rows(payload.get("attached_modules"))
        if attached_modules:
            document.add_heading("Attached Modules", level=1)
            for row in attached_modules[:24]:
                document.add_paragraph(
                    f"{row.get('id', 'module')} | kind={row.get('kind', '-')} | "
                    f"power={row.get('power_score', 0)} | capabilities={', '.join(row.get('capabilities', [])[:5])}",
                    style="List Bullet",
                )
    finally:
        if chart_dir is not None:
            chart_dir.cleanup()

    document.save(path)
    return str(path)
