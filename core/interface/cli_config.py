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


class ProfilePreset(TypedDict):
    timeout: int
    max_concurrency: int
    source_profile: str
    max_platforms: int


class SurfacePreset(TypedDict):
    timeout: int
    max_subdomains: int


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
    "quick": {"timeout": 10, "max_subdomains": 60},
    "balanced": {"timeout": 20, "max_subdomains": 250},
    "deep": {"timeout": 30, "max_subdomains": 700},
}

EXTENSION_CONTROL_MODES = ("auto", "manual", "hybrid")

PROMPT_KEYWORDS = {
    "profile": {"profile", "scan", "social", "persona", "identity", "username", "handle", "account"},
    "surface": {"surface", "domain", "asset", "infra", "recon", "footprint"},
    "fusion": {"fusion", "full", "combo", "allscan", "stack"},
    "orchestrate": {"orchestrate", "orch", "pipeline", "orchestration"},
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
    "wizard": {"wizard", "guide", "guided", "assist"},
    "about": {"about", "info", "details"},
    "explain": {"explain", "understand", "describe"},
    "banner": {"banner"},
    "help": {"help", "-h", "--help"},
    "exit": {"exit", "quit"},
}

