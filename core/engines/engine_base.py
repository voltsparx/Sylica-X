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

"""Base execution helpers for strict timeout/failure isolation."""

from __future__ import annotations

import abc
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from time import perf_counter
from typing import Any

from core.engines.engine_result import EngineResult
from core.engines.health_monitor import EngineHealthMonitor


class EngineBase(abc.ABC):
    """Base contract for Silica-X execution engines."""

    def __init__(self, *, monitor: EngineHealthMonitor | None = None) -> None:
        self._monitor = monitor or EngineHealthMonitor()

    @abc.abstractmethod
    async def run(
        self,
        tasks: Sequence[Callable[[], Awaitable[Any]]],
        context: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Run tasks and return compatibility payloads."""

    async def run_detailed(
        self,
        tasks: Sequence[Callable[[], Awaitable[Any]]],
        context: dict[str, Any] | None = None,
    ) -> list[EngineResult]:
        """Run tasks and return standardized engine results."""

        timeout_raw = (context or {}).get("timeout")
        timeout = float(timeout_raw) if isinstance(timeout_raw, (int, float)) and float(timeout_raw) > 0 else None
        results: list[EngineResult] = []
        for index, task in enumerate(tasks, start=1):
            name = self._task_name(task, index=index)
            self._monitor.begin()
            start = perf_counter()
            try:
                outcome = await self.timeout_guard(task(), timeout=timeout)
            except TimeoutError as exc:
                result = EngineResult(
                    name=name,
                    status="timeout",
                    data={},
                    error=str(exc),
                    execution_time=perf_counter() - start,
                )
            except Exception as exc:  # pragma: no cover - defensive boundary
                result = EngineResult(
                    name=name,
                    status="failed",
                    data={},
                    error=str(exc),
                    execution_time=perf_counter() - start,
                )
            else:
                result = EngineResult(
                    name=name,
                    status="success",
                    data={"payload": outcome},
                    error=None,
                    execution_time=perf_counter() - start,
                )
            finally:
                self._monitor.end()
            self._monitor.record(result)
            results.append(result)
        return results

    async def timeout_guard(self, awaitable: Awaitable[Any], timeout: float | None) -> Any:
        """Apply hard timeout guard to an awaitable."""

        if timeout is None:
            return await awaitable
        try:
            return await asyncio.wait_for(awaitable, timeout=float(timeout))
        except TimeoutError as exc:  # pragma: no cover - event-loop boundary
            raise TimeoutError(f"Execution timed out after {timeout} seconds.") from exc

    def exception_isolation(
        self,
        func: Callable[..., Any],
        *args: object,
        **kwargs: object,
    ) -> tuple[Any | None, str | None]:
        """Isolate sync exceptions without raising upstream."""

        try:
            return func(*args, **kwargs), None
        except Exception as exc:  # pragma: no cover - defensive boundary
            return None, str(exc)

    def health_check(self) -> dict[str, Any]:
        """Expose current engine-health snapshot."""

        return self._monitor.snapshot().as_dict()

    async def shutdown(self) -> None:
        """Optional asynchronous shutdown hook for engines."""

    @staticmethod
    def _task_name(task_factory: Callable[[], Awaitable[Any]], *, index: int) -> str:
        explicit = str(getattr(task_factory, "_silica_x_task_name", "")).strip()  # noqa: SLF001
        if explicit:
            return explicit
        name = str(getattr(task_factory, "__name__", "")).strip()
        if name and name != "<lambda>":
            return name
        return f"task-{index}"
