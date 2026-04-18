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

"""Subdomain harvest helpers for passive and active enumeration."""

from __future__ import annotations

import asyncio
from functools import partial
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


def locate_harvest_binary() -> str | None:
    """Locate the installed subdomain harvest binary."""

    return shutil.which("amass") or shutil.which("amass3")


def harvest_binary_status() -> dict[str, Any]:
    """Return harvest binary status details."""

    path = locate_harvest_binary()
    if path is None:
        return {
            "available": False,
            "path": None,
            "version": "",
            "passive_capable": True,
            "active_capable": True,
        }

    result = subprocess.run(
        [path, "enum", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    version = ""
    for line in (result.stdout or result.stderr).splitlines():
        if line.strip():
            version = line.strip()
            break
    return {
        "available": True,
        "path": path,
        "version": version,
        "passive_capable": True,
        "active_capable": True,
    }


async def harvest_binary_status_async() -> dict[str, Any]:
    """Async wrapper for harvest_binary_status."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, harvest_binary_status)


def _parse_harvest_lines(stdout: str) -> tuple[list[str], int]:
    names: list[str] = []
    raw_count = 0
    for line in stdout.splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        name = str(payload.get("name", "") or "").strip()
        if not name:
            continue
        names.append(name)
        raw_count += 1
    return sorted(set(names)), raw_count


def run_passive_subdomain_harvest(
    domain: str,
    timeout_seconds: int = 180,
    config_file: str | None = None,
) -> dict[str, Any]:
    """Run passive subdomain harvest for a domain."""

    binary = locate_harvest_binary()
    if binary is None:
        return {"error": "harvest binary not found", "domain": domain, "subdomains": []}

    command = [binary, "enum", "-d", domain, "-passive", "-json", "/dev/stdout"]
    if config_file is not None:
        command.extend(["-config", config_file])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"error": "subdomain harvest timed out", "domain": domain, "subdomains": []}

    subdomains, raw_count = _parse_harvest_lines(result.stdout)
    return {
        "domain": domain,
        "mode": "passive",
        "subdomains": subdomains,
        "raw_count": raw_count,
        "return_code": int(result.returncode),
        "stderr": result.stderr,
        "command": command,
        "error": None,
    }


async def run_passive_subdomain_harvest_async(
    domain: str,
    timeout_seconds: int = 180,
    config_file: str | None = None,
) -> dict[str, Any]:
    """Async wrapper for passive subdomain harvest."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(
            run_passive_subdomain_harvest,
            domain,
            timeout_seconds=timeout_seconds,
            config_file=config_file,
        ),
    )


def run_active_subdomain_harvest(
    domain: str,
    wordlist_file: str | None = None,
    timeout_seconds: int = 360,
    config_file: str | None = None,
) -> dict[str, Any]:
    """Run active subdomain harvest for a domain."""

    binary = locate_harvest_binary()
    if binary is None:
        return {"error": "harvest binary not found", "domain": domain, "subdomains": []}

    command = [binary, "enum", "-d", domain, "-json", "/dev/stdout"]
    wordlist_used: str | None = None
    if wordlist_file is not None:
        wordlist_used = str(wordlist_file)
        command.extend(["-brute", "-w", wordlist_used])
    else:
        default_wordlist = (
            Path(__file__).resolve().parent.parent.parent / "wordlists" / "attack_surface" / "subdomains_small.txt"
        )
        if default_wordlist.exists():
            wordlist_used = str(default_wordlist)
            command.extend(["-brute", "-w", wordlist_used])
    if config_file is not None:
        command.extend(["-config", config_file])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"error": "subdomain harvest timed out", "domain": domain, "subdomains": []}

    subdomains, raw_count = _parse_harvest_lines(result.stdout)
    return {
        "domain": domain,
        "mode": "active",
        "subdomains": subdomains,
        "raw_count": raw_count,
        "return_code": int(result.returncode),
        "stderr": result.stderr,
        "command": command,
        "wordlist_used": wordlist_used,
        "error": None,
    }


async def run_active_subdomain_harvest_async(
    domain: str,
    wordlist_file: str | None = None,
    timeout_seconds: int = 360,
    config_file: str | None = None,
) -> dict[str, Any]:
    """Async wrapper for active subdomain harvest."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(
            run_active_subdomain_harvest,
            domain,
            wordlist_file=wordlist_file,
            timeout_seconds=timeout_seconds,
            config_file=config_file,
        ),
    )


async def run_full_subdomain_harvest(
    domain: str,
    passive_timeout: int = 180,
    active_timeout: int = 360,
    wordlist_file: str | None = None,
    run_active: bool = False,
) -> dict[str, Any]:
    """Run passive harvest and optionally active harvest, then merge results."""

    passive_result = await run_passive_subdomain_harvest_async(
        domain,
        timeout_seconds=passive_timeout,
    )
    active_result: dict[str, Any] | None = None
    if run_active:
        active_result = await run_active_subdomain_harvest_async(
            domain,
            wordlist_file=wordlist_file,
            timeout_seconds=active_timeout,
        )

    passive_subdomains = set(passive_result.get("subdomains", []) or [])
    active_subdomains = set(active_result.get("subdomains", []) or []) if active_result else set()
    all_subdomains = sorted(passive_subdomains | active_subdomains)
    return {
        "domain": domain,
        "passive_result": passive_result,
        "active_result": active_result,
        "all_subdomains": all_subdomains,
        "total_count": len(all_subdomains),
        "passive_only_count": len(passive_subdomains - active_subdomains),
        "active_only_count": len(active_subdomains - passive_subdomains) if active_result else 0,
    }

