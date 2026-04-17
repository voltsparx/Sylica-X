"""Plugin: OCR extraction and text recovery from image sources."""

from __future__ import annotations

from plugins.ocr._shared import resolve_ocr_scan_payload


PLUGIN_SPEC = {
    "id": "ocr_extractor",
    "title": "OCR Extractor",
    "description": "Runs OCR extraction across local or remote image sources and preserves raw recovered text.",
    "scopes": ["ocr"],
    "aliases": ["ocr", "image_ocr", "text_scan"],
    "version": "1.0",
}


def run(context: dict) -> dict:
    result = resolve_ocr_scan_payload(context)
    summary = result.summary
    severity = "MEDIUM" if summary.ocr_hits else "INFO"
    return {
        "severity": severity,
        "summary": (
            f"OCR extracted text from {summary.ocr_hits} of {summary.processed_count} processed image source(s) "
            f"across {summary.image_count} requested input(s)."
        ),
        "highlights": [
            f"images={summary.image_count}",
            f"processed={summary.processed_count}",
            f"failed={summary.failed_count}",
            f"ocr_hits={summary.ocr_hits}",
        ],
        "data": result.as_dict(),
    }
