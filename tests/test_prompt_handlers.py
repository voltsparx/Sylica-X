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
#
# This file is part of Silica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

import argparse
import unittest

from core.prompt_handlers import (
    apply_prompt_defaults,
    handle_prompt_control_command,
    handle_prompt_set_command,
    handle_prompt_use_command,
    keyword_to_command,
    rewrite_tokens_with_keywords,
)
from core.foundation.session_state import PromptSessionState


class TestPromptHandlers(unittest.TestCase):
    def test_module_prompt_format(self):
        session = PromptSessionState(
            module="fusion",
            plugin_names=["alpha", "beta", "gamma"],
            filter_names=["delta"],
        )
        prompt = session.module_prompt()
        self.assertEqual(prompt, "sx(fusion*)>")

    def test_context_summary_format(self):
        session = PromptSessionState(
            module="surface",
            plugin_names=["alpha"],
            filter_names=["delta", "epsilon"],
            surface_preset="deep",
            surface_extension_control="hybrid",
        )
        summary = session.context_summary()
        self.assertIn("module=surface", summary)
        self.assertIn("preset=deep", summary)
        self.assertIn("ext=hybrid", summary)
        self.assertIn("plugins=1", summary)
        self.assertIn("filters=2", summary)

    def test_keyword_mapping(self):
        self.assertEqual(keyword_to_command("social"), "profile")
        self.assertEqual(keyword_to_command("domain"), "surface")
        self.assertEqual(keyword_to_command("full"), "fusion")
        self.assertEqual(keyword_to_command("pipeline"), "orchestrate")
        self.assertEqual(keyword_to_command("about"), "about")
        self.assertEqual(keyword_to_command("info"), "about")
        self.assertEqual(keyword_to_command("explain"), "explain")
        self.assertEqual(keyword_to_command("banner"), "banner")
        self.assertEqual(keyword_to_command("template"), "templates")
        self.assertEqual(keyword_to_command("modules"), "modules")
        self.assertIsNone(keyword_to_command("unknown"))

    def test_rewrite_tokens_with_keywords(self):
        self.assertEqual(rewrite_tokens_with_keywords(["social", "alice"]), ["profile", "alice"])
        self.assertEqual(rewrite_tokens_with_keywords(["surface", "example.com"]), ["surface", "example.com"])

    def test_apply_prompt_defaults_profile(self):
        session = PromptSessionState(
            module="profile",
            plugin_names=["orbit_link_matrix"],
            filter_names=["contact_canonicalizer"],
            all_plugins=False,
            all_filters=False,
            profile_preset="deep",
            surface_preset="quick",
            profile_extension_control="hybrid",
        )
        args = argparse.Namespace(
            command="profile",
            plugin=[],
            filter=[],
            all_plugins=False,
            all_filters=False,
            preset="balanced",
            extension_control="manual",
        )
        updated = apply_prompt_defaults(args, session)
        self.assertEqual(updated.plugin, ["orbit_link_matrix"])
        self.assertEqual(updated.filter, ["contact_canonicalizer"])
        self.assertEqual(updated.preset, "deep")
        self.assertEqual(updated.extension_control, "hybrid")

    def test_handle_prompt_set_command_plugins_and_filters(self):
        session = PromptSessionState()
        events: list[tuple[str, str]] = []

        handle_prompt_set_command(
            "set plugins all",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertEqual(session.plugin_names, [])
        self.assertTrue(any("Bulk plugin selection is disabled" in message for message, _ in events))

        handle_prompt_set_command(
            "set filters contact_canonicalizer,entity_name_resolver",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertFalse(session.all_filters)
        self.assertEqual(session.filter_names, ["contact_canonicalizer", "entity_name_resolver"])
        self.assertGreaterEqual(len(events), 2)

    def test_handle_prompt_set_command_resolves_aliases(self):
        session = PromptSessionState(module="profile")
        handle_prompt_set_command(
            "set plugins risk,contact_mesh",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.plugin_names, ["threat_conductor", "contact_lattice"])

        handle_prompt_set_command(
            "set filters pii,contacts",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.filter_names, ["pii_signal_classifier", "contact_canonicalizer"])

    def test_handle_prompt_set_command_resolves_titles(self):
        session = PromptSessionState(module="profile")
        handle_prompt_set_command(
            "set plugins Contact Lattice Analyzer,Threat Conductor",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.plugin_names, ["contact_lattice", "threat_conductor"])

        handle_prompt_set_command(
            "set filters Contact Canonicalizer,PII Signal Classifier",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.filter_names, ["contact_canonicalizer", "pii_signal_classifier"])

    def test_handle_prompt_set_command_rejects_incompatible_selection(self):
        session = PromptSessionState(module="surface")
        events: list[tuple[str, str]] = []
        handle_prompt_set_command(
            "set plugins orbit_link_matrix",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertEqual(session.plugin_names, [])
        self.assertTrue(any("Plugin selection blocked for module" in message for message, _ in events))

    def test_handle_prompt_set_command_supports_max_profile_preset(self):
        session = PromptSessionState(module="profile")
        handle_prompt_set_command(
            "set profile_preset max",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.profile_preset, "max")

    def test_handle_prompt_set_command_applies_template(self):
        session = PromptSessionState(module="profile")
        handle_prompt_set_command(
            "set template contact-discovery",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(
            session.plugin_names,
            [
                "contact_lattice",
                "orbit_link_matrix",
                "link_outbound_risk_profiler",
                "account_recovery_exposure_probe",
            ],
        )
        self.assertEqual(
            session.filter_names,
            [
                "contact_canonicalizer",
                "contact_quality_filter",
                "mailbox_provider_profiler",
                "link_hygiene_filter",
            ],
        )

    def test_apply_prompt_defaults_filters_incompatible_selection_by_scope(self):
        session = PromptSessionState(
            module="profile",
            plugin_names=["orbit_link_matrix", "threat_conductor"],
            filter_names=["contact_canonicalizer", "exposure_tier_matrix"],
            all_plugins=False,
            all_filters=False,
            profile_preset="deep",
            surface_preset="quick",
            surface_extension_control="hybrid",
        )
        args = argparse.Namespace(
            command="surface",
            plugin=[],
            filter=[],
            all_plugins=False,
            all_filters=False,
            preset="balanced",
            extension_control="manual",
        )
        updated = apply_prompt_defaults(args, session)
        self.assertEqual(updated.plugin, ["threat_conductor"])
        self.assertEqual(updated.filter, ["exposure_tier_matrix"])
        self.assertEqual(updated.preset, "quick")
        self.assertEqual(updated.extension_control, "hybrid")

    def test_apply_prompt_defaults_respects_explicit_flags(self):
        session = PromptSessionState(
            module="profile",
            profile_preset="deep",
            profile_extension_control="hybrid",
        )
        args = argparse.Namespace(
            command="profile",
            plugin=[],
            filter=[],
            all_plugins=False,
            all_filters=False,
            preset="balanced",
            extension_control="manual",
            _explicit_flags=("--preset", "--extension-control"),
        )
        updated = apply_prompt_defaults(args, session)
        self.assertEqual(updated.preset, "balanced")
        self.assertEqual(updated.extension_control, "manual")

    def test_apply_prompt_defaults_orchestrate_uses_mode_scope(self):
        session = PromptSessionState(
            module="profile",
            plugin_names=["orbit_link_matrix", "threat_conductor"],
            filter_names=["contact_canonicalizer", "exposure_tier_matrix"],
            all_plugins=False,
            all_filters=False,
            profile_preset="deep",
            surface_preset="quick",
            orchestrate_extension_control="hybrid",
        )
        args = argparse.Namespace(
            command="orchestrate",
            mode="surface",
            target="example.com",
            plugin=[],
            filter=[],
            all_plugins=False,
            all_filters=False,
            profile="balanced",
            extension_control="auto",
        )
        updated = apply_prompt_defaults(args, session)
        self.assertEqual(updated.plugin, ["threat_conductor"])
        self.assertEqual(updated.filter, ["exposure_tier_matrix"])
        self.assertEqual(updated.profile, "quick")
        self.assertEqual(updated.extension_control, "hybrid")

    def test_handle_prompt_set_command_extension_controls(self):
        session = PromptSessionState(module="fusion")
        handle_prompt_set_command(
            "set extension_control HYBRID",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.fusion_extension_control, "hybrid")

        handle_prompt_set_command(
            "set orchestrate-extension-control manual",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.orchestrate_extension_control, "manual")

    def test_handle_prompt_set_command_blocks_plugins_and_filters_in_auto_mode(self):
        session = PromptSessionState(module="profile", profile_extension_control="auto")
        events: list[tuple[str, str]] = []
        handle_prompt_set_command(
            "set plugins threat_conductor",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        handle_prompt_set_command(
            "set filters contact_canonicalizer",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertEqual(session.plugin_names, [])
        self.assertEqual(session.filter_names, [])
        self.assertTrue(any("while extension_control=auto" in message for message, _ in events))

    def test_handle_prompt_set_command_blocks_switch_to_auto_when_manual_config_exists(self):
        session = PromptSessionState(
            module="profile",
            plugin_names=["threat_conductor"],
            filter_names=["contact_canonicalizer"],
            profile_extension_control="manual",
        )
        events: list[tuple[str, str]] = []
        handle_prompt_set_command(
            "set extension_control auto",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertEqual(session.profile_extension_control, "manual")
        self.assertTrue(any("Cannot set extension_control=auto" in message for message, _ in events))

    def test_handle_prompt_control_command_select_module_and_selectors(self):
        session = PromptSessionState(module="profile")
        events: list[tuple[str, str]] = []
        handled = handle_prompt_control_command(
            "select module surface",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertTrue(handled)
        self.assertEqual(session.module, "surface")

        handled = handle_prompt_control_command(
            "select plugins threat_conductor",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertTrue(handled)
        self.assertEqual(session.plugin_names, ["threat_conductor"])

    def test_handle_prompt_control_command_add_and_remove_plugins_filters(self):
        session = PromptSessionState(module="profile")
        handle_prompt_control_command(
            "add plugins threat_conductor,contact_lattice",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.plugin_names, ["threat_conductor", "contact_lattice"])

        handle_prompt_control_command(
            "remove plugins contact_lattice",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.plugin_names, ["threat_conductor"])

        handle_prompt_control_command(
            "add filters contact_canonicalizer,entity_name_resolver",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.filter_names, ["contact_canonicalizer", "entity_name_resolver"])

        handle_prompt_control_command(
            "remove filters entity_name_resolver",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertEqual(session.filter_names, ["contact_canonicalizer"])

    def test_handle_prompt_control_command_blocks_mutation_in_auto_mode(self):
        session = PromptSessionState(module="profile", profile_extension_control="auto")
        events: list[tuple[str, str]] = []
        handle_prompt_control_command(
            "add plugins threat_conductor",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertEqual(session.plugin_names, [])
        self.assertTrue(any("while extension_control=auto" in message for message, _ in events))

    def test_handle_prompt_use_command(self):
        session = PromptSessionState(
            module="profile",
            plugin_names=["orbit_link_matrix", "threat_conductor"],
            filter_names=["contact_canonicalizer", "exposure_tier_matrix"],
        )
        result = handle_prompt_use_command(
            "use fusion",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertTrue(result)
        self.assertEqual(session.module, "fusion")
        self.assertEqual(session.plugin_names, ["orbit_link_matrix", "threat_conductor"])
        self.assertEqual(session.filter_names, ["contact_canonicalizer", "exposure_tier_matrix"])

        result = handle_prompt_use_command(
            "use surface",
            session,
            on_message=lambda _message, _color: None,
        )
        self.assertTrue(result)
        self.assertEqual(session.module, "surface")
        self.assertEqual(session.plugin_names, ["threat_conductor"])
        self.assertEqual(session.filter_names, ["exposure_tier_matrix"])


if __name__ == "__main__":
    unittest.main()
