"""Main runner orchestration for Silica-X v7.0."""

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
from typing import Sequence

from core.banner import show_banner
from core.anonymity import TOR_HOST, TOR_SOCKS_PORT, install_tor, probe_tor_status, start_tor
from core.about import build_about_text
from core.explain import build_explain_text
from core.cli_config import PROFILE_PRESETS, PROMPT_KEYWORDS, SURFACE_PRESETS
from core.cli_parsers import build_prompt_parser as _build_prompt_parser
from core.cli_parsers import build_root_parser as _build_root_parser
from core.colors import Colors, c
from core.correlator import correlate
from core.csv_export import export_to_csv
from core.domain_intel import normalize_domain, scan_domain_surface
from core.exposure import assess_domain_exposure, assess_profile_exposure, summarize_issues
from core.signal_sieve import execute_filters, list_filter_descriptors
from core.help_menu import show_flag_help, show_prompt_help
from core.html_report import generate_html
from core.metadata import PROJECT_NAME, VERSION, framework_signature
from core.narrative import build_nano_brief
from core.network import get_network_settings
from core.output import (
    append_framework_log,
    display_domain_results,
    display_results,
    list_scanned_targets,
    save_results,
)
from core.signal_forge import execute_plugins, list_plugin_descriptors
from core.platform_schema import PlatformValidationError
from core.scanner import scan_username
from core.session_state import PromptSessionState
from core.storage import ensure_output_tree, results_json_path, sanitize_target
from core.prompt_handlers import (
    apply_prompt_defaults as _apply_prompt_defaults_impl,
    handle_prompt_set_command as _handle_prompt_set_command_impl,
    handle_prompt_use_command as _handle_prompt_use_command_impl,
    keyword_to_command as _keyword_to_command_impl,
    rewrite_tokens_with_keywords as _rewrite_tokens_with_keywords_impl,
)


