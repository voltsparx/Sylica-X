import unittest

from core.domain import AssetEntity, DomainEntity, EmailEntity, ProfileEntity
from core.fusion.confidence_engine import aggregate_confidence_score
from core.fusion.correlator import correlate_entities
from core.fusion.deduplicator import deduplicate_entities
from core.fusion.graph_builder import build_relationship_graph


class TestFusionComponents(unittest.TestCase):
    def test_deduplicate_entities(self):
        entities = [
            ProfileEntity(
                id="p1",
                value="alice",
                source="github",
                confidence=0.9,
                attributes={},
                platform="github",
                profile_url="https://github.com/alice",
                status="FOUND",
            ),
            ProfileEntity(
                id="p1",
                value="alice",
                source="github",
                confidence=0.85,
                attributes={},
                platform="github",
                profile_url="https://github.com/alice",
                status="FOUND",
            ),
        ]
        deduped = deduplicate_entities(entities)
        self.assertEqual(len(deduped), 1)

    def test_correlator_and_graph_builder(self):
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
                relationships=("profile-1",),
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
                confidence=0.72,
                attributes={"parent_domain": "example.com"},
                asset_kind="subdomain",
            ),
        ]

        relation_map = correlate_entities(entities)
        self.assertIn("email-1", relation_map)
        self.assertIn("profile-1", relation_map.get("email-1", []))
        self.assertIn("domain-1", relation_map.get("asset-1", []))

        graph = build_relationship_graph(entities, relation_map)
        self.assertEqual(len(graph["nodes"]), 4)
        self.assertGreaterEqual(len(graph["edges"]), 2)

        confidence = aggregate_confidence_score(entities, relation_map)
        self.assertGreater(confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
