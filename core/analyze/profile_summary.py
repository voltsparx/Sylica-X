"""Shared helpers for profile result filtering and target aggregation."""

from __future__ import annotations


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


def summarize_target_intel(results: list[dict]) -> dict:
    found_rows = found_profile_rows(results)
    error_rows = error_profile_rows(results)

    found_platforms: set[str] = set()
    profile_links: set[str] = set()
    emails: set[str] = set()
    phones: set[str] = set()
    mentions: set[str] = set()
    external_links: set[str] = set()
    bios: set[str] = set()

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

        bio = str(row.get("bio") or "").strip()
        if bio:
            bios.add(bio)

    error_details: list[dict] = []
    for row in error_rows:
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

    return {
        "found_count": len(found_rows),
        "error_count": len(error_rows),
        "found_platforms": sorted(found_platforms),
        "profile_links": sorted(profile_links),
        "emails": sorted(emails),
        "phones": sorted(phones),
        "mentions": sorted(mentions),
        "external_links": sorted(external_links),
        "bios": sorted(bios),
        "errors": error_details,
    }
