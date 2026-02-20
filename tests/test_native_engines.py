import unittest

from core.async_engine import ASYNC_TASKS, recommend_async_concurrency
from core.thread_engine import THREAD_TASKS, WORKFLOWS, recommend_thread_concurrency, workflow_plan


class TestNativeEngines(unittest.TestCase):
    def test_workflow_async_keys_exist(self):
        for workflow_name, phases in WORKFLOWS.items():
            for task in phases.get("async", []):
                self.assertIn(task, ASYNC_TASKS, msg=f"{workflow_name}: missing async task '{task}'")

    def test_workflow_thread_keys_exist(self):
        for workflow_name, phases in WORKFLOWS.items():
            for task in phases.get("threads", []):
                self.assertIn(task, THREAD_TASKS, msg=f"{workflow_name}: missing thread task '{task}'")

    def test_workflow_plan_returns_three_phases(self):
        plan = workflow_plan("profile")
        self.assertEqual(set(plan.keys()), {"async", "threads", "sync"})
        self.assertGreater(len(plan["async"]), 0)
        self.assertGreater(len(plan["threads"]), 0)
        self.assertGreater(len(plan["sync"]), 0)

    def test_recommend_async_concurrency_bounds(self):
        self.assertEqual(recommend_async_concurrency(0, 50), 1)
        self.assertEqual(recommend_async_concurrency(3, 50), 3)
        self.assertEqual(recommend_async_concurrency(20, 5), 5)

    def test_recommend_thread_concurrency_bounds(self):
        self.assertEqual(recommend_thread_concurrency(0, 50), 1)
        self.assertEqual(recommend_thread_concurrency(4, 10), 4)
        self.assertEqual(recommend_thread_concurrency(50, 8), 8)


if __name__ == "__main__":
    unittest.main()
