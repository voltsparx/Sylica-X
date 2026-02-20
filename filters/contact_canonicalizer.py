"""Filter: contact canonicalizer for personal contact artifacts."""

from __future__ import annotations

import re
from collections import Counter


FILTER_SPEC = {
    "id": "contact_canonicalizer",
    "title": "Contact Canonicalizer",
    "description": "Normalizes and deduplicates email/phone artifacts into canonical forms.",
    "scopes": ["profile", "fusion"],
    "aliases": ["contact_normalizer", "contacts", "normalize"],
    "version": "1.1",
}


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if not digits:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if digits.startswith("1") and len(digits) == 11:
        return f"+{digits}"
    return f"+{digits}"


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    normalized_emails: set[str] = set()
    normalized_phones: set[str] = set()
    email_domains: Counter = Counter()

    for item in results:
        contacts = item.get("contacts", {})
        for email in contacts.get("emails", []):
            normalized = str(email).strip().lower()
            if normalized:
                normalized_emails.add(normalized)
                if "@" in normalized:
                    email_domains[normalized.split("@", 1)[1]] += 1
        for phone in contacts.get("phones", []):
            normalized = _normalize_phone(str(phone))
            if normalized:
                normalized_phones.add(normalized)

    highlights = [
        f"emails={len(normalized_emails)}",
        f"phones={len(normalized_phones)}",
    ] + [f"{domain}:{count}" for domain, count in email_domains.most_common(3)]

    return {
        "severity": "INFO",
        "summary": (
            f"Normalized {len(normalized_emails)} unique email(s) and "
            f"{len(normalized_phones)} unique phone(s)."
        ),
        "highlights": highlights,
        "data": {
            "emails_normalized": sorted(normalized_emails),
            "phones_normalized": sorted(normalized_phones),
            "email_domain_distribution": dict(email_domains),
        },
    }
