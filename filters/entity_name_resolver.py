"""Filter: entity name resolver for bio/context text."""

from __future__ import annotations

import re
from collections import Counter


FILTER_SPEC = {
    "id": "entity_name_resolver",
    "title": "Entity Name Resolver",
    "description": "Extracts likely full-name entities from biography snippets and profile descriptions.",
    "scopes": ["profile", "fusion"],
    "aliases": ["name_entity_filter", "names", "entities"],
    "version": "1.1",
}


NAME_PATTERN = re.compile(
    r"\b([A-Z][a-z]{1,20}(?:[-'][A-Z][a-z]{1,20})?\s+[A-Z][a-z]{1,20}(?:[-'][A-Z][a-z]{1,20})?)\b"
)


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    counter: Counter = Counter()

    for item in results:
        text_blob = " ".join(
            [
                str(item.get("bio") or "").title(),
                str(item.get("context") or "").title(),
            ]
        )
        for match in NAME_PATTERN.findall(text_blob):
            normalized = " ".join(part.strip() for part in match.split())
            if normalized:
                counter[normalized] += 1

    candidates = [name for name, count in counter.most_common(20)]
    highlights = [f"{name}:{counter[name]}" for name in candidates[:6]]
    severity = "MEDIUM" if len(candidates) >= 3 else "INFO"

    return {
        "severity": severity,
        "summary": f"Detected {len(candidates)} likely name entity candidate(s) in profile text.",
        "highlights": highlights,
        "data": {
            "name_candidates": candidates,
            "name_frequency": dict(counter),
        },
    }
