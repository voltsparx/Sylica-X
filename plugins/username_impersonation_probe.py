"""Plugin: detect lookalike usernames and likely impersonation variants."""

from __future__ import annotations

import difflib
import re


PLUGIN_SPEC = {
    "id": "username_impersonation_probe",
    "title": "Username Impersonation Probe",
    "description": "Detects high-similarity username variants in mentions and profile artifacts that may indicate impersonation.",
    "scopes": ["profile", "fusion"],
    "aliases": ["impersonation_probe", "lookalike_usernames", "username_variants"],
    "version": "1.0",
}


TOKEN_RE = re.compile(r"[A-Za-z0-9_.-]{3,40}")


def _normalize(value: str) -> str:
    token = str(value or "").strip().lower()
    return "".join(ch for ch in token if ch.isalnum())


def _candidate_tokens(value: str) -> list[str]:
    return [match.group(0) for match in TOKEN_RE.finditer(str(value or ""))]


def run(context: dict) -> dict:
    target_raw = str(context.get("target", "")).strip()
    target = _normalize(target_raw)
    if not target:
        return {
            "severity": "INFO",
            "summary": "Impersonation probe skipped: target username was not available in context.",
            "highlights": ["target_missing=true"],
            "data": {"target": target_raw, "candidates": [], "risk_score": 0},
        }

    raw_results = context.get("results", []) or []
    results = [row for row in raw_results if isinstance(row, dict)]
    candidate_map: dict[str, set[str]] = {}
    ratio_map: dict[str, float] = {}

    for row in results:
        if str(row.get("status", "")).upper() != "FOUND":
            continue
        platform = str(row.get("platform", "unknown")).strip().lower() or "unknown"
        raw_pool: list[str] = []
        raw_pool.extend(str(item) for item in (row.get("mentions", []) or []))
        raw_pool.extend(str(item) for item in (row.get("links", []) or []))

        for blob in raw_pool:
            for token in _candidate_tokens(blob):
                normalized = _normalize(token)
                if not normalized or normalized == target:
                    continue
                ratio = difflib.SequenceMatcher(a=target, b=normalized).ratio()
                if ratio < 0.78 or ratio > 0.99:
                    continue
                if abs(len(normalized) - len(target)) > 6:
                    continue

                candidate_map.setdefault(normalized, set()).add(platform)
                previous = ratio_map.get(normalized, 0.0)
                if ratio > previous:
                    ratio_map[normalized] = ratio

    ranked = sorted(
        (
            {
                "username": username,
                "similarity": round(ratio_map.get(username, 0.0), 3),
                "platforms": sorted(platforms),
            }
            for username, platforms in candidate_map.items()
        ),
        key=lambda item: (-item["similarity"], -len(item["platforms"]), item["username"]),
    )
    cross_platform = sum(1 for row in ranked if len(row["platforms"]) > 1)
    risk_score = min(100, (len(ranked) * 14) + (cross_platform * 10))
    severity = "HIGH" if risk_score >= 55 else "MEDIUM" if risk_score >= 25 else "INFO"

    summary = (
        f"Impersonation probe identified {len(ranked)} lookalike username candidate(s) "
        f"for target '{target_raw}', cross_platform={cross_platform}, risk_score={risk_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"target={target_raw}",
            f"lookalike_candidates={len(ranked)}",
            f"cross_platform_candidates={cross_platform}",
            f"risk_score={risk_score}",
        ],
        "data": {
            "target_username": target_raw,
            "normalized_target": target,
            "candidates": ranked[:120],
            "cross_platform_candidate_count": cross_platform,
            "risk_score": risk_score,
        },
    }
