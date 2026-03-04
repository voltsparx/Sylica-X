"""Shared resilient HTTP request helpers used by collectors."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import random
import time
from typing import Any

import aiohttp


_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for network-bound request collection."""

    attempts: int = 3
    base_delay_seconds: float = 0.35
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 6.0
    jitter_seconds: float = 0.15
    retryable_statuses: tuple[int, ...] = (408, 425, 429, 500, 502, 503, 504)


@dataclass(frozen=True)
class ResilientHttpResponse:
    status_code: int | None
    body: str
    response_url: str
    headers: dict[str, str]
    elapsed_ms: int | None
    error: str | None
    attempts_used: int


def _parse_retry_after_seconds(headers: dict[str, str]) -> float | None:
    value = headers.get("Retry-After")
    if not value:
        value = headers.get("retry-after")
    if not value:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    try:
        seconds = float(raw)
    except ValueError:
        try:
            target_dt = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        seconds = (target_dt - now).total_seconds()

    if seconds <= 0:
        return None
    return seconds


def _retry_delay_seconds(
    policy: RetryPolicy,
    attempt_index: int,
    *,
    response_headers: dict[str, str] | None = None,
) -> float:
    retry_after = None
    if response_headers:
        retry_after = _parse_retry_after_seconds(response_headers)
    if retry_after is not None:
        base = retry_after
    else:
        base = policy.base_delay_seconds * (policy.backoff_multiplier ** attempt_index)
    jitter = random.uniform(0.0, max(0.0, policy.jitter_seconds))
    return min(policy.max_delay_seconds, max(0.0, base + jitter))


def _is_retryable_status(policy: RetryPolicy, status_code: int | None) -> bool:
    if status_code is None:
        return True
    statuses = set(policy.retryable_statuses) or _RETRYABLE_STATUS_CODES
    return status_code in statuses


async def request_text_with_retries(
    session: aiohttp.ClientSession,
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 20,
    proxy_url: str | None = None,
    allow_redirects: bool = True,
    request_payload: dict[str, Any] | None = None,
    retry_policy: RetryPolicy | None = None,
) -> ResilientHttpResponse:
    """Perform an HTTP request with bounded retries and backoff.

    Request retries are used for transient network failures and retryable
    response statuses (e.g. 429/5xx).
    """

    policy = retry_policy or RetryPolicy()
    attempts = max(1, int(policy.attempts))
    method_name = str(method or "GET").upper()
    timeout = aiohttp.ClientTimeout(total=max(1, int(timeout_seconds)))
    request_headers = dict(headers or {})

    last_response: ResilientHttpResponse | None = None

    for attempt_index in range(attempts):
        started = time.perf_counter()
        try:
            request_kwargs: dict[str, Any] = {
                "method": method_name,
                "url": url,
                "headers": request_headers,
                "allow_redirects": allow_redirects,
                "timeout": timeout,
            }
            if proxy_url:
                request_kwargs["proxy"] = proxy_url
            if request_payload is not None:
                request_kwargs["json"] = request_payload

            async with session.request(**request_kwargs) as response:
                body = await response.text(errors="ignore")
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                last_response = ResilientHttpResponse(
                    status_code=response.status,
                    body=body,
                    response_url=str(response.url),
                    headers={key: value for key, value in response.headers.items()},
                    elapsed_ms=elapsed_ms,
                    error=None,
                    attempts_used=attempt_index + 1,
                )
        except asyncio.TimeoutError:
            last_response = ResilientHttpResponse(
                status_code=None,
                body="",
                response_url=url,
                headers={},
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                error="Timeout",
                attempts_used=attempt_index + 1,
            )
        except aiohttp.ClientError as exc:
            last_response = ResilientHttpResponse(
                status_code=None,
                body="",
                response_url=url,
                headers={},
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                error=f"Network error: {exc}",
                attempts_used=attempt_index + 1,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            last_response = ResilientHttpResponse(
                status_code=None,
                body="",
                response_url=url,
                headers={},
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                error=f"Unexpected error: {exc}",
                attempts_used=attempt_index + 1,
            )

        if attempt_index >= attempts - 1:
            break

        if last_response is None:
            continue
        if not _is_retryable_status(policy, last_response.status_code):
            break

        await asyncio.sleep(
            _retry_delay_seconds(
                policy,
                attempt_index,
                response_headers=last_response.headers,
            )
        )

    if last_response is None:  # pragma: no cover - defensive fallback
        return ResilientHttpResponse(
            status_code=None,
            body="",
            response_url=url,
            headers={},
            elapsed_ms=None,
            error="Request failed without response.",
            attempts_used=0,
        )
    return last_response
