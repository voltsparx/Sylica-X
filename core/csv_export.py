"""CSV export utilities for profile result payloads."""

from __future__ import annotations

import csv
import json

from core.storage import cli_report_path, legacy_results_json_path, results_json_path, sanitize_target


def export_to_csv(target: str) -> str | None:
    target_key = sanitize_target(target)
    json_file = results_json_path(target_key)
    if not json_file.exists():
        legacy = legacy_results_json_path(target_key)
        if legacy.exists():
            json_file = legacy
        else:
            print(f"No JSON results found for {target_key}")
            return None

    with json_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    csv_file = cli_report_path(target_key).with_suffix(".csv")
    with csv_file.open("w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(
            [
                "Platform",
                "Status",
                "Confidence",
                "HTTP",
                "RTT_MS",
                "Bio",
                "Emails",
                "Phones",
                "ExtractedLinks",
                "Mentions",
                "URL",
                "Context",
            ]
        )

        for row in data.get("results", []):
            contacts = row.get("contacts", {}) or {}
            writer.writerow(
                [
                    row.get("platform", ""),
                    row.get("status", ""),
                    row.get("confidence", 0),
                    row.get("http_status", ""),
                    row.get("response_time_ms", ""),
                    row.get("bio", ""),
                    "; ".join(contacts.get("emails", []) or []),
                    "; ".join(contacts.get("phones", []) or []),
                    "; ".join(row.get("links", []) or []),
                    "; ".join(row.get("mentions", []) or []),
                    row.get("url", ""),
                    row.get("context", ""),
                ]
            )

    print(f"CSV exported -> {csv_file}")
    return str(csv_file)
