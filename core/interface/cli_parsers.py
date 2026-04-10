# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Sylica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Sylica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Sylica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

"""CLI parser construction helpers for root and prompt modes."""

from __future__ import annotations

import argparse
from typing import NoReturn

from core.interface.cli_config import EXTENSION_CONTROL_MODES, PROFILE_PRESETS, SURFACE_PRESETS, SURFACE_RECON_MODES
from core.interface.command_spec import (
    FUSION_COMMAND_ALIASES,
    ORCHESTRATE_COMMAND_ALIASES,
    PROFILE_COMMAND_ALIASES,
    SURFACE_COMMAND_ALIASES,
)

MODULE_SORT_FIELDS = [
    "file",
    "kind",
    "power_score",
    "confidence_score",
    "plugin_score",
    "filter_score",
    "profile_score",
    "surface_score",
    "fusion_score",
    "capability_count",
]


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


def non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer.") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("Value must be zero or greater.")
    return parsed


def non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be a number.") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("Value must be zero or greater.")
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


def _add_phase_toggle(
    parser: argparse.ArgumentParser,
    *,
    flag_name: str,
    dest: str,
    label: str,
) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f"--{flag_name}",
        dest=dest,
        action="store_const",
        const=True,
        default=None,
        help=f"Enable {label}.",
    )
    group.add_argument(
        f"--no-{flag_name}",
        dest=dest,
        action="store_const",
        const=False,
        help=f"Disable {label}.",
    )


def _add_plugin_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        help="Plugin selector (id/alias/name), repeatable or comma-separated.",
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
        help="Filter selector (id/alias/name), repeatable or comma-separated.",
    )
    parser.add_argument(
        "--list-filters",
        action="store_true",
        help="List compatible filters for this scope and exit.",
    )


def _add_info_template_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--info-template",
        default="",
        help="Apply a bundled info-template (curated plugin/filter/module arrangement; consent-only targets).",
    )


def _add_extension_control_args(parser: argparse.ArgumentParser, *, default_mode: str) -> None:
    parser.add_argument(
        "--extension-control",
        choices=list(EXTENSION_CONTROL_MODES),
        default=default_mode,
        help="Extension control mode: auto, manual, or hybrid.",
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


def _add_modules_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scope",
        choices=["all", "profile", "surface", "fusion"],
        default="all",
        help="Filter module catalog by workflow scope.",
    )
    parser.add_argument(
        "--kind",
        choices=["all", "plugin", "filter"],
        default="all",
        help="Select catalog kind to display.",
    )
    parser.add_argument(
        "--search",
        default="",
        help="Full-text search across module id/path/capabilities.",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Capability tag filter (repeatable or comma-separated).",
    )
    parser.add_argument(
        "--min-score",
        type=non_negative_int,
        default=0,
        help="Minimum power score threshold (0-100).",
    )
    parser.add_argument(
        "--sort-by",
        choices=MODULE_SORT_FIELDS,
        default="file",
        help="Sort field for module listing.",
    )
    parser.add_argument(
        "--descending",
        action="store_true",
        help="Sort in descending order.",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=50,
        help="Maximum number of module entries to show.",
    )
    parser.add_argument(
        "--offset",
        type=non_negative_int,
        default=0,
        help="Entry offset for paginated module browsing.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Rebuild module catalog from intel-sources before listing.",
    )
    _add_info_template_args(parser)
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate catalog integrity and source drift before listing.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print modules view as JSON payload.",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Print summary stats only without listing entries.",
    )


def _add_frameworks_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--framework",
        choices=["all", "recursive-modules", "graph-registry", "console-shell"],
        default="all",
        help="Show local source-profile intel for a specific temp/ reference tree.",
    )
    parser.add_argument(
        "--modules",
        action="store_true",
        help="List modules discovered from the recursive-module source profile.",
    )
    parser.add_argument(
        "--presets",
        action="store_true",
        help="List recipes discovered from the recursive-module source profile.",
    )
    parser.add_argument(
        "--flags",
        action="store_true",
        help="List flags discovered from the recursive-module source profile.",
    )
    parser.add_argument(
        "--commands",
        action="store_true",
        help="List discovered command capabilities for the selected framework.",
    )
    parser.add_argument(
        "--search",
        default="",
        help="Filter module/recipe/flag output by search text.",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=25,
        help="Maximum number of rows to show for module/preset/flag listings.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print source-profile intel as JSON payload.",
    )


