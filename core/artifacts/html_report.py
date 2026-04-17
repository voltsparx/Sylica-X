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

"""HTML report generation for Silica-X."""

from __future__ import annotations

import html
import json
from datetime import datetime

from core.foundation.metadata import AUTHOR, PROJECT_NAME, VERSION, framework_signature
from core.analyze.profile_summary import (
    error_profile_rows,
    focused_profile_rows,
    found_profile_rows,
    summarize_target_intel,
)
from core.artifacts.storage import ensure_output_tree, html_report_path, sanitize_target
from core.foundation.output_config import OutputConfigError


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


def _compact_data_snapshot(data: object, *, max_items: int = 6) -> str:
    if not isinstance(data, dict) or not data:
        return "-"
    tokens: list[str] = []
    for key in sorted(data.keys(), key=str):
        value = data.get(key)
        if isinstance(value, (str, int, float, bool)):
            tokens.append(f"{key}={value}")
        elif isinstance(value, list):
            tokens.append(f"{key}[{len(value)}]")
        elif isinstance(value, dict):
            tokens.append(f"{key}{{{len(value)}}}")
        elif value is None:
            tokens.append(f"{key}=null")
        else:
            tokens.append(f"{key}=...")
        if len(tokens) >= max_items:
            break
    return ", ".join(tokens) if tokens else "-"


def _crypto_profile_html(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    profile = data.get("crypto_profile")
    if not isinstance(profile, dict):
        return ""
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
        sources = ", ".join(str(item) for item in source_fields if str(item).strip())
    else:
        sources = "-"
    return (
        "<p><strong>Crypto Config:</strong> "
        f"kind={html.escape(kind)} | "
        f"operation={html.escape(operation)} | "
        f"encoding={html.escape(output_encoding)} | "
        f"max_items={html.escape(str(max_items))} | "
        f"strict={html.escape(str(strict_mode))} | "
        f"sources={html.escape(sources)}"
        "</p>"
    )


def _status_badge(status: str) -> str:
    color_map = {
        "FOUND": "#ff8a3d",
        "NOT FOUND": "#8a8f98",
        "BLOCKED": "#ffb454",
        "INVALID_USERNAME": "#ffb454",
        "ERROR": "#ff6d7a",
    }
    color = color_map.get(status, "#8a8f98")
    return (
        f"<span class='badge' style='background:{color};'>{html.escape(status)}</span>"
    )


def _metric_card(label: str, value: str, hint: str = "") -> str:
    return (
        "<div class='metric-card'>"
        f"<div class='metric-label'>{html.escape(label)}</div>"
        f"<div class='metric-value'>{html.escape(value)}</div>"
        f"<div class='metric-hint'>{html.escape(hint)}</div>"
        "</div>"
    )


def _render_chip_list(values: list[str], *, empty_label: str = "None", max_items: int = 14) -> str:
    if not values:
        return f"<span class='muted'>{html.escape(empty_label)}</span>"

    chips = "".join(
        f"<span class='chip'>{html.escape(value)}</span>" for value in values[:max_items]
    )
    if len(values) > max_items:
        chips += f"<span class='chip chip-muted'>+{len(values) - max_items} more</span>"
    return chips


def _render_target_snapshot(target: str, snapshot: dict, total_checks: int) -> str:
    bios = "".join(
        f"<li>{html.escape(value[:260])}</li>" for value in snapshot.get("bios", [])[:4]
    ) or "<li>None</li>"

    return (
        "<section class='panel'>"
        "<h3>Target Intelligence Snapshot</h3>"
        f"<p><strong>Target:</strong> {html.escape(target)}</p>"
        f"<p><strong>Checks Run:</strong> {total_checks} | "
        f"<strong>Found Profiles:</strong> {snapshot.get('found_count', 0)} | "
        f"<strong>Errored/Blocked:</strong> {snapshot.get('error_count', 0)} | "
        f"<strong>Coverage Ratio:</strong> {snapshot.get('coverage_ratio', 0)}</p>"
        f"<p><strong>Avg Found Confidence:</strong> {snapshot.get('avg_found_confidence', 0)} | "
        f"<strong>Avg Found RTT:</strong> {snapshot.get('avg_found_response_time_ms', 0)} ms | "
        f"<strong>Avg Error RTT:</strong> {snapshot.get('avg_error_response_time_ms', 0)} ms</p>"
        f"<p><strong>Status Breakdown:</strong> {html.escape(str(snapshot.get('status_breakdown', {})))}</p>"
        "<div class='chip-group'>"
        "<h4>Found Platforms</h4>"
        f"<div>{_render_chip_list(snapshot.get('found_platforms', []))}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>Emails</h4>"
        f"<div>{_render_chip_list(snapshot.get('emails', []))}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>Email Domains</h4>"
        f"<div>{_render_chip_list(snapshot.get('email_domains', []))}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>Phones</h4>"
        f"<div>{_render_chip_list(snapshot.get('phones', []))}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>Names</h4>"
        f"<div>{_render_chip_list(snapshot.get('names', []))}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>Mentions</h4>"
        f"<div>{_render_chip_list(snapshot.get('mentions', []))}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>External Links</h4>"
        f"<div>{_render_chip_list(snapshot.get('external_links', []))}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>External Link Domains</h4>"
        f"<div>{_render_chip_list(snapshot.get('external_link_domains', []))}</div>"
        "</div>"
        "<h4>Bio Snippets</h4>"
        f"<ul>{bios}</ul>"
        "</section>"
    )


def _render_found_profile_table(rows: list[dict]) -> str:
    rendered_rows: list[str] = []
    for item in rows:
        contacts = item.get("contacts", {}) or {}
        links = item.get("links", []) or []
        mentions = item.get("mentions", []) or []
        profile_url = html.escape(str(item.get("url", "")))
        account_link = f"<a href='{profile_url}' target='_blank' rel='noreferrer'>{profile_url}</a>"

        extracted_links = "<br>".join(
            f"<a href='{html.escape(str(link))}' target='_blank' rel='noreferrer'>{html.escape(str(link))}</a>"
            for link in links[:8]
        )
        if not extracted_links:
            extracted_links = "-"

        bio = html.escape(str(item.get("bio") or "-")).replace("\n", "<br>")
        context = html.escape(str(item.get("context") or "-"))

        rendered_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('platform', 'Unknown')))}</td>"
            f"<td>{int(item.get('confidence', 0) or 0)}%</td>"
            f"<td>{account_link}</td>"
            f"<td>{html.escape(', '.join(contacts.get('emails', []) or []) or '-')}</td>"
            f"<td>{html.escape(', '.join(contacts.get('phones', []) or []) or '-')}</td>"
            f"<td>{html.escape(', '.join(str(value) for value in mentions[:10]) or '-')}</td>"
            f"<td>{extracted_links}</td>"
            f"<td>{bio}</td>"
            f"<td>{context}</td>"
            "</tr>"
        )

    return "\n".join(rendered_rows) or "<tr><td colspan='9'>No FOUND profiles in this run.</td></tr>"


def _render_error_table(rows: list[dict]) -> str:
    rendered_rows: list[str] = []
    for item in rows:
        profile_url = html.escape(str(item.get("url", "")))
        account_link = f"<a href='{profile_url}' target='_blank' rel='noreferrer'>{profile_url}</a>"
        http_value = item.get("http_status")
        rtt_value = item.get("response_time_ms")

        rendered_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('platform', 'Unknown')))}</td>"
            f"<td>{_status_badge(str(item.get('status', 'ERROR')))}</td>"
            f"<td>{account_link}</td>"
            f"<td>{html.escape(str(http_value if http_value is not None else '-'))}</td>"
            f"<td>{html.escape(str(rtt_value if rtt_value is not None else '-'))}</td>"
            f"<td>{html.escape(str(item.get('context') or '-'))}</td>"
            "</tr>"
        )

    return "\n".join(rendered_rows) or "<tr><td colspan='6'>No ERROR/BLOCKED websites in this run.</td></tr>"


