"""Hybrid parallel execution engine (async + threads + CPU tasks)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import os
from typing import Any

from core.async_engine import DEFAULT_ASYNC_CONCURRENCY, run_async_batch
from core.thread_engine import DEFAULT_THREAD_WORKERS, run_blocking_batch


BlockingCall = tuple[Callable[..., Any], tuple[object, ...], dict[str, object]]


@dataclass(frozen=True)
class ParallelRunResult:
    """Structured results from the hybrid engine."""

    async_results: tuple[object, ...]
    thread_results: tuple[object, ...]
    cpu_results: tuple[object, ...]

    def as_dict(self) -> dict[str, list[object]]:
        return {
            "async_results": list(self.async_results),
            "thread_results": list(self.thread_results),
            "cpu_results": list(self.cpu_results),
        }


def _execute_call(call: BlockingCall) -> Any:
    fn, args, kwargs = call
    return fn(*args, **kwargs)


class ParallelEngine:
    """Run async, blocking, and CPU-heavy work in one orchestration."""

    def __init__(
        self,
        *,
        async_concurrency: int = DEFAULT_ASYNC_CONCURRENCY,
        thread_concurrency: int = DEFAULT_THREAD_WORKERS,
        cpu_workers: int | None = None,
    ) -> None:
        self.async_concurrency = max(1, int(async_concurrency))
        self.thread_concurrency = max(1, int(thread_concurrency))
        self.cpu_workers = max(1, int(cpu_workers or (os.cpu_count() or 2)))

    async def run_hybrid(
        self,
        *,
        async_tasks: Sequence[Awaitable[object]] | None = None,
        thread_calls: Sequence[BlockingCall] | None = None,
        cpu_calls: Sequence[BlockingCall] | None = None,
    ) -> ParallelRunResult:
        """Execute hybrid workload concurrently with bounded resources."""

        async_tasks = list(async_tasks or [])
        thread_calls = list(thread_calls or [])
        cpu_calls = list(cpu_calls or [])

        async_phase = asyncio.create_task(
            run_async_batch(
                async_tasks,
                concurrency_limit=self.async_concurrency,
                return_exceptions=True,
            )
        )
        thread_phase = asyncio.create_task(
            run_blocking_batch(
                list(thread_calls),
                concurrency_limit=self.thread_concurrency,
            )
        )
        cpu_phase = asyncio.create_task(self._run_cpu_batch(cpu_calls))

        async_results_raw, thread_results_raw, cpu_results_raw = await asyncio.gather(
            async_phase,
            thread_phase,
            cpu_phase,
        )

        return ParallelRunResult(
            async_results=tuple(async_results_raw),
            thread_results=tuple(thread_results_raw),
            cpu_results=tuple(cpu_results_raw),
        )

    async def _run_cpu_batch(self, calls: Sequence[BlockingCall]) -> list[object]:
        if not calls:
            return []

        loop = asyncio.get_running_loop()
        results: list[object] = []
        # ProcessPool speeds up CPU-bound jobs when callables are picklable.
        with ProcessPoolExecutor(max_workers=self.cpu_workers) as pool:
            tasks = [loop.run_in_executor(pool, _execute_call, call) for call in calls]
            batch = await asyncio.gather(*tasks, return_exceptions=True)

        for item, call in zip(batch, calls):
            if isinstance(item, Exception):
                # Fall back to in-process execution for non-picklable callables.
                try:
                    results.append(_execute_call(call))
                except Exception as fallback_exc:  # pragma: no cover - defensive guard
                    results.append(fallback_exc)
            else:
                results.append(item)
        return results
