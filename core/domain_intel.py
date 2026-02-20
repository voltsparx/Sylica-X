"""Internal domain intelligence collection for Silica-X."""

from __future__ import annotations

import asyncio
import json
import re
import socket
from dataclasses import dataclass
from typing import Any

import aiohttp

from core.thread_engine import run_blocking


@dataclass(frozen=True)
class HttpArtifact:
    status: int | None
    final_url: str | None
    headers: dict[str, str]
    body: str
    error: str | None


def normalize_domain(raw_domain: str) -> str:
    value = raw_domain.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = value.split("/")[0].strip(".")
    return value


async def _resolve_addresses(domain: str) -> list[str]:
    def _resolve() -> list[str]:
        ips: set[str] = set()
        try:
            infos = socket.getaddrinfo(domain, None)
            for info in infos:
                if info and len(info) > 4 and info[4]:
                    ips.add(str(info[4][0]))
        except socket.gaierror:
            return []
        return sorted(ips)

    resolved = await run_blocking(_resolve)
    return resolved if isinstance(resolved, list) else []


async def _http_probe(
    session: aiohttp.ClientSession,
    url: str,
    timeout_seconds: int,
) -> HttpArtifact:
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout_seconds),
            allow_redirects=True,
        ) as response:
            body = await response.text(errors="ignore")
            return HttpArtifact(
                status=response.status,
                final_url=str(response.url),
                headers={k: v for k, v in response.headers.items()},
                body=body,
                error=None,
            )
    except Exception as exc:
        return HttpArtifact(
            status=None,
            final_url=None,
            headers={},
            body="",
            error=str(exc),
        )


def _extract_subdomains_from_ct_payload(payload: list[dict[str, Any]], domain: str) -> list[str]:
    collected: set[str] = set()
    suffix = f".{domain}"
    for item in payload:
        name_value = str(item.get("name_value", "")).lower().strip()
        if not name_value:
            continue
        for token in name_value.splitlines():
            candidate = token.strip().lstrip("*.").strip(".")
            if candidate == domain or candidate.endswith(suffix):
                collected.add(candidate)
    return sorted(collected)


async def _load_ct_subdomains(
    session: aiohttp.ClientSession,
    domain: str,
    timeout_seconds: int,
    max_subdomains: int,
) -> tuple[list[str], str | None]:
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    artifact = await _http_probe(session=session, url=url, timeout_seconds=timeout_seconds)
    if artifact.error:
        return [], artifact.error
    if artifact.status is None or artifact.status >= 400:
        return [], f"CT query returned HTTP {artifact.status}"
    try:
        payload = json.loads(artifact.body)
    except json.JSONDecodeError as exc:
        return [], f"CT payload parse error: {exc}"
    if not isinstance(payload, list):
        return [], "CT payload shape was not a JSON list"
    subdomains = _extract_subdomains_from_ct_payload(payload, domain)
    return subdomains[:max_subdomains], None


async def _load_rdap(
    session: aiohttp.ClientSession,
    domain: str,
    timeout_seconds: int,
) -> tuple[dict[str, Any], str | None]:
    url = f"https://rdap.org/domain/{domain}"
    artifact = await _http_probe(session=session, url=url, timeout_seconds=timeout_seconds)
    if artifact.error:
        return {}, artifact.error
    if artifact.status is None or artifact.status >= 400:
        return {}, f"RDAP query returned HTTP {artifact.status}"
    try:
        payload = json.loads(artifact.body)
    except json.JSONDecodeError as exc:
        return {}, f"RDAP payload parse error: {exc}"
    if not isinstance(payload, dict):
        return {}, "RDAP payload shape was not a JSON object"

    nameservers = [
        item.get("ldhName")
        for item in payload.get("nameservers", [])
        if isinstance(item, dict) and item.get("ldhName")
    ]
    statuses = [status for status in payload.get("status", []) if isinstance(status, str)]
    events = payload.get("events", [])
    last_changed = None
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("eventAction") in {"last changed", "registration"} and event.get("eventDate"):
                last_changed = event.get("eventDate")
                break

    return (
        {
            "handle": payload.get("handle"),
            "ldhName": payload.get("ldhName"),
            "status": statuses,
            "name_servers": nameservers,
            "last_changed": last_changed,
        },
        None,
    )


