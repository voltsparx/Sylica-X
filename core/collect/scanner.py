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

"""High-throughput username scanning across platform manifests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
import time
from typing import Any, Iterable
from urllib.parse import quote

import aiohttp

from core.collect.extractor import (
    extract_bio,
    extract_contacts,
    extract_links,
    extract_username_mentions,
)
from core.collect.platform_schema import PlatformConfig, load_platforms
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_CONCURRENCY = 25
_MAX_RESPONSE_BYTES = 140_000
_CACHE_TTL_SECONDS = 300
_REGEX_CACHE: dict[str, re.Pattern[str] | None] = {}
ContactExtract = dict[str, list[str]]
ProbePayload = dict[str, Any] | Exception
FollowupPayload = dict[str, Any] | Exception

_PROFILE_ALIASES = {
    "safe": "fast",
    "quick": "fast",
    "fast": "fast",
    "balanced": "balanced",
    "deep": "deep",
    "aggressive": "max",
    "max": "max",
}

_PLATFORM_CACHE: tuple[float, list[PlatformConfig]] = (0.0, [])


@dataclass(frozen=True)
class ProbeResult:
    status_code: int | None
    body: str
    response_url: str
    headers: dict[str, str]
    elapsed_ms: int | None
    error: str | None


def normalize_source_profile(raw_profile: str | None) -> str:
    """Normalize source profile labels to the internal set."""

    value = str(raw_profile or "").strip().lower()
    return _PROFILE_ALIASES.get(value, "balanced")


def _load_platforms_cached() -> list[PlatformConfig]:
    global _PLATFORM_CACHE
    now = time.monotonic()
    cached_at, cached = _PLATFORM_CACHE
    if cached and now - cached_at < _CACHE_TTL_SECONDS:
        return cached
    platforms = load_platforms()
    _PLATFORM_CACHE = (now, platforms)
    return platforms


def _score_platform(platform: PlatformConfig, profile: str) -> float:
    base = float(platform.confidence_weight) * 100.0
    methods = set(platform.detection_methods)
    method = platform.request_method.upper()

    if profile == "fast":
        base += 20.0 if "status_code" in methods else -5.0
        base += 12.0 if method == "HEAD" else 0.0
        base -= 8.0 if "message" in methods else 0.0
        base -= 6.0 if platform.request_payload is not None else 0.0
        base -= 6.0 if method in {"POST", "PUT"} else 0.0
    elif profile == "balanced":
        base += 10.0 if "status_code" in methods else 0.0
        base += 6.0 if "message" in methods else 0.0
        base += 4.0 if "response_url" in methods else 0.0
        base += 2.0 if method == "HEAD" else 0.0
    else:  # deep/max
        base += 18.0 if "message" in methods else 0.0
        base += 8.0 if "response_url" in methods else 0.0
        base += 6.0 if "status_code" in methods else 0.0
        base += 6.0 if method in {"POST", "PUT"} else 0.0
        base -= 4.0 if method == "HEAD" else 0.0

    return base


def select_platforms_for_profile(
    platforms: Iterable[PlatformConfig],
    *,
    source_profile: str,
    max_platforms: int | None,
) -> list[PlatformConfig]:
    """Choose platforms to scan based on profile and platform budget."""

    profile = normalize_source_profile(source_profile)
    ranked = sorted(
        list(platforms),
        key=lambda item: (-_score_platform(item, profile), item.name.lower()),
    )

    if max_platforms is None:
        return ranked
    limit = max(1, int(max_platforms)) if int(max_platforms) > 0 else 0
    return ranked[:limit] if limit > 0 else []


def _safe_username(raw_username: str) -> str:
    value = str(raw_username or "").strip()
    return value


def _evaluate_regex(platform: PlatformConfig, username: str) -> bool:
    if not platform.regex_check:
        return True
    pattern = _REGEX_CACHE.get(platform.regex_check)
    if pattern is None and platform.regex_check not in _REGEX_CACHE:
        try:
            pattern = re.compile(platform.regex_check)
        except re.error:
            pattern = None
        _REGEX_CACHE[platform.regex_check] = pattern
    if pattern is None:
        return True
    return bool(pattern.fullmatch(username))


def evaluate_presence(
    *,
    platform: PlatformConfig,
    username: str,
    status_code: int | None,
    body: str,
    response_url: str,
) -> tuple[str, str]:
    """Determine presence verdict using configured detection signals."""

    methods = set(platform.detection_methods)
    exists_statuses = set(platform.exists_statuses)
    not_found_statuses = set(platform.not_found_statuses)

    status_found = False
    status_not_found = False
    reasons: list[str] = []

    if "status_code" in methods:
        if status_code is not None:
            if exists_statuses and status_code in exists_statuses:
                status_found = True
                reasons.append(f"status_code={status_code}")
            elif not_found_statuses and status_code in not_found_statuses:
                status_not_found = True
                reasons.append(f"not_found_status={status_code}")
            elif not exists_statuses and 200 <= status_code < 300:
                status_found = True
                reasons.append(f"status_code={status_code}")
            elif not not_found_statuses and status_code in {404, 410}:
                status_not_found = True
                reasons.append(f"not_found_status={status_code}")

    if "message" in methods:
        lowered = (body or "").lower()
        for marker in platform.error_messages:
            if marker and marker.lower() in lowered:
                status_not_found = True
                reasons.append("error_message")
                break

    if "response_url" in methods and platform.error_url:
        error_url = platform.error_url.format(username=username)
        if response_url and response_url.startswith(error_url):
            status_not_found = True
            reasons.append("error_url")

    if status_not_found:
        return "NOT FOUND", "; ".join(reasons) or "not_found"
    if status_found:
        return "FOUND", "; ".join(reasons) or "found"

    if status_code in {401, 403, 429}:
        return "BLOCKED", "blocked"

    if status_code is None:
        return "ERROR", "request_failed"

    return "UNKNOWN", "no_signal"


async def _fetch_with_retries(
    session: aiohttp.ClientSession,
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    timeout_seconds: int,
    proxy_url: str | None,
    request_payload: dict[str, Any] | None,
    allow_redirects: bool,
    max_bytes: int,
    attempts: int,
) -> ProbeResult:
    attempts = max(1, int(attempts))
    timeout = aiohttp.ClientTimeout(total=max(1, int(timeout_seconds)))

    last_error: ProbeResult | None = None
    for attempt_index in range(attempts):
        started = time.perf_counter()
        try:
            request_kwargs: dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": headers,
                "timeout": timeout,
                "allow_redirects": allow_redirects,
                "proxy": proxy_url,
            }
            if request_payload is not None:
                request_kwargs["json"] = request_payload

            async with session.request(**request_kwargs) as response:
                if method.upper() == "HEAD":
                    body_text = ""
                else:
                    raw = await response.content.read(max_bytes)
                    body_text = raw.decode("utf-8", errors="ignore")
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                return ProbeResult(
                    status_code=response.status,
                    body=body_text,
                    response_url=str(response.url),
                    headers={key: value for key, value in response.headers.items()},
                    elapsed_ms=elapsed_ms,
                    error=None,
                )
        except asyncio.TimeoutError:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            last_error = ProbeResult(
                status_code=None,
                body="",
                response_url=url,
                headers={},
                elapsed_ms=elapsed_ms,
                error="Timeout",
            )
        except aiohttp.ClientError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            last_error = ProbeResult(
                status_code=None,
                body="",
                response_url=url,
                headers={},
                elapsed_ms=elapsed_ms,
                error=f"Network error: {exc}",
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            last_error = ProbeResult(
                status_code=None,
                body="",
                response_url=url,
                headers={},
                elapsed_ms=elapsed_ms,
                error=f"Unexpected error: {exc}",
            )

        if attempt_index < attempts - 1:
            await asyncio.sleep(0.12)

    return last_error or ProbeResult(
        status_code=None,
        body="",
        response_url=url,
        headers={},
        elapsed_ms=None,
        error="request_failed",
    )


async def _probe_platform(
    session: aiohttp.ClientSession,
    platform: PlatformConfig,
    *,
    username: str,
    timeout_seconds: int,
    proxy_url: str | None,
    profile: str,
) -> dict[str, Any]:
    platform_url = platform.url.format(username=quote(username, safe=""))
    url_probe = platform.url_probe.format(username=quote(username, safe=""))
    headers = {"User-Agent": "Silica-X/9.3.0", **(platform.headers or {})}

    if not _evaluate_regex(platform, username):
        return {
            "platform": platform.name,
            "url": platform_url,
            "status": "INVALID_USERNAME",
            "confidence": 0,
            "context": "regex_check_failed",
            "http_status": None,
            "response_time_ms": None,
            "contacts": {"emails": [], "phones": []},
            "links": [],
            "mentions": [],
            "bio": "",
        }

    methods = set(platform.detection_methods)
    need_body = "message" in methods
    method = platform.request_method.upper()
    request_payload = platform.request_payload

    if request_payload is not None and method not in {"POST", "PUT"}:
        method = "POST"
    if need_body and method == "HEAD":
        method = "GET"
    if not need_body and method == "GET" and request_payload is None:
        method = "HEAD"

    attempts = 2 if profile in {"deep", "max"} else 1

    response = await _fetch_with_retries(
        session,
        method=method,
        url=url_probe,
        headers=headers,
        timeout_seconds=timeout_seconds,
        proxy_url=proxy_url,
        request_payload=request_payload,
        allow_redirects=True,
        max_bytes=_MAX_RESPONSE_BYTES,
        attempts=attempts,
    )

    if method == "HEAD" and response.status_code in {403, 405}:
        response = await _fetch_with_retries(
            session,
            method="GET",
            url=url_probe,
            headers=headers,
            timeout_seconds=timeout_seconds,
            proxy_url=proxy_url,
            request_payload=None,
            allow_redirects=True,
            max_bytes=_MAX_RESPONSE_BYTES,
            attempts=1,
        )

    verdict, reason = evaluate_presence(
        platform=platform,
        username=username,
        status_code=response.status_code,
        body=response.body,
        response_url=response.response_url,
    )

    confidence = 0
    if verdict == "FOUND":
        confidence = int(round(float(platform.confidence_weight) * 100))
    elif verdict == "BLOCKED":
        confidence = 8
    elif verdict == "UNKNOWN":
        confidence = 5

    contacts: ContactExtract = {"emails": [], "phones": []}
    links: list[str] = []
    mentions: list[str] = []
    bio = ""

    if response.body and verdict == "FOUND":
        bio = extract_bio(response.body) or ""
        contacts = extract_contacts(response.body)
        links = extract_links(response.body)
        mentions = extract_username_mentions(response.body, username)

    extract_followup = True
    needs_followup = verdict == "FOUND" and not response.body and extract_followup

    return {
        "platform": platform.name,
        "url": platform_url,
        "status": verdict,
        "confidence": confidence,
        "context": reason,
        "http_status": response.status_code,
        "response_time_ms": response.elapsed_ms,
        "contacts": contacts,
        "links": links,
        "mentions": mentions,
        "bio": bio,
        "_needs_followup": needs_followup,
    }


async def _fetch_profile_content(
    session: aiohttp.ClientSession,
    platform: PlatformConfig,
    *,
    username: str,
    timeout_seconds: int,
    proxy_url: str | None,
) -> dict[str, Any]:
    url = platform.url.format(username=quote(username, safe=""))
    headers = {"User-Agent": "Silica-X/9.3.0", **(platform.headers or {})}
    response = await _fetch_with_retries(
        session,
        method="GET",
        url=url,
        headers=headers,
        timeout_seconds=timeout_seconds,
        proxy_url=proxy_url,
        request_payload=None,
        allow_redirects=True,
        max_bytes=_MAX_RESPONSE_BYTES,
        attempts=1,
    )

    if not response.body:
        return {"bio": "", "contacts": {"emails": [], "phones": []}, "links": [], "mentions": []}

    return {
        "bio": extract_bio(response.body) or "",
        "contacts": extract_contacts(response.body),
        "links": extract_links(response.body),
        "mentions": extract_username_mentions(response.body, username),
    }


async def scan_username(
    *,
    username: str,
    proxy_url: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    source_profile: str = "balanced",
    max_platforms: int | None = None,
) -> list[dict[str, Any]]:
    """Scan a username across platform manifests with async concurrency."""

    normalized_username = _safe_username(username)
    if not normalized_username:
        return []

    profile = normalize_source_profile(source_profile)
    platforms = _load_platforms_cached()
    selected = select_platforms_for_profile(
        platforms,
        source_profile=profile,
        max_platforms=max_platforms,
    )

    if not selected:
        return []

    concurrency_limit = max(1, int(max_concurrency))
    connector = aiohttp.TCPConnector(
        limit=concurrency_limit,
        limit_per_host=max(8, min(32, concurrency_limit)),
        ttl_dns_cache=300,
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def _probe_with_limit(index: int, platform: PlatformConfig) -> tuple[int, PlatformConfig, Any]:
            async with semaphore:
                payload: ProbePayload
                try:
                    payload = await _probe_platform(
                        session,
                        platform,
                        username=normalized_username,
                        timeout_seconds=timeout_seconds,
                        proxy_url=proxy_url,
                        profile=profile,
                    )
                except Exception as exc:  # pragma: no cover - defensive guard
                    payload = exc
                return index, platform, payload

        async def _follow_with_limit(index: int, platform: PlatformConfig) -> tuple[int, Any]:
            async with semaphore:
                payload: FollowupPayload
                try:
                    payload = await _fetch_profile_content(
                        session,
                        platform,
                        username=normalized_username,
                        timeout_seconds=timeout_seconds,
                        proxy_url=proxy_url,
                    )
                except Exception as exc:  # pragma: no cover - defensive guard
                    payload = exc
                return index, payload

        tasks = [
            asyncio.create_task(_probe_with_limit(index, platform))
            for index, platform in enumerate(selected)
        ]

        rows: list[dict[str, Any]] = [
            {
                "platform": platform.name,
                "url": platform.url.format(username=quote(normalized_username, safe="")),
                "status": "ERROR",
                "confidence": 0,
                "context": "pending",
                "http_status": None,
                "response_time_ms": None,
                "contacts": {"emails": [], "phones": []},
                "links": [],
                "mentions": [],
                "bio": "",
            }
            for platform in selected
        ]

        follow_tasks: list[asyncio.Task[tuple[int, Any]]] = []
        for future in asyncio.as_completed(tasks):
            index, platform, payload = await future
            if isinstance(payload, Exception):
                rows[index] = {
                    "platform": platform.name,
                    "url": platform.url.format(username=quote(normalized_username, safe="")),
                    "status": "ERROR",
                    "confidence": 0,
                    "context": str(payload),
                    "http_status": None,
                    "response_time_ms": None,
                    "contacts": {"emails": [], "phones": []},
                    "links": [],
                    "mentions": [],
                    "bio": "",
                }
                continue

            if payload.get("_needs_followup"):
                follow_tasks.append(asyncio.create_task(_follow_with_limit(index, platform)))
            payload.pop("_needs_followup", None)
            rows[index] = payload

        if follow_tasks:
            for follow_future in asyncio.as_completed(follow_tasks):
                row_index, payload = await follow_future
                if isinstance(payload, Exception) or not isinstance(payload, dict):
                    continue
                rows[row_index].update(payload)

    rows.sort(key=lambda item: str(item.get("platform", "")).lower())
    return rows
