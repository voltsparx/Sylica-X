"""Selector normalization helpers for plugin/filter name resolution."""

from __future__ import annotations


def selector_keys(value: str) -> tuple[str, ...]:
    """Generate normalized lookup keys from a selector string.

    Supports matching across ids/aliases/titles using common separator variants.
    """

    lowered = str(value).strip().lower()
    if not lowered:
        return ()

    tokens = lowered.replace("-", " ").replace("_", " ").split()
    if not tokens:
        return (lowered,)

    candidates = [
        lowered,
        " ".join(tokens),
        "".join(tokens),
        "_".join(tokens),
        "-".join(tokens),
    ]

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        deduped.append(candidate)
        seen.add(candidate)
    return tuple(deduped)
