# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Sylica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Sylica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Sylica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

import unittest

from core.domain import (
    BaseEntity,
    ProfileEntity,
    ServiceEntity,
    VulnerabilityReference,
    make_entity_id,
)


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
            entity.attributes["new"] = "value"
        self.assertEqual(entity.type, "profile")
        self.assertEqual(entity.confidence_score, 0.8)
        self.assertEqual(entity.metadata["status"], "FOUND")
        self.assertEqual(entity.relationships, ("user-1",))

    def test_service_entity_builds_keyword_query(self):
        entity = ServiceEntity(
            id="service-1",
            value="postgresql://192.0.2.10:5432",
            source="surface",
            confidence=0.9,
            authorized_host="192.0.2.10",
            port=5432,
            transport_protocol="tcp",
            service_product="PostgreSQL",
            service_vendor="postgresql",
            service_version="14.5",
        )
        self.assertEqual(entity.entity_type, "service")
        self.assertEqual(entity.keyword_query.lower(), "postgresql 14.5")

    def test_vulnerability_reference_defaults_tags(self):
        reference = VulnerabilityReference(source="NVD", url="https://nvd.nist.gov/")
        self.assertEqual(reference.tags, ())


if __name__ == "__main__":
    unittest.main()