def _render_correlation(correlation: dict) -> str:
    sections: list[str] = []
    mapping = [
        ("shared_bios", "Shared Bios"),
        ("shared_emails", "Shared Emails"),
        ("shared_phones", "Shared Phones"),
        ("shared_links", "Shared Links"),
        ("shared_mentions", "Shared Mentions"),
    ]
    for key, title in mapping:
        payload = correlation.get(key, {})
        if not payload:
            continue
        entries = []
        for artifact, platforms in payload.items():
            entries.append(
                f"<li><strong>{html.escape(str(artifact))}</strong> "
                f"<span class='muted'>-> {html.escape(', '.join(platforms))}</span></li>"
            )
        sections.append(f"<h4>{html.escape(title)}</h4><ul>{''.join(entries)}</ul>")

    cluster_map = correlation.get("confidence_cluster_map", {})
    if cluster_map:
        sections.append(
            "<h4>Confidence Clusters</h4>"
            "<ul>"
            f"<li><strong>High:</strong> {html.escape(', '.join(cluster_map.get('high', [])) or 'None')}</li>"
            f"<li><strong>Medium:</strong> {html.escape(', '.join(cluster_map.get('medium', [])) or 'None')}</li>"
            f"<li><strong>Low:</strong> {html.escape(', '.join(cluster_map.get('low', [])) or 'None')}</li>"
            "</ul>"
        )

    if not sections:
        return "<p class='muted'>No correlation overlaps were identified.</p>"
    return "".join(sections)


def _render_domain_section(domain_result: dict | None) -> str:
    if not domain_result:
        return ""

    subdomains = domain_result.get("subdomains", [])
    subdomain_items = "".join(f"<li>{html.escape(item)}</li>" for item in subdomains[:40]) or "<li>None</li>"
    notes = "".join(f"<li>{html.escape(note)}</li>" for note in domain_result.get("scan_notes", [])) or "<li>None</li>"
    https_data = domain_result.get("https", {})
    http_data = domain_result.get("http", {})
    rdap = domain_result.get("rdap", {})
    collector_status = domain_result.get("collector_status", {}) if isinstance(domain_result.get("collector_status"), dict) else {}
    collector_items = "".join(
        "<li>"
        f"<strong>{html.escape(str(key))}</strong>: "
        f"lane={html.escape(str(value.get('lane', '-')))} "
        f"status={html.escape(str(value.get('status', '-')))} "
        f"detail={html.escape(str(value.get('detail', '-')))}"
        "</li>"
        for key, value in collector_status.items()
        if isinstance(value, dict)
    ) or "<li>None</li>"
    surface_map = domain_result.get("surface_map", {}) if isinstance(domain_result.get("surface_map"), dict) else {}
    scan_controls = domain_result.get("scan_controls", {}) if isinstance(domain_result.get("scan_controls"), dict) else {}
    packet_crafting = domain_result.get("packet_crafting", {}) if isinstance(domain_result.get("packet_crafting"), dict) else {}
    source_summary = surface_map.get("source_summary", {}) if isinstance(surface_map.get("source_summary"), dict) else {}
    priority_summary = surface_map.get("priority_summary", {}) if isinstance(surface_map.get("priority_summary"), dict) else {}
    probe_plan = surface_map.get("probe_plan", {}) if isinstance(surface_map.get("probe_plan"), dict) else {}
    next_steps = domain_result.get("next_steps", []) if isinstance(domain_result.get("next_steps"), list) else []
    packet_bundles = packet_crafting.get("bundles", []) if isinstance(packet_crafting.get("bundles"), list) else []
    packet_bundle_items = "".join(
        "<li>"
        f"<strong>{html.escape(str(row.get('title', 'Packet Bundle')))}</strong>: "
        f"{html.escape(str(row.get('purpose', '-')))} "
        f"(artifacts={html.escape(str(row.get('artifact_count', 0)))})"
        "</li>"
        for row in packet_bundles[:6]
        if isinstance(row, dict)
    ) or "<li>None</li>"
    packet_notes = "".join(
        f"<li>{html.escape(str(note))}</li>"
        for note in list(packet_crafting.get("notes", []) or [])[:8]
    ) or "<li>None</li>"
    next_step_items = "".join(
        "<li>"
        f"[{html.escape(str(row.get('priority', 'P3')))}] "
        f"{html.escape(str(row.get('title', 'Action')))}"
        f"<br><span class='muted'>{html.escape(str(row.get('rationale', '-')))}</span>"
        f"<br><span class='muted'>Hint: {html.escape(str(row.get('command_hint', '-')))}</span>"
        "</li>"
        for row in next_steps[:6]
        if isinstance(row, dict)
    ) or "<li>None</li>"

    return (
        "<section class='panel'>"
        "<h3>Domain Surface Intelligence</h3>"
        f"<p><strong>Target:</strong> {html.escape(domain_result.get('target', ''))}</p>"
        f"<p><strong>Recon Mode:</strong> {html.escape(str(domain_result.get('recon_mode', 'hybrid')))}</p>"
        f"<p><strong>Resolved Addresses:</strong> {html.escape(', '.join(domain_result.get('resolved_addresses', [])) or 'None')}</p>"
        f"<p><strong>HTTPS:</strong> status={html.escape(str(https_data.get('status')))} "
        f"final={html.escape(str(https_data.get('final_url')))}</p>"
        f"<p><strong>HTTP:</strong> status={html.escape(str(http_data.get('status')))} "
        f"final={html.escape(str(http_data.get('final_url')))} "
        f"redirects_to_https={html.escape(str(http_data.get('redirects_to_https')))}</p>"
        f"<p><strong>RDAP Handle:</strong> {html.escape(str(rdap.get('handle') or '-'))}</p>"
        f"<p><strong>Scan Controls:</strong> "
        f"types={html.escape(', '.join(scan_controls.get('scan_types', []) or []) or 'none')} | "
        f"verbosity={html.escape(str(scan_controls.get('scan_verbosity', 'standard')))} | "
        f"os_fingerprint={html.escape(str(scan_controls.get('os_fingerprint_enabled', False)))} | "
        f"delay_seconds={html.escape(str(scan_controls.get('delay_seconds', 0.0)))}</p>"
        f"<p><strong>Attack Surface Score:</strong> {html.escape(str(surface_map.get('attack_surface_score', 0)))} "
        f"| <strong>Source Summary:</strong> {html.escape(str(source_summary))}</p>"
        "<h4>Subdomain Candidates</h4>"
        f"<ul>{subdomain_items}</ul>"
        "<h4>Prioritized Hosts</h4>"
        f"<div>{_render_chip_list(list(priority_summary.get('prioritized_hosts', []) or []), max_items=18)}</div>"
        "<h4>Matched Priority Labels</h4>"
        f"<div>{_render_chip_list(list(priority_summary.get('matched_priority_labels', []) or []), max_items=18)}</div>"
        "<h4>Recommended Ports</h4>"
        f"<div>{_render_chip_list([str(item) for item in list(probe_plan.get('recommended_ports', []) or [])], max_items=18)}</div>"
        "<h4>Common Paths</h4>"
        f"<div>{_render_chip_list(list(probe_plan.get('common_paths', []) or []), max_items=18)}</div>"
        "<h4>Packet Crafting Plan</h4>"
        f"<p><strong>Authorized Host:</strong> {html.escape(str(packet_crafting.get('authorized_host', '-')))}"
        f" | <strong>Requested Types:</strong> {html.escape(', '.join(packet_crafting.get('requested_scan_types', []) or []) or 'none')}"
        f" | <strong>Selected Ports:</strong> {html.escape(', '.join(str(item) for item in (packet_crafting.get('selected_ports', []) or [])) or 'none')}</p>"
        f"<ul>{packet_bundle_items}</ul>"
        "<h4>Packet Crafting Notes</h4>"
        f"<ul>{packet_notes}</ul>"
        "<h4>Collector Status</h4>"
        f"<ul>{collector_items}</ul>"
        "<h4>Collector Notes</h4>"
        f"<ul>{notes}</ul>"
        "<h4>Recommended Next Steps</h4>"
        f"<ul>{next_step_items}</ul>"
        "</section>"
    )


