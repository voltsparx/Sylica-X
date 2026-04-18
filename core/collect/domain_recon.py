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

"""Deep domain intelligence collection helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import partial
import importlib.util
import shutil
import socket
import subprocess
from typing import Any

import aiohttp


def _dedupe_sorted(values: list[str]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


async def collect_dns_records(
    domain: str,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """Collect DNS records for a domain using built-in socket support."""

    loop = asyncio.get_event_loop()
    result: dict[str, Any] = {
        "a_records": [],
        "aaaa_records": [],
        "ptr_records": [],
        "mx_records": [],
        "ns_records": [],
        "txt_records": [],
        "soa_record": [],
        "cname_records": [],
        "error": None,
    }

    try:
        a_infos = await asyncio.wait_for(
            loop.getaddrinfo(domain, None, socket.AF_INET),
            timeout=max(1, int(timeout_seconds)),
        )
        result["a_records"] = _dedupe_sorted([row[4][0] for row in a_infos if row and row[4]])
    except Exception as exc:
        result["error"] = str(exc)

    try:
        aaaa_infos = await asyncio.wait_for(
            loop.getaddrinfo(domain, None, socket.AF_INET6),
            timeout=max(1, int(timeout_seconds)),
        )
        result["aaaa_records"] = _dedupe_sorted([row[4][0] for row in aaaa_infos if row and row[4]])
    except Exception as exc:
        if result["error"] is None:
            result["error"] = str(exc)

    ptr_records: list[str] = []
    for ip_address in result["a_records"]:
        try:
            host, _service = await asyncio.wait_for(
                loop.getnameinfo((ip_address, 0), socket.NI_NAMEREQD),
                timeout=max(1, int(timeout_seconds)),
            )
            if host:
                ptr_records.append(str(host))
        except Exception:
            continue
    result["ptr_records"] = _dedupe_sorted(ptr_records)

    if importlib.util.find_spec("dns.resolver") is not None:
        try:
            import dns.resolver
        except Exception:
            dns = None
        else:
            dns = dns.resolver
        if dns is not None:
            def _resolve_text(record_type: str) -> list[str]:
                try:
                    answer = dns.resolve(domain, record_type)
                except Exception:
                    return []
                return [str(item).strip() for item in answer if str(item).strip()]

            result["mx_records"] = _dedupe_sorted(await loop.run_in_executor(None, partial(_resolve_text, "MX")))
            result["ns_records"] = _dedupe_sorted(await loop.run_in_executor(None, partial(_resolve_text, "NS")))
            result["txt_records"] = _dedupe_sorted(await loop.run_in_executor(None, partial(_resolve_text, "TXT")))
            result["soa_record"] = _dedupe_sorted(await loop.run_in_executor(None, partial(_resolve_text, "SOA")))
            result["cname_records"] = _dedupe_sorted(await loop.run_in_executor(None, partial(_resolve_text, "CNAME")))

    return result


async def collect_cert_transparency(
    domain: str,
    session: aiohttp.ClientSession,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    """Collect certificate-transparency entries from crt.sh."""

    url = f"https://crt.sh/?q=%.{domain}&output=json"
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=max(1, int(timeout_seconds))),
        ) as response:
            payload = await response.json(content_type=None)
    except Exception as exc:
        return {
            "domain": domain,
            "ct_entries": [],
            "entry_count": 0,
            "error": str(exc),
        }

    entries: list[str] = []
    if isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict):
                continue
            name_value = str(row.get("name_value", "") or "")
            for token in name_value.splitlines():
                candidate = token.strip().lower()
                if not candidate or candidate.startswith("*."):
                    continue
                entries.append(candidate)
    ct_entries = sorted(set(entries))
    return {
        "domain": domain,
        "ct_entries": ct_entries,
        "entry_count": len(ct_entries),
        "error": None,
    }


def collect_whois_data(domain: str, timeout_seconds: int = 15) -> dict[str, Any]:
    """Collect WHOIS output using the system whois binary."""

    payload: dict[str, Any] = {
        "domain": domain,
        "registrar": "",
        "creation_date": "",
        "expiry_date": "",
        "updated_date": "",
        "name_servers": [],
        "registrant_org": "",
        "registrant_country": "",
        "status": [],
        "dnssec": "",
        "raw_output": "",
        "error": None,
    }

    binary = shutil.which("whois")
    if binary is None:
        payload["error"] = "whois binary not available"
        return payload

    try:
        result = subprocess.run(
            [binary, domain],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        payload["error"] = "whois lookup timed out"
        return payload

    payload["raw_output"] = result.stdout
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if "registrar:" in lowered and not payload["registrar"]:
            payload["registrar"] = line.split(":", 1)[1].strip()
        elif ("creation date:" in lowered or "created:" in lowered) and not payload["creation_date"]:
            payload["creation_date"] = line.split(":", 1)[1].strip()
        elif ("expiry date:" in lowered or "expires:" in lowered) and not payload["expiry_date"]:
            payload["expiry_date"] = line.split(":", 1)[1].strip()
        elif "updated date:" in lowered and not payload["updated_date"]:
            payload["updated_date"] = line.split(":", 1)[1].strip()
        elif "name server:" in lowered:
            payload["name_servers"].append(line.split(":", 1)[1].strip())
        elif "registrant organization:" in lowered and not payload["registrant_org"]:
            payload["registrant_org"] = line.split(":", 1)[1].strip()
        elif "registrant country:" in lowered and not payload["registrant_country"]:
            payload["registrant_country"] = line.split(":", 1)[1].strip()
        elif "domain status:" in lowered:
            payload["status"].append(line.split(":", 1)[1].strip())
        elif "dnssec:" in lowered and not payload["dnssec"]:
            payload["dnssec"] = line.split(":", 1)[1].strip()

    payload["name_servers"] = _dedupe_sorted(payload["name_servers"])
    payload["status"] = _dedupe_sorted(payload["status"])
    return payload


async def collect_whois_data_async(domain: str, timeout_seconds: int = 15) -> dict[str, Any]:
    """Async wrapper for collect_whois_data."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(collect_whois_data, domain, timeout_seconds=timeout_seconds),
    )


