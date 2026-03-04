import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.extensions.signal_forge import execute_plugins, list_plugin_discovery_errors
from core.extensions.signal_sieve import execute_filters, list_filter_discovery_errors


class TestExtensionArchitecture(unittest.TestCase):
    def test_plugin_execution_imports_by_module_name_not_public_id(self):
        fake_module = SimpleNamespace(
            PLUGIN_SPEC={
                "id": "public_plugin_id",
                "title": "Public Plugin",
                "scopes": ["profile"],
            },
            run=lambda context: {
                "summary": "ok",
                "severity": "INFO",
                "highlights": [],
                "data": {},
            },
        )
        calls: list[str] = []

        def loader(name: str):
            calls.append(name)
            if name != "module_file":
                raise RuntimeError(f"unexpected import: {name}")
            return fake_module

        with (
            patch("core.extensions.signal_forge._iter_plugin_module_names", return_value=["module_file"]),
            patch("core.extensions.signal_forge._load_plugin_module", side_effect=loader),
        ):
            results, errors = execute_plugins(
                scope="profile",
                requested_plugins=["public_plugin_id"],
                include_all=False,
                context={"target": "alice", "mode": "profile"},
            )

        self.assertEqual(errors, [])
        self.assertEqual([row["id"] for row in results], ["public_plugin_id"])
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(calls[-1], "module_file")
        self.assertNotIn("public_plugin_id", calls)

    def test_filter_execution_imports_by_module_name_not_public_id(self):
        fake_module = SimpleNamespace(
            FILTER_SPEC={
                "id": "public_filter_id",
                "title": "Public Filter",
                "scopes": ["profile"],
            },
            run=lambda context: {
                "summary": "ok",
                "severity": "INFO",
                "highlights": [],
                "data": {},
            },
        )
        calls: list[str] = []

        def loader(name: str):
            calls.append(name)
            if name != "module_file":
                raise RuntimeError(f"unexpected import: {name}")
            return fake_module

        with (
            patch("core.extensions.signal_sieve._iter_filter_module_names", return_value=["module_file"]),
            patch("core.extensions.signal_sieve._load_filter_module", side_effect=loader),
        ):
            results, errors = execute_filters(
                scope="profile",
                requested_filters=["public_filter_id"],
                include_all=False,
                context={"target": "alice", "mode": "profile"},
            )

        self.assertEqual(errors, [])
        self.assertEqual([row["id"] for row in results], ["public_filter_id"])
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(calls[-1], "module_file")
        self.assertNotIn("public_filter_id", calls)

    def test_plugin_discovery_errors_are_reported(self):
        with (
            patch("core.extensions.signal_forge._iter_plugin_module_names", return_value=["broken_plugin"]),
            patch("core.extensions.signal_forge._load_plugin_module", side_effect=RuntimeError("boom")),
        ):
            errors = list_plugin_discovery_errors()
            _, exec_errors = execute_plugins(
                scope="profile",
                requested_plugins=["broken_plugin"],
                include_all=False,
                context={"target": "alice", "mode": "profile"},
            )

        self.assertTrue(any("broken_plugin" in error and "import failed" in error for error in errors))
        self.assertTrue(any("broken_plugin" in error and "import failed" in error for error in exec_errors))

    def test_filter_discovery_errors_are_reported(self):
        with (
            patch("core.extensions.signal_sieve._iter_filter_module_names", return_value=["broken_filter"]),
            patch("core.extensions.signal_sieve._load_filter_module", side_effect=RuntimeError("boom")),
        ):
            errors = list_filter_discovery_errors()
            _, exec_errors = execute_filters(
                scope="profile",
                requested_filters=["broken_filter"],
                include_all=False,
                context={"target": "alice", "mode": "profile"},
            )

        self.assertTrue(any("broken_filter" in error and "import failed" in error for error in errors))
        self.assertTrue(any("broken_filter" in error and "import failed" in error for error in exec_errors))


if __name__ == "__main__":
    unittest.main()


