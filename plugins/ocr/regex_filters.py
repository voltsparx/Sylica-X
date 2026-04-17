"""Plugin: structured regex and entity extraction from OCR text."""

from __future__ import annotations

from collections import Counter

from plugins.ocr._shared import resolve_ocr_scan_payload


PLUGIN_SPEC = {
    "id": "ocr_regex_filters",
    "title": "OCR Regex Filters",
    "description": "Extracts emails, URLs, phones, mentions, hashtags, names, and keywords from OCR text.",
    "scopes": ["ocr"],
    "aliases": ["ocr_regex", "ocr_structured", "ocr_signals"],
    "version": "1.0",
}


def run(context: dict) -> dict:
    result = resolve_ocr_scan_payload(context)
    aggregate: Counter[str] = Counter()
    for item in result.items:
        for key, values in item.extracted_signals.items():
            aggregate[key] += len(values)
    signal_total = sum(aggregate.values())
    severity = "MEDIUM" if signal_total else "INFO"
    return {
        "severity": severity,
        "summary": (
            f"Structured OCR extraction produced {signal_total} indicator(s) across "
            f"{len(result.items)} processed image source(s)."
        ),
        "highlights": [
            f"emails={aggregate.get('emails', 0)}",
            f"urls={aggregate.get('urls', 0)}",
            f"phones={aggregate.get('phones', 0)}",
            f"mentions={aggregate.get('mentions', 0)}",
            f"hashtags={aggregate.get('hashtags', 0)}",
            f"names={aggregate.get('names', 0)}",
        ],
        "data": result.as_dict(),
    }
