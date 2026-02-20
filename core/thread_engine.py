"""Silica-X native thread and sync engine wiring.

Blocking/CPU-heavy work should run in threads. Completed data then flows into
sync orchestration (plugins, filters, scoring, reporting).
"""

from __future__ import annotations

import asyncio
import atexit
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any
from typing import Final


THREAD_TASKS: Final[dict[str, str]] = {
    # DNS & socket operations
    "dns_resolution": "socket.getaddrinfo",
    "reverse_dns": "PTR lookups",
    # Blocking libraries
    "whois_parsing": "python-whois (blocking)",
    "geoip_lookup": "local GeoIP DB",
    # Heavy parsing
    "large_html_parsing": "BeautifulSoup on large pages",
    "regex_contact_extraction": "emails/phones from large text",
    "username_permutation_checks": "CPU-heavy variations",
    # Fusion computations
    "confidence_scoring": "weighted scoring",
    "similarity_matching": "bio similarity / Levenshtein",
}


SYNC_PIPELINE: Final[dict[str, str | list[str]]] = {
    "plugin discovery": "signal_forge",
    "filter application": "signal_sieve",
    "data normalization": "canonicalizers",
    "correlation engine": "cross-platform matching",
    "risk scoring": "exposure tiers",
    "report generation": [
        "HTML reports",
        "JSON output",
        "CSV export",
        "CLI rendering",
    ],
    "logging": "run logs & framework logs",
}


WORKFLOWS: Final[dict[str, dict[str, list[str]]]] = {
    "profile": {
        "async": [
            "platform_existence_checks",
            "profile_page_fetch",
            "avatar_download",
        ],
        "threads": [
            "large_html_parsing",
            "regex_contact_extraction",
            "confidence_scoring",
        ],
        "sync": [
            "correlation_engine",
            "report_generation",
        ],
    },
    "surface": {
        "async": [
            "crt_sh_queries",
            "rdap_api_calls",
            "http_probe",
        ],
        "threads": [
            "dns_resolution",
            "whois_parsing",
        ],
        "sync": [
            "asset_classification",
            "exposure_scoring",
            "report_generation",
        ],
    },
    "fusion": {
        "async": [
            "public API enrichment",
        ],
        "threads": [
            "similarity_matching",
            "confidence_scoring",
        ],
        "sync": [
            "signal_fusion",
            "risk_scoring",
            "final_report",
        ],
    },
}


ENGINE_RULES: Final[tuple[str, ...]] = (
    "Network wait -> ASYNC",
    "Blocks interpreter -> THREAD",
    "Needs full dataset -> SYNC",
)

_THREAD_WORKER_ENV = "SILICA_THREAD_WORKERS"
DEFAULT_THREAD_WORKERS: Final[int] = max(8, min(64, (os.cpu_count() or 4) * 4))
MAX_THREAD_BATCH_CONCURRENCY: Final[int] = max(8, min(128, DEFAULT_THREAD_WORKERS * 2))


def _resolve_thread_worker_count() -> int:
    override = os.getenv(_THREAD_WORKER_ENV)
    if not override:
        return DEFAULT_THREAD_WORKERS
    try:
        requested = int(override)
    except ValueError:
        return DEFAULT_THREAD_WORKERS
    return max(1, min(128, requested))


THREAD_EXECUTOR = ThreadPoolExecutor(
    max_workers=_resolve_thread_worker_count(),
    thread_name_prefix="silica-thread",
)
atexit.register(lambda: THREAD_EXECUTOR.shutdown(wait=False, cancel_futures=True))


def workflow_plan(workflow: str) -> dict[str, list[str]]:
    """Return async/thread/sync plan for a workflow."""

    key = workflow.strip().lower()
    plan = WORKFLOWS.get(key, {})
    return {
        "async": list(plan.get("async", [])),
        "threads": list(plan.get("threads", [])),
        "sync": list(plan.get("sync", [])),
    }


async def run_blocking(func: Callable[..., Any], *args: object, **kwargs: object) -> Any:
    """Run a blocking call on the shared thread engine."""

    loop = asyncio.get_running_loop()
    bound = partial(func, *args, **kwargs)
    return await loop.run_in_executor(THREAD_EXECUTOR, bound)


def recommend_thread_concurrency(call_count: int, requested_limit: int = DEFAULT_THREAD_WORKERS) -> int:
    """Pick thread batch size for blocking work without overloading workers."""

    bounded_request = max(1, int(requested_limit))
    if call_count <= 0:
        return 1
    return min(MAX_THREAD_BATCH_CONCURRENCY, bounded_request, call_count)


async def run_blocking_batch(
    calls: list[tuple[Callable[..., Any], tuple[object, ...], dict[str, object]]],
    *,
    concurrency_limit: int = DEFAULT_THREAD_WORKERS,
) -> list[Any]:
    """Run multiple blocking calls concurrently with bounded worker pressure."""

    if not calls:
        return []

    effective_limit = recommend_thread_concurrency(len(calls), concurrency_limit)
    if effective_limit >= len(calls):
        return list(await asyncio.gather(*(run_blocking(fn, *fn_args, **fn_kwargs) for fn, fn_args, fn_kwargs in calls)))

    semaphore = asyncio.Semaphore(effective_limit)

    async def _run_one(call: tuple[Callable[..., Any], tuple[object, ...], dict[str, object]]) -> Any:
        fn, fn_args, fn_kwargs = call
        async with semaphore:
            return await run_blocking(fn, *fn_args, **fn_kwargs)

    tasks = [asyncio.create_task(_run_one(call)) for call in calls]
    return list(await asyncio.gather(*tasks))
