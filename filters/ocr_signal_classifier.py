"""Filter: prioritize OCR scan batches that expose structured intelligence."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "ocr_signal_classifier",
    "title": "OCR Signal Classifier",
    "description": "Classifies OCR scan output by structured-signal density and extraction confidence.",
    "scopes": ["ocr"],
    "aliases": ["ocr_classifier", "ocr_triage"],
    "version": "1.0",
}


def run(context: dict) -> dict:
    payload = context.get("ocr_scan")
    if not isinstance(payload, dict):
        payload = {}
        for item in (context.get("plugins", []) or []):
            if not isinstance(item, dict):
                continue
            data = item.get("data")
            if isinstance(data, dict) and data.get("summary") and data.get("items") is not None:
                payload = data
                break

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    signal_totals = summary.get("signal_totals") if isinstance(summary.get("signal_totals"), dict) else {}
    processed = int(summary.get("processed_count") or 0)
    ocr_hits = int(summary.get("ocr_hits") or 0)
    signal_score = sum(int(value or 0) for value in signal_totals.values())

    if signal_score >= 6 or ocr_hits >= 2:
        severity = "MEDIUM"
        band = "dense_signal_batch"
    elif signal_score >= 1 or ocr_hits >= 1:
        severity = "LOW"
        band = "light_signal_batch"
    else:
        severity = "INFO"
        band = "minimal_signal_batch"

    return {
        "severity": severity,
        "summary": (
            f"OCR filter classified the batch as {band} using {signal_score} extracted indicator(s) "
            f"across {processed} processed image source(s)."
        ),
        "highlights": [
            f"classification={band}",
            f"processed={processed}",
            f"ocr_hits={ocr_hits}",
            f"signal_score={signal_score}",
        ],
        "data": {
            "classification": band,
            "processed_count": processed,
            "ocr_hits": ocr_hits,
            "signal_score": signal_score,
            "signal_totals": {str(key): int(value or 0) for key, value in signal_totals.items()},
        },
    }
