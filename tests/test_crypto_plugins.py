import unittest

from core.extensions.signal_forge import execute_plugins


class TestCryptoPlugins(unittest.TestCase):
    def test_crypto_plugins_execute_with_attachment_payloads(self):
        context = {
            "mode": "profile",
            "target": "alice",
            "attachments": ["alpha@example.com", "beta@example.org"],
            "crypto_key": "silica-key",
            "crypto_operation": "encrypt",
        }
        results, errors = execute_plugins(
            scope="profile",
            requested_plugins=[
                "crypto_aes_attachment",
                "crypto_xor_attachment",
                "crypto_rot13_attachment",
            ],
            include_all=False,
            context=context,
        )
        self.assertFalse(errors)
        result_ids = {row["id"] for row in results}
        self.assertIn("crypto_aes_attachment", result_ids)
        self.assertIn("crypto_xor_attachment", result_ids)
        self.assertIn("crypto_rot13_attachment", result_ids)

    def test_xor_plugin_respects_strict_mode_from_crypto_config(self):
        context = {
            "mode": "profile",
            "target": "alice",
            "attachments": ["%%%invalid%%%"],
            "crypto_config": {
                "operation": "decrypt",
                "output_encoding": "base64",
                "strict_mode": True,
                "source_fields": ["attachments"],
                "max_items": 4,
            },
        }
        results, errors = execute_plugins(
            scope="profile",
            requested_plugins=["crypto_xor_attachment"],
            include_all=False,
            context=context,
        )
        self.assertFalse(errors)
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertEqual(row.get("severity"), "HIGH")
        data = row.get("data", {})
        self.assertEqual(data.get("failed"), 1)
        profile = data.get("crypto_profile", {})
        self.assertEqual(profile.get("strict_mode"), True)

    def test_rot13_plugin_collects_payloads_from_results_source(self):
        context = {
            "mode": "profile",
            "target": "charlie",
            "results": [
                {
                    "platform": "demo",
                    "url": "https://example.test/charlie",
                    "bio": "charlie@sample.org",
                    "mentions": ["@charlie"],
                    "links": ["https://sample.org/about"],
                    "contacts": {"emails": ["charlie@sample.org"], "phones": ["+1-555-0100"]},
                }
            ],
            "crypto_config": {
                "operation": "encrypt",
                "source_fields": ["results"],
                "max_items": 8,
            },
        }
        results, errors = execute_plugins(
            scope="profile",
            requested_plugins=["crypto_rot13_attachment"],
            include_all=False,
            context=context,
        )
        self.assertFalse(errors)
        self.assertEqual(len(results), 1)
        data = results[0].get("data", {})
        self.assertGreater(data.get("payload_count", 0), 0)
        source_summary = data.get("source_summary", {})
        self.assertGreater(source_summary.get("results", 0), 0)


if __name__ == "__main__":
    unittest.main()
