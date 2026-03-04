import unittest

from core.domain import ProfileEntity
from core.filters import FilterPipeline
from core.filters.builtins import AnomalyFilter, ConfidenceFilter, DuplicateFilter


class TestFilterPipeline(unittest.TestCase):
    def test_pipeline_applies_filters_in_order(self):
        entities = [
            ProfileEntity(
                id="p1",
                value="alice",
                source="github",
                confidence=0.9,
                attributes={"status": "FOUND"},
                platform="github",
                profile_url="https://github.com/alice",
                status="FOUND",
            ),
            ProfileEntity(
                id="p2",
                value="alice",
                source="github",
                confidence=0.4,
                attributes={"status": "FOUND"},
                platform="github",
                profile_url="https://github.com/alice",
                status="FOUND",
            ),
            ProfileEntity(
                id="p3",
                value="alice",
                source="reddit",
                confidence=0.35,
                attributes={"status": "ERROR"},
                platform="reddit",
                profile_url="https://reddit.com/u/alice",
                status="ERROR",
            ),
        ]

        pipeline = FilterPipeline([DuplicateFilter(), ConfidenceFilter(), AnomalyFilter()])
        result = pipeline.run(entities, {"target": "alice", "min_confidence": 0.3})

        self.assertEqual(len([item for item in result if item.entity_type == "profile"]), 2)
        self.assertTrue(any(item.entity_type == "asset" for item in result))


if __name__ == "__main__":
    unittest.main()
