import asyncio
import random
import re
import time
from dataclasses import dataclass

import aiohttp

from core.async_engine import run_async_batch
from core.extractor import (
    extract_bio,
    extract_contacts,
    extract_links,
    extract_username_mentions,
)
from core.platform_schema import PlatformConfig, load_platforms
from core.thread_engine import run_blocking_batch


HEADERS_POOL = [
    {"User-Agent": "Mozilla/5.0"},
    {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
]

DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_CONCURRENCY = 20
WAF_SIGNATURES = (
    "challenge-error-text",
    "cloudflare",
    "perimeterx",
    "access denied",
    "captcha",
)


@dataclass
class FetchResult:
    status_code: int | None
    body: str
    response_url: str
    elapsed_ms: int | None
    error: str | None


def _format_template(template: str, username: str) -> str:
    return template.format(username=username)


def _matches_regex(pattern: str | None, username: str) -> bool:
    if not pattern:
        return True
    return re.search(pattern, username) is not None


def _contains_waf_fingerprint(text: str) -> bool:
    lowered = text.lower()
    return any(fingerprint in lowered for fingerprint in WAF_SIGNATURES)


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def _evaluate_status_code(platform: PlatformConfig, status_code: int) -> tuple[bool, str]:
    if status_code in platform.not_found_statuses:
        return False, f"status {status_code} in not_found_statuses"

    if platform.exists_statuses:
        if status_code in platform.exists_statuses:
            return True, f"status {status_code} in exists_statuses"
        return False, f"status {status_code} not in exists_statuses"

    if 200 <= status_code < 300:
        return True, f"status {status_code} in 2xx range"
    return False, f"status {status_code} outside 2xx range"


def _evaluate_message(platform: PlatformConfig, body: str) -> tuple[bool, str]:
    for error_message in platform.error_messages:
        if error_message in body:
            return False, "error message fingerprint matched"
    return True, "no error message fingerprints matched"


def _evaluate_response_url(
    platform: PlatformConfig, response_url: str, username: str, status_code: int
) -> tuple[bool, str]:
    if platform.error_url:
        expected_error_url = _format_template(platform.error_url, username)
        if _normalize_url(response_url) == _normalize_url(expected_error_url):
            return False, "response URL matched known error URL"
        return True, "response URL differed from error URL"

    if 200 <= status_code < 300:
        return True, "response URL method accepted with 2xx status"
    return False, "response URL method rejected with non-2xx status"


def evaluate_presence(
    platform: PlatformConfig,
    username: str,
    status_code: int | None,
    body: str,
    response_url: str,
) -> tuple[str, str]:
    if status_code is None:
        return "ERROR", "No HTTP status code"

    method_outcomes: list[bool] = []
    reasons: list[str] = []

    for method in platform.detection_methods:
        if method == "status_code":
            exists, reason = _evaluate_status_code(platform, status_code)
        elif method == "message":
            exists, reason = _evaluate_message(platform, body)
        elif method == "response_url":
            exists, reason = _evaluate_response_url(
                platform=platform,
                response_url=response_url,
                username=username,
                status_code=status_code,
            )
        else:
            return "ERROR", f"Unsupported detection method: {method}"

        method_outcomes.append(exists)
        reasons.append(f"{method}: {reason}")

    # Conservative verdicting: every configured check must agree with existence.
    if method_outcomes and all(method_outcomes):
        return "FOUND", "; ".join(reasons)
    return "NOT FOUND", "; ".join(reasons)


def _compute_confidence(
    platform: PlatformConfig,
    verdict: str,
    bio: str | None,
    mentions: list[str],
    contacts: dict[str, list[str]],
) -> int:
    if verdict != "FOUND":
        return 0

    confidence = int(platform.confidence_weight * 100)
    if bio:
        confidence += 5
    if mentions:
        confidence += 5
    if contacts.get("emails"):
        confidence += 10
    if contacts.get("phones"):
        confidence += 10
    return max(0, min(confidence, 100))


async def _request_platform(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: dict[str, str],
    timeout_seconds: int,
    proxy_url: str | None,
    allow_redirects: bool,
    request_payload: dict | None,
) -> FetchResult:
    start = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    try:
        if request_payload is None:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                allow_redirects=allow_redirects,
                timeout=timeout,
                proxy=proxy_url,
            ) as response:
                text = await response.text(errors="ignore")
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                return FetchResult(
                    status_code=response.status,
                    body=text,
                    response_url=str(response.url),
                    elapsed_ms=elapsed_ms,
                    error=None,
                )

        async with session.request(
            method=method,
            url=url,
            headers=headers,
            allow_redirects=allow_redirects,
            timeout=timeout,
            proxy=proxy_url,
            json=request_payload,
        ) as response:
            text = await response.text(errors="ignore")
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return FetchResult(
                status_code=response.status,
                body=text,
                response_url=str(response.url),
                elapsed_ms=elapsed_ms,
                error=None,
            )
    except asyncio.TimeoutError:
        return FetchResult(
            status_code=None,
            body="",
            response_url=url,
            elapsed_ms=int((time.perf_counter() - start) * 1000),
            error="Timeout",
        )
    except aiohttp.ClientError as exc:
        return FetchResult(
            status_code=None,
            body="",
            response_url=url,
            elapsed_ms=int((time.perf_counter() - start) * 1000),
            error=f"Network error: {exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        return FetchResult(
            status_code=None,
            body="",
            response_url=url,
            elapsed_ms=int((time.perf_counter() - start) * 1000),
            error=f"Unexpected error: {exc}",
        )


