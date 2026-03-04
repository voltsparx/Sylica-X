"""Shared CLI workflow presets and prompt keyword maps."""

from __future__ import annotations

from core.collect.scanner import DEFAULT_MAX_CONCURRENCY, DEFAULT_TIMEOUT_SECONDS


PROFILE_PRESETS = {
    "fast": {"timeout": 10, "max_concurrency": 8, "source_profile": "fast", "max_platforms": 25},
    "quick": {"timeout": 12, "max_concurrency": 10, "source_profile": "fast", "max_platforms": 25},
    "balanced": {
        "timeout": DEFAULT_TIMEOUT_SECONDS,
        "max_concurrency": DEFAULT_MAX_CONCURRENCY,
        "source_profile": "balanced",
        "max_platforms": 45,
    },
    "deep": {"timeout": 35, "max_concurrency": 35, "source_profile": "deep", "max_platforms": 60},
    "max": {"timeout": 50, "max_concurrency": 50, "source_profile": "max", "max_platforms": 70},
}

SURFACE_PRESETS = {
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
    "history": {"history", "targets", "recent", "scans", "scanned"},
    "config": {"config", "settings", "options"},
    "wizard": {"wizard", "guide", "guided", "assist"},
    "about": {"about", "info", "details"},
    "explain": {"explain", "understand", "describe"},
    "banner": {"banner"},
    "help": {"help", "-h", "--help"},
    "exit": {"exit", "quit"},
}

