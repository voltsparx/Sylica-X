"""Main runner orchestration for Silica-X."""

from __future__ import annotations

import argparse
import html
import json
import os
import shlex
import sys
import threading
import webbrowser
from dataclasses import dataclass
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any, Sequence

from core.interface.banner import show_banner
from core.collect.anonymity import TOR_HOST, TOR_SOCKS_PORT, install_tor, probe_tor_status, start_tor
from core.interface.about import build_about_text
from core.interface.explain import build_explain_text
from core.interface.cli_config import EXTENSION_CONTROL_MODES, PROFILE_PRESETS, PROMPT_KEYWORDS, SURFACE_PRESETS
from core.interface.cli_parsers import build_prompt_parser as _build_prompt_parser
from core.interface.cli_parsers import build_root_parser as _build_root_parser
from core.foundation.colors import Colors, c
from core.analyze.correlator import correlate
from core.artifacts.csv_export import export_to_csv
from core.collect.domain_intel import normalize_domain, scan_domain_surface
from core.analyze.exposure import assess_domain_exposure, assess_profile_exposure, summarize_issues
from core.extensions.signal_sieve import execute_filters, list_filter_descriptors, list_filter_discovery_errors
from core.interface.help_menu import show_flag_help, show_prompt_help
from core.artifacts.html_report import generate_html
from core.engines.fusion_engine import FusionEngine
from core.intel.advisor import IntelligenceAdvisor
from core.extensions.control_plane import merge_scan_modes, resolve_extension_control
from core.interface.symbols import symbol
from core.orchestrator import Orchestrator
from core.foundation.metadata import PROJECT_NAME, VERSION, framework_signature, utc_timestamp
from core.analyze.narrative import build_nano_brief
from core.collect.network import get_network_settings
from modules.catalog import ensure_module_catalog, query_module_catalog, summarize_module_catalog
from core.artifacts.output import (
    append_framework_log,
    display_domain_results,
    display_results,
    list_scanned_targets,
    save_results,
)
from core.extensions.plugin_manager import PluginManager
from core.intel.prompt_engine import PromptEngine
from core.artifacts.reporting import ReportGenerator
from core.intel.capability_matrix import build_capability_pack, write_capability_report
from core.extensions.signal_forge import list_plugin_descriptors, list_plugin_discovery_errors
from core.collect.platform_schema import PlatformValidationError, load_platforms
from core.analyze.profile_summary import error_profile_rows, found_profile_rows, summarize_target_intel
from core.collect.scanner import scan_username
from core.domain import BaseEntity
from core.foundation.session_state import PromptSessionState
from core.intelligence import IntelligenceEngine
from core.intelligence.entity_builder import build_fusion_entities, build_profile_entities, build_surface_entities
from core.artifacts.storage import ensure_output_tree, results_json_path, sanitize_target
from core.utils.quicktest_data import list_quicktest_templates, pick_quicktest_template
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
PROMPT_SHOW_COMMANDS = {"plugins", "filters", "modules", "history", "keywords", "config"}

PLUGIN_MANAGER = PluginManager()
FUSION_ENGINE = FusionEngine()
REPORT_GENERATOR = ReportGenerator()
INTELLIGENCE_ENGINE = IntelligenceEngine()


@dataclass
class RunnerState:
    use_tor: bool = False
    use_proxy: bool = False


def safe_path_component(value: str) -> str:
    allowed = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in value.strip())
    return allowed.strip("._") or "target"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def ask(message: str) -> str:
    return input(c(message, Colors.YELLOW)).strip()


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

        print(c(f"{symbol('action')} Installing Tor...", Colors.YELLOW))
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

    print(c(f"{symbol('action')} Starting Tor...", Colors.YELLOW))
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


def _prompt_extension_selection(
    *,
    kind: str,
    scopes: Sequence[str],
    default_all: bool = False,
) -> tuple[list[str], bool]:
    default_label = "all" if default_all else "none"
    unique_scopes = list(dict.fromkeys(str(scope).strip().lower() for scope in scopes if str(scope).strip()))
    while True:
        raw = ask(f"{kind} [none|all|list|selector1,selector2] [{default_label}]: ").strip()
        lowered = raw.lower()
        if not raw:
            return ([], True) if default_all else ([], False)
        if lowered in {"none", "off"}:
            return [], False
        if lowered == "all":
            return [], True
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
            return selectors, False
        print(c("Provide selectors separated by commas, or use none/all/list.", Colors.RED))


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


