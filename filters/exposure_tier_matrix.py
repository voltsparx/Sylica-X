"""Filter: exposure tier matrix for profile and surface artifacts."""

from __future__ import annotations

from collections import Counter


FILTER_SPEC = {
    "id": "exposure_tier_matrix",
    "title": "Exposure Tier Matrix",
    "description": "Assigns low/medium/high exposure tiers based on extracted artifacts and findings.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["exposure_tier_filter", "tier", "exposure"],
    "version": "1.1",
}


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    issues = context.get("issues", []) or []
    domain_result = context.get("domain_result") or {}

    tiers: Counter = Counter()
    for item in results:
        if item.get("status") != "FOUND":
            continue
        contact_count = len(item.get("contacts", {}).get("emails", [])) + len(
            item.get("contacts", {}).get("phones", [])
        )
        link_count = len(item.get("links", []))
        confidence = int(item.get("confidence", 0) or 0)
        score = confidence + (contact_count * 10) + (link_count * 3)
        if score >= 95:
            tiers["high"] += 1
        elif score >= 55:
            tiers["medium"] += 1
        else:
            tiers["low"] += 1

    if domain_result:
        subdomains = len(domain_result.get("subdomains", []) or [])
        if subdomains >= 150:
            tiers["high"] += 1
        elif subdomains >= 50:
            tiers["medium"] += 1
        elif subdomains > 0:
            tiers["low"] += 1

    issue_high = sum(1 for issue in issues if str(issue.get("severity", "")).upper() in {"HIGH", "CRITICAL"})
    issue_medium = sum(1 for issue in issues if str(issue.get("severity", "")).upper() == "MEDIUM")
    if issue_high:
        tiers["high"] += issue_high
    if issue_medium:
        tiers["medium"] += issue_medium

    dominant = "low"
    if tiers["high"] >= max(tiers["medium"], tiers["low"]):
        dominant = "high"
    elif tiers["medium"] >= max(tiers["high"], tiers["low"]):
        dominant = "medium"

    severity = "HIGH" if dominant == "high" else "MEDIUM" if dominant == "medium" else "INFO"
    return {
        "severity": severity,
        "summary": f"Exposure tiering complete with dominant tier '{dominant}'.",
        "highlights": [f"{tier}={count}" for tier, count in tiers.items()],
        "data": {
            "tier_distribution": dict(tiers),
            "dominant_tier": dominant,
        },
    }
