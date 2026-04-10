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

"""Curated read-only scan-combination profiles for packet crafting."""

from __future__ import annotations

from core.packet_crafting.models import PacketCraftingBundle, PacketCraftingProfile, PacketCraftingRequest
from core.packet_crafting.registry import craft_packet_bundle


_PACKET_CRAFTING_PROFILES: dict[str, PacketCraftingProfile] = {
    "local-subnet-discovery": PacketCraftingProfile(
        profile_id="local-subnet-discovery",
        title="Local Subnet Discovery",
        purpose="Craft read-only host-discovery and TCP exposure packets for an authorized local segment.",
        scan_types=("arp", "syn"),
        notes=(
            "Pairs local ARP discovery with SYN templates for follow-up service exposure review.",
            "Intended for authorized local-network research only.",
        ),
    ),
    "service-validation": PacketCraftingProfile(
        profile_id="service-validation",
        title="Service Validation",
        purpose="Craft read-only TCP and UDP validation templates for exposed services on an authorized host.",
        scan_types=("syn", "tcp-connect", "udp"),
        notes=(
            "Combines fast SYN discovery with definitive TCP connect templates and UDP review.",
            "Keeps the workflow read-only and excludes banner fuzzing or brute force behavior.",
        ),
    ),
    "firewall-behavior-study": PacketCraftingProfile(
        profile_id="firewall-behavior-study",
        title="Firewall Behavior Study",
        purpose="Craft comparative FIN, NULL, and XMAS templates for read-only firewall behavior analysis.",
        scan_types=("fin", "null", "xmas"),
        notes=(
            "Useful for comparing how an authorized host handles atypical TCP flag patterns.",
            "Excludes spoofing, fragmentation, decoys, and any evasion behavior.",
        ),
    ),
    "os-fingerprint-research": PacketCraftingProfile(
        profile_id="os-fingerprint-research",
        title="OS Fingerprint Research",
        purpose="Craft comparative TCP templates whose TTL and window responses can support read-only OS inference.",
        scan_types=("os-fingerprint", "syn", "fin", "null", "xmas"),
        notes=(
            "Supports passive TTL and window-size interpretation after responses are observed.",
            "Actual response analysis stays separate from packet crafting and remains scope-gated.",
        ),
    ),
}


class PacketCraftingCombinationEngine:
    """Compose multiple read-only packet-crafting engines into one investigation purpose."""

    def list_profiles(self) -> tuple[PacketCraftingProfile, ...]:
        """List every curated read-only packet-crafting profile in the framework inventory."""

        return tuple(_PACKET_CRAFTING_PROFILES.values())

    def craft_profile(self, profile_id: str, service_inquiry: PacketCraftingRequest) -> PacketCraftingBundle:
        """Craft one read-only combination profile for an authorized host or network."""

        normalized_profile_id = str(profile_id or "").strip().lower()
        try:
            profile = _PACKET_CRAFTING_PROFILES[normalized_profile_id]
        except KeyError as exc:
            raise ValueError(f"Unsupported packet crafting profile: {profile_id}") from exc

        nested_bundles = [craft_packet_bundle(scan_type, service_inquiry) for scan_type in profile.scan_types]
        artifacts = tuple(
            artifact
            for nested_bundle in nested_bundles
            for artifact in nested_bundle.artifacts
        )
        nested_notes = tuple(
            note
            for nested_bundle in nested_bundles
            for note in nested_bundle.notes
        )
        return PacketCraftingBundle(
            bundle_id=profile.profile_id,
            title=profile.title,
            purpose=profile.purpose,
            scan_types=profile.scan_types,
            artifacts=artifacts,
            notes=profile.notes + nested_notes,
        )


def list_packet_crafting_profiles() -> tuple[PacketCraftingProfile, ...]:
    """List curated read-only packet-crafting profiles exposed by the framework."""

    return PacketCraftingCombinationEngine().list_profiles()
