"""Engine selection and runtime backend adapters for orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Protocol

from core.execution_policy import ExecutionPolicy, load_execution_policy
from core.engines.async_engine import run_async_batch
from core.engines.parallel_engine import ParallelEngine
from core.engines.thread_engine import run_blocking
from core.utils.logging import get_logger


LOGGER = get_logger("engine_manager")
AsyncTaskFactory = Callable[[], Awaitable[Any]]


class ExecutionEngine(Protocol):
    """Execution backend contract."""

    async def run(
        self,
        tasks: Sequence[AsyncTaskFactory],
        context: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        """Execute async task factories and return ordered results."""


async def _run_with_timeout(task_factory: AsyncTaskFactory, timeout: int | None) -> Any:
    coroutine = task_factory()
    if timeout and timeout > 0:
        return await asyncio.wait_for(coroutine, timeout=float(timeout))
    return await coroutine


def _resolve_timeout(runtime: Mapping[str, Any]) -> int | None:
    raw_timeout = runtime.get("timeout")
    if not isinstance(raw_timeout, (int, float)):
        return None
    timeout = int(raw_timeout)
    return timeout if timeout > 0 else None


class AsyncEngine:
    """Native async execution backend."""

    async def run(
        self,
        tasks: Sequence[AsyncTaskFactory],
        context: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        runtime = dict(context or {})
        max_workers = max(1, int(runtime.get("max_workers", 10)))
        timeout = _resolve_timeout(runtime)
        wrapped = [_run_with_timeout(task_factory, timeout) for task_factory in tasks]
        return list(
            await run_async_batch(
                wrapped,
                concurrency_limit=max_workers,
                return_exceptions=True,
            )
        )


class ThreadEngine:
    """Thread-backed execution backend for blocking environments."""

    async def _execute_one(self, task_factory: AsyncTaskFactory, timeout: int | None) -> Any:
        def _runner() -> Any:
            coroutine = task_factory()
            if timeout and timeout > 0:
                return asyncio.run(asyncio.wait_for(coroutine, timeout=float(timeout)))
            return asyncio.run(coroutine)

        return await run_blocking(_runner)

    async def run(
        self,
        tasks: Sequence[AsyncTaskFactory],
        context: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        runtime = dict(context or {})
        max_workers = max(1, int(runtime.get("max_workers", 10)))
        timeout = _resolve_timeout(runtime)
        calls = [self._execute_one(task_factory, timeout) for task_factory in tasks]
        return list(
            await run_async_batch(
                calls,
                concurrency_limit=max_workers,
                return_exceptions=True,
            )
        )


class ProcessEngine:
    """Process-backed interface with safe fallback for non-picklable callables."""

    _fallback_engine = AsyncEngine()

    async def run(
        self,
        tasks: Sequence[AsyncTaskFactory],
        context: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        LOGGER.warning("ProcessEngine is using async fallback for callable compatibility.")
        return await self._fallback_engine.run(tasks=tasks, context=context)


class HybridEngine:
    """Hybrid backend using the shared parallel engine."""

    def __init__(self) -> None:
        self._parallel = ParallelEngine()

    async def run(
        self,
        tasks: Sequence[AsyncTaskFactory],
        context: Mapping[str, Any] | None = None,
    ) -> list[Any]:
        runtime = dict(context or {})
        timeout = _resolve_timeout(runtime)
        async_tasks = [_run_with_timeout(task_factory, timeout) for task_factory in tasks]
        batch = await self._parallel.run_hybrid(async_tasks=async_tasks)
        return [*batch.async_results, *batch.thread_results, *batch.cpu_results]


def get_engine(profile: ExecutionPolicy | str) -> ExecutionEngine:
    """Resolve execution engine from policy object or profile name."""

    policy = load_execution_policy(profile) if isinstance(profile, str) else profile
    engine_type = policy.engine_type.strip().lower()
    if engine_type == "async":
        return AsyncEngine()
    if engine_type == "thread":
        return ThreadEngine()
    if engine_type == "process":
        return ProcessEngine()
    return HybridEngine()
