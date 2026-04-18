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
# ──────────────────────────────────────────────────────────────

"""Unified attack-surface exposure mapping helpers."""

from __future__ import annotations

import asyncio
import socket
from typing import Any


def resolve_target(domain: str) -> dict[str, Any]:
    """Resolve a domain to an IPv4 address when possible."""

    try:
        resolved_ip = socket.gethostbyname(domain)
        return {"domain": domain, "resolved_ip": resolved_ip, "resolution_failed": False}
    except Exception:
        return {"domain": domain, "resolved_ip": None, "resolution_failed": True}


def _bucket_subdomain(subdomain: str) -> str:
    value = subdomain.lower()
    groups = {
        "administrative": ("admin", "portal", "manage", "internal", "dashboard"),
        "development": ("dev", "stage", "staging", "uat", "test", "qa", "sandbox"),
        "service": ("api", "auth", "cdn", "edge", "mail", "gateway", "webhook"),
        "legacy": ("old", "legacy", "backup", "bak", "archive", "deprecated"),
        "security": ("vpn", "bastion", "sso", "firewall", "proxy", "waf"),
    }
    for bucket_name, tokens in groups.items():
        if any(token in value for token in tokens):
            return bucket_name
    return "general"


def _empty_harvest_result(domain: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "passive_result": None,
        "active_result": None,
        "all_subdomains": [],
        "total_count": 0,
        "passive_only_count": 0,
        "active_only_count": 0,
    }


async def build_surface_exposure_map(
    domain: str,
    scan_preset: str = "quick_surface",
    run_subdomain_harvest: bool = True,
    run_active_harvest: bool = False,
    subdomain_wordlist: str | None = None,
    scan_timeout: int = 300,
    harvest_timeout: int = 180,
    extra_scan_flags: list[str] | None = None,
) -> dict[str, Any]:
    """Build a combined surface exposure map for one domain."""

    from core.collect.port_surface_probe import run_surface_scan_preset_async
    from core.collect.subdomain_harvest import run_full_subdomain_harvest

    resolution = resolve_target(domain)
    scan_target = resolution.get("resolved_ip") or domain

    scan_task = run_surface_scan_preset_async(
        str(scan_target),
        scan_preset,
        extra_flags=extra_scan_flags,
        timeout_seconds=scan_timeout,
    )
    if run_subdomain_harvest:
        harvest_task = run_full_subdomain_harvest(
            domain,
            passive_timeout=harvest_timeout,
            active_timeout=harvest_timeout,
            wordlist_file=subdomain_wordlist,
            run_active=run_active_harvest,
        )
    else:
        harvest_task = asyncio.sleep(0, result=_empty_harvest_result(domain))

    port_scan_result, harvest_result = await asyncio.gather(scan_task, harvest_task)

    exposed_ports = list(port_scan_result.get("open_ports", []) or [])
    exposed_services = list(port_scan_result.get("services", []) or [])
    discovered_subdomains = list(harvest_result.get("all_subdomains", []) or [])
    os_guesses = list(port_scan_result.get("os_guesses", []) or [])

    buckets: dict[str, list[str]] = {
        "administrative": [],
        "development": [],
        "service": [],
        "legacy": [],
        "security": [],
        "general": [],
    }
    for subdomain in discovered_subdomains:
        bucket = _bucket_subdomain(subdomain)
        buckets[bucket].append(subdomain)

    risk_flags: list[str] = []
    port_risks = {
        21: "FTP open — credential exposure risk",
        23: "Telnet open — plaintext protocol",
        445: "SMB open — lateral movement risk",
        3389: "RDP exposed — remote access risk",
        3306: "MySQL exposed — database accessible",
    }
    for port in exposed_ports:
        if port in port_risks:
            risk_flags.append(port_risks[port])
    if buckets["administrative"]:
        risk_flags.append("Admin surface exposed")
    if buckets["development"]:
        risk_flags.append("Development environment exposed")
    if buckets["legacy"]:
        risk_flags.append("Legacy surface detected")
    if len(discovered_subdomains) > 50:
        risk_flags.append("Large subdomain surface — high exposure")

    scan_error = port_scan_result.get("error") if isinstance(port_scan_result, dict) else None
    harvest_error = None
    if isinstance(harvest_result, dict):
        passive_result = harvest_result.get("passive_result")
        active_result = harvest_result.get("active_result")
        if isinstance(passive_result, dict) and passive_result.get("error"):
            harvest_error = str(passive_result.get("error"))
        elif isinstance(active_result, dict) and active_result.get("error"):
            harvest_error = str(active_result.get("error"))

    surface_error = None
    if scan_error and harvest_error:
        surface_error = f"{scan_error}; {harvest_error}"
    elif scan_error:
        surface_error = str(scan_error)
    elif harvest_error:
        surface_error = str(harvest_error)

    return {
        "domain": domain,
        "resolved_ip": resolution.get("resolved_ip"),
        "scan_preset": scan_preset,
        "exposed_ports": exposed_ports,
        "exposed_services": exposed_services,
        "discovered_subdomains": discovered_subdomains,
        "subdomain_count": len(discovered_subdomains),
        "subdomain_environment_buckets": buckets,
        "os_guesses": os_guesses,
        "risk_flags": risk_flags,
        "risk_score": len(risk_flags),
        "port_scan_result": port_scan_result,
        "harvest_result": harvest_result,
        "surface_error": surface_error,
    }

