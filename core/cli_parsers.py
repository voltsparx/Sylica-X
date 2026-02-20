"""CLI parser construction helpers for root and prompt modes."""

from __future__ import annotations

import argparse
from typing import NoReturn

from core.cli_config import PROFILE_PRESETS, SURFACE_PRESETS


class InteractiveArgumentParser(argparse.ArgumentParser):
    """Arg parser variant that raises ValueError instead of exiting."""

    def error(self, message: str) -> NoReturn:  # pragma: no cover - argparse hook
        raise ValueError(message)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer.") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")
    return parsed


def valid_port(value: str) -> int:
    port = positive_int(value)
    if port > 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535.")
    return port


def _add_toggle_flags(parser: argparse.ArgumentParser, name: str, label: str) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f"--{name}",
        dest=name,
        action="store_const",
        const=True,
        default=None,
        help=f"Enable {label}.",
    )
    group.add_argument(
        f"--no-{name}",
        dest=name,
        action="store_const",
        const=False,
        help=f"Disable {label}.",
    )


def _add_plugin_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin id/alias to execute (repeatable).",
    )
    parser.add_argument(
        "--all-plugins",
        action="store_true",
        help="Run all plugins compatible with this command scope.",
    )
    parser.add_argument(
        "--list-plugins",
        action="store_true",
        help="List compatible plugins for this scope and exit.",
    )


def _add_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--filter",
        action="append",
        default=[],
        help="Filter id/alias to execute (repeatable).",
    )
    parser.add_argument(
        "--all-filters",
        action="store_true",
        help="Run all filters compatible with this command scope.",
    )
    parser.add_argument(
        "--list-filters",
        action="store_true",
        help="List compatible filters for this scope and exit.",
    )


def _add_plugins_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scope",
        choices=["all", "profile", "surface", "fusion"],
        default="all",
        help="Filter inventory by workflow scope.",
    )


def _add_filters_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scope",
        choices=["all", "profile", "surface", "fusion"],
        default="all",
        help="Filter inventory by workflow scope.",
    )


def _add_history_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=25,
        help="Maximum number of scanned targets to list from output/html.",
    )


def _add_live_args(parser: argparse.ArgumentParser, *, default_dashboard_port: int) -> None:
    parser.add_argument("target", help="Target id for output/data/<target>/results.json.")
    parser.add_argument(
        "--port",
        type=valid_port,
        default=default_dashboard_port,
        help=f"Dashboard port (default: {default_dashboard_port}).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open browser.",
    )


def _add_anonymity_args(parser: argparse.ArgumentParser) -> None:
    _add_toggle_flags(parser, "tor", "Tor routing")
    _add_toggle_flags(parser, "proxy", "HTTP proxy routing")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check anonymity diagnostics (Tor presence/status + active anonymity mode).",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Open interactive anonymity prompts (same as prompt-mode `anonymity`).",
    )


def _add_profile_args(parser: argparse.ArgumentParser, *, default_dashboard_port: int) -> None:
    parser.add_argument("usernames", nargs="+", help="One or more usernames to scan.")
    _add_toggle_flags(parser, "tor", "Tor routing")
    _add_toggle_flags(parser, "proxy", "HTTP proxy routing")
    parser.add_argument(
        "--preset",
        choices=sorted(PROFILE_PRESETS.keys()),
        default="balanced",
        help="Runtime preset for casual and experienced workflows.",
    )
    parser.add_argument(
        "--timeout",
        type=positive_int,
        default=None,
        help="Per-request timeout override in seconds.",
    )
    parser.add_argument(
        "--max-concurrency",
        type=positive_int,
        default=None,
        help="Max concurrent platform requests override.",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Export output/cli/<username>.csv after each scan.",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate and print output/html/<username>.html path after each scan.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Launch live dashboard for scanned username (single username only).",
    )
    parser.add_argument(
        "--live-port",
        type=valid_port,
        default=default_dashboard_port,
        help=f"Live dashboard port (default: {default_dashboard_port}).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open browser for live dashboard.",
    )
    _add_plugin_args(parser)
    _add_filter_args(parser)


def _add_surface_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("domain", help="Domain to scan for attack-surface intelligence.")
    _add_toggle_flags(parser, "tor", "Tor routing")
    _add_toggle_flags(parser, "proxy", "HTTP proxy routing")
    parser.add_argument(
        "--preset",
        choices=sorted(SURFACE_PRESETS.keys()),
        default="balanced",
        help="Runtime preset for casual and experienced workflows.",
    )
    parser.add_argument(
        "--timeout",
        type=positive_int,
        default=None,
        help="HTTP probe timeout override in seconds.",
    )
    parser.add_argument(
        "--max-subdomains",
        type=positive_int,
        default=None,
        help="Maximum CT-derived subdomains to retain.",
    )
    _add_toggle_flags(parser, "ct", "Certificate Transparency lookup")
    _add_toggle_flags(parser, "rdap", "RDAP ownership lookup")
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate and print output/html/<domain>.html.",
    )
    _add_plugin_args(parser)
    _add_filter_args(parser)


