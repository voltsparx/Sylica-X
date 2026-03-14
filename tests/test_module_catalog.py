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
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from modules.catalog import (
    DEFAULT_CATALOG_VERSION,
    build_module_catalog,
    ensure_module_catalog,
    query_module_catalog,
    select_module_entries,
    summarize_module_catalog,
    validate_module_catalog,
)


class TestModuleCatalog(unittest.TestCase):
    def test_build_catalog_writes_indexes_and_classifies(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "intel-sources"
            output_root = Path(temp_dir) / "modules"
            (root / "source-pack-05" / "recon" / "modules").mkdir(parents=True, exist_ok=True)
            (root / "source-pack-07" / "modules").mkdir(parents=True, exist_ok=True)
            (root / "custom" / "pipeline").mkdir(parents=True, exist_ok=True)

            (root / "source-pack-05" / "recon" / "modules" / "user_lookup.py").write_text(
                "class Module:\n    pass\n# username profile account plugin",
                encoding="utf-8",
            )
            (root / "source-pack-07" / "modules" / "sfp_dns.py").write_text(
                "# module dns domain http surface",
                encoding="utf-8",
            )
            (root / "custom" / "pipeline" / "normalize_filter.py").write_text(
                "# filter sanitize normalize dedupe",
                encoding="utf-8",
            )

            payload = build_module_catalog(root, output_root=output_root)
            summary = summarize_module_catalog(payload)
            plugins = select_module_entries(payload, kind="plugin")
            filters = select_module_entries(payload, kind="filter")

            self.assertEqual(summary["framework_count"], 3)
            self.assertEqual(summary["module_count"], 3)
            self.assertGreaterEqual(summary["kind_counts"]["plugin"], 2)
            self.assertGreaterEqual(summary["kind_counts"]["filter"], 1)
            self.assertTrue(any("user_lookup.py" in str(item.get("file", "")) for item in plugins))
            self.assertTrue(any("normalize_filter.py" in str(item.get("file", "")) for item in filters))
            self.assertTrue((output_root / "index.json").exists())
            self.assertTrue((output_root / "plugin-modules.json").exists())
            self.assertTrue((output_root / "filter-modules.json").exists())

    def test_ensure_catalog_loads_existing_index_without_refresh(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "intel-sources"
            output_root = Path(temp_dir) / "modules"
            (root / "alpha").mkdir(parents=True, exist_ok=True)
            (root / "alpha" / "scan.py").write_text("# module plugin", encoding="utf-8")

            first = build_module_catalog(root, output_root=output_root)
            second = ensure_module_catalog(refresh=False, source_root=root, output_root=output_root)

            self.assertEqual(first.get("module_count"), second.get("module_count"))
            self.assertEqual(first.get("framework_count"), second.get("framework_count"))

    def test_query_catalog_supports_search_tags_and_sorting(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "intel-sources"
            output_root = Path(temp_dir) / "modules"
            (root / "alpha" / "modules").mkdir(parents=True, exist_ok=True)
            (root / "beta" / "collectors").mkdir(parents=True, exist_ok=True)
            (root / "gamma" / "filters").mkdir(parents=True, exist_ok=True)

            (root / "alpha" / "modules" / "identity_graph.py").write_text(
                "# plugin profile username account graph fusion link correlate risk score report",
                encoding="utf-8",
            )
            (root / "beta" / "collectors" / "dns_collector.py").write_text(
                "# plugin collector source dns domain subdomain rdap whois http",
                encoding="utf-8",
            )
            (root / "gamma" / "filters" / "identity_filter.py").write_text(
                "# filter normalize sanitize dedupe identity email profile",
                encoding="utf-8",
            )

            payload = build_module_catalog(root, output_root=output_root)
            query = query_module_catalog(
                payload,
                kind="plugin",
                scope="all",
                search="identity graph",
                tags=["identity", "correlation"],
                min_score=1,
                sort_by="power_score",
                descending=True,
                limit=5,
            )
            summary = summarize_module_catalog(payload)

            self.assertTrue(query["entries"])
            first = query["entries"][0]
            self.assertEqual(first["kind"], "plugin")
            self.assertIn("identity", first.get("capabilities", []))
            self.assertIn("correlation", first.get("capabilities", []))
            self.assertGreaterEqual(first.get("metrics", {}).get("power_score", 0), 1)
            self.assertIn("capability_counts", summary)
            self.assertIn("score_bands", summary)
            self.assertIn("power_score_avg", summary)

    def test_query_catalog_supports_offset_and_has_more(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "intel-sources"
            output_root = Path(temp_dir) / "modules"
            (root / "alpha" / "mods").mkdir(parents=True, exist_ok=True)

            for index in range(8):
                (root / "alpha" / "mods" / f"m{index}.py").write_text(
                    "# plugin profile dns domain fusion graph score",
                    encoding="utf-8",
                )

            payload = build_module_catalog(root, output_root=output_root)
            page = query_module_catalog(
                payload,
                kind="plugin",
                scope="all",
                sort_by="file",
                descending=False,
                limit=3,
                offset=2,
            )

            self.assertEqual(page["matched_total"], 8)
            self.assertEqual(page["returned_count"], 3)
            self.assertTrue(page["has_more"])
            self.assertEqual(page["query"]["offset"], 2)

    def test_ensure_catalog_rebuilds_on_version_mismatch(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "intel-sources"
            output_root = Path(temp_dir) / "modules"
            (root / "alpha").mkdir(parents=True, exist_ok=True)
            (root / "alpha" / "scan.py").write_text("# module plugin", encoding="utf-8")

            payload = build_module_catalog(root, output_root=output_root)
            payload["catalog_version"] = "0.1"
            (output_root / "index.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

            rebuilt = ensure_module_catalog(refresh=False, source_root=root, output_root=output_root)
            is_valid, _errors = validate_module_catalog(rebuilt)

            self.assertTrue(is_valid)
            self.assertEqual(rebuilt.get("catalog_version"), DEFAULT_CATALOG_VERSION)


if __name__ == "__main__":
    unittest.main()
