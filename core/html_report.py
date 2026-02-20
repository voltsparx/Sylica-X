"""HTML report generation for Silica-X."""

from __future__ import annotations

import html
from datetime import datetime

from core.metadata import AUTHOR, PROJECT_NAME, VERSION, framework_signature
from core.storage import ensure_output_tree, html_report_path, sanitize_target


def _status_badge(status: str) -> str:
    color_map = {
        "FOUND": "#1db954",
        "NOT FOUND": "#8a8f98",
        "BLOCKED": "#f39c12",
        "INVALID_USERNAME": "#f1c40f",
        "ERROR": "#e74c3c",
    }
    color = color_map.get(status, "#8a8f98")
    return (
        f'<span style="display:inline-block;padding:4px 8px;border-radius:999px;'
        f'font-weight:700;background:{color};color:#0f1115;">{html.escape(status)}</span>'
    )


def _metric_card(label: str, value: str, hint: str = "") -> str:
    return (
        "<div class='metric-card'>"
        f"<div class='metric-label'>{html.escape(label)}</div>"
        f"<div class='metric-value'>{html.escape(value)}</div>"
        f"<div class='metric-hint'>{html.escape(hint)}</div>"
        "</div>"
    )


def _render_profile_table(results: list[dict]) -> str:
    rows: list[str] = []
    for item in sorted(
        results,
        key=lambda row: (row.get("status") != "FOUND", -int(row.get("confidence", 0) or 0)),
    ):
        contacts = item.get("contacts", {})
        links = item.get("links", [])
        profile_url = html.escape(item.get("url", ""))
        account_link = f"<a href='{profile_url}' target='_blank' rel='noreferrer'>{profile_url}</a>"
        extracted_links = "<br>".join(
            f"<a href='{html.escape(link)}' target='_blank' rel='noreferrer'>{html.escape(link)}</a>"
            for link in links[:6]
        )
        if not extracted_links:
            extracted_links = "-"
        bio = html.escape(item.get("bio") or "-").replace("\n", "<br>")
        context = html.escape(item.get("context") or "-")
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.get('platform', 'Unknown'))}</td>"
            f"<td>{_status_badge(item.get('status', 'UNKNOWN'))}</td>"
            f"<td>{int(item.get('confidence', 0) or 0)}%</td>"
            f"<td>{account_link}</td>"
            f"<td>{html.escape(', '.join(contacts.get('emails', [])) or '-')}</td>"
            f"<td>{html.escape(', '.join(contacts.get('phones', [])) or '-')}</td>"
            f"<td>{extracted_links}</td>"
            f"<td>{bio}</td>"
            f"<td>{context}</td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='9'>No profile rows captured.</td></tr>"


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
        "<table>"
        "<tr><th>Severity</th><th>Scope</th><th>Title</th><th>Evidence</th><th>Recommendation</th></tr>"
        f"{''.join(rows)}"
        "</table>"
    )


