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

import json
import sqlite3
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from core.artifacts import csv_export
from core.artifacts import html_report
from core.artifacts import output as output_artifacts
from core.artifacts.sql_store import write_sqlite_report
from core.collect.media_intel import detect_image_tooling
from core.foundation.output_config import (
    clear_session_output_base_dir,
    get_session_output_base_dir,
    set_session_output_base_dir,
)


class TestArtifactEnrichment(unittest.TestCase):
    @contextmanager
    def _patch_paths(self, root: Path):
        previous = get_session_output_base_dir()
        set_session_output_base_dir(root)
        try:
            yield
        finally:
            if previous is None:
                clear_session_output_base_dir()
            else:
                set_session_output_base_dir(previous)

    def test_save_results_adds_summary_block(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self._patch_paths(root):
                json_path = output_artifacts.save_results(
                    target="alice",
                    results=[{"platform": "github", "status": "FOUND", "confidence": 88}],
                    correlation={},
                    issues=[{"title": "Public Contact Exposure", "severity": "HIGH"}],
                    issue_summary={"risk_score": 72},
                    plugin_results=[{"id": "p1", "severity": "MEDIUM", "summary": "x", "highlights": [], "data": {}}],
                    filter_results=[{"id": "f1", "severity": "INFO", "summary": "x", "highlights": [], "data": {}}],
                    extra_payload={
                        "selected_plugins": ["p1"],
                        "selected_filters": ["f1"],
                        "selected_modules": ["source-pack-01-module-1"],
                        "attached_modules": [{"id": "source-pack-01-module-1", "kind": "collector", "power_score": 88}],
                        "ocr_tooling": detect_image_tooling(),
                    },
                )

                payload = json.loads(Path(json_path).read_text(encoding="utf-8"))

        self.assertIn("summary", payload)
        self.assertEqual(payload["summary"]["result_count"], 1)
        self.assertEqual(payload["summary"]["issue_count"], 1)
        self.assertEqual(payload["summary"]["plugin_count"], 1)
        self.assertEqual(payload["summary"]["filter_count"], 1)
        self.assertEqual(payload["summary"]["selected_module_count"], 1)
        self.assertIn("ocr_preferred_engine", payload["summary"])

    def test_csv_export_writes_companion_csv_artifacts(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self._patch_paths(root):
                output_artifacts.save_results(
                    target="alice",
                    results=[
                        {
                            "platform": "github",
                            "status": "FOUND",
                            "confidence": 88,
                            "http_status": 200,
                            "response_time_ms": 210,
                            "bio": "hello",
                            "contacts": {"emails": ["alice@example.com"], "phones": ["+1 202 555 0100"]},
                            "links": ["https://example.com"],
                            "mentions": ["@alice"],
                            "url": "https://github.com/alice",
                            "context": "ok",
                        }
                    ],
                    correlation={},
                    issues=[{"title": "Public Contact Exposure", "severity": "HIGH", "scope": "identity"}],
                    issue_summary={"risk_score": 72},
                    plugin_results=[{"id": "p1", "title": "P1", "severity": "MEDIUM", "summary": "x", "highlights": [], "data": {}}],
                    filter_results=[{"id": "f1", "title": "F1", "severity": "INFO", "summary": "x", "highlights": [], "data": {}}],
                    intelligence_bundle={"scored_entities": [], "entity_facets": {"scored_contacts": []}},
                )
                csv_path = csv_export.export_to_csv("alice", stamp="20240101_000000")
                self.assertIsNotNone(csv_path)

                base = Path(csv_path)
                self.assertTrue(base.exists())
                self.assertTrue((base.with_suffix(".issues.csv")).exists())
                self.assertTrue((base.with_suffix(".plugins.csv")).exists())
                self.assertTrue((base.with_suffix(".filters.csv")).exists())
                self.assertTrue((base.with_suffix(".intel-entities.csv")).exists())
                self.assertTrue((base.with_suffix(".intel-contacts.csv")).exists())

    def test_html_report_contains_extension_overview(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self._patch_paths(root):
                html_path = html_report.generate_html(
                    target="alice",
                    results=[{"platform": "github", "status": "FOUND", "confidence": 88, "url": "https://github.com/alice"}],
                    correlation={},
                    issues=[{"title": "Public Contact Exposure", "severity": "HIGH", "scope": "identity"}],
                    issue_summary={"risk_score": 72},
                    narrative="brief",
                    plugin_results=[{"id": "p1", "title": "P1", "severity": "MEDIUM", "summary": "x", "highlights": [], "data": {}}],
                    plugin_errors=[],
                    filter_results=[{"id": "f1", "title": "F1", "severity": "INFO", "summary": "x", "highlights": [], "data": {}}],
                    filter_errors=[],
                )
                html_text = Path(html_path).read_text(encoding="utf-8")

        self.assertIn("Extension Signal Overview", html_text)
        self.assertIn("Raw plugin data payload", html_text)
        self.assertIn("Raw filter data payload", html_text)

    def test_sql_store_persists_attachments_and_ocr_items(self):
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "report.sqlite3"
            write_sqlite_report(
                db_path,
                {
                    "metadata": {"mode": "ocr", "generated_at_utc": "2026-01-01T00:00:00Z"},
                    "target": "alice",
                    "summary": {"result_count": 0},
                    "selected_plugins": ["ocr_extractor"],
                    "selected_filters": ["ocr_signal_classifier"],
                    "attached_modules": [{"id": "source-pack-01-module-1", "kind": "collector"}],
                    "ocr_scan": {
                        "items": [
                            {
                                "source": "image.png",
                                "source_kind": "local",
                                "ocr_engine": "pytesseract",
                                "confidence_hint": "high",
                                "normalized_text": "alice@example.com",
                                "signals": {"emails": ["alice@example.com"]},
                            }
                        ]
                    },
                },
            )

            conn = sqlite3.connect(db_path)
            try:
                attachment_count = conn.execute("SELECT COUNT(*) FROM attachments").fetchone()[0]
                ocr_item_count = conn.execute("SELECT COUNT(*) FROM ocr_items").fetchone()[0]
            finally:
                conn.close()

        self.assertEqual(attachment_count, 3)
        self.assertEqual(ocr_item_count, 1)


if __name__ == "__main__":
    unittest.main()
