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
import asyncio
import argparse
import io
from contextlib import redirect_stdout
from unittest.mock import patch

from core.runner import (
    EXIT_FAILURE,
    EXIT_USAGE,
    RunnerState,
    _normalize_multi_select_args,
    _split_csv_tokens,
    _keyword_to_command,
    build_prompt_parser,
    build_root_parser,
    compute_effective_state,
    run,
    safe_path_component,
)


class TestRunnerCli(unittest.TestCase):
    def test_compute_effective_state_uses_overrides(self):
        base = RunnerState(use_tor=False, use_proxy=True)
        resolved = compute_effective_state(base, tor_override=True, proxy_override=None)
        self.assertTrue(resolved.use_tor)
        self.assertTrue(resolved.use_proxy)

    def test_keyword_mapping_supports_prompt_shortcuts(self):
        self.assertEqual(_keyword_to_command("social"), "profile")
        self.assertEqual(_keyword_to_command("domain"), "surface")
        self.assertEqual(_keyword_to_command("full"), "fusion")
        self.assertEqual(_keyword_to_command("orch"), "orchestrate")
        self.assertEqual(_keyword_to_command("pipeline"), "orchestrate")
        self.assertEqual(_keyword_to_command("monitor"), "live")
        self.assertEqual(_keyword_to_command("plugins"), "plugins")
        self.assertEqual(_keyword_to_command("addonS"), "plugins")
        self.assertEqual(_keyword_to_command("filters"), "filters")
        self.assertEqual(_keyword_to_command("pii"), "filters")
        self.assertEqual(_keyword_to_command("template"), "templates")
        self.assertEqual(_keyword_to_command("modules"), "modules")
        self.assertEqual(_keyword_to_command("catalog"), "modules")
        self.assertEqual(_keyword_to_command("quicktest"), "quicktest")
        self.assertEqual(_keyword_to_command("smoketest"), "quicktest")
        self.assertEqual(_keyword_to_command("tor"), "anonymity")
        self.assertEqual(_keyword_to_command("history"), "history")
        self.assertEqual(_keyword_to_command("targets"), "history")
        self.assertEqual(_keyword_to_command("config"), "config")
        self.assertEqual(_keyword_to_command("about"), "about")
        self.assertEqual(_keyword_to_command("info"), "about")
        self.assertEqual(_keyword_to_command("explain"), "explain")
        self.assertEqual(_keyword_to_command("banner"), "banner")
        self.assertEqual(_keyword_to_command("framework"), "frameworks")
        self.assertEqual(_keyword_to_command("kit"), "surface-kit")
        self.assertIsNone(_keyword_to_command("unknown"))

    def test_root_profile_parser_parses_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "profile",
                "alice",
                "--preset",
                "deep",
                "--timeout",
                "30",
                "--max-concurrency",
                "12",
                "--csv",
                "--html",
                "--plugin",
                "orbit_link_matrix",
                "--plugin",
                "contact_lattice",
                "--filter",
                "contact_canonicalizer",
                "--filter",
                "entity_name_resolver",
            ]
        )
        self.assertEqual(args.command, "profile")
        self.assertEqual(args.usernames, ["alice"])
        self.assertEqual(args.preset, "deep")
        self.assertEqual(args.timeout, 30)
        self.assertEqual(args.max_concurrency, 12)
        self.assertTrue(args.csv)
        self.assertTrue(args.html)
        self.assertEqual(args.plugin, ["orbit_link_matrix", "contact_lattice"])
        self.assertEqual(args.filter, ["contact_canonicalizer", "entity_name_resolver"])
        self.assertEqual(args.extension_control, "manual")

    def test_root_profile_parser_accepts_max_preset(self):
        parser = build_root_parser()
        args = parser.parse_args(["profile", "alice", "--preset", "max"])
        self.assertEqual(args.command, "profile")
        self.assertEqual(args.preset, "max")

    def test_root_surface_parser_parses_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "surface",
                "example.com",
                "--preset",
                "quick",
                "--max-subdomains",
                "100",
                "--recon-mode",
                "passive",
                "-sS",
                "-aS",
                "-sV",
                "-O",
                "-vS",
                "--scan-delay",
                "0.25",
                "--no-ct",
                "--html",
                "--info-template",
                "surface-risk",
            ]
        )
        self.assertEqual(args.command, "surface")
        self.assertEqual(args.domain, "example.com")
        self.assertEqual(args.preset, "quick")
        self.assertEqual(args.max_subdomains, 100)
        self.assertEqual(args.recon_mode, "passive")
        self.assertEqual(args.scan_type, ["syn", "arp", "service"])
        self.assertTrue(args.os_fingerprint)
        self.assertEqual(args.scan_verbosity, "verbose")
        self.assertAlmostEqual(args.scan_delay, 0.25)
        self.assertFalse(args.ct)
        self.assertTrue(args.html)
        self.assertEqual(args.info_template, "surface-risk")
        self.assertEqual(args.extension_control, "manual")

    def test_root_fusion_parser_parses_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "fusion",
                "alice",
                "example.com",
                "--profile-preset",
                "quick",
                "--surface-preset",
                "deep",
                "--surface-recon-mode",
                "active",
                "-sU",
                "-sX",
                "--scan-delay",
                "0.4",
                "--html",
                "--plugin",
                "threat_conductor",
                "--filter",
                "exposure_tier_matrix",
            ]
        )
        self.assertEqual(args.command, "fusion")
        self.assertEqual(args.username, "alice")
        self.assertEqual(args.domain, "example.com")
        self.assertEqual(args.profile_preset, "quick")
        self.assertEqual(args.surface_preset, "deep")
        self.assertEqual(args.surface_recon_mode, "active")
        self.assertEqual(args.scan_type, ["udp", "xmas"])
        self.assertAlmostEqual(args.scan_delay, 0.4)
        self.assertTrue(args.html)
        self.assertEqual(args.plugin, ["threat_conductor"])
        self.assertEqual(args.filter, ["exposure_tier_matrix"])
        self.assertEqual(args.extension_control, "manual")

    def test_root_ocr_parser_parses_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "ocr",
                "image-one.png",
                "image-two.jpg",
                "--url",
                "https://example.com/image.png",
                "--preset",
                "deep",
                "--preprocess",
                "aggressive",
                "--threshold",
                "170",
                "--max-edge",
                "2400",
                "--max-bytes",
                "2000000",
                "--plugin",
                "ocr_extractor",
                "--filter",
                "ocr_signal_classifier",
                "--module",
                "source-pack-01-module-1,source-pack-01-module-2",
            ]
        )
        self.assertEqual(args.command, "ocr")
        self.assertEqual(args.paths, ["image-one.png", "image-two.jpg"])
        self.assertEqual(args.url, ["https://example.com/image.png"])
        self.assertEqual(args.preset, "deep")
        self.assertEqual(args.preprocess, "aggressive")
        self.assertEqual(args.threshold, 170)
        self.assertEqual(args.max_edge, 2400)
        self.assertEqual(args.max_bytes, 2000000)
        self.assertEqual(args.plugin, ["ocr_extractor"])
        self.assertEqual(args.filter, ["ocr_signal_classifier"])
        self.assertEqual(args.module, ["source-pack-01-module-1,source-pack-01-module-2"])
        self.assertEqual(args.extension_control, "manual")

    def test_root_orchestrate_parser_parses_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "orchestrate",
                "fusion",
                "alice",
                "--secondary-target",
                "example.com",
                "--profile",
                "deep",
                "--timeout",
                "42",
                "--max-workers",
                "18",
                "--source-profile",
                "max",
                "--max-platforms",
                "70",
                "--max-subdomains",
                "500",
                "-sN",
                "-sV",
                "-O",
                "--min-confidence",
                "0.4",
                "--json",
                "--html",
                "--plugin",
                "signal_fusion_core",
                "--filter",
                "signal_lane_fusion",
                "--module",
                "source-pack-01-module-1",
                "--extension-control",
                "hybrid",
            ]
        )
        self.assertEqual(args.command, "orchestrate")
        self.assertEqual(args.mode, "fusion")
        self.assertEqual(args.target, "alice")
        self.assertEqual(args.secondary_target, "example.com")
        self.assertEqual(args.profile, "deep")
        self.assertEqual(args.timeout, 42)
        self.assertEqual(args.max_workers, 18)
        self.assertEqual(args.source_profile, "max")
        self.assertEqual(args.module, ["source-pack-01-module-1"])
        self.assertEqual(args.max_platforms, 70)
        self.assertEqual(args.max_subdomains, 500)
        self.assertEqual(args.scan_type, ["null", "service"])
        self.assertTrue(args.os_fingerprint)
        self.assertAlmostEqual(args.min_confidence, 0.4)
        self.assertTrue(args.json)
        self.assertTrue(args.html)
        self.assertEqual(args.plugin, ["signal_fusion_core"])
        self.assertEqual(args.filter, ["signal_lane_fusion"])
        self.assertEqual(args.extension_control, "hybrid")

    def test_plugins_parser_parses_scope(self):
        parser = build_root_parser()
        args = parser.parse_args(["plugins", "--scope", "surface"])
        self.assertEqual(args.command, "plugins")
        self.assertEqual(args.scope, "surface")

    def test_filters_parser_parses_scope(self):
        parser = build_root_parser()
        args = parser.parse_args(["filters", "--scope", "profile"])
        self.assertEqual(args.command, "filters")
        self.assertEqual(args.scope, "profile")

    def test_modules_parser_parses_scope_kind_and_limit(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "modules",
                "--scope",
                "fusion",
                "--kind",
                "filter",
                "--search",
                "dns identity",
                "--tag",
                "identity",
                "--min-score",
                "25",
                "--sort-by",
                "power_score",
                "--descending",
                "--offset",
                "20",
                "--validate",
                "--stats-only",
                "--limit",
                "7",
            ]
        )
        self.assertEqual(args.command, "modules")
        self.assertEqual(args.scope, "fusion")
        self.assertEqual(args.kind, "filter")
        self.assertEqual(args.search, "dns identity")
        self.assertEqual(args.tag, ["identity"])
        self.assertEqual(args.min_score, 25)
        self.assertEqual(args.sort_by, "power_score")
        self.assertTrue(args.descending)
        self.assertEqual(args.offset, 20)
        self.assertTrue(args.validate)
        self.assertTrue(args.stats_only)
        self.assertEqual(args.limit, 7)

    def test_history_parser_parses_limit(self):
        parser = build_root_parser()
        args = parser.parse_args(["history", "--limit", "10"])
        self.assertEqual(args.command, "history")
        self.assertEqual(args.limit, 10)

    def test_frameworks_parser_parses_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(["frameworks", "--framework", "recursive-modules", "--modules", "--search", "httpx", "--limit", "5"])
        self.assertEqual(args.command, "frameworks")
        self.assertEqual(args.framework, "recursive-modules")
        self.assertTrue(args.modules)
        self.assertEqual(args.search, "httpx")
        self.assertEqual(args.limit, 5)

    def test_surface_kit_parser_parses_translation_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "surface-kit",
                "example.com",
                "--preset",
                "subdomain-enum",
                "--require-flag",
                "passive",
                "--exclude-flag",
                "deadly",
                "--dry-run",
            ]
        )
        self.assertEqual(args.command, "surface-kit")
        self.assertEqual(args.domain, "example.com")
        self.assertEqual(args.preset, "subdomain-enum")
        self.assertEqual(args.require_flag, ["passive"])
        self.assertEqual(args.exclude_flag, ["deadly"])
        self.assertTrue(args.dry_run)

    def test_quicktest_parser_parses_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(["quicktest", "--template", "atlas-mercier", "--seed", "9", "--json"])
        self.assertEqual(args.command, "quicktest")
        self.assertEqual(args.template, "atlas-mercier")
        self.assertEqual(args.seed, 9)
        self.assertTrue(args.json)

    def test_root_wizard_parser_parses_extended_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "wizard",
                "--profile-phase",
                "--surface-phase",
                "--fusion-phase",
                "--usernames",
                "alice,bob",
                "--domain",
                "example.com",
                "--profile-preset",
                "max",
                "--surface-preset",
                "deep",
                "-sS",
                "-sV",
                "-O",
                "--scan-delay",
                "0.2",
                "--extension-control",
                "hybrid",
                "--plugin",
                "threat_conductor",
                "--filter",
                "triage_priority_filter",
                "--html",
                "--csv",
                "--ct",
                "--no-rdap",
                "--sync-modules",
            ]
        )
        self.assertEqual(args.command, "wizard")
        self.assertTrue(args.run_profile)
        self.assertTrue(args.run_surface)
        self.assertTrue(args.run_fusion)
        self.assertEqual(args.usernames, "alice,bob")
        self.assertEqual(args.domain, "example.com")
        self.assertEqual(args.profile_preset, "max")
        self.assertEqual(args.surface_preset, "deep")
        self.assertEqual(args.scan_type, ["syn", "service"])
        self.assertTrue(args.os_fingerprint)
        self.assertAlmostEqual(args.scan_delay, 0.2)
        self.assertEqual(args.extension_control, "hybrid")
        self.assertEqual(args.plugin, ["threat_conductor"])
        self.assertEqual(args.filter, ["triage_priority_filter"])
        self.assertTrue(args.html)
        self.assertTrue(args.csv)
        self.assertTrue(args.ct)
        self.assertFalse(args.rdap)
        self.assertTrue(args.sync_modules)

    def test_root_wizard_parser_parses_ocr_flags(self):
        parser = build_root_parser()
        args = parser.parse_args(
            [
                "wizard",
                "--ocr-phase",
                "--image-paths",
                "one.png,two.jpg",
                "--image-urls",
                "https://example.com/one.png",
                "--ocr-preset",
                "deep",
                "--preprocess",
                "aggressive",
                "--threshold",
                "180",
                "--max-edge",
                "2048",
                "--max-bytes",
                "9000000",
            ]
        )
        self.assertEqual(args.command, "wizard")
        self.assertTrue(args.run_ocr)
        self.assertEqual(args.image_paths, "one.png,two.jpg")
        self.assertEqual(args.image_urls, "https://example.com/one.png")
        self.assertEqual(args.ocr_preset, "deep")
        self.assertEqual(args.preprocess, "aggressive")
        self.assertEqual(args.threshold, 180)
        self.assertEqual(args.max_edge, 2048)
        self.assertEqual(args.max_bytes, 9000000)

    def test_capability_pack_parser_parses_command(self):
        parser = build_root_parser()
        args = parser.parse_args(["capability-pack"])
        self.assertEqual(args.command, "capability-pack")

    def test_intel_alias_parser_parses_command(self):
        parser = build_root_parser()
        args = parser.parse_args(["intel"])
        self.assertEqual(args.command, "intel")

    def test_anonymity_parser_parses_check(self):
        parser = build_root_parser()
        args = parser.parse_args(["anonymity", "--check"])
        self.assertEqual(args.command, "anonymity")
        self.assertTrue(args.check)

    def test_root_parser_parses_global_about_flag(self):
        parser = build_root_parser()
        args = parser.parse_args(["--about"])
        self.assertIsNone(args.command)
        self.assertTrue(args.about_flag)

    def test_root_parser_parses_global_explain_flag(self):
        parser = build_root_parser()
        args = parser.parse_args(["--explain"])
        self.assertIsNone(args.command)
        self.assertTrue(args.explain_flag)

    def test_root_parser_parses_explain_command(self):
        parser = build_root_parser()
        args = parser.parse_args(["explain"])
        self.assertEqual(args.command, "explain")

    def test_run_rejects_global_about_flag_with_command(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            status = asyncio.run(run(["--about", "profile", "alice"]))
        self.assertEqual(status, EXIT_USAGE)

    def test_run_handles_modules_catalog_failure(self):
        stream = io.StringIO()
        with patch("core.runner.ensure_module_catalog", side_effect=RuntimeError("catalog_corrupted")):
            with redirect_stdout(stream):
                status = asyncio.run(run(["modules"]))
        self.assertEqual(status, EXIT_FAILURE)
        self.assertIn("Module catalog query failed", stream.getvalue())

    def test_root_live_parser_rejects_invalid_port(self):
        parser = build_root_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["live", "alice", "--port", "70000"])

    def test_safe_path_component_sanitizes_input(self):
        self.assertEqual(safe_path_component(" example.com "), "example.com")
        self.assertEqual(safe_path_component("john/doe"), "john_doe")
        self.assertEqual(safe_path_component("...."), "target")

    def test_split_csv_tokens_supports_comma_and_dedup(self):
        values = _split_csv_tokens(["threat_conductor, contact_lattice", "THREAT_conductor", " "])
        self.assertEqual(values, ["threat_conductor", "contact_lattice"])

    def test_normalize_multi_select_args_expands_modules_fields(self):
        args = argparse.Namespace(
            plugin=["threat_conductor,contact_lattice"],
            filter=["contact_canonicalizer,entity_name_resolver"],
            tag=["identity,pii"],
            scan_type=["syn,udp", "banner"],
        )
        _normalize_multi_select_args(args)
        self.assertEqual(args.plugin, ["threat_conductor", "contact_lattice"])
        self.assertEqual(args.filter, ["contact_canonicalizer", "entity_name_resolver"])
        self.assertEqual(args.tag, ["identity", "pii"])
        self.assertEqual(args.scan_type, ["syn", "udp", "banner"])

    def test_prompt_parser_raises_value_error_for_unknown_command(self):
        parser = build_prompt_parser()
        with self.assertRaises(ValueError):
            parser.parse_args(["unknown-cmd"])

    def test_prompt_parser_parses_explain_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["explain"])
        self.assertEqual(args.command, "explain")

    def test_prompt_parser_parses_capability_pack_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["capability-pack"])
        self.assertEqual(args.command, "capability-pack")

    def test_prompt_parser_parses_intel_alias_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["intel"])
        self.assertEqual(args.command, "intel")

    def test_prompt_parser_parses_modules_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["modules", "--kind", "plugin"])
        self.assertEqual(args.command, "modules")
        self.assertEqual(args.kind, "plugin")

    def test_prompt_parser_parses_frameworks_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["frameworks", "--framework", "graph-registry", "--commands"])
        self.assertEqual(args.command, "frameworks")
        self.assertEqual(args.framework, "graph-registry")
        self.assertTrue(args.commands)

    def test_prompt_parser_parses_surface_kit_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["surface-kit", "example.com", "--preset", "web-basic", "--dry-run"])
        self.assertEqual(args.command, "surface-kit")
        self.assertEqual(args.domain, "example.com")
        self.assertEqual(args.preset, "web-basic")
        self.assertTrue(args.dry_run)

    def test_prompt_parser_parses_quicktest_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["quicktest", "--template", "maya-cipher"])
        self.assertEqual(args.command, "quicktest")
        self.assertEqual(args.template, "maya-cipher")

    def test_prompt_parser_parses_orchestrate_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["orchestrate", "surface", "example.com", "--profile", "fast", "-sS", "-O"])
        self.assertEqual(args.command, "orchestrate")
        self.assertEqual(args.mode, "surface")
        self.assertEqual(args.target, "example.com")
        self.assertEqual(args.profile, "fast")
        self.assertEqual(args.scan_type, ["syn"])
        self.assertTrue(args.os_fingerprint)
        self.assertEqual(args.extension_control, "auto")

    def test_prompt_parser_parses_ocr_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(
            [
                "ocr",
                "one.png",
                "--url",
                "https://example.com/two.png",
                "--preprocess",
                "light",
                "--max-edge",
                "1600",
            ]
        )
        self.assertEqual(args.command, "ocr")
        self.assertEqual(args.paths, ["one.png"])
        self.assertEqual(args.url, ["https://example.com/two.png"])
        self.assertEqual(args.preprocess, "light")
        self.assertEqual(args.max_edge, 1600)

    def test_prompt_parser_parses_wizard_command_with_extended_flags(self):
        parser = build_prompt_parser()
        args = parser.parse_args(
            [
                "wizard",
                "--no-profile-phase",
                "--surface-phase",
                "--domain",
                "example.com",
                "--surface-preset",
                "quick",
                "-sT",
                "-vS",
                "--extension-control",
                "manual",
                "--info-template",
                "surface-risk",
                "--no-html",
                "--no-csv",
                "--no-ct",
                "--rdap",
            ]
        )
        self.assertEqual(args.command, "wizard")
        self.assertFalse(args.run_profile)
        self.assertTrue(args.run_surface)
        self.assertEqual(args.domain, "example.com")
        self.assertEqual(args.surface_preset, "quick")
        self.assertEqual(args.scan_type, ["tcp-connect"])
        self.assertEqual(args.scan_verbosity, "verbose")
        self.assertEqual(args.extension_control, "manual")
        self.assertEqual(args.info_template, "surface-risk")
        self.assertFalse(args.html)
        self.assertFalse(args.csv)
        self.assertFalse(args.ct)
        self.assertTrue(args.rdap)

    def test_templates_parser_parses_json_flag(self):
        parser = build_root_parser()
        args = parser.parse_args(["templates", "--json"])
        self.assertEqual(args.command, "templates")
        self.assertTrue(args.json)


if __name__ == "__main__":
    unittest.main()