def _add_fusion_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("username", help="Username for profile intelligence phase.")
    parser.add_argument("domain", help="Domain for attack-surface intelligence phase.")
    _add_toggle_flags(parser, "tor", "Tor routing")
    _add_toggle_flags(parser, "proxy", "HTTP proxy routing")
    parser.add_argument(
        "--profile-preset",
        choices=sorted(PROFILE_PRESETS.keys()),
        default="balanced",
        help="Preset for profile phase.",
    )
    parser.add_argument(
        "--surface-preset",
        choices=sorted(SURFACE_PRESETS.keys()),
        default="balanced",
        help="Preset for surface phase.",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Export profile phase CSV.",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate combined fusion HTML report.",
    )
    _add_plugin_args(parser)
    _add_filter_args(parser)


def build_root_parser(
    *,
    project_name: str,
    version: str,
    default_dashboard_port: int,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="silica-x.py",
        description=f"{project_name} v{version} OSINT runner (flags + prompt + keyword system).",
    )
    parser.add_argument(
        "--about",
        dest="about_flag",
        action="store_true",
        help="Show framework description and exit.",
    )
    parser.add_argument(
        "--explain",
        dest="explain_flag",
        action="store_true",
        help="Show plain-language command/plugin/filter explanations and exit.",
    )
    subparsers = parser.add_subparsers(dest="command")

    profile_parser = subparsers.add_parser(
        "profile",
        aliases=["scan", "persona", "social"],
        help="Run profile/social username intelligence scan.",
    )
    _add_profile_args(profile_parser, default_dashboard_port=default_dashboard_port)

    surface_parser = subparsers.add_parser(
        "surface",
        aliases=["domain", "asset"],
        help="Run domain attack-surface intelligence scan.",
    )
    _add_surface_args(surface_parser)

    fusion_parser = subparsers.add_parser(
        "fusion",
        aliases=["full", "combo"],
        help="Run profile + surface intelligence as one workflow.",
    )
    _add_fusion_args(fusion_parser)

    live_parser = subparsers.add_parser("live", help="Launch live dashboard for saved results.")
    _add_live_args(live_parser, default_dashboard_port=default_dashboard_port)

    anonymity_parser = subparsers.add_parser(
        "anonymity",
        help="Show or update Tor/proxy settings for this session.",
    )
    _add_anonymity_args(anonymity_parser)

    subparsers.add_parser("keywords", help="List prompt keyword mappings.")
    plugins_parser = subparsers.add_parser("plugins", help="List discovered plugins from plugins/ directory.")
    _add_plugins_args(plugins_parser)
    filters_parser = subparsers.add_parser("filters", help="List discovered filters from filters/ directory.")
    _add_filters_args(filters_parser)
    history_parser = subparsers.add_parser(
        "history",
        aliases=["targets", "scans"],
        help="List scanned targets discovered from output/html reports.",
    )
    _add_history_args(history_parser)
    subparsers.add_parser("help", help="Show command-line usage help.")
    subparsers.add_parser("about", help="Display framework metadata and contact details.")
    subparsers.add_parser("explain", help="Display plain-language workflow, plugin, and filter explanations.")

    wizard_parser = subparsers.add_parser(
        "wizard",
        help="Guided interactive multi-scan workflow.",
    )
    _add_toggle_flags(wizard_parser, "tor", "Tor routing")
    _add_toggle_flags(wizard_parser, "proxy", "HTTP proxy routing")

    prompt_parser = subparsers.add_parser(
        "prompt",
        help="Start interactive prompt mode.",
    )
    _add_toggle_flags(prompt_parser, "tor", "Tor routing")
    _add_toggle_flags(prompt_parser, "proxy", "HTTP proxy routing")

    return parser


def build_prompt_parser(*, default_dashboard_port: int) -> InteractiveArgumentParser:
    parser = InteractiveArgumentParser(prog="", add_help=False)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    profile_parser = subparsers.add_parser(
        "profile",
        aliases=["scan", "persona", "social"],
        add_help=False,
    )
    _add_profile_args(profile_parser, default_dashboard_port=default_dashboard_port)

    surface_parser = subparsers.add_parser(
        "surface",
        aliases=["domain", "asset"],
        add_help=False,
    )
    _add_surface_args(surface_parser)

    fusion_parser = subparsers.add_parser(
        "fusion",
        aliases=["full", "combo"],
        add_help=False,
    )
    _add_fusion_args(fusion_parser)

    live_parser = subparsers.add_parser("live", add_help=False)
    _add_live_args(live_parser, default_dashboard_port=default_dashboard_port)

    anonymity_parser = subparsers.add_parser("anonymity", add_help=False)
    _add_anonymity_args(anonymity_parser)

    subparsers.add_parser("keywords", add_help=False)
    plugins_parser = subparsers.add_parser("plugins", add_help=False)
    _add_plugins_args(plugins_parser)
    filters_parser = subparsers.add_parser("filters", add_help=False)
    _add_filters_args(filters_parser)
    history_parser = subparsers.add_parser("history", aliases=["targets", "scans"], add_help=False)
    _add_history_args(history_parser)
    subparsers.add_parser("help", add_help=False)
    subparsers.add_parser("about", add_help=False)
    subparsers.add_parser("explain", add_help=False)

    wizard_parser = subparsers.add_parser("wizard", add_help=False)
    _add_toggle_flags(wizard_parser, "tor", "Tor routing")
    _add_toggle_flags(wizard_parser, "proxy", "HTTP proxy routing")

    return parser
