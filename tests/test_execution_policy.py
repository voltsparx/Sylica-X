import unittest

from core.execution_policy import SCAN_PROFILES, load_execution_policy, normalize_profile_name
from core.engine_manager import AsyncEngine, HybridEngine, get_engine


class TestExecutionPolicy(unittest.TestCase):
    def test_profile_alias_normalization(self):
        self.assertEqual(normalize_profile_name("quick"), "fast")
        self.assertEqual(normalize_profile_name("FAST"), "fast")
        self.assertEqual(normalize_profile_name("unknown"), "balanced")

    def test_load_execution_policy_defaults_balanced(self):
        policy = load_execution_policy("not-real")
        self.assertEqual(policy.name, "balanced")
        self.assertGreater(policy.max_workers, 0)

    def test_scan_profiles_have_required_levels(self):
        self.assertIn("fast", SCAN_PROFILES)
        self.assertIn("balanced", SCAN_PROFILES)
        self.assertIn("deep", SCAN_PROFILES)
        self.assertIn("max", SCAN_PROFILES)

    def test_engine_manager_selects_expected_types(self):
        self.assertIsInstance(get_engine("fast"), AsyncEngine)
        self.assertIsInstance(get_engine("balanced"), HybridEngine)


if __name__ == "__main__":
    unittest.main()