def _print_plugin_inventory(scope: str | None = None) -> None:
    resolved_scope = None if scope in (None, "", "all") else scope
    plugins = list_plugin_descriptors(scope=resolved_scope)
    discovery_errors = list_plugin_discovery_errors(scope=resolved_scope)
    title_suffix = "all scopes" if resolved_scope is None else f"scope={resolved_scope}"
    print(c(f"\n{symbol('major')} Plugins ({title_suffix})", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    if not plugins:
        print(c(f"{symbol('warn')} No plugins discovered.", Colors.YELLOW))
        for error in discovery_errors:
            print(c(f"{symbol('warn')} {error}", Colors.YELLOW))
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
            print(c(f"  scopes: {scopes_text}", Colors.GREY))
            print(c(f"  aliases: {alias_text}", Colors.GREY))
            print(c(f"  desc: {plugin.get('description')}", Colors.GREY))

    core_plugins = [
        plugin for plugin in plugins if str(plugin.get("plugin_group") or "").strip().lower() != "cryptography"
    ]
    crypto_plugins = [
        plugin for plugin in plugins if str(plugin.get("plugin_group") or "").strip().lower() == "cryptography"
    ]
    print(
        c(
            f"{symbol('tip')} core plugins: {len(core_plugins)} | cryptography plugins: {len(crypto_plugins)}",
            Colors.GREY,
        )
    )
    _print_rows(core_plugins, heading="Core Plugin Set", accent=Colors.CYAN)
    _print_rows(crypto_plugins, heading="Cryptography Plugin Set", accent=Colors.MAGENTA)

    for error in discovery_errors:
        print(c(f"{symbol('warn')} {error}", Colors.YELLOW))
    print()


def _print_filter_inventory(scope: str | None = None) -> None:
    resolved_scope = None if scope in (None, "", "all") else scope
    filters = list_filter_descriptors(scope=resolved_scope)
    discovery_errors = list_filter_discovery_errors(scope=resolved_scope)
    title_suffix = "all scopes" if resolved_scope is None else f"scope={resolved_scope}"
    print(c(f"\n{symbol('major')} Filters ({title_suffix})", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    if not filters:
        print(c(f"{symbol('warn')} No filters discovered.", Colors.YELLOW))
        for error in discovery_errors:
            print(c(f"{symbol('warn')} {error}", Colors.YELLOW))
        print()
        return

    for row in filters:
        scopes_text = ", ".join(row.get("scopes", []))
        aliases = row.get("aliases", [])
        alias_text = ", ".join(aliases) if aliases else "-"
        print(c(f"{symbol('feature')} {row.get('id')} - {row.get('title')}", Colors.CYAN))
        print(c(f"  scopes: {scopes_text}", Colors.GREY))
        print(c(f"  aliases: {alias_text}", Colors.GREY))
        print(c(f"  desc: {row.get('description')}", Colors.GREY))
    for error in discovery_errors:
        print(c(f"{symbol('warn')} {error}", Colors.YELLOW))
    print()


def _print_modules_inventory(
    *,
    scope: str = "all",
    kind: str = "all",
    frameworks: list[str] | None = None,
    search: str = "",
    tags: list[str] | None = None,
    min_score: int = 0,
    sort_by: str = "framework",
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
        print(json.dumps(payload, indent=2))
        return

    summary = payload.get("summary", {})
    rows = payload.get("entries", [])
    query = payload.get("query", {})
    matched_total = int(payload.get("matched_total", len(rows)))
    returned_count = int(payload.get("returned_count", len(rows)))
    has_more = bool(payload.get("has_more", False))

    print(c(f"\n{symbol('major')} Modules (scope={scope}, kind={kind})", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"frameworks: {summary.get('framework_count', 0)}", Colors.CYAN))
    print(c(f"module_count: {summary.get('module_count', 0)}", Colors.CYAN))
    print(c(f"matched_total: {matched_total}", Colors.CYAN))
    print(c(f"returned_count: {returned_count}", Colors.CYAN))
    kind_counts = summary.get("kind_counts", {})
    scope_counts = summary.get("scope_counts", {})
    score_bands = summary.get("score_bands", {})
    language_counts = summary.get("language_counts", {})
    capability_counts = summary.get("capability_counts", {})
    print(
        c(
            "kind_counts: "
            f"plugin={kind_counts.get('plugin', 0)} filter={kind_counts.get('filter', 0)}",
            Colors.CYAN,
        )
    )
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
    if framework_values:
        print(c(f"framework_filter: {', '.join(framework_values)}", Colors.CYAN))
    if query.get("search"):
        print(c(f"search: {query.get('search')}", Colors.CYAN))
    if tag_values:
        print(c(f"tags: {', '.join(tag_values)}", Colors.CYAN))
    print(
        c(
            "query_controls: "
            f"min_score={query.get('min_score', 0)} "
            f"sort_by={query.get('sort_by', 'framework')} "
            f"descending={query.get('descending', False)} "
            f"limit={query.get('limit', 0)} "
            f"offset={query.get('offset', 0)} "
            f"validated={query.get('validated', False)}",
            Colors.CYAN,
        )
    )

    if has_more:
        print(c(f"{symbol('tip')} more_results=true (increase --offset or --limit to continue).", Colors.YELLOW))

    if stats_only:
        print(c(f"{symbol('tip')} stats_only=true (entry listing skipped).", Colors.YELLOW))
        print()
        return

    if not rows:
        print(c(f"{symbol('warn')} No module entries matched this query.", Colors.YELLOW))
        print(c(f"{symbol('tip')} Run `modules --sync` if catalog is empty or stale.", Colors.YELLOW))
        print()
        return

    for row in rows:
        print(c(f"{symbol('feature')} {row.get('framework')} :: {row.get('file')}", Colors.CYAN))
        print(
            c(
                f"  kind: {row.get('kind')} | scopes: {', '.join(row.get('scopes', []))} "
                f"| capabilities: {', '.join(row.get('capabilities', [])[:5]) or '-'}",
                Colors.GREY,
            )
        )
        signals = row.get("signals", {})
        metrics = row.get("metrics", {})
        print(
            c(
                "  scores: "
                f"power={metrics.get('power_score', 0)} "
                f"confidence={metrics.get('confidence_score', 0)} "
                f"plugin={signals.get('plugin_score', 0)} "
                f"filter={signals.get('filter_score', 0)} "
                f"profile={signals.get('profile_score', 0)} "
                f"surface={signals.get('surface_score', 0)} "
                f"fusion={signals.get('fusion_score', 0)} "
                f"size={metrics.get('file_size_bytes', 0)}B",
                Colors.GREY,
            )
        )
    print()


def _print_scan_history(limit: int = 25) -> None:
    rows = list_scanned_targets(limit=limit)
    print(c(f"\n{symbol('major')} Scan History", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    if not rows:
        print(c(f"{symbol('warn')} No scan artifacts found under output/data or output/html.", Colors.YELLOW))
        print()
        return

    for index, row in enumerate(rows, start=1):
        print(c(f"{index}. {row['target']}", Colors.CYAN))
        print(c(f"  updated: {row['modified_at']}", Colors.GREY))
        if row.get("source"):
            print(c(f"  source: {row['source']}", Colors.GREY))
        print(c(f"  file: {row['path']}", Colors.GREY))
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
    print(c(f"{symbol('tip')} Run `quicktest` to pick one randomly.", Colors.GREY))
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


def _print_runtime_loaded_inventory() -> None:
    plugins = list_plugin_descriptors(scope=None)
    filters = list_filter_descriptors(scope=None)
    plugin_errors = list_plugin_discovery_errors(scope=None)
    filter_errors = list_filter_discovery_errors(scope=None)
    plugin_scope_counts = _count_scope_coverage(plugins)
    filter_scope_counts = _count_scope_coverage(filters)

    platform_count = 0
    platform_error: str | None = None
    try:
        platform_count = len(load_platforms())
    except Exception as exc:  # pragma: no cover - startup diagnostics
        platform_error = str(exc)

    framework_count = 0
    module_count = 0
    module_plugin_count = 0
    module_filter_count = 0
    module_error: str | None = None
    try:
        catalog = ensure_module_catalog(
            refresh=False,
            validate_catalog=True,
            verify_source_fingerprint=False,
        )
        summary = summarize_module_catalog(catalog)
        framework_count = int(summary.get("framework_count", 0) or 0)
        module_count = int(summary.get("module_count", 0) or 0)
        kind_counts_raw = summary.get("kind_counts", {})
        kind_counts = kind_counts_raw if isinstance(kind_counts_raw, dict) else {}
        module_plugin_count = int(kind_counts.get("plugin", 0) or 0)
        module_filter_count = int(kind_counts.get("filter", 0) or 0)
    except Exception as exc:  # pragma: no cover - startup diagnostics
        module_error = str(exc)

    print(c(f"\n{symbol('major')} Runtime Inventory Loaded", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(
        c(
            f"{symbol('ok')} plugins={len(plugins)} filters={len(filters)} platforms={platform_count}",
            Colors.CYAN,
        )
    )
    print(
        c(
            f"{symbol('ok')} modules={module_count} frameworks={framework_count} "
            f"(plugin_modules={module_plugin_count} filter_modules={module_filter_count})",
            Colors.CYAN,
        )
    )
    print(
        c(
            f"{symbol('feature')} plugin_scope_coverage "
            f"profile={plugin_scope_counts['profile']} "
            f"surface={plugin_scope_counts['surface']} "
            f"fusion={plugin_scope_counts['fusion']}",
            Colors.GREY,
        )
    )
    print(
        c(
            f"{symbol('feature')} filter_scope_coverage "
            f"profile={filter_scope_counts['profile']} "
            f"surface={filter_scope_counts['surface']} "
            f"fusion={filter_scope_counts['fusion']}",
            Colors.GREY,
        )
    )
    if plugin_errors:
        print(c(f"{symbol('warn')} plugin discovery warnings={len(plugin_errors)}", Colors.YELLOW))
    if filter_errors:
        print(c(f"{symbol('warn')} filter discovery warnings={len(filter_errors)}", Colors.YELLOW))
    if platform_error:
        print(c(f"{symbol('warn')} platform inventory unavailable: {platform_error}", Colors.YELLOW))
    if module_error:
        print(c(f"{symbol('warn')} module catalog unavailable: {module_error}", Colors.YELLOW))


def launch_live_dashboard(
    target: str,
    port: int = DEFAULT_DASHBOARD_PORT,
    open_browser: bool = True,
    background: bool = True,
) -> None:
    safe_target = sanitize_target(target.strip())
    if not safe_target:
        raise ValueError("Target is required for live dashboard.")
    ensure_output_tree()

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib hook
            if self.path != "/":
                self.send_error(404)
                return

            file_path = results_json_path(safe_target)
            if not file_path.exists():
                self.send_response(404)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                msg = (
                    f"<h2>No results found for target: {html.escape(safe_target)}</h2>"
                    "<p>Generate a scan first. Reports are stored in output/data and output/html.</p>"
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
                "BLOCKED": "#f39c12",
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
                body {{ font-family: "Trebuchet MS", "Segoe UI", sans-serif; background:#0b1118; color:#e8edf2; padding:20px; }}
                .panel {{ background:#111a24; border:1px solid #2a3a4d; border-radius:12px; padding:14px; margin-top:12px; }}
                table {{ width:100%; border-collapse: collapse; }}
                th, td {{ border:1px solid #2a3a4d; padding:8px; text-align:left; }}
                th {{ background:#172330; }}
                a {{ color:#42a5f5; text-decoration:none; }}
                .muted {{ color:#9aa7b6; }}
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
                <h3>Nano AI Brief</h3>
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
                print(c(f"{symbol('warn')} Failed to open browser: {exc}", Colors.YELLOW))
        with HTTPServer(server_address, Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print(c(f"\n{symbol('warn')} Live dashboard stopped.", Colors.YELLOW))

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


def _resolve_surface_runtime(args: argparse.Namespace) -> tuple[int, int]:
    preset = SURFACE_PRESETS[args.preset]
    timeout_seconds = _int_from_value(args.timeout, preset["timeout"])
    max_subdomains = _int_from_value(args.max_subdomains, preset["max_subdomains"])
    return timeout_seconds, max_subdomains


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
        print(c(f"{symbol('warn')} {warning}", Colors.YELLOW))


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
                Colors.YELLOW,
            )
        )
        print(
            c(
                f"{symbol('tip')} Use `--extension-control manual|hybrid` for explicit selector control.",
                Colors.YELLOW,
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


def _wizard_preflight_extension_plan(
    *,
    scopes: Sequence[str],
    profile_preset: str,
    surface_preset: str,
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
        if scope not in {"profile", "surface", "fusion"}:
            continue
        if scope == "surface":
            mode = surface_preset
        elif scope == "fusion":
            mode = merge_scan_modes(profile_preset, surface_preset)
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
                    Colors.YELLOW,
                )
            )
            for item in plan.warnings:
                print(c(f" {symbol('warn')} {item}", Colors.YELLOW))

    if has_errors:
        print(c(f"{symbol('warn')} Stop: wizard extension configuration is invalid.", Colors.RED))
        print(
            c(
                f"{symbol('tip')} Use `plugins --scope <scope>` and `filters --scope <scope>` "
                "to inspect compatible selectors.",
                Colors.YELLOW,
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
) -> dict:
    if not entities:
        return {}
    anomaly_rows = _infer_entity_anomalies(
        entities,
        issues=issues,
        fused_anomalies=fused_anomalies,
    )
    try:
        return INTELLIGENCE_ENGINE.analyze(
            list(entities),
            mode=mode,
            target=target,
            anomalies=anomaly_rows,
        )
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
) -> None:
    selected_plugins = list(plugin_names or [])
    selected_filters = list(filter_names or [])
    plugin_label = "all" if include_all_plugins else (", ".join(selected_plugins) if selected_plugins else "none")
    filter_label = "all" if include_all_filters else (", ".join(selected_filters) if selected_filters else "none")

    print(c(f"\n{symbol('major')} Execution Guidance Checks", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"{symbol('action')} mode={mode} target={target}", Colors.CYAN))
    print(c(f"{symbol('action')} anonymity={get_anonymity_status(state)}", Colors.CYAN))
    print(c(f"{symbol('action')} timeout_seconds={timeout_seconds} worker_budget={worker_budget}", Colors.CYAN))
    print(c(f"{symbol('feature')} plugins={plugin_label}", Colors.CYAN))
    print(c(f"{symbol('feature')} filters={filter_label}", Colors.CYAN))
    if not include_all_plugins and not selected_plugins:
        print(c(f"{symbol('tip')} enable focused plugins for richer enrichment.", Colors.GREY))
    if not include_all_filters and not selected_filters:
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
    save_results(
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
    )

    if write_csv:
        export_to_csv(username)
    report_path = ""
    try:
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
        )
        if write_html:
            print(c(f"HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("profile_html_failed", f"target={username} reason={exc}", level="WARN")
        print(c(f"{symbol('warn')} HTML report generation failed: {exc}", Colors.YELLOW))

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
    scan_mode: str = "balanced",
    write_html: bool = False,
    plugin_names: list[str] | None = None,
    include_all_plugins: bool = False,
    filter_names: list[str] | None = None,
    include_all_filters: bool = False,
) -> tuple[int, dict | None]:
    normalized_domain = normalize_domain(domain)
    if not normalized_domain:
        print(c(f"{symbol('warn')} Invalid domain.", Colors.RED))
        return EXIT_USAGE, None

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
    )
    try:
        domain_result = await scan_domain_surface(
            domain=normalized_domain,
            timeout_seconds=timeout_seconds,
            include_ct=include_ct,
            include_rdap=include_rdap,
            max_subdomains=max_subdomains,
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
    )
    issue_summary = summarize_issues(issues)
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
    save_results(
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
    )

    report_path = ""
    try:
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
        )
        if write_html:
            print(c(f"HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("surface_html_failed", f"target={normalized_domain} reason={exc}", level="WARN")
        print(c(f"{symbol('warn')} HTML report generation failed: {exc}", Colors.YELLOW))

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
    for field in ("plugin", "filter", "framework", "tag"):
        value = getattr(args, field, None)
        if isinstance(value, list):
            setattr(args, field, _split_csv_tokens(value))


def _print_prompt_config(session: PromptSessionState, state: RunnerState) -> None:
    print(c(f"\n{symbol('major')} Prompt Configuration", Colors.BLUE))
    print(c("-" * 36, Colors.BLUE))
    print(c(f"prompt: {session.module_prompt()}", Colors.CYAN))
    print(c(f"module: {session.module}", Colors.CYAN))
    print(c(f"plugins: {session.plugins_label()}", Colors.CYAN))
    print(c(f"filters: {session.filters_label()}", Colors.CYAN))
    print(c(f"profile preset: {session.profile_preset}", Colors.CYAN))
    print(c(f"surface preset: {session.surface_preset}", Colors.CYAN))
    print(c(f"profile extension control: {session.profile_extension_control}", Colors.CYAN))
    print(c(f"surface extension control: {session.surface_extension_control}", Colors.CYAN))
    print(c(f"fusion extension control: {session.fusion_extension_control}", Colors.CYAN))
    print(c(f"orchestrate extension control: {session.orchestrate_extension_control}", Colors.CYAN))
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

    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope="profile",
        scan_mode=args.preset,
        control_mode=getattr(args, "extension_control", "manual"),
        requested_plugins=args.plugin,
        requested_filters=args.filter,
        include_all_plugins=args.all_plugins,
        include_all_filters=args.all_filters,
    )
    if not ok_plan:
        return EXIT_USAGE

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_FAILURE

    timeout_seconds, max_concurrency, source_profile, max_platforms = _resolve_profile_runtime(args)
    failures = 0
    for username in args.usernames:
        clean_username = username.strip()
        if not _validate_username(clean_username):
            print(c(f"{symbol('warn')} Invalid username: '{username}'", Colors.RED))
            failures += 1
            continue
        status, _ = await run_profile_scan(
            username=clean_username,
            state=effective_state,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            source_profile=source_profile,
            max_platforms=max_platforms,
            scan_mode=args.preset,
            write_csv=args.csv,
            write_html=args.html,
            live_dashboard=args.live,
            live_port=args.live_port,
            open_browser=not args.no_browser,
            prompt_mode=prompt_mode,
            plugin_names=list(plugin_ids),
            include_all_plugins=False,
            filter_names=list(filter_ids),
            include_all_filters=False,
        )
        if status != EXIT_SUCCESS:
            failures += 1
    return EXIT_FAILURE if failures else EXIT_SUCCESS


async def _handle_surface_command(args: argparse.Namespace, state: RunnerState) -> int:
    if args.list_plugins:
        _print_plugin_inventory(scope="surface")
        return EXIT_SUCCESS
    if args.list_filters:
        _print_filter_inventory(scope="surface")
        return EXIT_SUCCESS

    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope="surface",
        scan_mode=args.preset,
        control_mode=getattr(args, "extension_control", "manual"),
        requested_plugins=args.plugin,
        requested_filters=args.filter,
        include_all_plugins=args.all_plugins,
        include_all_filters=args.all_filters,
    )
    if not ok_plan:
        return EXIT_USAGE

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_FAILURE

    timeout_seconds, max_subdomains = _resolve_surface_runtime(args)
    include_ct = True if args.ct is None else bool(args.ct)
    include_rdap = True if args.rdap is None else bool(args.rdap)
    status, _ = await run_surface_scan(
        domain=args.domain,
        state=effective_state,
        timeout_seconds=timeout_seconds,
        max_subdomains=max_subdomains,
        scan_mode=args.preset,
        include_ct=include_ct,
        include_rdap=include_rdap,
        write_html=args.html,
        plugin_names=list(plugin_ids),
        include_all_plugins=False,
        filter_names=list(filter_ids),
        include_all_filters=False,
    )
    return status


async def _handle_fusion_command(
    args: argparse.Namespace,
    state: RunnerState,
) -> int:
    if args.list_plugins:
        _print_plugin_inventory(scope="fusion")
        return EXIT_SUCCESS
    if args.list_filters:
        _print_filter_inventory(scope="fusion")
        return EXIT_SUCCESS

    fusion_mode = merge_scan_modes(args.profile_preset, args.surface_preset)
    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope="fusion",
        scan_mode=fusion_mode,
        control_mode=getattr(args, "extension_control", "manual"),
        requested_plugins=args.plugin,
        requested_filters=args.filter,
        include_all_plugins=args.all_plugins,
        include_all_filters=args.all_filters,
    )
    if not ok_plan:
        return EXIT_USAGE

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"{symbol('warn')} {error}", Colors.RED))
        return EXIT_FAILURE

    username = args.username.strip()
    if not _validate_username(username):
        print(c(f"{symbol('warn')} Invalid username: '{args.username}'", Colors.RED))
        return EXIT_USAGE

    profile_preset = PROFILE_PRESETS[args.profile_preset]
    surface_preset = SURFACE_PRESETS[args.surface_preset]
    _print_runtime_guidance_checks(
        mode="fusion",
        target=f"{username} + {normalize_domain(args.domain)}",
        state=effective_state,
        timeout_seconds=max(profile_preset["timeout"], surface_preset["timeout"]),
        worker_budget=max(profile_preset["max_concurrency"], surface_preset["max_subdomains"]),
        plugin_names=list(plugin_ids),
        filter_names=list(filter_ids),
    )

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
        write_csv=args.csv,
        write_html=False,
        live_dashboard=False,
        prompt_mode=False,
    )
    if profile_status != EXIT_SUCCESS or profile_data is None:
        return EXIT_FAILURE

    surface_status, surface_data = await run_surface_scan(
        domain=args.domain,
        state=effective_state,
        timeout_seconds=surface_preset["timeout"],
        max_subdomains=surface_preset["max_subdomains"],
        scan_mode=args.surface_preset,
        include_ct=True,
        include_rdap=True,
        write_html=False,
    )
    if surface_status != EXIT_SUCCESS or surface_data is None:
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

    save_results(
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

    report_path = ""
    try:
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
            }
        )
        if args.html:
            print(c(f"Fusion HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("fusion_html_failed", f"target={combined_target} reason={exc}", level="WARN")
        print(c(f"{symbol('warn')} Fusion HTML report generation failed: {exc}", Colors.YELLOW))

    print(c(f"{symbol('ok')} Fusion bundle saved under output/data/{combined_target}/", Colors.GREEN))
    append_framework_log("fusion_scan_done", f"target={combined_target} report={report_path or '-'}")
    return EXIT_SUCCESS


async def _handle_orchestrate_command(args: argparse.Namespace, state: RunnerState) -> int:
    mode = str(args.mode).strip().lower()
    if args.list_plugins:
        _print_plugin_inventory(scope=mode)
        return EXIT_SUCCESS
    if args.list_filters:
        _print_filter_inventory(scope=mode)
        return EXIT_SUCCESS

    plugin_ids, filter_ids, _, ok_plan = _resolve_extension_plan_or_fail(
        scope=mode,
        scan_mode=args.profile,
        control_mode=getattr(args, "extension_control", "auto"),
        requested_plugins=args.plugin,
        requested_filters=args.filter,
        include_all_plugins=args.all_plugins,
        include_all_filters=args.all_filters,
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
    include_ct = True if args.ct is None else bool(args.ct)
    include_rdap = True if args.rdap is None else bool(args.rdap)
    min_confidence_value = _float_from_value(args.min_confidence, 0.0)
    if min_confidence_value < 0.0 or min_confidence_value > 1.0:
        print(c(f"{symbol('warn')} --min-confidence must be between 0.0 and 1.0.", Colors.RED))
        return EXIT_USAGE
    min_confidence = min_confidence_value

    config: dict[str, object] = {
        "profile": str(args.profile),
        "timeout": timeout_seconds,
        "max_workers": max_workers,
        "source_profile": source_profile,
        "max_platforms": max_platforms,
        "max_subdomains": max_subdomains,
        "include_ct": include_ct,
        "include_rdap": include_rdap,
        "min_confidence": min_confidence,
        "use_proxy": effective_state.use_proxy,
        "use_tor": effective_state.use_tor,
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
        print(c(f"{symbol('feature')} plugin: {item}", Colors.YELLOW))
    for item in filter_errors:
        print(c(f"{symbol('feature')} filter: {item}", Colors.YELLOW))

    data_dir = os.path.join("output", "data", storage_target)
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, "orchestrator.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    summary = str(payload.get("cli_summary", "")).strip()
    if summary:
        print(c(summary, Colors.CYAN))

    html_path = ""
    if args.html:
        html_path = os.path.join("output", "html", f"{storage_target}_orchestrator.html")
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(str(payload.get("html_report", "")))
        print(c(f"Orchestration HTML report generated -> {html_path}", Colors.GREEN))

    print(c(f"{symbol('ok')} Orchestration bundle saved -> {json_path}", Colors.GREEN))

    if args.json:
        print(json.dumps(payload, indent=2))

    append_framework_log(
        "orchestrator_scan_done",
        f"target={target_label} mode={mode} json={json_path} html={html_path or '-'}",
    )
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
            print(c("Tor routing is currently OFF.", Colors.YELLOW))
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


async def _handle_modules_command(args: argparse.Namespace) -> int:
    try:
        _print_modules_inventory(
            scope=args.scope,
            kind=args.kind,
            frameworks=args.framework,
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
        print(c(f"{symbol('tip')} Try `modules --sync` to rebuild catalog metadata.", Colors.YELLOW))
        return EXIT_FAILURE
    return EXIT_SUCCESS


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

    json_path = save_results(
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
    )

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
    )
    csv_path = export_to_csv(storage_target) or ""

    print(c(f"{symbol('ok')} Quicktest HTML report generated -> {report_path}", Colors.GREEN))
    if csv_path:
        print(c(f"{symbol('ok')} Quicktest CSV export generated -> {csv_path}", Colors.GREEN))
    print(c(f"{symbol('ok')} Quicktest artifacts key -> {storage_target}", Colors.GREEN))

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
        "--usernames",
        "--domain",
        "--profile-preset",
        "--surface-preset",
        "--extension-control",
        "--plugin",
        "--all-plugins",
        "--filter",
        "--all-filters",
        "--html",
        "--no-html",
        "--csv",
        "--no-csv",
        "--ct",
        "--no-ct",
        "--rdap",
        "--no-rdap",
        "--sync-modules",
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
                    f"(frameworks={module_summary.get('framework_count', 0)} "
                    f"modules={module_summary.get('module_count', 0)}).",
                    Colors.GREEN,
                )
            )
        except Exception as exc:
            append_framework_log("wizard_module_catalog_failed", str(exc), level="WARN")
            print(c(f"{symbol('warn')} Module catalog refresh failed: {exc}", Colors.RED))
            return EXIT_FAILURE

    run_profile_value = getattr(args, "run_profile", None)
    run_surface_value = getattr(args, "run_surface", None)
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

    if not run_profile and not run_surface:
        print(c(f"{symbol('warn')} Both profile and surface phases are disabled.", Colors.RED))
        return EXIT_USAGE

    profile_usernames: list[str] = []
    if run_profile:
        provided_usernames = _split_csv_tokens([str(getattr(args, "usernames", ""))])
        valid_usernames = [item for item in provided_usernames if _validate_username(item)]
        invalid_usernames = [item for item in provided_usernames if not _validate_username(item)]
        for invalid in invalid_usernames:
            print(c(f"{symbol('warn')} Ignoring invalid username selector: '{invalid}'", Colors.YELLOW))
        profile_usernames = valid_usernames
        if not profile_usernames:
            raw = ask("Enter usernames (comma-separated): ")
            profile_usernames = [item for item in _split_csv_tokens([raw]) if _validate_username(item)]
        if not profile_usernames:
            print(c(f"{symbol('warn')} No valid usernames entered; profile phase skipped.", Colors.YELLOW))
            run_profile = False

    surface_domain = ""
    if run_surface:
        surface_domain = str(getattr(args, "domain", "")).strip()
        if not surface_domain:
            surface_domain = ask("Enter target domain: ").strip()
        if not normalize_domain(surface_domain):
            print(c(f"{symbol('warn')} Invalid domain; surface phase skipped.", Colors.YELLOW))
            run_surface = False

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
    if run_profile or run_fusion:
        if csv_flag is not None:
            write_csv = bool(csv_flag)
        elif seeded_wizard:
            write_csv = False
        else:
            write_csv = _prompt_yes_no("Export profile/fusion CSV?", False)

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
    plugin_all = bool(getattr(args, "all_plugins", False))
    if plugin_all and plugin_names:
        print(
            c(
                f"{symbol('warn')} Ignoring explicit plugin selectors because --all-plugins is enabled.",
                Colors.YELLOW,
            )
        )
        plugin_names = []
    filter_names = list(getattr(args, "filter", []) or [])
    filter_all = bool(getattr(args, "all_filters", False))
    if filter_all and filter_names:
        print(
            c(
                f"{symbol('warn')} Ignoring explicit filter selectors because --all-filters is enabled.",
                Colors.YELLOW,
            )
        )
        filter_names = []

    selected_scopes: list[str] = []
    if run_profile:
        selected_scopes.append("profile")
    if run_surface:
        selected_scopes.append("surface")
    if run_fusion:
        selected_scopes.append("fusion")

    if (
        not seeded_wizard
        and not plugin_all
        and not plugin_names
        and _prompt_yes_no("Configure plugin selectors now?", False)
    ):
        if len(selected_scopes) > 1:
            print(
                c(
                    f"{symbol('tip')} Multi-phase wizard active. Plugin selectors must be compatible "
                    f"across: {', '.join(selected_scopes)}",
                    Colors.GREY,
                )
            )
        plugin_names, plugin_all = _prompt_extension_selection(
            kind="Plugins",
            scopes=selected_scopes,
            default_all=False,
        )

    if (
        not seeded_wizard
        and not filter_all
        and not filter_names
        and _prompt_yes_no("Configure filter selectors now?", False)
    ):
        if len(selected_scopes) > 1:
            print(
                c(
                    f"{symbol('tip')} Multi-phase wizard active. Filter selectors must be compatible "
                    f"across: {', '.join(selected_scopes)}",
                    Colors.GREY,
                )
            )
        filter_names, filter_all = _prompt_extension_selection(
            kind="Filters",
            scopes=selected_scopes,
            default_all=False,
        )

    if selected_scopes and not _wizard_preflight_extension_plan(
        scopes=selected_scopes,
        profile_preset=profile_preset,
        surface_preset=surface_preset,
        extension_control=extension_control,
        plugin_names=plugin_names,
        filter_names=filter_names,
        include_all_plugins=plugin_all,
        include_all_filters=filter_all,
    ):
        return EXIT_USAGE

    failures = 0
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
            all_plugins=plugin_all,
            list_plugins=False,
            filter=filter_names,
            all_filters=filter_all,
            list_filters=False,
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
            ct=include_ct,
            rdap=include_rdap,
            html=write_html,
            plugin=plugin_names,
            all_plugins=plugin_all,
            list_plugins=False,
            filter=filter_names,
            all_filters=filter_all,
            list_filters=False,
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
            extension_control=extension_control,
            csv=write_csv,
            html=write_html,
            plugin=plugin_names,
            all_plugins=plugin_all,
            list_plugins=False,
            filter=filter_names,
            all_filters=filter_all,
            list_filters=False,
        )
        if await _handle_fusion_command(fusion_args, state=state) != EXIT_SUCCESS:
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
        return await _handle_surface_command(args, state=state)
    if args.command in {"fusion", "full", "combo"}:
        return await _handle_fusion_command(args, state=state)
    if args.command in {"orchestrate", "orch"}:
        return await _handle_orchestrate_command(args, state=state)
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
        except ValueError as exc:
            print(c(f"Invalid command syntax: {exc}", Colors.RED))
            continue
        if not raw_tokens:
            continue

        first_token = raw_tokens[0].strip().lower()
        if first_token == "show":
            if len(raw_tokens) < 2:
                print(
                    c(
                        "Usage: show <plugins|filters|modules|history|keywords|config> [flags]",
                        Colors.YELLOW,
                    )
                )
                continue
            show_target = _keyword_to_command(raw_tokens[1]) or raw_tokens[1].strip().lower()
            if show_target not in PROMPT_SHOW_COMMANDS:
                print(c(f"Unsupported show target: {raw_tokens[1]}", Colors.RED))
                continue
            raw_tokens = [show_target, *raw_tokens[2:]]
        else:
            normalized_first = _keyword_to_command(first_token) or first_token
            if normalized_first in PROMPT_SHOW_COMMANDS:
                print(c(f"{symbol('tip')} Use `show {normalized_first}`.", Colors.YELLOW))
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
            show_banner(get_anonymity_status(state))
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
        if keyword_match == "modules":
            _print_modules_inventory(scope="all", kind="all", frameworks=[], limit=25, sync=False, as_json=False)
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
        except ValueError as exc:
            print(c(f"Invalid command usage. Type 'help' for options. ({exc})", Colors.RED))
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
    ensure_output_tree()
    parser = build_root_parser()
    argv_tokens = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(argv_tokens)
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