async def scan_platform(
    session: aiohttp.ClientSession,
    platform: PlatformConfig,
    username: str,
    proxy_url: str | None,
    timeout_seconds: int,
) -> dict:
    profile_url = _format_template(platform.url, username)
    probe_url = _format_template(platform.url_probe, username)

    result = {
        "platform": platform.name,
        "url": profile_url,
        "probe_url": probe_url,
        "status": "NOT FOUND",
        "confidence": 0,
        "bio": None,
        "links": [],
        "mentions": [],
        "contacts": {"emails": [], "phones": []},
        "http_status": None,
        "response_time_ms": None,
        "detection_methods": list(platform.detection_methods),
        "context": None,
    }

    if not _matches_regex(platform.regex_check, username):
        result["status"] = "INVALID_USERNAME"
        result["context"] = "Username failed platform regex policy"
        return result

    headers = random.choice(HEADERS_POOL).copy()
    headers.update(platform.headers)
    allow_redirects = "response_url" not in platform.detection_methods

    fetch_result = await _request_platform(
        session=session,
        method=platform.request_method,
        url=probe_url,
        headers=headers,
        timeout_seconds=timeout_seconds,
        proxy_url=proxy_url,
        allow_redirects=allow_redirects,
        request_payload=platform.request_payload,
    )

    # Retry unsupported HEAD probes as GET when needed.
    if (
        platform.request_method == "HEAD"
        and fetch_result.status_code in {405, 501}
        and fetch_result.error is None
    ):
        fetch_result = await _request_platform(
            session=session,
            method="GET",
            url=probe_url,
            headers=headers,
            timeout_seconds=timeout_seconds,
            proxy_url=proxy_url,
            allow_redirects=allow_redirects,
            request_payload=platform.request_payload,
        )

    result["http_status"] = fetch_result.status_code
    result["response_time_ms"] = fetch_result.elapsed_ms

    if fetch_result.error:
        result["status"] = "ERROR"
        result["context"] = fetch_result.error
        return result

    if _contains_waf_fingerprint(fetch_result.body):
        result["status"] = "BLOCKED"
        result["context"] = "Request likely blocked by anti-bot controls"
        return result

    verdict, reason = evaluate_presence(
        platform=platform,
        username=username,
        status_code=fetch_result.status_code,
        body=fetch_result.body,
        response_url=fetch_result.response_url,
    )
    result["status"] = verdict
    result["context"] = reason

    if verdict == "FOUND":
        parsed = await run_blocking_batch(
            [
                (extract_bio, (fetch_result.body,), {}),
                (extract_links, (fetch_result.body,), {}),
                (extract_contacts, (fetch_result.body,), {}),
                (extract_username_mentions, (fetch_result.body, username), {}),
            ],
            concurrency_limit=4,
        )
        bio = parsed[0] if isinstance(parsed[0], str) or parsed[0] is None else None
        links = parsed[1] if isinstance(parsed[1], list) else []
        contacts = parsed[2] if isinstance(parsed[2], dict) else {"emails": [], "phones": []}
        mentions = parsed[3] if isinstance(parsed[3], list) else []

        if not all(isinstance(item, str) for item in links):
            links = []
        if not (
            isinstance(contacts.get("emails"), list)
            and isinstance(contacts.get("phones"), list)
        ):
            contacts = {"emails": [], "phones": []}
        if not all(isinstance(item, str) for item in mentions):
            mentions = []

        contacts = {
            "emails": [item for item in contacts.get("emails", []) if isinstance(item, str)],
            "phones": [item for item in contacts.get("phones", []) if isinstance(item, str)],
        }
        result["bio"] = bio
        result["links"] = links
        result["contacts"] = contacts
        result["mentions"] = mentions
        result["confidence"] = _compute_confidence(
            platform=platform,
            verdict=verdict,
            bio=bio,
            mentions=mentions,
            contacts=contacts,
        )

    return result


async def scan_username(
    username: str,
    proxy_url: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
) -> list[dict]:
    platforms = load_platforms()
    effective_concurrency = max(1, int(max_concurrency))

    # Keep TLS verification enabled by default for trustworthy scan results.
    connector = aiohttp.TCPConnector(
        limit=max(64, effective_concurrency * 2),
        limit_per_host=max(10, effective_concurrency),
        ttl_dns_cache=300,
    )
    async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
        tasks = [
            scan_platform(
                session=session,
                platform=platform,
                username=username,
                proxy_url=proxy_url,
                timeout_seconds=timeout_seconds,
            )
            for platform in platforms
        ]
        rows = await run_async_batch(tasks, concurrency_limit=effective_concurrency)
        return [row for row in rows if isinstance(row, dict)]
