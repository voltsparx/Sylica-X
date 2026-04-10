import unittest
from pathlib import Path

from core.foundation.surface_wordlists import (
    SURFACE_COMMON_WEB_PATHS,
    SURFACE_PRIORITY_SUBDOMAIN_LABELS,
    SURFACE_TOP_PORTS,
    build_surface_wordlist_guidance,
    matched_surface_subdomain_labels,
    prioritize_surface_subdomains,
)


class TestSurfaceWordlists(unittest.TestCase):
    def test_framework_attack_surface_wordlist_files_exist(self):
        wordlist_root = Path(__file__).resolve().parents[1] / "wordlists" / "attack_surface"
        self.assertTrue((wordlist_root / "subdomains_small.txt").exists())
        self.assertTrue((wordlist_root / "paths_common.txt").exists())
        self.assertTrue((wordlist_root / "ports_top100.txt").exists())

    def test_prioritize_surface_subdomains_prefers_curated_labels(self):
        hosts = ["misc.example.com", "portal.example.com", "api.example.com"]
        prioritized = prioritize_surface_subdomains(hosts)
        self.assertEqual(prioritized[:2], ["api.example.com", "portal.example.com"])

    def test_matched_surface_subdomain_labels_deduplicates_labels(self):
        labels = matched_surface_subdomain_labels(
            ["api.example.com", "api.internal.example.com", "portal.example.com"]
        )
        self.assertEqual(labels, ["api", "portal"])

    def test_build_surface_wordlist_guidance_returns_framework_lists(self):
        guidance = build_surface_wordlist_guidance(["api.example.com", "misc.example.com"])
        self.assertIn("api", guidance["matched_priority_labels"])
        self.assertEqual(guidance["common_paths"][0], SURFACE_COMMON_WEB_PATHS[0])
        self.assertEqual(guidance["top_ports"][0], SURFACE_TOP_PORTS[0])
        self.assertIn("www", SURFACE_PRIORITY_SUBDOMAIN_LABELS)


if __name__ == "__main__":
    unittest.main()
