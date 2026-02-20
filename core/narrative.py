"""Small adaptive narrative generator for scan summaries."""

from __future__ import annotations

from typing import Iterable


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _severity_breakdown(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, int] = {}
    for key, raw_count in value.items():
        key_str = str(key).upper()
        normalized[key_str] = _safe_int(raw_count, 0)
    return normalized


def _severity_headline(severity_breakdown: dict[str, int]) -> str:
    if not severity_breakdown:
        return "No explicit risk indicators were triggered"
    if severity_breakdown.get("CRITICAL", 0) > 0:
        return "Critical findings were identified"
    if severity_breakdown.get("HIGH", 0) > 0:
        return "High-severity findings were identified"
    if severity_breakdown.get("MEDIUM", 0) > 0:
        return "Moderate risk findings were identified"
    return "Only low-severity findings were identified"


def _plural(value: int, singular: str, plural: str | None = None) -> str:
    if value == 1:
        return singular
    return plural if plural is not None else f"{singular}s"


def build_nano_brief(
    *,
    username: str | None = None,
    profile_results: list[dict] | None = None,
    domain: str | None = None,
    domain_result: dict | None = None,
    issues: Iterable[dict[str, str]] = (),
    issue_summary: dict[str, object] | None = None,
    correlation: dict | None = None,
) -> str:
    profile_results = profile_results or []
    issue_summary = issue_summary or {}
    correlation = correlation or {}

    found_profiles = sum(1 for item in profile_results if item.get("status") == "FOUND")
    blocked_profiles = sum(1 for item in profile_results if item.get("status") == "BLOCKED")
    total_profiles = len(profile_results)
    shared_emails = len((correlation.get("shared_emails") or {}).keys())
    shared_phones = len((correlation.get("shared_phones") or {}).keys())
    shared_bios = len((correlation.get("shared_bios") or {}).keys())

    severity_breakdown = _severity_breakdown(issue_summary.get("severity_breakdown", {}))
    risk_score = _safe_int(issue_summary.get("risk_score", 0), 0)
    total_issues = _safe_int(issue_summary.get("total", 0), 0)

    subject = username or domain or "target"
    lines: list[str] = []

    if profile_results:
        lines.append(
            f"For {subject}, {found_profiles} of {total_profiles} profile checks resolved as FOUND"
            f" with {blocked_profiles} blocked responses."
        )

    if domain_result:
        subdomain_count = len(domain_result.get("subdomains", []))
        address_count = len(domain_result.get("resolved_addresses", []))
        lines.append(
            f"Domain surface telemetry captured {subdomain_count} subdomain candidate"
            f" {_plural(subdomain_count, 'entry')} and {address_count} resolved"
            f" {_plural(address_count, 'address')}."
        )

    if shared_bios or shared_emails or shared_phones:
        lines.append(
            f"Correlation identified {shared_bios} shared bios, {shared_emails} shared emails,"
            f" and {shared_phones} shared phones across discovered assets."
        )

    if total_issues:
        lines.append(
            f"{_severity_headline(severity_breakdown)} across {total_issues}"
            f" {_plural(total_issues, 'issue')}; aggregate risk score is {risk_score}."
        )
    else:
        lines.append("No material exposure findings were produced by the current heuristic pass.")

    lines.append(
        "This narrative is auto-generated per run and updates as new scan artifacts alter"
        " confidence, exposure, and correlation signals."
    )
    return " ".join(lines)
