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

"""Registry helpers for Sylica-X packet-crafting engines."""

from __future__ import annotations

from core.packet_crafting.arp_engine import ArpPacketCraftingEngine
from core.packet_crafting.fin_engine import FinPacketCraftingEngine
from core.packet_crafting.models import (
    PacketCraftingBundle,
    PacketCraftingEngineDescriptor,
    PacketCraftingRequest,
)
from core.packet_crafting.null_engine import NullPacketCraftingEngine
from core.packet_crafting.os_fingerprint_engine import OsFingerprintPacketCraftingEngine
from core.packet_crafting.syn_engine import SynPacketCraftingEngine
from core.packet_crafting.tcp_connect_engine import TcpConnectPacketCraftingEngine
from core.packet_crafting.udp_engine import UdpPacketCraftingEngine
from core.packet_crafting.xmas_engine import XmasPacketCraftingEngine


_ENGINE_TYPES: dict[str, type] = {
    "arp": ArpPacketCraftingEngine,
    "syn": SynPacketCraftingEngine,
    "tcp-connect": TcpConnectPacketCraftingEngine,
    "udp": UdpPacketCraftingEngine,
    "fin": FinPacketCraftingEngine,
    "null": NullPacketCraftingEngine,
    "xmas": XmasPacketCraftingEngine,
    "os-fingerprint": OsFingerprintPacketCraftingEngine,
}


def create_packet_crafting_engine(scan_type: str):
    """Create one read-only packet-crafting engine for the requested scan type."""

    normalized_scan_type = str(scan_type or "").strip().lower()
    try:
        engine_type = _ENGINE_TYPES[normalized_scan_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported packet crafting scan type: {scan_type}") from exc
    return engine_type()


def craft_packet_bundle(scan_type: str, service_inquiry: PacketCraftingRequest) -> PacketCraftingBundle:
    """Craft a read-only packet bundle for one authorized scan type."""

    return create_packet_crafting_engine(scan_type).craft_packets(service_inquiry)


def list_packet_crafting_engines() -> tuple[PacketCraftingEngineDescriptor, ...]:
    """List every packet-crafting engine in the framework inventory."""

    return tuple(create_packet_crafting_engine(scan_type).descriptor() for scan_type in _ENGINE_TYPES)
