import unittest

from core.signal_sieve import list_filter_descriptors
from core.signal_forge import list_plugin_descriptors


class TestExtensionsRegistry(unittest.TestCase):
    def test_internal_plugins_present(self):
        plugins = list_plugin_descriptors(scope=None)
        plugin_ids = {item["id"] for item in plugins}
        expected = {
            "orbit_link_matrix",
            "contact_lattice",
            "identity_fusion_core",
            "header_hardening_probe",
            "subdomain_risk_atlas",
            "threat_conductor",
        }
        self.assertTrue(expected.issubset(plugin_ids))

    def test_internal_filters_present(self):
        filters = list_filter_descriptors(scope=None)
        filter_ids = {item["id"] for item in filters}
        expected = {
            "contact_canonicalizer",
            "entity_name_resolver",
            "pii_signal_classifier",
            "mailbox_provider_profiler",
            "sensitive_lexicon_guard",
            "exposure_tier_matrix",
        }
        self.assertTrue(expected.issubset(filter_ids))


if __name__ == "__main__":
    unittest.main()
