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
# ──────────────────────────────────────────────────────────────

import unittest
from unittest.mock import Mock, patch

from core.collect.subdomain_harvest import (
    harvest_binary_status,
    run_passive_subdomain_harvest,
)


class TestSubdomainHarvest(unittest.TestCase):
    def test_status_returns_dict(self):
        result = harvest_binary_status()
        self.assertIsInstance(result, dict)
        self.assertIn("available", result)

    def test_no_binary_passive_error(self):
        with patch("core.collect.subdomain_harvest.shutil.which", return_value=None):
            self.assertIn("error", run_passive_subdomain_harvest("example.com"))

    def test_parses_json_lines(self):
        mock_result = Mock(
            stdout='{"name":"sub.example.com"}\n{"name":"api.example.com"}\n',
            stderr="",
            returncode=0,
        )
        with (
            patch("core.collect.subdomain_harvest.locate_harvest_binary", return_value="/usr/bin/amass"),
            patch("core.collect.subdomain_harvest.subprocess.run", return_value=mock_result),
        ):
            result = run_passive_subdomain_harvest("example.com")
        self.assertEqual(result["subdomains"], ["api.example.com", "sub.example.com"])


if __name__ == "__main__":
    unittest.main()

