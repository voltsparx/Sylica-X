import asyncio
import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.cli_ui import CLIUI
from core.credential_manager import CredentialManager
from core.fusion_engine import FusionEngine
from core.intelligence_advisor import IntelligenceAdvisor
from core.parallel_engine import ParallelEngine
from core.plugin_manager import PluginManager
from core.prompt_intelligence import PromptEngine
from core.reporting import ReportGenerator
from core.reverse_engineering import (
    load_reverse_engineering_map,
    map_tools_to_silica_modules,
    recommend_research_focus,
)
from core.scheduler import Scheduler
from core.security_manager import SecurityManager


async def _async_increment(value: int) -> int:
    await asyncio.sleep(0)
    return value + 1


def _blocking_concat(left: str, right: str) -> str:
    return f"{left}{right}"


def _cpu_square(value: int) -> int:
    return value * value


class TestBlueprintModules(unittest.TestCase):
    def test_reverse_engineering_map_parsing_and_mapping(self):
        content = """
1. Sherlock
* Username account discovery across platforms
* Code: https://github.com/sherlock-project/sherlock

2. Amass
* Domain and network intelligence mapper
* Code: https://github.com/OWASP/Amass
""".strip()
        with TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "map.txt"
            map_path.write_text(content, encoding="utf-8")

            mapping = load_reverse_engineering_map(map_path)
            module_map = map_tools_to_silica_modules(mapping)
            profile_research = recommend_research_focus("profile", mapping)
            surface_research = recommend_research_focus("surface", mapping)

        self.assertEqual(len(mapping.tools), 2)
        self.assertEqual(mapping.tools[0].name, "Sherlock")
        self.assertIn("core/scanner.py", module_map)
        self.assertIn("Sherlock", module_map["core/scanner.py"])
        self.assertIn("Amass", module_map["core/domain_intel.py"])
        self.assertTrue(profile_research[0].startswith("Study patterns from:"))
        self.assertTrue(surface_research[0].startswith("Study patterns from:"))

    def test_parallel_engine_hybrid_execution(self):
        engine = ParallelEngine(async_concurrency=2, thread_concurrency=2, cpu_workers=1)
        result = asyncio.run(
            engine.run_hybrid(
                async_tasks=[_async_increment(1), _async_increment(4)],
                thread_calls=[(_blocking_concat, ("a", "b"), {})],
                cpu_calls=[(_cpu_square, (5,), {})],
            )
        )

        self.assertEqual(result.async_results, (2, 5))
        self.assertEqual(result.thread_results, ("ab",))
        self.assertEqual(result.cpu_results, (25,))
        self.assertEqual(result.as_dict()["cpu_results"], [25])

    def test_fusion_engine_fusion_and_graph(self):
        profile_data = {
            "target": "alice",
            "results": [
                {"status": "FOUND", "confidence": 80},
                {"status": "FOUND", "confidence": 60},
                {"status": "BLOCKED", "confidence": 0},
            ],
            "correlation": {"identity_overlap_score": 10},
            "issue_summary": {"risk_score": 70},
        }
        domain_data = {
            "domain_result": {
                "target": "example.com",
                "subdomains": [f"sub{i}.example.com" for i in range(120)],
                "resolved_addresses": ["1.1.1.1", "2.2.2.2"],
                "https": {"status": 500},
            }
        }
        engine = FusionEngine()

        fused = asyncio.run(engine.fuse_profile_domain(profile_data, domain_data))
        cached = asyncio.run(engine.fuse_profile_domain(profile_data, domain_data))
        graph = asyncio.run(engine.generate_graph(fused))

        self.assertEqual(fused["target"]["username"], "alice")
        self.assertEqual(fused["target"]["domain"], "example.com")
        self.assertIn("weak_identity_overlap", fused["anomalies"])
        self.assertIn("broad_attack_surface", fused["anomalies"])
        self.assertIn("unstable_https_surface", fused["anomalies"])
        self.assertIn("high_exposure_risk", fused["anomalies"])
        self.assertIs(cached, fused)
        self.assertGreaterEqual(len(graph["nodes"]), 3)
        self.assertGreaterEqual(len(graph["edges"]), 2)

    def test_plugin_manager_runs_selected_plugins(self):
        manager = PluginManager()
        context = {
            "target": "alice",
            "mode": "profile",
            "results": [
                {
                    "status": "FOUND",
                    "platform": "GitHub",
                    "contacts": {"emails": ["alice@example.com"], "phones": ["+1 555-000-1111"]},
                },
                {
                    "status": "FOUND",
                    "platform": "Reddit",
                    "contacts": {"emails": ["alice@example.com"], "phones": ["5550001111"]},
                },
            ],
            "correlation": {"identity_overlap_score": 20},
        }
        results, errors = asyncio.run(
            manager.run_plugins(
                context,
                scope="profile",
                requested_plugins=["contact_lattice", "identity_fusion_core"],
                chain=True,
            )
        )
        _, unknown_errors = asyncio.run(
            manager.run_plugins(
                context,
                scope="profile",
                requested_plugins=["missing-plugin-name"],
            )
        )

        result_ids = {row["id"] for row in results}
        self.assertIn("contact_lattice", result_ids)
        self.assertIn("identity_fusion_core", result_ids)
        self.assertFalse([err for err in errors if "missing dependencies" in err.lower()])
        self.assertTrue(any("Unknown plugin requested" in err for err in unknown_errors))

    def test_prompt_engine_and_advisor_recommendations(self):
        prompt = PromptEngine(history=["profile alice", "surface example.com", "fusion alice example.com"])
        suggestions = prompt.suggest_next(limit=3)
        self.assertEqual(len(suggestions), 3)

        map_content = """
1. Sherlock
* Username account discovery across platforms

2. Recon-ng
* Modular web reconnaissance platform
""".strip()
        with TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "reverse-map.txt"
            map_path.write_text(map_content, encoding="utf-8")
            advisor = IntelligenceAdvisor(history=["profile alice"], reverse_map_path=str(map_path))
            recommendations = advisor.recommend_next()
            normalized_confidence = advisor.estimate_confidence({"confidence_score": 80})

        self.assertGreater(len(recommendations), 0)
        self.assertTrue(any("Study patterns from:" in row for row in recommendations))
        self.assertAlmostEqual(normalized_confidence, 0.8, places=2)

    def test_credential_manager_roundtrip(self):
        manager = CredentialManager(key=CredentialManager.generate_key())

        manager.store_token("github", "ghp_example")
        self.assertEqual(manager.retrieve_token("github"), "ghp_example")
        self.assertTrue(manager.validate_token("github"))

        manager.rotate_token("github", "ghp_new_value")
        self.assertEqual(manager.retrieve_token("github"), "ghp_new_value")
        self.assertEqual(manager.list_services(), ["github"])
        self.assertTrue(manager.remove_token("github"))
        self.assertIsNone(manager.retrieve_token("github"))

    def test_report_generator_exports_and_cli_view(self):
        generator = ReportGenerator()
        fused_data = {
            "target": {"username": "alice", "domain": "example.com"},
            "confidence_score": 77,
            "risk": {"risk_score": 33},
            "anomalies": ["weak_identity_overlap"],
        }

        with patch("core.reporting.generate_html", return_value="dashboard.html") as mocked_generate:
            dashboard_path = generator.generate_html_dashboard(fused_data)
        self.assertEqual(dashboard_path, "dashboard.html")
        mocked_generate.assert_called_once()

        with TemporaryDirectory() as temp_dir:
            scoped_generator = ReportGenerator(output_dir=temp_dir)
            export_path = scoped_generator.export_pdf_excel(fused_data, format="excel")
            payload = json.loads(Path(export_path).read_text(encoding="utf-8"))

        self.assertTrue(export_path.endswith(".xlsx"))
        self.assertEqual(payload["format_hint"], "xlsx")
        summary = generator.cli_viewer(fused_data)
        self.assertIn("Confidence=77", summary)
        self.assertIn("Anomalies=weak_identity_overlap", summary)

    def test_scheduler_security_and_cli_ui(self):
        scheduler = Scheduler()

        def _scan(target: str) -> dict[str, str]:
            return {"target": target, "status": "ok"}

        scheduler.schedule_scan(_scan, "alice", 1)
        pending = asyncio.run(scheduler.run_pending(now=time.time() + 2))
        merged = scheduler.merge_results({"a": 1, "nested": {"k": 1}}, {"b": 2, "nested": {"z": 9}})
        alert = scheduler.send_alert("alice", {"risk_score": 40})

        self.assertEqual(len(pending), 1)
        self.assertTrue(pending[0]["ok"])
        self.assertEqual(merged["nested"]["k"], 1)
        self.assertEqual(merged["nested"]["z"], 9)
        self.assertIn("target=alice", alert)

        security = SecurityManager()
        with TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "sample.txt"
            source.write_text("hello-world", encoding="utf-8")
            key = security.generate_key()
            encrypted_path = security.encrypt_output(str(source), key=key)
            decrypted = security.decrypt_output(encrypted_path, key=key)
        self.assertEqual(decrypted.decode("utf-8"), "hello-world")
        sandbox_profile = security.sandbox_plugin("contact_lattice")
        self.assertFalse(sandbox_profile["allow_network"])

        ui = CLIUI()
        profile = ui.load_profile("quick")
        self.assertIn("timeout", profile)
        with self.assertRaises(ValueError):
            ui.load_profile("unknown-profile")


if __name__ == "__main__":
    unittest.main()
