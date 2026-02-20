"""Plugin: threat conductor risk orchestration."""

from __future__ import annotations

from collections import Counter


PLUGIN_SPEC = {
    "id": "threat_conductor",
    "title": "Threat Conductor",
    "description": "Combines correlation, issue distribution, and scan quality into an executive risk signal.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["risk_orchestrator", "risk", "orchestrator"],
    "version": "1.1",
}


SEVERITY_WEIGHTS = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 4,
    "CRITICAL": 7,
    "INFO": 0,
}


def run(context: dict) -> dict:
    issues = list(context.get("issues", []) or [])
    correlation = context.get("correlation", {}) or {}
    domain_result = context.get("domain_result") or {}
    results = list(context.get("results", []) or [])

    severity_counter: Counter = Counter(str(issue.get("severity", "LOW")).upper() for issue in issues)
    issue_weight = sum(SEVERITY_WEIGHTS.get(level, 1) * count for level, count in severity_counter.items())
    overlap = int(correlation.get("identity_overlap_score", 0) or 0)
    found_count = sum(1 for row in results if row.get("status") == "FOUND")
    blocked_count = sum(1 for row in results if row.get("status") == "BLOCKED")
    subdomain_count = len(domain_result.get("subdomains", []) or [])

    orchestration_score = min(
        100,
        issue_weight * 4
        + int(overlap * 0.45)
        + found_count * 2
        + min(20, subdomain_count // 12)
        + min(10, blocked_count * 2),
    )
    if orchestration_score >= 80:
        severity = "HIGH"
        stance = "Immediate risk review recommended."
    elif orchestration_score >= 50:
        severity = "MEDIUM"
        stance = "Escalate for analyst validation."
    else:
        severity = "INFO"
        stance = "Baseline risk posture with incremental follow-up."

    summary = (
        f"Orchestration score={orchestration_score} derived from issue_weight={issue_weight}, "
        f"identity_overlap={overlap}, found_profiles={found_count}, blocked_profiles={blocked_count}, "
        f"subdomains={subdomain_count}."
    )
    highlights = [
        f"score={orchestration_score}",
        f"issue_weight={issue_weight}",
        f"overlap={overlap}",
        f"blocked={blocked_count}",
        stance,
    ]
    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights,
        "data": {
            "orchestration_score": orchestration_score,
            "severity_distribution": dict(severity_counter),
            "recommended_stance": stance,
        },
    }
