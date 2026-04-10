import unittest
from unittest.mock import patch

from core.packet_crafting import (
    PacketCraftingCombinationEngine,
    PacketCraftingRequest,
    craft_packet_bundle,
    create_packet_crafting_engine,
    list_packet_crafting_engines,
    list_packet_crafting_profiles,
)


class _NoPayload:
    payload = None


class _Layer:
    def __init__(self, **fields):
        self.fields = fields
        self.payload = _NoPayload()

    def __truediv__(self, other):
        if isinstance(self.payload, _NoPayload):
            self.payload = other
        else:
            self.payload / other
        return self


class Ether(_Layer):
    pass


class ARP(_Layer):
    pass


class IP(_Layer):
    pass


class TCP(_Layer):
    pass


class UDP(_Layer):
    pass


class ICMP(_Layer):
    pass


class Raw(_Layer):
    pass


class _FakeScapyCatalog:
    Ether = Ether
    ARP = ARP
    IP = IP
    TCP = TCP
    UDP = UDP
    ICMP = ICMP
    Raw = Raw


def _summarize_layers(packet):
    names = []
    current_layer = packet
    while current_layer is not None and not isinstance(current_layer, _NoPayload):
        names.append(type(current_layer).__name__)
        current_layer = getattr(current_layer, "payload", None)
    return tuple(names)


class TestPacketCrafting(unittest.TestCase):
    def setUp(self):
        self.service_inquiry = PacketCraftingRequest(
            investigation_target="example.net",
            authorized_host="192.0.2.10",
            service_inquiry_ports=(53, 80),
            authorized_network_range="192.0.2.0/24",
            timeout_seconds=3.0,
            delay_seconds=0.25,
            source_port=41000,
        )
        self.catalog_patch = patch(
            "core.packet_crafting.base.load_scapy_layer_catalog",
            return_value=_FakeScapyCatalog(),
        )
        self.summary_patch = patch(
            "core.packet_crafting.base.summarize_packet_layers",
            side_effect=_summarize_layers,
        )
        self.catalog_patch.start()
        self.summary_patch.start()

    def tearDown(self):
        self.summary_patch.stop()
        self.catalog_patch.stop()

    def test_packet_crafting_inventory_lists_all_supported_engines(self):
        scan_types = {descriptor.scan_type for descriptor in list_packet_crafting_engines()}
        self.assertEqual(
            scan_types,
            {"arp", "syn", "tcp-connect", "udp", "fin", "null", "xmas", "os-fingerprint"},
        )

    def test_syn_packet_crafter_builds_one_packet_per_port(self):
        syn_bundle = craft_packet_bundle("syn", self.service_inquiry)
        self.assertEqual(syn_bundle.scan_types, ("syn",))
        self.assertEqual(len(syn_bundle.artifacts), 2)
        self.assertEqual(syn_bundle.artifacts[0].layer_stack, ("IP", "TCP"))
        self.assertEqual(syn_bundle.artifacts[0].service_inquiry_port, 53)
        self.assertEqual(syn_bundle.artifacts[1].service_inquiry_port, 80)

    def test_arp_packet_crafter_requires_authorized_network_range(self):
        with self.assertRaises(ValueError):
            craft_packet_bundle(
                "arp",
                PacketCraftingRequest(
                    investigation_target="example.net",
                    authorized_host="192.0.2.10",
                    service_inquiry_ports=(),
                ),
            )

    def test_tcp_connect_bundle_marks_response_dependent_stages(self):
        tcp_bundle = craft_packet_bundle("tcp-connect", self.service_inquiry)
        self.assertEqual(len(tcp_bundle.artifacts), 6)
        response_dependent = [artifact for artifact in tcp_bundle.artifacts if artifact.response_dependent]
        self.assertEqual(len(response_dependent), 4)

    def test_os_fingerprint_engine_builds_read_only_probe_set(self):
        engine = create_packet_crafting_engine("os-fingerprint")
        os_bundle = engine.craft_packets(self.service_inquiry)
        self.assertEqual(os_bundle.scan_types, ("os-fingerprint",))
        self.assertEqual([artifact.packet_label for artifact in os_bundle.artifacts[:2]], [
            "os_fingerprint_icmp_echo",
            "os_fingerprint_syn_53",
        ])
        self.assertEqual(os_bundle.artifacts[0].layer_stack, ("IP", "ICMP"))
        self.assertIn("spoofing", " ".join(os_bundle.notes))

    def test_combination_engine_builds_curated_profiles(self):
        profile_bundle = PacketCraftingCombinationEngine().craft_profile(
            "service-validation",
            self.service_inquiry,
        )
        self.assertEqual(profile_bundle.scan_types, ("syn", "tcp-connect", "udp"))
        self.assertEqual(len(profile_bundle.artifacts), 10)

    def test_profile_inventory_exposes_curated_combinations(self):
        profile_ids = {profile.profile_id for profile in list_packet_crafting_profiles()}
        self.assertIn("service-validation", profile_ids)
        self.assertIn("os-fingerprint-research", profile_ids)


if __name__ == "__main__":
    unittest.main()
