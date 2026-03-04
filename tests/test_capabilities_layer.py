import asyncio
import unittest

from core.capabilities.domain_enumeration import DomainEnumerationCapability
from core.capabilities.username_lookup import UsernameLookupCapability
from core.domain import DomainEntity, ProfileEntity


class _FakeProfileAdapter:
    async def collect(self, **kwargs):
        return [
            ProfileEntity(
                id="profile-1",
                value="alice",
                source="github",
                confidence=0.85,
                attributes={"status": "FOUND"},
                platform="github",
                profile_url="https://github.com/alice",
                status="FOUND",
            )
        ]


class _FakeDomainAdapter:
    async def collect(self, **kwargs):
        return [
            DomainEntity(
                id="domain-1",
                value="example.com",
                source="surface",
                confidence=0.8,
                attributes={},
                domain="example.com",
            )
        ]


class TestCapabilities(unittest.TestCase):
    def test_username_lookup_capability_returns_entities(self):
        capability = UsernameLookupCapability(adapter=_FakeProfileAdapter())
        results = asyncio.run(
            capability.execute(
                "alice",
                {
                    "mode": "profile",
                    "timeout": 10,
                    "max_workers": 5,
                    "source_profile": "fast",
                    "max_platforms": 25,
                    "proxy_url": None,
                },
            )
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_type, "profile")

    def test_domain_enumeration_capability_returns_entities(self):
        capability = DomainEnumerationCapability(adapter=_FakeDomainAdapter())
        results = asyncio.run(
            capability.execute(
                "example.com",
                {
                    "mode": "surface",
                    "timeout": 12,
                    "include_ct": True,
                    "include_rdap": True,
                    "max_subdomains": 100,
                },
            )
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entity_type, "domain")


if __name__ == "__main__":
    unittest.main()
