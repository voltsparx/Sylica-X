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

"""Help menu renderers for flag mode and prompt mode."""

from __future__ import annotations

from collections.abc import Sequence

from core.foundation.colors import Colors, c
from core.foundation.metadata import PROJECT_NAME, VERSION, VERSION_THEME
from core.interface.symbols import symbol

HelpItems = Sequence[tuple[str, str]]
COMMAND_COL_WIDTH = 44
DESCRIPTION_GAP = 6


def _rule(color: str = Colors.BLUE, *, width: int = 118) -> None:
    print(c("=" * width, color))


def _section(title: str, *, color: str = Colors.BLUE, icon: str = "major") -> None:
    print()
    _rule(color)
    print(c(f"  {symbol(icon)} {title}", Colors.BOLD + color))
    _rule(color)


def _item(command: str, description: str) -> None:
    label = command.strip().rstrip(":").strip()
    gap = " " * DESCRIPTION_GAP
    command_label = f"{label}:"
    if len(command_label) > COMMAND_COL_WIDTH:
        print(c(f"  {command_label}", Colors.CYAN))
        print(c(f"  {'':<{COMMAND_COL_WIDTH}}", Colors.CYAN) + c(f"{gap}{description}", Colors.GREY))
        return
    print(c(f"  {command_label:<{COMMAND_COL_WIDTH}}", Colors.CYAN) + c(f"{gap}{description}", Colors.GREY))


def _render_items(items: HelpItems) -> None:
    for command, description in items:
        _item(command, description)


def _example(command: str, description: str) -> None:
    print(c(f"  {symbol('action')} {command}", Colors.YELLOW))
    print(c(f"    {description}", Colors.GREY))


def show_flag_help() -> None:
    print(c(f"\n{PROJECT_NAME} v{VERSION} [{VERSION_THEME}] Flag Help", Colors.BOLD + Colors.CYAN))
    print(c(f"{symbol('action')} Usage: python sylica-x.py <command> [flags]", Colors.GREY))

    _section("Global Flags", icon="feature")
    _render_items(
        (
            ("--about:", "Show framework description and exit."),
            ("--explain:", "Show plain-language command and extension guide and exit."),
        )
    )

    _section("Primary Workflows")
    _render_items(
        (
            ("profile <username...>:", "Scan usernames for profile intelligence."),
            ("surface <domain>:", "Scan a domain for surface exposure signals."),
            ("fusion <username> <domain>:", "Run profile and surface workflows together with unified footprint mapping."),
            ("orchestrate <mode> <target>:", "Run policy-driven layered orchestration."),
            ("wizard:", "Run guided workflow questions."),
            ("quicktest [flags]:", "Run one random built-in victim template with report outputs."),
            ("surface-kit [domain] [flags]:", "Translate local source recipes into a native Sylica-X surface run."),
        )
    )

    _section("Inventory and Utility")
    _render_items(
        (
            ("plugins [--scope ...]:", "List available plugins."),
            ("filters [--scope ...]:", "List available filters."),
            ("templates [--json]:", "List bundled info-templates for focused arrangements."),
            ("modules [query flags]:", "List/sync/query source-intel module catalog."),
            ("frameworks [flags]:", "Inspect local source-profile intel from temp/ study trees."),
            ("history [--limit N]:", "List previously scanned targets."),
            ("live <target> [--port]:", "Open local live dashboard."),
            ("anonymity [flags]:", "Check or change Tor/proxy routing."),
            ("keywords:", "Show prompt keyword shortcuts."),
            ("about | explain | prompt | help:", "Metadata, explainers, interactive mode, help."),
        )
    )

    _section("Extension and Routing Controls")
    _render_items(
        (
            (
                "--plugin:",
                "Enable explicit plugins (repeatable/comma-separated selectors).",
            ),
            (
                "--filter:",
                "Enable explicit filters (repeatable/comma-separated selectors).",
            ),
            (
                "--info-template <id>:",
                "Apply a curated plugin/filter/module arrangement (consent-only targets).",
            ),
            (
                "--extension-control <mode>:",
                "auto | manual | hybrid (fail-fast conflict validation)",
            ),
            ("wizard preflight:", "Wizard validates extension compatibility before scans."),
            ("--tor / --proxy:", "Enable Tor/proxy routing."),
            ("--no-tor / --no-proxy:", "Disable Tor/proxy routing."),
            ("--check / --prompt:", "Run diagnostics or guided anonymity setup."),
        )
    )

    _section("Output")
    _render_items(
        (
            ("out-type <types>:", "Set persisted output formats (cli, html, csv, json)."),
            ("out-print <path>:", "Set current output base directory for this session."),
            ("default-out-print <path>:", "Set persisted default output base directory."),
            ("--html/--no-html --csv/--no-csv:", "Enable or disable HTML/CSV artifacts for this run."),
            ("wizard --help:", "Show full wizard flags (phases, presets, selectors, toggles)."),
            ("output/json output/html output/cli output/csv output/logs:", "Default artifact directories."),
        )
    )

    _section("Quick Start", icon="tip")
    _example(
        "python sylica-x.py profile alice --preset deep --plugin threat_conductor --html --csv:",
        "Run profile intelligence with explicit plugin selection and full artifacts.",
    )
    _example(
        "python sylica-x.py orchestrate fusion alice --secondary-target example.com --html:",
        "Run orchestration in fusion mode with HTML reporting.",
    )
    print()


