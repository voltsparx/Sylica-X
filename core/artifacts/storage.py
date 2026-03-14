# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Silica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Silica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Silica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

"""Output storage path utilities for Silica-X."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from core.foundation.output_config import OutputConfigError, get_output_settings


def output_root() -> Path:
    return get_output_settings().output_root


def json_dir() -> Path:
    return output_root() / "json"


def html_dir() -> Path:
    return output_root() / "html"


def cli_dir() -> Path:
    return output_root() / "cli"


def csv_dir() -> Path:
    return output_root() / "csv"


def log_dir() -> Path:
    return output_root() / "logs"


def sanitize_target(target: str) -> str:
    value = (target or "").strip()
    if not value:
        return "target"
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    normalized = normalized.strip("._")
    return normalized or "target"


def ensure_output_tree(types: Iterable[str] | None = None) -> None:
    settings = get_output_settings()
    selected = {item.strip().lower() for item in (types or settings.types) if str(item).strip()}
    root = output_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        log_dir().mkdir(parents=True, exist_ok=True)
        if "json" in selected:
            json_dir().mkdir(parents=True, exist_ok=True)
        if "html" in selected:
            html_dir().mkdir(parents=True, exist_ok=True)
        if "cli" in selected:
            cli_dir().mkdir(parents=True, exist_ok=True)
        if "csv" in selected:
            csv_dir().mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputConfigError(f"Unable to create output directories under {root}: {exc}") from exc


def _output_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def build_output_basename(target: str, stamp: str | None = None) -> str:
    stamp_value = stamp or _output_stamp()
    return f"{sanitize_target(target)}-info-{stamp_value}"


def data_target_dir(target: str) -> Path:
    return json_dir()


def results_json_path(target: str, *, stamp: str | None = None) -> Path:
    return json_dir() / f"{build_output_basename(target, stamp)}.json"


def latest_results_json_path(target: str) -> Path | None:
    try:
        ensure_output_tree(types={"json"})
    except OutputConfigError:
        return None
    target_key = sanitize_target(target)
    candidates = sorted(
        json_dir().glob(f"{target_key}-info-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def legacy_results_json_path(target: str) -> Path:
    return output_root() / sanitize_target(target) / "results.json"


def html_report_path(target: str, *, stamp: str | None = None) -> Path:
    return html_dir() / f"{build_output_basename(target, stamp)}.html"


def cli_report_path(target: str, *, stamp: str | None = None) -> Path:
    return cli_dir() / f"{build_output_basename(target, stamp)}.txt"


def csv_report_path(target: str, *, stamp: str | None = None) -> Path:
    return csv_dir() / f"{build_output_basename(target, stamp)}.csv"


def run_log_path(target: str, *, stamp: str | None = None) -> Path:
    return log_dir() / f"{build_output_basename(target, stamp)}.log"


def framework_log_path() -> Path:
    return log_dir() / "framework.log.txt"


@dataclass(frozen=True)
class HistoryRow:
    target: str
    path: str
    modified_at: str
    source: str = "unknown"


def _read_data_target_label(file_path: Path, fallback: str) -> str:
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    target_value = str(payload.get("target") or fallback).strip()
    return target_value or fallback


def _target_from_filename(file_path: Path) -> str:
    name = file_path.stem
    if "-info-" in name:
        return name.split("-info-", maxsplit=1)[0]
    return name


def list_targets(limit: int = 50) -> list[HistoryRow]:
    try:
        ensure_output_tree(types={"json", "html"})
    except OutputConfigError:
        return []
    cap = max(1, int(limit))
    collected: list[tuple[float, HistoryRow]] = []
    seen_keys: set[str] = set()

    for file_path in sorted(json_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        key = sanitize_target(_target_from_filename(file_path))
        stamp = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        target_label = _read_data_target_label(file_path, key)
        collected.append(
            (
                file_path.stat().st_mtime,
                HistoryRow(
                    target=target_label,
                    path=str(file_path),
                    modified_at=stamp,
                    source="data",
                ),
            )
        )
        seen_keys.add(key)

    for file_path in sorted(html_dir().glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        key = sanitize_target(_target_from_filename(file_path))
        if key in seen_keys:
            continue
        stamp = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        collected.append(
            (
                file_path.stat().st_mtime,
                HistoryRow(
                    target=file_path.stem,
                    path=str(file_path),
                    modified_at=stamp,
                    source="html",
                ),
            )
        )

    collected.sort(key=lambda row: row[0], reverse=True)
    return [row for _, row in collected[:cap]]


def list_targets_from_html(limit: int = 50) -> list[HistoryRow]:
    try:
        ensure_output_tree(types={"html"})
    except OutputConfigError:
        return []
    rows: list[HistoryRow] = []
    for file_path in sorted(html_dir().glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        stamp = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        rows.append(
            HistoryRow(
                target=_target_from_filename(file_path),
                path=str(file_path),
                modified_at=stamp,
                source="html",
            )
        )
        if len(rows) >= max(1, int(limit)):
            break
    return rows
