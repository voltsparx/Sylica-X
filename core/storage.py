"""Output storage path utilities for Silica-X."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


OUTPUT_ROOT = Path("output")
DATA_DIR = OUTPUT_ROOT / "data"
HTML_DIR = OUTPUT_ROOT / "html"
CLI_DIR = OUTPUT_ROOT / "cli"
LOG_DIR = OUTPUT_ROOT / "logs"


def sanitize_target(target: str) -> str:
    value = (target or "").strip()
    if not value:
        return "target"
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    normalized = normalized.strip("._")
    return normalized or "target"


def ensure_output_tree() -> None:
    for path in (OUTPUT_ROOT, DATA_DIR, HTML_DIR, CLI_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def data_target_dir(target: str) -> Path:
    return DATA_DIR / sanitize_target(target)


def results_json_path(target: str) -> Path:
    return data_target_dir(target) / "results.json"


def legacy_results_json_path(target: str) -> Path:
    return OUTPUT_ROOT / sanitize_target(target) / "results.json"


def html_report_path(target: str) -> Path:
    return HTML_DIR / f"{sanitize_target(target)}.html"


def cli_report_path(target: str) -> Path:
    return CLI_DIR / f"{sanitize_target(target)}.txt"


def run_log_path(target: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"{sanitize_target(target)}_{stamp}.txt"


def framework_log_path() -> Path:
    return LOG_DIR / "framework.log.txt"


@dataclass(frozen=True)
class HistoryRow:
    target: str
    path: str
    modified_at: str


def list_targets_from_html(limit: int = 50) -> list[HistoryRow]:
    ensure_output_tree()
    rows: list[HistoryRow] = []
    for file_path in sorted(HTML_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        stamp = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        rows.append(
            HistoryRow(
                target=file_path.stem,
                path=str(file_path),
                modified_at=stamp,
            )
        )
        if len(rows) >= max(1, int(limit)):
            break
    return rows
