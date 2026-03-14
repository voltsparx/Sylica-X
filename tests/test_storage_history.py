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
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from core.artifacts import storage
from core.foundation.output_config import (
    clear_session_output_base_dir,
    get_session_output_base_dir,
    set_session_output_base_dir,
)


class TestStorageHistory(unittest.TestCase):
    @contextmanager
    def _patch_paths(self, base_dir: Path):
        previous = get_session_output_base_dir()
        set_session_output_base_dir(base_dir)
        try:
            yield
        finally:
            if previous is None:
                clear_session_output_base_dir()
            else:
                set_session_output_base_dir(previous)

    def test_list_targets_prefers_data_results_over_html_duplicates(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self._patch_paths(root):
                data_file = root / "output" / "json" / "alice-info-20240101_000000.json"
                data_file.parent.mkdir(parents=True, exist_ok=True)
                data_file.write_text(json.dumps({"target": "alice"}), encoding="utf-8")

                html_file = root / "output" / "html" / "alice-info-20240101_000000.html"
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
                html_file = root / "output" / "html" / "legacy_target-info-20240101_000000.html"
                html_file.parent.mkdir(parents=True, exist_ok=True)
                html_file.write_text("<html></html>", encoding="utf-8")

                rows = storage.list_targets(limit=10)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].source, "html")
        self.assertTrue(rows[0].path.endswith("legacy_target.html"))


if __name__ == "__main__":
    unittest.main()
