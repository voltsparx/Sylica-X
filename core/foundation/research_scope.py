# ------------------------------------------------------------------------------
# SPDX-License-Identifier: Proprietary
#
# Sylica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Sylica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root
#
# This file is part of Sylica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ------------------------------------------------------------------------------

"""Authorized-scope and research-policy guardrails for the framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import ip_address, ip_network
from typing import Iterable


AUTHORIZED_RESEARCH_NOTICE: tuple[str, ...] = (
    "Authorized research only. Investigate public data or explicitly approved targets.",
    "Sylica-X avoids exploitation, evasion, brute force, and target modification.",
)

FORBIDDEN_CAPABILITIES: tuple[str, ...] = (
    "exploit_delivery",
    "payload_execution",
    "ip_spoofing",
    "idle_scanning",
    "packet_fragmentation_evasion",
    "credential_brute_force",
    "authentication_bypass",
    "target_modification",
    "unauthorized_collection",
)

SUPPORTED_RESEARCH_CAPABILITIES: tuple[str, ...] = (
    "passive_osint_collection",
    "active_reconnaissance",
    "service_banner_collection",
    "vulnerability_lookup",
    "metadata_extraction",
    "relationship_mapping",
    "confidence_scoring",
    "report_generation",
)


def _normalize_scope_value(value: str) -> str:
    """Normalize domains, hosts, or URLs for scope checks."""

    normalized = value.strip().lower()
    if normalized.startswith("http://"):
        normalized = normalized.removeprefix("http://")
    if normalized.startswith("https://"):
        normalized = normalized.removeprefix("https://")
    return normalized.rstrip("/")


@dataclass(frozen=True)
class ScopeBoundary:
    """Define approved domains, hosts, and networks for an investigation."""

    approved_domains: tuple[str, ...] = ()
    approved_hosts: tuple[str, ...] = ()
    approved_networks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "approved_domains",
            tuple(_normalize_scope_value(value) for value in self.approved_domains if value.strip()),
        )
        object.__setattr__(
            self,
            "approved_hosts",
            tuple(_normalize_scope_value(value) for value in self.approved_hosts if value.strip()),
        )
        object.__setattr__(
            self,
            "approved_networks",
            tuple(value.strip() for value in self.approved_networks if value.strip()),
        )

    def contains(self, investigation_target: str) -> bool:
        """Verify that a target is inside the explicitly approved scope."""

        normalized_target = _normalize_scope_value(investigation_target)
        if not normalized_target:
            return False

        if normalized_target in self.approved_hosts:
            return True

        for approved_domain in self.approved_domains:
            if normalized_target == approved_domain or normalized_target.endswith(f".{approved_domain}"):
                return True

        try:
            target_ip = ip_address(normalized_target)
        except ValueError:
            return False

        for approved_host in self.approved_hosts:
            try:
                if target_ip == ip_address(approved_host):
                    return True
            except ValueError:
                continue

        for approved_network in self.approved_networks:
            try:
                if target_ip in ip_network(approved_network, strict=False):
                    return True
            except ValueError:
                continue

        return False


@dataclass(frozen=True)
class ResearchPolicy:
    """Capture the equal-weight research rules that govern Sylica-X behavior."""

    allowed_capabilities: tuple[str, ...] = SUPPORTED_RESEARCH_CAPABILITIES
    forbidden_capabilities: tuple[str, ...] = FORBIDDEN_CAPABILITIES
    require_timeout_controls: bool = True
    require_delay_controls: bool = True
    require_typed_results: bool = True
    require_passive_active_separation: bool = True

    def ensure_capabilities_allowed(self, requested_capabilities: Iterable[str]) -> tuple[str, ...]:
        """Reject forbidden or unsupported capabilities before execution."""

        normalized_requested = tuple(
            capability.strip().lower() for capability in requested_capabilities if capability.strip()
        )
        forbidden_requested = tuple(
            capability for capability in normalized_requested if capability in self.forbidden_capabilities
        )
        if forbidden_requested:
            raise ValueError(
                "Requested capabilities are explicitly forbidden in Sylica-X: "
                + ", ".join(forbidden_requested)
            )

        unsupported_requested = tuple(
            capability for capability in normalized_requested if capability not in self.allowed_capabilities
        )
        if unsupported_requested:
            raise ValueError(
                "Requested capabilities are outside the currently supported research scope: "
                + ", ".join(unsupported_requested)
            )
        return normalized_requested

    @property
    def assessment_meaning(self) -> tuple[str, ...]:
        """Summarize the shared meaning across the assessment documents."""

        return (
            "All assessment documents are equal-weight framework requirements.",
            "Sylica-X is an authorized research framework for passive and active reconnaissance.",
            "Outputs must remain typed, entity-centric, source-aware, and confidence-aware.",
            "Active collection must stay scope-validated, timeout-aware, and delay-aware.",
            "Exploit delivery, evasion, brute force, auth bypass, and target modification stay outside the framework.",
        )


DEFAULT_RESEARCH_POLICY = ResearchPolicy()


@dataclass(frozen=True)
class InvestigationProfile:
    """Describe the guardrails, timing, and scope of one investigation run."""

    investigation_target: str
    scope_boundary: ScopeBoundary
    requested_capabilities: tuple[str, ...] = field(default_factory=tuple)
    request_timeout_seconds: float = 10.0
    request_delay_seconds: float = 0.0
    allow_passive_collection: bool = True
    allow_active_collection: bool = False
    research_policy: ResearchPolicy = DEFAULT_RESEARCH_POLICY

    def __post_init__(self) -> None:
        normalized_target = self.investigation_target.strip()
        if not normalized_target:
            raise ValueError("Investigation target is required.")
        if self.request_timeout_seconds <= 0:
            raise ValueError("Request timeout must be greater than zero.")
        if self.request_delay_seconds < 0:
            raise ValueError("Request delay cannot be negative.")
        if not self.allow_passive_collection and not self.allow_active_collection:
            raise ValueError("At least one collection mode must be enabled.")
        if self.allow_active_collection and not self.scope_boundary.contains(normalized_target):
            raise ValueError("Active reconnaissance requires the target to be inside authorized scope.")

        normalized_capabilities = self.research_policy.ensure_capabilities_allowed(
            self.requested_capabilities
        )
        object.__setattr__(self, "investigation_target", normalized_target)
        object.__setattr__(self, "requested_capabilities", normalized_capabilities)

    @property
    def assessment_meaning(self) -> tuple[str, ...]:
        """Expose the equal-weight assessment rules attached to this investigation."""

        return self.research_policy.assessment_meaning
