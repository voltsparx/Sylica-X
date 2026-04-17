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

"""Signal Forge: plugin discovery and execution engine."""

from __future__ import annotations

from collections.abc import Mapping
import importlib
import pkgutil
from typing import Any

from core.extensions.forge_schema import PluginContext, PluginExecutionResult, PluginSpec
from core.extensions.selector_keys import selector_keys


PLUGIN_PACKAGE = "plugins"
VALID_SCOPES = {"profile", "surface", "fusion", "ocr"}
_CRYPTO_MARKERS: tuple[str, ...] = (
    "cryptography",
    "crypto",
    "cipher",
    "aes",
    "xor",
    "rot13",
    "rsa",
    "pgp",
    "gpg",
    "fernet",
)
_CRYPTO_KIND_MARKERS: dict[str, tuple[str, ...]] = {
    "aes": ("aes",),
    "xor": ("xor",),
    "rot13": ("rot13",),
}


def _normalize_data_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _plugin_crypto_kind_from_fields(
    *,
    module_name: str,
    plugin_id: str,
    title: str,
    description: str,
    aliases: tuple[str, ...],
) -> str | None:
    haystack = " ".join(
        (
            module_name,
            plugin_id,
            title,
            description,
            " ".join(aliases),
        )
    ).lower()
    for kind, markers in _CRYPTO_KIND_MARKERS.items():
        if any(marker in haystack for marker in markers):
            return kind
    return None


def _plugin_group_from_fields(
    *,
    module_name: str,
    plugin_id: str,
    title: str,
    description: str,
    aliases: tuple[str, ...],
) -> str:
    if module_name.startswith("crypto."):
        return "cryptography"
    haystack = " ".join(
        (
            module_name,
            plugin_id,
            title,
            description,
            " ".join(aliases),
        )
    ).lower()
    if any(marker in haystack for marker in _CRYPTO_MARKERS):
        return "cryptography"
    return "core"


def classify_plugin_group(descriptor: Mapping[str, object]) -> str:
    """Classify plugin descriptor group for inventory display."""

    aliases_raw = descriptor.get("aliases")
    aliases: tuple[str, ...]
    if isinstance(aliases_raw, list):
        aliases = tuple(str(item).strip().lower() for item in aliases_raw if str(item).strip())
    else:
        aliases = ()
    return _plugin_group_from_fields(
        module_name=str(descriptor.get("module_name") or "").strip().lower(),
        plugin_id=str(descriptor.get("id") or "").strip().lower(),
        title=str(descriptor.get("title") or "").strip().lower(),
        description=str(descriptor.get("description") or "").strip().lower(),
        aliases=aliases,
    )


def classify_plugin_crypto_kind(descriptor: Mapping[str, object]) -> str | None:
    """Classify cryptography plugin subtype when available."""

    aliases_raw = descriptor.get("aliases")
    aliases: tuple[str, ...]
    if isinstance(aliases_raw, list):
        aliases = tuple(str(item).strip().lower() for item in aliases_raw if str(item).strip())
    else:
        aliases = ()
    return _plugin_crypto_kind_from_fields(
        module_name=str(descriptor.get("module_name") or "").strip().lower(),
        plugin_id=str(descriptor.get("id") or "").strip().lower(),
        title=str(descriptor.get("title") or "").strip().lower(),
        description=str(descriptor.get("description") or "").strip().lower(),
        aliases=aliases,
    )


def classify_plugin_special_type(descriptor: Mapping[str, object]) -> str | None:
    """Backward-compatibility alias returning legacy special type names."""

    return "cryptography" if classify_plugin_group(descriptor) == "cryptography" else None


def _is_private_module_name(module_name: str) -> bool:
    return any(part.startswith("_") for part in module_name.split("."))


def _iter_nested_module_names(root_package: str) -> list[str]:
    package = importlib.import_module(root_package)
    names: list[str] = []
    prefix = f"{root_package}."
    for module_info in pkgutil.walk_packages(package.__path__, prefix=prefix):
        full_name = module_info.name
        if not full_name.startswith(prefix):
            continue
        module_name = full_name[len(prefix) :]
        if module_info.ispkg:
            continue
        if _is_private_module_name(module_name):
            continue
        names.append(module_name)
    return sorted(names)


def _iter_top_level_module_names(root_package: str) -> list[str]:
    package = importlib.import_module(root_package)
    names: list[str] = []
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.ispkg:
            continue
        if module_info.name.startswith("_"):
            continue
        names.append(module_info.name)
    return sorted(names)


def _iter_module_names_with_fallback(root_package: str) -> list[str]:
    try:
        nested = _iter_nested_module_names(root_package)
    except Exception:
        nested = []
    if nested:
        return nested
    return _iter_top_level_module_names(root_package)


