import unittest
import asyncio
import io
from contextlib import redirect_stdout

from core.runner import (
    EXIT_USAGE,
    RunnerState,
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
        self.assertEqual(_keyword_to_command("monitor"), "live")
        self.assertEqual(_keyword_to_command("plugins"), "plugins")
        self.assertEqual(_keyword_to_command("addonS"), "plugins")
        self.assertEqual(_keyword_to_command("filters"), "filters")
        self.assertEqual(_keyword_to_command("pii"), "filters")
        self.assertEqual(_keyword_to_command("tor"), "anonymity")
        self.assertEqual(_keyword_to_command("history"), "history")
        self.assertEqual(_keyword_to_command("targets"), "history")
        self.assertEqual(_keyword_to_command("config"), "config")
        self.assertEqual(_keyword_to_command("about"), "about")
        self.assertEqual(_keyword_to_command("info"), "about")
        self.assertEqual(_keyword_to_command("explain"), "explain")
        self.assertEqual(_keyword_to_command("banner"), "banner")
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
                "--no-ct",
                "--html",
                "--all-plugins",
                "--all-filters",
            ]
        )
        self.assertEqual(args.command, "surface")
        self.assertEqual(args.domain, "example.com")
        self.assertEqual(args.preset, "quick")
        self.assertEqual(args.max_subdomains, 100)
        self.assertFalse(args.ct)
        self.assertTrue(args.html)
        self.assertTrue(args.all_plugins)
        self.assertTrue(args.all_filters)

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
        self.assertTrue(args.html)
        self.assertEqual(args.plugin, ["threat_conductor"])
        self.assertEqual(args.filter, ["exposure_tier_matrix"])

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

    def test_history_parser_parses_limit(self):
        parser = build_root_parser()
        args = parser.parse_args(["history", "--limit", "10"])
        self.assertEqual(args.command, "history")
        self.assertEqual(args.limit, 10)

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

    def test_root_live_parser_rejects_invalid_port(self):
        parser = build_root_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["live", "alice", "--port", "70000"])

    def test_safe_path_component_sanitizes_input(self):
        self.assertEqual(safe_path_component(" example.com "), "example.com")
        self.assertEqual(safe_path_component("john/doe"), "john_doe")
        self.assertEqual(safe_path_component("...."), "target")

    def test_prompt_parser_raises_value_error_for_unknown_command(self):
        parser = build_prompt_parser()
        with self.assertRaises(ValueError):
            parser.parse_args(["unknown-cmd"])

    def test_prompt_parser_parses_explain_command(self):
        parser = build_prompt_parser()
        args = parser.parse_args(["explain"])
        self.assertEqual(args.command, "explain")


if __name__ == "__main__":
    unittest.main()