def _render_issues(issues: list[dict[str, str]], issue_summary: dict) -> str:
    if not issues:
        return "<p class='muted'>No exposure findings were reported.</p>"

    rows = []
    for issue in issues:
        rows.append(
            "<tr>"
            f"<td>{html.escape(issue.get('severity', 'LOW'))}</td>"
            f"<td>{html.escape(issue.get('scope', '-'))}</td>"
            f"<td>{html.escape(issue.get('title', '-'))}</td>"
            f"<td>{html.escape(issue.get('evidence', '-'))}</td>"
            f"<td>{html.escape(issue.get('recommendation', '-'))}</td>"
            "</tr>"
        )

    return (
        f"<p><strong>Risk Score:</strong> {html.escape(str(issue_summary.get('risk_score', 0)))}</p>"
        f"<p><strong>Severity Breakdown:</strong> {html.escape(str(issue_summary.get('severity_breakdown', {})))}</p>"
        "<div class='table-wrap'>"
        "<table>"
        "<tr><th>Severity</th><th>Scope</th><th>Title</th><th>Evidence</th><th>Recommendation</th></tr>"
        f"{''.join(rows)}"
        "</table>"
        "</div>"
    )


def _render_plugins(plugin_results: list[dict], plugin_errors: list[str]) -> str:
    if not plugin_results and not plugin_errors:
        return "<p class='muted'>No plugins were executed for this run.</p>"

    cards = []
    for plugin in _safe_dict_rows(plugin_results):
        highlights = plugin.get("highlights", []) or []
        highlight_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in highlights[:8]) or "<li>None</li>"
        data_payload = plugin.get("data", {})
        payload_preview = _compact_data_snapshot(data_payload)
        payload_json = html.escape(json.dumps(data_payload, indent=2, default=str))
        crypto_config_html = _crypto_profile_html(data_payload)
        severity = str(plugin.get("severity", "INFO")).upper()
        cards.append(
            "<div class='subpanel'>"
            f"<h4>{html.escape(plugin.get('title', plugin.get('id', 'Plugin')))} "
            f"<span class='badge badge-inline'>{html.escape(severity)}</span></h4>"
            f"<p>{html.escape(plugin.get('summary', ''))}</p>"
            f"{crypto_config_html}"
            f"<p><strong>Data Snapshot:</strong> {html.escape(payload_preview)}</p>"
            "<ul>"
            f"{highlight_html}"
            "</ul>"
            "<details><summary>Raw plugin data payload</summary>"
            f"<pre>{payload_json}</pre>"
            "</details>"
            "</div>"
        )
    if plugin_errors:
        err = "".join(f"<li>{html.escape(str(item))}</li>" for item in plugin_errors)
        cards.append(f"<h4>Plugin Errors</h4><ul>{err}</ul>")

    return "".join(cards)


def _render_filters(filter_results: list[dict], filter_errors: list[str]) -> str:
    if not filter_results and not filter_errors:
        return "<p class='muted'>No filters were executed for this run.</p>"

    cards = []
    for row in _safe_dict_rows(filter_results):
        highlights = row.get("highlights", []) or []
        highlight_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in highlights[:8]) or "<li>None</li>"
        payload_preview = _compact_data_snapshot(row.get("data", {}))
        payload_json = html.escape(json.dumps(row.get("data", {}), indent=2, default=str))
        severity = str(row.get("severity", "INFO")).upper()
        cards.append(
            "<div class='subpanel'>"
            f"<h4>{html.escape(row.get('title', row.get('id', 'Filter')))} "
            f"<span class='badge badge-inline'>{html.escape(severity)}</span></h4>"
            f"<p>{html.escape(row.get('summary', ''))}</p>"
            f"<p><strong>Data Snapshot:</strong> {html.escape(payload_preview)}</p>"
            "<ul>"
            f"{highlight_html}"
            "</ul>"
            "<details><summary>Raw filter data payload</summary>"
            f"<pre>{payload_json}</pre>"
            "</details>"
            "</div>"
        )

    if filter_errors:
        err = "".join(f"<li>{html.escape(str(item))}</li>" for item in filter_errors)
        cards.append(f"<h4>Filter Errors</h4><ul>{err}</ul>")
    return "".join(cards)


def _render_extension_overview(
    issues: list[dict[str, str]],
    issue_summary: dict,
    plugin_results: list[dict],
    plugin_errors: list[str],
    filter_results: list[dict],
    filter_errors: list[str],
) -> str:
    safe_issues = _safe_dict_rows(issues)
    safe_plugins = _safe_dict_rows(plugin_results)
    safe_filters = _safe_dict_rows(filter_results)
    issue_breakdown = _severity_breakdown(safe_issues)
    plugin_breakdown = _severity_breakdown(safe_plugins)
    filter_breakdown = _severity_breakdown(safe_filters)

    cards = "".join(
        [
            _metric_card("Risk Score", str(issue_summary.get("risk_score", 0)), "exposure model"),
            _metric_card("Issues", str(len(safe_issues)), f"critical={issue_breakdown.get('CRITICAL', 0)}"),
            _metric_card("Plugins", str(len(safe_plugins)), f"errors={len(plugin_errors)}"),
            _metric_card("Filters", str(len(safe_filters)), f"errors={len(filter_errors)}"),
        ]
    )
    return (
        "<section class='panel'>"
        "<h3>Extension Signal Overview</h3>"
        f"<div class='metrics'>{cards}</div>"
        f"<p><strong>Issue Severity:</strong> {html.escape(str(issue_breakdown))}</p>"
        f"<p><strong>Plugin Severity:</strong> {html.escape(str(plugin_breakdown))}</p>"
        f"<p><strong>Filter Severity:</strong> {html.escape(str(filter_breakdown))}</p>"
        "</section>"
    )


