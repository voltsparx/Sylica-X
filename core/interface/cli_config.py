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

"""Shared CLI workflow presets and prompt keyword maps."""

from __future__ import annotations

from typing import TypedDict

from core.collect.scanner import DEFAULT_MAX_CONCURRENCY, DEFAULT_TIMEOUT_SECONDS
from core.foundation.recon_modes import RECON_MODES


class ProfilePreset(TypedDict):
    timeout: int
    max_concurrency: int
    source_profile: str
    max_platforms: int


class SurfacePreset(TypedDict):
    timeout: int
    max_subdomains: int
    recon_mode: str


class OCRPreset(TypedDict):
    timeout: int
    max_concurrency: int
    preprocess_mode: str
    max_bytes: int
    max_edge: int


PROFILE_PRESETS: dict[str, ProfilePreset] = {
    "safe": {"timeout": 10, "max_concurrency": 8, "source_profile": "fast", "max_platforms": 25},
    "fast": {"timeout": 10, "max_concurrency": 8, "source_profile": "fast", "max_platforms": 25},
    "quick": {"timeout": 12, "max_concurrency": 10, "source_profile": "fast", "max_platforms": 25},
    "balanced": {
        "timeout": DEFAULT_TIMEOUT_SECONDS,
        "max_concurrency": DEFAULT_MAX_CONCURRENCY,
        "source_profile": "balanced",
        "max_platforms": 45,
    },
    "deep": {"timeout": 35, "max_concurrency": 35, "source_profile": "deep", "max_platforms": 60},
    "aggressive": {"timeout": 50, "max_concurrency": 50, "source_profile": "max", "max_platforms": 70},
    "max": {"timeout": 50, "max_concurrency": 50, "source_profile": "max", "max_platforms": 70},
}

SURFACE_PRESETS: dict[str, SurfacePreset] = {
    "quick": {"timeout": 10, "max_subdomains": 60, "recon_mode": "passive"},
    "balanced": {"timeout": 20, "max_subdomains": 250, "recon_mode": "hybrid"},
    "deep": {"timeout": 30, "max_subdomains": 700, "recon_mode": "hybrid"},
    "max": {"timeout": 40, "max_subdomains": 1200, "recon_mode": "hybrid"},
}

OCR_PRESETS: dict[str, OCRPreset] = {
    "quick": {"timeout": 12, "max_concurrency": 2, "preprocess_mode": "light", "max_bytes": 8_000_000, "max_edge": 1600},
    "balanced": {"timeout": 20, "max_concurrency": 4, "preprocess_mode": "balanced", "max_bytes": 15_000_000, "max_edge": 2200},
    "deep": {"timeout": 35, "max_concurrency": 6, "preprocess_mode": "aggressive", "max_bytes": 25_000_000, "max_edge": 2800},
    "max": {"timeout": 45, "max_concurrency": 8, "preprocess_mode": "aggressive", "max_bytes": 32_000_000, "max_edge": 3200},
}

SURFACE_RECON_MODES: tuple[str, ...] = RECON_MODES

EXTENSION_CONTROL_MODES = ("auto", "manual", "hybrid")

PROMPT_KEYWORDS = {
    "profile": {"profile", "scan", "social", "persona", "identity", "username", "handle", "account"},
    "surface": {"surface", "domain", "asset", "infra", "recon", "footprint"},
    "fusion": {"fusion", "full", "combo", "allscan", "stack"},
    "ocr": {"ocr", "ocr-scan", "image-scan", "imageocr", "ocrimage"},
    "orchestrate": {"orchestrate", "orch", "pipeline", "orchestration"},
    "surface-kit": {"surface-kit", "kit", "recipes"},
    "frameworks": {"frameworks", "framework", "temp", "sources"},
    "anonymity": {"anonymity", "anon", "privacy", "routing", "tor"},
    "live": {"live", "dashboard", "watch", "monitor"},
    "keywords": {"keywords", "keyword", "verbs", "commands", "lexicon"},
    "plugins": {"plugins", "plugin", "addons", "extensions"},
    "filters": {"filters", "filter", "sanitize", "pii", "redact"},
    "modules": {"modules", "module-catalog", "catalog", "source-intel"},
    "templates": {"templates", "template", "info-templates", "info-template", "blueprints", "playbooks"},
    "quicktest": {"quicktest", "qtest", "smoke", "smoketest", "demo"},
    "history": {"history", "targets", "recent", "scans", "scanned"},
    "config": {"config", "settings", "options"},
    "doctor": {"doctor", "diag", "diagnostics", "health"},
    "wizard": {"wizard", "guide", "guided", "assist"},
    "about": {"about", "info", "details"},
    "explain": {"explain", "understand", "describe"},
    "banner": {"banner"},
    "help": {"help", "-h", "--help"},
    "exit": {"exit", "quit"},
}