def _render_plugins(plugin_results: list[dict], plugin_errors: list[str]) -> str:
    if not plugin_results and not plugin_errors:
        return "<p class='muted'>No plugins were executed for this run.</p>"

    cards = []
    for plugin in plugin_results:
        highlights = plugin.get("highlights", []) or []
        highlight_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in highlights[:8]) or "<li>None</li>"
        cards.append(
            "<div class='panel' style='margin-bottom:10px;'>"
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
            "<div class='panel' style='margin-bottom:10px;'>"
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


def _render_personal_info_snapshot(results: list[dict], filter_results: list[dict]) -> str:
    email_count = 0
    phone_count = 0
    mention_count = 0
    external_link_count = 0
    for row in results:
        contacts = row.get("contacts", {}) or {}
        email_count += len(contacts.get("emails", []) or [])
        phone_count += len(contacts.get("phones", []) or [])
        mention_count += len(row.get("mentions", []) or [])
        external_link_count += len(row.get("links", []) or [])

    pii_summary = ""
    for row in filter_results:
        if row.get("id") == "pii_signal_classifier":
            pii_summary = row.get("summary", "")
            break

    auto_text = (
        f"Nano AI analysis observed {email_count} email artifact(s), {phone_count} phone artifact(s), "
        f"{mention_count} mention artifact(s), and {external_link_count} extracted external link(s). "
        "This summary is auto-refreshed for each run as the personal-information surface changes."
    )
    if pii_summary:
        auto_text = f"{auto_text} Filter insight: {pii_summary}"
    return f"<p>{html.escape(auto_text)}</p>"


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

    target_key = sanitize_target(target)
    found_count = sum(1 for item in results if item.get("status") == "FOUND")
    blocked_count = sum(1 for item in results if item.get("status") == "BLOCKED")
    overlap_score = correlation.get("identity_overlap_score", 0)

    metrics_html = "".join(
        [
            _metric_card("Mode", mode.upper(), "workflow"),
            _metric_card("Target", target_key, "primary entity"),
            _metric_card("Profiles Found", str(found_count), "public profile detections"),
            _metric_card("Blocked", str(blocked_count), "anti-bot indicators"),
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
      <title>{html.escape(PROJECT_NAME)} v{html.escape(VERSION)} Report - {html.escape(target_key)}</title>
      <style>
        :root {{
          --bg:#090f15;
          --panel:#121d29;
          --panel-2:#1a2a39;
          --text:#e7edf5;
          --muted:#97a8ba;
          --accent:#26c281;
          --accent-2:#57a2ff;
          --line:#304458;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin:0;
          font-family: "Segoe UI", "Trebuchet MS", sans-serif;
          background:
            radial-gradient(circle at 85% -10%, rgba(87,162,255,0.22) 0%, rgba(87,162,255,0) 32%),
            radial-gradient(circle at -10% 10%, rgba(38,194,129,0.18) 0%, rgba(38,194,129,0) 35%),
            var(--bg);
          color: var(--text);
          padding: 26px;
        }}
        .header {{
          background: linear-gradient(120deg, rgba(38,194,129,0.16), rgba(87,162,255,0.12));
          border:1px solid var(--line);
          border-radius: 18px;
          padding: 18px 20px;
          margin-bottom: 18px;
        }}
        .header h1 {{ margin:0 0 8px 0; font-size: 1.6rem; }}
        .muted {{ color: var(--muted); }}
        .metrics {{
          display:grid;
          grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          gap: 12px;
          margin-bottom: 18px;
        }}
        .metric-card {{
          background: var(--panel);
          border:1px solid var(--line);
          border-radius: 14px;
          padding: 12px;
        }}
        .metric-label {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; }}
        .metric-value {{ font-size: 1.35rem; font-weight: 800; margin-top: 5px; }}
        .metric-hint {{ color: var(--muted); font-size: 0.8rem; margin-top: 4px; }}
        .panel {{
          background: var(--panel-2);
          border:1px solid var(--line);
          border-radius: 14px;
          padding: 14px;
          margin-bottom: 16px;
          overflow-x:auto;
        }}
        table {{ width:100%; border-collapse: collapse; min-width: 920px; }}
        th, td {{ border-bottom: 1px solid var(--line); padding: 10px; text-align:left; vertical-align: top; }}
        th {{ color: #b9cbe0; background: rgba(255,255,255,0.02); }}
        a {{ color: var(--accent-2); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        ul {{ padding-left: 20px; }}
        footer {{ margin-top: 18px; color: var(--muted); font-size: 0.84rem; }}
        .brief {{
          background: rgba(38,194,129,0.08);
          border-left: 4px solid var(--accent);
          padding: 10px 12px;
          border-radius: 8px;
        }}
      </style>
    </head>
    <body>
      <div class="header">
        <h1>{html.escape(PROJECT_NAME)} v{html.escape(VERSION)} Intelligence Report</h1>
        <div class="muted"><strong>Target:</strong> {html.escape(target_key)} |
        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
        <strong>Framework:</strong> {html.escape(framework_signature())}</div>
      </div>

      <div class="metrics">{metrics_html}</div>

      <section class="panel">
        <h3>Profile & Account Intelligence</h3>
        <table>
          <tr>
            <th>Platform</th><th>Status</th><th>Confidence</th><th>Profile Link</th>
            <th>Emails</th><th>Phones</th><th>Extracted Links</th><th>Bio</th><th>Context</th>
          </tr>
          {_render_profile_table(results)}
        </table>
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
        <h3>Personal Information Synopsis</h3>
        {_render_personal_info_snapshot(results, filter_results)}
      </section>

      <section class="panel">
        <h3>Nano AI Narrative</h3>
        <div class="brief">{html.escape(narrative or 'No narrative generated for this run.')}</div>
      </section>

      <footer>
        Generated by {html.escape(PROJECT_NAME)} v{html.escape(VERSION)} |
        Developed by {html.escape(AUTHOR)}
      </footer>
    </body>
    </html>
    """

    ensure_output_tree()
    report_file = html_report_path(target_key)
    report_file.write_text(report_html, encoding="utf-8")
    return str(report_file)
