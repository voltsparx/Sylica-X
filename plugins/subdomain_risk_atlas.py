"""Plugin: subdomain risk atlas and environment mapping."""

from __future__ import annotations

from collections import defaultdict


PLUGIN_SPEC = {
    "id": "subdomain_risk_atlas",
    "title": "Subdomain Risk Atlas",
    "description": "Classifies discovered subdomains by environment and high-risk naming patterns.",
    "scopes": ["surface", "fusion"],
    "aliases": ["subdomain_exposure_map", "subdomainmap", "subrisk"],
    "version": "1.1",
}


KEYWORD_GROUPS = {
    "development": ("dev", "stage", "staging", "uat", "test", "qa"),
    "administrative": ("admin", "portal", "manage", "internal"),
    "service": ("api", "auth", "cdn", "edge", "mail"),
    "legacy": ("old", "legacy", "backup", "bak", "archive"),
}


def run(context: dict) -> dict:
    domain_result = context.get("domain_result") or {}
    subdomains = list(domain_result.get("subdomains", []) or [])

    buckets: dict[str, list[str]] = defaultdict(list)
    for subdomain in subdomains:
        lower = str(subdomain).lower()
        matched = False
        for bucket, tokens in KEYWORD_GROUPS.items():
            if any(token in lower for token in tokens):
                buckets[bucket].append(subdomain)
                matched = True
        if not matched:
            buckets["general"].append(subdomain)

    high_risk_count = len(buckets["development"]) + len(buckets["legacy"]) + len(buckets["administrative"])
    severity = "HIGH" if high_risk_count >= 20 else "MEDIUM" if high_risk_count >= 8 else "INFO"
    map_score = min(100, (len(subdomains) // 2) + (high_risk_count * 2))

    highlights = [
        f"subdomains={len(subdomains)}",
        f"high_risk_named={high_risk_count}",
        f"map_score={map_score}",
    ]
    summary = (
        f"Subdomain exposure map processed {len(subdomains)} entries; "
        f"{high_risk_count} include high-risk environment naming patterns."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights,
        "data": {
            "bucket_counts": {bucket: len(values) for bucket, values in buckets.items()},
            "buckets": {bucket: sorted(set(values)) for bucket, values in buckets.items()},
            "map_score": map_score,
        },
    }
