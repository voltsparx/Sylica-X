"""Central execution policy definitions for scan modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ExecutionPolicy:
    """Immutable execution policy used by the orchestrator."""

    name: str
    engine_type: str
    max_workers: int
    timeout: int
    retry_count: int
    enabled_capabilities: tuple[str, ...]
    enabled_filters: tuple[str, ...]
    enrichment_depth: int
    correlation_level: int


SCAN_PROFILE_ALIASES: Final[dict[str, str]] = {
    "quick": "fast",
    "fast": "fast",
    "balanced": "balanced",
    "deep": "deep",
    "max": "max",
}


SCAN_PROFILES: Final[dict[str, ExecutionPolicy]] = {
    "fast": ExecutionPolicy(
        name="fast",
        engine_type="async",
        max_workers=8,
        timeout=10,
        retry_count=1,
        enabled_capabilities=("username_lookup",),
        enabled_filters=("duplicate", "confidence"),
        enrichment_depth=1,
        correlation_level=1,
    ),
    "balanced": ExecutionPolicy(
        name="balanced",
        engine_type="hybrid",
        max_workers=20,
        timeout=20,
        retry_count=2,
        enabled_capabilities=("username_lookup", "domain_enumeration"),
        enabled_filters=("duplicate", "confidence", "relevance", "scope"),
        enrichment_depth=2,
        correlation_level=2,
    ),
    "deep": ExecutionPolicy(
        name="deep",
        engine_type="hybrid",
        max_workers=35,
        timeout=35,
        retry_count=3,
        enabled_capabilities=("username_lookup", "domain_enumeration", "correlation"),
        enabled_filters=("duplicate", "confidence", "relevance", "scope", "keyword", "depth", "anomaly"),
        enrichment_depth=3,
        correlation_level=3,
    ),
    "max": ExecutionPolicy(
        name="max",
        engine_type="hybrid",
        max_workers=50,
        timeout=50,
        retry_count=4,
        enabled_capabilities=("username_lookup", "domain_enumeration", "correlation"),
        enabled_filters=("duplicate", "confidence", "relevance", "scope", "keyword", "risk", "depth", "anomaly"),
        enrichment_depth=4,
        correlation_level=4,
    ),
}


def normalize_profile_name(profile_name: str) -> str:
    """Normalize profile aliases to canonical policy names."""

    key = str(profile_name or "").strip().lower()
    return SCAN_PROFILE_ALIASES.get(key, "balanced")


def load_execution_policy(profile_name: str) -> ExecutionPolicy:
    """Return execution policy for a profile, defaulting safely to balanced."""

    normalized = normalize_profile_name(profile_name)
    return SCAN_PROFILES.get(normalized, SCAN_PROFILES["balanced"])