def _render_intelligence_bundle(intelligence_bundle: dict | None) -> str:
    bundle = intelligence_bundle or {}
    if not bundle:
        return "<p class='muted'>No intelligence scoring bundle was generated for this run.</p>"

    metadata = bundle.get("metadata", {}) or {}
    confidence_distribution = bundle.get("confidence_distribution", {}) or {}
    risk_summary = bundle.get("risk_summary", {}) or {}
    facets = bundle.get("entity_facets", {}) or {}
    scored_contacts = list(facets.get("scored_contacts", []) or [])
    scored_entities = list(bundle.get("scored_entities", []) or [])
    correlation_summary = bundle.get("correlation_summary", {}) or {}
    guidance = bundle.get("execution_guidance", {}) or {}
    actions = guidance.get("actions", []) if isinstance(guidance.get("actions"), list) else []
    footprint_map = bundle.get("footprint_map", {}) if isinstance(bundle.get("footprint_map"), dict) else {}

    contact_rows = []
    for item in scored_contacts[:28]:
        if not isinstance(item, dict):
            continue
        contact_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('kind', '-')))}</td>"
            f"<td>{html.escape(str(item.get('value', '-')))}</td>"
            f"<td>{html.escape(str(item.get('score_percent', 0)))}%</td>"
            f"<td>{html.escape(str(item.get('supporting_entities', 0)))}</td>"
            f"<td>{html.escape(str(item.get('risk_level', 'LOW')))}</td>"
            "</tr>"
        )
    if not contact_rows:
        contact_rows.append("<tr><td colspan='5'>No contact/name scoring rows.</td></tr>")

    entity_rows = []
    for item in scored_entities[:34]:
        if not isinstance(item, dict):
            continue
        entity_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('rank', '-')))}</td>"
            f"<td>{html.escape(str(item.get('entity_type', '-')))}</td>"
            f"<td>{html.escape(str(item.get('value', '-')))}</td>"
            f"<td>{html.escape(str(item.get('source', '-')))}</td>"
            f"<td>{html.escape(str(item.get('confidence_percent', 0)))}%</td>"
            f"<td>{html.escape(str(item.get('risk_level', 'LOW')))}</td>"
            f"<td>{html.escape(str(item.get('relationship_count', 0)))}</td>"
            "</tr>"
        )
    if not entity_rows:
        entity_rows.append("<tr><td colspan='7'>No scored entities.</td></tr>")

    reason_breakdown = correlation_summary.get("reason_breakdown", {}) or {}
    reason_items = "".join(
        f"<li><strong>{html.escape(str(reason))}</strong>: {html.escape(str(count))}</li>"
        for reason, count in list(reason_breakdown.items())[:12]
    ) or "<li>None</li>"
    guidance_items = "".join(
        "<li>"
        f"[{html.escape(str(item.get('priority', 'P3')))}] {html.escape(str(item.get('title', 'Action')))}"
        f"<br><span class='muted'>{html.escape(str(item.get('rationale', '-')))}</span>"
        f"<br><span class='muted'>Hint: {html.escape(str(item.get('command_hint', '-')))}</span>"
        "</li>"
        for item in actions[:8]
        if isinstance(item, dict)
    ) or "<li>None</li>"
    footprint_html = ""
    if footprint_map:
        summary = footprint_map.get("summary", {}) if isinstance(footprint_map.get("summary"), dict) else {}
        watchlist = footprint_map.get("watchlist", {}) if isinstance(footprint_map.get("watchlist"), dict) else {}
        indicators = footprint_map.get("threat_indicators", []) if isinstance(footprint_map.get("threat_indicators"), list) else []
        indicator_items = "".join(
            "<li>"
            f"[{html.escape(str(item.get('severity', 'INFO')))}] {html.escape(str(item.get('title', 'Signal')))}"
            f"<br><span class='muted'>{html.escape(str(item.get('evidence', '-')))}</span>"
            "</li>"
            for item in indicators[:8]
            if isinstance(item, dict)
        ) or "<li>None</li>"
        footprint_html = (
            "<h4>Digital Footprint Map</h4>"
            f"<p><strong>Profiles:</strong> {html.escape(str(summary.get('profile_count', 0)))} | "
            f"<strong>Linked Domains:</strong> {html.escape(str(summary.get('external_domain_count', 0)))} | "
            f"<strong>Surface Assets:</strong> {html.escape(str(summary.get('surface_asset_count', 0)))} | "
            f"<strong>Risk Signals:</strong> {html.escape(str(summary.get('risk_signal_count', 0)))}</p>"
            f"<p><strong>Observed Lanes:</strong> {html.escape(str(footprint_map.get('source_lanes', {})))}</p>"
            "<div class='chip-group'>"
            "<h4>Watch Handles</h4>"
            f"<div>{_render_chip_list(list(watchlist.get('handles', []) or []), max_items=18)}</div>"
            "</div>"
            "<div class='chip-group'>"
            "<h4>Watch Domains</h4>"
            f"<div>{_render_chip_list(list(watchlist.get('domains', []) or []), max_items=18)}</div>"
            "</div>"
            "<h4>Risk Signals</h4>"
            f"<ul>{indicator_items}</ul>"
        )

    return (
        f"<p><strong>Entities:</strong> {html.escape(str(metadata.get('entity_count', 0)))} | "
        f"<strong>Evidence:</strong> {html.escape(str(metadata.get('evidence_count', 0)))} | "
        f"<strong>Links:</strong> {html.escape(str(correlation_summary.get('link_count', 0)))}</p>"
        "<p><strong>Confidence Distribution:</strong> "
        f"high={html.escape(str(confidence_distribution.get('high', 0)))} "
        f"medium={html.escape(str(confidence_distribution.get('medium', 0)))} "
        f"low={html.escape(str(confidence_distribution.get('low', 0)))}</p>"
        f"<p><strong>Risk Summary:</strong> {html.escape(str(risk_summary))}</p>"
        "<div class='chip-group'>"
        "<h4>Emails</h4>"
        f"<div>{_render_chip_list(list(facets.get('emails', []) or []), max_items=18)}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>Phones</h4>"
        f"<div>{_render_chip_list(list(facets.get('phones', []) or []), max_items=18)}</div>"
        "</div>"
        "<div class='chip-group'>"
        "<h4>Names</h4>"
        f"<div>{_render_chip_list(list(facets.get('names', []) or []), max_items=18)}</div>"
        "</div>"
        "<h4>Top Contact / Name Signals</h4>"
        "<div class='table-wrap'>"
        "<table>"
        "<tr><th>Kind</th><th>Value</th><th>Score</th><th>Support</th><th>Risk</th></tr>"
        f"{''.join(contact_rows)}"
        "</table>"
        "</div>"
        "<h4>Top Scored Entities</h4>"
        "<div class='table-wrap'>"
        "<table>"
        "<tr><th>Rank</th><th>Type</th><th>Value</th><th>Source</th><th>Confidence</th><th>Risk</th><th>Links</th></tr>"
        f"{''.join(entity_rows)}"
        "</table>"
        "</div>"
        "<h4>Correlation Reasons</h4>"
        f"<ul>{reason_items}</ul>"
        f"{footprint_html}"
        "<h4>Explainable Guidance</h4>"
        f"<ul>{guidance_items}</ul>"
    )


