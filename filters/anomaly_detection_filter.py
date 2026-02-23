"""Filter: detect unusual identity and naming behavior patterns."""

from __future__ import annotations

import re
from collections import Counter


FILTER_SPEC = {
    "id": "anomaly_detection_filter",
    "title": "Anomaly Detection Filter",
    "description": "Flags inconsistent naming and one-off identity artifacts across discovered accounts.",
    "scopes": ["profile", "fusion"],
    "aliases": ["anomaly", "identity_anomaly", "outlier"],
    "version": "1.0",
}


HANDLE_RE = re.compile(r"^[a-z0-9._-]{2,40}$")


def _extract_handle(url: str) -> str:
    value = str(url or "").strip().rstrip("/")
    if not value:
        return ""
    tail = value.split("/")[-1].lstrip("@").lower()
    if HANDLE_RE.match(tail):
        return tail
    return ""


def _shape(handle: str) -> str:
    value = re.sub(r"[a-z]", "a", handle.lower())
    value = re.sub(r"[0-9]", "9", value)
    return value


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    handles = [_extract_handle(row.get("url", "")) for row in results if row.get("status") == "FOUND"]
    handles = [item for item in handles if item]

    if not handles:
        return {
            "severity": "INFO",
            "summary": "No FOUND handles available for anomaly analysis.",
            "highlights": [],
            "data": {"anomaly_count": 0, "anomalies": []},
        }

    anomalies: list[str] = []
    handle_counter: Counter = Counter(handles)
    shapes: Counter = Counter(_shape(item) for item in handles)
    baseline_handle, baseline_count = handle_counter.most_common(1)[0]

    if len(handle_counter) > 1:
        anomalies.append(f"multiple_handle_variants={len(handle_counter)} (baseline={baseline_handle}:{baseline_count})")

    if len(shapes) > 2:
        anomalies.append(f"inconsistent_naming_shapes={len(shapes)}")

    for handle in sorted(set(handles)):
        digit_ratio = sum(char.isdigit() for char in handle) / max(len(handle), 1)
        if digit_ratio >= 0.4:
            anomalies.append(f"digit_heavy:{handle}")
        if len(handle) >= 24:
            anomalies.append(f"long_handle:{handle}")
        if "__" in handle or "--" in handle or ".." in handle:
            anomalies.append(f"repeating_separator:{handle}")

    severity = "MEDIUM" if len(anomalies) >= 2 else "INFO"
    summary = (
        f"Anomaly scan produced {len(anomalies)} signal(s) across {len(handle_counter)} unique handle variant(s). "
        "Inconsistent naming may indicate secondary or disposable accounts."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": anomalies[:8],
        "data": {
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "handle_frequency": dict(handle_counter),
            "shape_frequency": dict(shapes),
        },
    }
