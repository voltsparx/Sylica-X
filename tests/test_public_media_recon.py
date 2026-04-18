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

from core.collect.public_media_recon import collect_post_text_intelligence


class TestPublicMediaRecon(unittest.TestCase):
    def test_post_text_empty_input(self):
        result = asyncio.run(collect_post_text_intelligence([]))
        self.assertEqual(result["post_count"], 0)

    def test_post_text_signal_extraction(self):
        result = asyncio.run(
            collect_post_text_intelligence(["email me at a@b.com #hello @user"])
        )
        self.assertIn("a@b.com", result["all_emails"])
        self.assertIn("hello", result["all_hashtags"])


if __name__ == "__main__":
    unittest.main()
