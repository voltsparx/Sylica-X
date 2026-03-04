"""Filter: prioritize subdomains that represent likely attack paths."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "subdomain_attack_path_filter",
    "title": "Subdomain Attack Path Filter",
    "description": "Ranks discovered subdomains by attack-path relevance for remediation triage.",
    "scopes": ["surface", "fusion"],
    "aliases": ["attack_path_filter", "subdomain_priority", "surface_priority"],
    "version": "1.0",
}


HIGH_PRIORITY_TOKENS = ("admin", "auth", "sso", "vpn", "portal", "api", "gateway", "bastion")
MEDIUM_PRIORITY_TOKENS = ("dev", "test", "stage", "staging", "uat", "legacy", "old", "debug")


def _plugin_row(context: dict, plugin_id: str) -> dict | None:
    for row in context.get("plugins", []) or []:
        if str(row.get("id", "")).strip().lower() == plugin_id:
            return row
    return None


def run(context: dict) -> dict:
    domain_result = context.get("domain_result", {}) or {}
    subdomains = [str(item).strip().lower() for item in (domain_result.get("subdomains", []) or []) if str(item).strip()]

    high_priority: set[str] = set()
    medium_priority: set[str] = set()
    for host in subdomains:
        if any(token in host for token in HIGH_PRIORITY_TOKENS):
            high_priority.add(host)
            continue
        if any(token in host for token in MEDIUM_PRIORITY_TOKENS):
            medium_priority.add(host)

    takeover = _plugin_row(context, "domain_takeover_risk_probe")
    takeover_high: list[str] = []
    if takeover:
        data = takeover.get("data", {}) or {}
        takeover_high = [str(item).strip().lower() for item in (data.get("high_risk_candidates", []) or []) if str(item).strip()]
        for host in takeover_high:
            high_priority.add(host)

    ranked = sorted(high_priority) + sorted(medium_priority - high_priority)
    score = min(100, (len(high_priority) * 12) + (len(medium_priority) * 4))
    severity = "HIGH" if score >= 60 else "MEDIUM" if score >= 25 else "INFO"
    summary = (
        f"Attack-path triage prioritized {len(high_priority)} high and {len(medium_priority)} medium "
        f"subdomain candidate(s), score={score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"subdomains={len(subdomains)}",
            f"high_priority={len(high_priority)}",
            f"medium_priority={len(medium_priority)}",
            f"takeover_high={len(takeover_high)}",
            f"score={score}",
        ],
        "data": {
            "high_priority_subdomains": sorted(high_priority)[:160],
            "medium_priority_subdomains": sorted(medium_priority)[:160],
            "ranked_subdomain_queue": ranked[:200],
            "score": score,
        },
    }

