import unittest

from core.foundation import DEFAULT_RESEARCH_POLICY, InvestigationProfile, ScopeBoundary


class TestResearchScope(unittest.TestCase):
    def test_scope_boundary_matches_domains_hosts_and_networks(self):
        scope_boundary = ScopeBoundary(
            approved_domains=("example.com",),
            approved_hosts=("198.51.100.10",),
            approved_networks=("192.0.2.0/24",),
        )

        self.assertTrue(scope_boundary.contains("example.com"))
        self.assertTrue(scope_boundary.contains("portal.example.com"))
        self.assertTrue(scope_boundary.contains("198.51.100.10"))
        self.assertTrue(scope_boundary.contains("192.0.2.44"))
        self.assertFalse(scope_boundary.contains("203.0.113.77"))

    def test_policy_rejects_forbidden_capabilities(self):
        with self.assertRaises(ValueError):
            DEFAULT_RESEARCH_POLICY.ensure_capabilities_allowed(("exploit_delivery",))

    def test_active_collection_requires_scope_match(self):
        with self.assertRaises(ValueError):
            InvestigationProfile(
                investigation_target="203.0.113.10",
                scope_boundary=ScopeBoundary(approved_networks=("192.0.2.0/24",)),
                requested_capabilities=("active_reconnaissance",),
                allow_active_collection=True,
            )

    def test_assessment_meaning_treats_documents_as_equal_weight(self):
        profile = InvestigationProfile(
            investigation_target="research.example.com",
            scope_boundary=ScopeBoundary(approved_domains=("example.com",)),
            requested_capabilities=("passive_osint_collection", "report_generation"),
        )

        self.assertIn("equal-weight", " ".join(profile.assessment_meaning))


if __name__ == "__main__":
    unittest.main()
