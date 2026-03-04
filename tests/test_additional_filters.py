import unittest

from core.domain import AssetEntity, ProfileEntity
from core.filters.depth_filter import DepthFilter
from core.filters.keyword_filter import KeywordFilter
from core.filters.risk_filter import RiskFilter
from core.filters.scope_filter import ScopeFilter


class TestAdditionalFilters(unittest.TestCase):
    def test_scope_filter(self):
        items = [
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
            AssetEntity(
                id="a1",
                value="dev.example.com",
                source="certificate_transparency",
                confidence=0.8,
                attributes={},
                asset_kind="subdomain",
            ),
        ]
        filtered = ScopeFilter().apply(items, {"allowed_sources": ["github"]})
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].source, "github")

    def test_keyword_filter(self):
        items = [
            ProfileEntity(
                id="p1",
                value="alice",
                source="github",
                confidence=0.9,
                attributes={"bio": "security researcher"},
                platform="github",
                profile_url="https://github.com/alice",
                status="FOUND",
            )
        ]
        filtered = KeywordFilter().apply(items, {"keywords": ["security"]})
        self.assertEqual(len(filtered), 1)

    def test_risk_filter(self):
        items = [
            AssetEntity(
                id="a1",
                value="api token leaked",
                source="mock",
                confidence=0.6,
                attributes={},
                asset_kind="note",
            )
        ]
        filtered = RiskFilter().apply(items, {})
        self.assertEqual(len(filtered), 0)

    def test_depth_filter(self):
        items = [
            ProfileEntity(
                id=f"p{idx}",
                value=f"user{idx}",
                source="github",
                confidence=0.9,
                attributes={},
                platform="github",
                profile_url=f"https://github.com/user{idx}",
                status="FOUND",
            )
            for idx in range(80)
        ]
        filtered = DepthFilter().apply(items, {"depth": 2})
        self.assertEqual(len(filtered), 60)


if __name__ == "__main__":
    unittest.main()
