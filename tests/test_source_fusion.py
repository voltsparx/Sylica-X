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
from subprocess import CompletedProcess
from unittest.mock import patch

from core.collect.source_fusion import (
    CONNECTOR_REGISTRY,
    ConnectorRuntime,
    collect_source_fusion_intel,
    detect_connector_runtimes,
)


class TestSourceFusionConnectors(unittest.TestCase):
    def test_detect_connector_runtimes_uses_binary_and_source_hints(self):
        def _binary_probe(names: tuple[str, ...]) -> str | None:
            if "source-pack-01" in names:
                return "/usr/bin/source-pack-01"
            return None

        def _source_probe(paths: tuple[str, ...]) -> str | None:
            if "intel-sources/source-pack-06/source-pack-06_project/__main__.py" in paths:
                return "intel-sources/source-pack-06/source-pack-06_project/__main__.py"
            return None

        with (
            patch("core.collect.source_fusion._find_binary_path", side_effect=_binary_probe),
            patch("core.collect.source_fusion._find_source_entry", side_effect=_source_probe),
        ):
            runtimes = detect_connector_runtimes()

        by_id = {row.spec.connector_id: row for row in runtimes}
        self.assertTrue(by_id["surface_grid_alpha"].executable)
        self.assertTrue(by_id["identity_mesh_alpha"].executable)
        self.assertFalse(by_id["module_fabric_core"].executable)

    def test_collect_source_fusion_intel_aggregates_signals(self):
        mesh_spec = next(spec for spec in CONNECTOR_REGISTRY if spec.connector_id == "identity_mesh_alpha")
        surface_spec = next(spec for spec in CONNECTOR_REGISTRY if spec.connector_id == "surface_grid_alpha")
        runtimes = [
            ConnectorRuntime(
                spec=mesh_spec,
                binary_path="/usr/bin/source-pack-06",
                source_entry=None,
                executable=True,
            ),
            ConnectorRuntime(
                spec=surface_spec,
                binary_path="/usr/bin/source-pack-01",
                source_entry=None,
                executable=True,
            ),
        ]

        def _subprocess_run(cmd, **_kwargs):  # noqa: ANN001
            command = " ".join(str(part) for part in cmd)
            if "source-pack-06" in command:
                return CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout="alice@example.com https://example.com/u/alice 8.8.8.8",
                    stderr="",
                )
            return CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="api.example.com login.example.com support@example.com",
                stderr="",
            )

        with (
            patch("core.collect.source_fusion.detect_connector_runtimes", return_value=runtimes),
            patch("core.collect.source_fusion.subprocess.run", side_effect=_subprocess_run),
        ):
            payload = collect_source_fusion_intel(
                mode="fusion",
                username="alice",
                domain="example.com",
                timeout_seconds=10,
                max_connectors=4,
            )

        self.assertEqual(payload["coverage"]["executed"], 2)
        self.assertEqual(payload["coverage"]["successful"], 2)
        self.assertIn("alice@example.com", payload["signals"]["emails"])
        self.assertIn("support@example.com", payload["signals"]["emails"])
        self.assertIn("api.example.com", payload["signals"]["subdomains"])

    def test_collect_source_fusion_intel_skips_invalid_username(self):
        mesh_spec = next(spec for spec in CONNECTOR_REGISTRY if spec.connector_id == "identity_mesh_alpha")
        runtimes = [
            ConnectorRuntime(
                spec=mesh_spec,
                binary_path="/usr/bin/source-pack-06",
                source_entry=None,
                executable=True,
            )
        ]

        with patch("core.collect.source_fusion.detect_connector_runtimes", return_value=runtimes):
            payload = collect_source_fusion_intel(
                mode="profile",
                username="bad user with spaces",
                domain=None,
                timeout_seconds=10,
                max_connectors=2,
            )

        self.assertEqual(payload["coverage"]["planned"], 0)
        self.assertEqual(payload["coverage"]["executed"], 0)


if __name__ == "__main__":
    unittest.main()
