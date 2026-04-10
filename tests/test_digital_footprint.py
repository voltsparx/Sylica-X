import unittest

from core.analyze.digital_footprint import build_digital_footprint_map
from core.domain import ProfileEntity
from core.runner import _analyze_intelligence_bundle


class TestDigitalFootprintMap(unittest.TestCase):
    def test_build_digital_footprint_map_summarizes_profile_and_surface_signals(self):
        bundle = {
            "entity_facets": {
                "emails": ["alice@example.com"],
                "phones": ["+15551234567"],
                "names": ["Alice Example"],
                "mentions": ["alice", "alice_ops"],
            }
        }
        profile_results = [
            {
                "platform": "GitHub",
                "url": "https://github.com/alice",
                "status": "FOUND",
                "confidence": 91,
                "contacts": {"emails": ["alice@example.com"], "phones": []},
                "links": ["https://blog.example.com", "https://status.example.net"],
                "mentions": ["alice_ops"],
            },
            {
                "platform": "Mastodon",
                "url": "https://social.example/@alice",
                "status": "FOUND",
                "confidence": 84,
                "contacts": {"emails": [], "phones": ["+1 (555) 123-4567"]},
                "links": ["https://example.com/about"],
                "mentions": ["alice"],
            },
        ]
        domain_result = {
            "target": "example.com",
            "resolved_addresses": ["1.1.1.1"],
            "subdomains": ["api.example.com", "status.example.com"],
        }
        issues = [
            {
                "severity": "HIGH",
                "title": "Recovery contact exposed",
                "scope": "profile",
                "evidence": "Public profile lists a recovery mailbox.",
            }
        ]

        footprint_map = build_digital_footprint_map(
            target="alice",
            mode="fusion",
            profile_results=profile_results,
            domain_result=domain_result,
            issues=issues,
            intelligence_bundle=bundle,
        )

        self.assertEqual(footprint_map["summary"]["profile_count"], 2)
        self.assertEqual(footprint_map["linked_infrastructure"]["primary_domain"], "example.com")
        self.assertIn("blog.example.com", footprint_map["linked_infrastructure"]["external_domains"])
        self.assertIn("alice@example.com", footprint_map["watchlist"]["emails"])
        self.assertIn("alice", footprint_map["watchlist"]["handles"])
        self.assertTrue(footprint_map["live_monitoring"]["ready"])
        self.assertTrue(footprint_map["threat_indicators"])

    def test_analyze_intelligence_bundle_attaches_footprint_map(self):
        entities = [
            ProfileEntity(
                id="profile-1",
                value="alice",
                source="github",
                confidence=0.9,
                attributes={"status": "FOUND", "platform_count": 1},
                platform="github",
                profile_url="https://github.com/alice",
                status="FOUND",
            )
        ]

        bundle = _analyze_intelligence_bundle(
            entities,
            mode="profile",
            target="alice",
            issues=[
                {
                    "severity": "MEDIUM",
                    "title": "Public contact exposed",
                    "scope": "profile",
                    "evidence": "Email reuse across collected profiles.",
                }
            ],
            profile_results=[
                {
                    "platform": "GitHub",
                    "url": "https://github.com/alice",
                    "status": "FOUND",
                    "confidence": 90,
                    "contacts": {"emails": ["alice@example.com"], "phones": []},
                    "links": ["https://example.com"],
                    "mentions": ["alice"],
                }
            ],
        )

        self.assertIn("footprint_map", bundle)
        self.assertEqual(bundle["footprint_map"]["summary"]["profile_count"], 1)


if __name__ == "__main__":
    unittest.main()
