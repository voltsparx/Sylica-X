"""Plugin: batch rollup and engine-health analysis for OCR scans."""

from __future__ import annotations

from plugins.ocr._shared import resolve_ocr_scan_payload


PLUGIN_SPEC = {
    "id": "ocr_batch_processor",
    "title": "OCR Batch Processor",
    "description": "Summarizes batch coverage, failures, preprocessing lanes, and engine runtime health for OCR scans.",
    "scopes": ["ocr"],
    "aliases": ["ocr_batch", "ocr_pipeline", "ocr_runtime"],
    "version": "1.0",
}


def run(context: dict) -> dict:
    result = resolve_ocr_scan_payload(context)
    summary = result.summary
    severity = "LOW" if summary.failed_count else "INFO"
    return {
        "severity": severity,
        "summary": (
            f"OCR batch processing completed {summary.processed_count} image source(s) "
            f"with {summary.failed_count} failure(s) and engine telemetry attached."
        ),
        "highlights": [
            f"processed={summary.processed_count}",
            f"failed={summary.failed_count}",
            f"engines={summary.engines}",
            f"languages={summary.languages}",
        ],
        "data": result.as_dict(),
    }
