"""Filter: PII signal classifier for personal data categories."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse


FILTER_SPEC = {
    "id": "pii_signal_classifier",
    "title": "PII Signal Classifier",
    "description": "Classifies extracted artifacts into personal data classes for analyst triage.",
    "scopes": ["profile", "fusion"],
    "aliases": ["personal_data_classifier", "pii", "classify"],
    "version": "1.1",
}


KEYWORDS = {
    "location_hint": ("city", "state", "country", "based in", "location"),
    "employment_hint": ("engineer", "manager", "ceo", "cto", "founder", "developer"),
    "education_hint": ("university", "college", "school", "bachelor", "master", "phd"),
}


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    counts: Counter = Counter()
    link_domains: Counter = Counter()

    for item in results:
        contacts = item.get("contacts", {})
        counts["email"] += len(contacts.get("emails", []))
        counts["phone"] += len(contacts.get("phones", []))
        counts["mention"] += len(item.get("mentions", []))
        if item.get("bio"):
            counts["bio_present"] += 1

        for link in item.get("links", []):
            parsed = urlparse(str(link))
            if parsed.netloc:
                link_domains[parsed.netloc.lower()] += 1
            counts["external_link"] += 1

        text_blob = f"{item.get('bio') or ''} {item.get('context') or ''}".lower()
        for key, tokens in KEYWORDS.items():
            if any(token in text_blob for token in tokens):
                counts[key] += 1

    highlights = [f"{key}={value}" for key, value in counts.most_common(8)]
    return {
        "severity": "INFO",
        "summary": f"Classified personal data across {len(results)} scanned profile row(s).",
        "highlights": highlights,
        "data": {
            "class_counts": dict(counts),
            "top_link_domains": dict(link_domains.most_common(10)),
        },
    }
