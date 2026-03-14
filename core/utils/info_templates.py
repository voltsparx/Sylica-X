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

"""Curated info-templates for plugin/filter/module arrangements."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, TypedDict


class InfoTemplate(TypedDict):
    id: str
    label: str
    description: str
    scopes: tuple[str, ...]
    plugins: tuple[str, ...]
    filters: tuple[str, ...]
    module_tags: tuple[str, ...]
    notes: str
    aliases: tuple[str, ...]


INFO_TEMPLATES: tuple[InfoTemplate, ...] = (
    {
        "id": "contact-discovery",
        "label": "Contact Discovery",
        "description": "Prioritize public contact signals and cross-platform attribution.",
        "scopes": ("profile", "fusion"),
        "plugins": (
            "contact_lattice",
            "orbit_link_matrix",
            "link_outbound_risk_profiler",
            "account_recovery_exposure_probe",
        ),
        "filters": (
            "contact_canonicalizer",
            "contact_quality_filter",
            "mailbox_provider_profiler",
            "link_hygiene_filter",
        ),
        "module_tags": ("identity", "enrichment", "reporting", "correlation"),
        "notes": "Use only for accounts you own or have explicit permission to assess.",
        "aliases": ("contacts", "contact", "reachability"),
    },
    {
        "id": "identity-correlation",
        "label": "Identity Correlation",
        "description": "Strengthen persona/identity links across profile signals.",
        "scopes": ("profile", "fusion"),
        "plugins": (
            "identity_fusion_core",
            "cross_platform_activity_timeline",
            "threat_conductor",
            "orbit_link_matrix",
        ),
        "filters": (
            "entity_name_resolver",
            "signal_lane_fusion",
            "evidence_consistency_filter",
            "noise_suppression_filter",
        ),
        "module_tags": ("identity", "correlation", "enrichment", "reporting"),
        "notes": "Use only for accounts you own or have explicit permission to assess.",
        "aliases": ("identity", "correlate", "persona"),
    },
    {
        "id": "account-protection",
        "label": "Account Protection",
        "description": "Highlight impersonation risk and recovery exposure.",
        "scopes": ("profile", "fusion"),
        "plugins": (
            "account_recovery_exposure_probe",
            "username_impersonation_probe",
            "threat_conductor",
            "link_outbound_risk_profiler",
        ),
        "filters": (
            "exposure_tier_matrix",
            "triage_priority_filter",
            "sensitive_lexicon_guard",
            "evidence_consistency_filter",
        ),
        "module_tags": ("identity", "risk", "reporting", "correlation"),
        "notes": "Use only for accounts you own or have explicit permission to assess.",
        "aliases": ("account", "protection", "impersonation"),
    },
    {
        "id": "surface-risk",
        "label": "Surface Risk",
        "description": "Focus on takeover risk and surface misconfiguration signals.",
        "scopes": ("surface", "fusion"),
        "plugins": (
            "subdomain_risk_atlas",
            "domain_takeover_risk_probe",
            "header_hardening_probe",
            "security_txt_analyzer",
        ),
        "filters": (
            "takeover_priority_filter",
            "subdomain_attack_path_filter",
            "disclosure_readiness_filter",
            "evidence_consistency_filter",
        ),
        "module_tags": ("infrastructure", "risk", "web", "reporting"),
        "notes": "Use only for domains you own or are authorized to assess.",
        "aliases": ("surface", "risk", "takeover"),
    },
    {
        "id": "surface-inventory",
        "label": "Surface Inventory",
        "description": "Enumerate surface assets with stability + ownership context.",
        "scopes": ("surface", "fusion"),
        "plugins": (
            "subdomain_risk_atlas",
            "header_hardening_probe",
            "rdap_lifecycle_inspector",
            "surface_transport_stability_probe",
        ),
        "filters": (
            "noise_suppression_filter",
            "exposure_tier_matrix",
            "triage_priority_filter",
            "evidence_consistency_filter",
        ),
        "module_tags": ("infrastructure", "web", "enrichment", "reporting"),
        "notes": "Use only for domains you own or are authorized to assess.",
        "aliases": ("inventory", "surface-map", "assets"),
    },
    {
        "id": "fusion-coverage",
        "label": "Fusion Coverage",
        "description": "Broad correlation and coverage across profile + surface signals.",
        "scopes": ("fusion",),
        "plugins": (
            "signal_fusion_core",
            "threat_conductor",
            "module_capability_matrix",
            "cross_platform_activity_timeline",
        ),
        "filters": (
            "signal_lane_fusion",
            "exposure_tier_matrix",
            "evidence_consistency_filter",
            "link_hygiene_filter",
        ),
        "module_tags": ("correlation", "identity", "infrastructure", "reporting"),
        "notes": "Use only for targets you own or have explicit permission to assess.",
        "aliases": ("fusion", "coverage", "full"),
    },
)


def _template_index() -> dict[str, InfoTemplate]:
    index: dict[str, InfoTemplate] = {}
    for template in INFO_TEMPLATES:
        keys = [template.get("id", "")]
        keys.extend(template.get("aliases", ()))
        for key in keys:
            normalized = str(key or "").strip().lower()
            if not normalized:
                continue
            index[normalized] = template
    return index


_INFO_TEMPLATE_INDEX = _template_index()


def info_template_ids() -> list[str]:
    return [template["id"] for template in INFO_TEMPLATES]


def list_info_templates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for template in INFO_TEMPLATES:
        rows.append(
            {
                "id": template["id"],
                "label": template["label"],
                "description": template["description"],
                "scopes": list(template["scopes"]),
                "plugins": list(template["plugins"]),
                "filters": list(template["filters"]),
                "module_tags": list(template["module_tags"]),
                "notes": template["notes"],
            }
        )
    return rows


def get_info_template(template_id: str, *, scope: str | None = None) -> InfoTemplate:
    normalized = str(template_id or "").strip().lower()
    if not normalized:
        raise ValueError("Info-template id is required.")
    template = _INFO_TEMPLATE_INDEX.get(normalized)
    if template is None:
        available = ", ".join(info_template_ids())
        raise ValueError(f"Unknown info-template '{template_id}'. Available: {available}")
    if scope:
        normalized_scope = str(scope).strip().lower()
        if normalized_scope and normalized_scope not in template["scopes"]:
            supported = ", ".join(template["scopes"])
            raise ValueError(
                f"Info-template '{template['id']}' is not compatible with scope '{normalized_scope}'. "
                f"Supported scopes: {supported}"
            )
    return deepcopy(template)


def merge_selectors(base: Iterable[str], extra: Iterable[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in list(base) + list(extra):
        token = str(item or "").strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(token)
    return merged

