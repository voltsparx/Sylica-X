import json
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core import storage


class TestStorageHistory(unittest.TestCase):
    @contextmanager
    def _patch_paths(self, root: Path):
        with ExitStack() as stack:
            stack.enter_context(patch.object(storage, "OUTPUT_ROOT", root))
            stack.enter_context(patch.object(storage, "DATA_DIR", root / "data"))
            stack.enter_context(patch.object(storage, "HTML_DIR", root / "html"))
            stack.enter_context(patch.object(storage, "CLI_DIR", root / "cli"))
            stack.enter_context(patch.object(storage, "LOG_DIR", root / "logs"))
            yield

    def test_list_targets_prefers_data_results_over_html_duplicates(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self._patch_paths(root):
                data_file = root / "data" / "alice" / "results.json"
                data_file.parent.mkdir(parents=True, exist_ok=True)
                data_file.write_text(json.dumps({"target": "alice"}), encoding="utf-8")

                html_file = root / "html" / "alice.html"
                html_file.parent.mkdir(parents=True, exist_ok=True)
                html_file.write_text("<html></html>", encoding="utf-8")

                rows = storage.list_targets(limit=10)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].source, "data")
        self.assertTrue(rows[0].path.endswith("results.json"))

    def test_list_targets_uses_html_when_no_data_results_exist(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self._patch_paths(root):
                html_file = root / "html" / "legacy_target.html"
                html_file.parent.mkdir(parents=True, exist_ok=True)
                html_file.write_text("<html></html>", encoding="utf-8")

                rows = storage.list_targets(limit=10)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].source, "html")
        self.assertTrue(rows[0].path.endswith("legacy_target.html"))


if __name__ == "__main__":
    unittest.main()
