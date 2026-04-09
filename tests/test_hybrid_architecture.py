import io
import unittest
from contextlib import redirect_stdout

from core.intel.capability_matrix import build_runtime_inventory_snapshot
from core.intel.hybrid_architecture import build_hybrid_architecture_snapshot, render_hybrid_inventory_lines
from core.interface.banner import show_banner
from core.interface.loading import spinner_frames


class TestHybridArchitecture(unittest.TestCase):
    def test_banner_restores_full_console_identity(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            show_banner("Tor only")
        text = stream.getvalue()
        self.assertIn(".d8888.", text)
        self.assertIn("Hybrid console lanes:", text)
        self.assertIn("Tor only", text)

    def test_hybrid_architecture_snapshot_is_native_to_silica(self):
        snapshot = build_hybrid_architecture_snapshot()
        self.assertEqual(snapshot["identity"], "silica-x-hybrid")
        self.assertEqual(len(snapshot["lanes"]), 4)
        self.assertEqual(len(snapshot["engines"]), 5)
        inspiration_ids = {row["id"] for row in snapshot["inspiration"]}
        self.assertEqual(inspiration_ids, {"metasploit-ui", "amass-registry", "bbot-event-flow"})

        lines = render_hybrid_inventory_lines(snapshot)
        self.assertTrue(any("console-dispatch" in line for line in lines))
        self.assertTrue(any("metasploit-ui" in line for line in lines))

    def test_runtime_inventory_snapshot_embeds_hybrid_architecture(self):
        hybrid = build_hybrid_architecture_snapshot()
        snapshot = build_runtime_inventory_snapshot(
            plugin_count=3,
            filter_count=2,
            platform_count=4,
            module_count=11,
            plugin_scope_counts={"profile": 2, "surface": 2, "fusion": 3},
            filter_scope_counts={"profile": 1, "surface": 1, "fusion": 2},
            hybrid_architecture=hybrid,
        )
        self.assertEqual(snapshot["hybrid_architecture"]["identity"], "silica-x-hybrid")
        self.assertEqual(snapshot["inventory"]["modules"], 11)

    def test_spinner_frames_match_metasploit_style_cycle(self):
        self.assertEqual(spinner_frames(), ("/", "-", "\\", "|"))


if __name__ == "__main__":
    unittest.main()
