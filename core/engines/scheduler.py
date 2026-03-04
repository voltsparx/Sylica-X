"""Scheduler and automation helpers for recurring scan workflows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import time
from typing import Any, Callable

from core.thread_engine import run_blocking


@dataclass
class ScheduledJob:
    scan_func: Callable[[str], Any]
    target: str
    interval_seconds: int
    next_run_at: float


@dataclass
class Scheduler:
    jobs: list[ScheduledJob] = field(default_factory=list)

    def schedule_scan(self, scan_func: Callable[[str], Any], target: str, interval_seconds: int) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        self.jobs.append(
            ScheduledJob(
                scan_func=scan_func,
                target=target,
                interval_seconds=int(interval_seconds),
                next_run_at=time.time() + int(interval_seconds),
            )
        )

    def merge_results(self, historical: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        merged = dict(historical)
        for key, value in new.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self.merge_results(merged[key], value)
            else:
                merged[key] = value
        return merged

    async def run_pending(self, *, now: float | None = None) -> list[dict[str, Any]]:
        run_at = time.time() if now is None else float(now)
        executed: list[dict[str, Any]] = []

        for job in self.jobs:
            if job.next_run_at > run_at:
                continue

            try:
                result = job.scan_func(job.target)
                if asyncio.iscoroutine(result):
                    payload = await result
                else:
                    payload = await run_blocking(lambda value: value, result)
                executed.append({"target": job.target, "ok": True, "result": payload})
            except Exception as exc:  # pragma: no cover - scheduling safety
                executed.append({"target": job.target, "ok": False, "error": str(exc)})
            finally:
                job.next_run_at = run_at + job.interval_seconds

        return executed

    def send_alert(self, target: str, findings: dict[str, Any]) -> str:
        score = findings.get("risk_score") if isinstance(findings, dict) else None
        return f"[alert] target={target} risk_score={score if score is not None else '-'}"
