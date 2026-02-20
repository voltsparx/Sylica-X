"""Signal Sieve: filter discovery and execution engine."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from core.sieve_schema import FilterExecutionResult, FilterSpec


FILTER_PACKAGE = "filters"
VALID_SCOPES = {"profile", "surface", "fusion"}


def _normalize_data_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _iter_filter_module_names() -> list[str]:
    package = importlib.import_module(FILTER_PACKAGE)
    names: list[str] = []
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.ispkg:
            continue
        if module_info.name.startswith("_"):
            continue
        names.append(module_info.name)
    return sorted(names)


def _load_filter_module(module_name: str):
    return importlib.import_module(f"{FILTER_PACKAGE}.{module_name}")


def _normalize_spec(module_name: str, raw: dict[str, Any]) -> FilterSpec:
    filter_id = str(raw.get("id") or module_name).strip().lower()
    title = str(raw.get("title") or filter_id).strip()
    description = str(raw.get("description") or "").strip() or "No description provided."

    scopes_raw = raw.get("scopes") or ["profile", "surface", "fusion"]
    scopes: tuple[str, ...]
    if isinstance(scopes_raw, str):
        scopes = (scopes_raw.lower(),)
    else:
        scopes = tuple(str(scope).lower() for scope in scopes_raw)

    valid_scopes = tuple(scope for scope in scopes if scope in VALID_SCOPES)
    if not valid_scopes:
        valid_scopes = ("profile", "surface", "fusion")

    aliases_raw = raw.get("aliases") or []
    aliases = tuple(str(alias).strip().lower() for alias in aliases_raw if str(alias).strip())

    return FilterSpec(
        filter_id=filter_id,
        title=title,
        description=description,
        scopes=valid_scopes,
        version=str(raw.get("version") or "1.0"),
        author=str(raw.get("author") or "Silica-X"),
        aliases=aliases,
    )


def list_filter_specs(scope: str | None = None) -> list[FilterSpec]:
    specs: list[FilterSpec] = []
    for module_name in _iter_filter_module_names():
        try:
            module = _load_filter_module(module_name)
        except Exception:  # pragma: no cover - defensive import safety
            continue
        raw = getattr(module, "FILTER_SPEC", {})
        if not isinstance(raw, dict):
            continue
        spec = _normalize_spec(module_name, raw)
        if scope and scope not in spec.scopes:
            continue
        specs.append(spec)
    return sorted(specs, key=lambda item: item.filter_id)


def list_filter_descriptors(scope: str | None = None) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for spec in list_filter_specs(scope=scope):
        descriptors.append(
            {
                "id": spec.filter_id,
                "title": spec.title,
                "description": spec.description,
                "scopes": list(spec.scopes),
                "version": spec.version,
                "author": spec.author,
                "aliases": list(spec.aliases),
            }
        )
    return descriptors


def _resolve_requested_filters(
    scope: str,
    requested_filters: list[str] | None,
    include_all: bool,
) -> tuple[list[FilterSpec], list[str]]:
    available_specs = list_filter_specs(scope=scope)
    by_key: dict[str, FilterSpec] = {}
    for spec in available_specs:
        by_key[spec.filter_id] = spec
        for alias in spec.aliases:
            by_key[alias] = spec

    if include_all:
        return available_specs, []

    requested_filters = requested_filters or []
    unknown: list[str] = []
    selected: list[FilterSpec] = []
    seen: set[str] = set()
    for raw_name in requested_filters:
        normalized = raw_name.strip().lower()
        if not normalized:
            continue
        matched_spec: FilterSpec | None = by_key.get(normalized)
        if matched_spec is None:
            unknown.append(raw_name)
            continue
        if matched_spec.filter_id in seen:
            continue
        selected.append(matched_spec)
        seen.add(matched_spec.filter_id)
    return selected, unknown


def execute_filters(
    *,
    scope: str,
    requested_filters: list[str] | None,
    include_all: bool,
    context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    if scope not in VALID_SCOPES:
        raise ValueError(f"Unsupported filter scope: {scope}")

    selected_specs, unknown = _resolve_requested_filters(
        scope=scope,
        requested_filters=requested_filters,
        include_all=include_all,
    )
    errors = [f"Unknown filter requested: {name}" for name in unknown]
    if not selected_specs:
        return [], errors

    results: list[dict[str, Any]] = []
    for spec in selected_specs:
        try:
            module = _load_filter_module(spec.filter_id)
            run_fn = getattr(module, "run", None)
            if run_fn is None or not callable(run_fn):
                errors.append(f"Filter '{spec.filter_id}' has no callable run(context).")
                continue
            payload = run_fn(context)
            if not isinstance(payload, dict):
                errors.append(f"Filter '{spec.filter_id}' returned non-dict payload.")
                continue

            result = FilterExecutionResult(
                filter_id=spec.filter_id,
                title=spec.title,
                description=spec.description,
                scope=scope,
                summary=str(payload.get("summary") or "No filter summary."),
                severity=str(payload.get("severity") or "INFO").upper(),
                highlights=tuple(str(item) for item in (payload.get("highlights") or [])),
                data=_normalize_data_payload(payload.get("data")),
            )
            results.append(
                {
                    "id": result.filter_id,
                    "title": result.title,
                    "description": result.description,
                    "scope": result.scope,
                    "summary": result.summary,
                    "severity": result.severity,
                    "highlights": list(result.highlights),
                    "data": result.data,
                }
            )
        except Exception as exc:  # pragma: no cover - filter safety guard
            errors.append(f"Filter '{spec.filter_id}' failed: {exc}")

    return results, errors
