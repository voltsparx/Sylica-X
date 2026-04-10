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

"""OS fingerprint packet crafting engine for read-only response analysis."""

from __future__ import annotations

from core.packet_crafting.base import PacketCraftingEngine
from core.packet_crafting.models import PacketCraftingBundle, PacketCraftingRequest


class OsFingerprintPacketCraftingEngine(PacketCraftingEngine):
    """Craft read-only packet probes that support TTL and TCP-window OS inference."""

    engine_id = "packet_crafter_os_fingerprint"
    scan_type = "os-fingerprint"
    title = "OS Fingerprint Packet Crafter"
    reads = (
        "TTL, TCP window size, reset behavior, and ICMP echo responses from an authorized host "
        "to support read-only operating-system inference."
    )
    packet_purpose = "Read-only OS fingerprint packet crafting for authorized host research."

    def craft_packets(self, service_inquiry: PacketCraftingRequest) -> PacketCraftingBundle:
        """Craft ICMP and TCP packet templates without transmitting or modifying any host."""

        scapy_catalog = self._scapy()
        primary_port = (
            min(self._validated_ports(service_inquiry))
            if service_inquiry.service_inquiry_ports
            else 80
        )
        sequence_number = self._sequence_number(service_inquiry, primary_port, offset=100)

        icmp_packet = scapy_catalog.IP(dst=service_inquiry.authorized_host) / scapy_catalog.ICMP()
        syn_packet = scapy_catalog.IP(dst=service_inquiry.authorized_host) / scapy_catalog.TCP(
            sport=int(service_inquiry.source_port),
            dport=primary_port,
            flags="S",
            seq=sequence_number,
        )
        ack_packet = scapy_catalog.IP(dst=service_inquiry.authorized_host) / scapy_catalog.TCP(
            sport=int(service_inquiry.source_port),
            dport=primary_port,
            flags="A",
            seq=sequence_number + 1,
            ack=int(service_inquiry.tcp_acknowledgement_seed),
        )
        null_packet = scapy_catalog.IP(dst=service_inquiry.authorized_host) / scapy_catalog.TCP(
            sport=int(service_inquiry.source_port),
            dport=primary_port,
            flags="",
            seq=sequence_number + 2,
        )

        artifacts = (
            self._artifact(
                service_inquiry=service_inquiry,
                packet_label="os_fingerprint_icmp_echo",
                packet_summary=f"ICMP echo request template for {service_inquiry.authorized_host}",
                response_guidance="Observed reply TTL and ICMP behavior can support read-only host-stack inference.",
                scapy_packet=icmp_packet,
            ),
            self._artifact(
                service_inquiry=service_inquiry,
                packet_label=f"os_fingerprint_syn_{primary_port}",
                packet_summary=(
                    f"TCP SYN fingerprint template for {service_inquiry.authorized_host}:{primary_port}"
                ),
                response_guidance=(
                    "SYN-ACK TTL and TCP window characteristics can contribute to read-only OS inference."
                ),
                scapy_packet=syn_packet,
                service_inquiry_port=primary_port,
            ),
            self._artifact(
                service_inquiry=service_inquiry,
                packet_label=f"os_fingerprint_ack_{primary_port}",
                packet_summary=(
                    f"TCP ACK fingerprint template for {service_inquiry.authorized_host}:{primary_port}"
                ),
                response_guidance=(
                    "RST behavior and acknowledgement handling can help distinguish TCP stack families."
                ),
                scapy_packet=ack_packet,
                service_inquiry_port=primary_port,
            ),
            self._artifact(
                service_inquiry=service_inquiry,
                packet_label=f"os_fingerprint_null_{primary_port}",
                packet_summary=(
                    f"TCP NULL fingerprint template for {service_inquiry.authorized_host}:{primary_port}"
                ),
                response_guidance=(
                    "Silence-versus-reset behavior can support read-only OS-family comparison."
                ),
                scapy_packet=null_packet,
                service_inquiry_port=primary_port,
            ),
        )
        return PacketCraftingBundle(
            bundle_id=self.engine_id,
            title=self.title,
            purpose=self.packet_purpose,
            scan_types=(self.scan_type,),
            artifacts=artifacts,
            notes=(
                "This engine only crafts comparative fingerprint probes for later response interpretation.",
                "It intentionally excludes spoofing, fragmentation, decoys, and any exploit behavior.",
            ),
        )