def show_prompt_help() -> None:
    print(c(f"\n{PROJECT_NAME} v{VERSION} [{VERSION_THEME}] Prompt Help", Colors.BOLD + Colors.CYAN))
    print(c(f"{symbol('action')} Type one command and press Enter.", Colors.GREY))

    _section("Workflow Commands")
    _render_items(
        (
            ("scan <username>:", "Quick profile alias."),
            ("profile <username...>:", "Run profile workflow with digital footprint mapping."),
            ("surface <domain>:", "Run surface workflow."),
            ("surface <domain> --recon-mode <...>:", "Choose passive, active, or hybrid reconnaissance."),
            ("fusion <username> <domain>:", "Run fusion workflow with profile, web, and surface linkage summary."),
            ("orchestrate <mode> <target>:", "Run layered orchestration."),
            ("surface-kit <domain> --preset <name>:", "Use local source recipes to drive a Sylica-X surface plan."),
            ("quicktest [flags]:", "Run one random built-in victim template."),
            ("wizard:", "Guided workflow with prompts."),
        )
    )

    _section("Inventory and Session")
    _render_items(
        (
            ("show plugins | show filters | show modules:", "Inventory and module intelligence catalog."),
            ("show frameworks:", "Inspect local source-profile inventory."),
            ("show templates:", "List bundled info-templates."),
            ("show history [--limit N]:", "List previously scanned targets."),
            ("show config:", "Show prompt defaults and active module."),
            ("surface ... --recon-mode passive|active|hybrid:", "Control surface collection lane depth and noise."),
            ("out-type <types>:", "Set persisted output formats (cli, html, csv, json)."),
            ("out-print <path>:", "Set current output base directory for this session."),
            ("default-out-print <path>:", "Set persisted default output base directory."),
            ("anonymity [flags]:", "Check or change Tor/proxy routing."),
            ("show keywords:", "Show all prompt shortcut aliases."),
            ("about | explain | help | clear | exit:", "Metadata, docs, help, clear screen, quit."),
        )
    )

    _section("Selection Controls")
    _render_items(
        (
            ("use <profile|surface|fusion>:", "Switch active module context."),
            ("select module <profile|surface|fusion>:", "Alias for `use` module switch by name."),
            (
                "set plugins <none|a,b>:",
                "Set module-compatible plugins (strict compatibility checks).",
            ),
            (
                "set filters <none|a,b>:",
                "Set module-compatible filters (strict compatibility checks).",
            ),
            ("set template <id>:", "Apply a bundled info-template to plugin/filter defaults."),
            ("select plugins <a,b>:", "Alias for `set plugins` (name-based selectors)."),
            ("select filters <a,b>:", "Alias for `set filters` (name-based selectors)."),
            ("select template <id>:", "Alias for `set template`."),
            ("add plugins <a,b> / remove plugins <a,b>:", "Incremental plugin control by name."),
            ("add filters <a,b> / remove filters <a,b>:", "Incremental filter control by name."),
        )
    )

    _section("Defaults and Modes")
    _render_items(
        (
            ("set profile_preset <...>:", "Default profile preset."),
            ("set surface_preset <...>:", "Default surface preset."),
            ("set extension_control <...>:", "Default control mode for active module."),
            ("set orchestrate_extension_control <...>:", "Default control mode for orchestrate."),
        )
    )

    _section("Prompt Format")
    print(c(f"  {symbol('feature')} sx(<module>)>", Colors.CYAN))
    print(c(f"  {symbol('tip')} A trailing `*` means the current module has custom selectors or control settings.", Colors.GREY))
    print(c(f"  {symbol('tip')} Run `show config` for the full session context.", Colors.GREY))

    _section("Prompt Examples", icon="tip")
    _example("show plugins:", "List plugin inventory.")
    _example("show frameworks:", "Inspect the local source-profile inventory and architecture references.")
    _example("use fusion:", "Switch prompt context to fusion workflows.")
    _example("surface-kit example.com --preset subdomain-enum --dry-run:", "Preview the translated Sylica-X plan for a source recipe.")
    _example("set plugins threat_conductor,signal_fusion_core:", "Set plugin defaults by name.")
    _example("quicktest --seed 7 --html --csv:", "Run deterministic synthetic smoke with reports.")
    print()


def show_help() -> None:
    # Backward-compatible wrapper
    show_prompt_help()
