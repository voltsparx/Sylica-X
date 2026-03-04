"""Shared helpers for profile result filtering and target aggregation."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse


FOCUS_STATUSES = ("FOUND", "ERROR", "BLOCKED")
ERROR_STATUSES = ("ERROR", "BLOCKED")


def focused_profile_rows(results: list[dict]) -> list[dict]:
    return [row for row in results if row.get("status") in FOCUS_STATUSES]


def found_profile_rows(results: list[dict]) -> list[dict]:
    rows = [row for row in results if row.get("status") == "FOUND"]
    return sorted(rows, key=lambda item: (-int(item.get("confidence", 0) or 0), str(item.get("platform", ""))))


def error_profile_rows(results: list[dict]) -> list[dict]:
    rows = [row for row in results if row.get("status") in ERROR_STATUSES]
    return sorted(rows, key=lambda item: (str(item.get("platform", "")), str(item.get("status", ""))))


def _extract_domain(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except ValueError:
        return ""
    host = (parsed.netloc or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def summarize_target_intel(results: list[dict]) -> dict:
    found_rows = found_profile_rows(results)
    error_rows = error_profile_rows(results)
    status_breakdown: Counter[str] = Counter(str(row.get("status", "UNKNOWN")) for row in results)

    found_platforms: set[str] = set()
    profile_links: set[str] = set()
    emails: set[str] = set()
    phones: set[str] = set()
    mentions: set[str] = set()
    external_links: set[str] = set()
    bios: set[str] = set()
    email_domains: Counter[str] = Counter()
    link_domains: Counter[str] = Counter()
    found_response_times: list[int] = []
    error_response_times: list[int] = []
    found_confidences: list[int] = []

    for row in found_rows:
        platform = str(row.get("platform") or "").strip()
        if platform:
            found_platforms.add(platform)

        profile_url = str(row.get("url") or "").strip()
        if profile_url:
            profile_links.add(profile_url)

        contacts = row.get("contacts", {}) or {}
        for email in contacts.get("emails", []) or []:
            value = str(email).strip()
            if value:
                emails.add(value)
                if "@" in value:
                    email_domain = value.rsplit("@", 1)[-1].strip().lower()
                    if email_domain:
                        email_domains[email_domain] += 1

        for phone in contacts.get("phones", []) or []:
            value = str(phone).strip()
            if value:
                phones.add(value)

        for mention in row.get("mentions", []) or []:
            value = str(mention).strip()
            if value:
                mentions.add(value)

        for link in row.get("links", []) or []:
            value = str(link).strip()
            if value:
                external_links.add(value)
                link_domain = _extract_domain(value)
                if link_domain:
                    link_domains[link_domain] += 1

        bio = str(row.get("bio") or "").strip()
        if bio:
            bios.add(bio)

        response_time = row.get("response_time_ms")
        if isinstance(response_time, int) and response_time > 0:
            found_response_times.append(response_time)

        confidence = row.get("confidence")
        if isinstance(confidence, int):
            found_confidences.append(confidence)

    error_details: list[dict] = []
    for row in error_rows:
        response_time = row.get("response_time_ms")
        if isinstance(response_time, int) and response_time > 0:
            error_response_times.append(response_time)
        error_details.append(
            {
                "platform": str(row.get("platform", "Unknown")),
                "status": str(row.get("status", "ERROR")),
                "url": str(row.get("url", "")),
                "http_status": row.get("http_status"),
                "response_time_ms": row.get("response_time_ms"),
                "context": str(row.get("context") or ""),
            }
        )

    total_results = len(results)
    found_count = len(found_rows)
    error_count = len(error_rows)
    coverage_ratio = round(found_count / float(total_results), 4) if total_results else 0.0
    avg_found_confidence = round(sum(found_confidences) / float(len(found_confidences)), 2) if found_confidences else 0.0
    avg_found_rtt = round(sum(found_response_times) / float(len(found_response_times)), 2) if found_response_times else 0.0
    avg_error_rtt = round(sum(error_response_times) / float(len(error_response_times)), 2) if error_response_times else 0.0

    return {
        "total_results": total_results,
        "found_count": found_count,
        "error_count": error_count,
        "coverage_ratio": coverage_ratio,
        "avg_found_confidence": avg_found_confidence,
        "avg_found_response_time_ms": avg_found_rtt,
        "avg_error_response_time_ms": avg_error_rtt,
        "status_breakdown": dict(sorted(status_breakdown.items(), key=lambda item: item[0])),
        "found_platforms": sorted(found_platforms),
        "profile_links": sorted(profile_links),
        "emails": sorted(emails),
        "email_domains": [f"{name}:{count}" for name, count in email_domains.most_common(10)],
        "phones": sorted(phones),
        "mentions": sorted(mentions),
        "external_links": sorted(external_links),
        "external_link_domains": [f"{name}:{count}" for name, count in link_domains.most_common(12)],
        "bios": sorted(bios),
        "errors": error_details,
    }
