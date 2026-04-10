# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Sylica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Sylica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root
#
# This file is part of Sylica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

"""Surface mapping and recon guidance helpers."""

from __future__ import annotations

from typing import Any

from core.foundation.recon_modes import normalize_recon_mode
from core.foundation.surface_wordlists import matched_surface_subdomain_labels


HIGH_PRIORITY_TOKENS = ("admin", "auth", "sso", "vpn", "portal", "api", "gateway", "bastion")
MEDIUM_PRIORITY_TOKENS = ("dev", "test", "stage", "staging", "uat", "legacy", "old", "debug")
ENVIRONMENT_BUCKETS: dict[str, tuple[str, ...]] = {
    "development": ("dev", "stage", "staging", "uat", "test", "qa"),
    "administrative": ("admin", "portal", "manage", "internal"),
    "service": ("api", "auth", "cdn", "edge", "mail", "gateway"),
    "legacy": ("old", "legacy", "backup", "bak", "archive"),
}


def _safe_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip().lower() for item in value if str(item).strip()]


def _safe_int_list(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    results: list[int] = []
    for item in value:
        try:
            results.append(int(item))
        except (TypeError, ValueError):
            continue
    return results


def _bucket_subdomains(subdomains: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {key: [] for key in ENVIRONMENT_BUCKETS}
    buckets["general"] = []
    for subdomain in subdomains:
        matched = False
        for bucket, tokens in ENVIRONMENT_BUCKETS.items():
            if any(token in subdomain for token in tokens):
                buckets[bucket].append(subdomain)
                matched = True
        if not matched:
            buckets["general"].append(subdomain)
    return {key: sorted(set(values)) for key, values in buckets.items()}


def _prioritize_hosts(subdomains: list[str]) -> tuple[list[str], list[str]]:
    high_priority: set[str] = set()
    medium_priority: set[str] = set()
    for host in subdomains:
        if any(token in host for token in HIGH_PRIORITY_TOKENS):
            high_priority.add(host)
            continue
        if any(token in host for token in MEDIUM_PRIORITY_TOKENS):
            medium_priority.add(host)
    return sorted(high_priority), sorted(medium_priority - high_priority)


def _collector_rows(domain_result: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = domain_result.get("collector_status", {})
    if not isinstance(rows, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for key, value in rows.items():
        if not isinstance(value, dict):
            continue
        normalized[str(key)] = {
            "lane": str(value.get("lane", "")),
            "status": str(value.get("status", "")),
            "detail": str(value.get("detail", "")),
        }
    return normalized


def build_surface_map(domain_result: dict[str, Any]) -> dict[str, Any]:
    """Build an attack-surface summary designed for analyst triage."""

    target = str(domain_result.get("target", "")).strip().lower()
    recon_mode = normalize_recon_mode(str(domain_result.get("recon_mode", "hybrid")))
    subdomains = _safe_list(domain_result.get("subdomains"))
    addresses = _safe_list(domain_result.get("resolved_addresses"))
    collector_rows = _collector_rows(domain_result)
    wordlist_payload = domain_result.get("surface_wordlists", {})
    if not isinstance(wordlist_payload, dict):
        wordlist_payload = {}
    rdap_payload = domain_result.get("rdap", {})
    rdap_nameservers = []
    if isinstance(rdap_payload, dict):
        rdap_nameservers = _safe_list(rdap_payload.get("name_servers"))

    bucketed = _bucket_subdomains(subdomains)
    high_priority, medium_priority = _prioritize_hosts(subdomains)

    active_enabled = recon_mode in {"active", "hybrid"}
    passive_enabled = recon_mode in {"passive", "hybrid"}
    active_signal_count = (
        len(addresses)
        + int(bool(domain_result.get("https", {}).get("status")))
        + int(bool(domain_result.get("http", {}).get("status")))
        + int(bool(domain_result.get("robots_txt_present")))
        + int(bool(domain_result.get("security_txt_present")))
    )
    passive_signal_count = len(subdomains) + len(rdap_nameservers) + int(bool(rdap_payload))
    attack_surface_score = min(
        100,
        (len(subdomains) // 2)
        + (len(high_priority) * 12)
        + (len(medium_priority) * 5)
        + (len(addresses) * 6)
        + (0 if domain_result.get("security_txt_present") else 6)
        + (0 if domain_result.get("http", {}).get("redirects_to_https") else 5),
    )

    prioritized_hosts = _safe_list(domain_result.get("prioritized_subdomains")) or (high_priority + medium_priority)[:16]
    matched_priority_labels = _safe_list(wordlist_payload.get("matched_priority_labels")) or matched_surface_subdomain_labels(subdomains)
    recommended_ports = _safe_int_list(wordlist_payload.get("top_ports"))
    common_paths = _safe_list(wordlist_payload.get("common_paths"))
    return {
        "target": target,
        "recon_mode": recon_mode,
        "lanes": {
            "passive_enabled": passive_enabled,
            "active_enabled": active_enabled,
            "collector_status": collector_rows,
        },
        "source_summary": {
            "passive_signals": passive_signal_count,
            "active_signals": active_signal_count,
            "addresses": len(addresses),
            "subdomains": len(subdomains),
            "nameservers": len(rdap_nameservers),
        },
        "environment_buckets": {key: len(values) for key, values in bucketed.items()},
        "priority_summary": {
            "high_priority_count": len(high_priority),
            "medium_priority_count": len(medium_priority),
            "prioritized_hosts": prioritized_hosts,
            "high_priority_hosts": high_priority[:80],
            "medium_priority_hosts": medium_priority[:80],
            "matched_priority_labels": matched_priority_labels,
        },
        "probe_plan": {
            "recommended_ports": recommended_ports[:32],
            "common_paths": common_paths[:24],
        },
        "attack_surface_score": attack_surface_score,
    }


def build_surface_next_steps(
    domain_result: dict[str, Any],
    *,
    issue_summary: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build concise next-step guidance for domain reconnaissance."""

    target = str(domain_result.get("target", "")).strip().lower() or "target"
    recon_mode = normalize_recon_mode(str(domain_result.get("recon_mode", "hybrid")))
    surface_map = build_surface_map(domain_result)
    priority_summary = surface_map.get("priority_summary", {}) if isinstance(surface_map, dict) else {}
    source_summary = surface_map.get("source_summary", {}) if isinstance(surface_map, dict) else {}
    probe_plan = surface_map.get("probe_plan", {}) if isinstance(surface_map, dict) else {}
    actions: list[dict[str, str]] = []

    if recon_mode == "passive":
        actions.append(
            {
                "priority": "P1",
                "title": "Validate passive findings with live probes",
                "rationale": "Passive-only recon found inventory, but live DNS and HTTP verification is still missing.",
                "command_hint": f"surface {target} --recon-mode hybrid --preset deep --html",
            }
        )
    elif recon_mode == "active":
        actions.append(
            {
                "priority": "P2",
                "title": "Add passive exposure coverage",
                "rationale": "Active probes ran, but CT and RDAP intelligence can still reveal shadow assets and ownership clues.",
                "command_hint": f"surface {target} --recon-mode hybrid --ct --rdap --html",
            }
        )

    high_priority_count = int(priority_summary.get("high_priority_count", 0) or 0)
    if high_priority_count > 0:
        actions.append(
            {
                "priority": "P1",
                "title": "Review high-priority subdomains",
                "rationale": f"{high_priority_count} likely attack-path host(s) were identified from naming patterns.",
                "command_hint": "show modules && use surface",
            }
        )

    recommended_ports = _safe_int_list(probe_plan.get("recommended_ports"))
    common_paths = _safe_list(probe_plan.get("common_paths"))
    if recommended_ports or common_paths:
        actions.append(
            {
                "priority": "P2",
                "title": "Review the built-in surface recon plan",
                "rationale": "Framework-owned recon wordlists supplied safe top-port and common-path guidance for authorized follow-up.",
                "command_hint": f"surface {target} --recon-mode hybrid --preset deep --html",
            }
        )

    if not bool(domain_result.get("security_txt_present")):
        actions.append(
            {
                "priority": "P2",
                "title": "Add a security.txt disclosure path",
                "rationale": "No security.txt was observed, which weakens disclosure readiness and external reporting clarity.",
                "command_hint": f"surface {target} --plugin security_txt_analyzer --html",
            }
        )

    if not bool(domain_result.get("http", {}).get("redirects_to_https")):
        actions.append(
            {
                "priority": "P2",
                "title": "Verify HTTP to HTTPS enforcement",
                "rationale": "The surface does not appear to force HTTPS consistently across the observed web entrypoint.",
                "command_hint": f"surface {target} --plugin header_hardening_probe --html",
            }
        )

    passive_signals = int(source_summary.get("passive_signals", 0) or 0)
    active_signals = int(source_summary.get("active_signals", 0) or 0)
    if passive_signals == 0 and active_signals == 0:
        actions.append(
            {
                "priority": "P1",
                "title": "Increase reconnaissance depth",
                "rationale": "Very little surface telemetry was collected, so the current picture is still too thin to trust.",
                "command_hint": f"surface {target} --recon-mode hybrid --preset max --html",
            }
        )

    risk_score = 0
    if isinstance(issue_summary, dict):
        risk_score = int(issue_summary.get("risk_score", 0) or 0)
    if risk_score >= 60:
        actions.append(
            {
                "priority": "P1",
                "title": "Escalate remediation review",
                "rationale": f"Risk score is {risk_score}, which indicates the attack surface deserves immediate analyst review.",
                "command_hint": f"surface {target} --preset max --filter triage_priority_filter --html",
            }
        )

    if not actions:
        actions.append(
            {
                "priority": "P3",
                "title": "Keep the current surface snapshot as baseline",
                "rationale": "No urgent next pivot was triggered by the current recon telemetry.",
                "command_hint": f"surface {target} --recon-mode hybrid --html",
            }
        )

    return actions[:6]
