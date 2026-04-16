# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Silica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Silica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Silica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

import unittest

from core.extensions.signal_forge import execute_plugins
from core.extensions.signal_sieve import execute_filters


class TestExtensionSelectionByName(unittest.TestCase):
    def test_execute_plugins_accepts_title(self):
        results, errors = execute_plugins(
            scope="profile",
            requested_plugins=["Contact Ember Analyzer"],
            include_all=False,
            context={"target": "alice", "mode": "profile", "results": []},
        )
        self.assertEqual(errors, [])
        self.assertEqual([row["id"] for row in results], ["contact_lattice"])

    def test_execute_plugins_accepts_normalized_title(self):
        results, errors = execute_plugins(
            scope="profile",
            requested_plugins=["contact-ember-analyzer"],
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