def _add_surface_kit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "domain",
        nargs="?",
        default="",
        help="Domain to translate into a source-derived Sylica-X surface run.",
    )
    _add_toggle_flags(parser, "tor", "Tor routing")
    _add_toggle_flags(parser, "proxy", "HTTP proxy routing")
    parser.add_argument(
        "--preset",
        default="subdomain-enum",
        help="Recipe name discovered from the recursive-module source profile.",
    )
    parser.add_argument(
        "--module",
        action="append",
        default=[],
        help="Narrow the source-derived plan to specific module names.",
    )
    parser.add_argument(
        "--require-flag",
        action="append",
        default=[],
        help="Require source flags when building the native Sylica-X plan.",
    )
    parser.add_argument(
        "--exclude-flag",
        action="append",
        default=[],
        help="Exclude source flags when building the native Sylica-X plan.",
    )
    parser.add_argument(
        "--recon-mode",
        choices=list(SURFACE_RECON_MODES),
        default=None,
        help="Override the translated Sylica-X recon mode.",
    )
    parser.add_argument(
        "--list-modules",
        action="store_true",
        help="List modules discovered from the recursive-module source profile.",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List recipes discovered from the recursive-module source profile.",
    )
    parser.add_argument(
        "--list-flags",
        action="store_true",
        help="List flags discovered from the recursive-module source profile.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the translated Sylica-X execution plan without running a scan.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print surface-kit planning output as JSON payload.",
    )
    parser.add_argument(
        "--search",
        default="",
        help="Filter listing output by search text.",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=25,
        help="Maximum number of listing rows to show.",
    )
    _add_toggle_flags(
        parser,
        "html",
        "HTML report output/html/<target>-info-<timestamp>.html",
    )
    _add_toggle_flags(
        parser,
        "csv",
        "CSV export output/csv/<target>-info-<timestamp>.csv",
    )
    parser.add_argument(
        "--out-type",
        default="",
        help="Override output formats for this run only (comma-separated, non-persistent).",
    )
    parser.add_argument(
        "--out-print",
        default="",
        help="Override output base directory for this run only (non-persistent).",
    )


def _add_history_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=25,
        help="Maximum number of scanned targets to list from output/json and output/html.",
    )


def _add_quicktest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--template",
        default="",
        help="Template id override; when omitted one of five templates is selected randomly.",
    )
    parser.add_argument(
        "--seed",
        type=non_negative_int,
        default=None,
        help="Random seed for deterministic template choice (used only when --template is omitted).",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List bundled quicktest templates and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the generated quicktest payload as JSON after report generation.",
    )
    parser.add_argument(
        "--out-type",
        default="",
        help="Override output formats for this run only (comma-separated, non-persistent).",
    )
    parser.add_argument(
        "--out-print",
        default="",
        help="Override output base directory for this run only (non-persistent).",
    )


def _add_live_args(parser: argparse.ArgumentParser, *, default_dashboard_port: int) -> None:
    parser.add_argument("target", help="Target id (latest) for output/json/<target>-info-<timestamp>.json.")
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


