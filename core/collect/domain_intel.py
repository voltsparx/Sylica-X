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

"""Domain surface intelligence collection helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import socket
import time
from typing import Any
from urllib.parse import quote, urlsplit

import aiohttp


DEFAULT_TIMEOUT_SECONDS = 20
_MAX_BODY_BYTES = 140_000


@dataclass(frozen=True)
class HttpArtifact:
    status: int | None
    final_url: str
    headers: dict[str, str]
    body: str
    error: str | None


def normalize_domain(raw: str | None) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""

    lowered = value.lower()
    if "//" not in lowered:
        lowered = f"http://{lowered}"

    parsed = urlsplit(lowered)
    host = parsed.hostname or ""
    return host.strip(".")


async def _resolve_addresses(domain: str, timeout_seconds: int) -> list[str]:
    if not domain:
        return []
    loop = asyncio.get_running_loop()
    try:
        infos = await asyncio.wait_for(
            loop.getaddrinfo(domain, None, type=socket.SOCK_STREAM),
            timeout=max(1, int(timeout_seconds)),
        )
    except Exception:
        return []

    addresses = {info[4][0] for info in infos if info and info[4]}
    return sorted(addresses)


async def _http_probe(
    session: aiohttp.ClientSession,
    url: str,
    timeout_seconds: int,
) -> HttpArtifact:
    started = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=max(1, int(timeout_seconds)))
    try:
        async with session.get(url, timeout=timeout, allow_redirects=True) as response:
            raw = await response.content.read(_MAX_BODY_BYTES)
            body = raw.decode("utf-8", errors="ignore")
            return HttpArtifact(
                status=response.status,
                final_url=str(response.url),
                headers={key: value for key, value in response.headers.items()},
                body=body,
                error=None,
            )
    except asyncio.TimeoutError:
        return HttpArtifact(status=None, final_url=url, headers={}, body="", error="Timeout")
    except aiohttp.ClientError as exc:
        return HttpArtifact(status=None, final_url=url, headers={}, body="", error=f"Network error: {exc}")
    except Exception as exc:  # pragma: no cover
        return HttpArtifact(status=None, final_url=url, headers={}, body="", error=str(exc))
    finally:
        _ = int((time.perf_counter() - started) * 1000)


async def _load_ct_subdomains(
    session: aiohttp.ClientSession,
    domain: str,
    timeout_seconds: int,
    max_subdomains: int,
) -> tuple[list[str], str | None]:
    if not domain:
        return [], "missing domain"

    url = f"https://crt.sh/?q=%25.{quote(domain)}&output=json"
    timeout = aiohttp.ClientTimeout(total=max(1, int(timeout_seconds)))
    try:
        async with session.get(url, timeout=timeout) as response:
            raw = await response.content.read(2_000_000)
            payload = json.loads(raw.decode("utf-8", errors="ignore"))
    except asyncio.TimeoutError:
        return [], "ct timeout"
    except Exception as exc:
        return [], f"ct error: {exc}"

    names: set[str] = set()
    if isinstance(payload, list):
        for row in payload:
            name_value = row.get("name_value") if isinstance(row, dict) else None
            if not name_value:
                continue
            for entry in str(name_value).split("\n"):
                entry = entry.strip().lower()
                if entry and entry.endswith(f".{domain}"):
                    names.add(entry)
                if len(names) >= max_subdomains:
                    break
            if len(names) >= max_subdomains:
                break

    return sorted(names)[:max_subdomains], None


async def _load_rdap(
    session: aiohttp.ClientSession,
    domain: str,
    timeout_seconds: int,
) -> tuple[dict[str, Any], str | None]:
    if not domain:
        return {}, "missing domain"

    url = f"https://rdap.org/domain/{quote(domain)}"
    timeout = aiohttp.ClientTimeout(total=max(1, int(timeout_seconds)))
    try:
        async with session.get(url, timeout=timeout) as response:
            raw = await response.content.read(500_000)
            payload = json.loads(raw.decode("utf-8", errors="ignore"))
    except asyncio.TimeoutError:
        return {}, "rdap timeout"
    except Exception as exc:
        return {}, f"rdap error: {exc}"

    return payload if isinstance(payload, dict) else {}, None


async def _fetch_small_text(
    session: aiohttp.ClientSession,
    url: str,
    timeout_seconds: int,
) -> tuple[bool, str]:
    timeout = aiohttp.ClientTimeout(total=max(1, int(timeout_seconds)))
    try:
        async with session.get(url, timeout=timeout, allow_redirects=True) as response:
            raw = await response.content.read(4000)
            body = raw.decode("utf-8", errors="ignore").strip()
            if response.status and response.status < 400:
                return True, body
            return False, body
    except Exception:
        return False, ""


def _http_artifact_payload(artifact: HttpArtifact) -> dict[str, Any]:
    return {
        "status": artifact.status,
        "final_url": artifact.final_url,
        "headers": artifact.headers,
        "error": artifact.error,
        "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _note_if_error(notes: list[str], label: str, error: str | None) -> None:
    if error:
        notes.append(f"{label}: {error}")


async def scan_domain_surface(
    *,
    domain: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    include_ct: bool = False,
    include_rdap: bool = False,
    max_subdomains: int = 250,
) -> dict[str, Any]:
    normalized_domain = normalize_domain(domain)
    if not normalized_domain:
        return {}

    timeout_seconds = max(5, int(timeout_seconds))
    max_subdomains = max(0, int(max_subdomains))

    connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        resolve_task = asyncio.create_task(_resolve_addresses(normalized_domain, timeout_seconds))
        https_task = asyncio.create_task(
            _http_probe(session, f"https://{normalized_domain}", timeout_seconds)
        )
        http_task = asyncio.create_task(
            _http_probe(session, f"http://{normalized_domain}", timeout_seconds)
        )

        ct_task = (
            asyncio.create_task(_load_ct_subdomains(session, normalized_domain, timeout_seconds, max_subdomains))
            if include_ct
            else None
        )
        rdap_task = (
            asyncio.create_task(_load_rdap(session, normalized_domain, timeout_seconds))
            if include_rdap
            else None
        )

        resolved_addresses = await resolve_task
        https_artifact, http_artifact = await asyncio.gather(https_task, http_task)

        subdomains: list[str] = []
        rdap_payload: dict[str, Any] = {}
        scan_notes: list[str] = []

        if ct_task:
            ct_payload, ct_error = await ct_task
            subdomains = ct_payload
            _note_if_error(scan_notes, "ct", ct_error)
        if rdap_task:
            rdap_payload, rdap_error = await rdap_task
            _note_if_error(scan_notes, "rdap", rdap_error)

        robots_present = False
        security_present = False
        robots_preview = ""
        security_preview = ""

        if timeout_seconds >= 15:
            preferred_scheme = "https" if https_artifact.status and https_artifact.status < 400 else "http"
            robots_url = f"{preferred_scheme}://{normalized_domain}/robots.txt"
            security_url = f"{preferred_scheme}://{normalized_domain}/.well-known/security.txt"

            robots_present, robots_preview = await _fetch_small_text(
                session, robots_url, min(8, timeout_seconds)
            )
            security_present, security_preview = await _fetch_small_text(
                session, security_url, min(8, timeout_seconds)
            )

    return {
        "target": normalized_domain,
        "resolved_addresses": resolved_addresses,
        "https": _http_artifact_payload(https_artifact),
        "http": _http_artifact_payload(http_artifact),
        "subdomains": subdomains,
        "rdap": rdap_payload,
        "scan_notes": scan_notes,
        "robots_txt_present": robots_present,
        "security_txt_present": security_present,
        "robots_preview": robots_preview[:400],
        "security_preview": security_preview[:400],
    }
