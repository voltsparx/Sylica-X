"""Plugin: classify outbound links for operational and phishing risk."""

from __future__ import annotations

from urllib.parse import urlparse


PLUGIN_SPEC = {
    "id": "link_outbound_risk_profiler",
    "title": "Link Outbound Risk Profiler",
    "description": "Classifies discovered outbound links by trust, transport security, and suspicious sharing patterns.",
    "scopes": ["profile", "fusion"],
    "aliases": ["link_risk", "outbound_links", "url_risk"],
    "version": "1.0",
}


SHORTENER_DOMAINS = {
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "goo.gl",
    "buff.ly",
    "cutt.ly",
    "rebrand.ly",
    "is.gd",
    "ow.ly",
}
FILE_SHARE_DOMAINS = {
    "drive.google.com",
    "dropbox.com",
    "dropboxusercontent.com",
    "mega.nz",
    "wetransfer.com",
    "mediafire.com",
    "onedrive.live.com",
}
SENSITIVE_TOKENS = ("reset", "recover", "auth", "login", "token", "verify", "invite")


def _netloc(host: str) -> str:
    lowered = str(host or "").strip().lower()
    if lowered.startswith("www."):
        return lowered[4:]
    return lowered


def run(context: dict) -> dict:
    raw_results = context.get("results", []) or []
    results = [row for row in raw_results if isinstance(row, dict)]
    links: list[str] = []
    for row in results:
        if str(row.get("status", "")).upper() != "FOUND":
            continue
        for value in row.get("links", []) or []:
            token = str(value).strip()
            if token:
                links.append(token)

    unique_links = sorted(set(links))
    shortener_links: list[str] = []
    file_share_links: list[str] = []
    non_https_links: list[str] = []
    sensitive_links: list[str] = []

    for link in unique_links:
        parsed = urlparse(link)
        host = _netloc(parsed.netloc)
        full = f"{parsed.path}?{parsed.query}".lower()

        if parsed.scheme.lower() != "https":
            non_https_links.append(link)
        if host in SHORTENER_DOMAINS:
            shortener_links.append(link)
        if host in FILE_SHARE_DOMAINS:
            file_share_links.append(link)
        if any(token in full for token in SENSITIVE_TOKENS):
            sensitive_links.append(link)

    risk_score = min(
        100,
        (len(shortener_links) * 15)
        + (len(non_https_links) * 8)
        + (len(sensitive_links) * 6)
        + (len(file_share_links) * 4),
    )
    severity = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 30 else "INFO"

    summary = (
        f"Outbound link profiling reviewed {len(unique_links)} unique link(s); "
        f"shorteners={len(shortener_links)}, non_https={len(non_https_links)}, "
        f"sensitive_paths={len(sensitive_links)}, score={risk_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"unique_links={len(unique_links)}",
            f"shorteners={len(shortener_links)}",
            f"non_https={len(non_https_links)}",
            f"sensitive_paths={len(sensitive_links)}",
            f"file_sharing={len(file_share_links)}",
            f"risk_score={risk_score}",
        ],
        "data": {
            "unique_links": unique_links[:250],
            "shortener_links": shortener_links[:120],
            "file_sharing_links": file_share_links[:120],
            "non_https_links": non_https_links[:120],
            "sensitive_links": sensitive_links[:120],
            "risk_score": risk_score,
        },
    }