def _render_ocr_scan(ocr_scan: dict | None) -> str:
    if not isinstance(ocr_scan, dict) or not ocr_scan:
        return ""

    summary = ocr_scan.get("summary") if isinstance(ocr_scan.get("summary"), dict) else {}
    items = _safe_dict_rows(ocr_scan.get("items"))
    failures = _safe_dict_rows(ocr_scan.get("failures"))

    item_cards: list[str] = []
    for item in items[:18]:
        raw_text = html.escape(str(item.get("raw_text") or "")).replace("\n", "<br>")
        item_cards.append(
            "<div class='subpanel'>"
            f"<h4>{html.escape(str(item.get('display_name') or item.get('source') or 'image'))}</h4>"
            f"<p><strong>Kind:</strong> {html.escape(str(item.get('source_kind', '-')))} | "
            f"<strong>Engine:</strong> {html.escape(str(item.get('ocr_engine', 'none')))} | "
            f"<strong>Confidence:</strong> {html.escape(str(item.get('confidence_hint', 'low')))}</p>"
            f"<p><strong>Signals:</strong> {html.escape(str(item.get('extracted_signals', {})))}</p>"
            f"<p><strong>Preprocess:</strong> {html.escape(', '.join(item.get('preprocess_pipeline', []) or []) or 'none')}</p>"
            "<details><summary>Recovered text</summary>"
            f"<pre>{raw_text or '-'}</pre>"
            "</details>"
            "</div>"
        )
    if not item_cards:
        item_cards.append("<p class='muted'>No OCR text was recovered from the supplied image sources.</p>")

    failure_html = ""
    if failures:
        failure_html = (
            "<h4>Failures</h4><ul>"
            + "".join(
                f"<li>{html.escape(str(row.get('source', 'image')))} "
                f"[{html.escape(str(row.get('source_kind', '-')))}] "
                f"{html.escape(str(row.get('error', '-')))}</li>"
                for row in failures[:20]
            )
            + "</ul>"
        )

    return (
        "<section class='panel' id='ocr-scan'>"
        "<h3>OCR Image Scan</h3>"
        f"<p><strong>Images:</strong> {html.escape(str(summary.get('image_count', 0)))} | "
        f"<strong>Processed:</strong> {html.escape(str(summary.get('processed_count', 0)))} | "
        f"<strong>Failed:</strong> {html.escape(str(summary.get('failed_count', 0)))} | "
        f"<strong>OCR Hits:</strong> {html.escape(str(summary.get('ocr_hits', 0)))}</p>"
        f"<p><strong>Engines:</strong> {html.escape(str(summary.get('engines', {})))} | "
        f"<strong>Languages:</strong> {html.escape(str(summary.get('languages', {})))}</p>"
        f"<p><strong>Signal Totals:</strong> {html.escape(str(summary.get('signal_totals', {})))}</p>"
        f"{''.join(item_cards)}"
        f"{failure_html}"
        "</section>"
    )


def _count_statuses(rows: list[dict]) -> dict[str, int]:
    counts = {"FOUND": 0, "ERROR": 0, "BLOCKED": 0, "NOT FOUND": 0, "OTHER": 0}
    for row in rows:
        status = str(row.get("status", "OTHER")).strip().upper() or "OTHER"
        if status not in counts:
            status = "OTHER"
        counts[status] += 1
    return counts


def _severity_badge(severity: str) -> str:
    color_map = {
        "CRITICAL": "#ff6b7d",
        "HIGH": "#ff8a3d",
        "MEDIUM": "#ffb454",
        "LOW": "#87d6a6",
        "INFO": "#70b9ff",
    }
    normalized = str(severity or "INFO").strip().upper() or "INFO"
    color = color_map.get(normalized, "#70b9ff")
    return (
        "<span class='severity-pill' "
        f"style='background:{html.escape(color)}22;border-color:{html.escape(color)}66;color:{html.escape(color)};'>{html.escape(normalized)}</span>"
    )


def _bar_row(label: str, value: int, maximum: int, tone: str, hint: str = "") -> str:
    width = 0.0 if maximum <= 0 or value <= 0 else max(8.0, min(100.0, (value / maximum) * 100.0))
    hint_html = f"<span class='bar-hint'>{html.escape(hint)}</span>" if hint else ""
    return (
        "<div class='bar-row'>"
        "<div class='bar-meta'>"
        f"<span class='bar-label'>{html.escape(label)}</span>"
        f"<span class='bar-value'>{html.escape(str(value))}</span>"
        "</div>"
        "<div class='bar-track'>"
        f"<span class='bar-fill {html.escape(tone)}' style='width:{width:.1f}%;'></span>"
        "</div>"
        f"{hint_html}"
        "</div>"
    )


def _render_graph_cluster(
    results: list[dict],
    issues: list[dict[str, str]],
    plugin_results: list[dict],
    filter_results: list[dict],
    intelligence_bundle: dict,
    ocr_scan: dict,
) -> str:
    status_counts = _count_statuses(results)
    issue_breakdown = _severity_breakdown(_safe_dict_rows(issues))
    plugin_breakdown = _severity_breakdown(_safe_dict_rows(plugin_results))
    filter_breakdown = _severity_breakdown(_safe_dict_rows(filter_results))
    confidence_distribution = (
        intelligence_bundle.get("confidence_distribution", {})
        if isinstance(intelligence_bundle.get("confidence_distribution"), dict)
        else {}
    )
    ocr_summary = ocr_scan.get("summary", {}) if isinstance(ocr_scan.get("summary"), dict) else {}

    result_max = max(sum(status_counts.values()), 1)
    severity_max = max(max(issue_breakdown.values(), default=0), 1)
    extension_max = max(
        max(plugin_breakdown.values(), default=0),
        max(filter_breakdown.values(), default=0),
        1,
    )
    confidence_max = max(
        int(confidence_distribution.get("high", 0) or 0),
        int(confidence_distribution.get("medium", 0) or 0),
        int(confidence_distribution.get("low", 0) or 0),
        1,
    )
    ocr_max = max(
        int(ocr_summary.get("image_count", 0) or 0),
        int(ocr_summary.get("processed_count", 0) or 0),
        int(ocr_summary.get("ocr_hits", 0) or 0),
        1,
    )

    ocr_card = ""
    if ocr_scan:
        ocr_card = (
            "<article class='subpanel graph-card'>"
            "<h4>OCR scan throughput</h4>"
            f"{_bar_row('Images supplied', int(ocr_summary.get('image_count', 0) or 0), ocr_max, 'tone-info')}"
            f"{_bar_row('Processed', int(ocr_summary.get('processed_count', 0) or 0), ocr_max, 'tone-positive')}"
            f"{_bar_row('OCR hits', int(ocr_summary.get('ocr_hits', 0) or 0), ocr_max, 'tone-warn')}"
            f"{_bar_row('Failures', int(ocr_summary.get('failed_count', 0) or 0), ocr_max, 'tone-critical')}"
            "</article>"
        )

    return (
        "<section class='panel' id='graphs'>"
        "<div class='section-banner'>"
        "<div>"
        "<div class='section-eyebrow'>Operational graphs</div>"
        "<h3>Run shape, vulnerabilities, and signal pressure</h3>"
        "</div>"
        "<p class='muted'>Reporter surfaces the current case shape with simple visual bars so an operator can understand coverage and pressure before reading raw tables.</p>"
        "</div>"
        "<div class='graph-grid'>"
        "<article class='subpanel graph-card'>"
        "<h4>Result coverage</h4>"
        f"{_bar_row('Found', status_counts.get('FOUND', 0), result_max, 'tone-positive', 'profiles confirmed')}"
        f"{_bar_row('Errors', status_counts.get('ERROR', 0), result_max, 'tone-critical', 'request or parsing failures')}"
        f"{_bar_row('Blocked', status_counts.get('BLOCKED', 0), result_max, 'tone-warn', 'access friction')}"
        f"{_bar_row('Not found', status_counts.get('NOT FOUND', 0), result_max, 'tone-neutral', 'negative coverage')}"
        "</article>"
        "<article class='subpanel graph-card'>"
        "<h4>Vulnerability severity</h4>"
        f"{_bar_row('Critical', issue_breakdown.get('CRITICAL', 0), severity_max, 'tone-critical')}"
        f"{_bar_row('High', issue_breakdown.get('HIGH', 0), severity_max, 'tone-high')}"
        f"{_bar_row('Medium', issue_breakdown.get('MEDIUM', 0), severity_max, 'tone-warn')}"
        f"{_bar_row('Low', issue_breakdown.get('LOW', 0), severity_max, 'tone-positive')}"
        f"{_bar_row('Info', issue_breakdown.get('INFO', 0), severity_max, 'tone-info')}"
        "</article>"
        "<article class='subpanel graph-card'>"
        "<h4>Extension pressure</h4>"
        f"{_bar_row('Plugin high+', plugin_breakdown.get('CRITICAL', 0) + plugin_breakdown.get('HIGH', 0), extension_max, 'tone-high')}"
        f"{_bar_row('Filter high+', filter_breakdown.get('CRITICAL', 0) + filter_breakdown.get('HIGH', 0), extension_max, 'tone-high')}"
        f"{_bar_row('Plugin medium', plugin_breakdown.get('MEDIUM', 0), extension_max, 'tone-warn')}"
        f"{_bar_row('Filter medium', filter_breakdown.get('MEDIUM', 0), extension_max, 'tone-warn')}"
        f"{_bar_row('Plugin info', plugin_breakdown.get('INFO', 0), extension_max, 'tone-info')}"
        "</article>"
        "<article class='subpanel graph-card'>"
        "<h4>Confidence mix</h4>"
        f"{_bar_row('High confidence', int(confidence_distribution.get('high', 0) or 0), confidence_max, 'tone-positive')}"
        f"{_bar_row('Medium confidence', int(confidence_distribution.get('medium', 0) or 0), confidence_max, 'tone-warn')}"
        f"{_bar_row('Low confidence', int(confidence_distribution.get('low', 0) or 0), confidence_max, 'tone-critical')}"
        "</article>"
        f"{ocr_card}"
        "</div>"
        "</section>"
    )