DEFAULT_DASHBOARD_PORT = 8000
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2


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
    print(c("\n[ Tor Diagnostics ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    for line in _tor_status_lines():
        print(c(line, Colors.CYAN))
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

        print(c("[*] Installing Tor...", Colors.YELLOW))
        ok, message = install_tor()
        if not ok:
            return False, f"Tor install failed: {message}"
        print(c(f"[+] Tor install completed: {message}", Colors.GREEN))
        status = probe_tor_status()

    if status.socks_reachable:
        return True, None

    if not prompt_user or not _can_prompt_user():
        return False, "Tor is installed but not running. Start Tor service/process, then retry."

    allow_start = _prompt_yes_no("Tor is installed but OFF. Start Tor now?", True)
    if not allow_start:
        return False, "Tor startup declined by user."

    print(c("[*] Starting Tor...", Colors.YELLOW))
    ok, message = start_tor(status.binary_path)
    if not ok:
        return False, f"Failed to start Tor: {message}"

    final_status = probe_tor_status()
    if not final_status.socks_reachable:
        return False, "Tor start command completed but SOCKS endpoint is still unreachable."
    print(c(f"[+] Tor is ON: {message}", Colors.GREEN))
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


def set_anonymity_interactive(state: RunnerState) -> bool:
    previous = RunnerState(use_tor=state.use_tor, use_proxy=state.use_proxy)

    state.use_tor = _prompt_yes_no("Use Tor routing?", state.use_tor)
    state.use_proxy = _prompt_yes_no("Use proxy routing?", state.use_proxy)

    ok, error = _validate_network_settings(state, prompt_user=True)
    if not ok:
        state.use_tor = previous.use_tor
        state.use_proxy = previous.use_proxy
        print(c(f"[!] {error}", Colors.RED))
        append_framework_log("anonymity_update_failed", error or "unknown", level="WARN")
        return False

    print(c("[+] Anonymity settings saved.", Colors.GREEN))
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
        print(c(f"[!] {error}", Colors.RED))
        append_framework_log("anonymity_update_failed", error or "unknown", level="WARN")
        return False

    state.use_tor = updated.use_tor
    state.use_proxy = updated.use_proxy
    print(c("[+] Anonymity settings saved.", Colors.GREEN))
    append_framework_log("anonymity_update", get_anonymity_status(state))
    return True


def _keyword_to_command(value: str) -> str | None:
    return _keyword_to_command_impl(value)


def _print_keyword_inventory() -> None:
    print(c("\n[ Prompt Keywords ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    for command, keywords in PROMPT_KEYWORDS.items():
        print(c(f"{command}: {', '.join(sorted(keywords))}", Colors.CYAN))
    print()


def _print_plugin_inventory(scope: str | None = None) -> None:
    resolved_scope = None if scope in (None, "", "all") else scope
    plugins = list_plugin_descriptors(scope=resolved_scope)
    title_suffix = "all scopes" if resolved_scope is None else f"scope={resolved_scope}"
    print(c(f"\n[ Plugins ] ({title_suffix})", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    if not plugins:
        print(c("No plugins discovered.", Colors.YELLOW))
        print()
        return

    for plugin in plugins:
        scopes_text = ", ".join(plugin.get("scopes", []))
        aliases = plugin.get("aliases", [])
        alias_text = ", ".join(aliases) if aliases else "-"
        print(c(f"{plugin.get('id')} - {plugin.get('title')}", Colors.CYAN))
        print(c(f"  scopes: {scopes_text}", Colors.GREY))
        print(c(f"  aliases: {alias_text}", Colors.GREY))
        print(c(f"  desc: {plugin.get('description')}", Colors.GREY))
    print()


def _print_filter_inventory(scope: str | None = None) -> None:
    resolved_scope = None if scope in (None, "", "all") else scope
    filters = list_filter_descriptors(scope=resolved_scope)
    title_suffix = "all scopes" if resolved_scope is None else f"scope={resolved_scope}"
    print(c(f"\n[ Filters ] ({title_suffix})", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    if not filters:
        print(c("No filters discovered.", Colors.YELLOW))
        print()
        return

    for row in filters:
        scopes_text = ", ".join(row.get("scopes", []))
        aliases = row.get("aliases", [])
        alias_text = ", ".join(aliases) if aliases else "-"
        print(c(f"{row.get('id')} - {row.get('title')}", Colors.CYAN))
        print(c(f"  scopes: {scopes_text}", Colors.GREY))
        print(c(f"  aliases: {alias_text}", Colors.GREY))
        print(c(f"  desc: {row.get('description')}", Colors.GREY))
    print()


def _print_scan_history(limit: int = 25) -> None:
    rows = list_scanned_targets(limit=limit)
    print(c("\n[ Scan History ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    if not rows:
        print(c("No HTML reports found under output/html.", Colors.YELLOW))
        print()
        return

    for index, row in enumerate(rows, start=1):
        print(c(f"{index}. {row['target']}", Colors.CYAN))
        print(c(f"  updated: {row['modified_at']}", Colors.GREY))
        print(c(f"  file: {row['path']}", Colors.GREY))
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
            rows = ""
            color_map = {
                "FOUND": "#1db954",
                "NOT FOUND": "#8a8f98",
                "ERROR": "#ff6b6b",
                "BLOCKED": "#f39c12",
                "INVALID_USERNAME": "#f1c40f",
            }
            for item in results:
                status = item.get("status", "UNKNOWN")
                color = color_map.get(status, "#8a8f98")
                rows += (
                    "<tr>"
                    f"<td>{html.escape(item.get('platform', 'Unknown'))}</td>"
                    f"<td style='color:{color};font-weight:bold;'>{html.escape(status)}</td>"
                    f"<td>{item.get('confidence', 0)}%</td>"
                    f"<td><a href='{html.escape(item.get('url', ''))}' target='_blank' rel='noreferrer'>"
                    f"{html.escape(item.get('url', ''))}</a></td>"
                    f"<td>{html.escape(item.get('context', '') or '')}</td>"
                    "</tr>"
                )
            if not rows:
                rows = "<tr><td colspan='5'>No profile result rows</td></tr>"

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
              <title>{html.escape(PROJECT_NAME)} Live - {html.escape(safe_target)}</title>
              <style>
                body {{ font-family: Segoe UI, sans-serif; background:#0b1118; color:#e8edf2; padding:20px; }}
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
                <p>{html.escape(safe_target)}</p>
                <p class="muted">Auto-refresh this page manually to read newly written results.</p>
              </div>
              <div class="panel">
                <h3>Profile Signals</h3>
                <table>
                  <tr><th>Platform</th><th>Status</th><th>Confidence</th><th>Profile Link</th><th>Context</th></tr>
                  {rows}
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
        print(c(f"[+] Dashboard live at http://localhost:{port}/", Colors.GREEN))
        if open_browser:
            try:
                webbrowser.open(f"http://localhost:{port}/")
            except Exception as exc:  # pragma: no cover - environment-dependent
                print(c(f"[!] Failed to open browser: {exc}", Colors.YELLOW))
        with HTTPServer(server_address, Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print(c("\n[!] Live dashboard stopped.", Colors.YELLOW))

    if background:
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
    else:
        run_server()


def _resolve_profile_runtime(args: argparse.Namespace) -> tuple[int, int]:
    preset = PROFILE_PRESETS[args.preset]
    timeout_seconds = args.timeout if args.timeout is not None else preset["timeout"]
    max_concurrency = (
        args.max_concurrency
        if args.max_concurrency is not None
        else preset["max_concurrency"]
    )
    return timeout_seconds, max_concurrency


def _resolve_surface_runtime(args: argparse.Namespace) -> tuple[int, int]:
    preset = SURFACE_PRESETS[args.preset]
    timeout_seconds = args.timeout if args.timeout is not None else preset["timeout"]
    max_subdomains = (
        args.max_subdomains
        if args.max_subdomains is not None
        else preset["max_subdomains"]
    )
    return timeout_seconds, max_subdomains


async def run_profile_scan(
    username: str,
    state: RunnerState,
    timeout_seconds: int,
    max_concurrency: int,
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
        print(c(f"[!] {error}", Colors.RED))
        append_framework_log("profile_scan_failed", f"target={username} reason={error}", level="WARN")
        return EXIT_FAILURE, None

    try:
        proxy_url = get_network_settings(state.use_proxy, state.use_tor)
        if proxy_url:
            print(c("[+] Network anonymization ENABLED", Colors.GREEN))
    except RuntimeError as exc:
        print(c(f"[!] {exc}", Colors.RED))
        append_framework_log("profile_scan_failed", f"target={username} reason={exc}", level="WARN")
        return EXIT_FAILURE, None

    print(c(f"\nProfile scan target: {username}\n", Colors.CYAN))
    try:
        results = await scan_username(
            username=username,
            proxy_url=proxy_url,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
        )
    except PlatformValidationError as exc:
        print(c(f"[!] Platform manifest validation failed: {exc}", Colors.RED))
        append_framework_log("profile_scan_failed", f"target={username} reason={exc}", level="WARN")
        return EXIT_FAILURE, None
    except Exception as exc:
        print(c(f"[!] Scan failed: {exc}", Colors.RED))
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
    plugin_results, plugin_errors = execute_plugins(
        scope="profile",
        requested_plugins=plugin_names,
        include_all=include_all_plugins,
        context={
            "target": username,
            "mode": "profile",
            "results": results,
            "correlation": correlation,
            "issues": issues,
            "issue_summary": issue_summary,
        },
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
        },
    )
    display_results(
        results,
        correlation,
        issues=issues,
        issue_summary=issue_summary,
        narrative=narrative,
        plugin_results=plugin_results,
        plugin_errors=plugin_errors,
        filter_results=filter_results,
        filter_errors=filter_errors,
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
        )
        if write_html:
            print(c(f"HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("profile_html_failed", f"target={username} reason={exc}", level="WARN")
        print(c(f"[!] HTML report generation failed: {exc}", Colors.YELLOW))

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
    }


async def run_surface_scan(
    domain: str,
    state: RunnerState,
    *,
    timeout_seconds: int,
    max_subdomains: int,
    include_ct: bool,
    include_rdap: bool,
    write_html: bool = False,
    plugin_names: list[str] | None = None,
    include_all_plugins: bool = False,
    filter_names: list[str] | None = None,
    include_all_filters: bool = False,
) -> tuple[int, dict | None]:
    normalized_domain = normalize_domain(domain)
    if not normalized_domain:
        print(c("[!] Invalid domain.", Colors.RED))
        return EXIT_USAGE, None

    append_framework_log("surface_scan_start", f"target={normalized_domain}")
    ok, error = _validate_network_settings(state, prompt_user=False)
    if not ok:
        print(c(f"[!] {error}", Colors.RED))
        append_framework_log("surface_scan_failed", f"target={normalized_domain} reason={error}", level="WARN")
        return EXIT_FAILURE, None

    try:
        proxy_url = get_network_settings(state.use_proxy, state.use_tor)
        if proxy_url:
            print(c("[+] Network anonymization ENABLED", Colors.GREEN))
    except RuntimeError as exc:
        print(c(f"[!] {exc}", Colors.RED))
        append_framework_log("surface_scan_failed", f"target={normalized_domain} reason={exc}", level="WARN")
        return EXIT_FAILURE, None

    print(c(f"\nDomain surface target: {normalized_domain}\n", Colors.CYAN))
    try:
        domain_result = await scan_domain_surface(
            domain=normalized_domain,
            timeout_seconds=timeout_seconds,
            include_ct=include_ct,
            include_rdap=include_rdap,
            max_subdomains=max_subdomains,
        )
    except Exception as exc:
        print(c(f"[!] Domain scan failed: {exc}", Colors.RED))
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
    plugin_results, plugin_errors = execute_plugins(
        scope="surface",
        requested_plugins=plugin_names,
        include_all=include_all_plugins,
        context={
            "target": normalized_domain,
            "mode": "surface",
            "results": [],
            "correlation": {},
            "domain_result": domain_result,
            "issues": issues,
            "issue_summary": issue_summary,
        },
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
        )
        if write_html:
            print(c(f"HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("surface_html_failed", f"target={normalized_domain} reason={exc}", level="WARN")
        print(c(f"[!] HTML report generation failed: {exc}", Colors.YELLOW))

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


def _print_prompt_config(session: PromptSessionState, state: RunnerState) -> None:
    print(c("\n[ Prompt Configuration ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    print(c(f"prompt: {session.module_prompt()}", Colors.CYAN))
    print(c(f"module: {session.module}", Colors.CYAN))
    print(c(f"plugins: {session.plugins_label()}", Colors.CYAN))
    print(c(f"filters: {session.filters_label()}", Colors.CYAN))
    print(c(f"profile preset: {session.profile_preset}", Colors.CYAN))
    print(c(f"surface preset: {session.surface_preset}", Colors.CYAN))
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
    print()


def _apply_prompt_defaults(args: argparse.Namespace, session: PromptSessionState) -> argparse.Namespace:
    return _apply_prompt_defaults_impl(args, session)


def _handle_prompt_set_command(command_text: str, session: PromptSessionState) -> bool:
    return _handle_prompt_set_command_impl(command_text, session)


def _handle_prompt_use_command(command_text: str, session: PromptSessionState) -> bool:
    return _handle_prompt_use_command_impl(command_text, session)


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
        print(c("[!] --live supports a single username at a time.", Colors.RED))
        return EXIT_USAGE

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"[!] {error}", Colors.RED))
        return EXIT_FAILURE

    timeout_seconds, max_concurrency = _resolve_profile_runtime(args)
    failures = 0
    for username in args.usernames:
        clean_username = username.strip()
        if not _validate_username(clean_username):
            print(c(f"[!] Invalid username: '{username}'", Colors.RED))
            failures += 1
            continue
        status, _ = await run_profile_scan(
            username=clean_username,
            state=effective_state,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            write_csv=args.csv,
            write_html=args.html,
            live_dashboard=args.live,
            live_port=args.live_port,
            open_browser=not args.no_browser,
            prompt_mode=prompt_mode,
            plugin_names=args.plugin,
            include_all_plugins=args.all_plugins,
            filter_names=args.filter,
            include_all_filters=args.all_filters,
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

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"[!] {error}", Colors.RED))
        return EXIT_FAILURE

    timeout_seconds, max_subdomains = _resolve_surface_runtime(args)
    include_ct = True if args.ct is None else bool(args.ct)
    include_rdap = True if args.rdap is None else bool(args.rdap)
    status, _ = await run_surface_scan(
        domain=args.domain,
        state=effective_state,
        timeout_seconds=timeout_seconds,
        max_subdomains=max_subdomains,
        include_ct=include_ct,
        include_rdap=include_rdap,
        write_html=args.html,
        plugin_names=args.plugin,
        include_all_plugins=args.all_plugins,
        filter_names=args.filter,
        include_all_filters=args.all_filters,
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

    effective_state = compute_effective_state(state, args.tor, args.proxy)
    ok, error = _validate_network_settings(effective_state, prompt_user=True)
    if not ok:
        print(c(f"[!] {error}", Colors.RED))
        return EXIT_FAILURE

    username = args.username.strip()
    if not _validate_username(username):
        print(c(f"[!] Invalid username: '{args.username}'", Colors.RED))
        return EXIT_USAGE

    profile_preset = PROFILE_PRESETS[args.profile_preset]
    surface_preset = SURFACE_PRESETS[args.surface_preset]

    profile_status, profile_data = await run_profile_scan(
        username=username,
        state=effective_state,
        timeout_seconds=profile_preset["timeout"],
        max_concurrency=profile_preset["max_concurrency"],
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
    plugin_results, plugin_errors = execute_plugins(
        scope="fusion",
        requested_plugins=args.plugin,
        include_all=args.all_plugins,
        context={
            "target": combined_target,
            "mode": "fusion",
            "results": profile_data.get("results", []),
            "correlation": profile_data.get("correlation", {}),
            "domain_result": surface_data.get("domain_result"),
            "issues": combined_issues,
            "issue_summary": combined_issue_summary,
        },
    )
    filter_results, filter_errors = execute_filters(
        scope="fusion",
        requested_filters=args.filter,
        include_all=args.all_filters,
        context={
            "target": combined_target,
            "mode": "fusion",
            "results": profile_data.get("results", []),
            "correlation": profile_data.get("correlation", {}),
            "domain_result": surface_data.get("domain_result"),
            "issues": combined_issues,
            "issue_summary": combined_issue_summary,
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
    )

    report_path = ""
    try:
        report_path = generate_html(
            target=combined_target,
            results=profile_data.get("results", []),
            correlation=profile_data.get("correlation", {}),
            issues=combined_issues,
            issue_summary=combined_issue_summary,
            narrative=combined_narrative,
            domain_result=surface_data.get("domain_result"),
            mode="fusion",
            plugin_results=plugin_results,
            plugin_errors=plugin_errors,
            filter_results=filter_results,
            filter_errors=filter_errors,
        )
        if args.html:
            print(c(f"Fusion HTML report generated -> {report_path}", Colors.GREEN))
    except Exception as exc:  # pragma: no cover - defensive
        append_framework_log("fusion_html_failed", f"target={combined_target} reason={exc}", level="WARN")
        print(c(f"[!] Fusion HTML report generation failed: {exc}", Colors.YELLOW))

    print(c(f"[+] Fusion bundle saved under output/data/{combined_target}/", Colors.GREEN))
    append_framework_log("fusion_scan_done", f"target={combined_target} report={report_path or '-'}")
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
                print(c(f"[!] {error}", Colors.RED))
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


async def _handle_history_command(args: argparse.Namespace) -> int:
    _print_scan_history(limit=args.limit)
    return EXIT_SUCCESS


async def _handle_wizard_command(
    args: argparse.Namespace,
    state: RunnerState,
    prompt_mode: bool,
) -> int:
    if args.tor is not None or args.proxy is not None:
        ok = apply_anonymity_flags(state, args.tor, args.proxy, prompt_user=True)
        if not ok:
            return EXIT_FAILURE

    print(c("\n[ Guided Workflow Wizard ]", Colors.BLUE))
    run_profile = _prompt_yes_no("Run profile intelligence phase?", True)
    run_surface = _prompt_yes_no("Run domain surface phase?", True)

    profile_usernames: list[str] = []
    if run_profile:
        raw = ask("Enter usernames (comma-separated): ")
        profile_usernames = [item.strip() for item in raw.split(",") if _validate_username(item)]
        if not profile_usernames:
            print(c("[!] No valid usernames entered; profile phase skipped.", Colors.YELLOW))
            run_profile = False

    surface_domain = ""
    if run_surface:
        surface_domain = ask("Enter target domain: ").strip()
        if not normalize_domain(surface_domain):
            print(c("[!] Invalid domain; surface phase skipped.", Colors.YELLOW))
            run_surface = False

    write_html = _prompt_yes_no("Generate HTML reports?", True)
    write_csv = run_profile and _prompt_yes_no("Export profile CSV?", False)
    plugin_raw = ask("Plugins [none|all|id1,id2] [none]: ").strip().lower()
    plugin_all = plugin_raw == "all"
    plugin_names = []
    if plugin_raw and plugin_raw not in {"none", "all"}:
        plugin_names = [item.strip() for item in plugin_raw.split(",") if item.strip()]
    filter_raw = ask("Filters [none|all|id1,id2] [none]: ").strip().lower()
    filter_all = filter_raw == "all"
    filter_names = []
    if filter_raw and filter_raw not in {"none", "all"}:
        filter_names = [item.strip() for item in filter_raw.split(",") if item.strip()]

    failures = 0
    if run_profile:
        profile_args = argparse.Namespace(
            usernames=profile_usernames,
            tor=None,
            proxy=None,
            preset="balanced",
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
            preset="balanced",
            timeout=None,
            max_subdomains=None,
            ct=None,
            rdap=None,
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

    if run_profile and run_surface and _prompt_yes_no("Generate a fusion bundle too?", True):
        fusion_args = argparse.Namespace(
            username=profile_usernames[0],
            domain=surface_domain,
            tor=None,
            proxy=None,
            profile_preset="balanced",
            surface_preset="balanced",
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


async def _dispatch(args: argparse.Namespace, state: RunnerState, prompt_mode: bool) -> int:
    if args.command in {"profile", "scan", "persona", "social"}:
        return await _handle_profile_command(args, state=state, prompt_mode=prompt_mode)
    if args.command in {"surface", "domain", "asset"}:
        return await _handle_surface_command(args, state=state)
    if args.command in {"fusion", "full", "combo"}:
        return await _handle_fusion_command(args, state=state)
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
    if args.command in {"history", "targets", "scans"}:
        return await _handle_history_command(args)
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
    return EXIT_USAGE


async def run_prompt_mode(initial_state: RunnerState | None = None) -> int:
    state = initial_state or RunnerState()
    session = PromptSessionState()
    clear_screen()
    show_banner(get_anonymity_status(state))
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

        lowered = command_text.lower()
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

        try:
            tokens = shlex.split(command_text)
        except ValueError as exc:
            print(c(f"Invalid command syntax: {exc}", Colors.RED))
            continue

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
        if tokens and keyword_match in {"profile", "surface", "fusion"} and len(tokens) == 1:
            if keyword_match == "profile":
                target = ask("Username target: ")
                tokens = ["profile", target]
            elif keyword_match == "surface":
                target = ask("Domain target: ")
                tokens = ["surface", target]
            else:
                username = ask("Username target: ")
                domain = ask("Domain target: ")
                tokens = ["fusion", username, domain]
        if len(tokens) == 2 and tokens[0] == "scan":
            # Preserve 'scan <username>' behavior in prompt.
            tokens = ["profile", tokens[1]]

        try:
            args = prompt_parser.parse_args(tokens)
        except ValueError as exc:
            print(c(f"Invalid command usage. Type 'help' for options. ({exc})", Colors.RED))
            continue

        args = _apply_prompt_defaults(args, session)
        try:
            await _dispatch(args, state=state, prompt_mode=True)
        except Exception as exc:  # pragma: no cover - prompt safety guard
            append_framework_log("prompt_dispatch_error", str(exc), level="ERROR")
            print(c(f"[!] Command failed: {exc}", Colors.RED))


async def run(argv: Sequence[str] | None = None) -> int:
    ensure_output_tree()
    parser = build_root_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    rendered_argv = " ".join(str(item) for item in (argv or []))
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
                print(c(f"[!] {error}", Colors.RED))
                return EXIT_FAILURE
        status = await run_prompt_mode(initial_state=initial_state)
        append_framework_log("framework_exit", f"status={status}")
        return status

    state = RunnerState()
    status = await _dispatch(args, state=state, prompt_mode=False)
    append_framework_log("framework_exit", f"status={status}")
    return status
