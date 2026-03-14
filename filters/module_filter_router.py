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

"""Filter: module-aware routing hints derived from source-intel catalogs."""

from __future__ import annotations

from modules.catalog import ensure_module_catalog, select_module_entries


FILTER_SPEC = {
    "id": "module_filter_router",
    "title": "Module Filter Router",
    "description": "Routes filter strategies using cataloged filter-like modules from source-intel trees.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["filter_router", "module_router", "catalog_router"],
    "version": "1.0",
}

VALID_SCOPES = {"profile", "surface", "fusion"}


def run(context: dict) -> dict:
    scope = str(context.get("mode", "fusion")).strip().lower()
    if scope not in VALID_SCOPES:
        scope = "fusion"

    catalog = ensure_module_catalog(refresh=False)
    scoped_total = select_module_entries(catalog, kind="all", scope=scope)
    scoped_filters = select_module_entries(catalog, kind="filter", scope=scope)

    if not scoped_total:
        return {
            "severity": "INFO",
            "summary": (
                "No scoped source-intel entries are cataloged yet. "
                "Run `python silica-x.py modules --sync` to populate routing intelligence."
            ),
            "highlights": [f"scope={scope}", "scoped_entries=0", "catalog_kind=filter"],
            "data": {
                "scope": scope,
                "catalog_kind": "filter",
                "scoped_entries": 0,
                "scoped_filter_entries": 0,
                "filter_density": 0.0,
            },
        }

    density = len(scoped_filters) / float(len(scoped_total))
    if density >= 0.45:
        severity = "INFO"
    elif density >= 0.2:
        severity = "MEDIUM"
    else:
        severity = "HIGH"

    highlights = [
        f"scope={scope}",
        f"scoped_entries={len(scoped_total)}",
        f"filter_entries={len(scoped_filters)}",
        f"filter_density={density:.2f}",
        "catalog_kind=filter",
    ]
    return {
        "severity": severity,
        "summary": (
            f"Filter routing density for '{scope}' is {density:.2f} "
            f"({len(scoped_filters)} filter-aligned catalog entries across {len(scoped_total)} scoped entries)."
        ),
        "highlights": highlights,
        "data": {
            "scope": scope,
            "catalog_kind": "filter",
            "scoped_entries": len(scoped_total),
            "scoped_filter_entries": len(scoped_filters),
            "filter_density": round(density, 4),
            "sample_filter_entries": [row.get("path") for row in scoped_filters[:12]],
        },
    }
