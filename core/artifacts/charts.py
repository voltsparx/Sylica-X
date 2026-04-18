# ──────────────────────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
# ──────────────────────────────────────────────────────────────────────────────

"""Shared chart generation helpers for portable report outputs."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _status_counts(payload: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in payload.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "unknown")).strip().upper() or "UNKNOWN"
        counts[status] = counts.get(status, 0) + 1
    return counts or {"NO DATA": 1}


def _severity_counts(payload: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in payload.get("issues", []) or []:
        if not isinstance(row, dict):
            continue
        severity = str(row.get("severity", "INFO")).strip().upper() or "INFO"
        counts[severity] = counts.get(severity, 0) + 1
    return counts or {"INFO": 1}


def _confidence_values(payload: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for row in payload.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        raw = _coerce_float(row.get("confidence"))
        if raw is not None:
            values.append(raw)
    return values or [0.0]


def _response_times(payload: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for row in payload.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        raw = _coerce_float(row.get("response_time_ms"))
        if raw is not None:
            values.append(raw)
    return values or [0.0]


def build_chart_images(payload: dict[str, Any]) -> tuple[TemporaryDirectory[str] | None, dict[str, Path]]:
    """Create chart PNGs and return their paths.

    Returns `(temp_dir, paths)` so the caller can keep the temp directory alive
    until report generation is finished.
    """

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None, {}

    temp_dir = TemporaryDirectory()
    root = Path(temp_dir.name)
    charts: dict[str, Path] = {}

    status_counts = _status_counts(payload)
    severity_counts = _severity_counts(payload)
    confidence_values = _confidence_values(payload)
    response_times = _response_times(payload)

    def _save(name: str) -> Path:
        return root / f"{name}.png"

    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    ax.bar(list(status_counts.keys()), list(status_counts.values()), color="#f47c20")
    ax.set_title("Result Status Distribution")
    ax.set_ylabel("Count")
    fig.tight_layout()
    status_path = _save("status-bar")
    fig.savefig(status_path, dpi=160)
    plt.close(fig)
    charts["status_bar"] = status_path

    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    ax.pie(
        list(severity_counts.values()),
        labels=list(severity_counts.keys()),
        autopct="%1.0f%%",
        colors=["#ff6b7d", "#ff8a3d", "#ffb454", "#70b9ff", "#87d6a6"][: len(severity_counts)],
    )
    ax.set_title("Issue Severity Mix")
    fig.tight_layout()
    severity_path = _save("severity-pie")
    fig.savefig(severity_path, dpi=160)
    plt.close(fig)
    charts["severity_pie"] = severity_path

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(range(1, len(response_times) + 1), response_times, color="#ff8a3d", linewidth=2.2)
    ax.set_title("Response Time Trend")
    ax.set_xlabel("Result Index")
    ax.set_ylabel("ms")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    line_path = _save("response-line")
    fig.savefig(line_path, dpi=160)
    plt.close(fig)
    charts["response_line"] = line_path

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.hist(confidence_values, bins=min(max(len(confidence_values), 4), 10), color="#d4651a", edgecolor="#fff4ea")
    ax.set_title("Confidence Histogram")
    ax.set_xlabel("Confidence")
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    hist_path = _save("confidence-hist")
    fig.savefig(hist_path, dpi=160)
    plt.close(fig)
    charts["confidence_hist"] = hist_path

    return temp_dir, charts
