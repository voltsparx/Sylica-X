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

"""Plugin: module capability matrix derived from Silica source-intel catalogs."""

from __future__ import annotations

from collections import Counter

from modules.catalog import ensure_module_catalog, select_module_entries


PLUGIN_SPEC = {
    "id": "module_capability_matrix",
    "title": "Module Capability Matrix",
    "description": "Maps plugin-like module signals from source-intel trees into scope-aware insights.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["module_matrix", "catalog_matrix", "signal_matrix"],
    "version": "1.0",
}

VALID_SCOPES = {"profile", "surface", "fusion"}


def _top_frameworks(rows: list[dict], *, limit: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        framework = str(row.get("framework", "")).strip()
        if framework:
            counter[framework] += 1
    return [f"{name}:{count}" for name, count in counter.most_common(limit)]


def run(context: dict) -> dict:
    scope = str(context.get("mode", "fusion")).strip().lower()
    if scope not in VALID_SCOPES:
        scope = "fusion"

    catalog = ensure_module_catalog(refresh=False)
    all_rows = select_module_entries(catalog, kind="plugin", scope="all")
    scoped_rows = select_module_entries(catalog, kind="plugin", scope=scope)

    if not all_rows:
        return {
            "severity": "INFO",
            "summary": (
                "No plugin-aligned source entries are cataloged yet. "
                "Run `python silica-x.py modules --sync` to build the catalog."
            ),
            "highlights": [f"scope={scope}", "catalog=empty", "catalog_kind=plugin"],
            "data": {
                "scope": scope,
                "catalog_kind": "plugin",
                "catalog_entries_total": 0,
                "catalog_entries_scoped": 0,
                "top_frameworks": [],
            },
        }

    scoped_count = len(scoped_rows)
    if scoped_count >= 400:
        severity = "HIGH"
    elif scoped_count >= 150:
        severity = "MEDIUM"
    else:
        severity = "INFO"

    frameworks = _top_frameworks(scoped_rows)
    highlights = [
        "catalog_kind=plugin",
        f"catalog_entries={len(all_rows)}",
        f"catalog_{scope}={scoped_count}",
        f"frameworks={len({row.get('framework') for row in scoped_rows})}",
    ]
    if frameworks:
        highlights.append(f"top={frameworks[0]}")

    return {
        "severity": severity,
        "summary": (
            f"Cataloged {len(all_rows)} plugin-aligned catalog entries, "
            f"with {scoped_count} aligned to '{scope}' workflow."
        ),
        "highlights": highlights,
        "data": {
            "scope": scope,
            "catalog_kind": "plugin",
            "catalog_entries_total": len(all_rows),
            "catalog_entries_scoped": scoped_count,
            "top_frameworks": frameworks,
            "sample_entries": [row.get("path") for row in scoped_rows[:12]],
        },
    }
