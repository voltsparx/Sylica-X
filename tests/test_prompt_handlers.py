import argparse
import unittest

from core.prompt_handlers import (
    apply_prompt_defaults,
    handle_prompt_set_command,
    handle_prompt_use_command,
    keyword_to_command,
    rewrite_tokens_with_keywords,
)
from core.session_state import PromptSessionState


class TestPromptHandlers(unittest.TestCase):
    def test_module_prompt_format(self):
        session = PromptSessionState(
            module="fusion",
            plugin_names=["alpha", "beta", "gamma"],
            filter_names=["delta"],
        )
        prompt = session.module_prompt()
        self.assertTrue(prompt.startswith("(console fusion"))
        self.assertIn("plugins=alpha,beta,+1", prompt)
        self.assertIn("filters=delta", prompt)
        self.assertTrue(prompt.endswith(")>>"))

    def test_keyword_mapping(self):
        self.assertEqual(keyword_to_command("social"), "profile")
        self.assertEqual(keyword_to_command("domain"), "surface")
        self.assertEqual(keyword_to_command("full"), "fusion")
        self.assertEqual(keyword_to_command("about"), "about")
        self.assertEqual(keyword_to_command("info"), "about")
        self.assertEqual(keyword_to_command("explain"), "explain")
        self.assertEqual(keyword_to_command("banner"), "banner")
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
        )
        args = argparse.Namespace(
            command="profile",
            plugin=[],
            filter=[],
            all_plugins=False,
            all_filters=False,
            preset="balanced",
        )
        updated = apply_prompt_defaults(args, session)
        self.assertEqual(updated.plugin, ["orbit_link_matrix"])
        self.assertEqual(updated.filter, ["contact_canonicalizer"])
        self.assertEqual(updated.preset, "deep")

    def test_handle_prompt_set_command_plugins_and_filters(self):
        session = PromptSessionState()
        events: list[tuple[str, str]] = []

        handle_prompt_set_command(
            "set plugins all",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertTrue(session.all_plugins)
        self.assertEqual(session.plugin_names, [])

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

    def test_handle_prompt_set_command_rejects_incompatible_selection(self):
        session = PromptSessionState(module="surface")
        events: list[tuple[str, str]] = []
        handle_prompt_set_command(
            "set plugins orbit_link_matrix",
            session,
            on_message=lambda message, color: events.append((message, color)),
        )
        self.assertEqual(session.plugin_names, [])
        self.assertTrue(any("No compatible plugins selected" in message for message, _ in events))

    def test_apply_prompt_defaults_filters_incompatible_selection_by_scope(self):
        session = PromptSessionState(
            module="profile",
            plugin_names=["orbit_link_matrix", "threat_conductor"],
            filter_names=["contact_canonicalizer", "exposure_tier_matrix"],
            all_plugins=False,
            all_filters=False,
            profile_preset="deep",
            surface_preset="quick",
        )
        args = argparse.Namespace(
            command="surface",
            plugin=[],
            filter=[],
            all_plugins=False,
            all_filters=False,
            preset="balanced",
        )
        updated = apply_prompt_defaults(args, session)
        self.assertEqual(updated.plugin, ["threat_conductor"])
        self.assertEqual(updated.filter, ["exposure_tier_matrix"])
        self.assertEqual(updated.preset, "quick")

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
