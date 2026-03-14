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

"""Extension control plane for plugin/filter automation and validation."""

from __future__ import annotations

from dataclasses import dataclass

from core.extensions.selector_keys import selector_keys
from core.extensions.signal_forge import list_plugin_descriptors
from core.extensions.signal_sieve import list_filter_descriptors


VALID_SCOPES = {"profile", "surface", "fusion"}
VALID_CONTROL_MODES = {"auto", "manual", "hybrid"}
MODE_ALIASES = {
    "safe": "fast",
    "quick": "fast",
    "fast": "fast",
    "standard": "balanced",
    "balanced": "balanced",
    "deep": "deep",
    "aggressive": "max",
    "max": "max",
}

MODE_PLUGIN_BUDGET = {"fast": 2, "balanced": 4, "deep": 8, "max": 99}
MODE_FILTER_BUDGET = {"fast": 2, "balanced": 4, "deep": 8, "max": 99}

AUTO_EXTENSION_MATRIX: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    "profile": {
        "fast": {
            "plugins": ("threat_conductor",),
            "filters": ("noise_suppression_filter",),
        },
        "balanced": {
            "plugins": ("threat_conductor", "orbit_link_matrix"),
            "filters": ("noise_suppression_filter", "exposure_tier_matrix"),
        },
        "deep": {
            "plugins": (
                "threat_conductor",
                "orbit_link_matrix",
                "contact_lattice",
                "account_recovery_exposure_probe",
                "link_outbound_risk_profiler",
            ),
            "filters": (
                "noise_suppression_filter",
                "exposure_tier_matrix",
                "contact_canonicalizer",
                "entity_name_resolver",
                "triage_priority_filter",
                "contact_quality_filter",
                "link_hygiene_filter",
                "evidence_consistency_filter",
            ),
        },
        "max": {
            "plugins": (
                "threat_conductor",
                "orbit_link_matrix",
                "contact_lattice",
                "cross_platform_activity_timeline",
                "identity_fusion_core",
                "module_capability_matrix",
                "account_recovery_exposure_probe",
                "link_outbound_risk_profiler",
                "username_impersonation_probe",
            ),
            "filters": (
                "noise_suppression_filter",
                "exposure_tier_matrix",
                "contact_canonicalizer",
                "entity_name_resolver",
                "module_filter_router",
                "signal_lane_fusion",
                "pii_signal_classifier",
                "triage_priority_filter",
                "contact_quality_filter",
                "link_hygiene_filter",
                "evidence_consistency_filter",
            ),
        },
    },
    "surface": {
        "fast": {
            "plugins": ("header_hardening_probe",),
            "filters": ("noise_suppression_filter",),
        },
        "balanced": {
            "plugins": ("header_hardening_probe", "subdomain_risk_atlas"),
            "filters": ("noise_suppression_filter", "exposure_tier_matrix"),
        },
        "deep": {
            "plugins": (
                "header_hardening_probe",
                "subdomain_risk_atlas",
                "domain_takeover_risk_probe",
                "module_capability_matrix",
                "rdap_lifecycle_inspector",
                "surface_transport_stability_probe",
            ),
            "filters": (
                "noise_suppression_filter",
                "exposure_tier_matrix",
                "takeover_priority_filter",
                "disclosure_readiness_filter",
                "triage_priority_filter",
                "subdomain_attack_path_filter",
                "evidence_consistency_filter",
            ),
        },
        "max": {
            "plugins": (
                "header_hardening_probe",
                "subdomain_risk_atlas",
                "domain_takeover_risk_probe",
                "security_txt_analyzer",
                "threat_conductor",
                "module_capability_matrix",
                "rdap_lifecycle_inspector",
                "surface_transport_stability_probe",
            ),
            "filters": (
                "noise_suppression_filter",
                "exposure_tier_matrix",
                "takeover_priority_filter",
                "disclosure_readiness_filter",
                "module_filter_router",
                "signal_lane_fusion",
                "triage_priority_filter",
                "subdomain_attack_path_filter",
                "evidence_consistency_filter",
            ),
        },
    },
    "fusion": {
        "fast": {
            "plugins": ("signal_fusion_core",),
            "filters": ("signal_lane_fusion",),
        },
        "balanced": {
            "plugins": ("signal_fusion_core", "threat_conductor"),
            "filters": ("signal_lane_fusion", "exposure_tier_matrix"),
        },
        "deep": {
            "plugins": (
                "signal_fusion_core",
                "threat_conductor",
                "email_pattern_inference",
                "module_capability_matrix",
                "account_recovery_exposure_probe",
                "link_outbound_risk_profiler",
                "rdap_lifecycle_inspector",
                "surface_transport_stability_probe",
            ),
            "filters": (
                "signal_lane_fusion",
                "exposure_tier_matrix",
                "contact_canonicalizer",
                "mailbox_provider_profiler",
                "triage_priority_filter",
                "contact_quality_filter",
                "link_hygiene_filter",
                "evidence_consistency_filter",
            ),
        },
        "max": {
            "plugins": (
                "signal_fusion_core",
                "threat_conductor",
                "email_pattern_inference",
                "module_capability_matrix",
                "subdomain_risk_atlas",
                "cross_platform_activity_timeline",
                "account_recovery_exposure_probe",
                "link_outbound_risk_profiler",
                "username_impersonation_probe",
                "rdap_lifecycle_inspector",
                "surface_transport_stability_probe",
            ),
            "filters": (
                "signal_lane_fusion",
                "exposure_tier_matrix",
                "contact_canonicalizer",
                "mailbox_provider_profiler",
                "module_filter_router",
                "pii_signal_classifier",
                "triage_priority_filter",
                "contact_quality_filter",
                "link_hygiene_filter",
                "subdomain_attack_path_filter",
                "evidence_consistency_filter",
            ),
        },
    },
}