def _add_surface_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scan-type",
        "--scan-types",
        dest="scan_type",
        action="append",
        default=[],
        help=(
            "Attack-surface scan directives (repeatable or comma-separated): "
            "arp, syn, tcp-connect, udp, fin, null, xmas, service, tls."
        ),
    )
    parser.add_argument("-aS", dest="scan_type", action="append_const", const="arp", help="Add ARP discovery intent.")
    parser.add_argument("-sS", dest="scan_type", action="append_const", const="syn", help="Add SYN scan intent.")
    parser.add_argument("-sT", dest="scan_type", action="append_const", const="tcp-connect", help="Add TCP connect scan intent.")
    parser.add_argument("-sU", dest="scan_type", action="append_const", const="udp", help="Add UDP scan intent.")
    parser.add_argument("-sF", dest="scan_type", action="append_const", const="fin", help="Add FIN scan intent.")
    parser.add_argument("-sN", dest="scan_type", action="append_const", const="null", help="Add NULL scan intent.")
    parser.add_argument("-sX", dest="scan_type", action="append_const", const="xmas", help="Add XMAS scan intent.")
    parser.add_argument("-sV", dest="scan_type", action="append_const", const="service", help="Add service version inquiry intent.")
    parser.add_argument(
        "--scan-verbosity",
        choices=["standard", "verbose"],
        default=None,
        help="Surface scan-plan verbosity for CLI, prompt, and report rendering.",
    )
    parser.add_argument(
        "-vS",
        dest="scan_verbosity",
        action="store_const",
        const="verbose",
        help="Enable verbose scan-plan rendering.",
    )
    parser.add_argument(
        "--scan-delay",
        type=non_negative_float,
        default=None,
        help="Delay between active service inquiries in seconds.",
    )
    _add_phase_toggle(
        parser,
        flag_name="os-fingerprint",
        dest="os_fingerprint",
        label="read-only OS fingerprint inference",
    )
    parser.add_argument(
        "-O",
        dest="os_fingerprint",
        action="store_const",
        const=True,
        default=None,
        help="Enable OS fingerprint inference controls.",
    )
    parser.add_argument(
        "--list-scan-types",
        action="store_true",
        help="List supported attack-surface scan directives and exit.",
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
    _add_toggle_flags(
        parser,
        "csv",
        "CSV export output/csv/<target>-info-<timestamp>.csv",
    )
    _add_toggle_flags(
        parser,
        "html",
        "HTML report output/html/<target>-info-<timestamp>.html",
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
    parser.add_argument(
        "--out-type",
        default="",
        help="Override output formats for this run only (comma-separated, non-persistent).",
    )
    parser.add_argument(
        "--out-print",
        default="",
        help="Override output base directory for this run only (non-persistent).",
    )
    _add_info_template_args(parser)
    _add_plugin_args(parser)
    _add_filter_args(parser)
    _add_extension_control_args(parser, default_mode="manual")


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
    parser.add_argument(
        "--recon-mode",
        choices=list(SURFACE_RECON_MODES),
        default=None,
        help="Surface reconnaissance lane: passive, active, or hybrid.",
    )
    _add_surface_scan_args(parser)
    _add_toggle_flags(parser, "ct", "Certificate Transparency lookup")
    _add_toggle_flags(parser, "rdap", "RDAP ownership lookup")
    _add_toggle_flags(
        parser,
        "html",
        "HTML report output/html/<target>-info-<timestamp>.html",
    )
    _add_toggle_flags(
        parser,
        "csv",
        "CSV export output/csv/<target>-info-<timestamp>.csv",
    )
    parser.add_argument(
        "--out-type",
        default="",
        help="Override output formats for this run only (comma-separated, non-persistent).",
    )
    parser.add_argument(
        "--out-print",
        default="",
        help="Override output base directory for this run only (non-persistent).",
    )
    _add_info_template_args(parser)
    _add_plugin_args(parser)
    _add_filter_args(parser)
    _add_extension_control_args(parser, default_mode="manual")


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
        "--surface-recon-mode",
        choices=list(SURFACE_RECON_MODES),
        default=None,
        help="Recon lane for the fusion surface phase: passive, active, or hybrid.",
    )
    _add_surface_scan_args(parser)
    _add_toggle_flags(
        parser,
        "csv",
        "CSV export output/csv/<target>-info-<timestamp>.csv",
    )
    _add_toggle_flags(
        parser,
        "html",
        "HTML report output/html/<target>-info-<timestamp>.html",
    )
    parser.add_argument(
        "--out-type",
        default="",
        help="Override output formats for this run only (comma-separated, non-persistent).",
    )
    parser.add_argument(
        "--out-print",
        default="",
        help="Override output base directory for this run only (non-persistent).",
    )
    _add_info_template_args(parser)
    _add_plugin_args(parser)
    _add_filter_args(parser)
    _add_extension_control_args(parser, default_mode="manual")


def _add_orchestrate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "mode",
        choices=["profile", "surface", "fusion"],
        help="Orchestration mode.",
    )
    parser.add_argument(
        "target",
        help="Primary target (username for profile/fusion, domain for surface).",
    )
    parser.add_argument(
        "--secondary-target",
        default="",
        help="Secondary target (required for fusion mode: domain).",
    )
    _add_toggle_flags(parser, "tor", "Tor routing")
    _add_toggle_flags(parser, "proxy", "HTTP proxy routing")
    _add_toggle_flags(parser, "ct", "Certificate Transparency lookup")
    _add_toggle_flags(parser, "rdap", "RDAP ownership lookup")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_PRESETS.keys()),
        default="balanced",
        help="Execution policy profile.",
    )
    parser.add_argument(
        "--timeout",
        type=positive_int,
        default=None,
        help="Task timeout override in seconds.",
    )
    parser.add_argument(
        "--max-workers",
        type=positive_int,
        default=None,
        help="Max orchestration workers override.",
    )
    parser.add_argument(
        "--source-profile",
        choices=["fast", "quick", "balanced", "deep", "max"],
        default=None,
        help="Source selection profile for username collection.",
    )
    parser.add_argument(
        "--max-platforms",
        type=positive_int,
        default=None,
        help="Maximum profile platforms for username collection.",
    )
    parser.add_argument(
        "--max-subdomains",
        type=positive_int,
        default=None,
        help="Maximum CT-derived subdomains for domain collection.",
    )
    parser.add_argument(
        "--recon-mode",
        choices=list(SURFACE_RECON_MODES),
        default=None,
        help="Surface reconnaissance lane for surface/fusion orchestration.",
    )
    _add_surface_scan_args(parser)
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.25,
        help="Minimum confidence threshold for orchestration filter pipeline (0.0-1.0).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full orchestration payload as JSON.",
    )
    _add_toggle_flags(
        parser,
        "html",
        "HTML report output/html/<target>-info-<timestamp>.html",
    )
    _add_toggle_flags(
        parser,
        "csv",
        "CSV export output/csv/<target>-info-<timestamp>.csv",
    )
    parser.add_argument(
        "--out-type",
        default="",
        help="Override output formats for this run only (comma-separated, non-persistent).",
    )
    parser.add_argument(
        "--out-print",
        default="",
        help="Override output base directory for this run only (non-persistent).",
    )
    _add_info_template_args(parser)
    _add_plugin_args(parser)
    _add_filter_args(parser)
    _add_extension_control_args(parser, default_mode="auto")


