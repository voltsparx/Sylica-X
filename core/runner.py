# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

"""Main runner orchestration for Silica-X."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
import difflib
import html
import json
import os
import shlex
import sys
import threading
import webbrowser
from datetime import datetime
from dataclasses import dataclass
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any

from core.interface.banner import show_banner
from core.collect.anonymity import TOR_HOST, TOR_SOCKS_PORT, install_tor, probe_tor_status, start_tor
from core.interface.about import build_about_text
from core.interface.explain import build_explain_text
from core.interface.cli_config import EXTENSION_CONTROL_MODES, OCR_PRESETS, PROFILE_PRESETS, PROMPT_KEYWORDS, SURFACE_PRESETS
from core.interface.command_spec import (
    OCR_COMMAND_ALIASES,
    SurfaceScanDirectives,
    invalid_surface_scan_types,
    resolve_surface_scan_directives,
    surface_scan_type_specs,
)
from core.interface.cli_parsers import build_prompt_parser as _build_prompt_parser
from core.interface.cli_parsers import build_root_parser as _build_root_parser
from core.foundation.colors import Colors, c
from core.analyze.correlator import correlate
from core.artifacts.csv_export import export_to_csv
from core.collect.domain_intel import normalize_domain, scan_domain_surface
from core.analyze.exposure import assess_domain_exposure, assess_profile_exposure, summarize_issues
from core.extensions.signal_sieve import execute_filters, list_filter_descriptors, list_filter_discovery_errors
from core.interface.help_menu import show_flag_help, show_prompt_help
from core.interface.loading import run_with_spinner
from core.artifacts.html_report import generate_html
from core.engines.fusion_engine import FusionEngine
from core.intel.advisor import IntelligenceAdvisor
from core.intel.hybrid_architecture import build_hybrid_architecture_snapshot, render_hybrid_inventory_lines
from core.extensions.control_plane import merge_scan_modes, resolve_extension_control
from core.extensions.attachables import resolve_module_attachments
from core.interface.symbols import symbol
from core.orchestrator import Orchestrator
from core.foundation.metadata import PROJECT_NAME, VERSION, framework_signature, utc_timestamp
from core.foundation.output_config import (
    DEFAULT_OUTPUT_TYPES,
    OutputConfigError,
    clear_output_base_dir,
    clear_session_output_base_dir,
    describe_output_settings,
    get_output_settings,
    get_session_output_base_dir,
    parse_output_types,
    set_session_output_base_dir,
    set_session_output_types,
    tokenize_output_types,
    update_output_base_dir,
    update_output_types,
)
from core.analyze.narrative import build_nano_brief
from core.collect.network import get_network_settings
from modules.catalog import ensure_module_catalog, query_module_catalog, summarize_module_catalog
from core.artifacts.output import (
    append_framework_log,
    display_domain_results,
    display_ocr_results,
    display_results,
    list_scanned_targets,
    save_results,
)
from core.extensions.plugin_manager import PluginManager
from core.intel.prompt_engine import PromptEngine
from core.artifacts.reporting import ReportGenerator
from core.intel.capability_matrix import (
    build_capability_pack,
    build_runtime_inventory_snapshot,
    write_capability_report,
    write_runtime_inventory_snapshot,
)
from core.intel.recon_sources import (
    build_surface_recipe_plan,
    filter_recipe_flags,
    filter_recipe_modules,
    filter_recipes,
    load_console_shell_reference,
    load_graph_registry_reference,
    load_recursive_module_reference,
    load_source_inventory,
)
from core.extensions.signal_forge import list_plugin_descriptors, list_plugin_discovery_errors
from core.collect.platform_schema import PlatformValidationError, load_platforms
from core.analyze.profile_summary import error_profile_rows, found_profile_rows, summarize_target_intel
from core.analyze.surface_map import build_surface_map, build_surface_next_steps
from core.analyze.digital_footprint import build_digital_footprint_map
from core.collect.scanner import scan_username
from core.collect.ocr_image_scan import OCRImageScanResult
from core.engines.ocr_image_scan_engine import OCRImageScanEngine
from core.domain import BaseEntity
from core.foundation.session_state import PromptSessionState
from core.intelligence import IntelligenceEngine
from core.intelligence.entity_builder import build_fusion_entities, build_profile_entities, build_surface_entities
from core.packet_crafting import build_surface_packet_crafting_plan
from core.artifacts.storage import (
    cli_report_path,
    ensure_output_tree,
    html_report_path,
    latest_results_json_path,
    results_json_path,
    run_log_path,
    sanitize_target,
)
from core.utils.quicktest_data import list_quicktest_templates, pick_quicktest_template
from core.utils.info_templates import get_info_template, list_info_templates, merge_selectors
from core.prompt_handlers import (
    apply_prompt_defaults as _apply_prompt_defaults_impl,
    handle_prompt_control_command as _handle_prompt_control_command_impl,
    handle_prompt_set_command as _handle_prompt_set_command_impl,
    handle_prompt_use_command as _handle_prompt_use_command_impl,
    keyword_to_command as _keyword_to_command_impl,
    rewrite_tokens_with_keywords as _rewrite_tokens_with_keywords_impl,
)


DEFAULT_DASHBOARD_PORT = 8000
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
PROMPT_SHOW_COMMANDS = {"plugins", "filters", "modules", "frameworks", "history", "keywords", "config", "templates"}


def _prompt_command_catalog() -> list[str]:
    commands = {
        "about",
        "add",
        "anonymity",
        "banner",
        "capability-pack",
        "clear",
        "default-out-print",
        "exit",
        "explain",
        "filters",
        "frameworks",
        "fusion",
        "help",
        "history",
        "intel",
        "keywords",
        "live",
        "modules",
        "ocr",
        "orchestrate",
        "out-print",
        "out-type",
        "surface-kit",
        "profile",
        "quicktest",
        "remove",
        "scan",
        "select",
        "set",
        "show",
        "surface",
        "templates",
        "use",
        "version",
        "wizard",
    }
    for keywords in PROMPT_KEYWORDS.values():
        commands.update(keywords)
    return sorted(commands)


def _print_prompt_help_hint(command_text: str | None = None) -> None:
    normalized = str(command_text or "").strip().lower()
    if normalized.startswith("show "):
        requested = normalized.split(maxsplit=1)[1].strip()
        suggestion = difflib.get_close_matches(requested, sorted(PROMPT_SHOW_COMMANDS), n=1)
        if suggestion:
            print(c(f"{symbol('tip')} Unknown `show` target: {requested}. Try `show {suggestion[0]}`.", Colors.EMBER))
            return
        print(c(f"{symbol('tip')} Use `show` with: {', '.join(sorted(PROMPT_SHOW_COMMANDS))}.", Colors.EMBER))
        return

    first = normalized.split(maxsplit=1)[0] if normalized else ""
    if first:
        suggestion = difflib.get_close_matches(first, _prompt_command_catalog(), n=1)
        if suggestion:
            print(c(f"{symbol('tip')} Unknown command: {first}. Try `{suggestion[0]}` or `help`.", Colors.EMBER))
            return
    print(c(f"{symbol('tip')} Invalid command. Use `help` to list commands.", Colors.EMBER))


def _set_non_exiting_parser(parser: argparse.ArgumentParser) -> None:
    parser.exit_on_error = False
    for action in getattr(parser, "_actions", []):
        if not isinstance(action, argparse._SubParsersAction):  # noqa: SLF001 - argparse internals
            continue
        for subparser in action.choices.values():
            subparser.exit_on_error = False

PLUGIN_MANAGER = PluginManager()
FUSION_ENGINE = FusionEngine()
REPORT_GENERATOR = ReportGenerator()
INTELLIGENCE_ENGINE = IntelligenceEngine()


@dataclass
class RunnerState:
    use_tor: bool = False
    use_proxy: bool = False


@dataclass(frozen=True)
class RuntimeInventorySummary:
    plugin_count: int
    filter_count: int
    platform_count: int
    module_count: int
    plugin_scope_counts: dict[str, int]
    filter_scope_counts: dict[str, int]
    plugin_errors: tuple[str, ...]
    filter_errors: tuple[str, ...]
    platform_error: str | None
    module_error: str | None
    hybrid_architecture: dict[str, object]


def safe_path_component(value: str) -> str:
    allowed = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value.strip())
    return allowed.strip("._") or "target"


def clear_screen() -> None:
    if not bool(getattr(sys.stdout, "isatty", lambda: False)()):
        return
    os.system("cls" if os.name == "nt" else "clear")


def ask(message: str) -> str:
    return input(c(message, Colors.EMBER)).strip()


def _configure_console_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(errors="replace")
        except Exception:
            continue


def get_anonymity_status(state: RunnerState) -> str:
    if state.use_tor and state.use_proxy:
        return "Tor + Proxy"
    if state.use_tor:
        return "Tor only"
    if state.use_proxy:
        return "Proxy only"
    return "No anonymization"


def compute_effective_state(
    base_state: RunnerState,
    tor_override: bool | None,
    proxy_override: bool | None,
) -> RunnerState:
    return RunnerState(
        use_tor=base_state.use_tor if tor_override is None else tor_override,
        use_proxy=base_state.use_proxy if proxy_override is None else proxy_override,
    )


def _validate_username(username: str) -> bool:
    value = username.strip()
    return bool(value) and " " not in value


def _int_from_value(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                return default
    return default


def _float_from_value(value: object, default: float) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return float(text)
            except ValueError:
                return default
    return default


def _can_prompt_user() -> bool:
    return bool(getattr(sys.stdin, "isatty", lambda: False)())


def _tor_status_lines() -> list[str]:
    status = probe_tor_status()
    lines = [
        f"os={status.os_name}",
        f"binary_found={status.binary_found}",
        f"binary_path={status.binary_path or '-'}",
        f"socks_reachable={status.socks_reachable} ({TOR_HOST}:{TOR_SOCKS_PORT})",
        f"install_supported={status.install_supported}",
    ]
    lines.extend(f"note: {item}" for item in status.notes)
    return lines


def _print_tor_status() -> None:
    print(c(f"\n{symbol('major')} Tor Diagnostics", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    for line in _tor_status_lines():
        print(c(f"{symbol('bullet')} {line}", Colors.CYAN))
    print()


def _ensure_tor_ready(*, prompt_user: bool) -> tuple[bool, str | None]:
    status = probe_tor_status()
    if status.socks_reachable:
        return True, None

    if not status.binary_found:
        if not status.install_supported:
            return (
                False,
                f"Tor not detected on {status.os_name}. Please install Tor manually to use --tor.",
            )

        if not prompt_user or not _can_prompt_user():
            return (
                False,
                "Tor not detected. Run `anonymity --prompt` for guided install or install Tor manually.",
            )

        allow_install = _prompt_yes_no("Tor is not installed. Install Tor now?", True)
        if not allow_install:
            return False, "Tor required for --tor was declined by user."

        print(c(f"{symbol('action')} Installing Tor...", Colors.EMBER))
        ok, message = install_tor()
        if not ok:
            return False, f"Tor install failed: {message}"
        print(c(f"{symbol('ok')} Tor install completed: {message}", Colors.GREEN))
        status = probe_tor_status()

    if status.socks_reachable:
        return True, None

    if not prompt_user or not _can_prompt_user():
        return False, "Tor is installed but not running. Start Tor service/process, then retry."

    allow_start = _prompt_yes_no("Tor is installed but OFF. Start Tor now?", True)
    if not allow_start:
        return False, "Tor startup declined by user."

    print(c(f"{symbol('action')} Starting Tor...", Colors.EMBER))
    ok, message = start_tor(status.binary_path)
    if not ok:
        return False, f"Failed to start Tor: {message}"

    final_status = probe_tor_status()
    if not final_status.socks_reachable:
        return False, "Tor start command completed but SOCKS endpoint is still unreachable."
    print(c(f"{symbol('ok')} Tor is ON: {message}", Colors.GREEN))
    return True, None


def _validate_network_settings(state: RunnerState, *, prompt_user: bool = False) -> tuple[bool, str | None]:
    if state.use_tor:
        ok, error = _ensure_tor_ready(prompt_user=prompt_user)
        if not ok:
            return False, error

    try:
        get_network_settings(state.use_proxy, state.use_tor)
        return True, None
    except RuntimeError as exc:
        return False, str(exc)


def _prompt_yes_no(question: str, current: bool) -> bool:
    suffix = "y" if current else "n"
    while True:
        answer = ask(f"{question} (y/n) [{suffix}]: ").lower()
        if answer == "":
            return current
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print(c("Please answer with y or n.", Colors.RED))


def _prompt_choice(question: str, options: Sequence[str], default: str) -> str:
    choices = [str(item).strip().lower() for item in options if str(item).strip()]
    if not choices:
        raise ValueError("Prompt choice options are required.")
    default_value = str(default).strip().lower()
    if default_value not in choices:
        default_value = choices[0]
    choice_label = "/".join(choices)
    while True:
        answer = ask(f"{question} [{default_value}] ({choice_label}): ").strip().lower()
        if not answer:
            return default_value
        if answer in choices:
            return answer
        print(c(f"Invalid option. Choose one of: {choice_label}", Colors.RED))


def _explicit_toggle(args: argparse.Namespace, name: str) -> bool | None:
    explicit = {str(flag).strip().lower() for flag in getattr(args, "_explicit_flags", ())}
    flag = f"--{name}"
    no_flag = f"--no-{name}"
    if flag in explicit or no_flag in explicit:
        return getattr(args, name, None)
    return None


def _resolve_output_types(
    *,
    html_flag: bool | None,
    csv_flag: bool | None,
    allow_html: bool = True,
    allow_csv: bool = True,
    force_json: bool = False,
    base_types: Sequence[str] | set[str] | None = None,
) -> set[str]:
    settings = get_output_settings()
    if base_types is None:
        types = {item.lower() for item in settings.types}
    else:
        types = {str(item).strip().lower() for item in base_types if str(item).strip()}
        if not types:
            types = {item.lower() for item in settings.types}
    if html_flag is not None:
        if html_flag:
            types.add("html")
        else:
            types.discard("html")
    if csv_flag is not None:
        if csv_flag:
            types.add("csv")
        else:
            types.discard("csv")
    if not allow_html:
        types.discard("html")
    if not allow_csv:
        types.discard("csv")
    if force_json:
        types.add("json")
    return types


def _parse_output_type_override(raw: object) -> tuple[set[str] | None, str | None]:
    if raw is None:
        tokens: list[str] = []
    elif isinstance(raw, str):
        tokens = tokenize_output_types(raw)
    elif isinstance(raw, Iterable):
        tokens = tokenize_output_types(str(item) for item in raw)
    else:
        tokens = tokenize_output_types(str(raw))
    if not tokens:
        return None, None
    lowered = [token.lower() for token in tokens if token]
    if any(token in {"none", "off", "disable", "disabled"} for token in lowered):
        return None, "Output types cannot be empty. Choose at least one of: cli, html, csv, json."
    if any(token in {"default", "reset"} for token in lowered):
        return set(DEFAULT_OUTPUT_TYPES), None
    types, unknown = parse_output_types(lowered)
    if unknown:
        return None, f"Unknown output types: {', '.join(sorted(set(unknown)))}"
    if not types:
        return None, "Output types cannot be empty. Choose at least one of: cli, html, csv, json."
    return set(types), None


def _apply_output_base_override(path_value: str | None) -> tuple[bool, str | None]:
    text = str(path_value or "").strip()
    if not text:
        return False, None
    previous = get_session_output_base_dir()
    try:
        set_session_output_base_dir(text)
        return True, str(previous) if previous else None
    except OutputConfigError as exc:
        return False, str(exc)


def _restore_output_base_override(previous_value: str | None) -> None:
    if previous_value is None:
        clear_session_output_base_dir()
        return
    try:
        set_session_output_base_dir(previous_value)
    except OutputConfigError:
        clear_session_output_base_dir()


def _prompt_extension_selection(
    *,
    kind: str,
    scopes: Sequence[str],
) -> list[str]:
    default_label = "none"
    unique_scopes = list(dict.fromkeys(str(scope).strip().lower() for scope in scopes if str(scope).strip()))
    while True:
        raw = ask(f"{kind} [none|list|selector1,selector2] [{default_label}]: ").strip()
        lowered = raw.lower()
        if not raw:
            return []
        if lowered in {"none", "off"}:
            return []
        if lowered in {"list", "ls", "?"}:
            if kind.lower().startswith("plugin"):
                for scope in unique_scopes or ["all"]:
                    _print_plugin_inventory(scope=scope)
            else:
                for scope in unique_scopes or ["all"]:
                    _print_filter_inventory(scope=scope)
            continue
        selectors = _split_csv_tokens([raw])
        if selectors:
            return selectors
        print(c("Provide selectors separated by commas, or use none/list.", Colors.RED))


def set_anonymity_interactive(state: RunnerState) -> bool:
    previous = RunnerState(use_tor=state.use_tor, use_proxy=state.use_proxy)

    state.use_tor = _prompt_yes_no("Use Tor routing?", state.use_tor)
    state.use_proxy = _prompt_yes_no("Use proxy routing?", state.use_proxy)

    ok, error = _validate_network_settings(state, prompt_user=True)
    if not ok:
        state.use_tor = previous.use_tor
        state.use_proxy = previous.use_proxy
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        append_framework_log("anonymity_update_failed", error or "unknown", level="WARN")
        return False

    print(c(f"{symbol('ok')} Anonymity settings saved.", Colors.GREEN))
    append_framework_log("anonymity_update", get_anonymity_status(state))
    return True


def apply_anonymity_flags(
    state: RunnerState,
    tor: bool | None,
    proxy: bool | None,
    *,
    prompt_user: bool = False,
) -> bool:
    updated = compute_effective_state(state, tor_override=tor, proxy_override=proxy)
    ok, error = _validate_network_settings(updated, prompt_user=prompt_user)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        append_framework_log("anonymity_update_failed", error or "unknown", level="WARN")
        return False

    state.use_tor = updated.use_tor
    state.use_proxy = updated.use_proxy
    print(c(f"{symbol('ok')} Anonymity settings saved.", Colors.GREEN))
    append_framework_log("anonymity_update", get_anonymity_status(state))
    return True


def _keyword_to_command(value: str) -> str | None:
    return _keyword_to_command_impl(value)


def _print_keyword_inventory() -> None:
    print(c(f"\n{symbol('major')} Prompt Keywords", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    for command, keywords in PROMPT_KEYWORDS.items():
        print(c(f"{symbol('bullet')} {command}: {', '.join(sorted(keywords))}", Colors.CYAN))
        print()
    print()


def _print_plugin_inventory(scope: str | None = None) -> None:
    resolved_scope = None if scope in (None, "", "all") else scope
    plugins = list_plugin_descriptors(scope=resolved_scope)
    discovery_errors = list_plugin_discovery_errors(scope=resolved_scope)
    title_suffix = "all scopes" if resolved_scope is None else f"scope={resolved_scope}"
    print(c(f"\n{symbol('major')} Plugins ({title_suffix})", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    if not plugins:
        print(c(f"{symbol('warn')} No plugins discovered.", Colors.EMBER))
        for error in discovery_errors:
            print(c(f"{symbol('warn')} {error}", Colors.EMBER))
        print()
        return

    def _print_rows(rows: list[dict[str, Any]], *, heading: str, accent: str) -> None:
        if not rows:
            return
        print(c(f"{symbol('tip')} {heading}", accent))
        for plugin in rows:
            scopes_text = ", ".join(plugin.get("scopes", []))
            aliases = plugin.get("aliases", [])
            alias_text = ", ".join(aliases) if aliases else "-"
            print(c(f"{symbol('feature')} {plugin.get('id')} - {plugin.get('title')}", Colors.CYAN))
            crypto_kind = str(plugin.get("crypto_kind") or "").strip().lower()
            if crypto_kind:
                print(c(f"  crypto-kind: {crypto_kind}", Colors.MAGENTA))
            print(c(f"  scopes: {scopes_text}", Colors.WHITE))
            print(c(f"  aliases: {alias_text}", Colors.WHITE))
            print(c(f"  desc: {plugin.get('description')}", Colors.WHITE))
            print()

    core_plugins = [
        plugin for plugin in plugins if str(plugin.get("plugin_group") or "").strip().lower() != "cryptography"
    ]
    crypto_plugins = [
        plugin for plugin in plugins if str(plugin.get("plugin_group") or "").strip().lower() == "cryptography"
    ]
    print(
        c(
            f"{symbol('tip')} core plugins: {len(core_plugins)} | cryptography plugins: {len(crypto_plugins)}",
            Colors.WHITE,
        )
    )
    _print_rows(core_plugins, heading="Core Plugin Set", accent=Colors.CYAN)
    _print_rows(crypto_plugins, heading="Cryptography Plugin Set", accent=Colors.MAGENTA)

    for error in discovery_errors:
        print(c(f"{symbol('warn')} {error}", Colors.EMBER))
    print()


def _print_filter_inventory(scope: str | None = None) -> None:
    resolved_scope = None if scope in (None, "", "all") else scope
    filters = list_filter_descriptors(scope=resolved_scope)
    discovery_errors = list_filter_discovery_errors(scope=resolved_scope)
    title_suffix = "all scopes" if resolved_scope is None else f"scope={resolved_scope}"
    print(c(f"\n{symbol('major')} Filters ({title_suffix})", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    if not filters:
        print(c(f"{symbol('warn')} No filters discovered.", Colors.EMBER))
        for error in discovery_errors:
            print(c(f"{symbol('warn')} {error}", Colors.EMBER))
        print()
        return

    for row in filters:
        scopes_text = ", ".join(row.get("scopes", []))
        aliases = row.get("aliases", [])
        alias_text = ", ".join(aliases) if aliases else "-"
        print(c(f"{symbol('feature')} {row.get('id')} - {row.get('title')}", Colors.CYAN))
        print(c(f"  scopes: {scopes_text}", Colors.WHITE))
        print(c(f"  aliases: {alias_text}", Colors.WHITE))
        print(c(f"  desc: {row.get('description')}", Colors.WHITE))
        print()
    for error in discovery_errors:
        print(c(f"{symbol('warn')} {error}", Colors.EMBER))
    print()


def _sanitize_module_label(*, label: str | None = None) -> str:
    if label:
        return label
    return "module"


def _sanitize_modules_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(payload)
    summary = cleaned.get("summary", {})
    if isinstance(summary, dict):
        summary = dict(summary)
        summary.pop("framework_count", None)
        summary.pop("frameworks", None)
        summary.pop("kind_counts", None)
        cleaned["summary"] = summary

    query = cleaned.get("query", {})
    if isinstance(query, dict):
        query = dict(query)
        query.pop("frameworks", None)
        cleaned["query"] = query

    entries = []
    offset = 0
    if isinstance(query, dict):
        offset = _int_from_value(query.get("offset"), 0)
    for index, row in enumerate(cleaned.get("entries", []) or []):
        if not isinstance(row, dict):
            continue
        sanitized = dict(row)
        label = f"module-{offset + index + 1}"
        sanitized["file"] = label
        sanitized.pop("framework", None)
        sanitized.pop("path", None)
        sanitized["id"] = label
        entries.append(sanitized)
    cleaned["entries"] = entries
    return cleaned


def _print_modules_inventory(
    *,
    scope: str = "all",
    kind: str = "all",
    frameworks: list[str] | None = None,
    search: str = "",
    tags: list[str] | None = None,
    min_score: int = 0,
    sort_by: str = "file",
    descending: bool = False,
    limit: int = 50,
    offset: int = 0,
    sync: bool = False,
    validate_catalog: bool = False,
    as_json: bool = False,
    stats_only: bool = False,
) -> None:
    framework_values = [item.strip() for item in (frameworks or []) if item and item.strip()]
    tag_values = [item.strip() for item in (tags or []) if item and item.strip()]
    catalog = ensure_module_catalog(
        refresh=sync,
        validate_catalog=True,
        verify_source_fingerprint=validate_catalog,
    )
    payload = query_module_catalog(
        catalog,
        kind=kind,
        scope=scope,
        frameworks=framework_values,
        search=search,
        tags=tag_values,
        min_score=min_score,
        sort_by=sort_by,
        descending=descending,
        limit=max(1, int(limit)),
        offset=max(0, int(offset)),
    )
    if stats_only:
        payload["entries"] = []

    payload["query"]["sync"] = bool(sync)
    payload["query"]["validated"] = bool(validate_catalog)
    payload["query"]["stats_only"] = bool(stats_only)
    if as_json:
        print(json.dumps(_sanitize_modules_payload(payload), indent=2))
        return

    summary = payload.get("summary", {})
    rows = payload.get("entries", [])
    query = payload.get("query", {})
    matched_total = int(payload.get("matched_total", len(rows)))
    returned_count = int(payload.get("returned_count", len(rows)))
    has_more = bool(payload.get("has_more", False))

    print(c(f"\n{symbol('major')} Modules (scope={scope}, kind={kind})", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"module_count: {summary.get('module_count', 0)}", Colors.CYAN))
    print(c(f"matched_total: {matched_total}", Colors.CYAN))
    print(c(f"returned_count: {returned_count}", Colors.CYAN))
    scope_counts = summary.get("scope_counts", {})
    score_bands = summary.get("score_bands", {})
    language_counts = summary.get("language_counts", {})
    capability_counts = summary.get("capability_counts", {})
    print(
        c(
            "scope_counts: "
            f"profile={scope_counts.get('profile', 0)} "
            f"surface={scope_counts.get('surface', 0)} fusion={scope_counts.get('fusion', 0)}",
            Colors.CYAN,
        )
    )
    print(c(f"power_score_avg: {summary.get('power_score_avg', 0)}", Colors.CYAN))
    print(
        c(
            "score_bands: "
            f"high={score_bands.get('high', 0)} "
            f"medium={score_bands.get('medium', 0)} "
            f"low={score_bands.get('low', 0)}",
            Colors.CYAN,
        )
    )

    if isinstance(language_counts, dict) and language_counts:
        top_languages = sorted(
            ((str(name), int(count)) for name, count in language_counts.items()),
            key=lambda item: (-item[1], item[0]),
        )[:6]
        print(c(f"top_languages: {', '.join(f'{name}:{count}' for name, count in top_languages)}", Colors.CYAN))
    if isinstance(capability_counts, dict) and capability_counts:
        top_capabilities = sorted(
            ((str(name), int(count)) for name, count in capability_counts.items()),
            key=lambda item: (-item[1], item[0]),
        )[:6]
        print(c(f"top_capabilities: {', '.join(f'{name}:{count}' for name, count in top_capabilities)}", Colors.CYAN))
    if query.get("search"):
        print(c(f"search: {query.get('search')}", Colors.CYAN))
    if tag_values:
        print(c(f"tags: {', '.join(tag_values)}", Colors.CYAN))
    print(
        c(
            "query_controls: "
            f"min_score={query.get('min_score', 0)} "
            f"sort_by={query.get('sort_by', 'file')} "
            f"descending={query.get('descending', False)} "
            f"limit={query.get('limit', 0)} "
            f"offset={query.get('offset', 0)} "
            f"validated={query.get('validated', False)}",
            Colors.CYAN,
        )
    )

    if has_more:
        print(c(f"{symbol('tip')} more_results=true (increase --offset or --limit to continue).", Colors.EMBER))

    if stats_only:
        print(c(f"{symbol('tip')} stats_only=true (entry listing skipped).", Colors.EMBER))
        print()
        return

    if not rows:
        print(c(f"{symbol('warn')} No module entries matched this query.", Colors.EMBER))
        print(c(f"{symbol('tip')} Run `modules --sync` if catalog is empty or stale.", Colors.EMBER))
        print()
        return

    offset_value = _int_from_value(query.get("offset"), 0) if isinstance(query, dict) else 0
    for index, row in enumerate(rows):
        label = _sanitize_module_label(label=f"module-{offset_value + index + 1}")
        print(c(f"{symbol('feature')} {label}", Colors.CYAN))
        print(
            c(
                f"  scopes: {', '.join(row.get('scopes', []))} "
                f"| capabilities: {', '.join(row.get('capabilities', [])[:5]) or '-'}",
                Colors.WHITE,
            )
        )
        signals = row.get("signals", {})
        metrics = row.get("metrics", {})
        print(
            c(
                "  scores: "
                f"power={metrics.get('power_score', 0)} "
                f"confidence={metrics.get('confidence_score', 0)} "
                f"profile={signals.get('profile_score', 0)} "
                f"surface={signals.get('surface_score', 0)} "
                f"fusion={signals.get('fusion_score', 0)} "
                f"size={metrics.get('file_size_bytes', 0)}B",
                Colors.WHITE,
            )
        )
        print()
    print()


def _print_framework_inventory(
    *,
    framework: str = "all",
    show_modules: bool = False,
    show_presets: bool = False,
    show_flags: bool = False,
    show_commands: bool = False,
    search: str = "",
    limit: int = 25,
    as_json: bool = False,
) -> None:
    inventory = load_source_inventory()
    selected = str(framework or "all").strip().lower()

    payload: dict[str, Any]
    if selected == "recursive-modules":
        payload = {"inventory": inventory, "recursive_modules": load_recursive_module_reference()}
    elif selected == "graph-registry":
        payload = {"inventory": inventory, "graph_registry": load_graph_registry_reference()}
    elif selected == "console-shell":
        payload = {"inventory": inventory, "console_shell": load_console_shell_reference()}
    else:
        payload = inventory

    if as_json:
        if selected == "recursive-modules":
            if show_modules:
                payload = {"profile": "recursive-modules", "modules": filter_recipe_modules(search=search, limit=limit)}
            elif show_presets:
                payload = {"profile": "recursive-modules", "recipes": filter_recipes(search=search, limit=limit)}
            elif show_flags:
                payload = {"profile": "recursive-modules", "flags": filter_recipe_flags(search=search, limit=limit)}
            elif show_commands:
                payload = {"profile": "recursive-modules", "commands": load_recursive_module_reference().get("commands", [])}
        print(json.dumps(payload, indent=2))
        return

    print(c(f"\n{symbol('major')} Source Profile Intel", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))

    frameworks = inventory.get("profiles", [])
    if selected == "all":
        for row in frameworks:
            if not isinstance(row, dict):
                continue
            print(c(f"{symbol('feature')} {row.get('name')}", Colors.CYAN))
            print(c(f"  path: {row.get('path')}", Colors.WHITE))
            print(c(f"  summary: {row.get('summary')}", Colors.WHITE))
            extra = []
            if row.get("module_count") is not None:
                extra.append(f"modules={row.get('module_count')}")
            if row.get("preset_count") is not None:
                extra.append(f"presets={row.get('preset_count')}")
            if row.get("command_count") is not None:
                extra.append(f"commands={row.get('command_count')}")
            if row.get("engine_component_count") is not None:
                extra.append(f"engine_components={row.get('engine_component_count')}")
            if row.get("plugin_family_count") is not None:
                extra.append(f"plugin_families={row.get('plugin_family_count')}")
            if extra:
                print(c(f"  stats: {', '.join(extra)}", Colors.WHITE))
            print()

        other_dirs = inventory.get("other_dirs", [])
        if other_dirs:
            print(c(f"{symbol('tip')} Other temp/ directories", Colors.EMBER))
            for row in other_dirs:
                if isinstance(row, dict):
                    print(c(f"  - {row.get('name')}: {row.get('path')}", Colors.GREY))
            print()
        return

    if selected == "recursive-modules":
        reference = load_recursive_module_reference()
        print(c(f"{symbol('feature')} recursive-modules", Colors.CYAN))
        print(c(f"  path: {reference.get('path')}", Colors.WHITE))
        print(c(f"  architecture: {', '.join(reference.get('architecture', []))}", Colors.WHITE))
        print(
            c(
                f"  stats: modules={reference.get('module_count', 0)} "
                f"recipes={reference.get('recipe_count', 0)} flags={reference.get('flag_count', 0)} "
                f"commands={len(reference.get('commands', []))}",
                Colors.WHITE,
            )
        )
        if show_commands:
            print()
            print(c(f"{symbol('major')} Source Command Capabilities", Colors.BLUE))
            print(c("-" * 36, Colors.BLUE))
            for row in reference.get("commands", []):
                if isinstance(row, dict):
                    print(c(f"{symbol('bullet')} {row.get('id')}: {row.get('title')}", Colors.CYAN))
            print()
        if show_presets:
            print()
            print(c(f"{symbol('major')} Source Recipes", Colors.BLUE))
            print(c("-" * 36, Colors.BLUE))
            for row in filter_recipes(search=search, limit=limit):
                print(c(f"{symbol('feature')} {row.get('name')}", Colors.CYAN))
                print(c(f"  desc: {row.get('description')}", Colors.WHITE))
                print(c(f"  flags: {', '.join(row.get('flags', [])) or '-'}", Colors.WHITE))
                print(c(f"  includes: {', '.join(row.get('include', [])) or '-'}", Colors.WHITE))
                print()
        if show_flags:
            print()
            print(c(f"{symbol('major')} Source Flags", Colors.BLUE))
            print(c("-" * 36, Colors.BLUE))
            for row in filter_recipe_flags(search=search, limit=limit):
                print(c(f"{symbol('feature')} {row.get('name')} ({row.get('count')})", Colors.CYAN))
                print(c(f"  sample modules: {', '.join(row.get('modules', [])[:8]) or '-'}", Colors.WHITE))
                print()
        if show_modules:
            print()
            print(c(f"{symbol('major')} Source Modules", Colors.BLUE))
            print(c("-" * 36, Colors.BLUE))
            for row in filter_recipe_modules(search=search, limit=limit):
                print(c(f"{symbol('feature')} {row.get('name')} [{row.get('type')}]", Colors.CYAN))
                print(c(f"  desc: {row.get('description')}", Colors.WHITE))
                print(c(f"  flags: {', '.join(row.get('flags', [])) or '-'}", Colors.WHITE))
                print(
                    c(
                        f"  flow: consumes={', '.join(row.get('consumes', [])[:4]) or '-'} "
                        f"produces={', '.join(row.get('produces', [])[:4]) or '-'}",
                        Colors.WHITE,
                    )
                )
                print()
        print()
        return

    if selected == "graph-registry":
        reference = load_graph_registry_reference()
        print(c(f"{symbol('feature')} graph-registry", Colors.CYAN))
        print(c(f"  path: {reference.get('path')}", Colors.WHITE))
        print(c(f"  architecture: {', '.join(reference.get('architecture', []))}", Colors.WHITE))
        print(
            c(
                f"  commands: {', '.join(reference.get('commands', [])) or '-'}",
                Colors.WHITE,
            )
        )
        print(
            c(
                f"  engine: {', '.join(reference.get('engine_components', [])) or '-'}",
                Colors.WHITE,
            )
        )
        print(
            c(
                f"  plugin families: {', '.join(reference.get('plugin_families', [])[:12]) or '-'}",
                Colors.WHITE,
            )
        )
        print()
        return

    reference = load_console_shell_reference()
    print(c(f"{symbol('feature')} console-shell", Colors.CYAN))
    print(c(f"  path: {reference.get('path')}", Colors.WHITE))
    print(c(f"  architecture: {', '.join(reference.get('architecture', []))}", Colors.WHITE))
    print()


def _print_surface_recipe_plan(plan: dict[str, Any]) -> None:
    preset = plan.get("recipe", {}) if isinstance(plan.get("recipe"), dict) else {}
    mapping = plan.get("sylica_mapping", {}) if isinstance(plan.get("sylica_mapping"), dict) else {}

    print(c(f"\n{symbol('major')} Surface Kit Plan", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"{symbol('feature')} target={plan.get('target')} preset={preset.get('name')}", Colors.CYAN))
    print(c(f"  preset_desc: {preset.get('description', '-')}", Colors.WHITE))
    print(
        c(
            f"  translated_to: surface_preset={mapping.get('surface_preset')} "
            f"recon_mode={mapping.get('recon_mode')} ct={mapping.get('include_ct')} "
            f"rdap={mapping.get('include_rdap')}",
            Colors.WHITE,
        )
    )
    print(c(f"  coverage: {mapping.get('coverage', '-')}", Colors.WHITE))
    print(c(f"  selected_flags: {', '.join(plan.get('selected_flags', [])) or '-'}", Colors.WHITE))
    print(c(f"  selected_module_count: {plan.get('selected_module_count', 0)}", Colors.WHITE))
    print(
        c(
            f"  native_capabilities: {', '.join(plan.get('native_capabilities', [])) or '-'}",
            Colors.WHITE,
        )
    )
    print(
        c(
            f"  partial_capabilities: {', '.join(plan.get('partial_capabilities', [])) or '-'}",
            Colors.WHITE,
        )
    )
    print(
        c(
            f"  unsupported_capabilities: {', '.join(plan.get('unsupported_capabilities', [])) or '-'}",
            Colors.WHITE,
        )
    )
    unsupported_modules = plan.get("unsupported_modules_preview", [])
    if isinstance(unsupported_modules, list) and unsupported_modules:
        print(c(f"  unsupported_modules_preview: {', '.join(unsupported_modules)}", Colors.WHITE))
    print(c(f"  sylica_command: {plan.get('execution_preview', '-')}", Colors.CYAN))
    print()


def _print_scan_history(limit: int = 25) -> None:
    rows = list_scanned_targets(limit=limit)
    print(c(f"\n{symbol('major')} Scan History", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    if not rows:
        print(c(f"{symbol('warn')} No scan artifacts found under output/json or output/html.", Colors.EMBER))
        print()
        return

    for index, row in enumerate(rows, start=1):
        print(c(f"{index}. {row['target']}", Colors.CYAN))
        print(c(f"  updated: {row['modified_at']}", Colors.GREY))
        if row.get("source"):
            print(c(f"  source: {row['source']}", Colors.GREY))
        print(c(f"  file: {row['path']}", Colors.GREY))
        print()
    print()


def _print_quicktest_templates() -> None:
    rows = list_quicktest_templates()
    print(c(f"\n{symbol('major')} Quicktest Templates", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    for row in rows:
        print(
            c(
                f"{symbol('feature')} {row.get('id')} :: {row.get('label')} "
                f"(username={row.get('username')} domain={row.get('domain')})",
                Colors.CYAN,
            )
        )
        print()
    print(c(f"{symbol('tip')} Run `quicktest` to pick one randomly.", Colors.GREY))
    print()


def _print_info_templates(*, as_json: bool = False) -> None:
    rows = list_info_templates()
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    print(c(f"\n{symbol('major')} Info-Templates", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    for row in rows:
        scopes = ", ".join(row.get("scopes", [])) or "-"
        tags = ", ".join(row.get("module_tags", [])) or "-"
        plugins = row.get("plugins", [])
        filters = row.get("filters", [])
        print(
            c(
                f"{symbol('feature')} {row.get('id')} :: {row.get('label')} "
                f"(scopes={scopes})",
                Colors.CYAN,
            )
        )
        print(c(f"  {row.get('description')}", Colors.GREY))
        print(c(f"  plugins: {', '.join(plugins)}", Colors.WHITE))
        print(c(f"  filters: {', '.join(filters)}", Colors.WHITE))
        print(c(f"  module tags: {tags}", Colors.WHITE))
        note = str(row.get("notes", "")).strip()
        if note:
            print(c(f"  note: {note}", Colors.EMBER))
        print()
    print(c(f"{symbol('tip')} Apply with --info-template <id> or `set template <id>` in prompt mode.", Colors.GREY))
    print()


def _count_scope_coverage(rows: list[dict]) -> dict[str, int]:
    counts = {"profile": 0, "surface": 0, "fusion": 0}
    for row in rows:
        scopes = row.get("scopes", [])
        if not isinstance(scopes, list):
            continue
        scope_set = {str(scope).strip().lower() for scope in scopes if isinstance(scope, str)}
        for scope in ("profile", "surface", "fusion"):
            if scope in scope_set:
                counts[scope] += 1
    return counts


def _collect_runtime_inventory() -> RuntimeInventorySummary:
    def _build() -> RuntimeInventorySummary:
        plugins = list_plugin_descriptors(scope=None)
        filters = list_filter_descriptors(scope=None)
        plugin_errors = tuple(list_plugin_discovery_errors(scope=None))
        filter_errors = tuple(list_filter_discovery_errors(scope=None))
        plugin_scope_counts = _count_scope_coverage(plugins)
        filter_scope_counts = _count_scope_coverage(filters)

        platform_count = 0
        platform_error: str | None = None
        try:
            platform_count = len(load_platforms())
        except Exception as exc:  # pragma: no cover - startup diagnostics
            platform_error = str(exc)

        module_count = 0
        module_error: str | None = None
        try:
            catalog = ensure_module_catalog(
                refresh=False,
                validate_catalog=True,
                verify_source_fingerprint=False,
            )
            summary = summarize_module_catalog(catalog)
            module_count = int(summary.get("module_count", 0) or 0)
        except Exception as exc:  # pragma: no cover - startup diagnostics
            module_error = str(exc)

        return RuntimeInventorySummary(
            plugin_count=len(plugins),
            filter_count=len(filters),
            platform_count=platform_count,
            module_count=module_count,
            plugin_scope_counts=plugin_scope_counts,
            filter_scope_counts=filter_scope_counts,
            plugin_errors=plugin_errors,
            filter_errors=filter_errors,
            platform_error=platform_error,
            module_error=module_error,
            hybrid_architecture=build_hybrid_architecture_snapshot(),
        )

    return run_with_spinner("[*] Loading Silica-X runtime inventory... ", _build)


def _print_runtime_loaded_inventory() -> None:
    inventory = _collect_runtime_inventory()

    print(
        c(
            "Loaded: "
            f"plugins={inventory.plugin_count} "
            f"filters={inventory.filter_count} "
            f"platforms={inventory.platform_count} "
            f"modules={inventory.module_count}",
            Colors.CYAN,
        )
    )
    print(
        c(
            "Coverage: "
            f"plugins={inventory.plugin_scope_counts['profile']}/{inventory.plugin_scope_counts['surface']}/{inventory.plugin_scope_counts['fusion']} "
            f"filters={inventory.filter_scope_counts['profile']}/{inventory.filter_scope_counts['surface']}/{inventory.filter_scope_counts['fusion']}",
            Colors.GREY,
        )
    )
    hybrid_lines = render_hybrid_inventory_lines(inventory.hybrid_architecture)
    print(c(hybrid_lines[0], Colors.EMBER))
    print(c(hybrid_lines[1], Colors.GREY))
    print(c(hybrid_lines[2], Colors.GREY))
    if inventory.plugin_errors:
        print(c(f"{symbol('warn')} plugin discovery warnings={len(inventory.plugin_errors)}", Colors.EMBER))
    if inventory.filter_errors:
        print(c(f"{symbol('warn')} filter discovery warnings={len(inventory.filter_errors)}", Colors.EMBER))
    if inventory.platform_error:
        print(c(f"{symbol('warn')} platform inventory unavailable: {inventory.platform_error}", Colors.EMBER))
    if inventory.module_error:
        print(c(f"{symbol('warn')} module catalog unavailable: {inventory.module_error}", Colors.EMBER))

    snapshot = build_runtime_inventory_snapshot(
        plugin_count=inventory.plugin_count,
        filter_count=inventory.filter_count,
        platform_count=inventory.platform_count,
        module_count=inventory.module_count,
        plugin_scope_counts=inventory.plugin_scope_counts,
        filter_scope_counts=inventory.filter_scope_counts,
        plugin_error_count=len(inventory.plugin_errors),
        filter_error_count=len(inventory.filter_errors),
        platform_error=inventory.platform_error,
        module_error=inventory.module_error,
        hybrid_architecture=inventory.hybrid_architecture,
    )
    try:
        write_runtime_inventory_snapshot(snapshot)
    except Exception as exc:  # pragma: no cover - diagnostics-only path
        print(c(f"{symbol('warn')} runtime inventory snapshot failed: {exc}", Colors.EMBER))
    print()


def launch_live_dashboard(
    target: str,
    port: int = DEFAULT_DASHBOARD_PORT,
    open_browser: bool = True,
    background: bool = True,
) -> None:
    safe_target = sanitize_target(target.strip())
    if not safe_target:
        raise ValueError("Target is required for live dashboard.")
    try:
        ensure_output_tree()
    except OutputConfigError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        return

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib hook
            if self.path != "/":
                self.send_error(404)
                return

            file_path = latest_results_json_path(safe_target)
            if file_path is None or not file_path.exists():
                self.send_response(404)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                msg = (
                    f"<h2>No results found for target: {html.escape(safe_target)}</h2>"
                    "<p>Generate a scan first. Reports are stored in output/json and output/html.</p>"
                )
                self.wfile.write(msg.encode())
                return

            try:
                with file_path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                self.send_response(500)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                msg = f"<h2>Failed to load results: {html.escape(str(exc))}</h2>"
                self.wfile.write(msg.encode())
                return

            results = data.get("results", [])
            found_rows = found_profile_rows(results)
            error_rows = error_profile_rows(results)
            snapshot = summarize_target_intel(results)
            display_target = str(data.get("target") or safe_target)

            found_table_rows = ""
            for item in found_rows:
                emails = ", ".join((item.get("contacts", {}) or {}).get("emails", []) or []) or "-"
                phones = ", ".join((item.get("contacts", {}) or {}).get("phones", []) or []) or "-"
                found_table_rows += (
                    "<tr>"
                    f"<td>{html.escape(item.get('platform', 'Unknown'))}</td>"
                    f"<td>{int(item.get('confidence', 0) or 0)}%</td>"
                    f"<td><a href='{html.escape(item.get('url', ''))}' target='_blank' rel='noreferrer'>"
                    f"{html.escape(item.get('url', ''))}</a></td>"
                    f"<td>{html.escape(emails)}</td>"
                    f"<td>{html.escape(phones)}</td>"
                    f"<td>{html.escape(item.get('context', '') or '-')}</td>"
                    "</tr>"
                )
            if not found_table_rows:
                found_table_rows = "<tr><td colspan='6'>No FOUND profiles.</td></tr>"

            error_table_rows = ""
            error_color_map = {
                "ERROR": "#ff6b6b",
                "BLOCKED": "#ff9a3d",
            }
            for item in error_rows:
                status = str(item.get("status", "ERROR"))
                color = error_color_map.get(status, "#ff6b6b")
                error_table_rows += (
                    "<tr>"
                    f"<td>{html.escape(item.get('platform', 'Unknown'))}</td>"
                    f"<td style='color:{color};font-weight:bold;'>{html.escape(status)}</td>"
                    f"<td><a href='{html.escape(item.get('url', ''))}' target='_blank' rel='noreferrer'>"
                    f"{html.escape(item.get('url', ''))}</a></td>"
                    f"<td>{html.escape(str(item.get('http_status', '-') if item.get('http_status') is not None else '-'))}</td>"
                    f"<td>{html.escape(str(item.get('response_time_ms', '-') if item.get('response_time_ms') is not None else '-'))}</td>"
                    f"<td>{html.escape(item.get('context', '') or '-')}</td>"
                    "</tr>"
                )
            if not error_table_rows:
                error_table_rows = "<tr><td colspan='6'>No ERROR/BLOCKED websites.</td></tr>"

            narrative = html.escape(data.get("narrative") or "No narrative generated.")
            issues = data.get("issues", [])
            issue_items = "".join(
                f"<li><strong>{html.escape(issue.get('severity', 'LOW'))}</strong> "
                f"{html.escape(issue.get('title', 'Issue'))} - {html.escape(issue.get('evidence', ''))}</li>"
                for issue in issues
            ) or "<li>No issues reported.</li>"
            plugins = data.get("plugins", [])
            plugin_items = "".join(
                f"<li><strong>{html.escape(plugin.get('title', plugin.get('id', 'plugin')))}</strong> "
                f"[{html.escape(str(plugin.get('severity', 'INFO')).upper())}] "
                f"{html.escape(plugin.get('summary', ''))}</li>"
                for plugin in plugins
            ) or "<li>No plugin output.</li>"
            filters = data.get("filters", [])
            filter_items = "".join(
                f"<li><strong>{html.escape(row.get('title', row.get('id', 'filter')))}</strong> "
                f"[{html.escape(str(row.get('severity', 'INFO')).upper())}] "
                f"{html.escape(row.get('summary', ''))}</li>"
                for row in filters
            ) or "<li>No filter output.</li>"

            html_content = f"""
            <html>
            <head>
              <title>{html.escape(PROJECT_NAME)} Live - {html.escape(display_target)}</title>
              <style>
                body {{ font-family: "Trebuchet MS", "Segoe UI", sans-serif; background:#140d08; color:#fff1e4; padding:20px; }}
                .panel {{ background:#23150d; border:1px solid #6a4327; border-radius:12px; padding:14px; margin-top:12px; }}
                table {{ width:100%; border-collapse: collapse; }}
                th, td {{ border:1px solid #6a4327; padding:8px; text-align:left; }}
                th {{ background:#311d12; color:#ffd6af; }}
                a {{ color:#ffb15e; text-decoration:none; }}
                .muted {{ color:#d1b295; }}
              </style>
            </head>
            <body>
              <h1>{html.escape(PROJECT_NAME)} v{html.escape(VERSION)} Live Dashboard</h1>
              <div class="panel">
                <h3>Target</h3>
                <p>{html.escape(display_target)}</p>
                <p class="muted">Found profiles: {snapshot["found_count"]} | Errored sites: {snapshot["error_count"]}</p>
                <p class="muted">Found platforms: {html.escape(", ".join(snapshot["found_platforms"]) or "none")}</p>
                <p class="muted">Emails: {html.escape(", ".join(snapshot["emails"]) or "none")}</p>
                <p class="muted">Phones: {html.escape(", ".join(snapshot["phones"]) or "none")}</p>
                <p class="muted">Auto-refresh this page manually to read newly written results.</p>
              </div>
              <div class="panel">
                <h3>Found Social Media Profiles</h3>
                <table>
                  <tr><th>Platform</th><th>Confidence</th><th>Profile Link</th><th>Emails</th><th>Phones</th><th>Context</th></tr>
                  {found_table_rows}
                </table>
              </div>
              <div class="panel">
                <h3>Errored / Blocked Websites</h3>
                <table>
                  <tr><th>Platform</th><th>Status</th><th>Profile Link</th><th>HTTP</th><th>RTT ms</th><th>Reason</th></tr>
                  {error_table_rows}
                </table>
              </div>
              <div class="panel">
                <h3>Exposure Findings</h3>
                <ul>{issue_items}</ul>
              </div>
              <div class="panel">
                <h3>Plugin Intelligence</h3>
                <ul>{plugin_items}</ul>
              </div>
              <div class="panel">
                <h3>Filter Intelligence</h3>
                <ul>{filter_items}</ul>
              </div>
              <div class="panel">
                <h3>Reporter Brief</h3>
                <p>{narrative}</p>
              </div>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html_content.encode())

    def run_server() -> None:
        server_address = ("", port)
        print(c(f"{symbol('ok')} Dashboard live at http://localhost:{port}/", Colors.GREEN))
        if open_browser:
            try:
                webbrowser.open(f"http://localhost:{port}/")
            except Exception as exc:  # pragma: no cover - environment-dependent
                print(c(f"{symbol('warn')} Failed to open browser: {exc}", Colors.EMBER))
        with HTTPServer(server_address, Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print(c(f"\n{symbol('warn')} Live dashboard stopped.", Colors.EMBER))

    if background:
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
    else:
        run_server()


def _resolve_profile_runtime(args: argparse.Namespace) -> tuple[int, int, str, int | None]:
    preset = PROFILE_PRESETS[args.preset]
    timeout_seconds = _int_from_value(args.timeout, preset["timeout"])
    max_concurrency = _int_from_value(args.max_concurrency, preset["max_concurrency"])
    source_profile = str(preset.get("source_profile", "balanced"))
    max_platforms = preset.get("max_platforms")
    max_platform_limit = int(max_platforms) if isinstance(max_platforms, int) and max_platforms > 0 else None
    return timeout_seconds, max_concurrency, source_profile, max_platform_limit


def _resolve_surface_runtime(args: argparse.Namespace) -> tuple[int, int, SurfaceScanDirectives]:
    preset = SURFACE_PRESETS[args.preset]
    timeout_seconds = _int_from_value(args.timeout, preset["timeout"])
    max_subdomains = _int_from_value(args.max_subdomains, preset["max_subdomains"])
    directives = _resolve_surface_scan_directives_from_args(
        args,
        default_recon_mode=str(getattr(args, "recon_mode", None) or preset.get("recon_mode", "hybrid")),
    )
    return timeout_seconds, max_subdomains, directives


def _resolve_ocr_runtime(args: argparse.Namespace) -> tuple[int, int, str, int, int | None, int | None]:
    preset = OCR_PRESETS[args.preset]
    timeout_seconds = _int_from_value(args.timeout, preset["timeout"])
    max_concurrency = _int_from_value(args.max_concurrency, preset["max_concurrency"])
    preprocess_mode = str(getattr(args, "preprocess", None) or preset.get("preprocess_mode", "balanced"))
    max_bytes = _int_from_value(getattr(args, "max_bytes", None), preset["max_bytes"])
    max_edge = (
        _int_from_value(getattr(args, "max_edge", None), preset["max_edge"])
        if getattr(args, "max_edge", None) is not None
        else int(preset["max_edge"])
    )
    threshold_value = getattr(args, "threshold", None)
    threshold = int(threshold_value) if threshold_value is not None else None
    return timeout_seconds, max_concurrency, preprocess_mode, max_bytes, max_edge, threshold


def _resolve_surface_scan_directives_from_args(
    args: argparse.Namespace,
    *,
    default_recon_mode: str,
) -> SurfaceScanDirectives:
    requested_scan_types = list(getattr(args, "scan_type", []) or [])
    invalid_scan_types = invalid_surface_scan_types(requested_scan_types)
    if invalid_scan_types:
        joined = ", ".join(invalid_scan_types)
        raise ValueError(f"Unsupported scan types: {joined}")

    requested_recon_mode = str(
        getattr(args, "surface_recon_mode", None)
        or getattr(args, "recon_mode", None)
        or default_recon_mode
    )
    return resolve_surface_scan_directives(
        recon_mode=requested_recon_mode,
        requested_scan_types=requested_scan_types,
        os_fingerprint_enabled=bool(getattr(args, "os_fingerprint", False)),
        scan_verbosity=getattr(args, "scan_verbosity", None),
        delay_seconds=getattr(args, "scan_delay", None),
    )


def _print_extension_control_feedback(
    *,
    scope: str,
    mode_name: str,
    control_mode: str,
    plugin_ids: tuple[str, ...],
    filter_ids: tuple[str, ...],
    warnings: tuple[str, ...],
) -> None:
    print(
        c(
            f"{symbol('action')} Extension control ({scope}): mode={mode_name} control={control_mode} "
            f"plugins={len(plugin_ids)} filters={len(filter_ids)}",
            Colors.CYAN,
        )
    )
    for warning in warnings:
        print(c(f"{symbol('warn')} {warning}", Colors.EMBER))


def _print_surface_scan_type_inventory() -> None:
    print(c(f"\n{symbol('major')} Surface Scan Directives", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    for spec in surface_scan_type_specs():
        aliases = ", ".join(spec.aliases) or "-"
        short_flag = spec.short_flag or "-"
        print(c(f"{symbol('feature')} {spec.identifier} [{short_flag}]", Colors.CYAN))
        print(c(f"  title: {spec.title}", Colors.WHITE))
        print(c(f"  aliases: {aliases}", Colors.WHITE))
        print(c(f"  summary: {spec.summary}", Colors.GREY))
        print()
    print(c(f"{symbol('tip')} Use with `--scan-type`, repeated flags, or prompt-mode command flags.", Colors.GREY))
    print()


def _resolve_extension_plan_or_fail(
    *,
    scope: str,
    scan_mode: str,
    control_mode: str,
    requested_plugins: list[str],
    requested_filters: list[str],
    include_all_plugins: bool,
    include_all_filters: bool,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], bool]:
    plan = resolve_extension_control(
        scope=scope,
        scan_mode=scan_mode,
        control_mode=control_mode,
        requested_plugins=requested_plugins,
        requested_filters=requested_filters,
        include_all_plugins=include_all_plugins,
        include_all_filters=include_all_filters,
    )
    if plan.errors:
        print(c(f"{symbol('error')} Extension configuration errors:", Colors.RED))
        for item in plan.errors:
            print(c(f" {symbol('error')} {item}", Colors.RED))
        print(c(f"{symbol('warn')} Stop: extension plan invalid; scan was not started.", Colors.RED))
        print(
            c(
                f"{symbol('tip')} Inspect compatible selectors with: "
                f"`plugins --scope {scope}` and `filters --scope {scope}`.",
                Colors.EMBER,
            )
        )
        print(
            c(
                f"{symbol('tip')} Use `--extension-control manual|hybrid` for explicit selector control.",
                Colors.EMBER,
            )
        )
        return (), (), (), False

    _print_extension_control_feedback(
        scope=scope,
        mode_name=plan.scan_mode,
        control_mode=plan.control_mode,
        plugin_ids=plan.plugins,
        filter_ids=plan.filters,
        warnings=plan.warnings,
    )
    return plan.plugins, plan.filters, plan.warnings, True


def _resolve_module_plan_or_fail(
    *,
    scope: str,
    requested_modules: list[str],
) -> tuple[tuple[str, ...], tuple[dict[str, Any], ...], tuple[str, ...], bool]:
    plan = resolve_module_attachments(scope=scope, requested_modules=requested_modules)
    if plan.errors:
        print(c(f"{symbol('error')} Module attachment errors:", Colors.RED))
        for item in plan.errors:
            print(c(f" {symbol('error')} {item}", Colors.RED))
        print(c(f"{symbol('warn')} Stop: module attachment plan invalid; scan was not started.", Colors.RED))
        print(c(f"{symbol('tip')} Inspect compatible module entries with: `modules --scope {scope}`.", Colors.EMBER))
        return (), (), (), False
    for item in plan.warnings:
        print(c(f"{symbol('tip')} {item}", Colors.GREY))
    return plan.module_ids, plan.entries, plan.warnings, True


def _preflight_attachable_payload(
    *,
    plugin_ids: Sequence[str],
    filter_ids: Sequence[str],
    module_entries: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "selected_plugins": list(plugin_ids),
        "selected_filters": list(filter_ids),
        "selected_modules": [str(row.get("id", "")) for row in module_entries if isinstance(row, dict)],
        "attached_modules": [dict(row) for row in module_entries if isinstance(row, dict)],
    }


def _print_execution_preview(
    *,
    heading: str,
    scope: str,
    target: str,
    state: RunnerState,
    scan_mode: str,
    extension_control: str,
    plugin_ids: Sequence[str],
    filter_ids: Sequence[str],
    module_entries: Sequence[dict[str, Any]],
    output_types: Sequence[str],
    output_root: str,
    extra_lines: Sequence[str] | None = None,
) -> None:
    print(c(f"\n{symbol('major')} {heading}", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"scope: {scope}", Colors.CYAN))
    print(c(f"target: {target}", Colors.CYAN))
    print(c(f"scan mode: {scan_mode}", Colors.CYAN))
    print(c(f"extension control: {extension_control}", Colors.CYAN))
    print(c(f"anonymity: {get_anonymity_status(state)}", Colors.CYAN))
    print(c("enabled attachables:", Colors.BLUE))
    print(c(f"  plugins: {', '.join(plugin_ids) or 'none'}", Colors.CYAN))
    print(c(f"  filters: {', '.join(filter_ids) or 'none'}", Colors.CYAN))
    if module_entries:
        module_labels = ", ".join(str(row.get("id", "module")) for row in module_entries[:8])
        if len(module_entries) > 8:
            module_labels += f", +{len(module_entries) - 8} more"
    else:
        module_labels = "none"
    print(c(f"  modules: {module_labels}", Colors.CYAN))
    print(c(f"output types: {', '.join(output_types) or 'none'}", Colors.CYAN))
    print(c(f"output root: {output_root}", Colors.CYAN))
    for line in extra_lines or ():
        print(c(line, Colors.GREY))
    print()


def _confirm_execution(*, prompt_mode: bool) -> bool:
    if not _can_prompt_user():
        return True
    try:
        if prompt_mode:
            answer = input(c("Press Enter to start or press c to stop this configured command: ", Colors.EMBER))
            if str(answer).strip().lower() == "c":
                print(c(f"{symbol('warn')} Command cancelled; prompt session is still active.", Colors.EMBER))
                return False
            return True
        input(c("Press Enter to start or press Ctrl+C to cancel: ", Colors.EMBER))
        return True
    except KeyboardInterrupt:
        print(c(f"\n{symbol('warn')} Execution cancelled before start.", Colors.EMBER))
        return False


def _wizard_preflight_extension_plan(
    *,
    scopes: Sequence[str],
    profile_preset: str,
    surface_preset: str,
    ocr_preset: str,
    extension_control: str,
    plugin_names: list[str],
    filter_names: list[str],
    include_all_plugins: bool,
    include_all_filters: bool,
) -> bool:
    unique_scopes = list(dict.fromkeys(str(scope).strip().lower() for scope in scopes if str(scope).strip()))
    if not unique_scopes:
        return True

    has_errors = False
    for scope in unique_scopes:
        if scope not in {"profile", "surface", "fusion", "ocr"}:
            continue
        if scope == "surface":
            mode = surface_preset
        elif scope == "fusion":
            mode = merge_scan_modes(profile_preset, surface_preset)
        elif scope == "ocr":
            mode = ocr_preset
        else:
            mode = profile_preset

        plan = resolve_extension_control(
            scope=scope,
            scan_mode=mode,
            control_mode=extension_control,
            requested_plugins=plugin_names,
            requested_filters=filter_names,
            include_all_plugins=include_all_plugins,
            include_all_filters=include_all_filters,
        )
        if plan.errors:
            has_errors = True
            print(
                c(
                    f"{symbol('error')} Wizard extension preflight failed "
                    f"(scope={scope}, mode={plan.scan_mode}, control={plan.control_mode})",
                    Colors.RED,
                )
            )
            for item in plan.errors:
                print(c(f" {symbol('error')} {item}", Colors.RED))
            continue
        if plan.warnings:
            print(
                c(
                    f"{symbol('warn')} Wizard extension preflight warnings "
                    f"(scope={scope}, mode={plan.scan_mode}, control={plan.control_mode})",
                    Colors.EMBER,
                )
            )
            for item in plan.warnings:
                print(c(f" {symbol('warn')} {item}", Colors.EMBER))

    if has_errors:
        print(c(f"{symbol('warn')} Stop: wizard extension configuration is invalid.", Colors.RED))
        print(
            c(
                f"{symbol('tip')} Use `plugins --scope <scope>` and `filters --scope <scope>` "
                "to inspect compatible selectors.",
                Colors.EMBER,
            )
        )
        return False
    return True


def _infer_entity_anomalies(
    entities: Sequence[BaseEntity],
    *,
    issues: Sequence[dict] | None = None,
    fused_anomalies: Sequence[object] | None = None,
) -> list[dict[str, str]]:
    anomalies: list[dict[str, str]] = []
    first_entity_id = entities[0].id if entities else ""

    for entity in entities:
        attributes = dict(entity.attributes)
        status = str(attributes.get("status", "")).strip().upper()
        if status in {"ERROR", "BLOCKED", "INVALID_USERNAME"}:
            anomalies.append(
                {
                    "entity_id": entity.id,
                    "reason": f"status_{status.lower()}",
                }
            )
        if entity.entity_type == "domain":
            https_data = attributes.get("https", {})
            if isinstance(https_data, dict):
                status_code = https_data.get("status")
                if isinstance(status_code, int) and status_code >= 400:
                    anomalies.append(
                        {
                            "entity_id": entity.id,
                            "reason": f"https_status_{status_code}",
                        }
                    )

    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        title = str(issue.get("title", "")).strip().lower().replace(" ", "_")
        if not title:
            continue
        severity = str(issue.get("severity", "LOW")).strip().upper()
        if severity in {"HIGH", "CRITICAL", "MEDIUM"}:
            anomalies.append(
                {
                    "entity_id": first_entity_id,
                    "reason": f"issue_{title}",
                }
            )

    for item in fused_anomalies or []:
        if isinstance(item, dict):
            entity_id = str(item.get("entity_id", "")).strip() or first_entity_id
            reason = str(item.get("reason", "")).strip()
            if entity_id and reason:
                anomalies.append({"entity_id": entity_id, "reason": reason})
            continue
        text = str(item).strip()
        if text and first_entity_id:
            anomalies.append({"entity_id": first_entity_id, "reason": text})

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in anomalies:
        entity_id = str(row.get("entity_id", "")).strip()
        reason = str(row.get("reason", "")).strip().lower()
        if not entity_id or not reason:
            continue
        key = (entity_id, reason)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"entity_id": entity_id, "reason": reason})
    return deduped


def _analyze_intelligence_bundle(
    entities: Sequence[BaseEntity],
    *,
    mode: str,
    target: str,
    issues: Sequence[dict] | None = None,
    fused_anomalies: Sequence[object] | None = None,
    profile_results: Sequence[dict[str, Any]] | None = None,
    domain_result: dict[str, Any] | None = None,
) -> dict:
    if not entities:
        return {}
    anomaly_rows = _infer_entity_anomalies(
        entities,
        issues=issues,
        fused_anomalies=fused_anomalies,
    )
    try:
        bundle = INTELLIGENCE_ENGINE.analyze(
            list(entities),
            mode=mode,
            target=target,
            anomalies=anomaly_rows,
        )
        footprint_map = build_digital_footprint_map(
            target=target,
            mode=mode,
            profile_results=profile_results,
            domain_result=domain_result,
            issues=issues,
            intelligence_bundle=bundle,
        )
        if footprint_map:
            bundle["footprint_map"] = footprint_map
        return bundle
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("intelligence_bundle_failed", f"target={target} mode={mode} reason={exc}", level="WARN")
        return {}


def _print_runtime_guidance_checks(
    *,
    mode: str,
    target: str,
    state: RunnerState,
    timeout_seconds: int,
    worker_budget: int,
    plugin_names: Sequence[str] | None = None,
    filter_names: Sequence[str] | None = None,
    include_all_plugins: bool = False,
    include_all_filters: bool = False,
    surface_scan_directives: SurfaceScanDirectives | None = None,
) -> None:
    selected_plugins = list(plugin_names or [])
    selected_filters = list(filter_names or [])
    plugin_label = ", ".join(selected_plugins) if selected_plugins else "none"
    filter_label = ", ".join(selected_filters) if selected_filters else "none"

    print(c(f"\n{symbol('major')} Execution Guidance Checks", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"{symbol('action')} mode={mode} target={target}", Colors.CYAN))
    print(c(f"{symbol('action')} anonymity={get_anonymity_status(state)}", Colors.CYAN))
    print(c(f"{symbol('action')} timeout_seconds={timeout_seconds} worker_budget={worker_budget}", Colors.CYAN))
    print(c(f"{symbol('feature')} plugins={plugin_label}", Colors.CYAN))
    print(c(f"{symbol('feature')} filters={filter_label}", Colors.CYAN))
    if surface_scan_directives is not None:
        directive_label = ", ".join(surface_scan_directives.scan_types) or "default-http-dns"
        print(c(f"{symbol('feature')} scan_types={directive_label}", Colors.CYAN))
        print(
            c(
                f"{symbol('feature')} scan_verbosity={surface_scan_directives.scan_verbosity} "
                f"os_fingerprint={surface_scan_directives.os_fingerprint_enabled} "
                f"scan_delay={surface_scan_directives.delay_seconds:.2f}s",
                Colors.CYAN,
            )
        )
        for note in surface_scan_directives.notes:
            print(c(f"{symbol('tip')} {note}", Colors.GREY))
    if not selected_plugins:
        print(c(f"{symbol('tip')} enable focused plugins for richer enrichment.", Colors.GREY))
    if not selected_filters:
        print(c(f"{symbol('tip')} enable filters to reduce low-signal noise.", Colors.GREY))


def _build_crypto_plugin_config(
    *,
    scope: str,
    scan_mode: str,
    timeout_seconds: int,
    worker_budget: int,
) -> dict[str, object]:
    mode = merge_scan_modes(scan_mode, scan_mode)
    max_items = 12
    if mode == "fast":
        max_items = 10
    elif mode == "deep":
        max_items = 22
    elif mode == "max":
        max_items = 36

    source_fields: list[str]
    if scope == "surface":
        source_fields = ["domain_result", "issues", "intelligence_bundle", "target"]
    elif scope == "fusion":
        source_fields = [
            "results",
            "domain_result",
            "correlation",
            "issues",
            "intelligence_bundle",
            "target",
        ]
    else:
        source_fields = ["results", "correlation", "issues", "intelligence_bundle", "target"]

    return {
        "operation": "encrypt",
        "output_encoding": "base64",
        "max_items": max_items,
        "strict_mode": mode in {"deep", "max"},
        "source_fields": source_fields,
        "include_metadata": True,
        "scan_scope": scope,
        "scan_mode": mode,
        "timeout_seconds": timeout_seconds,
        "worker_budget": worker_budget,
    }


async def run_profile_scan(
    username: str,
    state: RunnerState,
    timeout_seconds: int,
    max_concurrency: int,
    source_profile: str = "balanced",
    max_platforms: int | None = None,
    scan_mode: str = "balanced",
    *,
    write_csv: bool = False,
    write_html: bool = False,
    live_dashboard: bool = False,
    live_port: int = DEFAULT_DASHBOARD_PORT,
    open_browser: bool = True,
    prompt_mode: bool = False,
    plugin_names: list[str] | None = None,
    include_all_plugins: bool = False,
    filter_names: list[str] | None = None,
    include_all_filters: bool = False,
    output_types: set[str] | None = None,
    output_stamp: str | None = None,
) -> tuple[int, dict | None]:
    append_framework_log("profile_scan_start", f"target={username}")
    ok, error = _validate_network_settings(state, prompt_user=prompt_mode)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        append_framework_log("profile_scan_failed", f"target={username} reason={error}", level="WARN")
        return EXIT_FAILURE, None

    try:
        proxy_url = get_network_settings(state.use_proxy, state.use_tor)
        if proxy_url:
            print(c(f"{symbol('ok')} Network anonymization ENABLED", Colors.GREEN))
    except RuntimeError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        append_framework_log("profile_scan_failed", f"target={username} reason={exc}", level="WARN")
        return EXIT_FAILURE, None

    print(c(f"\n{symbol('action')} Profile scan target: {username}\n", Colors.CYAN))
    print(
        c(
            f"{symbol('bullet')} Source profile: "
            f"{source_profile} | platform budget: {max_platforms if max_platforms is not None else 'all'}",
            Colors.CYAN,
        )
    )
    _print_runtime_guidance_checks(
        mode="profile",
        target=username,
        state=state,
        timeout_seconds=timeout_seconds,
        worker_budget=max_concurrency,
        plugin_names=plugin_names,
        filter_names=filter_names,
        include_all_plugins=include_all_plugins,
        include_all_filters=include_all_filters,
    )
    try:
        results = await scan_username(
            username=username,
            proxy_url=proxy_url,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            source_profile=source_profile,
            max_platforms=max_platforms,
        )
    except PlatformValidationError as exc:
        print(c(f"{symbol('warn')} Platform manifest validation failed: {exc}", Colors.RED))
        append_framework_log("profile_scan_failed", f"target={username} reason={exc}", level="WARN")
        return EXIT_FAILURE, None
    except Exception as exc:
        print(c(f"{symbol('warn')} Scan failed: {exc}", Colors.RED))
        append_framework_log("profile_scan_failed", f"target={username} reason={exc}", level="WARN")
        return EXIT_FAILURE, None

    correlation = correlate(results)
    issues = assess_profile_exposure(results)
    issue_summary = summarize_issues(issues)
    narrative = build_nano_brief(
        username=username,
        profile_results=results,
        correlation=correlation,
        issues=issues,
        issue_summary=issue_summary,
    )
    intelligence_entities = build_profile_entities(username, results)
    intelligence_bundle = _analyze_intelligence_bundle(
        intelligence_entities,
        mode=source_profile,
        target=username,
        issues=issues,
        profile_results=results,
    )
    plugin_results, plugin_errors = await PLUGIN_MANAGER.run_plugins(
        {
            "target": username,
            "mode": "profile",
            "results": results,
            "correlation": correlation,
            "issues": issues,
            "issue_summary": issue_summary,
            "intelligence_bundle": intelligence_bundle,
            "proxy_url": proxy_url,
            "use_tor": state.use_tor,
            "use_proxy": state.use_proxy,
            "crypto_config": _build_crypto_plugin_config(
                scope="profile",
                scan_mode=scan_mode,
                timeout_seconds=timeout_seconds,
                worker_budget=max_concurrency,
            ),
        },
        scope="profile",
        requested_plugins=plugin_names,
        include_all=include_all_plugins,
        chain=False,
    )
    filter_results, filter_errors = execute_filters(
        scope="profile",
        requested_filters=filter_names,
        include_all=include_all_filters,
        context={
            "target": username,
            "mode": "profile",
            "results": results,
            "correlation": correlation,
            "issues": issues,
            "issue_summary": issue_summary,
            "plugins": plugin_results,
            "plugin_errors": plugin_errors,
            "intelligence_bundle": intelligence_bundle,
        },
    )
    display_results(
        results,
        correlation,
        target=username,
        issues=issues,
        issue_summary=issue_summary,
        narrative=narrative,
        plugin_results=plugin_results,
        plugin_errors=plugin_errors,
        filter_results=filter_results,
        filter_errors=filter_errors,
        intelligence_bundle=intelligence_bundle,
    )
    selected_types = output_types or _resolve_output_types(html_flag=None, csv_flag=None)
    stamp = output_stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    write_csv = write_csv or ("csv" in selected_types)
    write_html = write_html or ("html" in selected_types)

    saved = save_results(
        username,
        results,
        correlation,
        issues=issues,
        issue_summary=issue_summary,
        narrative=narrative,
        mode="profile",
        plugin_results=plugin_results,
        plugin_errors=plugin_errors,
        filter_results=filter_results,
        filter_errors=filter_errors,
        intelligence_bundle=intelligence_bundle,
        output_types=selected_types,
        output_stamp=stamp,
        return_payload=write_csv,
    )

    if write_csv:
        payload = saved[1] if isinstance(saved, tuple) and len(saved) > 1 else None
        export_to_csv(username, payload=payload, stamp=stamp)
    report_path = ""
    try:
        if write_html:
            report_path = generate_html(
                target=username,
                results=results,
                correlation=correlation,
                issues=issues,
                issue_summary=issue_summary,
                narrative=narrative,
                mode="profile",
                plugin_results=plugin_results,
                plugin_errors=plugin_errors,
                filter_results=filter_results,
                filter_errors=filter_errors,
                intelligence_bundle=intelligence_bundle,
                output_stamp=stamp,
            )
            print(c(f"HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("profile_html_failed", f"target={username} reason={exc}", level="WARN")
        print(c(f"{symbol('warn')} HTML report generation failed: {exc}", Colors.EMBER))

    if live_dashboard:
        launch_live_dashboard(
            target=username,
            port=live_port,
            open_browser=open_browser,
            background=prompt_mode,
        )

    append_framework_log("profile_scan_done", f"target={username} report={report_path or '-'}")

    return EXIT_SUCCESS, {
        "target": username,
        "results": results,
        "correlation": correlation,
        "issues": issues,
        "issue_summary": issue_summary,
        "narrative": narrative,
        "plugins": plugin_results,
        "plugin_errors": plugin_errors,
        "filters": filter_results,
        "filter_errors": filter_errors,
        "intelligence_bundle": intelligence_bundle,
    }


async def run_surface_scan(
    domain: str,
    state: RunnerState,
    *,
    timeout_seconds: int,
    max_subdomains: int,
    include_ct: bool,
    include_rdap: bool,
    recon_mode: str = "hybrid",
    scan_directives: SurfaceScanDirectives | None = None,
    scan_mode: str = "balanced",
    write_csv: bool = False,
    write_html: bool = False,
    plugin_names: list[str] | None = None,
    include_all_plugins: bool = False,
    filter_names: list[str] | None = None,
    include_all_filters: bool = False,
    output_types: set[str] | None = None,
    output_stamp: str | None = None,
) -> tuple[int, dict | None]:
    normalized_domain = normalize_domain(domain)
    if not normalized_domain:
        print(c(f"{symbol('warn')} Invalid domain.", Colors.RED))
        return EXIT_USAGE, None

    resolved_scan_directives = scan_directives or resolve_surface_scan_directives(recon_mode=recon_mode)
    recon_mode = resolved_scan_directives.recon_mode

    append_framework_log("surface_scan_start", f"target={normalized_domain}")
    ok, error = _validate_network_settings(state, prompt_user=False)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        append_framework_log("surface_scan_failed", f"target={normalized_domain} reason={error}", level="WARN")
        return EXIT_FAILURE, None

    try:
        proxy_url = get_network_settings(state.use_proxy, state.use_tor)
        if proxy_url:
            print(c(f"{symbol('ok')} Network anonymization ENABLED", Colors.GREEN))
    except RuntimeError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        append_framework_log("surface_scan_failed", f"target={normalized_domain} reason={exc}", level="WARN")
        return EXIT_FAILURE, None

    print(c(f"\n{symbol('action')} Domain surface target: {normalized_domain}\n", Colors.CYAN))
    print(c(f"{symbol('bullet')} Recon mode: {recon_mode}", Colors.CYAN))
    _print_runtime_guidance_checks(
        mode="surface",
        target=normalized_domain,
        state=state,
        timeout_seconds=timeout_seconds,
        worker_budget=max_subdomains,
        plugin_names=plugin_names,
        filter_names=filter_names,
        include_all_plugins=include_all_plugins,
        include_all_filters=include_all_filters,
        surface_scan_directives=resolved_scan_directives,
    )
    try:
        domain_result = await scan_domain_surface(
            domain=normalized_domain,
            timeout_seconds=timeout_seconds,
            include_ct=include_ct,
            include_rdap=include_rdap,
            max_subdomains=max_subdomains,
            recon_mode=recon_mode,
        )
    except Exception as exc:
        print(c(f"{symbol('warn')} Domain scan failed: {exc}", Colors.RED))
        append_framework_log("surface_scan_failed", f"target={normalized_domain} reason={exc}", level="WARN")
        return EXIT_FAILURE, None

    issues = assess_domain_exposure(
        domain=normalized_domain,
        https_headers=domain_result.get("https", {}).get("headers", {}),
        http_redirects_to_https=bool(domain_result.get("http", {}).get("redirects_to_https")),
        certificate_transparency_count=len(domain_result.get("subdomains", [])),
        active_http_observed=str(domain_result.get("recon_mode", "hybrid")).lower() in {"active", "hybrid"},
    )
    issue_summary = summarize_issues(issues)
    domain_result["scan_controls"] = resolved_scan_directives.as_dict()
    domain_result["surface_map"] = build_surface_map(domain_result)
    domain_result["next_steps"] = build_surface_next_steps(domain_result, issue_summary=issue_summary)
    domain_result["packet_crafting"] = build_surface_packet_crafting_plan(
        domain_result,
        scan_directives=resolved_scan_directives,
    ).as_dict()
    narrative = build_nano_brief(
        domain=normalized_domain,
        domain_result=domain_result,
        issues=issues,
        issue_summary=issue_summary,
    )
    intelligence_entities = build_surface_entities(domain_result)
    intelligence_bundle = _analyze_intelligence_bundle(
        intelligence_entities,
        mode="surface",
        target=normalized_domain,
        issues=issues,
        domain_result=domain_result,
    )
    plugin_results, plugin_errors = await PLUGIN_MANAGER.run_plugins(
        {
            "target": normalized_domain,
            "mode": "surface",
            "results": [],
            "correlation": {},
            "domain_result": domain_result,
            "issues": issues,
            "issue_summary": issue_summary,
            "intelligence_bundle": intelligence_bundle,
            "proxy_url": proxy_url,
            "use_tor": state.use_tor,
            "use_proxy": state.use_proxy,
            "crypto_config": _build_crypto_plugin_config(
                scope="surface",
                scan_mode=scan_mode,
                timeout_seconds=timeout_seconds,
                worker_budget=max_subdomains,
            ),
        },
        scope="surface",
        requested_plugins=plugin_names,
        include_all=include_all_plugins,
        chain=False,
    )
    filter_results, filter_errors = execute_filters(
        scope="surface",
        requested_filters=filter_names,
        include_all=include_all_filters,
        context={
            "target": normalized_domain,
            "mode": "surface",
            "results": [],
            "correlation": {},
            "domain_result": domain_result,
            "issues": issues,
            "issue_summary": issue_summary,
            "plugins": plugin_results,
            "plugin_errors": plugin_errors,
            "intelligence_bundle": intelligence_bundle,
        },
    )
    display_domain_results(
        domain_result,
        issues=issues,
        issue_summary=issue_summary,
        narrative=narrative,
        plugin_results=plugin_results,
        plugin_errors=plugin_errors,
        filter_results=filter_results,
        filter_errors=filter_errors,
        intelligence_bundle=intelligence_bundle,
    )
    selected_types = output_types or _resolve_output_types(html_flag=None, csv_flag=None)
    stamp = output_stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    write_csv = write_csv or ("csv" in selected_types)
    write_html = write_html or ("html" in selected_types)

    saved = save_results(
        normalized_domain,
        [],
        {},
        issues=issues,
        issue_summary=issue_summary,
        narrative=narrative,
        domain_result=domain_result,
        mode="surface",
        plugin_results=plugin_results,
        plugin_errors=plugin_errors,
        filter_results=filter_results,
        filter_errors=filter_errors,
        intelligence_bundle=intelligence_bundle,
        output_types=selected_types,
        output_stamp=stamp,
        return_payload=write_csv,
    )
    report_path = ""
    try:
        if write_html:
            report_path = generate_html(
                target=normalized_domain,
                results=[],
                correlation={},
                issues=issues,
                issue_summary=issue_summary,
                narrative=narrative,
                domain_result=domain_result,
                mode="surface",
                plugin_results=plugin_results,
                plugin_errors=plugin_errors,
                filter_results=filter_results,
                filter_errors=filter_errors,
                intelligence_bundle=intelligence_bundle,
                output_stamp=stamp,
            )
            print(c(f"HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("surface_html_failed", f"target={normalized_domain} reason={exc}", level="WARN")
        print(c(f"{symbol('warn')} HTML report generation failed: {exc}", Colors.EMBER))

    if write_csv:
        payload = saved[1] if isinstance(saved, tuple) and len(saved) > 1 else None
        export_to_csv(normalized_domain, payload=payload, stamp=stamp)

    append_framework_log("surface_scan_done", f"target={normalized_domain} report={report_path or '-'}")

    return EXIT_SUCCESS, {
        "target": normalized_domain,
        "domain_result": domain_result,
        "issues": issues,
        "issue_summary": issue_summary,
        "narrative": narrative,
        "plugins": plugin_results,
        "plugin_errors": plugin_errors,
        "filters": filter_results,
        "filter_errors": filter_errors,
        "intelligence_bundle": intelligence_bundle,
    }


async def run_ocr_scan(
    *,
    target: str,
    image_paths: list[str],
    image_urls: list[str],
    state: RunnerState,
    timeout_seconds: int,
    max_concurrency: int,
    preprocess_mode: str,
    max_bytes: int,
    max_edge: int | None,
    threshold: int | None,
    scan_mode: str = "balanced",
    write_csv: bool = False,
    write_html: bool = False,
    plugin_names: list[str] | None = None,
    include_all_plugins: bool = False,
    filter_names: list[str] | None = None,
    include_all_filters: bool = False,
    output_types: set[str] | None = None,
    output_stamp: str | None = None,
) -> tuple[int, dict | None]:
    target_label = str(target or "ocr-scan").strip() or "ocr-scan"
    sources_present = bool(image_paths or image_urls)
    if not sources_present:
        print(c(f"{symbol('warn')} OCR scan requires at least one local image path or remote image URL.", Colors.RED))
        return EXIT_USAGE, None

    append_framework_log("ocr_scan_start", f"target={target_label}")
    proxy_url: str | None = None
    if image_urls:
        ok, error = _validate_network_settings(state, prompt_user=False)
        if not ok:
            print(c(f"{symbol('warn')} {error}", Colors.RED))
            append_framework_log("ocr_scan_failed", f"target={target_label} reason={error}", level="WARN")
            return EXIT_FAILURE, None
        try:
            proxy_url = get_network_settings(state.use_proxy, state.use_tor)
        except RuntimeError as exc:
            print(c(f"{symbol('warn')} {exc}", Colors.RED))
            append_framework_log("ocr_scan_failed", f"target={target_label} reason={exc}", level="WARN")
            return EXIT_FAILURE, None

    print(c(f"\n{symbol('action')} OCR image-scan target: {target_label}\n", Colors.CYAN))
    _print_runtime_guidance_checks(
        mode="ocr",
        target=target_label,
        state=state,
        timeout_seconds=timeout_seconds,
        worker_budget=max_concurrency,
        plugin_names=plugin_names,
        filter_names=filter_names,
        include_all_plugins=include_all_plugins,
        include_all_filters=include_all_filters,
    )
    print(c(f"{symbol('feature')} preprocess={preprocess_mode} max_bytes={max_bytes} max_edge={max_edge or '-'} threshold={threshold if threshold is not None else '-'}", Colors.CYAN))

    try:
        ocr_result = await OCRImageScanEngine().run_ocr_scan(
            paths=list(image_paths),
            urls=list(image_urls),
            preprocess_mode=preprocess_mode,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            max_bytes=max_bytes,
            max_edge=max_edge,
            threshold=threshold,
            proxy_url=proxy_url,
        )
    except Exception as exc:
        print(c(f"{symbol('warn')} OCR image scan failed: {exc}", Colors.RED))
        append_framework_log("ocr_scan_failed", f"target={target_label} reason={exc}", level="WARN")
        return EXIT_FAILURE, None

    summary = ocr_result.summary
    signal_totals = summary.signal_totals
    narrative = (
        f"OCR image scan processed {summary.processed_count} of {summary.image_count} supplied image sources, "
        f"recovered text from {summary.ocr_hits} item(s), and extracted "
        f"emails={signal_totals.get('emails', 0)}, urls={signal_totals.get('urls', 0)}, "
        f"phones={signal_totals.get('phones', 0)}, mentions={signal_totals.get('mentions', 0)}."
    )
    payload = ocr_result.as_dict()
    payload["target"] = target_label

    plugin_results, plugin_errors = await PLUGIN_MANAGER.run_plugins(
        {
            "target": target_label,
            "mode": "ocr",
            "ocr_scan": payload,
            "image_paths": list(image_paths),
            "image_urls": list(image_urls),
            "preprocess_mode": preprocess_mode,
            "timeout": timeout_seconds,
            "max_bytes": max_bytes,
            "max_edge": max_edge,
            "threshold": threshold,
            "proxy_url": proxy_url or "",
            "use_tor": state.use_tor,
            "use_proxy": state.use_proxy,
        },
        scope="ocr",
        requested_plugins=plugin_names,
        include_all=include_all_plugins,
        chain=True,
    )
    filter_results, filter_errors = execute_filters(
        scope="ocr",
        requested_filters=filter_names,
        include_all=include_all_filters,
        context={
            "target": target_label,
            "mode": "ocr",
            "ocr_scan": payload,
            "plugins": plugin_results,
            "plugin_errors": plugin_errors,
        },
    )

    display_ocr_results(
        payload,
        plugin_results=plugin_results,
        plugin_errors=plugin_errors,
        filter_results=filter_results,
        filter_errors=filter_errors,
        narrative=narrative,
    )

    selected_types = output_types or _resolve_output_types(html_flag=None, csv_flag=None)
    stamp = output_stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    write_csv = write_csv or ("csv" in selected_types)
    write_html = write_html or ("html" in selected_types)

    saved = save_results(
        target_label,
        [],
        {},
        narrative=narrative,
        mode="ocr",
        plugin_results=plugin_results,
        plugin_errors=plugin_errors,
        filter_results=filter_results,
        filter_errors=filter_errors,
        extra_payload={"ocr_scan": payload},
        output_types=selected_types,
        output_stamp=stamp,
        return_payload=write_csv,
    )

    report_path = ""
    try:
        if write_html:
            report_path = generate_html(
                target=target_label,
                results=[],
                correlation={},
                narrative=narrative,
                mode="ocr",
                plugin_results=plugin_results,
                plugin_errors=plugin_errors,
                filter_results=filter_results,
                filter_errors=filter_errors,
                ocr_scan=payload,
                output_stamp=stamp,
            )
            print(c(f"HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("ocr_html_failed", f"target={target_label} reason={exc}", level="WARN")
        print(c(f"{symbol('warn')} HTML report generation failed: {exc}", Colors.EMBER))

    if write_csv:
        csv_payload = saved[1] if isinstance(saved, tuple) and len(saved) > 1 else None
        export_to_csv(target_label, payload=csv_payload, stamp=stamp)

    append_framework_log("ocr_scan_done", f"target={target_label} report={report_path or '-'}")
    return EXIT_SUCCESS, {
        "target": target_label,
        "ocr_scan": payload,
        "narrative": narrative,
        "plugins": plugin_results,
        "plugin_errors": plugin_errors,
        "filters": filter_results,
        "filter_errors": filter_errors,
    }


def build_root_parser() -> argparse.ArgumentParser:
    return _build_root_parser(
        project_name=PROJECT_NAME,
        version=VERSION,
        default_dashboard_port=DEFAULT_DASHBOARD_PORT,
    )


def build_prompt_parser() -> argparse.ArgumentParser:
    return _build_prompt_parser(default_dashboard_port=DEFAULT_DASHBOARD_PORT)


def _rewrite_tokens_with_keywords(tokens: list[str]) -> list[str]:
    return _rewrite_tokens_with_keywords_impl(tokens)


def _extract_explicit_flags(tokens: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        value = str(token).strip().lower()
        if not value.startswith("--"):
            continue
        flag = value.split("=", maxsplit=1)[0]
        if flag in seen:
            continue
        seen.add(flag)
        ordered.append(flag)
    return tuple(ordered)


def _split_csv_tokens(values: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for chunk in str(raw).split(","):
            token = chunk.strip()
            if not token:
                continue
            lowered = token.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            expanded.append(token)
    return expanded


def _normalize_multi_select_args(args: argparse.Namespace) -> None:
    for field in ("plugin", "filter", "module", "tag", "scan_type", "url"):
        value = getattr(args, field, None)
        if isinstance(value, list):
            setattr(args, field, _split_csv_tokens(value))


def _apply_info_template(
    *,
    scope: str,
    template_id: str | None,
    plugin_names: list[str],
    filter_names: list[str],
    emit: bool = True,
) -> tuple[list[str], list[str], tuple[str, ...], bool]:
    template_value = str(template_id or "").strip()
    if not template_value:
        return plugin_names, filter_names, (), True
    try:
        template = get_info_template(template_value, scope=scope)
    except ValueError as exc:
        if emit:
            print(c(f"{symbol('warn')} {exc}", Colors.RED))
        return plugin_names, filter_names, (), False

    merged_plugins = merge_selectors(plugin_names, template.get("plugins", ()))
    merged_filters = merge_selectors(filter_names, template.get("filters", ()))
    module_tags = tuple(template.get("module_tags", ()))

    if emit:
        print(
            c(
                f"{symbol('ok')} info-template={template.get('id')} "
                f"plugins={len(merged_plugins)} filters={len(merged_filters)}",
                Colors.CYAN,
            )
        )
        if module_tags:
            print(c(f"{symbol('tip')} module tags: {', '.join(module_tags)}", Colors.GREY))
    return merged_plugins, merged_filters, module_tags, True


def _print_prompt_config(session: PromptSessionState, state: RunnerState) -> None:
    print(c(f"\n{symbol('major')} Prompt Configuration", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"prompt: {session.module_prompt()}", Colors.CYAN))
    print(c(f"context: {session.context_summary()}", Colors.CYAN))
    print(c("enabled attachables:", Colors.BLUE))
    print(c(f"  plugins: {session.plugins_label()}", Colors.CYAN))
    print(c(f"  filters: {session.filters_label()}", Colors.CYAN))
    print(c(f"  modules: {session.modules_label()}", Colors.CYAN))
    print(c(f"profile preset: {session.profile_preset}", Colors.CYAN))
    print(c(f"surface preset: {session.surface_preset}", Colors.CYAN))
    print(c(f"profile extension control: {session.profile_extension_control}", Colors.CYAN))
    print(c(f"surface extension control: {session.surface_extension_control}", Colors.CYAN))
    print(c(f"fusion extension control: {session.fusion_extension_control}", Colors.CYAN))
    print(c(f"orchestrate extension control: {session.orchestrate_extension_control}", Colors.CYAN))
    output_settings = describe_output_settings()
    print(c(f"output root: {output_settings.get('output_root')}", Colors.CYAN))
    print(c(f"output types: {output_settings.get('output_types')}", Colors.CYAN))
    print(c(f"output default base: {output_settings.get('default_base_dir')}", Colors.CYAN))
    print(c(f"output current base: {output_settings.get('current_base_dir')}", Colors.CYAN))
    print(c(f"output config: {output_settings.get('config_path')}", Colors.CYAN))
    print(c(f"anonymity: {get_anonymity_status(state)}", Colors.CYAN))
    tor_status = probe_tor_status()
    print(c(f"tor binary: {'present' if tor_status.binary_found else 'missing'}", Colors.CYAN))
    print(
        c(
            f"tor socks: {'reachable' if tor_status.socks_reachable else 'unreachable'} "
            f"({TOR_HOST}:{TOR_SOCKS_PORT})",
            Colors.CYAN,
        )
    )
    prompt_engine = PromptEngine(history=session.history)
    advisor = IntelligenceAdvisor(history=session.history, auto_build_capability_pack=True)
    prompt_suggestions = prompt_engine.suggest_next(limit=3)
    advisor_suggestions = advisor.recommend_next()[:2]
    print(c(f"prompt suggestions: {', '.join(prompt_suggestions)}", Colors.CYAN))
    print(c(f"advisor hints: {', '.join(advisor_suggestions)}", Colors.CYAN))
    print()


def _apply_prompt_defaults(args: argparse.Namespace, session: PromptSessionState) -> argparse.Namespace:
    return _apply_prompt_defaults_impl(args, session)


def _handle_prompt_set_command(command_text: str, session: PromptSessionState) -> bool:
    return _handle_prompt_set_command_impl(command_text, session)


def _handle_prompt_use_command(command_text: str, session: PromptSessionState) -> bool:
    return _handle_prompt_use_command_impl(command_text, session)


def _handle_prompt_control_command(command_text: str, session: PromptSessionState) -> bool:
    return _handle_prompt_control_command_impl(command_text, session)


async def _handle_ocr_command(args: argparse.Namespace, state: RunnerState, prompt_mode: bool = False) -> int:
    if args.list_plugins:
        _print_plugin_inventory(scope="ocr")
        return EXIT_SUCCESS
    if args.list_filters:
        _print_filter_inventory(scope="ocr")
        return EXIT_SUCCESS

    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope="ocr",
        scan_mode=args.preset,
        control_mode=getattr(args, "extension_control", "manual"),
        requested_plugins=list(getattr(args, "plugin", []) or []),
        requested_filters=list(getattr(args, "filter", []) or []),
        include_all_plugins=False,
        include_all_filters=False,
    )
    if not ok_plan:
        return EXIT_USAGE

    module_ids, module_entries, _, ok_modules = _resolve_module_plan_or_fail(
        scope="ocr",
        requested_modules=list(getattr(args, "module", []) or []),
    )
    if not ok_modules:
        return EXIT_USAGE

    override_types, error = _parse_output_type_override(getattr(args, "out_type", None))
    if error:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_USAGE
    html_flag = _explicit_toggle(args, "html")
    csv_flag = _explicit_toggle(args, "csv")
    selected_types = _resolve_output_types(
        html_flag=html_flag,
        csv_flag=csv_flag,
        base_types=override_types,
    )

    override_applied, override_prev = _apply_output_base_override(getattr(args, "out_print", None))
    if getattr(args, "out_print", None) and not override_applied and override_prev:
        print(c(f"{symbol('warn')} {override_prev}", Colors.RED))
        return EXIT_FAILURE

    preview_root = str(get_output_settings().output_root)
    _print_execution_preview(
        heading="Execution Review",
        scope="ocr",
        target=str(getattr(args, "target", "ocr-scan") or "ocr-scan"),
        state=state,
        scan_mode=str(args.preset),
        extension_control=str(getattr(args, "extension_control", "manual")),
        plugin_ids=plugin_ids,
        filter_ids=filter_ids,
        module_entries=module_entries,
        output_types=sorted(selected_types),
        output_root=preview_root,
        extra_lines=(
            f"image paths: {len(list(getattr(args, 'paths', []) or []))}",
            f"image urls: {len(list(getattr(args, 'url', []) or []))}",
        ),
    )
    if not _confirm_execution(prompt_mode=prompt_mode):
        if override_applied:
            _restore_output_base_override(override_prev)
        return EXIT_SUCCESS

    try:
        timeout_seconds, max_concurrency, preprocess_mode, max_bytes, max_edge, threshold = _resolve_ocr_runtime(args)
        status, _ = await run_ocr_scan(
            target=str(getattr(args, "target", "ocr-scan") or "ocr-scan"),
            image_paths=list(getattr(args, "paths", []) or []),
            image_urls=list(getattr(args, "url", []) or []),
            state=state,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            preprocess_mode=preprocess_mode,
            max_bytes=max_bytes,
            max_edge=max_edge,
            threshold=threshold,
            scan_mode=args.preset,
            write_csv=bool(getattr(args, "csv", False)),
            write_html=bool(getattr(args, "html", False)),
            plugin_names=list(plugin_ids),
            include_all_plugins=False,
            filter_names=list(filter_ids),
            include_all_filters=False,
            extra_payload=_preflight_attachable_payload(
                plugin_ids=plugin_ids,
                filter_ids=filter_ids,
                module_entries=module_entries,
            ),
            output_types=selected_types,
            output_stamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
        )
        return status
    finally:
        if override_applied:
            _restore_output_base_override(override_prev)


async def _handle_profile_command(
    args: argparse.Namespace,
    state: RunnerState,
    prompt_mode: bool,
) -> int:
    if args.list_plugins:
        _print_plugin_inventory(scope="profile")
        return EXIT_SUCCESS
    if args.list_filters:
        _print_filter_inventory(scope="profile")
        return EXIT_SUCCESS

    if args.live and len(args.usernames) != 1:
        print(c(f"{symbol('warn')} --live supports a single username at a time.", Colors.RED))
        return EXIT_USAGE

    plugin_names = list(getattr(args, "plugin", []) or [])
    filter_names = list(getattr(args, "filter", []) or [])
    plugin_names, filter_names, _, ok_template = _apply_info_template(
        scope="profile",
        template_id=getattr(args, "info_template", ""),
        plugin_names=plugin_names,
        filter_names=filter_names,
        emit=True,
    )
    if not ok_template:
        return EXIT_USAGE

    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope="profile",
        scan_mode=args.preset,
        control_mode=getattr(args, "extension_control", "manual"),
        requested_plugins=plugin_names,
        requested_filters=filter_names,
        include_all_plugins=False,
        include_all_filters=False,
    )
    if not ok_plan:
        return EXIT_USAGE

    module_ids, module_entries, _, ok_modules = _resolve_module_plan_or_fail(
        scope="profile",
        requested_modules=list(getattr(args, "module", []) or []),
    )
    if not ok_modules:
        return EXIT_USAGE

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_FAILURE

    timeout_seconds, max_concurrency, source_profile, max_platforms = _resolve_profile_runtime(args)
    override_types, error = _parse_output_type_override(getattr(args, "out_type", None))
    if error:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_USAGE
    html_flag = _explicit_toggle(args, "html")
    csv_flag = _explicit_toggle(args, "csv")
    selected_types = _resolve_output_types(
        html_flag=html_flag,
        csv_flag=csv_flag,
        base_types=override_types,
        force_json=bool(getattr(args, "live", False)),
    )

    override_applied, override_prev = _apply_output_base_override(getattr(args, "out_print", None))
    if getattr(args, "out_print", None) and not override_applied and override_prev:
        print(c(f"{symbol('warn')} {override_prev}", Colors.RED))
        return EXIT_FAILURE
    preview_root = str(get_output_settings().output_root)
    usernames_label = ", ".join(str(item).strip() for item in args.usernames[:4])
    if len(args.usernames) > 4:
        usernames_label += f", +{len(args.usernames) - 4} more"
    _print_execution_preview(
        heading="Execution Review",
        scope="profile",
        target=usernames_label,
        state=effective_state,
        scan_mode=str(args.preset),
        extension_control=str(getattr(args, "extension_control", "manual")),
        plugin_ids=plugin_ids,
        filter_ids=filter_ids,
        module_entries=module_entries,
        output_types=sorted(selected_types),
        output_root=preview_root,
        extra_lines=(
            f"timeout seconds: {timeout_seconds}",
            f"max concurrency: {max_concurrency}",
            f"source profile: {source_profile}",
        ),
    )
    if not _confirm_execution(prompt_mode=prompt_mode):
        if override_applied:
            _restore_output_base_override(override_prev)
        return EXIT_SUCCESS
    failures = 0
    try:
        for username in args.usernames:
            clean_username = username.strip()
            if not _validate_username(clean_username):
                print(c(f"{symbol('warn')} Invalid username: '{username}'", Colors.RED))
                failures += 1
                continue
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            status, _ = await run_profile_scan(
                username=clean_username,
                state=effective_state,
                timeout_seconds=timeout_seconds,
                max_concurrency=max_concurrency,
                source_profile=source_profile,
                max_platforms=max_platforms,
                scan_mode=args.preset,
                write_csv=bool(getattr(args, "csv", False)),
                write_html=bool(getattr(args, "html", False)),
                live_dashboard=bool(getattr(args, "live", False)),
                live_port=args.live_port,
                open_browser=not args.no_browser,
                prompt_mode=prompt_mode,
                plugin_names=list(plugin_ids),
                include_all_plugins=False,
                filter_names=list(filter_ids),
                include_all_filters=False,
                extra_payload=_preflight_attachable_payload(
                    plugin_ids=plugin_ids,
                    filter_ids=filter_ids,
                    module_entries=module_entries,
                ),
                output_types=selected_types,
                output_stamp=stamp,
            )
            if status != EXIT_SUCCESS:
                failures += 1
    finally:
        if override_applied:
            _restore_output_base_override(override_prev)
    return EXIT_FAILURE if failures else EXIT_SUCCESS


async def _handle_surface_command(args: argparse.Namespace, state: RunnerState, prompt_mode: bool = False) -> int:
    if args.list_scan_types:
        _print_surface_scan_type_inventory()
        return EXIT_SUCCESS
    if args.list_plugins:
        _print_plugin_inventory(scope="surface")
        return EXIT_SUCCESS
    if args.list_filters:
        _print_filter_inventory(scope="surface")
        return EXIT_SUCCESS

    plugin_names = list(getattr(args, "plugin", []) or [])
    filter_names = list(getattr(args, "filter", []) or [])
    plugin_names, filter_names, _, ok_template = _apply_info_template(
        scope="surface",
        template_id=getattr(args, "info_template", ""),
        plugin_names=plugin_names,
        filter_names=filter_names,
        emit=True,
    )
    if not ok_template:
        return EXIT_USAGE

    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope="surface",
        scan_mode=args.preset,
        control_mode=getattr(args, "extension_control", "manual"),
        requested_plugins=plugin_names,
        requested_filters=filter_names,
        include_all_plugins=False,
        include_all_filters=False,
    )
    if not ok_plan:
        return EXIT_USAGE

    module_ids, module_entries, _, ok_modules = _resolve_module_plan_or_fail(
        scope="surface",
        requested_modules=list(getattr(args, "module", []) or []),
    )
    if not ok_modules:
        return EXIT_USAGE

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_FAILURE

    try:
        timeout_seconds, max_subdomains, scan_directives = _resolve_surface_runtime(args)
    except ValueError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        return EXIT_USAGE
    include_ct = True if args.ct is None else bool(args.ct)
    include_rdap = True if args.rdap is None else bool(args.rdap)

    override_types, error = _parse_output_type_override(getattr(args, "out_type", None))
    if error:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_USAGE
    html_flag = _explicit_toggle(args, "html")
    csv_flag = _explicit_toggle(args, "csv")
    selected_types = _resolve_output_types(
        html_flag=html_flag,
        csv_flag=csv_flag,
        base_types=override_types,
    )

    override_applied, override_prev = _apply_output_base_override(getattr(args, "out_print", None))
    if getattr(args, "out_print", None) and not override_applied and override_prev:
        print(c(f"{symbol('warn')} {override_prev}", Colors.RED))
        return EXIT_FAILURE
    preview_root = str(get_output_settings().output_root)
    _print_execution_preview(
        heading="Execution Review",
        scope="surface",
        target=str(args.domain),
        state=effective_state,
        scan_mode=str(args.preset),
        extension_control=str(getattr(args, "extension_control", "manual")),
        plugin_ids=plugin_ids,
        filter_ids=filter_ids,
        module_entries=module_entries,
        output_types=sorted(selected_types),
        output_root=preview_root,
        extra_lines=(
            f"timeout seconds: {timeout_seconds}",
            f"max subdomains: {max_subdomains}",
            f"recon mode: {scan_directives.recon_mode}",
        ),
    )
    if not _confirm_execution(prompt_mode=prompt_mode):
        if override_applied:
            _restore_output_base_override(override_prev)
        return EXIT_SUCCESS
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        status, _ = await run_surface_scan(
            domain=args.domain,
            state=effective_state,
            timeout_seconds=timeout_seconds,
            max_subdomains=max_subdomains,
            recon_mode=scan_directives.recon_mode,
            scan_directives=scan_directives,
            scan_mode=args.preset,
            include_ct=include_ct,
            include_rdap=include_rdap,
            write_html=bool(getattr(args, "html", False)),
            write_csv=bool(getattr(args, "csv", False)),
            plugin_names=list(plugin_ids),
            include_all_plugins=False,
            filter_names=list(filter_ids),
            include_all_filters=False,
            extra_payload=_preflight_attachable_payload(
                plugin_ids=plugin_ids,
                filter_ids=filter_ids,
                module_entries=module_entries,
            ),
            output_types=selected_types,
            output_stamp=stamp,
        )
    finally:
        if override_applied:
            _restore_output_base_override(override_prev)
    return status


async def _handle_fusion_command(
    args: argparse.Namespace,
    state: RunnerState,
    prompt_mode: bool = False,
) -> int:
    if args.list_scan_types:
        _print_surface_scan_type_inventory()
        return EXIT_SUCCESS
    if args.list_plugins:
        _print_plugin_inventory(scope="fusion")
        return EXIT_SUCCESS
    if args.list_filters:
        _print_filter_inventory(scope="fusion")
        return EXIT_SUCCESS

    fusion_mode = merge_scan_modes(args.profile_preset, args.surface_preset)
    plugin_names = list(getattr(args, "plugin", []) or [])
    filter_names = list(getattr(args, "filter", []) or [])
    plugin_names, filter_names, _, ok_template = _apply_info_template(
        scope="fusion",
        template_id=getattr(args, "info_template", ""),
        plugin_names=plugin_names,
        filter_names=filter_names,
        emit=True,
    )
    if not ok_template:
        return EXIT_USAGE

    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope="fusion",
        scan_mode=fusion_mode,
        control_mode=getattr(args, "extension_control", "manual"),
        requested_plugins=plugin_names,
        requested_filters=filter_names,
        include_all_plugins=False,
        include_all_filters=False,
    )
    if not ok_plan:
        return EXIT_USAGE

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_FAILURE

    override_types, error = _parse_output_type_override(getattr(args, "out_type", None))
    if error:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_USAGE
    html_flag = _explicit_toggle(args, "html")
    csv_flag = _explicit_toggle(args, "csv")
    selected_types = _resolve_output_types(
        html_flag=html_flag,
        csv_flag=csv_flag,
        base_types=override_types,
    )

    override_applied, override_prev = _apply_output_base_override(getattr(args, "out_print", None))
    if getattr(args, "out_print", None) and not override_applied and override_prev:
        print(c(f"{symbol('warn')} {override_prev}", Colors.RED))
        return EXIT_FAILURE

    username = args.username.strip()
    if not _validate_username(username):
        print(c(f"{symbol('warn')} Invalid username: '{args.username}'", Colors.RED))
        if override_applied:
            _restore_output_base_override(override_prev)
        return EXIT_USAGE

    profile_preset = PROFILE_PRESETS[args.profile_preset]
    surface_preset = SURFACE_PRESETS[args.surface_preset]
    try:
        surface_scan_directives = _resolve_surface_scan_directives_from_args(
            args,
            default_recon_mode=str(
                getattr(args, "surface_recon_mode", None)
                or surface_preset.get("recon_mode", "hybrid")
            ),
        )
    except ValueError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        return EXIT_USAGE
    _print_runtime_guidance_checks(
        mode="fusion",
        target=f"{username} + {normalize_domain(args.domain)}",
        state=effective_state,
        timeout_seconds=max(profile_preset["timeout"], surface_preset["timeout"]),
        worker_budget=max(profile_preset["max_concurrency"], surface_preset["max_subdomains"]),
        plugin_names=list(plugin_ids),
        filter_names=list(filter_ids),
        surface_scan_directives=surface_scan_directives,
    )

    try:
        profile_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_status, profile_data = await run_profile_scan(
            username=username,
            state=effective_state,
            timeout_seconds=profile_preset["timeout"],
            max_concurrency=profile_preset["max_concurrency"],
            source_profile=str(profile_preset.get("source_profile", "balanced")),
            max_platforms=(
                profile_preset["max_platforms"]
                if isinstance(profile_preset.get("max_platforms"), int) and profile_preset["max_platforms"] > 0
                else None
            ),
            scan_mode=args.profile_preset,
            write_csv=bool(getattr(args, "csv", False)),
            write_html=bool(getattr(args, "html", False)),
            live_dashboard=False,
            prompt_mode=False,
            output_types=selected_types,
            output_stamp=profile_stamp,
        )
        if profile_status != EXIT_SUCCESS or profile_data is None:
            return EXIT_FAILURE

        surface_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        surface_status, surface_data = await run_surface_scan(
            domain=args.domain,
            state=effective_state,
            timeout_seconds=surface_preset["timeout"],
            max_subdomains=surface_preset["max_subdomains"],
            recon_mode=surface_scan_directives.recon_mode,
            scan_directives=surface_scan_directives,
            scan_mode=args.surface_preset,
            include_ct=True,
            include_rdap=True,
            write_html=bool(getattr(args, "html", False)),
            write_csv=bool(getattr(args, "csv", False)),
            output_types=selected_types,
            output_stamp=surface_stamp,
        )
        if surface_status != EXIT_SUCCESS or surface_data is None:
            return EXIT_FAILURE
    finally:
        if override_applied:
            _restore_output_base_override(override_prev)

    fusion_override_applied = False
    fusion_override_prev: str | None = None
    if getattr(args, "out_print", None):
        fusion_override_applied, fusion_override_prev = _apply_output_base_override(getattr(args, "out_print", None))
        if not fusion_override_applied and fusion_override_prev:
            print(c(f"{symbol('warn')} {fusion_override_prev}", Colors.RED))
            return EXIT_FAILURE

    combined_target = safe_path_component(f"{username}_fusion_{normalize_domain(args.domain)}")
    combined_issues = list(profile_data.get("issues", [])) + list(surface_data.get("issues", []))
    combined_issue_summary = summarize_issues(combined_issues)
    combined_narrative = build_nano_brief(
        username=username,
        profile_results=profile_data.get("results", []),
        correlation=profile_data.get("correlation", {}),
        domain=surface_data.get("target"),
        domain_result=surface_data.get("domain_result"),
        issues=combined_issues,
        issue_summary=combined_issue_summary,
    )
    fused_intel = await FUSION_ENGINE.fuse_profile_domain(profile_data, surface_data)
    fusion_graph = await FUSION_ENGINE.generate_graph(fused_intel)
    intelligence_entities = build_fusion_entities(
        username,
        list(profile_data.get("results", []) or []),
        surface_data.get("domain_result") if isinstance(surface_data.get("domain_result"), dict) else None,
    )
    intelligence_bundle = _analyze_intelligence_bundle(
        intelligence_entities,
        mode=fusion_mode,
        target=combined_target,
        issues=combined_issues,
        fused_anomalies=list(fused_intel.get("anomalies", []) or []),
        profile_results=list(profile_data.get("results", []) or []),
        domain_result=surface_data.get("domain_result") if isinstance(surface_data.get("domain_result"), dict) else None,
    )
    fused_intel["intelligence_bundle"] = intelligence_bundle
    fused_intel["risk_summary"] = intelligence_bundle.get("risk_summary", {})
    fused_intel["confidence_distribution"] = intelligence_bundle.get("confidence_distribution", {})
    advisor = IntelligenceAdvisor(
        history=[{"mode": "profile"}, {"mode": "surface"}, {"mode": "fusion"}],
        auto_build_capability_pack=True,
    )
    fused_intel["advisor_confidence"] = advisor.estimate_confidence(fused_intel)
    fused_intel["advisor_recommendations"] = advisor.recommend_next()

    plugin_results, plugin_errors = await PLUGIN_MANAGER.run_plugins(
        {
            "target": combined_target,
            "mode": "fusion",
            "results": profile_data.get("results", []),
            "correlation": profile_data.get("correlation", {}),
            "domain_result": surface_data.get("domain_result"),
            "issues": combined_issues,
            "issue_summary": combined_issue_summary,
            "fused_intel": fused_intel,
            "fusion_graph": fusion_graph,
            "intelligence_bundle": intelligence_bundle,
            "proxy_url": get_network_settings(effective_state.use_proxy, effective_state.use_tor),
            "use_tor": effective_state.use_tor,
            "use_proxy": effective_state.use_proxy,
            "crypto_config": _build_crypto_plugin_config(
                scope="fusion",
                scan_mode=fusion_mode,
                timeout_seconds=max(profile_preset["timeout"], surface_preset["timeout"]),
                worker_budget=max(profile_preset["max_concurrency"], surface_preset["max_subdomains"]),
            ),
        },
        scope="fusion",
        requested_plugins=list(plugin_ids),
        include_all=False,
        chain=True,
    )
    filter_results, filter_errors = execute_filters(
        scope="fusion",
        requested_filters=list(filter_ids),
        include_all=False,
        context={
            "target": combined_target,
            "mode": "fusion",
            "results": profile_data.get("results", []),
            "correlation": profile_data.get("correlation", {}),
            "domain_result": surface_data.get("domain_result"),
            "issues": combined_issues,
            "issue_summary": combined_issue_summary,
            "plugins": plugin_results,
            "plugin_errors": plugin_errors,
            "fused_intel": fused_intel,
            "fusion_graph": fusion_graph,
            "intelligence_bundle": intelligence_bundle,
        },
    )

    fusion_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = save_results(
        combined_target,
        profile_data.get("results", []),
        profile_data.get("correlation", {}),
        issues=combined_issues,
        issue_summary=combined_issue_summary,
        narrative=combined_narrative,
        domain_result=surface_data.get("domain_result"),
        mode="fusion",
        plugin_results=plugin_results,
        plugin_errors=plugin_errors,
        filter_results=filter_results,
        filter_errors=filter_errors,
        fused_intel=fused_intel,
        fusion_graph=fusion_graph,
        intelligence_bundle=intelligence_bundle,
        output_types=selected_types,
        output_stamp=fusion_stamp,
        return_payload=("csv" in selected_types),
    )
    guidance_actions = (
        intelligence_bundle.get("execution_guidance", {}).get("actions", [])
        if isinstance(intelligence_bundle.get("execution_guidance"), dict)
        else []
    )
    if isinstance(guidance_actions, list) and guidance_actions:
        print(c(f"\n{symbol('major')} Fusion Guidance", Colors.GREEN))
        print(c("-" * 36, Colors.GREEN))
        for action in guidance_actions[:5]:
            if not isinstance(action, dict):
                continue
            print(c(f"{symbol('action')} [{action.get('priority', 'P3')}] {action.get('title', 'Action')}", Colors.GREEN))
            print(c(f"  {symbol('bullet')} why: {action.get('rationale', '-')}", Colors.GREY))
            print(c(f"  {symbol('tip')} hint: {action.get('command_hint', '-')}", Colors.GREY))

    if "csv" in selected_types or getattr(args, "csv", False):
        payload = saved[1] if isinstance(saved, tuple) and len(saved) > 1 else None
        export_to_csv(combined_target, payload=payload, stamp=fusion_stamp)

    report_path = ""
    try:
        if "html" in selected_types or getattr(args, "html", False):
            report_path = REPORT_GENERATOR.generate_html_dashboard(
                {
                    "target": combined_target,
                    "results": profile_data.get("results", []),
                    "correlation": profile_data.get("correlation", {}),
                    "issues": combined_issues,
                    "issue_summary": combined_issue_summary,
                    "narrative": combined_narrative,
                    "domain_result": surface_data.get("domain_result"),
                    "mode": "fusion",
                    "plugins": plugin_results,
                    "plugin_errors": plugin_errors,
                    "filters": filter_results,
                    "filter_errors": filter_errors,
                    "fused_intel": fused_intel,
                    "fusion_graph": fusion_graph,
                    "intelligence_bundle": intelligence_bundle,
                    "output_stamp": fusion_stamp,
                }
            )
            print(c(f"Fusion HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("fusion_html_failed", f"target={combined_target} reason={exc}", level="WARN")
        print(c(f"{symbol('warn')} Fusion HTML report generation failed: {exc}", Colors.EMBER))

    print(c(f"{symbol('ok')} Fusion bundle saved under output/json/", Colors.GREEN))
    append_framework_log("fusion_scan_done", f"target={combined_target} report={report_path or '-'}")
    if fusion_override_applied:
        _restore_output_base_override(fusion_override_prev)
    return EXIT_SUCCESS


async def _handle_orchestrate_command(args: argparse.Namespace, state: RunnerState, prompt_mode: bool = False) -> int:
    mode = str(args.mode).strip().lower()
    if args.list_scan_types:
        _print_surface_scan_type_inventory()
        return EXIT_SUCCESS
    if args.list_plugins:
        _print_plugin_inventory(scope=mode)
        return EXIT_SUCCESS
    if args.list_filters:
        _print_filter_inventory(scope=mode)
        return EXIT_SUCCESS

    plugin_names = list(getattr(args, "plugin", []) or [])
    filter_names = list(getattr(args, "filter", []) or [])
    plugin_names, filter_names, _, ok_template = _apply_info_template(
        scope=mode,
        template_id=getattr(args, "info_template", ""),
        plugin_names=plugin_names,
        filter_names=filter_names,
        emit=True,
    )
    if not ok_template:
        return EXIT_USAGE

    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope=mode,
        scan_mode=args.profile,
        control_mode=getattr(args, "extension_control", "auto"),
        requested_plugins=plugin_names,
        requested_filters=filter_names,
        include_all_plugins=False,
        include_all_filters=False,
    )
    if not ok_plan:
        return EXIT_USAGE

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_FAILURE

    primary_target = args.target.strip()
    if not primary_target:
        print(c(f"{symbol('warn')} Target is required.", Colors.RED))
        return EXIT_USAGE

    secondary_target = str(args.secondary_target or "").strip()
    orchestrator_target = primary_target
    storage_target = safe_path_component(primary_target)
    target_label = primary_target

    if mode == "profile":
        if not _validate_username(primary_target):
            print(c(f"{symbol('warn')} Invalid username target: '{primary_target}'", Colors.RED))
            return EXIT_USAGE
    elif mode == "surface":
        normalized = normalize_domain(primary_target)
        if not normalized:
            print(c(f"{symbol('warn')} Invalid domain target: '{primary_target}'", Colors.RED))
            return EXIT_USAGE
        orchestrator_target = normalized
        storage_target = safe_path_component(normalized)
        target_label = normalized
    elif mode == "fusion":
        normalized_secondary = normalize_domain(secondary_target)
        if not _validate_username(primary_target):
            print(c(f"{symbol('warn')} Invalid fusion username target: '{primary_target}'", Colors.RED))
            return EXIT_USAGE
        if not normalized_secondary:
            print(c(f"{symbol('warn')} Fusion mode requires --secondary-target with a valid domain.", Colors.RED))
            return EXIT_USAGE
        orchestrator_target = primary_target
        storage_target = safe_path_component(f"{primary_target}_fusion_{normalized_secondary}")
        target_label = f"{primary_target} + {normalized_secondary}"
    else:
        print(c(f"{symbol('warn')} Unsupported mode: {mode}", Colors.RED))
        return EXIT_USAGE

    override_types, error = _parse_output_type_override(getattr(args, "out_type", None))
    if error:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_USAGE
    html_flag = _explicit_toggle(args, "html")
    csv_flag = _explicit_toggle(args, "csv")
    selected_types = _resolve_output_types(
        html_flag=html_flag,
        csv_flag=csv_flag,
        base_types=override_types,
    )

    override_applied, override_prev = _apply_output_base_override(getattr(args, "out_print", None))
    if getattr(args, "out_print", None) and not override_applied and override_prev:
        print(c(f"{symbol('warn')} {override_prev}", Colors.RED))
        return EXIT_FAILURE

    profile_preset = PROFILE_PRESETS[args.profile]
    timeout_seconds = _int_from_value(args.timeout, profile_preset["timeout"])
    max_workers = _int_from_value(args.max_workers, profile_preset["max_concurrency"])
    source_profile = (
        str(args.source_profile).strip().lower()
        if args.source_profile
        else str(profile_preset.get("source_profile", "balanced"))
    )

    max_platforms: int | None = None
    if args.max_platforms is not None:
        max_platforms = _int_from_value(args.max_platforms, profile_preset["max_platforms"])
    elif isinstance(profile_preset.get("max_platforms"), int):
        preset_limit = profile_preset["max_platforms"]
        if preset_limit > 0:
            max_platforms = preset_limit

    max_subdomains = (
        _int_from_value(args.max_subdomains, SURFACE_PRESETS["balanced"]["max_subdomains"])
        if args.max_subdomains is not None
        else SURFACE_PRESETS["balanced"]["max_subdomains"]
    )
    try:
        surface_scan_directives = _resolve_surface_scan_directives_from_args(
            args,
            default_recon_mode=str(
                getattr(args, "recon_mode", None)
                or SURFACE_PRESETS["balanced"].get("recon_mode", "hybrid")
            ),
        )
    except ValueError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        if override_applied:
            _restore_output_base_override(override_prev)
        return EXIT_USAGE
    recon_mode = surface_scan_directives.recon_mode
    include_ct = True if args.ct is None else bool(args.ct)
    include_rdap = True if args.rdap is None else bool(args.rdap)
    min_confidence_value = _float_from_value(args.min_confidence, 0.0)
    if min_confidence_value < 0.0 or min_confidence_value > 1.0:
        print(c(f"{symbol('warn')} --min-confidence must be between 0.0 and 1.0.", Colors.RED))
        if override_applied:
            _restore_output_base_override(override_prev)
        return EXIT_USAGE
    min_confidence = min_confidence_value

    config: dict[str, object] = {
        "profile": str(args.profile),
        "timeout": timeout_seconds,
        "max_workers": max_workers,
        "source_profile": source_profile,
        "max_platforms": max_platforms,
        "max_subdomains": max_subdomains,
        "recon_mode": recon_mode,
        "include_ct": include_ct,
        "include_rdap": include_rdap,
        "min_confidence": min_confidence,
        "use_proxy": effective_state.use_proxy,
        "use_tor": effective_state.use_tor,
        "scan_controls": surface_scan_directives.as_dict(),
    }

    if mode == "fusion":
        normalized_secondary = normalize_domain(secondary_target)
        config["profile_target"] = primary_target
        config["surface_target"] = normalized_secondary

    _print_runtime_guidance_checks(
        mode=f"orchestrate:{mode}",
        target=target_label,
        state=effective_state,
        timeout_seconds=timeout_seconds,
        worker_budget=max_workers,
        plugin_names=list(plugin_ids),
        filter_names=list(filter_ids),
        surface_scan_directives=surface_scan_directives if mode in {"surface", "fusion"} else None,
    )

    print(c(f"\n{symbol('action')} Orchestration mode: {mode} | target: {target_label}\n", Colors.CYAN))
    append_framework_log(
        "orchestrator_scan_start",
        f"mode={mode} target={target_label} policy={args.profile} source_profile={source_profile}",
    )

    orchestrator = Orchestrator(target=orchestrator_target, mode=mode, config=config)
    try:
        payload = await orchestrator.run()
    except Exception as exc:
        append_framework_log("orchestrator_scan_failed", f"target={target_label} reason={exc}", level="WARN")
        print(c(f"{symbol('warn')} Orchestration failed: {exc}", Colors.RED))
        if override_applied:
            _restore_output_base_override(override_prev)
        return EXIT_FAILURE

    anomalies = payload.get("fused", {}).get("anomalies", [])
    issue_summary = {"total": len(anomalies)} if isinstance(anomalies, list) else {"total": 0}
    crypto_worker_budget = max_subdomains if mode == "surface" else max_workers
    if mode == "fusion":
        crypto_worker_budget = max(max_workers, max_subdomains)
    plugin_context = {
        "target": target_label,
        "mode": mode,
        "results": payload.get("fused", {}).get("graph", {}).get("nodes", []),
        "correlation": payload.get("fused", {}).get("relationship_map", {}),
        "issues": anomalies if isinstance(anomalies, list) else [],
        "issue_summary": issue_summary,
        "fused_intel": payload.get("fused", {}),
        "fusion_graph": payload.get("fused", {}).get("graph", {}),
        "intelligence_bundle": payload.get("fused", {}).get("intelligence_bundle", {}),
        "proxy_url": get_network_settings(effective_state.use_proxy, effective_state.use_tor),
        "use_tor": effective_state.use_tor,
        "use_proxy": effective_state.use_proxy,
        "scan_controls": surface_scan_directives.as_dict(),
        "crypto_config": _build_crypto_plugin_config(
            scope=mode,
            scan_mode=str(args.profile),
            timeout_seconds=timeout_seconds,
            worker_budget=crypto_worker_budget,
        ),
    }
    plugin_results: list[dict] = []
    plugin_errors: list[str] = []
    if plugin_ids:
        plugin_results, plugin_errors = await PLUGIN_MANAGER.run_plugins(
            plugin_context,
            scope=mode,
            requested_plugins=list(plugin_ids),
            include_all=False,
            chain=True,
        )

    filter_context = dict(plugin_context)
    filter_context.update(
        {
            "plugins": plugin_results,
            "plugin_errors": plugin_errors,
        }
    )
    filter_results: list[dict] = []
    filter_errors: list[str] = []
    if filter_ids:
        filter_results, filter_errors = execute_filters(
            scope=mode,
            requested_filters=list(filter_ids),
            include_all=False,
            context=filter_context,
        )

    payload["plugins"] = plugin_results
    payload["plugin_errors"] = plugin_errors
    payload["filters"] = filter_results
    payload["filter_errors"] = filter_errors
    for item in plugin_errors:
        print(c(f"{symbol('feature')} plugin: {item}", Colors.EMBER))
    for item in filter_errors:
        print(c(f"{symbol('feature')} filter: {item}", Colors.EMBER))

    output_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        ensure_output_tree(types=selected_types)
    except OutputConfigError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        return EXIT_FAILURE
    json_path: str | None = None
    if "json" in selected_types:
        json_file = results_json_path(storage_target, stamp=output_stamp)
        try:
            with json_file.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            json_path = str(json_file)
        except OSError as exc:
            append_framework_log(
                "orchestrator_output_failed",
                f"json_write_failed target={target_label} reason={exc}",
                level="WARN",
            )
            print(c(f"{symbol('warn')} Failed to write orchestration JSON: {exc}", Colors.EMBER))

    summary = str(payload.get("cli_summary", "")).strip()
    if summary:
        print(c(summary, Colors.CYAN))

    cli_path: str | None = None
    if "cli" in selected_types:
        cli_text = str(payload.get("txt_report") or payload.get("cli_summary") or "").strip()
        if not cli_text:
            cli_text = f"Orchestration bundle saved for {target_label}."
        cli_file = cli_report_path(storage_target, stamp=output_stamp)
        try:
            cli_file.write_text(cli_text, encoding="utf-8")
            cli_path = str(cli_file)
        except OSError as exc:
            append_framework_log(
                "orchestrator_output_failed",
                f"cli_write_failed target={target_label} reason={exc}",
                level="WARN",
            )
            print(c(f"{symbol('warn')} Failed to write orchestration CLI report: {exc}", Colors.EMBER))

    html_path = ""
    if "html" in selected_types or args.html:
        html_text = str(payload.get("html_report", "") or "")
        if html_text:
            html_file = html_report_path(storage_target, stamp=output_stamp)
            try:
                html_file.write_text(html_text, encoding="utf-8")
                html_path = str(html_file)
                print(c(f"Orchestration HTML report generated -> {html_path}", Colors.GREEN))
            except OSError as exc:
                append_framework_log(
                    "orchestrator_output_failed",
                    f"html_write_failed target={target_label} reason={exc}",
                    level="WARN",
                )
                print(c(f"{symbol('warn')} Failed to write orchestration HTML report: {exc}", Colors.EMBER))
        else:
            print(c(f"{symbol('warn')} Orchestration HTML payload was empty.", Colors.EMBER))

    if "csv" in selected_types:
        csv_payload = {
            "metadata": {"mode": mode},
            "target": target_label,
            "results": [],
            "issues": payload.get("fused", {}).get("anomalies", []) if isinstance(payload.get("fused"), dict) else [],
            "plugins": plugin_results,
            "filters": filter_results,
            "intelligence_bundle": (
                payload.get("fused", {}).get("intelligence_bundle", {})
                if isinstance(payload.get("fused"), dict)
                else {}
            ),
        }
        export_to_csv(storage_target, payload=csv_payload, stamp=output_stamp)

    run_log: str | None = None
    try:
        log_file = run_log_path(storage_target, stamp=output_stamp)
        log_file.write_text(
            (
                f"timestamp={utc_timestamp()}\n"
                f"target={target_label}\n"
                f"mode=orchestrate:{mode}\n"
                f"plugins={len(plugin_results)}\n"
                f"filters={len(filter_results)}\n"
                f"anomalies={len(anomalies) if isinstance(anomalies, list) else 0}\n"
            ),
            encoding="utf-8",
        )
        run_log = str(log_file)
    except OSError as exc:
        append_framework_log(
            "orchestrator_output_failed",
            f"log_write_failed target={target_label} reason={exc}",
            level="WARN",
        )
        print(c(f"{symbol('warn')} Failed to write orchestration run log: {exc}", Colors.EMBER))

    if json_path:
        print(c(f"{symbol('ok')} Orchestration bundle saved -> {json_path}", Colors.GREEN))
    if cli_path:
        print(c(f"{symbol('ok')} Orchestration CLI report saved -> {cli_path}", Colors.GREEN))
    if run_log:
        print(c(f"{symbol('ok')} Orchestration run log saved -> {run_log}", Colors.GREEN))

    if args.json:
        print(json.dumps(payload, indent=2))

    append_framework_log(
        "orchestrator_scan_done",
        f"target={target_label} mode={mode} json={json_path or '-'} html={html_path or '-'}",
    )
    if override_applied:
        _restore_output_base_override(override_prev)
    return EXIT_SUCCESS


async def _handle_live_command(args: argparse.Namespace, prompt_mode: bool) -> int:
    if not args.target.strip():
        print(c("Invalid target.", Colors.RED))
        return EXIT_USAGE

    launch_live_dashboard(
        target=args.target.strip(),
        port=args.port,
        open_browser=not args.no_browser,
        background=prompt_mode,
    )
    return EXIT_SUCCESS


async def _handle_anonymity_command(
    args: argparse.Namespace,
    state: RunnerState,
    prompt_mode: bool,
) -> int:
    if args.check:
        print(c(f"Current anonymity: {get_anonymity_status(state)}", Colors.CYAN))
        _print_tor_status()
        return EXIT_SUCCESS

    if args.prompt:
        set_anonymity_interactive(state)
    elif prompt_mode and args.tor is None and args.proxy is None:
        if state.use_tor:
            ok, error = _validate_network_settings(state, prompt_user=True)
            if not ok:
                print(c(f"{symbol('warn')} {error}", Colors.RED))
                return EXIT_FAILURE
            print(c("Tor routing is enabled and operational.", Colors.GREEN))
        else:
            print(c("Tor routing is currently OFF.", Colors.EMBER))
            if _prompt_yes_no("Open anonymity configuration now?", True):
                set_anonymity_interactive(state)
    elif args.tor is None and args.proxy is None:
        print(c(f"Current anonymity: {get_anonymity_status(state)}", Colors.CYAN))
    else:
        ok = apply_anonymity_flags(state, tor=args.tor, proxy=args.proxy, prompt_user=True)
        if not ok:
            return EXIT_FAILURE

    if prompt_mode:
        show_banner(get_anonymity_status(state))
    return EXIT_SUCCESS


async def _handle_plugins_command(args: argparse.Namespace) -> int:
    _print_plugin_inventory(scope=args.scope)
    return EXIT_SUCCESS


async def _handle_filters_command(args: argparse.Namespace) -> int:
    _print_filter_inventory(scope=args.scope)
    return EXIT_SUCCESS


async def _handle_templates_command(args: argparse.Namespace) -> int:
    _print_info_templates(as_json=bool(getattr(args, "json", False)))
    return EXIT_SUCCESS


async def _handle_out_type_command(args: argparse.Namespace) -> int:
    raw = getattr(args, "types", None)
    if isinstance(raw, list):
        raw_value = ",".join(str(item) for item in raw)
    else:
        raw_value = str(raw or "").strip()
    tokens = tokenize_output_types(raw_value)
    if not tokens:
        settings = describe_output_settings()
        print(c(f"{symbol('tip')} Current output types: {settings.get('output_types')}", Colors.CYAN))
        print(c(f"{symbol('tip')} Allowed types: cli, html, csv, json", Colors.GREY))
        print(c(f"{symbol('tip')} Example: out-type cli,html,csv,json", Colors.GREY))
        return EXIT_SUCCESS
    types_override, error = _parse_output_type_override(tokens)
    if error:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        print(c(f"{symbol('tip')} Allowed types: cli, html, csv, json", Colors.EMBER))
        return EXIT_USAGE
    desired = types_override or set(DEFAULT_OUTPUT_TYPES)
    try:
        types = update_output_types(desired)
        config_saved = True
    except OutputConfigError as exc:
        types = set_session_output_types(desired)
        config_saved = False
        print(c(f"{symbol('warn')} {exc}", Colors.EMBER))
    try:
        ensure_output_tree(types=types)
    except OutputConfigError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.EMBER))
        return EXIT_FAILURE
    print(c(f"{symbol('ok')} Output types set: {', '.join(types)}", Colors.GREEN))
    if not config_saved:
        print(c(f"{symbol('tip')} Output types applied for this session only (config not saved).", Colors.GREY))
    if "json" not in types:
        print(c(f"{symbol('tip')} JSON output is disabled; live dashboards require JSON results.", Colors.GREY))
    return EXIT_SUCCESS


async def _handle_out_print_command(args: argparse.Namespace, *, make_default: bool = False) -> int:
    path_value = getattr(args, "path", None)
    text = str(path_value or "").strip()
    if not text:
        settings = describe_output_settings()
        print(c(f"{symbol('tip')} output root: {settings.get('output_root')}", Colors.CYAN))
        print(c(f"{symbol('tip')} output types: {settings.get('output_types')}", Colors.CYAN))
        print(c(f"{symbol('tip')} default base: {settings.get('default_base_dir')}", Colors.CYAN))
        print(c(f"{symbol('tip')} current base: {settings.get('current_base_dir')}", Colors.CYAN))
        print(c(f"{symbol('tip')} config: {settings.get('config_path')}", Colors.CYAN))
        return EXIT_SUCCESS
    lowered = text.lower()
    if lowered in {"reset", "clear"}:
        try:
            clear_output_base_dir(clear_default=make_default)
            clear_session_output_base_dir()
        except OutputConfigError as exc:
            print(c(f"{symbol('warn')} {exc}", Colors.EMBER))
            return EXIT_FAILURE
        try:
            ensure_output_tree(types=get_output_settings().types)
        except OutputConfigError as exc:
            print(c(f"{symbol('warn')} {exc}", Colors.EMBER))
            return EXIT_FAILURE
        label = "default" if make_default else "current"
        print(c(f"{symbol('ok')} Output {label} base directory reset to working-dir.", Colors.GREEN))
        return EXIT_SUCCESS
    try:
        base_dir = update_output_base_dir(text, make_default=make_default)
        config_saved = True
    except OutputConfigError as exc:
        try:
            base_dir = set_session_output_base_dir(text)
            config_saved = False
            print(c(f"{symbol('warn')} {exc}", Colors.EMBER))
        except OutputConfigError as session_exc:
            print(c(f"{symbol('warn')} {session_exc}", Colors.RED))
            return EXIT_FAILURE
    try:
        ensure_output_tree(types=get_output_settings().types)
    except OutputConfigError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.EMBER))
        return EXIT_FAILURE
    label = "default" if make_default else "current"
    print(c(f"{symbol('ok')} Output {label} base directory: {base_dir}", Colors.GREEN))
    print(c(f"{symbol('tip')} Output root will be {base_dir / 'output'}", Colors.GREY))
    if not config_saved:
        print(c(f"{symbol('tip')} Output base applied for this session only (config not saved).", Colors.GREY))
    return EXIT_SUCCESS


async def _handle_modules_command(args: argparse.Namespace) -> int:
    try:
        template_id = str(getattr(args, "info_template", "") or "").strip()
        if template_id:
            scope_hint = args.scope if str(args.scope).strip().lower() != "all" else None
            try:
                template = get_info_template(template_id, scope=scope_hint)
            except ValueError as exc:
                print(c(f"{symbol('warn')} {exc}", Colors.RED))
                return EXIT_USAGE
            args.tag = merge_selectors(args.tag or [], template.get("module_tags", ()))
            if not args.json:
                print(
                    c(
                        f"{symbol('ok')} info-template={template.get('id')} "
                        f"module tags={', '.join(template.get('module_tags', ())) or '-'}",
                        Colors.CYAN,
                    )
                )
        _print_modules_inventory(
            scope=args.scope,
            kind=args.kind,
            frameworks=getattr(args, "framework", None),
            search=args.search,
            tags=args.tag,
            min_score=args.min_score,
            sort_by=args.sort_by,
            descending=args.descending,
            limit=args.limit,
            offset=args.offset,
            sync=args.sync,
            validate_catalog=args.validate,
            as_json=args.json,
            stats_only=args.stats_only,
        )
    except Exception as exc:  # pragma: no cover - defensive user-facing guard
        append_framework_log("modules_query_failed", str(exc), level="WARN")
        print(c(f"{symbol('warn')} Module catalog query failed: {exc}", Colors.RED))
        print(c(f"{symbol('tip')} Try `modules --sync` to rebuild catalog metadata.", Colors.EMBER))
        return EXIT_FAILURE
    return EXIT_SUCCESS


async def _handle_frameworks_command(args: argparse.Namespace) -> int:
    try:
        _print_framework_inventory(
            framework=str(getattr(args, "framework", "all") or "all"),
            show_modules=bool(getattr(args, "modules", False)),
            show_presets=bool(getattr(args, "presets", False)),
            show_flags=bool(getattr(args, "flags", False)),
            show_commands=bool(getattr(args, "commands", False)),
            search=str(getattr(args, "search", "") or ""),
            limit=_int_from_value(getattr(args, "limit", 25), 25),
            as_json=bool(getattr(args, "json", False)),
        )
    except Exception as exc:  # pragma: no cover - defensive user-facing guard
        append_framework_log("framework_intel_failed", str(exc), level="WARN")
        print(c(f"{symbol('warn')} Framework intel query failed: {exc}", Colors.RED))
        return EXIT_FAILURE
    return EXIT_SUCCESS


async def _handle_surface_kit_command(args: argparse.Namespace, state: RunnerState) -> int:
    if getattr(args, "list_modules", False):
        _print_framework_inventory(
            framework="recursive-modules",
            show_modules=True,
            search=str(getattr(args, "search", "") or ""),
            limit=_int_from_value(getattr(args, "limit", 25), 25),
            as_json=bool(getattr(args, "json", False)),
        )
        return EXIT_SUCCESS
    if getattr(args, "list_presets", False):
        _print_framework_inventory(
            framework="recursive-modules",
            show_presets=True,
            search=str(getattr(args, "search", "") or ""),
            limit=_int_from_value(getattr(args, "limit", 25), 25),
            as_json=bool(getattr(args, "json", False)),
        )
        return EXIT_SUCCESS
    if getattr(args, "list_flags", False):
        _print_framework_inventory(
            framework="recursive-modules",
            show_flags=True,
            search=str(getattr(args, "search", "") or ""),
            limit=_int_from_value(getattr(args, "limit", 25), 25),
            as_json=bool(getattr(args, "json", False)),
        )
        return EXIT_SUCCESS

    domain = str(getattr(args, "domain", "") or "").strip()
    if not domain:
        _print_framework_inventory(
            framework="recursive-modules",
            show_commands=True,
            show_presets=True,
            search=str(getattr(args, "search", "") or ""),
            limit=_int_from_value(getattr(args, "limit", 25), 25),
            as_json=bool(getattr(args, "json", False)),
        )
        print(c(f"{symbol('tip')} Supply a domain to run a source-derived surface-kit workflow.", Colors.EMBER))
        return EXIT_SUCCESS

    try:
        plan = build_surface_recipe_plan(
            domain=domain,
            recipe_name=str(getattr(args, "preset", "subdomain-enum") or "subdomain-enum"),
            modules=_split_csv_tokens(getattr(args, "module", []) or []),
            require_flags=_split_csv_tokens(getattr(args, "require_flag", []) or []),
            exclude_flags=_split_csv_tokens(getattr(args, "exclude_flag", []) or []),
            recon_mode=getattr(args, "recon_mode", None),
        )
    except ValueError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        return EXIT_USAGE

    if getattr(args, "json", False):
        print(json.dumps(plan, indent=2))
    else:
        _print_surface_recipe_plan(plan)

    if bool(getattr(args, "dry_run", False)):
        return EXIT_SUCCESS

    mapping = plan.get("sylica_mapping", {}) if isinstance(plan.get("sylica_mapping"), dict) else {}
    resolved_preset = str(mapping.get("surface_preset", "balanced"))
    resolved_recon_mode = str(mapping.get("recon_mode", "hybrid"))
    timeout_seconds, max_subdomains, _ = _resolve_surface_runtime(
        argparse.Namespace(
            preset=resolved_preset,
            timeout=None,
            max_subdomains=None,
            recon_mode=resolved_recon_mode,
        )
    )
    override_types, error = _parse_output_type_override(getattr(args, "out_type", None))
    if error:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_USAGE
    selected_types = _resolve_output_types(
        html_flag=getattr(args, "html", None),
        csv_flag=getattr(args, "csv", None),
        base_types=override_types,
    )
    override_applied, override_prev = _apply_output_base_override(getattr(args, "out_print", None))
    if getattr(args, "out_print", None) and not override_applied and override_prev:
        print(c(f"{symbol('warn')} {override_prev}", Colors.RED))
        return EXIT_FAILURE

    effective_state = compute_effective_state(
        state,
        getattr(args, "tor", None),
        getattr(args, "proxy", None),
    )
    try:
        status, _payload = await run_surface_scan(
            domain=domain,
            state=effective_state,
            timeout_seconds=timeout_seconds,
            max_subdomains=max_subdomains,
            include_ct=bool(mapping.get("include_ct", True)),
            include_rdap=bool(mapping.get("include_rdap", True)),
            recon_mode=resolved_recon_mode,
            scan_mode=resolved_preset,
            write_csv=bool(getattr(args, "csv", False)),
            write_html=bool(getattr(args, "html", False)),
            output_types=selected_types,
        )
    finally:
        if override_applied:
            _restore_output_base_override(override_prev)
    return status


async def _handle_history_command(args: argparse.Namespace) -> int:
    _print_scan_history(limit=args.limit)
    return EXIT_SUCCESS


async def _handle_quicktest_command(args: argparse.Namespace) -> int:
    if args.list_templates:
        _print_quicktest_templates()
        return EXIT_SUCCESS

    template_name = str(args.template or "").strip()
    seed_value = _int_from_value(args.seed, 0) if args.seed is not None else None
    try:
        selected = pick_quicktest_template(
            template_id=template_name or None,
            seed=seed_value,
        )
    except ValueError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.RED))
        return EXIT_USAGE

    template_id = str(selected.get("id", "template")).strip() or "template"
    username = str(selected.get("username", "subject")).strip() or "subject"
    domain = normalize_domain(str(selected.get("domain", "")).strip())
    if not domain:
        print(c(f"{symbol('warn')} Quicktest template '{template_id}' has invalid domain.", Colors.RED))
        return EXIT_FAILURE

    profile_results = list(selected.get("profile_results", []) or [])
    domain_result = dict(selected.get("domain_result", {}) or {})
    domain_result["target"] = domain
    correlation = correlate(profile_results)
    profile_issues = assess_profile_exposure(profile_results)
    domain_issues = assess_domain_exposure(
        domain,
        domain_result.get("https", {}).get("headers", {}),
        bool(domain_result.get("http", {}).get("redirects_to_https")),
        len(domain_result.get("subdomains", [])),
        active_http_observed=str(domain_result.get("recon_mode", "hybrid")).lower() in {"active", "hybrid"},
    )
    issues = [*profile_issues, *domain_issues]
    issue_summary = summarize_issues(issues)
    narrative = build_nano_brief(
        username=username,
        profile_results=profile_results,
        correlation=correlation,
        domain=domain,
        domain_result=domain_result,
        issues=issues,
        issue_summary=issue_summary,
    )
    run_suffix = utc_timestamp().replace("+00:00", "z").replace("-", "").replace(":", "")
    storage_target = safe_path_component(f"quicktest_{template_id}_{run_suffix}")
    display_target = f"{username} + {domain} [{template_id}]"

    fused_intel = await FUSION_ENGINE.fuse_profile_domain(
        {
            "target": username,
            "results": profile_results,
            "correlation": correlation,
            "issue_summary": issue_summary,
        },
        {
            "target": domain,
            "domain_result": domain_result,
            "issue_summary": issue_summary,
        },
    )
    fusion_graph = await FUSION_ENGINE.generate_graph(fused_intel)
    intelligence_entities = build_fusion_entities(username, profile_results, domain_result)
    intelligence_bundle = _analyze_intelligence_bundle(
        intelligence_entities,
        mode="quicktest",
        target=storage_target,
        issues=issues,
        fused_anomalies=list(fused_intel.get("anomalies", []) or []),
    )
    fused_intel["intelligence_bundle"] = intelligence_bundle
    fused_intel["risk_summary"] = intelligence_bundle.get("risk_summary", {})
    fused_intel["confidence_distribution"] = intelligence_bundle.get("confidence_distribution", {})

    print(c(f"\n{symbol('major')} Quicktest Run", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"{symbol('action')} template={template_id} selection={selected.get('selection_mode', 'random')}", Colors.CYAN))
    print(c(f"{symbol('action')} target={display_target}", Colors.CYAN))
    print(c(f"{symbol('bullet')} profile_rows={len(profile_results)} subdomains={len(domain_result.get('subdomains', []))}", Colors.CYAN))

    display_results(
        profile_results,
        correlation,
        target=display_target,
        issues=issues,
        issue_summary=issue_summary,
        narrative=narrative,
        plugin_results=[],
        plugin_errors=[],
        filter_results=[],
        filter_errors=[],
        intelligence_bundle=intelligence_bundle,
    )

    override_types, error = _parse_output_type_override(getattr(args, "out_type", None))
    if error:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_USAGE
    selected_types = _resolve_output_types(html_flag=None, csv_flag=None, base_types=override_types)
    output_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    override_applied, override_prev = _apply_output_base_override(getattr(args, "out_print", None))
    if getattr(args, "out_print", None) and not override_applied and override_prev:
        print(c(f"{symbol('warn')} {override_prev}", Colors.RED))
        return EXIT_FAILURE
    saved = save_results(
        storage_target,
        profile_results,
        correlation,
        issues=issues,
        issue_summary=issue_summary,
        narrative=narrative,
        domain_result=domain_result,
        mode="quicktest",
        plugin_results=[],
        plugin_errors=[],
        filter_results=[],
        filter_errors=[],
        fused_intel=fused_intel,
        fusion_graph=fusion_graph,
        intelligence_bundle=intelligence_bundle,
        output_types=selected_types,
        output_stamp=output_stamp,
        return_payload=("csv" in selected_types),
    )
    json_path = saved[0] if isinstance(saved, tuple) else saved

    report_path = ""
    if "html" in selected_types:
        report_path = generate_html(
            target=storage_target,
            results=profile_results,
            correlation=correlation,
            issues=issues,
            issue_summary=issue_summary,
            narrative=narrative,
            domain_result=domain_result,
            mode="quicktest",
            plugin_results=[],
            plugin_errors=[],
            filter_results=[],
            filter_errors=[],
            intelligence_bundle=intelligence_bundle,
            output_stamp=output_stamp,
        )
        print(c(f"{symbol('ok')} Quicktest HTML report generated -> {report_path}", Colors.GREEN))
    csv_path = ""
    if "csv" in selected_types:
        payload = saved[1] if isinstance(saved, tuple) and len(saved) > 1 else None
        csv_path = export_to_csv(storage_target, payload=payload, stamp=output_stamp) or ""
        if csv_path:
            print(c(f"{symbol('ok')} Quicktest CSV export generated -> {csv_path}", Colors.GREEN))
    print(c(f"{symbol('ok')} Quicktest artifacts key -> {storage_target}", Colors.GREEN))
    if override_applied:
        _restore_output_base_override(override_prev)

    payload = {
        "template": {
            "id": template_id,
            "label": selected.get("label"),
            "username": username,
            "domain": domain,
            "selection_mode": selected.get("selection_mode", "random"),
        },
        "storage_target": storage_target,
        "display_target": display_target,
        "results": profile_results,
        "domain_result": domain_result,
        "correlation": correlation,
        "issues": issues,
        "issue_summary": issue_summary,
        "narrative": narrative,
        "fused_intel": fused_intel,
        "fusion_graph": fusion_graph,
        "intelligence_bundle": intelligence_bundle,
        "artifacts": {
            "json_path": json_path,
            "html_path": report_path,
            "csv_path": csv_path,
        },
    }

    append_framework_log(
        "quicktest_done",
        (
            f"template={template_id} selection={selected.get('selection_mode', 'random')} "
            f"target={storage_target} json={json_path} html={report_path} csv={csv_path or '-'}"
        ),
    )

    if args.json:
        print(json.dumps(payload, indent=2))
    return EXIT_SUCCESS


async def _handle_wizard_command(
    args: argparse.Namespace,
    state: RunnerState,
    prompt_mode: bool,
) -> int:
    if getattr(args, "list_scan_types", False):
        _print_surface_scan_type_inventory()
        return EXIT_SUCCESS
    explicit_flags_raw = getattr(args, "_explicit_flags", ())
    explicit_flags = {
        str(flag).strip().lower()
        for flag in explicit_flags_raw
        if isinstance(flag, str) and str(flag).strip()
    }
    wizard_seed_flags = {
        "--profile-phase",
        "--no-profile-phase",
        "--surface-phase",
        "--no-surface-phase",
        "--fusion-phase",
        "--no-fusion-phase",
        "--ocr-phase",
        "--no-ocr-phase",
        "--usernames",
        "--domain",
        "--image-paths",
        "--image-urls",
        "--profile-preset",
        "--surface-preset",
        "--ocr-preset",
        "--preprocess",
        "--threshold",
        "--max-edge",
        "--max-bytes",
        "--extension-control",
        "--plugin",
        "--filter",
        "--info-template",
        "--html",
        "--no-html",
        "--csv",
        "--no-csv",
        "--ct",
        "--no-ct",
        "--rdap",
        "--no-rdap",
        "--sync-modules",
        "--out-type",
        "--out-print",
    }
    seeded_wizard = bool(explicit_flags & wizard_seed_flags)

    listed_inventory = False
    if getattr(args, "list_plugins", False):
        _print_plugin_inventory(scope="all")
        listed_inventory = True
    if getattr(args, "list_filters", False):
        _print_filter_inventory(scope="all")
        listed_inventory = True
    if listed_inventory:
        return EXIT_SUCCESS

    if args.tor is not None or args.proxy is not None:
        ok = apply_anonymity_flags(state, args.tor, args.proxy, prompt_user=True)
        if not ok:
            return EXIT_FAILURE

    print(c(f"\n{symbol('major')} Guided Workflow Wizard", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))

    sync_modules = bool(getattr(args, "sync_modules", False))
    if not sync_modules and not seeded_wizard:
        sync_modules = _prompt_yes_no("Refresh module catalog before scanning?", False)
    if sync_modules:
        try:
            module_catalog = ensure_module_catalog(
                refresh=True,
                validate_catalog=True,
                verify_source_fingerprint=False,
            )
            module_summary = summarize_module_catalog(module_catalog)
            print(
                c(
                    f"{symbol('ok')} Module catalog refreshed "
                    f"(modules={module_summary.get('module_count', 0)}).",
                    Colors.GREEN,
                )
            )
        except Exception as exc:
            append_framework_log("wizard_module_catalog_failed", str(exc), level="WARN")
            print(c(f"{symbol('warn')} Module catalog refresh failed: {exc}", Colors.RED))
            return EXIT_FAILURE

    run_profile_value = getattr(args, "run_profile", None)
    run_surface_value = getattr(args, "run_surface", None)
    run_ocr_value = getattr(args, "run_ocr", None)
    if run_profile_value is not None:
        run_profile = bool(run_profile_value)
    elif seeded_wizard and str(getattr(args, "usernames", "")).strip():
        run_profile = True
    else:
        run_profile = _prompt_yes_no("Run profile intelligence phase?", True)

    if run_surface_value is not None:
        run_surface = bool(run_surface_value)
    elif seeded_wizard and str(getattr(args, "domain", "")).strip():
        run_surface = True
    else:
        run_surface = _prompt_yes_no("Run domain surface phase?", True)

    if run_ocr_value is not None:
        run_ocr = bool(run_ocr_value)
    elif seeded_wizard and (
        str(getattr(args, "image_paths", "")).strip() or str(getattr(args, "image_urls", "")).strip()
    ):
        run_ocr = True
    else:
        run_ocr = _prompt_yes_no("Run OCR image-scan phase?", False)

    if not run_profile and not run_surface and not run_ocr:
        print(c(f"{symbol('warn')} All wizard phases are disabled.", Colors.RED))
        return EXIT_USAGE

    profile_usernames: list[str] = []
    if run_profile:
        provided_usernames = _split_csv_tokens([str(getattr(args, "usernames", ""))])
        valid_usernames = [item for item in provided_usernames if _validate_username(item)]
        invalid_usernames = [item for item in provided_usernames if not _validate_username(item)]
        for invalid in invalid_usernames:
            print(c(f"{symbol('warn')} Ignoring invalid username selector: '{invalid}'", Colors.EMBER))
        profile_usernames = valid_usernames
        if not profile_usernames:
            raw = ask("Enter usernames (comma-separated): ")
            profile_usernames = [item for item in _split_csv_tokens([raw]) if _validate_username(item)]
        if not profile_usernames:
            print(c(f"{symbol('warn')} No valid usernames entered; profile phase skipped.", Colors.EMBER))
            run_profile = False

    surface_domain = ""
    if run_surface:
        surface_domain = str(getattr(args, "domain", "")).strip()
        if not surface_domain:
            surface_domain = ask("Enter target domain: ").strip()
        if not normalize_domain(surface_domain):
            print(c(f"{symbol('warn')} Invalid domain; surface phase skipped.", Colors.EMBER))
            run_surface = False

    image_paths = _split_csv_tokens([str(getattr(args, "image_paths", ""))])
    image_urls = _split_csv_tokens([str(getattr(args, "image_urls", ""))])
    if run_ocr and not image_paths and not image_urls:
        raw_paths = ask("Enter local image paths (comma-separated, optional): ")
        image_paths = _split_csv_tokens([raw_paths])
        raw_urls = ask("Enter remote image URLs (comma-separated, optional): ")
        image_urls = [item for item in _split_csv_tokens([raw_urls]) if item.startswith(("http://", "https://"))]
    else:
        image_urls = [item for item in image_urls if item.startswith(("http://", "https://"))]
    if run_ocr and not image_paths and not image_urls:
        print(c(f"{symbol('warn')} No OCR image sources supplied; OCR phase skipped.", Colors.EMBER))
        run_ocr = False

    run_fusion_value = getattr(args, "run_fusion", None)
    run_fusion = False
    if run_profile and run_surface:
        if run_fusion_value is not None:
            run_fusion = bool(run_fusion_value)
        elif seeded_wizard:
            run_fusion = False
        else:
            run_fusion = _prompt_yes_no("Generate a fusion bundle too?", True)

    profile_preset = str(getattr(args, "profile_preset", None) or "balanced").strip().lower()
    if run_profile or run_fusion:
        if getattr(args, "profile_preset", None) is None:
            profile_preset = _prompt_choice(
                "Profile preset",
                sorted(PROFILE_PRESETS.keys()),
                profile_preset,
            )
        if profile_preset not in PROFILE_PRESETS:
            print(c(f"{symbol('warn')} Invalid profile preset: {profile_preset}", Colors.RED))
            return EXIT_USAGE

    surface_preset = str(getattr(args, "surface_preset", None) or "balanced").strip().lower()
    if run_surface or run_fusion:
        if getattr(args, "surface_preset", None) is None:
            surface_preset = _prompt_choice(
                "Surface preset",
                sorted(SURFACE_PRESETS.keys()),
                surface_preset,
            )
        if surface_preset not in SURFACE_PRESETS:
            print(c(f"{symbol('warn')} Invalid surface preset: {surface_preset}", Colors.RED))
            return EXIT_USAGE

    ocr_preset = str(getattr(args, "ocr_preset", None) or "balanced").strip().lower()
    if run_ocr:
        if getattr(args, "ocr_preset", None) is None:
            ocr_preset = _prompt_choice(
                "OCR preset",
                sorted(OCR_PRESETS.keys()),
                ocr_preset,
            )
        if ocr_preset not in OCR_PRESETS:
            print(c(f"{symbol('warn')} Invalid OCR preset: {ocr_preset}", Colors.RED))
            return EXIT_USAGE

    extension_control = str(getattr(args, "extension_control", None) or "manual").strip().lower()
    if getattr(args, "extension_control", None) is None:
        extension_control = _prompt_choice(
            "Extension control mode",
            EXTENSION_CONTROL_MODES,
            extension_control,
        )
    if extension_control not in EXTENSION_CONTROL_MODES:
        print(c(f"{symbol('warn')} Invalid extension control mode: {extension_control}", Colors.RED))
        return EXIT_USAGE

    write_html_flag = getattr(args, "html", None)
    if write_html_flag is not None:
        write_html = bool(write_html_flag)
    elif seeded_wizard:
        write_html = False
    else:
        write_html = _prompt_yes_no("Generate HTML reports?", True)
    write_csv = False
    csv_flag = getattr(args, "csv", None)
    if run_profile or run_fusion or run_ocr:
        if csv_flag is not None:
            write_csv = bool(csv_flag)
        elif seeded_wizard:
            write_csv = False
        else:
            write_csv = _prompt_yes_no("Export CSV companions?", False)

    include_ct = True
    include_rdap = True
    if run_surface or run_fusion:
        ct_flag = getattr(args, "ct", None)
        rdap_flag = getattr(args, "rdap", None)
        include_ct = bool(ct_flag) if ct_flag is not None else _prompt_yes_no(
            "Include Certificate Transparency lookup?",
            True,
        )
        include_rdap = bool(rdap_flag) if rdap_flag is not None else _prompt_yes_no(
            "Include RDAP ownership lookup?",
            True,
        )

    plugin_names = list(getattr(args, "plugin", []) or [])
    filter_names = list(getattr(args, "filter", []) or [])

    selected_scopes: list[str] = []
    if run_profile:
        selected_scopes.append("profile")
    if run_surface:
        selected_scopes.append("surface")
    if run_fusion:
        selected_scopes.append("fusion")
    if run_ocr:
        selected_scopes.append("ocr")

    template_id = str(getattr(args, "info_template", "") or "").strip()
    if template_id:
        try:
            template = get_info_template(template_id)
        except ValueError as exc:
            print(c(f"{symbol('warn')} {exc}", Colors.RED))
            return EXIT_USAGE
        template_scopes = set(template.get("scopes", ()))
        incompatible = [scope for scope in selected_scopes if scope not in template_scopes]
        if incompatible:
            print(
                c(
                    f"{symbol('warn')} Info-template '{template.get('id')}' is not compatible with "
                    f"wizard scopes: {', '.join(incompatible)}.",
                    Colors.RED,
                )
            )
            return EXIT_USAGE
        plugin_names = merge_selectors(plugin_names, template.get("plugins", ()))
        filter_names = merge_selectors(filter_names, template.get("filters", ()))
        print(
            c(
                f"{symbol('ok')} info-template={template.get('id')} "
                f"plugins={len(plugin_names)} filters={len(filter_names)}",
                Colors.CYAN,
            )
        )
        module_tags = template.get("module_tags", ())
        if module_tags:
            print(c(f"{symbol('tip')} module tags: {', '.join(module_tags)}", Colors.GREY))

    if not seeded_wizard and not plugin_names and _prompt_yes_no("Configure plugin selectors now?", False):
        if len(selected_scopes) > 1:
            print(
                c(
                    f"{symbol('tip')} Multi-phase wizard active. Plugin selectors must be compatible "
                    f"across: {', '.join(selected_scopes)}",
                    Colors.GREY,
                )
            )
        plugin_names = _prompt_extension_selection(
            kind="Plugins",
            scopes=selected_scopes,
        )

    if not seeded_wizard and not filter_names and _prompt_yes_no("Configure filter selectors now?", False):
        if len(selected_scopes) > 1:
            print(
                c(
                    f"{symbol('tip')} Multi-phase wizard active. Filter selectors must be compatible "
                    f"across: {', '.join(selected_scopes)}",
                    Colors.GREY,
                )
            )
        filter_names = _prompt_extension_selection(
            kind="Filters",
            scopes=selected_scopes,
        )

    if selected_scopes and not _wizard_preflight_extension_plan(
        scopes=selected_scopes,
        profile_preset=profile_preset,
        surface_preset=surface_preset,
        ocr_preset=ocr_preset,
        extension_control=extension_control,
        plugin_names=plugin_names,
        filter_names=filter_names,
        include_all_plugins=False,
        include_all_filters=False,
    ):
        return EXIT_USAGE

    failures = 0
    explicit_output_flags: list[str] = []
    if write_html:
        explicit_output_flags.append("--html")
    else:
        explicit_output_flags.append("--no-html")
    if write_csv:
        explicit_output_flags.append("--csv")
    else:
        explicit_output_flags.append("--no-csv")

    if run_profile:
        profile_args = argparse.Namespace(
            usernames=profile_usernames,
            tor=None,
            proxy=None,
            preset=profile_preset,
            extension_control=extension_control,
            timeout=None,
            max_concurrency=None,
            csv=write_csv,
            html=write_html,
            live=False,
            live_port=DEFAULT_DASHBOARD_PORT,
            no_browser=False,
            plugin=plugin_names,
            list_plugins=False,
            filter=filter_names,
            list_filters=False,
            info_template="",
            out_type=str(getattr(args, "out_type", "") or ""),
            out_print=str(getattr(args, "out_print", "") or ""),
            _explicit_flags=tuple(explicit_output_flags),
        )
        if await _handle_profile_command(profile_args, state=state, prompt_mode=prompt_mode) != EXIT_SUCCESS:
            failures += 1

    if run_surface:
        surface_args = argparse.Namespace(
            domain=surface_domain,
            tor=None,
            proxy=None,
            preset=surface_preset,
            extension_control=extension_control,
            timeout=None,
            max_subdomains=None,
            recon_mode=str(getattr(args, "surface_recon_mode", None) or SURFACE_PRESETS[surface_preset].get("recon_mode", "hybrid")),
            scan_type=list(getattr(args, "scan_type", []) or []),
            scan_verbosity=getattr(args, "scan_verbosity", None),
            scan_delay=getattr(args, "scan_delay", None),
            os_fingerprint=getattr(args, "os_fingerprint", None),
            list_scan_types=False,
            ct=include_ct,
            rdap=include_rdap,
            html=write_html,
            csv=write_csv,
            plugin=plugin_names,
            list_plugins=False,
            filter=filter_names,
            list_filters=False,
            info_template="",
            out_type=str(getattr(args, "out_type", "") or ""),
            out_print=str(getattr(args, "out_print", "") or ""),
            _explicit_flags=tuple(explicit_output_flags),
        )
        if await _handle_surface_command(surface_args, state=state) != EXIT_SUCCESS:
            failures += 1

    if run_fusion:
        fusion_args = argparse.Namespace(
            username=profile_usernames[0],
            domain=surface_domain,
            tor=None,
            proxy=None,
            profile_preset=profile_preset,
            surface_preset=surface_preset,
            surface_recon_mode=str(getattr(args, "surface_recon_mode", None) or SURFACE_PRESETS[surface_preset].get("recon_mode", "hybrid")),
            scan_type=list(getattr(args, "scan_type", []) or []),
            scan_verbosity=getattr(args, "scan_verbosity", None),
            scan_delay=getattr(args, "scan_delay", None),
            os_fingerprint=getattr(args, "os_fingerprint", None),
            list_scan_types=False,
            extension_control=extension_control,
            csv=write_csv,
            html=write_html,
            plugin=plugin_names,
            list_plugins=False,
            filter=filter_names,
            list_filters=False,
            info_template="",
            out_type=str(getattr(args, "out_type", "") or ""),
            out_print=str(getattr(args, "out_print", "") or ""),
            _explicit_flags=tuple(explicit_output_flags),
        )
        if await _handle_fusion_command(fusion_args, state=state) != EXIT_SUCCESS:
            failures += 1

    if run_ocr:
        ocr_args = argparse.Namespace(
            paths=image_paths,
            url=image_urls,
            target="wizard-ocr-scan",
            preset=ocr_preset,
            timeout=None,
            max_concurrency=None,
            preprocess=str(getattr(args, "preprocess", None) or OCR_PRESETS[ocr_preset].get("preprocess_mode", "balanced")),
            threshold=getattr(args, "threshold", None),
            max_edge=getattr(args, "max_edge", None),
            max_bytes=getattr(args, "max_bytes", None),
            html=write_html,
            csv=write_csv,
            plugin=plugin_names,
            list_plugins=False,
            filter=filter_names,
            list_filters=False,
            extension_control=extension_control,
            out_type=str(getattr(args, "out_type", "") or ""),
            out_print=str(getattr(args, "out_print", "") or ""),
            _explicit_flags=tuple(explicit_output_flags),
        )
        if await _handle_ocr_command(ocr_args, state=state) != EXIT_SUCCESS:
            failures += 1

    return EXIT_FAILURE if failures else EXIT_SUCCESS


async def _handle_capability_pack_command() -> int:
    try:
        module_catalog = ensure_module_catalog(refresh=True)
        module_summary = summarize_module_catalog(module_catalog)
        capability_path = build_capability_pack()
        report_path = write_capability_report(build_pack=False)
    except Exception as exc:
        append_framework_log("capability_pack_generation_failed", str(exc), level="WARN")
        print(c(f"{symbol('warn')} Capability pack generation failed: {exc}", Colors.RED))
        return EXIT_FAILURE

    print(c(f"{symbol('ok')} Capability pack generated at {capability_path}", Colors.GREEN))
    print(c(f"{symbol('ok')} Capability report generated at {report_path}", Colors.GREEN))
    print(
        c(
            f"{symbol('ok')} Module catalog refreshed at modules/index.json "
            f"(modules={module_summary.get('module_count', 0)})",
            Colors.GREEN,
        )
    )
    append_framework_log(
        "capability_pack_generated",
        f"capability_pack={capability_path} report={report_path} "
        f"module_catalog_count={module_summary.get('module_count', 0)}",
    )
    return EXIT_SUCCESS


async def _dispatch(args: argparse.Namespace, state: RunnerState, prompt_mode: bool) -> int:
    if args.command in {"profile", "scan", "persona", "social"}:
        return await _handle_profile_command(args, state=state, prompt_mode=prompt_mode)
    if args.command in {"surface", "domain", "asset"}:
        return await _handle_surface_command(args, state=state, prompt_mode=prompt_mode)
    if args.command in {"fusion", "full", "combo"}:
        return await _handle_fusion_command(args, state=state, prompt_mode=prompt_mode)
    if args.command in set(OCR_COMMAND_ALIASES):
        return await _handle_ocr_command(args, state=state, prompt_mode=prompt_mode)
    if args.command in {"orchestrate", "orch"}:
        return await _handle_orchestrate_command(args, state=state, prompt_mode=prompt_mode)
    if args.command == "frameworks":
        return await _handle_frameworks_command(args)
    if args.command == "surface-kit":
        return await _handle_surface_kit_command(args, state=state)
    if args.command == "live":
        return await _handle_live_command(args, prompt_mode=prompt_mode)
    if args.command == "anonymity":
        return await _handle_anonymity_command(args, state=state, prompt_mode=prompt_mode)
    if args.command == "keywords":
        _print_keyword_inventory()
        return EXIT_SUCCESS
    if args.command == "plugins":
        return await _handle_plugins_command(args)
    if args.command == "filters":
        return await _handle_filters_command(args)
    if args.command in {"templates", "info-templates"}:
        return await _handle_templates_command(args)
    if args.command == "out-type":
        return await _handle_out_type_command(args)
    if args.command == "out-print":
        return await _handle_out_print_command(args)
    if args.command == "default-out-print":
        return await _handle_out_print_command(args, make_default=True)
    if args.command == "modules":
        return await _handle_modules_command(args)
    if args.command in {"history", "targets", "scans"}:
        return await _handle_history_command(args)
    if args.command in {"quicktest", "qtest", "smoke"}:
        return await _handle_quicktest_command(args)
    if args.command == "help":
        show_flag_help()
        return EXIT_SUCCESS
    if args.command == "about":
        print(c(build_about_text(), Colors.CYAN))
        return EXIT_SUCCESS
    if args.command == "explain":
        print(c(build_explain_text(), Colors.CYAN))
        return EXIT_SUCCESS
    if args.command == "wizard":
        return await _handle_wizard_command(args, state=state, prompt_mode=prompt_mode)
    if args.command in {"capability-pack", "intel"}:
        return await _handle_capability_pack_command()
    return EXIT_USAGE


async def run_prompt_mode(initial_state: RunnerState | None = None) -> int:
    state = initial_state or RunnerState()
    session = PromptSessionState()
    clear_screen()
    show_banner(get_anonymity_status(state))
    _print_runtime_loaded_inventory()
    prompt_parser = build_prompt_parser()

    while True:
        try:
            user_input = ask(f"{session.module_prompt()} ")
        except (KeyboardInterrupt, EOFError):
            print(c("\nInterrupted. Exiting.", Colors.RED))
            return EXIT_SUCCESS

        command_text = user_input.strip()
        if not command_text:
            continue

        try:
            raw_tokens = shlex.split(command_text)
        except ValueError:
            _print_prompt_help_hint(command_text)
            continue
        if not raw_tokens:
            continue

        first_token = raw_tokens[0].strip().lower()
        if first_token == "show":
            if len(raw_tokens) < 2:
                _print_prompt_help_hint(command_text)
                continue
            show_target = _keyword_to_command(raw_tokens[1]) or raw_tokens[1].strip().lower()
            if show_target not in PROMPT_SHOW_COMMANDS:
                _print_prompt_help_hint(command_text)
                continue
            raw_tokens = [show_target, *raw_tokens[2:]]
        else:
            normalized_first = _keyword_to_command(first_token) or first_token
            if normalized_first in PROMPT_SHOW_COMMANDS:
                print(c(f"{symbol('tip')} Use `show {normalized_first}`.", Colors.EMBER))
                continue

        lowered = " ".join(raw_tokens).lower()
        keyword_match = _keyword_to_command(lowered)
        if lowered in PROMPT_KEYWORDS["exit"]:
            print(c("\nExiting Silica-X.", Colors.RED))
            return EXIT_SUCCESS
        if lowered in PROMPT_KEYWORDS["help"]:
            show_prompt_help()
            continue
        if lowered == "clear":
            clear_screen()
            continue
        if keyword_match == "banner" or lowered == "banner":
            clear_screen()
            show_banner(get_anonymity_status(state))
            _print_runtime_loaded_inventory()
            continue
        if lowered == "version":
            print(c(framework_signature(), Colors.CYAN))
            continue
        if keyword_match == "about" or lowered == "about":
            print(c(build_about_text(), Colors.CYAN))
            continue
        if keyword_match == "explain" or lowered == "explain":
            print(c(build_explain_text(), Colors.CYAN))
            continue
        if keyword_match == "keywords":
            _print_keyword_inventory()
            continue
        if keyword_match == "plugins":
            _print_plugin_inventory(scope="all")
            continue
        if keyword_match == "filters":
            _print_filter_inventory(scope="all")
            continue
        if keyword_match == "templates":
            _print_info_templates(as_json=False)
            continue
        if keyword_match == "modules":
            _print_modules_inventory(scope="all", kind="all", frameworks=[], limit=25, sync=False, as_json=False)
            continue
        if keyword_match == "frameworks":
            _print_framework_inventory(framework="all", as_json=False)
            continue
        if keyword_match == "history":
            _print_scan_history(limit=25)
            continue
        if keyword_match == "config" or lowered == "config":
            _print_prompt_config(session, state)
            continue
        if lowered.startswith("set "):
            _handle_prompt_set_command(command_text, session)
            continue
        if lowered.startswith("use "):
            _handle_prompt_use_command(command_text, session)
            continue
        if lowered.startswith("select ") or lowered.startswith("add ") or lowered.startswith("remove "):
            _handle_prompt_control_command(command_text, session)
            continue

        tokens = list(raw_tokens)
        tokens = _rewrite_tokens_with_keywords(tokens)

        # Casual shortcuts:
        if tokens and tokens[0] == "profile" and len(tokens) == 1:
            target = ask("Username target: ")
            tokens = ["profile", target]
        if tokens and tokens[0] == "surface" and len(tokens) == 1:
            target = ask("Domain target: ")
            tokens = ["surface", target]
        if tokens and tokens[0] == "fusion" and len(tokens) == 1:
            username = ask("Username target: ")
            domain = ask("Domain target: ")
            tokens = ["fusion", username, domain]
        if tokens and tokens[0] == "scan" and len(tokens) == 1:
            target = ask("Username target: ")
            tokens = ["scan", target]
        if tokens and tokens[0] == "orchestrate" and len(tokens) == 1:
            mode = ask("Orchestration mode [profile|surface|fusion] [profile]: ").strip().lower() or "profile"
            primary_target = ask("Primary target: ").strip()
            tokens = ["orchestrate", mode, primary_target]
            if mode == "fusion":
                secondary_target = ask("Secondary domain target: ").strip()
                if secondary_target:
                    tokens.extend(["--secondary-target", secondary_target])
        if tokens and tokens[0] == "ocr" and len(tokens) == 1:
            local_paths = ask("Local image paths (comma-separated, optional): ").strip()
            remote_urls = ask("Remote image URLs (comma-separated, optional): ").strip()
            tokens = ["ocr", *_split_csv_tokens([local_paths])]
            for value in _split_csv_tokens([remote_urls]):
                tokens.extend(["--url", value])
        if tokens and keyword_match in {"profile", "surface", "fusion", "orchestrate"} and len(tokens) == 1:
            if keyword_match == "profile":
                target = ask("Username target: ")
                tokens = ["profile", target]
            elif keyword_match == "surface":
                target = ask("Domain target: ")
                tokens = ["surface", target]
            elif keyword_match == "orchestrate":
                mode = ask("Orchestration mode [profile|surface|fusion] [profile]: ").strip().lower() or "profile"
                primary_target = ask("Primary target: ").strip()
                tokens = ["orchestrate", mode, primary_target]
                if mode == "fusion":
                    secondary_target = ask("Secondary domain target: ").strip()
                    if secondary_target:
                        tokens.extend(["--secondary-target", secondary_target])
            else:
                username = ask("Username target: ")
                domain = ask("Domain target: ")
                tokens = ["fusion", username, domain]
        if len(tokens) == 2 and tokens[0] == "scan":
            # Preserve 'scan <username>' behavior in prompt.
            tokens = ["profile", tokens[1]]
        explicit_flags = _extract_explicit_flags(tokens)

        try:
            args = prompt_parser.parse_args(tokens)
        except ValueError:
            _print_prompt_help_hint(command_text)
            continue

        setattr(args, "_explicit_flags", explicit_flags)
        args = _apply_prompt_defaults(args, session)
        _normalize_multi_select_args(args)
        try:
            await _dispatch(args, state=state, prompt_mode=True)
            session.history.append(command_text)
            if len(session.history) > 200:
                session.history = session.history[-200:]
        except Exception as exc:  # pragma: no cover - prompt safety guard
            append_framework_log("prompt_dispatch_error", str(exc), level="ERROR")
            print(c(f"{symbol('warn')} Command failed: {exc}", Colors.RED))


async def run(argv: Sequence[str] | None = None) -> int:
    _configure_console_output()
    try:
        ensure_output_tree()
    except OutputConfigError as exc:
        print(c(f"{symbol('warn')} {exc}", Colors.EMBER))
    parser = build_root_parser()
    _set_non_exiting_parser(parser)
    argv_tokens = list(argv) if argv is not None else sys.argv[1:]
    try:
        args = parser.parse_args(argv_tokens)
    except (argparse.ArgumentError, ValueError):
        print(c(f"{symbol('tip')} Invalid command. Use `help` command.", Colors.EMBER))
        append_framework_log("framework_exit", f"status={EXIT_USAGE} reason=parse_error")
        return EXIT_USAGE
    setattr(args, "_explicit_flags", _extract_explicit_flags(argv_tokens))
    _normalize_multi_select_args(args)
    rendered_argv = " ".join(str(item) for item in argv_tokens)
    append_framework_log("framework_start", f"argv={rendered_argv}")

    if (getattr(args, "about_flag", False) or getattr(args, "explain_flag", False)) and args.command is not None:
        print(
            c(
                "Global flags --about/--explain cannot be combined with a command. "
                "Run them alone (example: python silica-x.py --about).",
                Colors.RED,
            )
        )
        append_framework_log("framework_exit", f"status={EXIT_USAGE}")
        return EXIT_USAGE

    if getattr(args, "about_flag", False) or getattr(args, "explain_flag", False):
        if getattr(args, "about_flag", False):
            print(c(build_about_text(), Colors.CYAN))
        if getattr(args, "explain_flag", False):
            print(c(build_explain_text(), Colors.CYAN))
        append_framework_log("framework_exit", f"status={EXIT_SUCCESS}")
        return EXIT_SUCCESS

    if args.command in (None, "prompt"):
        initial_state = RunnerState()
        if args.command == "prompt":
            initial_state = compute_effective_state(
                base_state=initial_state,
                tor_override=args.tor,
                proxy_override=args.proxy,
            )
            ok, error = _validate_network_settings(initial_state, prompt_user=True)
            if not ok:
                print(c(f"{symbol('warn')} {error}", Colors.RED))
                return EXIT_FAILURE
        status = await run_prompt_mode(initial_state=initial_state)
        append_framework_log("framework_exit", f"status={status}")
        return status

    state = RunnerState()
    status = await _dispatch(args, state=state, prompt_mode=False)
    append_framework_log("framework_exit", f"status={status}")
    return status

