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

import asyncio
import unittest
from unittest.mock import patch

from core.collect.domain_recon import collect_cert_transparency, collect_whois_data


class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def json(self, content_type=None):
        return self._payload


class _MockSession:
    def __init__(self, payload):
        self._payload = payload

    def get(self, *args, **kwargs):
        return _MockResponse(self._payload)


class TestDomainRecon(unittest.TestCase):
    def test_whois_no_binary(self):
        with patch("core.collect.domain_recon.shutil.which", return_value=None):
            self.assertIn("error", collect_whois_data("example.com"))

    def test_ct_parses_entries(self):
        session = _MockSession([{"name_value": "sub.example.com"}])
        result = asyncio.run(collect_cert_transparency("example.com", session))
        self.assertEqual(result["ct_entries"], ["sub.example.com"])


if __name__ == "__main__":
    unittest.main()

