import unittest

from core.extensions.control_plane import merge_scan_modes, resolve_extension_control


class TestExtensionControlPlane(unittest.TestCase):
    def test_auto_profile_fast_returns_defaults(self):
        plan = resolve_extension_control(
            scope="profile",
            scan_mode="fast",
            control_mode="auto",
            requested_plugins=[],
            requested_filters=[],
            include_all_plugins=False,
            include_all_filters=False,
        )
        self.assertEqual(plan.scan_mode, "fast")
        self.assertEqual(plan.control_mode, "auto")
        self.assertTrue(plan.plugins)
        self.assertTrue(plan.filters)
        self.assertEqual(plan.errors, ())

    def test_auto_rejects_manual_flags(self):
        plan = resolve_extension_control(
            scope="profile",
            scan_mode="balanced",
            control_mode="auto",
            requested_plugins=["threat_conductor"],
            requested_filters=[],
            include_all_plugins=False,
            include_all_filters=False,
        )
        self.assertTrue(any("Auto extension control" in item for item in plan.errors))

    def test_manual_unknown_selector_errors(self):
        plan = resolve_extension_control(
            scope="surface",
            scan_mode="balanced",
            control_mode="manual",
            requested_plugins=["unknown_plugin_name"],
            requested_filters=["unknown_filter_name"],
            include_all_plugins=False,
            include_all_filters=False,
        )
        self.assertTrue(any("Unknown plugin selector" in item for item in plan.errors))
        self.assertTrue(any("Unknown filter selector" in item for item in plan.errors))

    def test_manual_conflict_filter_errors(self):
        plan = resolve_extension_control(
            scope="fusion",
            scan_mode="max",
            control_mode="manual",
            requested_plugins=[],
            requested_filters=["pii_signal_classifier", "sensitive_lexicon_guard"],
            include_all_plugins=False,
            include_all_filters=False,
        )
        self.assertTrue(any("Filter conflict" in item for item in plan.errors))

    def test_hybrid_conflict_auto_resolves_with_warning(self):
        plan = resolve_extension_control(
            scope="fusion",
            scan_mode="max",
            control_mode="hybrid",
            requested_plugins=["identity_fusion_core"],
            requested_filters=[],
            include_all_plugins=False,
            include_all_filters=False,
        )
        self.assertTrue(any("Plugin conflict resolved" in item for item in plan.warnings))
        self.assertNotIn("identity_fusion_core", plan.plugins)

    def test_merge_scan_modes(self):
        self.assertEqual(merge_scan_modes("quick", "balanced"), "balanced")
        self.assertEqual(merge_scan_modes("deep", "max"), "max")


if __name__ == "__main__":
    unittest.main()
