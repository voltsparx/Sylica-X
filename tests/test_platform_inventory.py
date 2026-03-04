import unittest

from core.analyze.profile_summary import summarize_target_intel
from core.collect.platform_schema import load_platforms


class TestPlatformInventory(unittest.TestCase):
    def test_platform_inventory_contains_seventy_sources(self):
        platforms = load_platforms("platforms")
        names = {row.name for row in platforms}

        self.assertGreaterEqual(len(platforms), 70)
        self.assertIn("About.me", names)
        self.assertIn("Academia.edu", names)
        self.assertIn("ArtStation", names)
        self.assertIn("CyberDefenders", names)
        self.assertIn("Disqus", names)

    def test_target_snapshot_contains_richer_metrics(self):
        payload = [
            {
                "platform": "GitHub",
                "url": "https://github.com/alice",
                "status": "FOUND",
                "confidence": 92,
                "contacts": {"emails": ["alice@example.com"], "phones": ["+1-111-111-1111"]},
                "mentions": ["alice", "alice-dev"],
                "links": ["https://blog.example.com/about", "https://x.com/alice"],
                "bio": "security engineer",
                "response_time_ms": 210,
            },
            {
                "platform": "Reddit",
                "url": "https://reddit.com/u/alice",
                "status": "FOUND",
                "confidence": 85,
                "contacts": {"emails": ["alice@work.example.com"], "phones": []},
                "mentions": ["alice_osint"],
                "links": ["https://work.example.com/team"],
                "bio": "researcher",
                "response_time_ms": 180,
            },
            {
                "platform": "SomeSite",
                "url": "https://somesite.example/alice",
                "status": "ERROR",
                "response_time_ms": 450,
                "context": "rate limited",
            },
        ]

        summary = summarize_target_intel(payload)
        self.assertEqual(summary["total_results"], 3)
        self.assertEqual(summary["found_count"], 2)
        self.assertEqual(summary["error_count"], 1)
        self.assertGreater(summary["coverage_ratio"], 0.6)
        self.assertIn("example.com:1", summary["email_domains"])
        self.assertIn("work.example.com:1", summary["email_domains"])
        self.assertTrue(summary["external_link_domains"])
        self.assertIn("FOUND", summary["status_breakdown"])


if __name__ == "__main__":
    unittest.main()