PLUGIN_CONFLICT_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "signal_fusion_core",
        "identity_fusion_core",
        "Both plugins provide fusion-core aggregation; select only one.",
    ),
)
FILTER_CONFLICT_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "pii_signal_classifier",
        "sensitive_lexicon_guard",
        "Both filters enforce overlapping sensitivity suppression; select one.",
    ),
)
CROSS_CONFLICT_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "module_capability_matrix",
        "module_filter_router",
        "Module matrix plugin conflicts with module router filter in strict/manual mode.",
    ),
)


@dataclass(frozen=True)
class ExtensionControlPlan:
    """Resolved extension execution plan with validation metadata."""

    scope: str
    scan_mode: str
    control_mode: str
    plugins: tuple[str, ...]
    filters: tuple[str, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def normalize_scan_mode(mode: str) -> str:
    """Normalize mode aliases into fast/balanced/deep/max."""

    key = str(mode or "").strip().lower()
    return MODE_ALIASES.get(key, "balanced")


def merge_scan_modes(primary_mode: str, secondary_mode: str) -> str:
    """Merge two mode names into highest-depth mode."""

    order = {"fast": 1, "balanced": 2, "deep": 3, "max": 4}
    first = normalize_scan_mode(primary_mode)
    second = normalize_scan_mode(secondary_mode)
    return first if order[first] >= order[second] else second


def _build_lookup(descriptors: list[dict[str, object]]) -> tuple[dict[str, str], set[str]]:
    by_key: dict[str, str] = {}
    ids: set[str] = set()
    for descriptor in descriptors:
        item_id = str(descriptor.get("id", "")).strip().lower()
        if not item_id:
            continue
        ids.add(item_id)

        for key in selector_keys(item_id):
            by_key.setdefault(key, item_id)

        title = str(descriptor.get("title", "")).strip()
        if title:
            for key in selector_keys(title):
                by_key.setdefault(key, item_id)

        aliases = descriptor.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                for key in selector_keys(str(alias)):
                    by_key.setdefault(key, item_id)

    return by_key, ids


def _resolve_selector_ids(selectors: list[str], lookup: dict[str, str]) -> tuple[list[str], list[str]]:
    selected: list[str] = []
    unknown: list[str] = []
    seen: set[str] = set()

    for raw in selectors:
        keys = selector_keys(raw)
        if not keys:
            continue
        matched: str | None = None
        for key in keys:
            matched = lookup.get(key)
            if matched is not None:
                break
        if matched is None:
            unknown.append(raw)
            continue
        if matched in seen:
            continue
        selected.append(matched)
        seen.add(matched)

    return selected, unknown


def _unique(items: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return tuple(ordered)


def _auto_extensions_for_scope(
    *,
    scope: str,
    mode: str,
    available_plugins: set[str],
    available_filters: set[str],
) -> tuple[list[str], list[str]]:
    matrix = AUTO_EXTENSION_MATRIX.get(scope, AUTO_EXTENSION_MATRIX["profile"])
    mode_matrix = matrix.get(mode, matrix["balanced"])

    auto_plugins = [item for item in mode_matrix.get("plugins", ()) if item in available_plugins]
    auto_filters = [item for item in mode_matrix.get("filters", ()) if item in available_filters]
    return auto_plugins, auto_filters


def _apply_conflict_rules(
    *,
    plugins: list[str],
    filters: list[str],
    control_mode: str,
    errors: list[str],
    warnings: list[str],
) -> tuple[list[str], list[str]]:
    plugin_set = set(plugins)
    filter_set = set(filters)

    for keep_id, drop_id, reason in PLUGIN_CONFLICT_RULES:
        if keep_id in plugin_set and drop_id in plugin_set:
            if control_mode == "manual":
                errors.append(f"Plugin conflict: {keep_id} + {drop_id}. {reason}")
            else:
                plugin_set.remove(drop_id)
                warnings.append(f"Plugin conflict resolved: removed {drop_id}. {reason}")

    for keep_id, drop_id, reason in FILTER_CONFLICT_RULES:
        if keep_id in filter_set and drop_id in filter_set:
            if control_mode == "manual":
                errors.append(f"Filter conflict: {keep_id} + {drop_id}. {reason}")
            else:
                filter_set.remove(drop_id)
                warnings.append(f"Filter conflict resolved: removed {drop_id}. {reason}")

    for plugin_id, filter_id, reason in CROSS_CONFLICT_RULES:
        if plugin_id in plugin_set and filter_id in filter_set:
            if control_mode == "manual":
                errors.append(f"Plugin/filter conflict: {plugin_id} + {filter_id}. {reason}")
            else:
                filter_set.remove(filter_id)
                warnings.append(
                    f"Plugin/filter conflict resolved: removed filter {filter_id}. {reason}"
                )

    resolved_plugins = [item for item in plugins if item in plugin_set]
    resolved_filters = [item for item in filters if item in filter_set]
    return resolved_plugins, resolved_filters


def resolve_extension_control(
    *,
    scope: str,
    scan_mode: str,
    control_mode: str,
    requested_plugins: list[str] | None,
    requested_filters: list[str] | None,
    include_all_plugins: bool,
    include_all_filters: bool,
) -> ExtensionControlPlan:
    """Resolve extension execution plan with manual/auto/hybrid controls."""

    errors: list[str] = []
    warnings: list[str] = []

    normalized_scope = str(scope or "").strip().lower()
    normalized_mode = normalize_scan_mode(scan_mode)
    normalized_control = str(control_mode or "").strip().lower()
    if normalized_scope not in VALID_SCOPES:
        errors.append(f"Unsupported extension scope: {scope}")
    if normalized_control not in VALID_CONTROL_MODES:
        errors.append(f"Unsupported extension control mode: {control_mode}")
    if include_all_plugins or include_all_filters:
        errors.append(
            "Bulk selection for plugins/filters is disabled. "
            "Use explicit selectors or --info-template instead."
        )
        include_all_plugins = False
        include_all_filters = False

    scoped_plugin_descriptors = list_plugin_descriptors(
        scope=normalized_scope if normalized_scope in VALID_SCOPES else None
    )
    scoped_filter_descriptors = list_filter_descriptors(
        scope=normalized_scope if normalized_scope in VALID_SCOPES else None
    )
    global_plugin_descriptors = list_plugin_descriptors(scope=None)
    global_filter_descriptors = list_filter_descriptors(scope=None)

    plugin_lookup, available_plugin_ids = _build_lookup(scoped_plugin_descriptors)
    filter_lookup, available_filter_ids = _build_lookup(scoped_filter_descriptors)
    global_plugin_lookup, _ = _build_lookup(global_plugin_descriptors)
    global_filter_lookup, _ = _build_lookup(global_filter_descriptors)

    requested_plugin_names = [item for item in (requested_plugins or []) if str(item).strip()]
    requested_filter_names = [item for item in (requested_filters or []) if str(item).strip()]

    if include_all_plugins and requested_plugin_names:
        errors.append("Cannot combine bulk plugin selection with explicit plugin selectors.")
    if include_all_filters and requested_filter_names:
        errors.append("Cannot combine bulk filter selection with explicit filter selectors.")

    if normalized_control == "auto" and (
        include_all_plugins or include_all_filters or requested_plugin_names or requested_filter_names
    ):
        errors.append(
            "Auto extension control cannot be combined with manual plugin/filter flags. "
            "Use --extension-control hybrid or manual."
        )

    manual_plugins: list[str]
    manual_filters: list[str]
    if include_all_plugins:
        manual_plugins = sorted(available_plugin_ids)
    else:
        manual_plugins, unknown_plugins = _resolve_selector_ids(requested_plugin_names, plugin_lookup)
        for unknown in unknown_plugins:
            keys = selector_keys(unknown)
            if normalized_scope in VALID_SCOPES and any(key in global_plugin_lookup for key in keys):
                errors.append(
                    f"Incompatible plugin selector for scope '{normalized_scope}': {unknown}. "
                    "Inspect compatible selectors with `plugins --scope ...`."
                )
            else:
                errors.append(f"Unknown plugin selector: {unknown}")

    if include_all_filters:
        manual_filters = sorted(available_filter_ids)
    else:
        manual_filters, unknown_filters = _resolve_selector_ids(requested_filter_names, filter_lookup)
        for unknown in unknown_filters:
            keys = selector_keys(unknown)
            if normalized_scope in VALID_SCOPES and any(key in global_filter_lookup for key in keys):
                errors.append(
                    f"Incompatible filter selector for scope '{normalized_scope}': {unknown}. "
                    "Inspect compatible selectors with `filters --scope ...`."
                )
            else:
                errors.append(f"Unknown filter selector: {unknown}")

    auto_plugins, auto_filters = _auto_extensions_for_scope(
        scope=normalized_scope if normalized_scope in VALID_SCOPES else "profile",
        mode=normalized_mode,
        available_plugins=available_plugin_ids,
        available_filters=available_filter_ids,
    )

    resolved_plugins: list[str] = []
    resolved_filters: list[str] = []

    if normalized_control == "manual":
        resolved_plugins = manual_plugins
        resolved_filters = manual_filters
    elif normalized_control == "hybrid":
        resolved_plugins = list(_unique([*auto_plugins, *manual_plugins]))
        resolved_filters = list(_unique([*auto_filters, *manual_filters]))
    else:
        resolved_plugins = list(_unique(auto_plugins))
        resolved_filters = list(_unique(auto_filters))

    resolved_plugins, resolved_filters = _apply_conflict_rules(
        plugins=resolved_plugins,
        filters=resolved_filters,
        control_mode=normalized_control,
        errors=errors,
        warnings=warnings,
    )

    plugin_budget = MODE_PLUGIN_BUDGET[normalized_mode]
    filter_budget = MODE_FILTER_BUDGET[normalized_mode]
    if len(resolved_plugins) > plugin_budget and normalized_control in {"manual", "hybrid"}:
        errors.append(
            f"Mode '{normalized_mode}' allows at most {plugin_budget} plugins, got {len(resolved_plugins)}."
        )
    if len(resolved_filters) > filter_budget and normalized_control in {"manual", "hybrid"}:
        errors.append(
            f"Mode '{normalized_mode}' allows at most {filter_budget} filters, got {len(resolved_filters)}."
        )

    return ExtensionControlPlan(
        scope=normalized_scope,
        scan_mode=normalized_mode,
        control_mode=normalized_control,
        plugins=_unique(resolved_plugins),
        filters=_unique(resolved_filters),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
