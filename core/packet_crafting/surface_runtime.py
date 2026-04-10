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

"""Surface-runtime packet-crafting summaries for read-only scan planning."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from typing import Any

from core.interface.command_spec import SurfaceScanDirectives
from core.packet_crafting import (
    PacketCraftingBundle,
    PacketCraftingCombinationEngine,
    PacketCraftingRequest,
    craft_packet_bundle,
    list_packet_crafting_profiles,
)


_PACKET_CRAFTING_SCAN_TYPES = frozenset(
    {"arp", "syn", "tcp-connect", "udp", "fin", "null", "xmas", "os-fingerprint"}
)
_PROFILE_ENGINE = PacketCraftingCombinationEngine()


@dataclass(frozen=True)
class SurfacePacketCraftingPlan:
    """Summarize read-only packet-crafting bundles for an authorized surface target."""

    investigation_target: str
    authorized_host: str
    requested_scan_types: tuple[str, ...]
    selected_ports: tuple[int, ...]
    bundles: tuple[dict[str, Any], ...]
    recommended_profiles: tuple[dict[str, Any], ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Render a JSON-safe packet-crafting plan for reports and output."""

        return {
            "investigation_target": self.investigation_target,
            "authorized_host": self.authorized_host,
            "requested_scan_types": list(self.requested_scan_types),
            "selected_ports": list(self.selected_ports),
            "bundles": list(self.bundles),
            "recommended_profiles": list(self.recommended_profiles),
            "notes": list(self.notes),
        }


def _safe_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _safe_port_list(value: object) -> list[int]:
    ports: list[int] = []
    if not isinstance(value, list):
        return ports
    for item in value:
        try:
            port = int(item)
        except (TypeError, ValueError):
            continue
        if 1 <= port <= 65535:
            ports.append(port)
    return ports


def _candidate_host(domain_result: dict[str, Any]) -> str:
    for value in _safe_text_list(domain_result.get("resolved_addresses")):
        return value
    return str(domain_result.get("target") or "").strip()


def _authorized_network_range(authorized_host: str) -> str | None:
    try:
        subject_ip = ip_address(authorized_host)
    except ValueError:
        return None
    if not subject_ip.is_private:
        return None
    return str(ip_network(f"{subject_ip}/24", strict=False))


def _selected_ports(domain_result: dict[str, Any], *, limit: int = 8) -> tuple[int, ...]:
    probe_plan = domain_result.get("surface_map", {})
    if isinstance(probe_plan, dict):
        plan_ports = probe_plan.get("probe_plan", {})
        if isinstance(plan_ports, dict):
            values = _safe_port_list(plan_ports.get("recommended_ports"))
            if values:
                return tuple(values[: max(1, int(limit))])

    surface_wordlists = domain_result.get("surface_wordlists", {})
    if isinstance(surface_wordlists, dict):
        values = _safe_port_list(surface_wordlists.get("top_ports"))
        if values:
            return tuple(values[: max(1, int(limit))])
    return ()


def _bundle_summary(bundle: PacketCraftingBundle) -> dict[str, Any]:
    artifacts = []
    for artifact in bundle.artifacts:
        artifacts.append(
            {
                "engine_id": artifact.engine_id,
                "scan_type": artifact.scan_type,
                "packet_label": artifact.packet_label,
                "packet_summary": artifact.packet_summary,
                "layer_stack": list(artifact.layer_stack),
                "authorized_host": artifact.authorized_host,
                "service_inquiry_port": artifact.service_inquiry_port,
                "timeout_seconds": artifact.timeout_seconds,
                "delay_seconds": artifact.delay_seconds,
                "response_guidance": artifact.response_guidance,
                "response_dependent": artifact.response_dependent,
            }
        )
    return {
        "bundle_id": bundle.bundle_id,
        "title": bundle.title,
        "purpose": bundle.purpose,
        "scan_types": list(bundle.scan_types),
        "artifact_count": len(bundle.artifacts),
        "artifacts": artifacts[:24],
        "notes": list(bundle.notes),
    }


