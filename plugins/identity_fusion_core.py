"""Plugin: identity fusion core and confidence calibration."""

from __future__ import annotations

from collections import Counter


PLUGIN_SPEC = {
    "id": "identity_fusion_core",
    "title": "Identity Fusion Core",
    "description": "Aggregates confidence, mention density, and identity overlaps into a fusion index.",
    "scopes": ["profile", "fusion"],
    "aliases": ["persona_signal_fusion", "persona", "fusionindex"],
    "version": "1.1",
}


def run(context: dict) -> dict:
    results = context.get("results", []) or []
    correlation = context.get("correlation", {}) or {}

    found_rows = [item for item in results if item.get("status") == "FOUND"]
    if not found_rows:
        return {
            "severity": "INFO",
            "summary": "No FOUND profiles detected; persona fusion index not computed.",
            "highlights": [],
            "data": {"fusion_index": 0},
        }

    avg_confidence = int(
        sum(int(item.get("confidence", 0) or 0) for item in found_rows) / len(found_rows)
    )
    mention_count = sum(len(item.get("mentions", [])) for item in found_rows)
    overlap_score = int(correlation.get("identity_overlap_score", 0) or 0)
    status_distribution = correlation.get("status_distribution", {}) or {}
    blocked_count = int(status_distribution.get("BLOCKED", 0))
    avg_rtt = int((correlation.get("response_time_stats") or {}).get("avg_ms") or 0)

    platform_counter: Counter = Counter(item.get("platform", "Unknown") for item in found_rows)
    top_platforms = [f"{platform}:{count}" for platform, count in platform_counter.most_common(5)]

    fusion_index = min(100, int(avg_confidence * 0.45 + overlap_score * 0.45 + min(mention_count, 20) * 0.5))
    if blocked_count > 0:
        fusion_index = max(0, fusion_index - min(20, blocked_count * 3))
    if avg_rtt > 3000:
        fusion_index = max(0, fusion_index - 5)

    severity = "HIGH" if fusion_index >= 75 else "MEDIUM" if fusion_index >= 45 else "INFO"
    summary = (
        f"Persona fusion index={fusion_index} using avg_confidence={avg_confidence}, "
        f"overlap_score={overlap_score}, mention_count={mention_count}, blocked={blocked_count}, avg_rtt={avg_rtt}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": top_platforms,
        "data": {
            "fusion_index": fusion_index,
            "avg_confidence": avg_confidence,
            "overlap_score": overlap_score,
            "mention_count": mention_count,
            "blocked_count": blocked_count,
            "average_rtt_ms": avg_rtt,
            "top_platforms": top_platforms,
        },
    }
