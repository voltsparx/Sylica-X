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

"""Console, JSON, CLI-report, and log output helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import Any, Iterable

from core.foundation.colors import Colors, c
from core.foundation.metadata import framework_signature, utc_timestamp
from core.interface.symbols import symbol
from core.analyze.profile_summary import (
    error_profile_rows,
    focused_profile_rows,
    found_profile_rows,
    summarize_target_intel,
)
from core.artifacts.storage import (
    cli_report_path,
    data_target_dir,
    ensure_output_tree,
    framework_log_path,
    legacy_results_json_path,
    list_targets,
    results_json_path,
    run_log_path,
    sanitize_target,
)
from core.foundation.output_config import OutputConfigError, get_output_settings


def _safe_dict_rows(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _severity_breakdown(rows: list[dict]) -> dict[str, int]:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for row in rows:
        severity = str(row.get("severity", "INFO")).strip().upper()
        if severity not in counts:
            severity = "INFO"
        counts[severity] += 1
    return counts


def _compact_data_snapshot(data: object, *, max_items: int = 5) -> str:
    if not isinstance(data, dict) or not data:
        return "-"
    pairs: list[str] = []
    for key in sorted(data.keys(), key=str):
        value = data.get(key)
        if isinstance(value, (str, int, float, bool)):
            pairs.append(f"{key}={value}")
        elif isinstance(value, list):
            pairs.append(f"{key}[{len(value)}]")
        elif isinstance(value, dict):
            pairs.append(f"{key}{{{len(value)}}}")
        elif value is None:
            pairs.append(f"{key}=null")
        else:
            pairs.append(f"{key}=...")
        if len(pairs) >= max_items:
            break
    return ", ".join(pairs) if pairs else "-"


def _crypto_profile_summary(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    profile = data.get("crypto_profile")
    if not isinstance(profile, dict):
        return None
    kind = str(profile.get("crypto_kind", data.get("crypto_kind", "crypto"))).strip().lower() or "crypto"
    operation = str(profile.get("operation", data.get("operation", "encrypt"))).strip().lower() or "encrypt"
    output_encoding = str(profile.get("output_encoding", "base64")).strip().lower() or "base64"
    try:
        max_items = int(profile.get("max_items", 0) or 0)
    except (TypeError, ValueError):
        max_items = 0
    strict_mode = bool(profile.get("strict_mode", False))
    source_fields = profile.get("source_fields")
    if isinstance(source_fields, list):
        sources_text = ",".join(str(item) for item in source_fields if str(item).strip())
    else:
        sources_text = "-"
    return (
        f"{kind} cfg: op={operation} encoding={output_encoding} max_items={max_items} "
        f"strict={strict_mode} sources={sources_text}"
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


def _preview(values: list[str], limit: int = 8) -> str:
    if not values:
        return "none"
    if len(values) <= limit:
        return ", ".join(values)
    return f"{', '.join(values[:limit])} ... (+{len(values) - limit} more)"


def _section(title: str, color: str = Colors.BLUE) -> None:
    print(c(f"\n{symbol('major')} {title}", color))
    print(c("-" * 36, color))


def _top_scored_items(items: list[dict], *, limit: int = 8) -> list[dict]:
    rows = [item for item in items if isinstance(item, dict)]
    rows.sort(
        key=lambda item: (
            -float(item.get("score", item.get("confidence_score", 0.0)) or 0.0),
            -int(item.get("supporting_entities", 0) or 0),
            str(item.get("value", "")).lower(),
        )
    )
    return rows[:limit]


def _print_issue_block(issues: Iterable[dict[str, str]]) -> None:
    issue_list = list(issues)
    if not issue_list:
        print(c(f"\n{symbol('ok')} Exposure Findings: none", Colors.GREEN))
        return

    _section("Exposure Findings", Colors.MAGENTA)
    for idx, issue in enumerate(issue_list, start=1):
        severity = issue.get("severity", "LOW")
        severity_color = Colors.RED if severity in {"HIGH", "CRITICAL"} else Colors.YELLOW
        marker = symbol("error") if severity in {"HIGH", "CRITICAL"} else symbol("warn")
        print(c(f"{marker} #{idx} [{severity}] {issue.get('title', 'Issue')}", severity_color))
        print(c(f"  {symbol('bullet')} scope: {issue.get('scope', '-')}", Colors.GREY))
        print(c(f"  {symbol('bullet')} evidence: {issue.get('evidence', '-')}", Colors.GREY))
        print(c(f"  {symbol('tip')} recommendation: {issue.get('recommendation', '-')}", Colors.CYAN))


def _print_plugin_block(
    plugin_results: Iterable[dict] | None,
    plugin_errors: Iterable[str] | None,
) -> None:
    rows = _safe_dict_rows(list(plugin_results or []))
    errors = list(plugin_errors or [])
    if not rows and not errors:
        return

    _section("Plugin Intelligence", Colors.BLUE)
    for row in rows:
        severity = str(row.get("severity", "INFO")).upper()
        color = Colors.RED if severity in {"HIGH", "CRITICAL"} else Colors.YELLOW if severity == "MEDIUM" else Colors.CYAN
        marker = symbol("error") if severity in {"HIGH", "CRITICAL"} else symbol("warn") if severity == "MEDIUM" else symbol("feature")
        print(c(f"{marker} [{severity}] {row.get('title', row.get('id', 'plugin'))}", color))
        print(c(f"  {symbol('bullet')} summary: {row.get('summary', '')}", Colors.GREY))
        print(c(f"  {symbol('bullet')} data: {_compact_data_snapshot(row.get('data', {}))}", Colors.GREY))
        crypto_line = _crypto_profile_summary(row.get("data", {}))
        if crypto_line:
            print(c(f"  {symbol('tip')} {crypto_line}", Colors.MAGENTA))
        highlights = row.get("highlights", [])
        for item in highlights[:6]:
            print(c(f"  {symbol('bullet')} {item}", Colors.GREY))
    if errors:
        print(c(f"\n{symbol('warn')} Plugin errors:", Colors.RED))
        for err in errors:
            print(c(f"{symbol('error')} {err}", Colors.RED))


def _print_filter_block(
    filter_results: Iterable[dict] | None,
    filter_errors: Iterable[str] | None,
) -> None:
    rows = _safe_dict_rows(list(filter_results or []))
    errors = list(filter_errors or [])
    if not rows and not errors:
        return

    _section("Filter Intelligence", Colors.BLUE)
    for row in rows:
        severity = str(row.get("severity", "INFO")).upper()
        color = Colors.RED if severity in {"HIGH", "CRITICAL"} else Colors.YELLOW if severity == "MEDIUM" else Colors.CYAN
        marker = symbol("error") if severity in {"HIGH", "CRITICAL"} else symbol("warn") if severity == "MEDIUM" else symbol("feature")
        print(c(f"{marker} [{severity}] {row.get('title', row.get('id', 'filter'))}", color))
        print(c(f"  {symbol('bullet')} summary: {row.get('summary', '')}", Colors.GREY))
        print(c(f"  {symbol('bullet')} data: {_compact_data_snapshot(row.get('data', {}))}", Colors.GREY))
        highlights = row.get("highlights", [])
        for item in highlights[:6]:
            print(c(f"  {symbol('bullet')} {item}", Colors.GREY))
    if errors:
        print(c(f"\n{symbol('warn')} Filter errors:", Colors.RED))
        for err in errors:
            print(c(f"{symbol('error')} {err}", Colors.RED))


def _print_intelligence_block(intelligence_bundle: dict | None) -> None:
    bundle = intelligence_bundle or {}
    if not bundle:
        return

    metadata = bundle.get("metadata", {}) or {}
    risk_summary = bundle.get("risk_summary", {}) or {}
    confidence_distribution = bundle.get("confidence_distribution", {}) or {}
    facets = bundle.get("entity_facets", {}) or {}
    scored_contacts = list(facets.get("scored_contacts", []) or [])
    scored_entities = list(bundle.get("scored_entities", []) or [])
    guidance = bundle.get("execution_guidance", {}) or {}
    correlation_summary = bundle.get("correlation_summary", {}) or {}

    _section("Intelligence Scoring", Colors.BLUE)
    print(
        c(
            "Entities: "
            f"{metadata.get('entity_count', 0)} "
            f"| Evidence: {metadata.get('evidence_count', 0)} "
            f"| Links: {correlation_summary.get('link_count', 0)}",
            Colors.CYAN,
        )
    )
    print(
        c(
            "Confidence distribution: "
            f"high={confidence_distribution.get('high', 0)} "
            f"medium={confidence_distribution.get('medium', 0)} "
            f"low={confidence_distribution.get('low', 0)}",
            Colors.CYAN,
        )
    )
    print(c(f"Risk summary: {risk_summary}", Colors.MAGENTA))
    print(c(f"Emails: {_preview(list(facets.get('emails', []) or []), limit=10)}", Colors.GREY))
    print(c(f"Phones: {_preview(list(facets.get('phones', []) or []), limit=10)}", Colors.GREY))
    print(c(f"Names: {_preview(list(facets.get('names', []) or []), limit=10)}", Colors.GREY))
    footprint_map = bundle.get("footprint_map", {}) if isinstance(bundle.get("footprint_map"), dict) else {}
    if footprint_map:
        summary = footprint_map.get("summary", {}) if isinstance(footprint_map.get("summary"), dict) else {}
        watchlist = footprint_map.get("watchlist", {}) if isinstance(footprint_map.get("watchlist"), dict) else {}
        indicators = footprint_map.get("threat_indicators", []) if isinstance(footprint_map.get("threat_indicators"), list) else []
        print(c(f"\n{symbol('major')} Digital Footprint Map", Colors.MAGENTA))
        print(
            c(
                "Profiles: "
                f"{summary.get('profile_count', 0)} "
                f"| Linked domains: {summary.get('external_domain_count', 0)} "
                f"| Surface assets: {summary.get('surface_asset_count', 0)} "
                f"| Risk signals: {summary.get('risk_signal_count', 0)}",
                Colors.MAGENTA,
            )
        )
        print(c(f"Observed lanes: {footprint_map.get('source_lanes', {})}", Colors.GREY))
        print(c(f"Watch handles: {_preview(list(watchlist.get('handles', []) or []), limit=10)}", Colors.GREY))
        print(c(f"Watch domains: {_preview(list(watchlist.get('domains', []) or []), limit=10)}", Colors.GREY))
        for row in indicators[:6]:
            if not isinstance(row, dict):
                continue
            print(
                c(
                    f"{symbol('bullet')} [{row.get('severity', 'INFO')}] {row.get('title', 'Signal')}"
                    f" -> {row.get('evidence', '-')}",
                    Colors.YELLOW,
                )
            )

    top_contacts = _top_scored_items(scored_contacts, limit=8)
    if top_contacts:
        print(c(f"\n{symbol('major')} Top contact/name signals", Colors.YELLOW))
        for item in top_contacts:
            print(
                c(
                    f"{symbol('bullet')} [{str(item.get('kind', '?')).upper()}] {item.get('value', '-')}"
                    f" score={item.get('score_percent', 0)}%"
                    f" support={item.get('supporting_entities', 0)}"
                    f" risk={item.get('risk_level', 'LOW')}",
                    Colors.YELLOW,
                )
            )

    top_entities = _top_scored_items(scored_entities, limit=10)
    if top_entities:
        print(c(f"\n{symbol('major')} Top scored entities", Colors.CYAN))
        for row in top_entities:
            print(
                c(
                    f"{symbol('bullet')} {row.get('entity_type', '-')} {row.get('value', '-')}"
                    f" [{row.get('source', '-')}]"
                    f" confidence={row.get('confidence_percent', 0)}%"
                    f" risk={row.get('risk_level', '-')}"
                    f" relations={row.get('relationship_count', 0)}",
                    Colors.CYAN,
                )
            )

    actions = guidance.get("actions", []) if isinstance(guidance.get("actions"), list) else []
    if actions:
        print(c(f"\n{symbol('major')} Explainable guidance", Colors.GREEN))
        for action in actions[:6]:
            if not isinstance(action, dict):
                continue
            print(c(f"{symbol('action')} [{action.get('priority', 'P3')}] {action.get('title', 'Action')}", Colors.GREEN))
            print(c(f"  {symbol('bullet')} why: {action.get('rationale', '-')}", Colors.GREY))
            print(c(f"  {symbol('tip')} hint: {action.get('command_hint', '-')}", Colors.GREY))


def _build_payload_summary(payload: dict[str, Any]) -> dict[str, Any]:
    results = _safe_dict_rows(payload.get("results"))
    found = [row for row in results if str(row.get("status", "")).upper() == "FOUND"]
    errors = [row for row in results if str(row.get("status", "")).upper() in {"ERROR", "BLOCKED"}]
    issues = _safe_dict_rows(payload.get("issues"))
    plugins = _safe_dict_rows(payload.get("plugins"))
    filters = _safe_dict_rows(payload.get("filters"))

    summary: dict[str, Any] = {
        "result_count": len(results),
        "found_count": len(found),
        "error_or_blocked_count": len(errors),
        "issue_count": len(issues),
        "plugin_count": len(plugins),
        "filter_count": len(filters),
        "plugin_error_count": len(payload.get("plugin_errors") or []),
        "filter_error_count": len(payload.get("filter_errors") or []),
        "issue_severity": _severity_breakdown(issues),
        "plugin_severity": _severity_breakdown(plugins),
        "filter_severity": _severity_breakdown(filters),
    }
    return summary


def _print_extension_summary(summary: dict[str, Any]) -> None:
    _section("Extension Summary", Colors.BLUE)
    issue_severity = summary.get("issue_severity", {}) if isinstance(summary.get("issue_severity"), dict) else {}
    plugin_severity = summary.get("plugin_severity", {}) if isinstance(summary.get("plugin_severity"), dict) else {}
    filter_severity = summary.get("filter_severity", {}) if isinstance(summary.get("filter_severity"), dict) else {}
    print(
        c(
            f"{symbol('bullet')} results={summary.get('result_count', 0)} "
            f"found={summary.get('found_count', 0)} "
            f"errors={summary.get('error_or_blocked_count', 0)}",
            Colors.CYAN,
        )
    )
    print(
        c(
            f"{symbol('bullet')} issues={summary.get('issue_count', 0)} "
            f"plugins={summary.get('plugin_count', 0)} "
            f"filters={summary.get('filter_count', 0)}",
            Colors.CYAN,
        )
    )
    print(
        c(
            f"{symbol('warn')} issue_severity={issue_severity} "
            f"plugin_severity={plugin_severity} "
            f"filter_severity={filter_severity}",
            Colors.GREY,
        )
    )


def display_results(
    results: list[dict],
    correlation: dict,
    *,
    target: str | None = None,
    issues: list[dict[str, str]] | None = None,
    issue_summary: dict | None = None,
    narrative: str | None = None,
    plugin_results: list[dict] | None = None,
    plugin_errors: list[str] | None = None,
    filter_results: list[dict] | None = None,
    filter_errors: list[str] | None = None,
    intelligence_bundle: dict | None = None,
) -> None:
    _section("Scan Results", Colors.BLUE)
    resolved_target = (target or "").strip() or "unknown"
    print(c(f"{symbol('action')} Target: {resolved_target}", Colors.CYAN))

    found_rows = found_profile_rows(results)
    error_rows = error_profile_rows(results)
    focus_rows = focused_profile_rows(results)
    snapshot = summarize_target_intel(results)

    _section("Found Social Media", Colors.GREEN)
    if not found_rows:
        print(c(f"{symbol('warn')} No FOUND profiles.", Colors.GREY))
    for item in found_rows:
        platform = item.get("platform", "Unknown")
        url = item.get("url", "")
        confidence = int(item.get("confidence", 0) or 0)
        print(c(f"{symbol('ok')} {platform} ({confidence}%)", Colors.GREEN))
        print(c(f"  {symbol('bullet')} profile: {url}", Colors.CYAN))
        contacts = item.get("contacts", {})
        if item.get("bio"):
            print(c(f"  {symbol('bullet')} bio: {str(item['bio'])[:180]}", Colors.GREY))
        if item.get("links"):
            top_links = ", ".join(item["links"][:6])
            print(c(f"  {symbol('bullet')} extracted links: {top_links}", Colors.YELLOW))
        if contacts.get("emails"):
            print(c(f"  {symbol('bullet')} emails: {', '.join(contacts['emails'])}", Colors.YELLOW))
        if contacts.get("phones"):
            print(c(f"  {symbol('bullet')} phones: {', '.join(contacts['phones'])}", Colors.YELLOW))
        if item.get("mentions"):
            print(c(f"  {symbol('bullet')} mentions: {', '.join(item['mentions'][:8])}", Colors.GREY))
        if item.get("http_status") is not None:
            print(c(f"  {symbol('bullet')} http: {item['http_status']}", Colors.GREY))
        if item.get("response_time_ms") is not None:
            print(c(f"  {symbol('bullet')} rtt: {item['response_time_ms']} ms", Colors.GREY))

    _section("Errored / Blocked Websites", Colors.RED)
    if not error_rows:
        print(c(f"{symbol('ok')} No ERROR/BLOCKED websites.", Colors.GREY))
    for item in error_rows:
        status = item.get("status", "ERROR")
        status_color = _status_color(status)
        platform = item.get("platform", "Unknown")
        url = item.get("url", "")
        marker = symbol("warn") if status in {"BLOCKED", "INVALID_USERNAME"} else symbol("error")
        print(c(f"{marker} [{status}] {platform}", status_color))
        print(c(f"  {symbol('bullet')} profile: {url}", Colors.CYAN))
        if item.get("http_status") is not None:
            print(c(f"  {symbol('bullet')} http: {item['http_status']}", Colors.GREY))
        if item.get("response_time_ms") is not None:
            print(c(f"  {symbol('bullet')} rtt: {item['response_time_ms']} ms", Colors.GREY))
        if item.get("context"):
            print(c(f"  {symbol('warn')} reason: {item['context']}", Colors.YELLOW))

    _section("Summary", Colors.BLUE)
    status_counter: Counter = Counter(item.get("status", "UNKNOWN") for item in results)
    preferred_order = ["FOUND", "ERROR", "BLOCKED", "NOT FOUND", "INVALID_USERNAME"]
    summary_parts: list[str] = []
    for key in preferred_order:
        if key in status_counter:
            summary_parts.append(f"{key.replace(' ', '_')}={status_counter[key]}")
    for key in sorted(status_counter):
        if key not in preferred_order:
            summary_parts.append(f"{key.replace(' ', '_')}={status_counter[key]}")
    summary_line = " ".join(summary_parts)
    print(c(f"{symbol('bullet')} {summary_line or 'No results'}", Colors.CYAN))
    print(c(f"{symbol('bullet')} VISIBLE_ROWS={len(focus_rows)}", Colors.CYAN))
    print(c(f"{symbol('bullet')} TOTAL_RESULTS={snapshot['total_results']}", Colors.CYAN))
    print(c(f"{symbol('ok')} FOUND_PROFILES={snapshot['found_count']}", Colors.GREEN))
    print(c(f"{symbol('error')} ERRORED_WEBSITES={snapshot['error_count']}", Colors.RED))
    print(c(f"{symbol('bullet')} COVERAGE_RATIO={snapshot['coverage_ratio']}", Colors.CYAN))
    print(c(f"{symbol('bullet')} AVG_FOUND_CONFIDENCE={snapshot['avg_found_confidence']}", Colors.CYAN))
    print(c(f"{symbol('bullet')} AVG_FOUND_RTT_MS={snapshot['avg_found_response_time_ms']}", Colors.CYAN))
    print(c(f"{symbol('bullet')} AVG_ERROR_RTT_MS={snapshot['avg_error_response_time_ms']}", Colors.CYAN))
    print(c(f"{symbol('bullet')} STATUS_BREAKDOWN={snapshot['status_breakdown']}", Colors.CYAN))

    if snapshot["profile_links"]:
        _section("Confirmed Profile Links", Colors.GREEN)
        for link in snapshot["profile_links"]:
            print(c(f"{symbol('bullet')} {link}", Colors.GREEN))

    _section("Target Intelligence Snapshot", Colors.BLUE)
    print(c(f"{symbol('bullet')} Found platforms: {_preview(snapshot['found_platforms'])}", Colors.GREY))
    print(c(f"{symbol('bullet')} Emails: {_preview(snapshot['emails'])}", Colors.GREY))
    print(c(f"{symbol('bullet')} Email domains: {_preview(snapshot['email_domains'])}", Colors.GREY))
    print(c(f"{symbol('bullet')} Phones: {_preview(snapshot['phones'])}", Colors.GREY))
    print(c(f"{symbol('bullet')} Names: {_preview(snapshot['names'])}", Colors.GREY))
    print(c(f"{symbol('bullet')} Mentions: {_preview(snapshot['mentions'])}", Colors.GREY))
    print(c(f"{symbol('bullet')} External links: {_preview(snapshot['external_links'])}", Colors.GREY))
    print(c(f"{symbol('bullet')} Link domains: {_preview(snapshot['external_link_domains'])}", Colors.GREY))
    if snapshot["bios"]:
        print(c(f"{symbol('bullet')} Bio snippets captured: {len(snapshot['bios'])}", Colors.GREY))

    shared_links = correlation.get("shared_links", {})
    shared_emails = correlation.get("shared_emails", {})
    shared_phones = correlation.get("shared_phones", {})
    overlap_score = correlation.get("identity_overlap_score", 0)
    _section("Correlation", Colors.BLUE)
    print(c(f"{symbol('action')} Identity overlap score: {overlap_score}/100", Colors.CYAN))
    print(c(f"{symbol('bullet')} Shared links: {len(shared_links)}", Colors.GREY))
    print(c(f"{symbol('bullet')} Shared emails: {len(shared_emails)}", Colors.GREY))
    print(c(f"{symbol('bullet')} Shared phones: {len(shared_phones)}", Colors.GREY))
    cluster_map = correlation.get("confidence_cluster_map", {})
    print(c(f"{symbol('bullet')} High-confidence cluster: {', '.join(cluster_map.get('high', [])) or 'None'}", Colors.GREY))

    if issues is not None:
        _print_issue_block(issues)
    if issue_summary:
        print(c(f"\n{symbol('warn')} Risk score: {issue_summary.get('risk_score', 0)}", Colors.MAGENTA))
        print(c(f"{symbol('bullet')} Severity breakdown: {issue_summary.get('severity_breakdown', {})}", Colors.MAGENTA))
    _print_extension_summary(
        _build_payload_summary(
            {
                "results": results,
                "issues": issues or [],
                "plugins": plugin_results or [],
                "filters": filter_results or [],
                "plugin_errors": plugin_errors or [],
                "filter_errors": filter_errors or [],
            }
        )
    )
    _print_intelligence_block(intelligence_bundle)
    _print_plugin_block(plugin_results, plugin_errors)
    _print_filter_block(filter_results, filter_errors)
    if narrative:
        _section("Nano AI Brief", Colors.CYAN)
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
    intelligence_bundle: dict | None = None,
) -> None:
    target = domain_result.get("target", "unknown")
    _section("Domain Surface Scan", Colors.BLUE)
    print(c(f"{symbol('action')} Target: {target}", Colors.CYAN))
    addresses = domain_result.get("resolved_addresses", [])
    print(c(f"{symbol('bullet')} Resolved addresses ({len(addresses)}): {', '.join(addresses) or 'none'}", Colors.GREY))

    https_data = domain_result.get("https", {})
    http_data = domain_result.get("http", {})
    print(c(f"{symbol('bullet')} HTTPS status: {https_data.get('status')} final={https_data.get('final_url')}", Colors.GREY))
    print(c(f"{symbol('bullet')} HTTP status: {http_data.get('status')} final={http_data.get('final_url')}", Colors.GREY))
    print(c(f"{symbol('bullet')} HTTP->HTTPS redirect: {http_data.get('redirects_to_https')}", Colors.GREY))
    print(c(f"{symbol('bullet')} Recon mode: {domain_result.get('recon_mode', 'hybrid')}", Colors.GREY))

    subdomains = domain_result.get("subdomains", [])
    if subdomains:
        print(c(f"{symbol('action')} Subdomains ({len(subdomains)}):", Colors.YELLOW))
        for name in subdomains[:25]:
            print(c(f"{symbol('bullet')} {name}", Colors.YELLOW))
        if len(subdomains) > 25:
            print(c(f"{symbol('tip')} ... and {len(subdomains) - 25} more", Colors.YELLOW))
    else:
        print(c(f"{symbol('bullet')} Subdomains: none", Colors.GREY))

    print(c(f"{symbol('bullet')} robots.txt present: {domain_result.get('robots_txt_present')}", Colors.GREY))
    print(c(f"{symbol('bullet')} security.txt present: {domain_result.get('security_txt_present')}", Colors.GREY))
    if domain_result.get("scan_notes"):
        print(c(f"{symbol('tip')} Scan notes:", Colors.YELLOW))
        for note in domain_result["scan_notes"]:
            print(c(f"{symbol('bullet')} {note}", Colors.YELLOW))
    collector_status = domain_result.get("collector_status", {})
    if isinstance(collector_status, dict):
        print(c(f"\n{symbol('major')} Recon Collector Status", Colors.BLUE))
        print(c("-" * 36, Colors.BLUE))
        for key, value in collector_status.items():
            if not isinstance(value, dict):
                continue
            print(
                c(
                    f"{symbol('bullet')} {key}: lane={value.get('lane')} "
                    f"status={value.get('status')} detail={value.get('detail')}",
                    Colors.GREY,
                )
            )
    surface_map = domain_result.get("surface_map", {})
    if isinstance(surface_map, dict):
        priority_summary = surface_map.get("priority_summary", {}) if isinstance(surface_map.get("priority_summary"), dict) else {}
        source_summary = surface_map.get("source_summary", {}) if isinstance(surface_map.get("source_summary"), dict) else {}
        print(c(f"\n{symbol('major')} Attack Surface Map", Colors.BLUE))
        print(c("-" * 36, Colors.BLUE))
        print(c(f"{symbol('action')} score={surface_map.get('attack_surface_score', 0)}", Colors.CYAN))
        print(c(f"{symbol('bullet')} source_summary={source_summary}", Colors.GREY))
        print(
            c(
                f"{symbol('bullet')} prioritized={_preview(list(priority_summary.get('prioritized_hosts', []) or []), limit=10)}",
                Colors.GREY,
            )
        )
    next_steps = domain_result.get("next_steps", [])
    if isinstance(next_steps, list) and next_steps:
        print(c(f"\n{symbol('major')} Recommended Next Steps", Colors.GREEN))
        print(c("-" * 36, Colors.GREEN))
        for row in next_steps[:6]:
            if not isinstance(row, dict):
                continue
            print(c(f"{symbol('action')} [{row.get('priority', 'P3')}] {row.get('title', 'Action')}", Colors.GREEN))
            print(c(f"  {symbol('bullet')} why: {row.get('rationale', '-')}", Colors.GREY))
            print(c(f"  {symbol('tip')} hint: {row.get('command_hint', '-')}", Colors.CYAN))

    if issues is not None:
        _print_issue_block(issues)
    if issue_summary:
        print(c(f"\n{symbol('warn')} Risk score: {issue_summary.get('risk_score', 0)}", Colors.MAGENTA))
        print(c(f"{symbol('bullet')} Severity breakdown: {issue_summary.get('severity_breakdown', {})}", Colors.MAGENTA))
    _print_extension_summary(
        _build_payload_summary(
            {
                "results": [],
                "issues": issues or [],
                "plugins": plugin_results or [],
                "filters": filter_results or [],
                "plugin_errors": plugin_errors or [],
                "filter_errors": filter_errors or [],
            }
        )
    )
    _print_intelligence_block(intelligence_bundle)
    _print_plugin_block(plugin_results, plugin_errors)
    _print_filter_block(filter_results, filter_errors)
    if narrative:
        _section("Nano AI Brief", Colors.CYAN)
        print(c(narrative, Colors.CYAN))

    print(c(f"\n{framework_signature()}", Colors.GREY))


def _render_cli_report(payload: dict) -> str:
    metadata = payload.get("metadata", {}) or {}
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    lines: list[str] = []
    lines.append(f"Framework: {metadata.get('framework', '-')}")
    lines.append(f"Generated UTC: {metadata.get('generated_at_utc', '-')}")
    lines.append(f"Mode: {metadata.get('mode', '-')}")
    lines.append(f"Target: {payload.get('target', '-')}")
    if payload.get("target_key"):
        lines.append(f"Storage Key: {payload.get('target_key')}")
    lines.append("")
    if summary:
        lines.append("[Artifact Summary]")
        lines.append(
            f"- results={summary.get('result_count', 0)} found={summary.get('found_count', 0)} "
            f"errors={summary.get('error_or_blocked_count', 0)}"
        )
        lines.append(
            f"- issues={summary.get('issue_count', 0)} plugins={summary.get('plugin_count', 0)} "
            f"filters={summary.get('filter_count', 0)}"
        )
        lines.append(f"- issue_severity={summary.get('issue_severity', {})}")
        lines.append(f"- plugin_severity={summary.get('plugin_severity', {})}")
        lines.append(f"- filter_severity={summary.get('filter_severity', {})}")
        lines.append("")

    results = payload.get("results", []) or []
    snapshot = summarize_target_intel(results)
    found_rows = found_profile_rows(results)
    error_rows = error_profile_rows(results)

    lines.append("[Found Social Profiles]")
    if not found_rows:
        lines.append("- none")
    else:
        for row in found_rows:
            lines.append(
                f"- {row.get('platform', 'Unknown')}: FOUND "
                f"({int(row.get('confidence', 0) or 0)}%) -> {row.get('url', '')}"
            )
    lines.append("")

    lines.append("[Errored / Blocked Websites]")
    if not error_rows:
        lines.append("- none")
    else:
        for row in error_rows:
            lines.append(
                f"- {row.get('platform', 'Unknown')}: {row.get('status', 'ERROR')} "
                f"http={row.get('http_status', '-')} reason={row.get('context', '-') or '-'}"
            )
    lines.append("")

    lines.append("[Target Intelligence Snapshot]")
    lines.append(f"- total_results: {snapshot['total_results']}")
    lines.append(f"- coverage_ratio: {snapshot['coverage_ratio']}")
    lines.append(f"- avg_found_confidence: {snapshot['avg_found_confidence']}")
    lines.append(f"- avg_found_response_time_ms: {snapshot['avg_found_response_time_ms']}")
    lines.append(f"- avg_error_response_time_ms: {snapshot['avg_error_response_time_ms']}")
    lines.append(f"- status_breakdown: {snapshot['status_breakdown']}")
    lines.append(f"- found_platforms: {', '.join(snapshot['found_platforms']) or 'none'}")
    lines.append(f"- profile_links: {', '.join(snapshot['profile_links']) or 'none'}")
    lines.append(f"- emails: {', '.join(snapshot['emails']) or 'none'}")
    lines.append(f"- email_domains: {', '.join(snapshot['email_domains']) or 'none'}")
    lines.append(f"- phones: {', '.join(snapshot['phones']) or 'none'}")
    lines.append(f"- names: {', '.join(snapshot['names']) or 'none'}")
    lines.append(f"- mentions: {', '.join(snapshot['mentions']) or 'none'}")
    lines.append(f"- external_links: {', '.join(snapshot['external_links']) or 'none'}")
    lines.append(f"- external_link_domains: {', '.join(snapshot['external_link_domains']) or 'none'}")
    lines.append("")

    domain_result = payload.get("domain_result")
    if domain_result:
        lines.append("[Domain Surface]")
        lines.append(f"- target: {domain_result.get('target', '-')}")
        lines.append(f"- recon_mode: {domain_result.get('recon_mode', 'hybrid')}")
        lines.append(
            f"- resolved_addresses: {', '.join(domain_result.get('resolved_addresses', []) or []) or 'none'}"
        )
        lines.append(f"- subdomains: {len(domain_result.get('subdomains', []) or [])}")
        surface_map = domain_result.get("surface_map", {}) if isinstance(domain_result.get("surface_map"), dict) else {}
        if surface_map:
            lines.append(f"- attack_surface_score: {surface_map.get('attack_surface_score', 0)}")
            lines.append(f"- source_summary: {surface_map.get('source_summary', {})}")
            priority_summary = surface_map.get("priority_summary", {})
            if isinstance(priority_summary, dict):
                lines.append(
                    "- prioritized_hosts: "
                    f"{', '.join(priority_summary.get('prioritized_hosts', []) or []) or 'none'}"
                )
        next_steps = domain_result.get("next_steps", [])
        if isinstance(next_steps, list) and next_steps:
            lines.append("- recon_next_steps:")
            for row in next_steps[:4]:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"  - [{row.get('priority', 'P3')}] {row.get('title', 'Action')}: "
                    f"{row.get('rationale', '-')}"
                )
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
        for row in _safe_dict_rows(plugin_rows):
            lines.append(
                f"- [{str(row.get('severity', 'INFO')).upper()}] "
                f"{row.get('title', row.get('id', 'plugin'))}: {row.get('summary', '')} "
                f"(data: {_compact_data_snapshot(row.get('data', {}), max_items=4)})"
            )
        for err in plugin_errors:
            lines.append(f"- {symbol('error')} {err}")
    lines.append("")

    filter_rows = payload.get("filters", []) or []
    filter_errors = payload.get("filter_errors", []) or []
    lines.append("[Filter Intelligence]")
    if not filter_rows and not filter_errors:
        lines.append("- none")
    else:
        for row in _safe_dict_rows(filter_rows):
            lines.append(
                f"- [{str(row.get('severity', 'INFO')).upper()}] "
                f"{row.get('title', row.get('id', 'filter'))}: {row.get('summary', '')} "
                f"(data: {_compact_data_snapshot(row.get('data', {}), max_items=4)})"
            )
        for err in filter_errors:
            lines.append(f"- {symbol('error')} {err}")
    lines.append("")

    fused_intel = payload.get("fused_intel", {}) or {}
    fusion_graph = payload.get("fusion_graph", {}) or {}
    if fused_intel:
        lines.append("[Fusion Intelligence]")
        lines.append(f"- confidence_score: {fused_intel.get('confidence_score', '-')}")
        lines.append(f"- anomalies: {', '.join(fused_intel.get('anomalies', []) or []) or 'none'}")
        if isinstance(fused_intel.get("risk"), dict):
            lines.append(f"- risk_score: {fused_intel.get('risk', {}).get('risk_score', '-')}")
        lines.append(
            f"- graph_nodes: {len(fusion_graph.get('nodes', []) or [])} "
            f"graph_edges: {len(fusion_graph.get('edges', []) or [])}"
        )
        lines.append("")

    intelligence_bundle = payload.get("intelligence_bundle", {}) or {}
    if intelligence_bundle:
        metadata = intelligence_bundle.get("metadata", {}) or {}
        facets = intelligence_bundle.get("entity_facets", {}) or {}
        confidence_distribution = intelligence_bundle.get("confidence_distribution", {}) or {}
        risk_summary = intelligence_bundle.get("risk_summary", {}) or {}
        scored_entities = intelligence_bundle.get("scored_entities", []) or []
        guidance = intelligence_bundle.get("execution_guidance", {}) or {}
        footprint_map = intelligence_bundle.get("footprint_map", {}) or {}

        lines.append("[Intelligence Scoring]")
        lines.append(
            f"- entities: {metadata.get('entity_count', 0)} evidence: {metadata.get('evidence_count', 0)}"
        )
        lines.append(
            "- confidence_distribution: "
            f"high={confidence_distribution.get('high', 0)} "
            f"medium={confidence_distribution.get('medium', 0)} "
            f"low={confidence_distribution.get('low', 0)}"
        )
        lines.append(f"- risk_summary: {risk_summary}")
        lines.append(f"- emails: {', '.join(facets.get('emails', []) or []) or 'none'}")
        lines.append(f"- phones: {', '.join(facets.get('phones', []) or []) or 'none'}")
        lines.append(f"- names: {', '.join(facets.get('names', []) or []) or 'none'}")
        if isinstance(footprint_map, dict) and footprint_map:
            summary = footprint_map.get("summary", {}) if isinstance(footprint_map.get("summary"), dict) else {}
            watchlist = footprint_map.get("watchlist", {}) if isinstance(footprint_map.get("watchlist"), dict) else {}
            lines.append("[Digital Footprint Map]")
            lines.append(
                f"- profiles={summary.get('profile_count', 0)} "
                f"linked_domains={summary.get('external_domain_count', 0)} "
                f"surface_assets={summary.get('surface_asset_count', 0)} "
                f"risk_signals={summary.get('risk_signal_count', 0)}"
            )
            lines.append(f"- lanes: {footprint_map.get('source_lanes', {})}")
            lines.append(f"- watch_handles: {', '.join(watchlist.get('handles', []) or []) or 'none'}")
            lines.append(f"- watch_domains: {', '.join(watchlist.get('domains', []) or []) or 'none'}")
        if scored_entities:
            lines.append("- top_scored_entities:")
            for row in list(scored_entities)[:12]:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    "  - "
                    f"{row.get('entity_type', '-')} {row.get('value', '-')}"
                    f" ({row.get('confidence_percent', 0)}%, risk={row.get('risk_level', '-')})"
                )
        actions = guidance.get("actions", []) if isinstance(guidance.get("actions"), list) else []
        if actions:
            lines.append("- guidance:")
            for item in actions[:6]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"  - [{item.get('priority', 'P3')}] {item.get('title', 'Action')}: "
                    f"{item.get('rationale', '-')}"
                )
                lines.append(f"    hint={item.get('command_hint', '-')}")
        lines.append("")

    narrative = str(payload.get("narrative") or "").strip()
    lines.append("[Nano AI Brief]")
    lines.append(f"- {narrative or 'No narrative generated.'}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def append_framework_log(event: str, details: str = "", *, level: str = "INFO") -> str:
    try:
        ensure_output_tree()
        path = framework_log_path()
        line = f"[{utc_timestamp()}] [{level.upper()}] {event}"
        if details:
            line = f"{line} | {details}"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return str(path)
    except (OutputConfigError, OSError):
        return ""


def list_scanned_targets(limit: int = 50) -> list[dict[str, str]]:
    rows = list_targets(limit=limit)
    return [
        {
            "target": row.target,
            "path": row.path,
            "modified_at": row.modified_at,
            "source": row.source,
        }
        for row in rows
    ]


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
    fused_intel: dict | None = None,
    fusion_graph: dict | None = None,
    intelligence_bundle: dict | None = None,
    output_types: set[str] | None = None,
    output_stamp: str | None = None,
    return_payload: bool = False,
) -> str | tuple[str, dict[str, Any]]:
    settings = get_output_settings()
    selected_types = {item.lower() for item in (output_types or set(settings.types)) if str(item).strip()}
    output_ready = True
    try:
        ensure_output_tree(types=selected_types)
    except OutputConfigError as exc:
        output_ready = False
        print(c(f"{symbol('warn')} {exc}", Colors.YELLOW))
        append_framework_log("save_results_failed", f"output_tree_failed reason={exc}", level="WARN")
        selected_types = set()
    target_display = str(target or "").strip()
    target_key = sanitize_target(target_display)
    stamp = output_stamp or datetime.now().strftime("%Y%m%d_%H%M%S")

    payload: dict[str, Any] = {
        "metadata": {
            "generated_at_utc": utc_timestamp(),
            "mode": mode,
            "framework": framework_signature(),
        },
        "target": target_display or target_key,
        "target_key": target_key,
        "results": results or [],
        "domain_result": domain_result,
        "correlation": correlation or {},
        "issues": issues or [],
        "issue_summary": issue_summary or {},
        "plugins": plugin_results or [],
        "plugin_errors": plugin_errors or [],
        "filters": filter_results or [],
        "filter_errors": filter_errors or [],
        "fused_intel": fused_intel or {},
        "fusion_graph": fusion_graph or {},
        "intelligence_bundle": intelligence_bundle or {},
        "narrative": narrative,
    }
    payload["summary"] = _build_payload_summary(payload)

    results_count = len(payload["results"]) if isinstance(payload["results"], list) else 0
    issues_count = len(payload["issues"]) if isinstance(payload["issues"], list) else 0
    plugins_count = len(payload["plugins"]) if isinstance(payload["plugins"], list) else 0
    filters_count = len(payload["filters"]) if isinstance(payload["filters"], list) else 0
    payload_summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    plugin_severity = payload_summary.get("plugin_severity", {}) if isinstance(payload_summary.get("plugin_severity"), dict) else {}
    filter_severity = payload_summary.get("filter_severity", {}) if isinstance(payload_summary.get("filter_severity"), dict) else {}
    issue_severity = payload_summary.get("issue_severity", {}) if isinstance(payload_summary.get("issue_severity"), dict) else {}
    fusion_graph_raw = payload.get("fusion_graph")
    fusion_graph_payload: dict[str, Any] = fusion_graph_raw if isinstance(fusion_graph_raw, dict) else {}
    intelligence_raw = payload.get("intelligence_bundle")
    intelligence_payload: dict[str, Any] = intelligence_raw if isinstance(intelligence_raw, dict) else {}
    fusion_nodes = len(fusion_graph_payload.get("nodes", []) or [])
    fusion_edges = len(fusion_graph_payload.get("edges", []) or [])
    intelligence_entities = len(intelligence_payload.get("entities", []) or [])
    intelligence_links = len(intelligence_payload.get("relationships", []) or [])

    json_path: Path | None = None
    if output_ready and "json" in selected_types:
        data_target_dir(target_key).mkdir(parents=True, exist_ok=True)
        json_path = results_json_path(target_key, stamp=stamp)
        try:
            with json_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=4)
        except OSError as exc:
            append_framework_log("save_results_failed", f"json_write_failed target={target_key} reason={exc}", level="WARN")
            print(c(f"{symbol('warn')} Failed to write JSON output: {exc}", Colors.YELLOW))
            json_path = None

        if json_path is not None:
            legacy_path = legacy_results_json_path(target_key)
            try:
                legacy_path.parent.mkdir(parents=True, exist_ok=True)
                with legacy_path.open("w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=4)
            except OSError as exc:
                append_framework_log(
                    "save_results_failed",
                    f"legacy_json_write_failed target={target_key} reason={exc}",
                    level="WARN",
                )
                print(c(f"{symbol('warn')} Failed to write legacy JSON output: {exc}", Colors.YELLOW))

    cli_path: Path | None = None
    if output_ready and "cli" in selected_types:
        cli_path = cli_report_path(target_key, stamp=stamp)
        try:
            cli_path.write_text(_render_cli_report(payload), encoding="utf-8")
        except OSError as exc:
            append_framework_log("save_results_failed", f"cli_write_failed target={target_key} reason={exc}", level="WARN")
            print(c(f"{symbol('warn')} Failed to write CLI report: {exc}", Colors.YELLOW))
            cli_path = None

    run_log: Path | None = None
    if output_ready:
        run_log = run_log_path(target_key, stamp=stamp)
        try:
            run_log.write_text(
                (
                    f"timestamp={utc_timestamp()}\n"
                    f"target={target_display or target_key}\n"
                    f"target_key={target_key}\n"
                    f"mode={mode}\n"
                    f"results={results_count}\n"
                    f"issues={issues_count}\n"
                    f"plugins={plugins_count}\n"
                    f"filters={filters_count}\n"
                    f"issue_severity={issue_severity}\n"
                    f"plugin_severity={plugin_severity}\n"
                    f"filter_severity={filter_severity}\n"
                    f"fusion_nodes={fusion_nodes}\n"
                    f"fusion_edges={fusion_edges}\n"
                    f"intelligence_entities={intelligence_entities}\n"
                    f"intelligence_links={intelligence_links}\n"
                    f"framework={framework_signature()}\n"
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            append_framework_log(
                "save_results_failed",
                f"log_write_failed target={target_key} reason={exc}",
                level="WARN",
            )
            print(c(f"{symbol('warn')} Failed to write run log: {exc}", Colors.YELLOW))
            run_log = None
    append_framework_log(
        "scan_saved",
        (
            f"target={target_display or target_key} target_key={target_key} "
            f"mode={mode} json={json_path or '-'} cli={cli_path or '-'} log={run_log or '-'}"
        ),
    )

    if json_path is not None:
        print(c(f"\n{symbol('ok')} Results JSON saved to {json_path}", Colors.GREEN))
    if cli_path is not None:
        print(c(f"{symbol('ok')} CLI report saved to {cli_path}", Colors.GREEN))
    if run_log is not None:
        print(c(f"{symbol('ok')} Run log saved to {run_log}", Colors.GREEN))
    if return_payload:
        return str(json_path or run_log or ""), payload
    return str(json_path or run_log or "")
