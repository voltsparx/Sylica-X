import unittest

from core.domain import AssetEntity, DomainEntity, EmailEntity, ProfileEntity
from core.fusion import FusionEngine


class TestFusionEngineLayer(unittest.TestCase):
    def test_fusion_builds_graph_and_anomalies(self):
        entities = [
            ProfileEntity(
                id="profile-1",
                value="alice",
                source="github",
                confidence=0.9,
                attributes={"status": "FOUND"},
                platform="github",
                profile_url="https://github.com/alice",
                status="FOUND",
            ),
            EmailEntity(
                id="email-1",
                value="alice@example.com",
                source="github",
                confidence=0.7,
                attributes={"owner": "alice"},
                email_domain="example.com",
            ),
            DomainEntity(
                id="domain-1",
                value="example.com",
                source="surface",
                confidence=0.8,
                attributes={},
                domain="example.com",
            ),
            AssetEntity(
                id="asset-1",
                value="dev.example.com",
                source="certificate_transparency",
                confidence=0.75,
                attributes={"parent_domain": "example.com", "status": "ERROR"},
                asset_kind="subdomain",
            ),
        ]

        engine = FusionEngine()
        fused = engine.fuse(entities)

        self.assertEqual(fused["entity_count"], 4)
        self.assertGreater(fused["confidence_score"], 0)
        self.assertGreaterEqual(len(fused["anomalies"]), 1)
        self.assertGreaterEqual(len(fused["graph"]["nodes"]), 4)
        self.assertGreaterEqual(len(fused["graph"]["edges"]), 2)


if __name__ == "__main__":
    unittest.main()
