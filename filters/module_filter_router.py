"""Filter: module-aware routing hints derived from source-intel catalogs."""

from __future__ import annotations

from collections import Counter

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


def _top_frameworks(rows: list[dict], *, limit: int = 5) -> list[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        framework = str(row.get("framework", "")).strip()
        if framework:
            counts[framework] += 1
    return [f"{name}:{count}" for name, count in counts.most_common(limit)]


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
                "No scoped source-intel modules are cataloged yet. "
                "Run `python silica-x.py modules --sync` to populate module routing intelligence."
            ),
            "highlights": [f"scope={scope}", "scoped_modules=0"],
            "data": {
                "scope": scope,
                "scoped_modules": 0,
                "scoped_filter_modules": 0,
                "filter_density": 0.0,
                "top_filter_frameworks": [],
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
        f"scoped_modules={len(scoped_total)}",
        f"filter_modules={len(scoped_filters)}",
        f"filter_density={density:.2f}",
    ]
    frameworks = _top_frameworks(scoped_filters)
    if frameworks:
        highlights.append(f"top={frameworks[0]}")

    return {
        "severity": severity,
        "summary": (
            f"Filter routing density for '{scope}' is {density:.2f} "
            f"({len(scoped_filters)} filter-like modules across {len(scoped_total)} scoped modules)."
        ),
        "highlights": highlights,
        "data": {
            "scope": scope,
            "scoped_modules": len(scoped_total),
            "scoped_filter_modules": len(scoped_filters),
            "filter_density": round(density, 4),
            "top_filter_frameworks": frameworks,
            "sample_filter_modules": [row.get("path") for row in scoped_filters[:12]],
        },
    }