def _add_wizard_args(parser: argparse.ArgumentParser) -> None:
    _add_toggle_flags(parser, "tor", "Tor routing")
    _add_toggle_flags(parser, "proxy", "HTTP proxy routing")
    _add_phase_toggle(parser, flag_name="profile-phase", dest="run_profile", label="profile phase")
    _add_phase_toggle(parser, flag_name="surface-phase", dest="run_surface", label="surface phase")
    _add_phase_toggle(parser, flag_name="fusion-phase", dest="run_fusion", label="fusion phase")
    parser.add_argument(
        "--usernames",
        default="",
        help="Comma-separated usernames for profile phase (skip username prompt).",
    )
    parser.add_argument(
        "--domain",
        default="",
        help="Domain for surface phase (skip domain prompt).",
    )
    parser.add_argument(
        "--profile-preset",
        choices=sorted(PROFILE_PRESETS.keys()),
        default=None,
        help="Default profile preset inside wizard workflow.",
    )
    parser.add_argument(
        "--surface-preset",
        choices=sorted(SURFACE_PRESETS.keys()),
        default=None,
        help="Default surface preset inside wizard workflow.",
    )
    parser.add_argument(
        "--surface-recon-mode",
        choices=list(SURFACE_RECON_MODES),
        default=None,
        help="Default reconnaissance lane for wizard surface workflows.",
    )
    _add_surface_scan_args(parser)
    parser.add_argument(
        "--out-type",
        default="",
        help="Override output formats for this wizard run only (comma-separated, non-persistent).",
    )
    parser.add_argument(
        "--out-print",
        default="",
        help="Override output base directory for this wizard run only (non-persistent).",
    )
    parser.add_argument(
        "--extension-control",
        choices=list(EXTENSION_CONTROL_MODES),
        default=None,
        help="Wizard extension control mode: auto, manual, or hybrid.",
    )
    _add_toggle_flags(parser, "html", "HTML report output")
    _add_toggle_flags(parser, "csv", "profile/fusion CSV export")
    _add_toggle_flags(parser, "ct", "Certificate Transparency lookup")
    _add_toggle_flags(parser, "rdap", "RDAP ownership lookup")
    parser.add_argument(
        "--sync-modules",
        action="store_true",
        help="Refresh module catalog before wizard execution.",
    )
    _add_info_template_args(parser)
    _add_plugin_args(parser)
    _add_filter_args(parser)


