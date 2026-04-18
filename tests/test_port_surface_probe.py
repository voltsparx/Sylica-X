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
# ──────────────────────────────────────────────────────────────

import unittest
from unittest.mock import patch

from core.collect.port_surface_probe import (
    SURFACE_SCAN_PRESETS,
    SURFACE_SCAN_PROFILES,
    list_surface_scan_profiles,
    parse_surface_scan_xml,
    run_surface_scan,
)


class TestPortSurfaceProbe(unittest.TestCase):
    def test_scan_profiles_not_empty(self):
        self.assertGreater(len(SURFACE_SCAN_PROFILES), 60)

    def test_scan_presets_not_empty(self):
        self.assertGreaterEqual(len(SURFACE_SCAN_PRESETS), 14)

    def test_every_preset_profile_exists(self):
        for preset_profiles in SURFACE_SCAN_PRESETS.values():
            for profile_name in preset_profiles:
                self.assertIn(profile_name, SURFACE_SCAN_PROFILES)

    def test_parse_empty_xml(self):
        self.assertIsInstance(parse_surface_scan_xml(""), dict)

    def test_parse_minimal_xml(self):
        xml_text = """<?xml version="1.0"?>
<nmaprun>
  <scaninfo type="syn" protocol="tcp" numservices="1" services="80" />
  <host>
    <status state="up" />
    <address addr="127.0.0.1" addrtype="ipv4" />
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open" reason="syn-ack" />
        <service name="http" />
      </port>
    </ports>
  </host>
  <runstats>
    <finished elapsed="1.23" exit="success" summary="done" />
  </runstats>
</nmaprun>
"""
        result = parse_surface_scan_xml(xml_text)
        self.assertEqual(result["hosts"][0]["address"], "127.0.0.1")
        self.assertEqual(result["hosts"][0]["ports"][0]["port"], 80)

    def test_list_profiles_sorted(self):
        self.assertEqual(list_surface_scan_profiles(), sorted(list_surface_scan_profiles()))

    def test_no_binary_returns_error(self):
        with patch("core.collect.port_surface_probe.shutil.which", return_value=None):
            self.assertIn("error", run_surface_scan("127.0.0.1", ["stealth_sweep"]))


if __name__ == "__main__":
    unittest.main()

