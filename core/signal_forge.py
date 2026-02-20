"""Signal Forge: plugin discovery and execution engine."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from core.forge_schema import PluginContext, PluginExecutionResult, PluginSpec


PLUGIN_PACKAGE = "plugins"
VALID_SCOPES = {"profile", "surface", "fusion"}


def _normalize_data_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _iter_plugin_module_names() -> list[str]:
    package = importlib.import_module(PLUGIN_PACKAGE)
    names: list[str] = []
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.ispkg:
            continue
        if module_info.name.startswith("_"):
            continue
        names.append(module_info.name)
    return sorted(names)


def _load_plugin_module(module_name: str):
    return importlib.import_module(f"{PLUGIN_PACKAGE}.{module_name}")


def _normalize_spec(module_name: str, raw: dict[str, Any]) -> PluginSpec:
    plugin_id = str(raw.get("id") or module_name).strip().lower()
    title = str(raw.get("title") or plugin_id).strip()
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

    return PluginSpec(
        plugin_id=plugin_id,
        title=title,
        description=description,
        scopes=valid_scopes,
        version=str(raw.get("version") or "1.0"),
        author=str(raw.get("author") or "Silica-X"),
        aliases=aliases,
    )


def list_plugin_specs(scope: str | None = None) -> list[PluginSpec]:
    specs: list[PluginSpec] = []
    for module_name in _iter_plugin_module_names():
        try:
            module = _load_plugin_module(module_name)
        except Exception:  # pragma: no cover - defensive import safety
            continue
        raw = getattr(module, "PLUGIN_SPEC", {})
        if not isinstance(raw, dict):
            continue
        spec = _normalize_spec(module_name, raw)
        if scope and scope not in spec.scopes:
            continue
        specs.append(spec)
    return sorted(specs, key=lambda item: item.plugin_id)


def list_plugin_descriptors(scope: str | None = None) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for spec in list_plugin_specs(scope=scope):
        descriptors.append(
            {
                "id": spec.plugin_id,
                "title": spec.title,
                "description": spec.description,
                "scopes": list(spec.scopes),
                "version": spec.version,
                "author": spec.author,
                "aliases": list(spec.aliases),
            }
        )
    return descriptors


def _resolve_requested_plugins(
    scope: str,
    requested_plugins: list[str] | None,
    include_all: bool,
) -> tuple[list[PluginSpec], list[str]]:
    available_specs = list_plugin_specs(scope=scope)
    by_key: dict[str, PluginSpec] = {}
    for spec in available_specs:
        by_key[spec.plugin_id] = spec
        for alias in spec.aliases:
            by_key[alias] = spec

    if include_all:
        return available_specs, []

    requested_plugins = requested_plugins or []
    unknown: list[str] = []
    selected: list[PluginSpec] = []
    seen: set[str] = set()
    for raw_name in requested_plugins:
        normalized = raw_name.strip().lower()
        if not normalized:
            continue
        matched_spec: PluginSpec | None = by_key.get(normalized)
        if matched_spec is None:
            unknown.append(raw_name)
            continue
        if matched_spec.plugin_id in seen:
            continue
        selected.append(matched_spec)
        seen.add(matched_spec.plugin_id)
    return selected, unknown


def execute_plugins(
    *,
    scope: str,
    requested_plugins: list[str] | None,
    include_all: bool,
    context: PluginContext,
) -> tuple[list[dict[str, Any]], list[str]]:
    if scope not in VALID_SCOPES:
        raise ValueError(f"Unsupported plugin scope: {scope}")

    selected_specs, unknown = _resolve_requested_plugins(
        scope=scope,
        requested_plugins=requested_plugins,
        include_all=include_all,
    )
    errors = [f"Unknown plugin requested: {name}" for name in unknown]
    if not selected_specs:
        return [], errors

    results: list[dict[str, Any]] = []
    for spec in selected_specs:
        try:
            module = _load_plugin_module(spec.plugin_id)
            run_fn = getattr(module, "run", None)
            if run_fn is None or not callable(run_fn):
                errors.append(f"Plugin '{spec.plugin_id}' has no callable run(context).")
                continue
            payload = run_fn(context)
            if not isinstance(payload, dict):
                errors.append(f"Plugin '{spec.plugin_id}' returned non-dict payload.")
                continue

            result = PluginExecutionResult(
                plugin_id=spec.plugin_id,
                title=spec.title,
                description=spec.description,
                scope=scope,
                summary=str(payload.get("summary") or "No plugin summary."),
                severity=str(payload.get("severity") or "INFO").upper(),
                highlights=tuple(str(item) for item in (payload.get("highlights") or [])),
                data=_normalize_data_payload(payload.get("data")),
            )
            results.append(
                {
                    "id": result.plugin_id,
                    "title": result.title,
                    "description": result.description,
                    "scope": result.scope,
                    "summary": result.summary,
                    "severity": result.severity,
                    "highlights": list(result.highlights),
                    "data": result.data,
                }
            )
        except Exception as exc:  # pragma: no cover - plugin safety guard
            errors.append(f"Plugin '{spec.plugin_id}' failed: {exc}")

    return results, errors
