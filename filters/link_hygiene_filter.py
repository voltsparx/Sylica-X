"""Filter: prioritize risky links for analyst review."""

from __future__ import annotations

from urllib.parse import urlparse


FILTER_SPEC = {
    "id": "link_hygiene_filter",
    "title": "Link Hygiene Filter",
    "description": "Flags non-HTTPS, shortener, and suspicious-query links to tighten outbound intelligence hygiene.",
    "scopes": ["profile", "fusion"],
    "aliases": ["link_hygiene", "url_hygiene", "link_risk_filter"],
    "version": "1.0",
}


SHORTENER_DOMAINS = {
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "goo.gl",
    "buff.ly",
    "cutt.ly",
    "is.gd",
    "ow.ly",
}


def _host(link: str) -> str:
    value = urlparse(link).netloc.lower().strip()
    if value.startswith("www."):
        return value[4:]
    return value


def _plugin_row(context: dict, plugin_id: str) -> dict | None:
    for row in context.get("plugins", []) or []:
        if str(row.get("id", "")).strip().lower() == plugin_id:
            return row
    return None


def run(context: dict) -> dict:
    plugin = _plugin_row(context, "link_outbound_risk_profiler")
    risky_from_plugin: list[str] = []
    if plugin:
        data = plugin.get("data", {}) or {}
        risky_from_plugin.extend(str(item) for item in (data.get("shortener_links", []) or []))
        risky_from_plugin.extend(str(item) for item in (data.get("non_https_links", []) or []))
        risky_from_plugin.extend(str(item) for item in (data.get("sensitive_links", []) or []))

    collected_links: list[str] = []
    for row in context.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).upper() != "FOUND":
            continue
        for link in row.get("links", []) or []:
            token = str(link).strip()
            if token:
                collected_links.append(token)

    unique_links = sorted(set(collected_links))
    risky_links = set(str(item).strip() for item in risky_from_plugin if str(item).strip())
    for link in unique_links:
        parsed = urlparse(link)
        if parsed.scheme.lower() != "https":
            risky_links.add(link)
            continue
        host = _host(link)
        if host in SHORTENER_DOMAINS:
            risky_links.add(link)
            continue
        if len(parsed.query) > 90:
            risky_links.add(link)

    risky_sorted = sorted(risky_links)
    risk_score = min(100, (len(risky_sorted) * 12) + (len([item for item in risky_sorted if item.startswith("http://")]) * 6))
    severity = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 25 else "INFO"
    summary = (
        f"Link hygiene flagged {len(risky_sorted)} risky link(s) out of {len(unique_links)} observed, "
        f"risk_score={risk_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"total_links={len(unique_links)}",
            f"risky_links={len(risky_sorted)}",
            f"http_links={len([item for item in risky_sorted if item.startswith('http://')])}",
            f"risk_score={risk_score}",
        ],
        "data": {
            "total_links": len(unique_links),
            "risky_links": risky_sorted[:180],
            "safe_link_count": max(0, len(unique_links) - len(risky_sorted)),
            "risk_score": risk_score,
        },
    }
