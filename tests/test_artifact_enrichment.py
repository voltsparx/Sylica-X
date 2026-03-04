import json
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.artifacts import csv_export
from core.artifacts import html_report
from core.artifacts import output as output_artifacts
from core.artifacts import storage


class TestArtifactEnrichment(unittest.TestCase):
    @contextmanager
    def _patch_paths(self, root: Path):
        with ExitStack() as stack:
            stack.enter_context(patch.object(storage, "OUTPUT_ROOT", root))
            stack.enter_context(patch.object(storage, "DATA_DIR", root / "data"))
            stack.enter_context(patch.object(storage, "HTML_DIR", root / "html"))
            stack.enter_context(patch.object(storage, "CLI_DIR", root / "cli"))
            stack.enter_context(patch.object(storage, "LOG_DIR", root / "logs"))
            yield

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
                )

                payload = json.loads(Path(json_path).read_text(encoding="utf-8"))

        self.assertIn("summary", payload)
        self.assertEqual(payload["summary"]["result_count"], 1)
        self.assertEqual(payload["summary"]["issue_count"], 1)
        self.assertEqual(payload["summary"]["plugin_count"], 1)
        self.assertEqual(payload["summary"]["filter_count"], 1)

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
                csv_path = csv_export.export_to_csv("alice")
                self.assertIsNotNone(csv_path)

                base = root / "cli" / "alice"
                self.assertTrue((base.with_suffix(".csv")).exists())
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


if __name__ == "__main__":
    unittest.main()

