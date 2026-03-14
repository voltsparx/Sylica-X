# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Silica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Silica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Silica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

"""CSV export utilities for profile result payloads."""

from __future__ import annotations

import csv
import json

from core.artifacts.storage import (
    csv_report_path,
    ensure_output_tree,
    legacy_results_json_path,
    latest_results_json_path,
    sanitize_target,
)
from core.foundation.output_config import OutputConfigError


def _safe_rows(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _write_csv(path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(header)
        writer.writerows(rows)


def export_to_csv(target: str, *, payload: dict | None = None, stamp: str | None = None) -> str | None:
    target_key = sanitize_target(target)
    data = payload
    if data is None:
        json_file = latest_results_json_path(target_key)
        if json_file is None or not json_file.exists():
            legacy = legacy_results_json_path(target_key)
            if legacy.exists():
                json_file = legacy
            else:
                print(f"No JSON results found for {target_key}")
                return None

        try:
            with json_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            print(f"CSV export failed: malformed JSON for {target_key} ({exc})")
            return None
        except OSError as exc:
            print(f"CSV export failed: unable to read JSON for {target_key} ({exc})")
            return None

    if not isinstance(data, dict):
        print(f"CSV export failed: unexpected JSON payload type for {target_key}.")
        return None

    try:
        ensure_output_tree(types={"csv"})
    except OutputConfigError as exc:
        print(f"CSV export failed: unable to prepare output directories ({exc})")
        return None
    csv_file = csv_report_path(target_key, stamp=stamp)
    mode = str((data.get("metadata", {}) or {}).get("mode", "")).strip()
    target_name = str(data.get("target", target_key)).strip() or target_key
    risk_score = (data.get("issue_summary", {}) or {}).get("risk_score", "")

    result_rows: list[list[object]] = []
    for row in _safe_rows(data.get("results")):
        contacts = row.get("contacts", {}) or {}
        result_rows.append(
            [
                target_name,
                mode,
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
                risk_score,
            ]
        )

    try:
        _write_csv(
            csv_file,
            [
                "Target",
                "Mode",
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
                "RiskScore",
            ],
            result_rows,
        )
    except OSError as exc:
        print(f"CSV export failed: unable to write {csv_file} ({exc})")
        return None

    companion_paths: list[str] = []

    issues_file = csv_file.with_suffix(".issues.csv")
    issue_rows = [
        [
            target_name,
            mode,
            row.get("severity", ""),
            row.get("scope", ""),
            row.get("title", ""),
            row.get("evidence", ""),
            row.get("recommendation", ""),
        ]
        for row in _safe_rows(data.get("issues"))
    ]
    try:
        _write_csv(
            issues_file,
            ["Target", "Mode", "Severity", "Scope", "Title", "Evidence", "Recommendation"],
            issue_rows,
        )
        companion_paths.append(str(issues_file))
    except OSError as exc:
        print(f"CSV export warning: unable to write {issues_file} ({exc})")

    plugins_file = csv_file.with_suffix(".plugins.csv")
    plugin_rows = [
        [
            target_name,
            mode,
            row.get("id", ""),
            row.get("title", ""),
            row.get("severity", ""),
            row.get("summary", ""),
            "; ".join(str(item) for item in (row.get("highlights", []) or [])),
            json.dumps(row.get("data", {}) if isinstance(row.get("data"), dict) else {}, ensure_ascii=False),
        ]
        for row in _safe_rows(data.get("plugins"))
    ]
    try:
        _write_csv(
            plugins_file,
            ["Target", "Mode", "PluginId", "Title", "Severity", "Summary", "Highlights", "DataJson"],
            plugin_rows,
        )
        companion_paths.append(str(plugins_file))
    except OSError as exc:
        print(f"CSV export warning: unable to write {plugins_file} ({exc})")

    filters_file = csv_file.with_suffix(".filters.csv")
    filter_rows = [
        [
            target_name,
            mode,
            row.get("id", ""),
            row.get("title", ""),
            row.get("severity", ""),
            row.get("summary", ""),
            "; ".join(str(item) for item in (row.get("highlights", []) or [])),
            json.dumps(row.get("data", {}) if isinstance(row.get("data"), dict) else {}, ensure_ascii=False),
        ]
        for row in _safe_rows(data.get("filters"))
    ]
    try:
        _write_csv(
            filters_file,
            ["Target", "Mode", "FilterId", "Title", "Severity", "Summary", "Highlights", "DataJson"],
            filter_rows,
        )
        companion_paths.append(str(filters_file))
    except OSError as exc:
        print(f"CSV export warning: unable to write {filters_file} ({exc})")

    intelligence_bundle = data.get("intelligence_bundle", {}) or {}
    entities_file = csv_file.with_suffix(".intel-entities.csv")
    entity_rows = [
        [
            target_name,
            mode,
            row.get("rank", ""),
            row.get("entity_type", ""),
            row.get("value", ""),
            row.get("source", ""),
            row.get("confidence_percent", ""),
            row.get("risk_level", ""),
            row.get("relationship_count", ""),
        ]
        for row in _safe_rows(intelligence_bundle.get("scored_entities"))
    ]
    try:
        _write_csv(
            entities_file,
            ["Target", "Mode", "Rank", "EntityType", "Value", "Source", "ConfidencePercent", "RiskLevel", "Links"],
            entity_rows,
        )
        companion_paths.append(str(entities_file))
    except OSError as exc:
        print(f"CSV export warning: unable to write {entities_file} ({exc})")

    contacts_file = csv_file.with_suffix(".intel-contacts.csv")
    scored_contacts = ((intelligence_bundle.get("entity_facets", {}) or {}).get("scored_contacts", []))
    contact_rows = [
        [
            target_name,
            mode,
            row.get("kind", ""),
            row.get("value", ""),
            row.get("score_percent", ""),
            row.get("supporting_entities", ""),
            row.get("risk_level", ""),
        ]
        for row in _safe_rows(scored_contacts)
    ]
    try:
        _write_csv(
            contacts_file,
            ["Target", "Mode", "Kind", "Value", "ScorePercent", "SupportingEntities", "RiskLevel"],
            contact_rows,
        )
        companion_paths.append(str(contacts_file))
    except OSError as exc:
        print(f"CSV export warning: unable to write {contacts_file} ({exc})")

    print(f"CSV exported -> {csv_file}")
    print(f"CSV companion exports -> {', '.join(companion_paths)}")
    return str(csv_file)

