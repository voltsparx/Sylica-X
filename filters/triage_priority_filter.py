"""Filter: convert raw issue/plugin signals into actionable triage priority."""

from __future__ import annotations


FILTER_SPEC = {
    "id": "triage_priority_filter",
    "title": "Triage Priority Filter",
    "description": "Calculates a single triage priority from issue severity and plugin signal intensity.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["triage_priority", "priority_filter", "incident_triage"],
    "version": "1.0",
}


def _severity_count(rows: list[dict], key: str) -> dict[str, int]:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for row in rows:
        value = str(row.get(key, "INFO")).strip().upper()
        if value not in counts:
            value = "INFO"
        counts[value] += 1
    return counts


def run(context: dict) -> dict:
    issues = [row for row in (context.get("issues", []) or []) if isinstance(row, dict)]
    plugins = [row for row in (context.get("plugins", []) or []) if isinstance(row, dict)]

    issue_counts = _severity_count(issues, "severity")
    plugin_counts = _severity_count(plugins, "severity")

    score = min(
        100,
        (issue_counts["CRITICAL"] * 24)
        + (issue_counts["HIGH"] * 14)
        + (issue_counts["MEDIUM"] * 7)
        + (plugin_counts["HIGH"] * 10)
        + (plugin_counts["MEDIUM"] * 5),
    )

    if score >= 70:
        priority = "high"
        severity = "HIGH"
    elif score >= 35:
        priority = "medium"
        severity = "MEDIUM"
    else:
        priority = "low"
        severity = "INFO"

    issue_titles = [str(item.get("title", "")).strip() for item in issues if str(item.get("title", "")).strip()]
    high_plugins = [
        str(item.get("id", "")).strip()
        for item in plugins
        if str(item.get("severity", "")).strip().upper() in {"CRITICAL", "HIGH"}
    ]
    reasons = issue_titles[:5] + high_plugins[:5]

    summary = (
        f"Triage priority='{priority}' with score={score}; "
        f"issues(high+critical)={issue_counts['HIGH'] + issue_counts['CRITICAL']}, "
        f"plugins(high+critical)={plugin_counts['HIGH'] + plugin_counts['CRITICAL']}."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"priority={priority}",
            f"score={score}",
            f"critical_issues={issue_counts['CRITICAL']}",
            f"high_issues={issue_counts['HIGH']}",
            f"high_plugins={plugin_counts['HIGH']}",
        ],
        "data": {
            "priority": priority,
            "score": score,
            "issue_severity_counts": issue_counts,
            "plugin_severity_counts": plugin_counts,
            "top_reasons": reasons,
        },
    }
