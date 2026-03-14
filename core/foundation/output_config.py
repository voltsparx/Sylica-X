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

"""Output configuration persistence and resolution."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable


CONFIG_FILENAME = ".silica-x-config"
DEFAULT_OUTPUT_TYPES = ("cli", "html", "csv", "json")
ALLOWED_OUTPUT_TYPES = set(DEFAULT_OUTPUT_TYPES)

_SESSION_BASE_DIR: Path | None = None
_SESSION_TYPES: tuple[str, ...] | None = None


class OutputConfigError(RuntimeError):
    """Raised when output configuration cannot be persisted or resolved."""


@dataclass(frozen=True)
class OutputSettings:
    base_dir: Path
    output_root: Path
    types: tuple[str, ...]
    default_base_dir: Path | None
    current_base_dir: Path | None


def _config_path() -> Path:
    return Path.home() / CONFIG_FILENAME


def _load_config() -> dict:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_config(payload: dict) -> None:
    path = _config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        raise OutputConfigError(f"Unable to write output config at {path}: {exc}") from exc


def tokenize_output_types(raw: Iterable[str] | str | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        text = raw.replace(",", " ").strip().lower()
        return [chunk for chunk in (part.strip() for part in text.split()) if chunk]
    tokens: list[str] = []
    for item in raw:
        tokens.extend(tokenize_output_types(str(item)))
    return tokens


def parse_output_types(raw: Iterable[str] | str | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    tokens = tokenize_output_types(raw)
    if not tokens:
        return DEFAULT_OUTPUT_TYPES, ()
    if any(token in {"all", "*"} for token in tokens):
        return DEFAULT_OUTPUT_TYPES, ()

    ordered: list[str] = []
    seen: set[str] = set()
    unknown: list[str] = []
    for token in tokens:
        if token in ALLOWED_OUTPUT_TYPES:
            if token not in seen:
                seen.add(token)
                ordered.append(token)
        else:
            unknown.append(token)
    return (tuple(ordered), tuple(unknown))


def _normalize_output_types(raw: Iterable[str] | str | None) -> tuple[str, ...]:
    types, unknown = parse_output_types(raw)
    if unknown:
        return DEFAULT_OUTPUT_TYPES
    return types or DEFAULT_OUTPUT_TYPES


def _normalize_base_dir(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Path(text).expanduser().resolve()


def update_output_types(raw: Iterable[str] | str) -> tuple[str, ...]:
    types = _normalize_output_types(raw)
    payload = _load_config()
    output_cfg = payload.setdefault("output", {})
    output_cfg["types"] = list(types)
    _write_config(payload)
    global _SESSION_TYPES
    _SESSION_TYPES = types
    return types


def set_session_output_types(raw: Iterable[str] | str) -> tuple[str, ...]:
    types = _normalize_output_types(raw)
    global _SESSION_TYPES
    _SESSION_TYPES = types
    return types


def update_output_base_dir(value: str | Path | None, *, make_default: bool) -> Path:
    path = _normalize_base_dir(value) or Path.cwd().resolve()
    if path.exists() and not path.is_dir():
        raise OutputConfigError(f"Output base path is not a directory: {path}")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputConfigError(f"Unable to create output base directory {path}: {exc}") from exc
    payload = _load_config()
    output_cfg = payload.setdefault("output", {})
    if make_default:
        output_cfg["default_base_dir"] = str(path)
        output_cfg["current_base_dir"] = str(path)
    else:
        output_cfg["current_base_dir"] = str(path)
    _write_config(payload)
    global _SESSION_BASE_DIR
    _SESSION_BASE_DIR = path
    return path


def set_session_output_base_dir(value: str | Path | None) -> Path:
    path = _normalize_base_dir(value) or Path.cwd().resolve()
    if path.exists() and not path.is_dir():
        raise OutputConfigError(f"Output base path is not a directory: {path}")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputConfigError(f"Unable to create output base directory {path}: {exc}") from exc
    global _SESSION_BASE_DIR
    _SESSION_BASE_DIR = path
    return path


def clear_output_base_dir(*, clear_default: bool = False) -> None:
    payload = _load_config()
    output_cfg = payload.setdefault("output", {})
    output_cfg.pop("current_base_dir", None)
    if clear_default:
        output_cfg.pop("default_base_dir", None)
    _write_config(payload)
    global _SESSION_BASE_DIR
    _SESSION_BASE_DIR = None


def clear_session_output_base_dir() -> None:
    global _SESSION_BASE_DIR
    _SESSION_BASE_DIR = None


def get_session_output_base_dir() -> Path | None:
    return _SESSION_BASE_DIR


def get_output_settings() -> OutputSettings:
    payload = _load_config()
    output_cfg = payload.get("output", {}) if isinstance(payload.get("output"), dict) else {}
    default_base = _normalize_base_dir(output_cfg.get("default_base_dir"))
    current_base = _normalize_base_dir(output_cfg.get("current_base_dir"))
    types = _normalize_output_types(output_cfg.get("types"))

    if _SESSION_TYPES:
        types = _SESSION_TYPES

    base_dir = _SESSION_BASE_DIR or current_base or default_base or Path.cwd().resolve()
    output_root = base_dir / "output"
    return OutputSettings(
        base_dir=base_dir,
        output_root=output_root,
        types=types,
        default_base_dir=default_base,
        current_base_dir=current_base,
    )


def describe_output_settings() -> dict[str, str]:
    settings = get_output_settings()
    default_base = str(settings.default_base_dir) if settings.default_base_dir else "working-dir"
    current_base = str(settings.current_base_dir) if settings.current_base_dir else "working-dir"
    return {
        "output_root": str(settings.output_root),
        "output_types": ",".join(settings.types),
        "default_base_dir": default_base,
        "current_base_dir": current_base,
        "config_path": str(_config_path()),
    }