def _iter_plugin_module_names() -> list[str]:
    return _iter_module_names_with_fallback(PLUGIN_PACKAGE)


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
        module_name=module_name,
        plugin_id=plugin_id,
        title=title,
        description=description,
        scopes=valid_scopes,
        version=str(raw.get("version") or "1.0"),
        author=str(raw.get("author") or "Silica-X"),
        aliases=aliases,
    )


def _discover_plugin_specs(scope: str | None = None) -> tuple[list[PluginSpec], list[str]]:
    specs: list[PluginSpec] = []
    errors: list[str] = []
    try:
        module_names = _iter_plugin_module_names()
    except Exception as exc:  # pragma: no cover - defensive import safety
        errors.append(f"Plugin package discovery failed: {exc}")
        return [], errors

    for module_name in module_names:
        try:
            module = _load_plugin_module(module_name)
        except Exception as exc:  # pragma: no cover - defensive import safety
            errors.append(f"Plugin module '{module_name}' import failed: {exc}")
            continue
        raw = getattr(module, "PLUGIN_SPEC", {})
        if not isinstance(raw, dict):
            errors.append(f"Plugin module '{module_name}' has invalid PLUGIN_SPEC (expected dict).")
            continue
        spec = _normalize_spec(module_name, raw)
        if scope and scope not in spec.scopes:
            continue
        specs.append(spec)
    return sorted(specs, key=lambda item: item.plugin_id), errors


def list_plugin_specs(scope: str | None = None) -> list[PluginSpec]:
    specs, _ = _discover_plugin_specs(scope=scope)
    return specs


def list_plugin_discovery_errors(scope: str | None = None) -> list[str]:
    _, errors = _discover_plugin_specs(scope=scope)
    return errors


def list_plugin_descriptors(scope: str | None = None) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for spec in list_plugin_specs(scope=scope):
        plugin_group = _plugin_group_from_fields(
            module_name=spec.module_name,
            plugin_id=spec.plugin_id,
            title=spec.title,
            description=spec.description,
            aliases=spec.aliases,
        )
        crypto_kind = _plugin_crypto_kind_from_fields(
            module_name=spec.module_name,
            plugin_id=spec.plugin_id,
            title=spec.title,
            description=spec.description,
            aliases=spec.aliases,
        )
        descriptors.append(
            {
                "module_name": spec.module_name,
                "id": spec.plugin_id,
                "title": spec.title,
                "description": spec.description,
                "scopes": list(spec.scopes),
                "version": spec.version,
                "author": spec.author,
                "aliases": list(spec.aliases),
                "plugin_group": plugin_group,
                "crypto_kind": crypto_kind,
            }
        )
    return descriptors


def _resolve_requested_plugins(
    scope: str,
    requested_plugins: list[str] | None,
    include_all: bool,
) -> tuple[list[PluginSpec], list[str], list[str]]:
    available_specs, discovery_errors = _discover_plugin_specs(scope=scope)
    by_key: dict[str, PluginSpec] = {}
    for spec in available_specs:
        for key in selector_keys(spec.plugin_id):
            by_key.setdefault(key, spec)
        for key in selector_keys(spec.title):
            by_key.setdefault(key, spec)
        for alias in spec.aliases:
            for key in selector_keys(alias):
                by_key.setdefault(key, spec)

    if include_all:
        return available_specs, [], discovery_errors

    requested_plugins = requested_plugins or []
    unknown: list[str] = []
    selected: list[PluginSpec] = []
    seen: set[str] = set()
    for raw_name in requested_plugins:
        keys = selector_keys(raw_name)
        if not keys:
            continue
        matched_spec: PluginSpec | None = None
        for key in keys:
            matched_spec = by_key.get(key)
            if matched_spec is not None:
                break
        if matched_spec is None:
            unknown.append(raw_name)
            continue
        if matched_spec.plugin_id in seen:
            continue
        selected.append(matched_spec)
        seen.add(matched_spec.plugin_id)
    return selected, unknown, discovery_errors


def execute_plugins(
    *,
    scope: str,
    requested_plugins: list[str] | None,
    include_all: bool,
    context: PluginContext,
) -> tuple[list[dict[str, Any]], list[str]]:
    if scope not in VALID_SCOPES:
        raise ValueError(f"Unsupported plugin scope: {scope}")

    selected_specs, unknown, discovery_errors = _resolve_requested_plugins(
        scope=scope,
        requested_plugins=requested_plugins,
        include_all=include_all,
    )
    errors = [*discovery_errors, *[f"Unknown plugin requested: {name}" for name in unknown]]
    if not selected_specs:
        return [], errors

    results: list[dict[str, Any]] = []
    for spec in selected_specs:
        try:
            module = _load_plugin_module(spec.module_name)
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
