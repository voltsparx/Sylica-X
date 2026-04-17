# ──────────────────────────────────────────────────────────────────────────────
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
# ──────────────────────────────────────────────────────────────────────────────

"""Shared helpers for user-selectable attachables such as modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.extensions.selector_keys import selector_keys
from modules.catalog import ensure_module_catalog, select_module_entries


MODULE_ATTACHABLE_SCOPES = {"profile", "surface", "fusion"}
MAX_ATTACHED_MODULES = 12


@dataclass(frozen=True)
class ModuleAttachmentPlan:
    """Resolved module attachable selection with validation details."""

    scope: str
    module_ids: tuple[str, ...]
    entries: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def _module_lookup(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for entry in entries:
        entry_id = str(entry.get("id", "")).strip().lower()
        if not entry_id:
            continue
        keys = set(selector_keys(entry_id))
        file_value = str(entry.get("file", "")).strip()
        path_value = str(entry.get("path", "")).strip()
        framework = str(entry.get("framework", "")).strip()
        if file_value:
            keys.update(selector_keys(file_value))
        if path_value:
            keys.update(selector_keys(path_value))
        if framework and file_value:
            keys.update(selector_keys(f"{framework} {file_value}"))
        for key in keys:
            lookup.setdefault(key, entry)
    return lookup


def _sanitize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    metrics = entry.get("metrics", {}) if isinstance(entry.get("metrics"), dict) else {}
    return {
        "id": str(entry.get("id", "")).strip(),
        "framework": str(entry.get("framework", "")).strip(),
        "file": str(entry.get("file", "")).strip(),
        "kind": str(entry.get("kind", "")).strip(),
        "scopes": list(entry.get("scopes", []) or []),
        "capabilities": list(entry.get("capabilities", []) or []),
        "power_score": int(metrics.get("power_score", 0) or 0),
        "confidence_score": int(metrics.get("confidence_score", 0) or 0),
    }


def resolve_module_attachments(
    *,
    scope: str,
    requested_modules: list[str] | None,
) -> ModuleAttachmentPlan:
    """Resolve selected module-catalog entries for a workflow scope."""

    normalized_scope = str(scope or "").strip().lower()
    requested = [str(item).strip() for item in (requested_modules or []) if str(item).strip()]
    if not requested:
        return ModuleAttachmentPlan(
            scope=normalized_scope,
            module_ids=(),
            entries=(),
            errors=(),
            warnings=(),
        )

    if normalized_scope not in MODULE_ATTACHABLE_SCOPES:
        return ModuleAttachmentPlan(
            scope=normalized_scope,
            module_ids=(),
            entries=(),
            errors=(f"Module attachments are not supported for scope '{normalized_scope}'.",),
            warnings=(),
        )

    try:
        catalog = ensure_module_catalog(refresh=False, validate_catalog=True)
        scoped_entries = select_module_entries(catalog, scope=normalized_scope, kind="all", limit=1000)
        all_entries = select_module_entries(catalog, scope="all", kind="all", limit=1000)
    except Exception as exc:  # pragma: no cover - defensive
        return ModuleAttachmentPlan(
            scope=normalized_scope,
            module_ids=(),
            entries=(),
            errors=(f"Unable to load module catalog: {exc}",),
            warnings=(),
        )

    scoped_lookup = _module_lookup(scoped_entries)
    global_lookup = _module_lookup(all_entries)
    selected: list[dict[str, Any]] = []
    selected_ids: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()

    for raw in requested:
        matched: dict[str, Any] | None = None
        for key in selector_keys(raw):
            matched = scoped_lookup.get(key)
            if matched is not None:
                break
        if matched is None:
            if any(key in global_lookup for key in selector_keys(raw)):
                errors.append(
                    f"Incompatible module selector for scope '{normalized_scope}': {raw}. "
                    "Use `modules --scope ...` to inspect compatible module entries."
                )
            else:
                errors.append(f"Unknown module selector: {raw}")
            continue

        entry_id = str(matched.get("id", "")).strip().lower()
        if not entry_id or entry_id in seen:
            continue
        seen.add(entry_id)
        selected.append(_sanitize_entry(matched))
        selected_ids.append(entry_id)

    if len(selected_ids) > MAX_ATTACHED_MODULES:
        errors.append(
            f"Too many attached modules requested ({len(selected_ids)}). "
            f"Select at most {MAX_ATTACHED_MODULES} module entries."
        )

    warnings = ()
    if selected_ids:
        warnings = (
            "Attached modules are catalog-backed research context. They are tracked in configuration and reports, but they do not execute directly like plugins or filters.",
        )

    return ModuleAttachmentPlan(
        scope=normalized_scope,
        module_ids=tuple(selected_ids),
        entries=tuple(selected),
        errors=tuple(errors),
        warnings=warnings,
    )