def _build_reporter_facts(
    *,
    mode: str,
    snapshot: dict,
    issue_summary: dict,
    domain_result: dict | None,
    intelligence_bundle: dict,
    ocr_scan: dict,
) -> list[str]:
    facts = [
        f"Mode {mode.upper()} reviewed {snapshot.get('found_count', 0)} confirmed profiles and {snapshot.get('error_count', 0)} unstable or blocked results.",
        f"Coverage ratio currently sits at {snapshot.get('coverage_ratio', 0)} with average found confidence at {snapshot.get('avg_found_confidence', 0)}.",
        f"Risk score is {issue_summary.get('risk_score', 0)} based on the current exposure and vulnerability findings.",
    ]
    if isinstance(domain_result, dict) and domain_result:
        surface_map = domain_result.get("surface_map", {}) if isinstance(domain_result.get("surface_map"), dict) else {}
        facts.append(
            "Surface intelligence tracked "
            f"{len(domain_result.get('subdomains', []) or [])} subdomain candidates and "
            f"attack surface score {surface_map.get('attack_surface_score', 0)}."
        )
    if isinstance(intelligence_bundle, dict) and intelligence_bundle:
        metadata = intelligence_bundle.get("metadata", {}) if isinstance(intelligence_bundle.get("metadata"), dict) else {}
        facts.append(
            "Fusion scoring mapped "
            f"{metadata.get('entity_count', 0)} entities and {metadata.get('evidence_count', 0)} evidence items into the case graph."
        )
    if isinstance(ocr_scan, dict) and ocr_scan:
        summary = ocr_scan.get("summary", {}) if isinstance(ocr_scan.get("summary"), dict) else {}
        facts.append(
            "OCR processed "
            f"{summary.get('processed_count', 0)} media inputs with {summary.get('ocr_hits', 0)} text-positive hits."
        )
    return facts


def _render_reporter_brief(
    *,
    mode: str,
    narrative: str | None,
    snapshot: dict,
    issue_summary: dict,
    domain_result: dict | None,
    intelligence_bundle: dict,
    ocr_scan: dict,
) -> str:
    facts = "".join(
        f"<li>{html.escape(item)}</li>"
        for item in _build_reporter_facts(
            mode=mode,
            snapshot=snapshot,
            issue_summary=issue_summary,
            domain_result=domain_result,
            intelligence_bundle=intelligence_bundle,
            ocr_scan=ocr_scan,
        )
    )
    summary_text = narrative or (
        "Reporter did not receive a narrative string for this run, so this closing brief reflects the structured telemetry captured across results, vulnerabilities, extensions, and intelligence scoring."
    )
    return (
        "<section class='panel reporter-panel' id='reporter'>"
        "<div class='section-banner'>"
        "<div>"
        "<div class='section-eyebrow'>Reporter</div>"
        "<h3>Reporter Brief</h3>"
        "</div>"
        "<span class='panel-chip'>Case closeout</span>"
        "</div>"
        f"<div class='brief'>{html.escape(summary_text)}</div>"
        "<div class='subpanel section-block'>"
        "<h4>Case summary</h4>"
        f"<ul>{facts}</ul>"
        "</div>"
        "</section>"
    )


