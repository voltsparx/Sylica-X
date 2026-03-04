"""Filter: flag consistency gaps across results, issues, and intelligence bundle."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "evidence_consistency_filter",
    "title": "Evidence Consistency Filter",
    "description": "Detects contradictions across confidence, issue severity, and intelligence risk posture.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["consistency_filter", "evidence_quality", "signal_consistency"],
    "version": "1.0",
}


def run(context: dict) -> dict:
    results = [row for row in (context.get("results", []) or []) if isinstance(row, dict)]
    issues = [row for row in (context.get("issues", []) or []) if isinstance(row, dict)]
    intelligence_bundle_raw = context.get("intelligence_bundle", {}) or {}
    intelligence_bundle = intelligence_bundle_raw if isinstance(intelligence_bundle_raw, dict) else {}

    found_rows = [row for row in results if str(row.get("status", "")).upper() == "FOUND"]
    avg_confidence = 0.0
    if found_rows:
        avg_confidence = sum(int(row.get("confidence", 0) or 0) for row in found_rows) / len(found_rows)

    critical_issue_count = sum(
        1 for row in issues if str(row.get("severity", "")).strip().upper() in {"CRITICAL", "HIGH"}
    )

    risk_summary_raw = intelligence_bundle.get("risk_summary", {})
    risk_summary = risk_summary_raw if isinstance(risk_summary_raw, dict) else {}
    high_risk_entities = int(risk_summary.get("CRITICAL", 0) or 0) + int(risk_summary.get("HIGH", 0) or 0)

    confidence_distribution_raw = intelligence_bundle.get("confidence_distribution", {})
    confidence_distribution = confidence_distribution_raw if isinstance(confidence_distribution_raw, dict) else {}
    low_confidence_entities = int(confidence_distribution.get("low", 0) or 0)

    anomalies: list[str] = []
    if found_rows and avg_confidence < 35:
        anomalies.append("found_profiles_with_low_confidence")
    if critical_issue_count >= 3 and avg_confidence < 45:
        anomalies.append("high_issue_count_but_low_evidence_confidence")
    if high_risk_entities >= 3 and critical_issue_count == 0:
        anomalies.append("intelligence_high_risk_without_matching_exposure_issues")
    if low_confidence_entities >= 10 and high_risk_entities == 0 and critical_issue_count == 0:
        anomalies.append("low_confidence_cluster_without_prioritized_risk")

    consistency_score = max(0, 100 - (len(anomalies) * 22))
    severity = "HIGH" if len(anomalies) >= 3 else "MEDIUM" if len(anomalies) >= 1 else "INFO"
    summary = (
        f"Consistency analysis completed with anomalies={len(anomalies)}, "
        f"avg_found_confidence={round(avg_confidence, 2)}, consistency_score={consistency_score}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"anomalies={len(anomalies)}",
            f"avg_found_confidence={round(avg_confidence, 2)}",
            f"high_issue_count={critical_issue_count}",
            f"high_risk_entities={high_risk_entities}",
            f"consistency_score={consistency_score}",
        ],
        "data": {
            "anomalies": anomalies,
            "avg_found_confidence": round(avg_confidence, 2),
            "high_issue_count": critical_issue_count,
            "high_risk_entities": high_risk_entities,
            "low_confidence_entities": low_confidence_entities,
            "consistency_score": consistency_score,
        },
    }
