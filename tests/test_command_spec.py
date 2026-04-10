import unittest

from core.interface.command_spec import normalize_surface_scan_types, resolve_surface_scan_directives


class TestCommandSpec(unittest.TestCase):
    def test_normalize_surface_scan_types_deduplicates_aliases(self):
        directives = normalize_surface_scan_types(["syn", "SYN-SCAN", "tcp_connect", "banner"])
        self.assertEqual(directives, ("syn", "tcp-connect", "service"))

    def test_resolve_surface_scan_directives_upgrades_passive_when_active_requested(self):
        directives = resolve_surface_scan_directives(
            recon_mode="passive",
            requested_scan_types=["syn", "udp"],
            os_fingerprint_enabled=True,
            scan_verbosity="verbose",
            delay_seconds=0.5,
        )
        self.assertEqual(directives.recon_mode, "active")
        self.assertEqual(directives.scan_types, ("syn", "udp"))
        self.assertTrue(directives.os_fingerprint_enabled)
        self.assertEqual(directives.scan_verbosity, "verbose")
        self.assertAlmostEqual(directives.delay_seconds, 0.5)
        self.assertTrue(directives.active_inquiry_requested)
        self.assertTrue(any("upgraded recon mode" in note.lower() for note in directives.notes))


if __name__ == "__main__":
    unittest.main()
