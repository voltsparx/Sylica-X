"""Console, JSON, CLI-report, and log output helpers."""

from __future__ import annotations

import json
from collections import Counter
from typing import Iterable

from core.colors import Colors, c
from core.metadata import framework_signature, utc_timestamp
from core.storage import (
    cli_report_path,
    data_target_dir,
    ensure_output_tree,
    framework_log_path,
    legacy_results_json_path,
    list_targets_from_html,
    results_json_path,
    run_log_path,
    sanitize_target,
)


def _status_color(status: str) -> str:
    mapping = {
        "FOUND": Colors.GREEN,
        "NOT FOUND": Colors.GREY,
        "BLOCKED": Colors.YELLOW,
        "INVALID_USERNAME": Colors.YELLOW,
        "ERROR": Colors.RED,
    }
    return mapping.get(status, Colors.GREY)


def _print_issue_block(issues: Iterable[dict[str, str]]) -> None:
    issue_list = list(issues)
    if not issue_list:
        print(c("\n[ Exposure Findings ] none", Colors.GREEN))
        return

    print(c("\n[ Exposure Findings ]", Colors.MAGENTA))
    for idx, issue in enumerate(issue_list, start=1):
        severity = issue.get("severity", "LOW")
        severity_color = Colors.RED if severity in {"HIGH", "CRITICAL"} else Colors.YELLOW
        print(c(f"{idx}. [{severity}] {issue.get('title', 'Issue')}", severity_color))
        print(c(f"   scope: {issue.get('scope', '-')}", Colors.GREY))
        print(c(f"   evidence: {issue.get('evidence', '-')}", Colors.GREY))
        print(c(f"   recommendation: {issue.get('recommendation', '-')}", Colors.CYAN))


