"""Exposure heuristics and lightweight risk scoring."""

from __future__ import annotations

from collections import Counter
from typing import Iterable


SEVERITY_WEIGHTS = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 5,
}


def _issue(
    *,
    scope: str,
    severity: str,
    title: str,
    evidence: str,
    recommendation: str,
) -> dict[str, str]:
    return {
        "scope": scope,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def assess_profile_exposure(results: list[dict]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    found_count = sum(1 for item in results if item.get("status") == "FOUND")
    blocked_count = sum(1 for item in results if item.get("status") == "BLOCKED")
    public_emails = sum(
        len(item.get("contacts", {}).get("emails", []))
        for item in results
        if item.get("status") == "FOUND"
    )
    public_phones = sum(
        len(item.get("contacts", {}).get("phones", []))
        for item in results
        if item.get("status") == "FOUND"
    )

    if found_count >= 10:
        issues.append(
            _issue(
                scope="identity",
                severity="MEDIUM",
                title="Large Public Account Footprint",
                evidence=f"{found_count} discoverable profiles were found.",
                recommendation="Review account privacy settings and consolidate identity hygiene.",
            )
        )

    if public_emails > 0:
        issues.append(
            _issue(
                scope="identity",
                severity="HIGH",
                title="Public Email Exposure",
                evidence=f"{public_emails} email artifact(s) were extracted from public pages.",
                recommendation="Rotate exposed addresses or use role-based/public-only aliases.",
            )
        )

    if public_phones > 0:
        issues.append(
            _issue(
                scope="identity",
                severity="HIGH",
                title="Public Phone Number Exposure",
                evidence=f"{public_phones} phone artifact(s) were extracted from public pages.",
                recommendation="Move sensitive phone numbers behind private channels.",
            )
        )

    if blocked_count > 0:
        issues.append(
            _issue(
                scope="collection",
                severity="LOW",
                title="Anti-Bot Countermeasures Observed",
                evidence=f"{blocked_count} platform checks returned blocking fingerprints.",
                recommendation="Use validated legal collection pathways and diversify request profiles.",
            )
        )

    return issues


def assess_domain_exposure(
    domain: str,
    https_headers: dict[str, str],
    http_redirects_to_https: bool,
    certificate_transparency_count: int,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    normalized_headers = {k.lower(): v for k, v in https_headers.items()}

    if not http_redirects_to_https:
        issues.append(
            _issue(
                scope=domain,
                severity="MEDIUM",
                title="HTTP Not Strictly Redirected",
                evidence="HTTP endpoint did not clearly redirect to HTTPS.",
                recommendation="Enforce full HTTP->HTTPS redirects at edge and app layers.",
            )
        )

    if "strict-transport-security" not in normalized_headers:
        issues.append(
            _issue(
                scope=domain,
                severity="HIGH",
                title="Missing HSTS Header",
                evidence="Strict-Transport-Security header not observed.",
                recommendation="Enable HSTS with an adequate max-age and includeSubDomains where appropriate.",
            )
        )

    if "content-security-policy" not in normalized_headers:
        issues.append(
            _issue(
                scope=domain,
                severity="MEDIUM",
                title="Missing Content-Security-Policy",
                evidence="Content-Security-Policy header not observed.",
                recommendation="Deploy a restrictive CSP and iterate in report-only mode first if needed.",
            )
        )

    if "x-frame-options" not in normalized_headers:
        issues.append(
            _issue(
                scope=domain,
                severity="MEDIUM",
                title="Missing X-Frame-Options",
                evidence="X-Frame-Options header not observed.",
                recommendation="Set X-Frame-Options to DENY or SAMEORIGIN.",
            )
        )

    server_banner = normalized_headers.get("server")
    if server_banner:
        issues.append(
            _issue(
                scope=domain,
                severity="LOW",
                title="Server Banner Disclosure",
                evidence=f"Server header exposed: {server_banner[:100]}",
                recommendation="Reduce banner detail at the reverse proxy/web server layer.",
            )
        )

    x_powered_by = normalized_headers.get("x-powered-by")
    if x_powered_by:
        issues.append(
            _issue(
                scope=domain,
                severity="LOW",
                title="Technology Banner Disclosure",
                evidence=f"X-Powered-By exposed: {x_powered_by[:100]}",
                recommendation="Disable X-Powered-By and related framework fingerprinting headers.",
            )
        )

    if certificate_transparency_count >= 100:
        issues.append(
            _issue(
                scope=domain,
                severity="MEDIUM",
                title="High Subdomain Attack Surface",
                evidence=f"{certificate_transparency_count} CT subdomain observations were collected.",
                recommendation="Continuously inventory and decommission stale or shadow subdomains.",
            )
        )

    return issues


def summarize_issues(issues: Iterable[dict[str, str]]) -> dict[str, object]:
    items = list(issues)
    counts = Counter(issue.get("severity", "LOW") for issue in items)
    score = sum(SEVERITY_WEIGHTS.get(issue.get("severity", "LOW"), 1) for issue in items)
    return {
        "total": len(items),
        "severity_breakdown": dict(counts),
        "risk_score": score,
    }
