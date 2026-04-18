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

import asyncio
import unittest

from core.engine_manager import AsyncEngine
from core.engines.engine_result import EngineResult
from core.engines.health_monitor import EngineHealthMonitor


class TestEngineRuntime(unittest.TestCase):
    def test_engine_result_schema(self):
        result = EngineResult(
            name="username_lookup",
            status="success",
            data={"payload": {"value": "alice"}},
            error=None,
            execution_time=0.031,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.name, "username_lookup")
        self.assertEqual(result.status, "success")
        self.assertIn("payload", result.data)

    def test_health_monitor_tracks_failures(self):
        monitor = EngineHealthMonitor()
        monitor.record(EngineResult(name="task_a", status="success", data={"payload": 1}, execution_time=0.2))
        monitor.record(EngineResult(name="task_a", status="failed", data={}, error="boom", execution_time=0.5))
        monitor.record(EngineResult(name="task_b", status="timeout", data={}, error="timeout", execution_time=0.7))
        snapshot = monitor.snapshot().as_dict()
        self.assertEqual(snapshot["failed_engines"], 2)
        self.assertGreater(snapshot["average_response_time"], 0.0)
        self.assertEqual(snapshot["engine_failure_counts"]["task_a"], 1)
        self.assertEqual(snapshot["engine_failure_counts"]["task_b"], 1)

    def test_async_engine_run_detailed_isolates_timeout(self):
        async def _ok():
            return {"value": "ok"}

        async def _slow():
            await asyncio.sleep(0.05)
            return {"value": "slow"}

        engine = AsyncEngine()
        task_ok = lambda: _ok()
        setattr(task_ok, "_silica_x_task_name", "ok_task")
        task_slow = lambda: _slow()
        setattr(task_slow, "_silica_x_task_name", "slow_task")

        results = asyncio.run(
            engine.run_detailed(
                [task_ok, task_slow],
                {"max_workers": 2, "timeout": 0.01},
            )
        )
        status_map = {item.name: item.status for item in results}
        self.assertEqual(status_map["ok_task"], "success")
        self.assertEqual(status_map["slow_task"], "timeout")

        health = engine.health_check()
        self.assertGreaterEqual(int(health.get("failed_engines", 0)), 1)


if __name__ == "__main__":
    unittest.main()

