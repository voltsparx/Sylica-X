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

from core.collect.ocr_pipeline import (
    extract_ocr_signals,
    merge_ocr_engine_results,
    preprocess_for_ocr,
    run_ocr_pipeline,
)
from core.foundation.operator_config import load_operator_config


class TestOcrPipeline(unittest.TestCase):
    def test_preprocess_off_unchanged(self):
        payload = b"x" * 100
        self.assertEqual(preprocess_for_ocr(payload, "off"), payload)

    def test_merge_both_empty(self):
        self.assertEqual(merge_ocr_engine_results({}, {})["merged_text"], "")

    def test_merge_only_tesseract(self):
        tesseract = {"text": "hello world", "engine": "tesseract", "available": True}
        self.assertEqual(merge_ocr_engine_results(tesseract, {})["merged_text"], "hello world")

    def test_extract_signals_email(self):
        result = extract_ocr_signals("contact me at test@example.com today")
        self.assertIn("test@example.com", result["emails"])

    def test_pipeline_returns_dict(self):
        result = run_ocr_pipeline(b"fakebytes", use_tesseract=False, use_easyocr=False)
        self.assertIsInstance(result, dict)
        self.assertIn("merged_text", result)

    def test_config_defaults(self):
        result = load_operator_config("/nonexistent/path.yml")
        self.assertIsInstance(result, dict)
        self.assertIn("surface_probe", result)


if __name__ == "__main__":
    unittest.main()