def _recommended_profiles(requested_scan_types: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    requested = set(requested_scan_types)
    matches: list[dict[str, Any]] = []
    for profile in list_packet_crafting_profiles():
        overlap = len(requested.intersection(profile.scan_types))
        if overlap <= 0:
            continue
        matches.append(
            {
                "profile_id": profile.profile_id,
                "title": profile.title,
                "purpose": profile.purpose,
                "scan_types": list(profile.scan_types),
                "overlap_count": overlap,
                "notes": list(profile.notes),
            }
        )
    matches.sort(key=lambda row: (-int(row["overlap_count"]), str(row["profile_id"])))
    return tuple(matches[:4])


def build_surface_packet_crafting_plan(
    domain_result: dict[str, Any],
    *,
    scan_directives: SurfaceScanDirectives,
) -> SurfacePacketCraftingPlan:
    """Build a read-only packet-crafting plan from normalized surface scan directives."""

    investigation_target = str(domain_result.get("target") or "").strip()
    authorized_host = _candidate_host(domain_result)
    requested_scan_types = tuple(
        scan_type for scan_type in scan_directives.scan_types if scan_type in _PACKET_CRAFTING_SCAN_TYPES
    )
    selected_ports = _selected_ports(domain_result)
    notes: list[str] = []
    bundles: list[dict[str, Any]] = []

    if not investigation_target or not authorized_host:
        notes.append("Packet-crafting plan skipped because no authorized host or target was available.")
        return SurfacePacketCraftingPlan(
            investigation_target=investigation_target,
            authorized_host=authorized_host,
            requested_scan_types=requested_scan_types,
            selected_ports=selected_ports,
            bundles=(),
            recommended_profiles=(),
            notes=tuple(notes),
        )

    if not requested_scan_types:
        notes.append("No packet-crafting scan directives were requested for this surface run.")
        return SurfacePacketCraftingPlan(
            investigation_target=investigation_target,
            authorized_host=authorized_host,
            requested_scan_types=requested_scan_types,
            selected_ports=selected_ports,
            bundles=(),
            recommended_profiles=_recommended_profiles(scan_directives.scan_types),
            notes=tuple(notes),
        )

    if not selected_ports and any(scan_type != "arp" for scan_type in requested_scan_types):
        notes.append("No recommended service ports were available, so packet crafting stayed unplanned.")
        return SurfacePacketCraftingPlan(
            investigation_target=investigation_target,
            authorized_host=authorized_host,
            requested_scan_types=requested_scan_types,
            selected_ports=selected_ports,
            bundles=(),
            recommended_profiles=_recommended_profiles(requested_scan_types),
            notes=tuple(notes),
        )

    service_inquiry = PacketCraftingRequest(
        investigation_target=investigation_target,
        authorized_host=authorized_host,
        service_inquiry_ports=selected_ports,
        authorized_network_range=_authorized_network_range(authorized_host),
        timeout_seconds=max(1.0, float(domain_result.get("timeout_seconds") or 2.0)),
        delay_seconds=float(scan_directives.delay_seconds),
        include_os_fingerprint=bool(scan_directives.os_fingerprint_enabled),
    )

    for scan_type in requested_scan_types:
        try:
            bundles.append(_bundle_summary(craft_packet_bundle(scan_type, service_inquiry)))
        except RuntimeError as exc:
            notes.append(f"Packet crafting for {scan_type} is unavailable: {exc}")
        except ValueError as exc:
            notes.append(f"Packet crafting for {scan_type} was skipped: {exc}")

    if not bundles:
        notes.append("No packet-crafting bundle could be generated for the requested directives.")

    return SurfacePacketCraftingPlan(
        investigation_target=investigation_target,
        authorized_host=authorized_host,
        requested_scan_types=requested_scan_types,
        selected_ports=selected_ports,
        bundles=tuple(bundles),
        recommended_profiles=_recommended_profiles(requested_scan_types),
        notes=tuple(notes),
    )
