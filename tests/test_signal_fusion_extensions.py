import unittest
from unittest.mock import patch

from filters.signal_lane_fusion import run as run_signal_lane_filter
from plugins.signal_fusion_core import run as run_signal_fusion_plugin


class TestSignalFusionExtensions(unittest.TestCase):
    def test_signal_fusion_core_plugin_returns_normalized_payload(self):
        fake_fusion = {
            "mode": "fusion",
            "username": "alice",
            "domain": "example.com",
            "coverage": {"detected": 7, "executable": 3, "planned": 2, "executed": 2, "successful": 2},
            "signals": {
                "emails": ["alice@example.com"],
                "urls": ["https://example.com/u/alice"],
                "ips": ["1.1.1.1"],
                "domains": ["example.com", "api.example.com"],
                "subdomains": ["api.example.com"],
                "username_mentions": ["alice"],
            },
            "detected_tools": [],
            "tool_runs": [],
        }
        fake_summary = {
            "framework_count": 7,
            "module_count": 1000,
            "kind_counts": {"plugin": 700, "filter": 300},
            "scope_counts": {"profile": 500, "surface": 800, "fusion": 650},
        }

        with (
            patch("plugins.signal_fusion_core.collect_source_fusion_intel", return_value=fake_fusion),
            patch("plugins.signal_fusion_core.ensure_module_catalog", return_value={"modules": []}),
            patch("plugins.signal_fusion_core.summarize_module_catalog", return_value=fake_summary),
        ):
            payload = run_signal_fusion_plugin(
                {
                    "mode": "fusion",
                    "target": "alice",
                    "domain_result": {"target": "example.com"},
                }
            )

        self.assertIn(payload["severity"], {"INFO", "MEDIUM", "HIGH"})
        self.assertIn("fusion_intel", payload["data"])
        self.assertEqual(payload["data"]["catalog_summary"]["module_count"], 1000)

    def test_signal_lane_fusion_filter_routes_lanes(self):
        payload = run_signal_lane_filter(
            {
                "plugins": [
                    {
                        "id": "signal_fusion_core",
                        "data": {
                            "fusion_intel": {
                                "signals": {
                                    "emails": ["alice@example.com", "alice@example.com"],
                                    "urls": ["https://example.com"],
                                    "ips": ["8.8.8.8"],
                                    "domains": ["example.com", "api.example.com"],
                                    "subdomains": ["api.example.com"],
                                    "username_mentions": ["alice"],
                                }
                            }
                        },
                    }
                ]
            }
        )

        self.assertIn(payload["severity"], {"INFO", "MEDIUM", "HIGH"})
        self.assertIn("signals", payload["data"])
        self.assertIn("lanes", payload["data"])
        self.assertIn("identity-correlation-lane", payload["data"]["lanes"])
        self.assertIn("infrastructure-surface-lane", payload["data"]["lanes"])


if __name__ == "__main__":
    unittest.main()
