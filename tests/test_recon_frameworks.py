import tempfile
import textwrap
import unittest
from pathlib import Path

from core.intel.recon_sources import (
    build_surface_recipe_plan,
    filter_recipe_modules,
    filter_recipes,
    load_graph_registry_reference,
    load_recursive_module_reference,
    load_source_inventory,
)


class TestReconFrameworks(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temp_dir.name)
        self._build_recursive_modules_fixture()
        self._build_graph_registry_fixture()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _build_recursive_modules_fixture(self) -> None:
        framework_root = self.temp_root / "recursive-source"
        docs_modules = framework_root / "docs" / "modules"
        presets = framework_root / "presets"
        docs_modules.mkdir(parents=True, exist_ok=True)
        presets.mkdir(parents=True, exist_ok=True)

        (docs_modules / "list_of_modules.md").write_text(
            textwrap.dedent(
                """
                | Module | Type | API | Description | Flags | Consumes | Produces | Author |
                | --- | --- | --- | --- | --- | --- | --- | --- |
                | httpx | active | no | HTTP surface checks | passive, httpx, web | domain | headers, urls | voltsparx |
                | crt | passive | no | Certificate transparency subdomain collector | passive, ct, dns | domain | subdomains | voltsparx |
                | rdap | passive | no | RDAP ownership enrichment | passive, rdap, whois | domain | ownership | voltsparx |
                """
            ).strip(),
            encoding="utf-8",
        )

        (presets / "subdomain-enum.yml").write_text(
            textwrap.dedent(
                """
                description: Passive subdomain discovery
                flags:
                  - passive
                  - ct
                  - rdap
                modules:
                  - crt
                  - rdap
                """
            ).strip(),
            encoding="utf-8",
        )

        (presets / "web-basic.yml").write_text(
            textwrap.dedent(
                """
                description: Light web surface inspection
                flags:
                  - httpx
                  - web
                modules:
                  - httpx
                """
            ).strip(),
            encoding="utf-8",
        )

        (framework_root / "cli.py").write_text(
            textwrap.dedent(
                """
                import argparse

                parser = argparse.ArgumentParser()
                parser.add_argument("--dry-run", dest="options.dry_run")
                parser.add_argument("--list-modules", dest="options.list_modules")
                parser.add_argument("--version", dest="options.version")
                """
            ).strip(),
            encoding="utf-8",
        )

    def _build_graph_registry_fixture(self) -> None:
        framework_root = self.temp_root / "graph-source"
        (framework_root / "cmd" / "oam_enum").mkdir(parents=True, exist_ok=True)
        (framework_root / "cmd" / "oam_track").mkdir(parents=True, exist_ok=True)
        (framework_root / "engine" / "plugins" / "surface").mkdir(parents=True, exist_ok=True)
        (framework_root / "internal").mkdir(parents=True, exist_ok=True)

    def test_load_source_inventory_discovers_local_profiles(self):
        payload = load_source_inventory(self.temp_root)
        names = {str(row.get("name")) for row in payload.get("profiles", []) if isinstance(row, dict)}
        self.assertIn("recursive-modules", names)
        self.assertIn("graph-registry", names)

    def test_load_recursive_module_reference_parses_modules_and_recipes(self):
        payload = load_recursive_module_reference(self.temp_root / "recursive-source")
        self.assertGreater(payload.get("module_count", 0), 0)
        self.assertGreater(payload.get("recipe_count", 0), 0)
        recipe_names = {str(row.get("name")) for row in payload.get("recipes", []) if isinstance(row, dict)}
        self.assertIn("subdomain-enum", recipe_names)

    def test_filter_recipe_modules_finds_httpx(self):
        rows = filter_recipe_modules(search="httpx", limit=10, reference_root=self.temp_root / "recursive-source")
        names = {str(row.get("name")) for row in rows if isinstance(row, dict)}
        self.assertIn("httpx", names)

    def test_filter_recipes_finds_web(self):
        rows = filter_recipes(search="web", limit=10, reference_root=self.temp_root / "recursive-source")
        names = {str(row.get("name")) for row in rows if isinstance(row, dict)}
        self.assertIn("web-basic", names)

    def test_build_surface_recipe_plan_translates_to_silica_x_surface(self):
        payload = build_surface_recipe_plan(
            domain="example.com",
            recipe_name="subdomain-enum",
            reference_root=self.temp_root / "recursive-source",
        )
        mapping = payload.get("silica_x_mapping", {})
        self.assertEqual(mapping.get("recon_mode"), "passive")
        self.assertEqual(mapping.get("surface_preset"), "deep")
        self.assertTrue(mapping.get("include_ct"))
        self.assertIn("silica-x.py surface example.com", str(payload.get("execution_preview", "")))

    def test_load_graph_registry_reference_discovers_commands(self):
        payload = load_graph_registry_reference(self.temp_root / "graph-source")
        commands = payload.get("commands", [])
        self.assertIn("oam_enum", commands)
        self.assertIn("oam_track", commands)


if __name__ == "__main__":
    unittest.main()