def generate_html(
    target: str,
    results: list[dict] | None,
    correlation: dict | None,
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
    intelligence_bundle: dict | None = None,
    ocr_scan: dict | None = None,
    output_stamp: str | None = None,
) -> str:
    results = results or []
    correlation = correlation or {}
    issues = issues or []
    issue_summary = issue_summary or {}
    plugin_results = plugin_results or []
    plugin_errors = plugin_errors or []
    filter_results = filter_results or []
    filter_errors = filter_errors or []
    intelligence_bundle = intelligence_bundle or {}
    ocr_scan = ocr_scan or {}

    display_target = str(target or "").strip()
    target_display = display_target or sanitize_target(target)
    target_key = sanitize_target(target_display)

    found_rows = found_profile_rows(results)
    error_rows = error_profile_rows(results)
    focus_rows = focused_profile_rows(results)
    snapshot = summarize_target_intel(results)
    issue_breakdown = _severity_breakdown(_safe_dict_rows(issues))
    plugin_breakdown = _severity_breakdown(_safe_dict_rows(plugin_results))
    filter_breakdown = _severity_breakdown(_safe_dict_rows(filter_results))
    confidence_distribution = (
        intelligence_bundle.get("confidence_distribution", {})
        if isinstance(intelligence_bundle.get("confidence_distribution"), dict)
        else {}
    )

    overlap_score = correlation.get("identity_overlap_score", 0)
    metrics_html = "".join(
        [
            _metric_card("Mode", mode.upper(), "workflow"),
            _metric_card("Target", target_display or target_key, "entity"),
            _metric_card("Platforms Checked", str(len(results)), "total websites queried"),
            _metric_card("Found Profiles", str(len(found_rows)), "confirmed social profiles"),
            _metric_card("Errors/Blocked", str(len(error_rows)), "sites requiring retry"),
            _metric_card("Visible Rows", str(len(focus_rows)), "found + error rows"),
            _metric_card("Overlap Score", str(overlap_score), "identity correlation"),
            _metric_card("Risk Score", str(issue_summary.get("risk_score", 0)), "exposure signal"),
        ]
    )
    triage_chips = "".join(
        [
            f"<span class='panel-chip'>{html.escape(mode.upper())} case</span>",
            f"<span class='panel-chip'>issues {html.escape(str(len(issues)))}</span>",
            f"<span class='panel-chip'>plugins {html.escape(str(len(plugin_results)))}</span>",
            f"<span class='panel-chip'>filters {html.escape(str(len(filter_results)))}</span>",
            f"<span class='panel-chip'>ocr {'active' if ocr_scan else 'idle'}</span>",
        ]
    )
    exposure_level = "HIGH" if (issue_breakdown.get("CRITICAL", 0) or issue_breakdown.get("HIGH", 0)) else "INFO"

    report_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{html.escape(PROJECT_NAME)} Reporter v{html.escape(VERSION)} - {html.escape(target_display or target_key)}</title>
      <style>
        :root {{
          --bg:#120904;
          --panel:#211109;
          --panel-2:#2d170b;
          --panel-3:#371d0f;
          --text:#fff4ea;
          --muted:#dcbca3;
          --accent:#ff8a3d;
          --accent-2:#ffb454;
          --accent-3:#ffd28c;
          --info:#70b9ff;
          --positive:#87d6a6;
          --warn:#ffcf73;
          --critical:#ff6b7d;
          --line:#7e4b28;
          --shadow:0 22px 60px rgba(0, 0, 0, 0.45);
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: "Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif;
          color: var(--text);
          background:
            radial-gradient(circle at 10% -10%, rgba(255,138,61,0.26) 0%, rgba(255,138,61,0) 34%),
            radial-gradient(circle at 100% 0%, rgba(255,180,84,0.18) 0%, rgba(255,180,84,0) 32%),
            linear-gradient(145deg, #120904 0%, #1a0f08 44%, #120904 100%);
          min-height: 100vh;
          padding: 22px;
        }}
        .shell {{ max-width: 1360px; margin: 0 auto; }}
        .header {{
          background:
            linear-gradient(145deg, rgba(255,138,61,0.20), rgba(255,177,94,0.08)),
            linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
          border: 1px solid var(--line);
          border-radius: 22px;
          padding: 24px 24px 20px;
          margin-bottom: 18px;
          box-shadow: var(--shadow);
          backdrop-filter: blur(6px);
        }}
        .header-top {{
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: flex-start;
          flex-wrap: wrap;
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 2rem; letter-spacing: -0.02em; }}
        .header-lead {{ max-width: 820px; }}
        .header-copy {{
          color: var(--muted);
          margin: 8px 0 0;
          line-height: 1.55;
        }}
        .header-pills {{
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          justify-content: flex-end;
          max-width: 380px;
        }}
        .quick-nav {{
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 16px 0 14px;
        }}
        .quick-nav a {{
          border: 1px solid var(--line);
          border-radius: 999px;
          padding: 6px 12px;
          background: rgba(255,255,255,0.03);
          color: var(--text);
          font-size: 0.82rem;
          text-decoration: none;
          transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
        }}
        .quick-nav a:hover {{
          border-color: var(--accent-2);
          transform: translateY(-1px);
          background: rgba(255,255,255,0.06);
        }}
        .muted {{ color: var(--muted); }}
        .metrics {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          gap: 12px;
          margin-bottom: 16px;
        }}
        .metric-card {{
          background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015));
          border: 1px solid var(--line);
          border-radius: 16px;
          padding: 14px 14px 12px;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }}
        .metric-label {{
          color: var(--muted);
          font-size: 0.76rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }}
        .metric-value {{ font-size: 1.42rem; font-weight: 800; margin-top: 4px; }}
        .metric-hint {{ color: var(--muted); font-size: 0.78rem; margin-top: 4px; }}
        .panel {{
          background: linear-gradient(180deg, rgba(43,24,13,0.92), rgba(28,16,10,0.98));
          border: 1px solid var(--line);
          border-radius: 18px;
          padding: 16px;
          margin-bottom: 16px;
          box-shadow: var(--shadow);
        }}
        .reporter-panel {{
          border-color: rgba(255, 180, 84, 0.45);
          box-shadow: 0 22px 70px rgba(255, 138, 61, 0.14), var(--shadow);
        }}
        .section-banner {{
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: flex-start;
          margin-bottom: 12px;
          flex-wrap: wrap;
        }}
        .section-eyebrow {{
          color: var(--accent-3);
          font-size: 0.76rem;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          margin-bottom: 6px;
        }}
        .subpanel {{
          background: linear-gradient(180deg, rgba(255,255,255,0.032), rgba(255,255,255,0.015));
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 14px;
          padding: 12px 14px;
          margin-bottom: 12px;
        }}
        .badge {{
          display: inline-block;
          padding: 4px 10px;
          border-radius: 999px;
          color: #0d1117;
          font-weight: 700;
          letter-spacing: 0.03em;
        }}
        .badge-inline {{
          background: rgba(255,177,94,0.16);
          border: 1px solid rgba(255,177,94,0.4);
          color: var(--text);
          margin-left: 8px;
          padding: 2px 8px;
          font-size: 0.74rem;
          vertical-align: middle;
        }}
        .severity-pill {{
          display: inline-flex;
          align-items: center;
          padding: 4px 10px;
          border-radius: 999px;
          border: 1px solid transparent;
          font-size: 0.76rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }}
        .triage-grid {{
          display: grid;
          grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.95fr);
          gap: 16px;
        }}
        .panel-chip {{
          display: inline-flex;
          align-items: center;
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(255, 180, 84, 0.12);
          border: 1px solid rgba(255, 180, 84, 0.24);
          color: var(--text);
          font-size: 0.8rem;
          margin: 0 8px 8px 0;
        }}
        .summary-stack {{
          display: grid;
          gap: 10px;
        }}
        .summary-row {{
          display: flex;
          justify-content: space-between;
          gap: 14px;
          padding: 10px 12px;
          border-radius: 12px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
        }}
        .summary-row strong {{ font-size: 1rem; }}
        .graph-grid {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 14px;
        }}
        .graph-card h4 {{ margin-top: 0; margin-bottom: 12px; }}
        .bar-row {{ margin-bottom: 12px; }}
        .bar-meta {{
          display: flex;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 6px;
          font-size: 0.85rem;
        }}
        .bar-label {{ color: var(--muted); }}
        .bar-value {{ color: var(--text); font-weight: 700; }}
        .bar-track {{
          width: 100%;
          height: 10px;
          border-radius: 999px;
          background: rgba(255,255,255,0.08);
          overflow: hidden;
        }}
        .bar-fill {{
          display: block;
          height: 100%;
          border-radius: 999px;
        }}
        .tone-positive {{ background: linear-gradient(90deg, #5fc48e, #87d6a6); }}
        .tone-critical {{ background: linear-gradient(90deg, #ff5473, #ff7f7b); }}
        .tone-high {{ background: linear-gradient(90deg, #ff7f3f, #ffb454); }}
        .tone-warn {{ background: linear-gradient(90deg, #e8a847, #ffd068); }}
        .tone-info {{ background: linear-gradient(90deg, #4e9df0, #70b9ff); }}
        .tone-neutral {{ background: linear-gradient(90deg, #7b8590, #9ca7b3); }}
        .bar-hint {{
          display: block;
          color: var(--muted);
          font-size: 0.75rem;
          margin-top: 5px;
        }}
        .chip-group {{ margin-top: 12px; }}
        .chip-group h4 {{ margin: 0 0 6px 0; }}
        .chip {{
          display: inline-block;
          border: 1px solid rgba(255,255,255,0.16);
          border-radius: 999px;
          padding: 4px 9px;
          margin: 4px 6px 0 0;
          font-size: 0.82rem;
          background: rgba(255,255,255,0.03);
          color: var(--text);
        }}
        .chip-muted {{ color: var(--muted); }}
        .table-wrap {{ overflow-x: auto; border-radius: 10px; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 980px; }}
        th, td {{
          border-bottom: 1px solid var(--line);
          padding: 9px;
          text-align: left;
          vertical-align: top;
          font-size: 0.92rem;
        }}
        th {{
          color: #ffd7b0;
          background: rgba(255,255,255,0.03);
          position: sticky;
          top: 0;
        }}
        a {{ color: var(--accent-2); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        ul {{ padding-left: 20px; }}
        details {{
          margin-top: 8px;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 10px;
          padding: 6px 8px;
          background: rgba(7,11,18,0.30);
        }}
        summary {{
          cursor: pointer;
          color: #ffd2a1;
          font-weight: 600;
        }}
        pre {{
          white-space: pre-wrap;
          word-break: break-word;
          max-height: 240px;
          overflow: auto;
          background: rgba(0, 0, 0, 0.35);
          border: 1px solid rgba(255,255,255,0.12);
          border-radius: 8px;
          padding: 8px;
          color: #ffe1c3;
          font-size: 0.8rem;
        }}
        .brief {{
          background: rgba(255,138,61,0.10);
          border: 1px solid rgba(255,138,61,0.38);
          border-left: 4px solid var(--accent);
          border-radius: 12px;
          padding: 12px 14px;
          line-height: 1.6;
        }}
        .section-block {{ margin-top: 12px; }}
        footer {{ margin-top: 16px; color: var(--muted); font-size: 0.84rem; }}
        @media (max-width: 760px) {{
          body {{ padding: 12px; }}
          .header h1 {{ font-size: 1.45rem; }}
          .triage-grid {{ grid-template-columns: 1fr; }}
          table {{ min-width: 760px; }}
        }}
      </style>
    </head>
    <body>
      <div class="shell">
        <div class="header">
          <div class="header-top">
            <div class="header-lead">
              <h1>{html.escape(PROJECT_NAME)} Reporter v{html.escape(VERSION)}</h1>
              <div class="muted"><strong>Target:</strong> {html.escape(target_display or target_key)} |
              <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
              <strong>Framework:</strong> {html.escape(framework_signature())}</div>
              <p class="header-copy">Reporter is the v10.0 case-view layer for Silica-X. It reshapes raw results into triage-friendly sections, categorized vulnerability context, extension drill-downs, and an operator-ready closing summary.</p>
            </div>
            <div class="header-pills">{triage_chips}</div>
          </div>
        </div>

        <div class="quick-nav">
          <a href="#overview">Overview</a>
          <a href="#graphs">Graphs</a>
          <a href="#profiles">Profiles</a>
          <a href="#errors">Errors</a>
          <a href="#correlation">Correlation</a>
          <a href="#exposure">Exposure</a>
          {"<a href='#ocr-scan'>OCR Scan</a>" if ocr_scan else ""}
          <a href="#plugins">Plugins</a>
          <a href="#filters">Filters</a>
          <a href="#intelligence">Intelligence</a>
          <a href="#reporter">Reporter</a>
        </div>

        <div class="metrics">{metrics_html}</div>

        <section class="panel" id="overview">
          <div class="section-banner">
            <div>
              <div class="section-eyebrow">Overview</div>
              <h3>Case triage snapshot</h3>
            </div>
            <span class="panel-chip">Ember report theme</span>
          </div>
          <div class="triage-grid">
            <div>{_render_target_snapshot(target_display or target_key, snapshot, len(results))}</div>
            <div class="summary-stack">
              <div class="summary-row"><span>Issue severity</span><strong>{html.escape(str(issue_breakdown))}</strong></div>
              <div class="summary-row"><span>Plugin severity</span><strong>{html.escape(str(plugin_breakdown))}</strong></div>
              <div class="summary-row"><span>Filter severity</span><strong>{html.escape(str(filter_breakdown))}</strong></div>
              <div class="summary-row"><span>Confidence mix</span><strong>high={html.escape(str(confidence_distribution.get('high', 0)))} medium={html.escape(str(confidence_distribution.get('medium', 0)))} low={html.escape(str(confidence_distribution.get('low', 0)))}</strong></div>
            </div>
          </div>
        </section>

        {_render_extension_overview(issues, issue_summary, plugin_results, plugin_errors, filter_results, filter_errors)}
        {_render_graph_cluster(results, issues, plugin_results, filter_results, intelligence_bundle, ocr_scan)}

        <section class="panel" id="profiles">
          <div class="section-banner">
            <div>
              <div class="section-eyebrow">Identity lane</div>
              <h3>Found Social Media Profiles</h3>
            </div>
            <span class="panel-chip">{html.escape(str(len(found_rows)))} found</span>
          </div>
          <div class="table-wrap">
            <table>
              <tr>
                <th>Platform</th><th>Confidence</th><th>Profile Link</th><th>Emails</th><th>Phones</th>
                <th>Mentions</th><th>Extracted Links</th><th>Bio</th><th>Context</th>
              </tr>
              {_render_found_profile_table(found_rows)}
            </table>
          </div>
        </section>

        <section class="panel" id="errors">
          <div class="section-banner">
            <div>
              <div class="section-eyebrow">Reliability</div>
              <h3>Errored / Blocked Websites</h3>
            </div>
            <span class="panel-chip">{html.escape(str(len(error_rows)))} unstable rows</span>
          </div>
          <div class="table-wrap">
            <table>
              <tr><th>Platform</th><th>Status</th><th>Profile Link</th><th>HTTP</th><th>RTT (ms)</th><th>Reason</th></tr>
              {_render_error_table(error_rows)}
            </table>
          </div>
        </section>

        <section class="panel" id="correlation">
          <div class="section-banner">
            <div>
              <div class="section-eyebrow">Correlation</div>
              <h3>Correlation Engine</h3>
            </div>
            <span class="panel-chip">overlap {html.escape(str(overlap_score))}</span>
          </div>
          {_render_correlation(correlation)}
        </section>

        {_render_domain_section(domain_result)}

        <section class="panel" id="exposure">
          <div class="section-banner">
            <div>
              <div class="section-eyebrow">Vulnerabilities</div>
              <h3>Exposure & Vulnerability Signals</h3>
            </div>
            {_severity_badge(exposure_level)}
          </div>
          {_render_issues(issues, issue_summary)}
        </section>

        {_render_ocr_scan(ocr_scan)}

        <section class="panel" id="plugins">
          <div class="section-banner">
            <div>
              <div class="section-eyebrow">Extensions</div>
              <h3>Plugin Intelligence</h3>
            </div>
            <span class="panel-chip">{html.escape(str(len(plugin_results)))} plugin results</span>
          </div>
          {_render_plugins(plugin_results, plugin_errors)}
        </section>

        <section class="panel" id="filters">
          <div class="section-banner">
            <div>
              <div class="section-eyebrow">Extensions</div>
              <h3>Filter Intelligence</h3>
            </div>
            <span class="panel-chip">{html.escape(str(len(filter_results)))} filter results</span>
          </div>
          {_render_filters(filter_results, filter_errors)}
        </section>

        <section class="panel" id="intelligence">
          <div class="section-banner">
            <div>
              <div class="section-eyebrow">Scoring</div>
              <h3>Intelligence Scoring & Guidance</h3>
            </div>
            <span class="panel-chip">fusion-ready</span>
          </div>
          {_render_intelligence_bundle(intelligence_bundle)}
        </section>

        {_render_reporter_brief(
            mode=mode,
            narrative=narrative,
            snapshot=snapshot,
            issue_summary=issue_summary,
            domain_result=domain_result,
            intelligence_bundle=intelligence_bundle,
            ocr_scan=ocr_scan,
        )}

        <footer>
          Generated by {html.escape(PROJECT_NAME)} Reporter v{html.escape(VERSION)} |
          Developed by {html.escape(AUTHOR)}
        </footer>
      </div>
    </body>
    </html>
    """

    try:
        ensure_output_tree(types={"html"})
    except OutputConfigError as exc:
        raise RuntimeError(f"Unable to prepare HTML output directory: {exc}") from exc
    report_file = html_report_path(target_key, stamp=output_stamp)
    report_file.write_text(report_html, encoding="utf-8")
    return str(report_file)
