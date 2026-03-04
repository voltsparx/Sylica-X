import unittest

from core.domain import BaseEntity, ProfileEntity, make_entity_id


class TestDomainEntities(unittest.TestCase):
    def test_make_entity_id_is_stable(self):
        first = make_entity_id("profile", "github", "alice")
        second = make_entity_id("profile", "github", "alice")
        self.assertEqual(first, second)

    def test_base_entity_clamps_confidence(self):
        entity = BaseEntity(
            id="base-1",
            value="x",
            source="test",
            confidence=5.0,
            attributes={"a": 1},
        )
        self.assertEqual(entity.confidence, 1.0)

    def test_attributes_are_mapping_proxy(self):
        entity = ProfileEntity(
            id="profile-1",
            value="alice",
            source="github",
            confidence=0.8,
            attributes={"status": "FOUND"},
            relationships=("user-1",),
            platform="github",
            profile_url="https://github.com/alice",
            status="FOUND",
        )
        with self.assertRaises(TypeError):
            entity.attributes["new"] = "value"  # type: ignore[index]
        self.assertEqual(entity.type, "profile")
        self.assertEqual(entity.confidence_score, 0.8)
        self.assertEqual(entity.metadata["status"], "FOUND")
        self.assertEqual(entity.relationships, ("user-1",))


if __name__ == "__main__":
    unittest.main()
