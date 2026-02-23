import unittest

from core.signal_forge import execute_plugins
from core.signal_sieve import execute_filters


class TestExtensionSelectionByName(unittest.TestCase):
    def test_execute_plugins_accepts_title(self):
        results, errors = execute_plugins(
            scope="profile",
            requested_plugins=["Contact Lattice Analyzer"],
            include_all=False,
            context={"target": "alice", "mode": "profile", "results": []},
        )
        self.assertEqual(errors, [])
        self.assertEqual([row["id"] for row in results], ["contact_lattice"])

    def test_execute_plugins_accepts_normalized_title(self):
        results, errors = execute_plugins(
            scope="profile",
            requested_plugins=["contact-lattice-analyzer"],
            include_all=False,
            context={"target": "alice", "mode": "profile", "results": []},
        )
        self.assertEqual(errors, [])
        self.assertEqual([row["id"] for row in results], ["contact_lattice"])

    def test_execute_filters_accepts_title_and_compact_name(self):
        results, errors = execute_filters(
            scope="profile",
            requested_filters=["Contact Canonicalizer", "PIISignalClassifier"],
            include_all=False,
            context={"target": "alice", "mode": "profile", "results": []},
        )
        self.assertEqual(errors, [])
        self.assertEqual(
            [row["id"] for row in results],
            ["contact_canonicalizer", "pii_signal_classifier"],
        )


if __name__ == "__main__":
    unittest.main()