def build_root_parser(
    *,
    project_name: str,
    version: str,
    default_dashboard_port: int,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sylica-x.py",
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
        PROFILE_COMMAND_ALIASES[0],
        aliases=list(PROFILE_COMMAND_ALIASES[1:]),
        help="Run profile/social username intelligence scan.",
    )
    _add_profile_args(profile_parser, default_dashboard_port=default_dashboard_port)

    surface_parser = subparsers.add_parser(
        SURFACE_COMMAND_ALIASES[0],
        aliases=list(SURFACE_COMMAND_ALIASES[1:]),
        help="Run domain attack-surface intelligence scan.",
    )
    _add_surface_args(surface_parser)

    fusion_parser = subparsers.add_parser(
        FUSION_COMMAND_ALIASES[0],
        aliases=list(FUSION_COMMAND_ALIASES[1:]),
        help="Run profile + surface intelligence as one workflow.",
    )
    _add_fusion_args(fusion_parser)

    orchestrate_parser = subparsers.add_parser(
        ORCHESTRATE_COMMAND_ALIASES[0],
        aliases=list(ORCHESTRATE_COMMAND_ALIASES[1:]),
        help="Run policy-driven layered orchestration pipeline.",
    )
    _add_orchestrate_args(orchestrate_parser)

    frameworks_parser = subparsers.add_parser(
        "frameworks",
        help="Inspect local source-profile intel from temp/.",
    )
    _add_frameworks_args(frameworks_parser)

    surface_kit_parser = subparsers.add_parser(
        "surface-kit",
        help="Use local source-study recipes to plan or run a native Sylica-X surface workflow.",
    )
    _add_surface_kit_args(surface_kit_parser)

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
    templates_parser = subparsers.add_parser(
        "templates",
        aliases=["info-templates"],
        help="List bundled info-templates for plugin/filter/module arrangements.",
    )
    templates_parser.add_argument(
        "--json",
        action="store_true",
        help="Print info-templates as JSON payload.",
    )
    out_type_parser = subparsers.add_parser("out-type", help="Set output formats (cli, html, csv, json).")
    out_type_parser.add_argument(
        "types",
        nargs="*",
        help="Comma-separated output types or a list (example: cli,html,csv,json).",
    )
    out_print_parser = subparsers.add_parser("out-print", help="Set output base directory for this session.")
    out_print_parser.add_argument(
        "path",
        nargs="?",
        default="",
        help="Base directory where the output folder will be created.",
    )
    default_out_print_parser = subparsers.add_parser(
        "default-out-print",
        help="Set default output base directory (persisted).",
    )
    default_out_print_parser.add_argument(
        "path",
        nargs="?",
        default="",
        help="Base directory where the output folder will be created.",
    )
    modules_parser = subparsers.add_parser(
        "modules",
        help="List/sync source-intel module catalog discovered from intel-sources.",
    )
    _add_modules_args(modules_parser)
    history_parser = subparsers.add_parser(
        "history",
        aliases=["targets", "scans"],
        help="List scanned targets discovered from output/json and output/html artifacts.",
    )
    _add_history_args(history_parser)
    quicktest_parser = subparsers.add_parser(
        "quicktest",
        aliases=["qtest", "smoke"],
        help="Run an offline quicktest using one random built-in victim template.",
    )
    _add_quicktest_args(quicktest_parser)
    subparsers.add_parser("help", help="Show command-line usage help.")
    subparsers.add_parser("about", help="Display framework metadata and contact details.")
    subparsers.add_parser("explain", help="Display plain-language workflow, plugin, and filter explanations.")
    subparsers.add_parser(
        "capability-pack",
        aliases=["intel"],
        help="Generate Sylica-X capability-pack folders and report artifacts.",
    )

    wizard_parser = subparsers.add_parser(
        "wizard",
        help="Guided interactive multi-scan workflow.",
    )
    _add_wizard_args(wizard_parser)

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
        PROFILE_COMMAND_ALIASES[0],
        aliases=list(PROFILE_COMMAND_ALIASES[1:]),
        add_help=False,
    )
    _add_profile_args(profile_parser, default_dashboard_port=default_dashboard_port)

    surface_parser = subparsers.add_parser(
        SURFACE_COMMAND_ALIASES[0],
        aliases=list(SURFACE_COMMAND_ALIASES[1:]),
        add_help=False,
    )
    _add_surface_args(surface_parser)

    fusion_parser = subparsers.add_parser(
        FUSION_COMMAND_ALIASES[0],
        aliases=list(FUSION_COMMAND_ALIASES[1:]),
        add_help=False,
    )
    _add_fusion_args(fusion_parser)

    orchestrate_parser = subparsers.add_parser(
        ORCHESTRATE_COMMAND_ALIASES[0],
        aliases=list(ORCHESTRATE_COMMAND_ALIASES[1:]),
        add_help=False,
    )
    _add_orchestrate_args(orchestrate_parser)

    frameworks_parser = subparsers.add_parser("frameworks", add_help=False)
    _add_frameworks_args(frameworks_parser)

    surface_kit_parser = subparsers.add_parser("surface-kit", add_help=False)
    _add_surface_kit_args(surface_kit_parser)

    live_parser = subparsers.add_parser("live", add_help=False)
    _add_live_args(live_parser, default_dashboard_port=default_dashboard_port)

    anonymity_parser = subparsers.add_parser("anonymity", add_help=False)
    _add_anonymity_args(anonymity_parser)

    subparsers.add_parser("keywords", add_help=False)
    plugins_parser = subparsers.add_parser("plugins", add_help=False)
    _add_plugins_args(plugins_parser)
    filters_parser = subparsers.add_parser("filters", add_help=False)
    _add_filters_args(filters_parser)
    templates_parser = subparsers.add_parser("templates", aliases=["info-templates"], add_help=False)
    templates_parser.add_argument("--json", action="store_true")
    out_type_parser = subparsers.add_parser("out-type", add_help=False)
    out_type_parser.add_argument("types", nargs="*", default=[])
    out_print_parser = subparsers.add_parser("out-print", add_help=False)
    out_print_parser.add_argument("path", nargs="?", default="")
    default_out_print_parser = subparsers.add_parser("default-out-print", add_help=False)
    default_out_print_parser.add_argument("path", nargs="?", default="")
    modules_parser = subparsers.add_parser("modules", add_help=False)
    _add_modules_args(modules_parser)
    history_parser = subparsers.add_parser("history", aliases=["targets", "scans"], add_help=False)
    _add_history_args(history_parser)
    quicktest_parser = subparsers.add_parser("quicktest", aliases=["qtest", "smoke"], add_help=False)
    _add_quicktest_args(quicktest_parser)
    subparsers.add_parser("help", add_help=False)
    subparsers.add_parser("about", add_help=False)
    subparsers.add_parser("explain", add_help=False)
    subparsers.add_parser("capability-pack", aliases=["intel"], add_help=False)

    wizard_parser = subparsers.add_parser("wizard", add_help=False)
    _add_wizard_args(wizard_parser)

    return parser