def _print_plugin_block(
    plugin_results: Iterable[dict] | None,
    plugin_errors: Iterable[str] | None,
) -> None:
    rows = list(plugin_results or [])
    errors = list(plugin_errors or [])
    if not rows and not errors:
        return

    print(c("\n[ Plugin Intelligence ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    for row in rows:
        severity = str(row.get("severity", "INFO")).upper()
        color = Colors.RED if severity in {"HIGH", "CRITICAL"} else Colors.YELLOW if severity == "MEDIUM" else Colors.CYAN
        print(c(f"[{severity}] {row.get('title', row.get('id', 'plugin'))}", color))
        print(c(f"  summary: {row.get('summary', '')}", Colors.GREY))
        highlights = row.get("highlights", [])
        for item in highlights[:6]:
            print(c(f"  - {item}", Colors.GREY))
    if errors:
        print(c("\nPlugin errors:", Colors.RED))
        for err in errors:
            print(c(f"- {err}", Colors.RED))


def _print_filter_block(
    filter_results: Iterable[dict] | None,
    filter_errors: Iterable[str] | None,
) -> None:
    rows = list(filter_results or [])
    errors = list(filter_errors or [])
    if not rows and not errors:
        return

    print(c("\n[ Filter Intelligence ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    for row in rows:
        severity = str(row.get("severity", "INFO")).upper()
        color = Colors.RED if severity in {"HIGH", "CRITICAL"} else Colors.YELLOW if severity == "MEDIUM" else Colors.CYAN
        print(c(f"[{severity}] {row.get('title', row.get('id', 'filter'))}", color))
        print(c(f"  summary: {row.get('summary', '')}", Colors.GREY))
        highlights = row.get("highlights", [])
        for item in highlights[:6]:
            print(c(f"  - {item}", Colors.GREY))
    if errors:
        print(c("\nFilter errors:", Colors.RED))
        for err in errors:
            print(c(f"- {err}", Colors.RED))


def display_results(
    results: list[dict],
    correlation: dict,
    *,
    issues: list[dict[str, str]] | None = None,
    issue_summary: dict | None = None,
    narrative: str | None = None,
    plugin_results: list[dict] | None = None,
    plugin_errors: list[str] | None = None,
    filter_results: list[dict] | None = None,
    filter_errors: list[str] | None = None,
) -> None:
    print(c("\n[ Scan Results ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))

    found_links: list[str] = []
    status_counter: Counter = Counter()
    for item in sorted(
        results,
        key=lambda row: (row.get("status") != "FOUND", -int(row.get("confidence", 0) or 0)),
    ):
        status = item.get("status", "UNKNOWN")
        status_counter[status] += 1
        status_color = _status_color(status)
        platform = item.get("platform", "Unknown")
        url = item.get("url", "")
        confidence = int(item.get("confidence", 0) or 0)
        print(c(f"[{status}] {platform} ({confidence}%)", status_color))
        print(c(f"  profile: {url}", Colors.CYAN))
        if status == "FOUND":
            found_links.append(url)
            contacts = item.get("contacts", {})
            if item.get("bio"):
                print(c(f"  bio: {item['bio'][:180]}", Colors.GREY))
            if item.get("links"):
                top_links = ", ".join(item["links"][:4])
                print(c(f"  extracted links: {top_links}", Colors.YELLOW))
            if contacts.get("emails"):
                print(c(f"  emails: {', '.join(contacts['emails'])}", Colors.YELLOW))
            if contacts.get("phones"):
                print(c(f"  phones: {', '.join(contacts['phones'])}", Colors.YELLOW))
            if item.get("mentions"):
                print(c(f"  mentions: {', '.join(item['mentions'][:6])}", Colors.GREY))
        if item.get("http_status") is not None:
            print(c(f"  http: {item['http_status']}", Colors.GREY))
        if item.get("response_time_ms") is not None:
            print(c(f"  rtt: {item['response_time_ms']} ms", Colors.GREY))

    print(c("\n[ Summary ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    summary_line = " ".join(f"{key.replace(' ', '_')}={value}" for key, value in status_counter.items())
    print(c(summary_line or "No results", Colors.CYAN))
    print(c(f"FOUND_PROFILES={len(found_links)}", Colors.GREEN))

    if found_links:
        print(c("\n[ Confirmed Profile Links ]", Colors.GREEN))
        for link in found_links:
            print(c(f"- {link}", Colors.GREEN))

    shared_links = correlation.get("shared_links", {})
    shared_emails = correlation.get("shared_emails", {})
    shared_phones = correlation.get("shared_phones", {})
    overlap_score = correlation.get("identity_overlap_score", 0)
    print(c("\n[ Correlation ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    print(c(f"Identity overlap score: {overlap_score}/100", Colors.CYAN))
    print(c(f"Shared links: {len(shared_links)}", Colors.GREY))
    print(c(f"Shared emails: {len(shared_emails)}", Colors.GREY))
    print(c(f"Shared phones: {len(shared_phones)}", Colors.GREY))
    cluster_map = correlation.get("confidence_cluster_map", {})
    print(c(f"High-confidence cluster: {', '.join(cluster_map.get('high', [])) or 'None'}", Colors.GREY))

    if issues is not None:
        _print_issue_block(issues)
    if issue_summary:
        print(c(f"\nRisk score: {issue_summary.get('risk_score', 0)}", Colors.MAGENTA))
        print(c(f"Severity breakdown: {issue_summary.get('severity_breakdown', {})}", Colors.MAGENTA))
    _print_plugin_block(plugin_results, plugin_errors)
    _print_filter_block(filter_results, filter_errors)
    if narrative:
        print(c("\n[ Nano AI Brief ]", Colors.CYAN))
        print(c(narrative, Colors.CYAN))

    print(c(f"\n{framework_signature()}", Colors.GREY))


def display_domain_results(
    domain_result: dict,
    *,
    issues: list[dict[str, str]] | None = None,
    issue_summary: dict | None = None,
    narrative: str | None = None,
    plugin_results: list[dict] | None = None,
    plugin_errors: list[str] | None = None,
    filter_results: list[dict] | None = None,
    filter_errors: list[str] | None = None,
) -> None:
    target = domain_result.get("target", "unknown")
    print(c("\n[ Domain Surface Scan ]", Colors.BLUE))
    print(c("------------------------------------", Colors.BLUE))
    print(c(f"Target: {target}", Colors.CYAN))
    addresses = domain_result.get("resolved_addresses", [])
    print(c(f"Resolved addresses ({len(addresses)}): {', '.join(addresses) or 'none'}", Colors.GREY))

    https_data = domain_result.get("https", {})
    http_data = domain_result.get("http", {})
    print(c(f"HTTPS status: {https_data.get('status')} final={https_data.get('final_url')}", Colors.GREY))
    print(c(f"HTTP status: {http_data.get('status')} final={http_data.get('final_url')}", Colors.GREY))
    print(c(f"HTTP->HTTPS redirect: {http_data.get('redirects_to_https')}", Colors.GREY))

    subdomains = domain_result.get("subdomains", [])
    if subdomains:
        print(c(f"Subdomains ({len(subdomains)}):", Colors.YELLOW))
        for name in subdomains[:25]:
            print(c(f"- {name}", Colors.YELLOW))
        if len(subdomains) > 25:
            print(c(f"... and {len(subdomains) - 25} more", Colors.YELLOW))
    else:
        print(c("Subdomains: none", Colors.GREY))

    print(c(f"robots.txt present: {domain_result.get('robots_txt_present')}", Colors.GREY))
    print(c(f"security.txt present: {domain_result.get('security_txt_present')}", Colors.GREY))
    if domain_result.get("scan_notes"):
        print(c("Scan notes:", Colors.YELLOW))
        for note in domain_result["scan_notes"]:
            print(c(f"- {note}", Colors.YELLOW))

    if issues is not None:
        _print_issue_block(issues)
    if issue_summary:
        print(c(f"\nRisk score: {issue_summary.get('risk_score', 0)}", Colors.MAGENTA))
        print(c(f"Severity breakdown: {issue_summary.get('severity_breakdown', {})}", Colors.MAGENTA))
    _print_plugin_block(plugin_results, plugin_errors)
    _print_filter_block(filter_results, filter_errors)
    if narrative:
        print(c("\n[ Nano AI Brief ]", Colors.CYAN))
        print(c(narrative, Colors.CYAN))

    print(c(f"\n{framework_signature()}", Colors.GREY))


def _render_cli_report(payload: dict) -> str:
    metadata = payload.get("metadata", {}) or {}
    lines: list[str] = []
    lines.append(f"Framework: {metadata.get('framework', '-')}")
    lines.append(f"Generated UTC: {metadata.get('generated_at_utc', '-')}")
    lines.append(f"Mode: {metadata.get('mode', '-')}")
    lines.append(f"Target: {payload.get('target', '-')}")
    lines.append("")

    results = payload.get("results", []) or []
    if results:
        lines.append("[Profile Results]")
        for row in sorted(results, key=lambda item: (item.get("status") != "FOUND", item.get("platform", ""))):
            lines.append(
                f"- {row.get('platform', 'Unknown')}: {row.get('status', 'UNKNOWN')} "
                f"({int(row.get('confidence', 0) or 0)}%) -> {row.get('url', '')}"
            )
        lines.append("")

    domain_result = payload.get("domain_result")
    if domain_result:
        lines.append("[Domain Surface]")
        lines.append(f"- target: {domain_result.get('target', '-')}")
        lines.append(
            f"- resolved_addresses: {', '.join(domain_result.get('resolved_addresses', []) or []) or 'none'}"
        )
        lines.append(f"- subdomains: {len(domain_result.get('subdomains', []) or [])}")
        lines.append("")

    correlation = payload.get("correlation", {}) or {}
    if correlation:
        lines.append("[Correlation]")
        lines.append(f"- identity_overlap_score: {correlation.get('identity_overlap_score', 0)}")
        lines.append(f"- shared_links: {len(correlation.get('shared_links', {}) or {})}")
        lines.append(f"- shared_emails: {len(correlation.get('shared_emails', {}) or {})}")
        lines.append(f"- shared_phones: {len(correlation.get('shared_phones', {}) or {})}")
        lines.append("")

    issues = payload.get("issues", []) or []
    lines.append("[Exposure Findings]")
    if not issues:
        lines.append("- none")
    else:
        for issue in issues:
            lines.append(
                f"- [{issue.get('severity', 'LOW')}] {issue.get('title', 'Issue')} "
                f"(scope={issue.get('scope', '-')}) evidence={issue.get('evidence', '-')}"
            )
    lines.append("")

    plugin_rows = payload.get("plugins", []) or []
    plugin_errors = payload.get("plugin_errors", []) or []
    lines.append("[Plugin Intelligence]")
    if not plugin_rows and not plugin_errors:
        lines.append("- none")
    else:
        for row in plugin_rows:
            lines.append(
                f"- [{str(row.get('severity', 'INFO')).upper()}] "
                f"{row.get('title', row.get('id', 'plugin'))}: {row.get('summary', '')}"
            )
        for err in plugin_errors:
            lines.append(f"- [ERROR] {err}")
    lines.append("")

    filter_rows = payload.get("filters", []) or []
    filter_errors = payload.get("filter_errors", []) or []
    lines.append("[Filter Intelligence]")
    if not filter_rows and not filter_errors:
        lines.append("- none")
    else:
        for row in filter_rows:
            lines.append(
                f"- [{str(row.get('severity', 'INFO')).upper()}] "
                f"{row.get('title', row.get('id', 'filter'))}: {row.get('summary', '')}"
            )
        for err in filter_errors:
            lines.append(f"- [ERROR] {err}")
    lines.append("")

    narrative = str(payload.get("narrative") or "").strip()
    lines.append("[Nano AI Brief]")
    lines.append(f"- {narrative or 'No narrative generated.'}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def append_framework_log(event: str, details: str = "", *, level: str = "INFO") -> str:
    ensure_output_tree()
    path = framework_log_path()
    line = f"[{utc_timestamp()}] [{level.upper()}] {event}"
    if details:
        line = f"{line} | {details}"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return str(path)


def list_scanned_targets(limit: int = 50) -> list[dict[str, str]]:
    rows = list_targets_from_html(limit=limit)
    return [{"target": row.target, "path": row.path, "modified_at": row.modified_at} for row in rows]


def save_results(
    target: str,
    results: list[dict] | None = None,
    correlation: dict | None = None,
    *,
    issues: list[dict[str, str]] | None = None,
    issue_summary: dict | None = None,
    narrative: str | None = None,
    domain_result: dict | None = None,
    mode: str = "profile",
    plugin_results: list[dict] | None = None,
    plugin_errors: list[str] | None = None,
    filter_results: list[dict] | None = None,
    filter_errors: list[str] | None = None,
) -> str:
    ensure_output_tree()
    target_key = sanitize_target(target)
    data_target_dir(target_key).mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": {
            "generated_at_utc": utc_timestamp(),
            "mode": mode,
            "framework": framework_signature(),
        },
        "target": target_key,
        "results": results or [],
        "domain_result": domain_result,
        "correlation": correlation or {},
        "issues": issues or [],
        "issue_summary": issue_summary or {},
        "plugins": plugin_results or [],
        "plugin_errors": plugin_errors or [],
        "filters": filter_results or [],
        "filter_errors": filter_errors or [],
        "narrative": narrative,
    }

    results_count = len(payload["results"]) if isinstance(payload["results"], list) else 0
    issues_count = len(payload["issues"]) if isinstance(payload["issues"], list) else 0
    plugins_count = len(payload["plugins"]) if isinstance(payload["plugins"], list) else 0
    filters_count = len(payload["filters"]) if isinstance(payload["filters"], list) else 0

    json_path = results_json_path(target_key)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)

    # Compatibility mirror for legacy paths used by older integrations.
    legacy_path = legacy_results_json_path(target_key)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    with legacy_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)

    cli_path = cli_report_path(target_key)
    cli_path.write_text(_render_cli_report(payload), encoding="utf-8")

    run_log = run_log_path(target_key)
    run_log.write_text(
        (
            f"timestamp={utc_timestamp()}\n"
            f"target={target_key}\n"
            f"mode={mode}\n"
            f"results={results_count}\n"
            f"issues={issues_count}\n"
            f"plugins={plugins_count}\n"
            f"filters={filters_count}\n"
            f"framework={framework_signature()}\n"
        ),
        encoding="utf-8",
    )
    append_framework_log(
        "scan_saved",
        f"target={target_key} mode={mode} json={json_path} cli={cli_path} log={run_log}",
    )

    print(c(f"\nResults JSON saved to {json_path}", Colors.GREEN))
    print(c(f"CLI report saved to {cli_path}", Colors.GREEN))
    print(c(f"Run log saved to {run_log}", Colors.GREEN))
    return str(json_path)
