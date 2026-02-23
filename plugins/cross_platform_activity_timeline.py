"""Plugin: infer cross-platform activity timeline from public timestamp hints."""

from __future__ import annotations

import re
from datetime import datetime


PLUGIN_SPEC = {
    "id": "cross_platform_activity_timeline",
    "title": "Cross-Platform Activity Timeline",
    "description": "Extracts public date hints across profiles to build a lightweight activity timeline.",
    "scopes": ["profile", "fusion"],
    "aliases": ["activity_timeline", "timeline", "public_activity"],
    "version": "1.0",
}


ISO_DATE_RE = re.compile(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b")
MONTH_DATE_RE = re.compile(
    r"\b("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\s+(\d{1,2}),?\s+(20\d{2})\b",
    re.IGNORECASE,
)
MONTH_LOOKUP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _normalize_date(year: int, month: int, day: int) -> str:
    try:
        parsed = datetime(year=year, month=month, day=day)
    except ValueError:
        return ""
    return parsed.strftime("%Y-%m-%d")


def _extract_dates(text: str) -> list[str]:
    values: set[str] = set()
    body = str(text or "")
    for year_text, month_text, day_text in ISO_DATE_RE.findall(body):
        value = _normalize_date(int(year_text), int(month_text), int(day_text))
        if value:
            values.add(value)

    for month_name, day_text, year_text in MONTH_DATE_RE.findall(body):
        month = MONTH_LOOKUP.get(month_name[:3].lower())
        if month is None:
            continue
        value = _normalize_date(int(year_text), int(month), int(day_text))
        if value:
            values.add(value)
    return sorted(values)


def run(context: dict) -> dict:
    results = context.get("results", []) or []

    timeline_events: list[dict[str, str]] = []
    fallback_platforms: list[str] = []
    for row in results:
        if row.get("status") != "FOUND":
            continue
        platform = str(row.get("platform", "Unknown"))
        corpus = " ".join(
            [
                str(row.get("bio") or ""),
                str(row.get("context") or ""),
                " ".join(str(item) for item in (row.get("links", []) or [])),
            ]
        )
        dates = _extract_dates(corpus)
        if not dates:
            fallback_platforms.append(platform)
            continue
        for date_value in dates[:5]:
            timeline_events.append(
                {
                    "date": date_value,
                    "platform": platform,
                    "evidence": "public_date_hint",
                }
            )

    timeline_events.sort(key=lambda item: (item["date"], item["platform"]))
    unique_dates = sorted({item["date"] for item in timeline_events})
    first_date = unique_dates[0] if unique_dates else "-"
    last_date = unique_dates[-1] if unique_dates else "-"

    severity = "MEDIUM" if len(unique_dates) >= 8 else "INFO"
    summary = (
        f"Timeline extractor identified {len(timeline_events)} dated activity marker(s) across "
        f"{len({item['platform'] for item in timeline_events})} platform(s). "
        "Posting patterns may reveal time zones or work cycles."
    )
    if not timeline_events:
        summary = (
            "No explicit public timestamp markers were extracted from scanned profile artifacts. "
            "Posting patterns may reveal time zones or work cycles."
        )

    highlights = [
        f"dated_events={len(timeline_events)}",
        f"unique_dates={len(unique_dates)}",
        f"first_date={first_date}",
        f"last_date={last_date}",
    ]
    if fallback_platforms:
        highlights.append(f"no_timestamps={len(fallback_platforms)}")

    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights,
        "data": {
            "timeline": timeline_events[:120],
            "unique_dates": unique_dates,
            "no_timestamp_platforms": sorted(set(fallback_platforms)),
            "window": {"first": first_date, "last": last_date},
        },
    }
