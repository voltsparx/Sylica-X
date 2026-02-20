"""Filter: sensitive lexicon guard for personal-information phrases."""

from __future__ import annotations

import re
from collections import Counter


FILTER_SPEC = {
    "id": "sensitive_lexicon_guard",
    "title": "Sensitive Lexicon Guard",
    "description": "Flags sensitive personal-information phrases in bios and profile context text.",
    "scopes": ["profile", "fusion"],
    "aliases": ["sensitive_keyword_filter", "sensitive", "privacy"],
    "version": "1.1",
}


SENSITIVE_TOKENS = (
    "address",
    "home",
    "phone",
    "mobile",
    "contact me",
    "direct line",
    "telegram",
    "whatsapp",
    "location",
    "dob",
    "birth",
    "passport",
    "email me",
    "contact",
    "residence",
)


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    token_counter: Counter = Counter()

    for item in results:
        text = f"{item.get('bio') or ''} {item.get('context') or ''}".lower()
        for token in SENSITIVE_TOKENS:
            pattern = r"\b" + re.escape(token) + r"\b"
            if re.search(pattern, text):
                token_counter[token] += 1

    flagged = sum(token_counter.values())
    severity = "HIGH" if flagged >= 8 else "MEDIUM" if flagged >= 3 else "INFO"

    return {
        "severity": severity,
        "summary": f"Sensitive keyword filter flagged {flagged} potential personal-info phrase match(es).",
        "highlights": [f"{token}:{count}" for token, count in token_counter.most_common(8)],
        "data": {
            "keyword_hits": dict(token_counter),
            "total_hits": flagged,
        },
    }
