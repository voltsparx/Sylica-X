# ------------------------------------------------------------------------------
# SPDX-License-Identifier: Proprietary
# ------------------------------------------------------------------------------

"""Portable PDF report generation for Silica-X payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.artifacts.charts import build_chart_images


def _safe_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _table_from_rows(
    rows: list[list[str]],
    *,
    colors: Any,
    Table: Any,
    TableStyle: Any,
) -> Any:
    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f47c20")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#8a4a1f")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fff4eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def generate_pdf_report(path: Path, payload: dict[str, Any]) -> str:
    """Write a rich PDF case report for a full payload."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("reportlab is required for PDF report output.") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReporterMeta", parent=styles["BodyText"], textColor=colors.HexColor("#7c3f18")))
    styles["Title"].textColor = colors.HexColor("#d4651a")
    styles["Heading2"].textColor = colors.HexColor("#b45519")

    story: list[Any] = []
    story.append(Paragraph("Silica-X Reporter", styles["Title"]))
    story.append(
        Paragraph(
            f"Target: {payload.get('target', '-')}<br/>"
            f"Mode: {(payload.get('metadata') or {}).get('mode', '-')}<br/>"
            f"Generated: {(payload.get('metadata') or {}).get('generated_at_utc', '-')}",
            styles["ReporterMeta"],
        )
    )
    story.append(Spacer(1, 0.16 * inch))

    story.append(Paragraph("Reporter Brief", styles["Heading2"]))
    story.append(Paragraph(str(payload.get("narrative") or "No Reporter Brief was generated."), styles["BodyText"]))
    story.append(Spacer(1, 0.16 * inch))

    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    if summary:
        summary_rows = [["Metric", "Value"], *[[str(key), str(value)] for key, value in summary.items()]]
        story.append(Paragraph("Overview", styles["Heading2"]))
        story.append(_table_from_rows(summary_rows, colors=colors, Table=Table, TableStyle=TableStyle))
        story.append(Spacer(1, 0.18 * inch))

    chart_dir, charts = build_chart_images(payload)
    document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=34, leftMargin=34, topMargin=34, bottomMargin=34)
    try:
        if charts:
            story.append(Paragraph("Visual Intelligence", styles["Heading2"]))
            for key in ("status_bar", "severity_pie", "response_line", "confidence_hist"):
                chart_path = charts.get(key)
                if chart_path is None:
                    continue
                story.append(Image(str(chart_path), width=6.2 * inch, height=3.2 * inch))
                story.append(Spacer(1, 0.12 * inch))

        selected_plugins = payload.get("selected_plugins", []) if isinstance(payload.get("selected_plugins"), list) else []
        selected_filters = payload.get("selected_filters", []) if isinstance(payload.get("selected_filters"), list) else []
        attached_modules = _safe_rows(payload.get("attached_modules"))
        if selected_plugins or selected_filters or attached_modules:
            story.append(Paragraph("Attachables", styles["Heading2"]))
            if selected_plugins:
                story.append(Paragraph(f"Enabled plugins: {', '.join(str(item) for item in selected_plugins)}", styles["BodyText"]))
            if selected_filters:
                story.append(Paragraph(f"Enabled filters: {', '.join(str(item) for item in selected_filters)}", styles["BodyText"]))
            if attached_modules:
                rows = [["Module", "Kind", "Framework", "Power"]]
                rows.extend(
                    [
                        [
                            str(row.get("id", "module")),
                            str(row.get("kind", "-")),
                            str(row.get("framework", "-")),
                            str(row.get("power_score", 0)),
                        ]
                        for row in attached_modules[:18]
                    ]
                )
                story.append(_table_from_rows(rows, colors=colors, Table=Table, TableStyle=TableStyle))
                story.append(Spacer(1, 0.18 * inch))

        ocr_tooling = payload.get("ocr_tooling", {}) if isinstance(payload.get("ocr_tooling"), dict) else {}
        if ocr_tooling:
            pytesseract_info = ocr_tooling.get("pytesseract", {}) if isinstance(ocr_tooling.get("pytesseract"), dict) else {}
            tooling_rows = [
                ["Tool", "Available", "Details"],
                ["Preferred engine", "yes", str(ocr_tooling.get("preferred_engine", "none"))],
                ["Pillow", str(bool((ocr_tooling.get("pillow") or {}).get("available"))).lower(), "image preprocessing/runtime"],
                ["EasyOCR", str(bool((ocr_tooling.get("easyocr") or {}).get("available"))).lower(), "neural OCR backend"],
                [
                    "PyTesseract",
                    str(bool(pytesseract_info.get("available"))).lower(),
                    f"binary_found={bool(pytesseract_info.get('tesseract_binary_found'))} path={pytesseract_info.get('tesseract_binary', '-') or '-'}",
                ],
            ]
            story.append(Paragraph("OCR Tooling", styles["Heading2"]))
            story.append(_table_from_rows(tooling_rows, colors=colors, Table=Table, TableStyle=TableStyle))
            story.append(Spacer(1, 0.18 * inch))

        def _append_section(title: str, rows: list[list[str]]) -> None:
            story.append(Paragraph(title, styles["Heading2"]))
            if len(rows) == 1:
                story.append(Paragraph("No entries recorded.", styles["BodyText"]))
                story.append(Spacer(1, 0.12 * inch))
                return
            story.append(_table_from_rows(rows, colors=colors, Table=Table, TableStyle=TableStyle))
            story.append(Spacer(1, 0.18 * inch))

        result_rows = [["Platform", "Status", "Confidence", "Response ms", "URL"]]
        result_rows.extend(
            [
                [
                    str(row.get("platform", "platform")),
                    str(row.get("status", "-")),
                    str(row.get("confidence", "-")),
                    str(row.get("response_time_ms", "-")),
                    str(row.get("url", "-")),
                ]
                for row in _safe_rows(payload.get("results"))[:24]
            ]
        )
        _append_section("Results", result_rows)

        issue_rows = [["Severity", "Title", "Scope", "Evidence"]]
        issue_rows.extend(
            [
                [
                    str(row.get("severity", "INFO")),
                    str(row.get("title", "Issue")),
                    str(row.get("scope", "-")),
                    str(row.get("evidence", "-"))[:120],
                ]
                for row in _safe_rows(payload.get("issues"))[:24]
            ]
        )
        _append_section("Vulnerabilities", issue_rows)

        plugin_rows = [["Plugin", "Severity", "Summary"]]
        plugin_rows.extend(
            [
                [
                    str(row.get("title", row.get("id", "plugin"))),
                    str(row.get("severity", "INFO")),
                    str(row.get("summary", "-"))[:160],
                ]
                for row in _safe_rows(payload.get("plugins"))[:18]
            ]
        )
        _append_section("Plugin Intelligence", plugin_rows)

        filter_rows = [["Filter", "Severity", "Summary"]]
        filter_rows.extend(
            [
                [
                    str(row.get("title", row.get("id", "filter"))),
                    str(row.get("severity", "INFO")),
                    str(row.get("summary", "-"))[:160],
                ]
                for row in _safe_rows(payload.get("filters"))[:18]
            ]
        )
        _append_section("Filter Intelligence", filter_rows)

        ocr_scan = payload.get("ocr_scan", {}) if isinstance(payload.get("ocr_scan"), dict) else {}
        ocr_items = _safe_rows(ocr_scan.get("items"))
        if ocr_items:
            ocr_rows = [["Source", "Kind", "Engine", "Confidence", "Signals"]]
            ocr_rows.extend(
                [
                    [
                        str(row.get("source", "image")),
                        str(row.get("source_kind", "-")),
                        str(row.get("ocr_engine", "none")),
                        str(row.get("confidence_hint", "-")),
                        ", ".join(
                            f"{key}:{len(value)}"
                            for key, value in (row.get("signals", {}) or {}).items()
                            if isinstance(value, list) and value
                        )
                        or "-",
                    ]
                    for row in ocr_items[:20]
                ]
            )
            _append_section("OCR Scan Highlights", ocr_rows)
        document.build(story)
    finally:
        if chart_dir is not None:
            chart_dir.cleanup()

    return str(path)
