"""Plugin: contact lattice exposure analytics."""

from __future__ import annotations

import re
from collections import defaultdict


PLUGIN_SPEC = {
    "id": "contact_lattice",
    "title": "Contact Lattice Analyzer",
    "description": "Correlates exposed emails/phones across platforms and calculates contact mesh density.",
    "scopes": ["profile", "fusion"],
    "aliases": ["contact_mesh", "contacts", "mesh"],
    "version": "1.1",
}


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if not digits:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


def run(context: dict) -> dict:
    results = context.get("results", []) or []

    email_platforms: dict[str, list[str]] = defaultdict(list)
    phone_platforms: dict[str, list[str]] = defaultdict(list)
    for item in results:
        if item.get("status") != "FOUND":
            continue
        platform = item.get("platform", "Unknown")
        contacts = item.get("contacts", {})
        for email in contacts.get("emails", []):
            normalized = str(email).strip().lower()
            if normalized:
                email_platforms[normalized].append(platform)
        for phone in contacts.get("phones", []):
            normalized = _normalize_phone(str(phone))
            if normalized:
                phone_platforms[normalized].append(platform)

    shared_emails = {
        key: sorted(set(values)) for key, values in email_platforms.items() if len(set(values)) > 1
    }
    shared_phones = {
        key: sorted(set(values)) for key, values in phone_platforms.items() if len(set(values)) > 1
    }

    total_email_nodes = len(email_platforms)
    total_phone_nodes = len(phone_platforms)
    mesh_density = min(100, (len(shared_emails) * 10) + (len(shared_phones) * 15))

    unique_platforms = len(
        {platform for values in email_platforms.values() for platform in values}
        | {platform for values in phone_platforms.values() for platform in values}
    )
    highlights = [
        f"email_nodes={total_email_nodes}",
        f"phone_nodes={total_phone_nodes}",
        f"platform_nodes={unique_platforms}",
        f"mesh_density={mesh_density}",
    ]
    severity = "HIGH" if mesh_density >= 70 else "MEDIUM" if mesh_density >= 35 else "INFO"
    summary = (
        f"Built contact mesh with {total_email_nodes} email nodes and {total_phone_nodes} phone nodes; "
        f"cross-platform reuse detected in {len(shared_emails)} email and {len(shared_phones)} phone artifacts."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights,
        "data": {
            "shared_emails": shared_emails,
            "shared_phones": shared_phones,
            "mesh_density": mesh_density,
        },
    }
