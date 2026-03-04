import asyncio
import unittest

from core.capabilities.base import Capability
from core.domain import BaseEntity, ProfileEntity
from core.orchestrator import Orchestrator


class _MockUsernameCapability(Capability):
    capability_id = "username_lookup"

    async def execute(self, target: str, context):
        return [
            ProfileEntity(
                id="profile-mock-1",
                value=target,
                source="mock",
                confidence=0.92,
                attributes={"status": "FOUND"},
                platform="mock",
                profile_url=f"https://mock.local/{target}",
                status="FOUND",
            )
        ]

    def supported_entities(self) -> tuple[type[BaseEntity], ...]:
        return (ProfileEntity,)


class TestOrchestratorLayer(unittest.TestCase):
    def test_orchestrator_runs_end_to_end(self):
        orchestrator = Orchestrator(target="alice", mode="profile", config={"profile": "fast"})
        orchestrator._capabilities = {"username_lookup": _MockUsernameCapability()}  # noqa: SLF001

        payload = asyncio.run(orchestrator.run())

        self.assertEqual(payload["target"], "alice")
        self.assertEqual(payload["mode"], "profile")
        self.assertIn("fused", payload)
        self.assertGreaterEqual(payload["fused"]["entity_count"], 1)
        self.assertIn("advisory", payload)
        self.assertIn("lifecycle", payload)


if __name__ == "__main__":
    unittest.main()
