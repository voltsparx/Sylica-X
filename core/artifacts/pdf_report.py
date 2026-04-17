# ──────────────────────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
# ──────────────────────────────────────────────────────────────────────────────

"""Portable PDF report generation for Silica-X payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.artifacts.charts import build_chart_images


def _safe_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def generate_pdf_report(path: Path, payload: dict[str, Any]) -> str:
    """Write a PDF case report for a full payload."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("reportlab is required for PDF report output.") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    story: list[Any] = []
    story.append(Paragraph("Silica-X Reporter", styles["Title"]))
    story.append(
        Paragraph(
            f"Target: {payload.get('target', '-')}<br/>"
            f"Mode: {(payload.get('metadata') or {}).get('mode', '-')}<br/>"
            f"Generated: {(payload.get('metadata') or {}).get('generated_at_utc', '-')}",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.18 * inch))
    story.append(Paragraph("Reporter Brief", styles["Heading2"]))
    story.append(Paragraph(str(payload.get("narrative") or "No Reporter Brief was generated."), styles["BodyText"]))
    story.append(Spacer(1, 0.16 * inch))

    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    summary_rows = [["Metric", "Value"], *[[str(key), str(value)] for key, value in summary.items()]]
    summary_table = Table(summary_rows, repeatRows=1)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f47c20")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#8a4a1f")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fff3ea")),
            ]
        )
    )
    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(summary_table)
    story.append(Spacer(1, 0.18 * inch))

    chart_dir, charts = build_chart_images(payload)
    try:
        if charts:
            story.append(Paragraph("Visuals", styles["Heading2"]))
            for key in ("status_bar", "severity_pie", "response_line", "confidence_hist"):
                chart_path = charts.get(key)
                if chart_path is None:
                    continue
                story.append(Image(str(chart_path), width=6.2 * inch, height=3.2 * inch))
                story.append(Spacer(1, 0.12 * inch))

        def _append_section(title: str, rows: list[dict[str, Any]], render: callable, limit: int) -> None:
            story.append(Paragraph(title, styles["Heading2"]))
            if not rows:
                story.append(Paragraph("No entries recorded.", styles["BodyText"]))
                return
            for row in rows[:limit]:
                story.append(Paragraph(render(row), styles["BodyText"]))
                story.append(Spacer(1, 0.05 * inch))

        _append_section(
            "Results",
            _safe_rows(payload.get("results")),
            lambda row: (
                f"{row.get('platform', 'platform')} | status={row.get('status', '-')} | "
                f"confidence={row.get('confidence', '-')} | url={row.get('url', '-')}"
            ),
            45,
        )
        _append_section(
            "Vulnerabilities",
            _safe_rows(payload.get("issues")),
            lambda row: (
                f"[{row.get('severity', 'INFO')}] {row.get('title', 'Issue')} | "
                f"scope={row.get('scope', '-')} | evidence={row.get('evidence', '-')}"
            ),
            40,
        )
        _append_section(
            "Plugin Intelligence",
            _safe_rows(payload.get("plugins")),
            lambda row: (
                f"{row.get('title', row.get('id', 'plugin'))} | "
                f"severity={row.get('severity', 'INFO')} | summary={row.get('summary', '-')}"
            ),
            30,
        )
        _append_section(
            "Filter Intelligence",
            _safe_rows(payload.get("filters")),
            lambda row: (
                f"{row.get('title', row.get('id', 'filter'))} | "
                f"severity={row.get('severity', 'INFO')} | summary={row.get('summary', '-')}"
            ),
            30,
        )
    finally:
        if chart_dir is not None:
            chart_dir.cleanup()

    document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    document.build(story)
    return str(path)
