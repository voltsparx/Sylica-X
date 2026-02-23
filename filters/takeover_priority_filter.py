"""Filter: prioritize likely subdomain takeover exposures."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "takeover_priority_filter",
    "title": "Takeover Priority Filter",
    "description": "Prioritizes takeover-prone assets so analysts can triage high-impact surface risk first.",
    "scopes": ["surface", "fusion"],
    "aliases": ["takeover_priority", "subtakeover", "takeover"],
    "version": "1.0",
}


def _plugin_row(context: dict, plugin_id: str) -> dict | None:
    for row in context.get("plugins", []) or []:
        if str(row.get("id") or "").strip().lower() == plugin_id:
            return row
    return None


def run(context: dict) -> dict:
    plugin = _plugin_row(context, "domain_takeover_risk_probe")
    domain_result = context.get("domain_result") or {}

    high_candidates: list[str] = []
    medium_candidates: list[str] = []
    takeover_score = 0
    if plugin:
        data = plugin.get("data", {}) or {}
        high_candidates = [str(item) for item in (data.get("high_risk_candidates") or [])]
        medium_candidates = [str(item) for item in (data.get("medium_risk_candidates") or [])]
        takeover_score = int(data.get("takeover_risk_score", 0) or 0)

    if not high_candidates and not medium_candidates:
        subdomains = [str(item) for item in (domain_result.get("subdomains", []) or [])]
        token_matches = [item for item in subdomains if any(key in item for key in ("cdn", "app", "blog", "help", "status"))]
        medium_candidates = token_matches[:15]
        takeover_score = min(100, len(medium_candidates) * 6)

    priority = "high" if takeover_score >= 55 else "medium" if takeover_score >= 25 else "low"
    severity = "HIGH" if priority == "high" else "MEDIUM" if priority == "medium" else "INFO"
    summary = (
        f"Potential takeover triage marked priority='{priority}' "
        f"(high_candidates={len(high_candidates)}, medium_candidates={len(medium_candidates)}, score={takeover_score})."
    )

    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"priority={priority}",
            f"score={takeover_score}",
            f"high={len(high_candidates)}",
            f"medium={len(medium_candidates)}",
            "Potential Takeover Risk section generated.",
        ],
        "data": {
            "priority": priority,
            "takeover_risk_score": takeover_score,
            "high_candidates": high_candidates,
            "medium_candidates": medium_candidates,
        },
    }
