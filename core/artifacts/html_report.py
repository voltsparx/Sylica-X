"""HTML report generation for Silica-X."""

from __future__ import annotations

import html
from datetime import datetime

from core.foundation.metadata import AUTHOR, PROJECT_NAME, VERSION, framework_signature
from core.analyze.profile_summary import (
    error_profile_rows,
    focused_profile_rows,
    found_profile_rows,
    summarize_target_intel,
)
from core.artifacts.storage import ensure_output_tree, html_report_path, sanitize_target


def _status_badge(status: str) -> str:
    color_map = {
        "FOUND": "#20d981",
        "NOT FOUND": "#8a8f98",
        "BLOCKED": "#f5b949",
        "INVALID_USERNAME": "#f5b949",
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

    return (
        "<section class='panel'>"
        "<h3>Domain Surface Intelligence</h3>"
        f"<p><strong>Target:</strong> {html.escape(domain_result.get('target', ''))}</p>"
        f"<p><strong>Resolved Addresses:</strong> {html.escape(', '.join(domain_result.get('resolved_addresses', [])) or 'None')}</p>"
        f"<p><strong>HTTPS:</strong> status={html.escape(str(https_data.get('status')))} "
        f"final={html.escape(str(https_data.get('final_url')))}</p>"
        f"<p><strong>HTTP:</strong> status={html.escape(str(http_data.get('status')))} "
        f"final={html.escape(str(http_data.get('final_url')))} "
        f"redirects_to_https={html.escape(str(http_data.get('redirects_to_https')))}</p>"
        f"<p><strong>RDAP Handle:</strong> {html.escape(str(rdap.get('handle') or '-'))}</p>"
        "<h4>Subdomain Candidates</h4>"
        f"<ul>{subdomain_items}</ul>"
        "<h4>Collector Notes</h4>"
        f"<ul>{notes}</ul>"
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
    for plugin in plugin_results:
        highlights = plugin.get("highlights", []) or []
        highlight_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in highlights[:8]) or "<li>None</li>"
        cards.append(
            "<div class='subpanel'>"
            f"<h4>{html.escape(plugin.get('title', plugin.get('id', 'Plugin')))} "
            f"<span class='muted'>[{html.escape(str(plugin.get('severity', 'INFO')).upper())}]</span></h4>"
            f"<p>{html.escape(plugin.get('summary', ''))}</p>"
            "<ul>"
            f"{highlight_html}"
            "</ul>"
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
    for row in filter_results:
        highlights = row.get("highlights", []) or []
        highlight_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in highlights[:8]) or "<li>None</li>"
        cards.append(
            "<div class='subpanel'>"
            f"<h4>{html.escape(row.get('title', row.get('id', 'Filter')))} "
            f"<span class='muted'>[{html.escape(str(row.get('severity', 'INFO')).upper())}]</span></h4>"
            f"<p>{html.escape(row.get('summary', ''))}</p>"
            "<ul>"
            f"{highlight_html}"
            "</ul>"
            "</div>"
        )

    if filter_errors:
        err = "".join(f"<li>{html.escape(str(item))}</li>" for item in filter_errors)
        cards.append(f"<h4>Filter Errors</h4><ul>{err}</ul>")
    return "".join(cards)


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
) -> str:
    results = results or []
    correlation = correlation or {}
    issues = issues or []
    issue_summary = issue_summary or {}
    plugin_results = plugin_results or []
    plugin_errors = plugin_errors or []
    filter_results = filter_results or []
    filter_errors = filter_errors or []

    display_target = str(target or "").strip()
    target_display = display_target or sanitize_target(target)
    target_key = sanitize_target(target_display)

    found_rows = found_profile_rows(results)
    error_rows = error_profile_rows(results)
    focus_rows = focused_profile_rows(results)
    snapshot = summarize_target_intel(results)

    overlap_score = correlation.get("identity_overlap_score", 0)
    metrics_html = "".join(
        [
            _metric_card("Mode", mode.upper(), "workflow"),
            _metric_card("Target", target_display, "entity"),
            _metric_card("Platforms Checked", str(len(results)), "total websites queried"),
            _metric_card("Found Profiles", str(len(found_rows)), "confirmed social profiles"),
            _metric_card("Errors/Blocked", str(len(error_rows)), "sites requiring retry"),
            _metric_card("Visible Rows", str(len(focus_rows)), "found + error rows"),
            _metric_card("Overlap Score", str(overlap_score), "identity correlation"),
            _metric_card("Risk Score", str(issue_summary.get("risk_score", 0)), "exposure signal"),
        ]
    )

    report_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{html.escape(PROJECT_NAME)} v{html.escape(VERSION)} Report - {html.escape(target_display)}</title>
      <style>
        :root {{
          --bg:#070b12;
          --panel:#101927;
          --panel-2:#162438;
          --text:#edf3fb;
          --muted:#a0b0c2;
          --accent:#27d89a;
          --accent-2:#5ea9ff;
          --line:#2c4258;
          --shadow:0 14px 40px rgba(0, 0, 0, 0.42);
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin:0;
          font-family: "Avenir Next", "Trebuchet MS", "Segoe UI", sans-serif;
          color: var(--text);
          background:
            radial-gradient(circle at 12% -6%, rgba(39,216,154,0.24) 0%, rgba(39,216,154,0) 35%),
            radial-gradient(circle at 88% -15%, rgba(94,169,255,0.24) 0%, rgba(94,169,255,0) 40%),
            linear-gradient(145deg, #070b12 0%, #0a111a 45%, #070b12 100%);
          min-height: 100vh;
          padding: 20px;
        }}
        .shell {{ max-width: 1300px; margin: 0 auto; }}
        .header {{
          background: linear-gradient(130deg, rgba(39,216,154,0.17), rgba(94,169,255,0.14));
          border: 1px solid var(--line);
          border-radius: 18px;
          padding: 20px 22px;
          margin-bottom: 16px;
          box-shadow: var(--shadow);
          backdrop-filter: blur(6px);
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 1.75rem; }}
        .muted {{ color: var(--muted); }}
        .metrics {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          gap: 12px;
          margin-bottom: 16px;
        }}
        .metric-card {{
          background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 12px;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }}
        .metric-label {{
          color: var(--muted);
          font-size: 0.76rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }}
        .metric-value {{ font-size: 1.34rem; font-weight: 800; margin-top: 4px; }}
        .metric-hint {{ color: var(--muted); font-size: 0.78rem; margin-top: 4px; }}
        .panel {{
          background: linear-gradient(180deg, rgba(18,31,48,0.88), rgba(16,25,39,0.95));
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 14px;
          margin-bottom: 14px;
          box-shadow: var(--shadow);
        }}
        .subpanel {{
          background: rgba(255,255,255,0.02);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 10px;
          padding: 10px 12px;
          margin-bottom: 10px;
        }}
        .badge {{
          display: inline-block;
          padding: 4px 10px;
          border-radius: 999px;
          color: #0d1117;
          font-weight: 700;
          letter-spacing: 0.03em;
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
          color: #c4d3e4;
          background: rgba(255,255,255,0.03);
          position: sticky;
          top: 0;
        }}
        a {{ color: var(--accent-2); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        ul {{ padding-left: 20px; }}
        .brief {{
          background: rgba(39,216,154,0.09);
          border: 1px solid rgba(39,216,154,0.38);
          border-left: 4px solid var(--accent);
          border-radius: 8px;
          padding: 10px 12px;
        }}
        footer {{ margin-top: 16px; color: var(--muted); font-size: 0.84rem; }}
        @media (max-width: 760px) {{
          body {{ padding: 12px; }}
          .header h1 {{ font-size: 1.35rem; }}
          table {{ min-width: 760px; }}
        }}
      </style>
    </head>
    <body>
      <div class="shell">
        <div class="header">
          <h1>{html.escape(PROJECT_NAME)} v{html.escape(VERSION)} Intelligence Report</h1>
          <div class="muted"><strong>Target:</strong> {html.escape(target_display)} |
          <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
          <strong>Framework:</strong> {html.escape(framework_signature())}</div>
        </div>

        <div class="metrics">{metrics_html}</div>

        {_render_target_snapshot(target_display, snapshot, len(results))}

        <section class="panel">
          <h3>Found Social Media Profiles</h3>
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

        <section class="panel">
          <h3>Errored / Blocked Websites</h3>
          <div class="table-wrap">
            <table>
              <tr><th>Platform</th><th>Status</th><th>Profile Link</th><th>HTTP</th><th>RTT (ms)</th><th>Reason</th></tr>
              {_render_error_table(error_rows)}
            </table>
          </div>
        </section>

        <section class="panel">
          <h3>Correlation Engine</h3>
          {_render_correlation(correlation)}
        </section>

        {_render_domain_section(domain_result)}

        <section class="panel">
          <h3>Exposure & Vulnerability Signals</h3>
          {_render_issues(issues, issue_summary)}
        </section>

        <section class="panel">
          <h3>Plugin Intelligence</h3>
          {_render_plugins(plugin_results, plugin_errors)}
        </section>

        <section class="panel">
          <h3>Filter Intelligence</h3>
          {_render_filters(filter_results, filter_errors)}
        </section>

        <section class="panel">
          <h3>Nano AI Narrative</h3>
          <div class="brief">{html.escape(narrative or 'No narrative generated for this run.')}</div>
        </section>

        <footer>
          Generated by {html.escape(PROJECT_NAME)} v{html.escape(VERSION)} |
          Developed by {html.escape(AUTHOR)}
        </footer>
      </div>
    </body>
    </html>
    """

    ensure_output_tree()
    report_file = html_report_path(target_key)
    report_file.write_text(report_html, encoding="utf-8")
    return str(report_file)

