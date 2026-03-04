import unittest

from core.extensions.signal_forge import execute_plugins
from core.extensions.signal_sieve import execute_filters


class TestNewExtensionPack(unittest.TestCase):
    def test_new_profile_plugins_execute(self):
        context = {
            "target": "alice",
            "mode": "profile",
            "results": [
                {
                    "platform": "github",
                    "status": "FOUND",
                    "confidence": 82,
                    "bio": "Security researcher",
                    "links": ["https://example.com/about", "http://bit.ly/alice"],
                    "mentions": ["@alic3", "alice_dev"],
                    "contacts": {"emails": ["alice@example.com"], "phones": ["+1 202 555 0100"]},
                },
                {
                    "platform": "x",
                    "status": "FOUND",
                    "confidence": 73,
                    "bio": "OSINT analyst",
                    "links": ["https://tinyurl.com/alice", "https://blog.example.com/reset?token=abc"],
                    "mentions": ["@alice", "@alice_dev"],
                    "contacts": {"emails": ["alice@example.com", "alice@gmail.com"], "phones": []},
                },
            ],
            "issues": [],
            "issue_summary": {"total": 0},
            "intelligence_bundle": {},
        }

        results, errors = execute_plugins(
            scope="profile",
            requested_plugins=[
                "account_recovery_exposure_probe",
                "link_outbound_risk_profiler",
                "username_impersonation_probe",
            ],
            include_all=False,
            context=context,
        )

        self.assertFalse(any("failed" in item.lower() for item in errors))
        result_ids = {row["id"] for row in results}
        self.assertIn("account_recovery_exposure_probe", result_ids)
        self.assertIn("link_outbound_risk_profiler", result_ids)
        self.assertIn("username_impersonation_probe", result_ids)

    def test_new_surface_plugins_execute(self):
        context = {
            "target": "example.com",
            "mode": "surface",
            "domain_result": {
                "target": "example.com",
                "resolved_addresses": ["1.1.1.1"],
                "https": {"status": 200, "final_url": "https://example.com", "headers": {}, "error": ""},
                "http": {
                    "status": 200,
                    "final_url": "http://example.com",
                    "headers": {},
                    "error": "",
                    "redirects_to_https": False,
                },
                "subdomains": ["admin.example.com", "api.example.com"],
                "rdap": {
                    "handle": "ABC123",
                    "status": ["active"],
                    "name_servers": ["ns1.example.net"],
                    "last_changed": "2022-01-01T00:00:00Z",
                },
                "scan_notes": [],
            },
            "issues": [],
            "issue_summary": {"total": 0},
            "intelligence_bundle": {},
        }

        results, errors = execute_plugins(
            scope="surface",
            requested_plugins=[
                "rdap_lifecycle_inspector",
                "surface_transport_stability_probe",
            ],
            include_all=False,
            context=context,
        )

        self.assertFalse(any("failed" in item.lower() for item in errors))
        result_ids = {row["id"] for row in results}
        self.assertIn("rdap_lifecycle_inspector", result_ids)
        self.assertIn("surface_transport_stability_probe", result_ids)

    def test_new_filters_execute(self):
        profile_filter_context = {
            "target": "alice",
            "mode": "profile",
            "results": [
                {
                    "platform": "github",
                    "status": "FOUND",
                    "confidence": 81,
                    "links": ["http://bit.ly/a", "https://example.com"],
                    "contacts": {"emails": ["alice@mailinator.com", "alice@example.com"], "phones": ["+1 202 555 0100"]},
                }
            ],
            "issues": [{"title": "Public Contact Exposure", "severity": "HIGH"}],
            "plugins": [
                {
                    "id": "link_outbound_risk_profiler",
                    "severity": "MEDIUM",
                    "data": {
                        "shortener_links": ["http://bit.ly/a"],
                        "non_https_links": ["http://bit.ly/a"],
                        "sensitive_links": [],
                    },
                }
            ],
            "intelligence_bundle": {
                "risk_summary": {"total": 1, "CRITICAL": 0, "HIGH": 1},
                "confidence_distribution": {"low": 0, "medium": 1, "high": 0},
            },
        }
        profile_results, profile_errors = execute_filters(
            scope="profile",
            requested_filters=[
                "triage_priority_filter",
                "contact_quality_filter",
                "link_hygiene_filter",
                "evidence_consistency_filter",
            ],
            include_all=False,
            context=profile_filter_context,
        )
        self.assertFalse(any("failed" in item.lower() for item in profile_errors))
        profile_ids = {row["id"] for row in profile_results}
        self.assertIn("triage_priority_filter", profile_ids)
        self.assertIn("contact_quality_filter", profile_ids)
        self.assertIn("link_hygiene_filter", profile_ids)
        self.assertIn("evidence_consistency_filter", profile_ids)

        surface_filter_context = {
            "target": "example.com",
            "mode": "surface",
            "results": [],
            "domain_result": {
                "subdomains": ["admin.example.com", "dev.example.com", "api.example.com"],
            },
            "issues": [{"title": "Potential Subdomain Takeover Risk", "severity": "MEDIUM"}],
            "plugins": [
                {
                    "id": "domain_takeover_risk_probe",
                    "severity": "HIGH",
                    "data": {"high_risk_candidates": ["admin.example.com"]},
                }
            ],
            "intelligence_bundle": {
                "risk_summary": {"total": 1, "CRITICAL": 0, "HIGH": 0},
                "confidence_distribution": {"low": 0, "medium": 0, "high": 0},
            },
        }
        surface_results, surface_errors = execute_filters(
            scope="surface",
            requested_filters=[
                "triage_priority_filter",
                "subdomain_attack_path_filter",
                "evidence_consistency_filter",
            ],
            include_all=False,
            context=surface_filter_context,
        )
        self.assertFalse(any("failed" in item.lower() for item in surface_errors))
        surface_ids = {row["id"] for row in surface_results}
        self.assertIn("triage_priority_filter", surface_ids)
        self.assertIn("subdomain_attack_path_filter", surface_ids)
        self.assertIn("evidence_consistency_filter", surface_ids)


if __name__ == "__main__":
    unittest.main()