async def collect_http_headers(
    domain: str,
    session: aiohttp.ClientSession,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """Collect HTTP and HTTPS headers plus a security posture summary."""

    async def _probe(url: str) -> tuple[dict[str, Any], str | None]:
        probe = {
            "final_url": url,
            "status_code": 0,
            "headers": {},
            "server": "",
            "x_powered_by": "",
            "content_security_policy": "",
            "strict_transport_security": "",
            "x_frame_options": "",
            "x_content_type_options": "",
            "referrer_policy": "",
            "permissions_policy": "",
            "set_cookie_flags": [],
        }
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=max(1, int(timeout_seconds))),
                allow_redirects=True,
                max_redirects=5,
            ) as response:
                headers = {key: value for key, value in response.headers.items()}
                probe.update(
                    {
                        "final_url": str(response.url),
                        "status_code": int(response.status),
                        "headers": headers,
                        "server": str(headers.get("server", "") or ""),
                        "x_powered_by": str(headers.get("x-powered-by", "") or ""),
                        "content_security_policy": str(headers.get("content-security-policy", "") or ""),
                        "strict_transport_security": str(headers.get("strict-transport-security", "") or ""),
                        "x_frame_options": str(headers.get("x-frame-options", "") or ""),
                        "x_content_type_options": str(headers.get("x-content-type-options", "") or ""),
                        "referrer_policy": str(headers.get("referrer-policy", "") or ""),
                        "permissions_policy": str(headers.get("permissions-policy", "") or ""),
                        "set_cookie_flags": list(response.headers.getall("Set-Cookie", [])),
                    }
                )
                return probe, None
        except Exception as exc:
            return probe, str(exc)

    http_probe, http_error = await _probe(f"http://{domain}")
    https_probe, https_error = await _probe(f"https://{domain}")
    posture_source = https_probe if https_probe.get("headers") else http_probe
    posture_keys = [
        "server",
        "x_powered_by",
        "content_security_policy",
        "strict_transport_security",
        "x_frame_options",
        "x_content_type_options",
        "referrer_policy",
        "permissions_policy",
    ]
    security_posture = {
        key: {
            "present": bool(str(posture_source.get(key, "") or "").strip()),
            "value": str(posture_source.get(key, "") or ""),
        }
        for key in posture_keys
    }
    headers_score = sum(1 for row in security_posture.values() if row["present"])

    error = None
    if http_error and https_error:
        error = f"http: {http_error}; https: {https_error}"
    elif http_error:
        error = f"http: {http_error}"
    elif https_error:
        error = f"https: {https_error}"

    return {
        "domain": domain,
        "http_probe": http_probe,
        "https_probe": https_probe,
        "redirects_to_https": bool(str(http_probe.get("final_url", "")).startswith("https://")),
        "security_posture": security_posture,
        "headers_score": headers_score,
        "error": error,
    }


async def run_domain_deep_recon(
    domain: str,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Run full deep domain reconnaissance."""

    connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        dns_result, ct_result, http_result = await asyncio.gather(
            collect_dns_records(domain, timeout_seconds=min(timeout_seconds, 15)),
            collect_cert_transparency(domain, session, timeout_seconds=min(timeout_seconds, 20)),
            collect_http_headers(domain, session, timeout_seconds=min(timeout_seconds, 15)),
        )
        whois_result = await collect_whois_data_async(domain, timeout_seconds=min(timeout_seconds, 15))

    known_dns_tokens = set(dns_result.get("ptr_records", []) or [])
    known_dns_tokens.update(dns_result.get("cname_records", []) or [])
    known_dns_tokens.update(dns_result.get("ns_records", []) or [])
    known_dns_tokens.update(dns_result.get("mx_records", []) or [])
    known_dns_tokens.update(dns_result.get("soa_record", []) or [])
    additional_ct_subdomains = sorted(
        {
            entry
            for entry in ct_result.get("ct_entries", []) or []
            if "." in entry and not entry.startswith("*.") and entry not in known_dns_tokens and entry != domain
        }
    )

    return {
        "domain": domain,
        "dns": dns_result,
        "whois": whois_result,
        "cert_transparency": ct_result,
        "http_headers": http_result,
        "additional_ct_subdomains": additional_ct_subdomains,
        "recon_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

