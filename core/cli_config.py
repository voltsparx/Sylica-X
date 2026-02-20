"""Shared CLI workflow presets and prompt keyword maps."""

from __future__ import annotations

from core.scanner import DEFAULT_MAX_CONCURRENCY, DEFAULT_TIMEOUT_SECONDS


PROFILE_PRESETS = {
    "quick": {"timeout": 12, "max_concurrency": 10},
    "balanced": {"timeout": DEFAULT_TIMEOUT_SECONDS, "max_concurrency": DEFAULT_MAX_CONCURRENCY},
    "deep": {"timeout": 35, "max_concurrency": 35},
}

SURFACE_PRESETS = {
    "quick": {"timeout": 10, "max_subdomains": 60},
    "balanced": {"timeout": 20, "max_subdomains": 250},
    "deep": {"timeout": 30, "max_subdomains": 700},
}

PROMPT_KEYWORDS = {
    "profile": {"profile", "scan", "social", "persona", "identity", "username", "handle", "account"},
    "surface": {"surface", "domain", "asset", "infra", "recon", "footprint"},
    "fusion": {"fusion", "full", "combo", "allscan", "stack"},
    "anonymity": {"anonymity", "anon", "privacy", "routing", "tor"},
    "live": {"live", "dashboard", "watch", "monitor"},
    "keywords": {"keywords", "keyword", "verbs", "commands", "lexicon"},
    "plugins": {"plugins", "plugin", "addons", "extensions", "modules"},
    "filters": {"filters", "filter", "sanitize", "pii", "redact"},
    "history": {"history", "targets", "recent", "scans", "scanned"},
    "config": {"config", "settings", "options"},
    "wizard": {"wizard", "guide", "guided", "assist"},
    "about": {"about", "info", "details"},
    "explain": {"explain", "understand", "describe"},
    "banner": {"banner"},
    "help": {"help", "-h", "--help"},
    "exit": {"exit", "quit"},
}
