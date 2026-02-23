"""Plugin: domain takeover risk probe via passive DNS health heuristics."""

from __future__ import annotations

import socket


PLUGIN_SPEC = {
    "id": "domain_takeover_risk_probe",
    "title": "Domain Takeover Risk Probe",
    "description": "Flags subdomains that look deprovisioned or dangling based on passive DNS resolution signals.",
    "scopes": ["surface"],
    "aliases": ["takeover_probe", "dangling_dns", "subtakeover"],
    "version": "1.0",
}


PROVIDER_TOKENS = (
    "github",
    "heroku",
    "azure",
    "s3",
    "cloudfront",
    "netlify",
    "vercel",
    "readthedocs",
    "zendesk",
    "fastly",
    "pantheon",
)
SUSPICIOUS_ROLE_TOKENS = ("cdn", "app", "static", "blog", "docs", "help", "status", "portal")
MAX_DNS_CHECKS = 80


def _resolves(host: str) -> bool:
    try:
        socket.getaddrinfo(host, None)
        return True
    except socket.gaierror:
        return False
    except OSError:
        return False


def _token_hit(value: str, tokens: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in tokens)


def run(context: dict) -> dict:
    domain_result = context.get("domain_result") or {}
    subdomains = [str(item).strip().lower() for item in (domain_result.get("subdomains", []) or []) if str(item).strip()]

    high_risk: list[str] = []
    medium_risk: list[str] = []
    resolved_count = 0
    unresolved_count = 0

    for host in subdomains[:MAX_DNS_CHECKS]:
        is_resolved = _resolves(host)
        if is_resolved:
            resolved_count += 1
            continue
        unresolved_count += 1

        if _token_hit(host, PROVIDER_TOKENS):
            high_risk.append(host)
            continue
        if _token_hit(host, SUSPICIOUS_ROLE_TOKENS):
            medium_risk.append(host)

    score = min(100, len(high_risk) * 35 + len(medium_risk) * 12 + (unresolved_count // 3))
    severity = "HIGH" if score >= 55 else "MEDIUM" if score >= 25 else "INFO"
    highlights = [
        f"checked={min(len(subdomains), MAX_DNS_CHECKS)}",
        f"resolved={resolved_count}",
        f"unresolved={unresolved_count}",
        f"high_risk={len(high_risk)}",
        f"score={score}",
    ]
    highlights.extend(high_risk[:5])

    summary = (
        f"Passive DNS health probe reviewed {min(len(subdomains), MAX_DNS_CHECKS)} subdomain(s); "
        f"{len(high_risk)} high-risk and {len(medium_risk)} medium-risk takeover candidate(s) were flagged. "
        "Dangling DNS records can allow attackers to claim this subdomain."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights,
        "data": {
            "checked_subdomains": min(len(subdomains), MAX_DNS_CHECKS),
            "resolved_count": resolved_count,
            "unresolved_count": unresolved_count,
            "high_risk_candidates": high_risk,
            "medium_risk_candidates": medium_risk,
            "takeover_risk_score": score,
            "method_note": "Passive resolution heuristic only; CNAME ownership validation not performed.",
        },
    }
