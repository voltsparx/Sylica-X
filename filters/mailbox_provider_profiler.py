"""Filter: mailbox provider profiler."""

from __future__ import annotations

from collections import Counter


FILTER_SPEC = {
    "id": "mailbox_provider_profiler",
    "title": "Mailbox Provider Profiler",
    "description": "Separates public/free mailbox providers from custom domains in contact artifacts.",
    "scopes": ["profile", "fusion"],
    "aliases": ["free_provider_filter", "mailbox", "provider"],
    "version": "1.1",
}


FREE_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "proton.me",
    "protonmail.com",
    "icloud.com",
    "aol.com",
    "zoho.com",
    "gmx.com",
    "yandex.com",
}


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    free_counter: Counter = Counter()
    custom_counter: Counter = Counter()

    for item in results:
        contacts = item.get("contacts", {})
        for email in contacts.get("emails", []):
            normalized = str(email).strip().lower()
            if "@" not in normalized:
                continue
            domain = normalized.split("@", 1)[1]
            if domain in FREE_PROVIDERS:
                free_counter[domain] += 1
            else:
                custom_counter[domain] += 1

    free_total = sum(free_counter.values())
    custom_total = sum(custom_counter.values())
    severity = "MEDIUM" if free_total > custom_total and free_total > 0 else "INFO"

    highlights = [f"free_total={free_total}", f"custom_total={custom_total}"]
    highlights += [f"{domain}:{count}" for domain, count in free_counter.most_common(4)]

    return {
        "severity": severity,
        "summary": (
            f"Email provider split detected {free_total} free-provider artifact(s) and "
            f"{custom_total} custom-domain artifact(s)."
        ),
        "highlights": highlights,
        "data": {
            "free_provider_distribution": dict(free_counter),
            "custom_domain_distribution": dict(custom_counter),
        },
    }
