"""Plugin: infer likely organization email patterns from identity artifacts."""

from __future__ import annotations

import re
from collections import Counter


PLUGIN_SPEC = {
    "id": "email_pattern_inference",
    "title": "Email Pattern Inference",
    "description": "Infers possible corporate mailbox formats from usernames and target domain artifacts.",
    "scopes": ["fusion"],
    "aliases": ["email_pattern", "mail_pattern", "address_pattern"],
    "version": "1.0",
}


HANDLE_RE = re.compile(r"^[a-z0-9._-]{2,40}$")


def _extract_handle_from_url(url: str) -> str:
    value = str(url or "").strip().rstrip("/")
    if not value:
        return ""
    tail = value.split("/")[-1].lstrip("@").strip().lower()
    if HANDLE_RE.match(tail):
        return tail
    return ""


def _split_name_parts(handle: str) -> tuple[str, str]:
    if "." in handle:
        parts = [item for item in handle.split(".") if item]
        if len(parts) >= 2:
            return parts[0], parts[1]
    if "_" in handle:
        parts = [item for item in handle.split("_") if item]
        if len(parts) >= 2:
            return parts[0], parts[1]
    if "-" in handle:
        parts = [item for item in handle.split("-") if item]
        if len(parts) >= 2:
            return parts[0], parts[1]
    return handle, ""


def _infer_domain(context: dict) -> str:
    domain_result = context.get("domain_result") or {}
    domain = str(domain_result.get("target") or "").strip().lower()
    if domain:
        return domain

    target = str(context.get("target") or "").strip().lower()
    marker = "_fusion_"
    if marker in target:
        return target.split(marker, 1)[1].strip().strip("._")
    return ""


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    domain = _infer_domain(context)

    handles: Counter = Counter()
    for row in results:
        if row.get("status") != "FOUND":
            continue
        handle = _extract_handle_from_url(str(row.get("url") or ""))
        if handle:
            handles[handle] += 1
        for mention in row.get("mentions", []) or []:
            candidate = str(mention).strip().lower().lstrip("@")
            if HANDLE_RE.match(candidate):
                handles[candidate] += 1

    if not domain:
        return {
            "severity": "INFO",
            "summary": "No domain context available; email pattern inference skipped.",
            "highlights": [],
            "data": {"patterns": [], "domain": ""},
        }

    candidates = [item for item, _count in handles.most_common(3)] or ["user"]
    first, last = _split_name_parts(candidates[0])
    fi = first[:1] if first else "u"
    li = last[:1] if last else "x"

    pattern_values: list[str] = []
    templates = [
        f"{first}.{last}@{domain}" if first and last else "",
        f"{first}{last}@{domain}" if first and last else "",
        f"{fi}{last}@{domain}" if first and last else "",
        f"{first}{li}@{domain}" if first and last else "",
        f"{first}@{domain}" if first else "",
        f"{candidates[0]}@{domain}",
    ]
    seen: set[str] = set()
    for item in templates:
        value = item.strip(".@")
        if not value or value in seen:
            continue
        pattern_values.append(value)
        seen.add(value)

    summary = (
        f"Inferred {len(pattern_values)} likely mailbox format candidate(s) for {domain} using "
        f"{len(handles)} username artifact(s). Common formats include first.last@domain — useful for identity correlation. "
        "No validation or email delivery was performed."
    )
    return {
        "severity": "INFO",
        "summary": summary,
        "highlights": pattern_values[:6],
        "data": {
            "domain": domain,
            "source_handles": [item for item, _count in handles.most_common(8)],
            "patterns": pattern_values,
        },
    }