def _preview_lines(text: str, max_lines: int = 5, max_chars: int = 400) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    preview = "\n".join(lines[:max_lines])
    return preview[:max_chars]


async def scan_domain_surface(
    domain: str,
    timeout_seconds: int = 20,
    include_ct: bool = True,
    include_rdap: bool = True,
    max_subdomains: int = 250,
) -> dict[str, Any]:
    normalized_domain = normalize_domain(domain)
    if not normalized_domain:
        raise ValueError("Domain must not be empty.")

    notes: list[str] = []
    addresses = await _resolve_addresses(normalized_domain)
    if not addresses:
        notes.append("No DNS A/AAAA records resolved with local resolver.")

    # Keep TLS verification enabled by default for trustworthy collection.
    connector = aiohttp.TCPConnector(limit=40, limit_per_host=20, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
        https_task = _http_probe(
            session=session,
            url=f"https://{normalized_domain}",
            timeout_seconds=timeout_seconds,
        )
        http_task = _http_probe(
            session=session,
            url=f"http://{normalized_domain}",
            timeout_seconds=timeout_seconds,
        )
        robots_task = _http_probe(
            session=session,
            url=f"https://{normalized_domain}/robots.txt",
            timeout_seconds=timeout_seconds,
        )
        security_task = _http_probe(
            session=session,
            url=f"https://{normalized_domain}/.well-known/security.txt",
            timeout_seconds=timeout_seconds,
        )

        optional_tasks: list[asyncio.Task] = []
        if include_ct:
            optional_tasks.append(
                asyncio.create_task(
                    _load_ct_subdomains(
                        session=session,
                        domain=normalized_domain,
                        timeout_seconds=timeout_seconds,
                        max_subdomains=max_subdomains,
                    )
                )
            )

        if include_rdap:
            optional_tasks.append(
                asyncio.create_task(
                    _load_rdap(
                        session=session,
                        domain=normalized_domain,
                        timeout_seconds=timeout_seconds,
                    )
                )
            )

        https_result, http_result, robots_result, security_result = await asyncio.gather(
            https_task,
            http_task,
            robots_task,
            security_task,
        )

        subdomains: list[str] = []
        ct_error = None

        rdap_data: dict[str, Any] = {}
        rdap_error = None
        if optional_tasks:
            optional_results = await asyncio.gather(*optional_tasks)
            result_index = 0
            if include_ct:
                subdomains, ct_error = optional_results[result_index]
                result_index += 1
            if include_rdap:
                rdap_data, rdap_error = optional_results[result_index]

    if https_result.error:
        notes.append(f"HTTPS probe failed: {https_result.error}")
    if http_result.error:
        notes.append(f"HTTP probe failed: {http_result.error}")
    if ct_error:
        notes.append(f"Certificate Transparency query issue: {ct_error}")
    if rdap_error:
        notes.append(f"RDAP query issue: {rdap_error}")

    http_redirects_to_https = bool(
        http_result.final_url and http_result.final_url.lower().startswith("https://")
    )
    return {
        "target": normalized_domain,
        "resolved_addresses": addresses,
        "https": {
            "status": https_result.status,
            "final_url": https_result.final_url,
            "headers": https_result.headers,
            "error": https_result.error,
        },
        "http": {
            "status": http_result.status,
            "final_url": http_result.final_url,
            "headers": http_result.headers,
            "error": http_result.error,
            "redirects_to_https": http_redirects_to_https,
        },
        "robots_txt_present": robots_result.status is not None and robots_result.status < 400,
        "robots_preview": _preview_lines(robots_result.body),
        "security_txt_present": security_result.status is not None and security_result.status < 400,
        "security_preview": _preview_lines(security_result.body),
        "subdomains": subdomains,
        "rdap": rdap_data,
        "scan_notes": notes,
    }
