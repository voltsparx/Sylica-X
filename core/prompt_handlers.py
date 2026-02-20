"""Prompt command parsing and session-state mutation helpers."""

from __future__ import annotations

import argparse
from typing import Callable

from core.cli_config import PROFILE_PRESETS, PROMPT_KEYWORDS, SURFACE_PRESETS
from core.colors import Colors, c
from core.session_state import PromptSessionState
from core.signal_forge import list_plugin_descriptors
from core.signal_sieve import list_filter_descriptors


VALID_MODULES = {"profile", "surface", "fusion"}
PROFILE_ALIASES = {"profile", "scan", "persona", "social"}
SURFACE_ALIASES = {"surface", "domain", "asset"}
FUSION_ALIASES = {"fusion", "full", "combo"}


def keyword_to_command(value: str) -> str | None:
    lowered = value.strip().lower()
    for command, keywords in PROMPT_KEYWORDS.items():
        if lowered in keywords:
            return command
    return None


def rewrite_tokens_with_keywords(tokens: list[str]) -> list[str]:
    if not tokens:
        return tokens
    mapped = keyword_to_command(tokens[0])
    if mapped:
        return [mapped, *tokens[1:]]
    return tokens


def _normalize_module(value: str) -> str:
    lowered = value.strip().lower()
    if lowered not in VALID_MODULES:
        return "profile"
    return lowered


def _module_for_command(command: str) -> str | None:
    lowered = command.strip().lower()
    if lowered in PROFILE_ALIASES:
        return "profile"
    if lowered in SURFACE_ALIASES:
        return "surface"
    if lowered in FUSION_ALIASES:
        return "fusion"
    return None


def _split_csv_values(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _descriptor_lookup(descriptors: list[dict[str, object]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for descriptor in descriptors:
        descriptor_id = str(descriptor.get("id", "")).strip().lower()
        if not descriptor_id:
            continue
        lookup[descriptor_id] = descriptor_id
        aliases = descriptor.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                alias_name = str(alias).strip().lower()
                if alias_name:
                    lookup[alias_name] = descriptor_id
    return lookup


def _resolve_compatible_names(
    requested_names: list[str],
    *,
    descriptors: list[dict[str, object]],
) -> tuple[list[str], list[str]]:
    by_key = _descriptor_lookup(descriptors)
    selected: list[str] = []
    seen: set[str] = set()
    rejected: list[str] = []
    for raw_name in requested_names:
        lowered = raw_name.strip().lower()
        if not lowered:
            continue
        matched = by_key.get(lowered)
        if matched is None:
            rejected.append(raw_name)
            continue
        if matched in seen:
            continue
        selected.append(matched)
        seen.add(matched)
    return selected, rejected


def _resolve_plugins_for_scope(names: list[str], scope: str) -> tuple[list[str], list[str]]:
    descriptors = list_plugin_descriptors(scope=scope)
    return _resolve_compatible_names(names, descriptors=descriptors)


def _resolve_filters_for_scope(names: list[str], scope: str) -> tuple[list[str], list[str]]:
    descriptors = list_filter_descriptors(scope=scope)
    return _resolve_compatible_names(names, descriptors=descriptors)


def apply_prompt_defaults(args: argparse.Namespace, session: PromptSessionState) -> argparse.Namespace:
    command = str(getattr(args, "command", ""))
    scope = _module_for_command(command)
    if scope is None:
        return args

    if not getattr(args, "plugin", None) and not getattr(args, "all_plugins", False):
        if session.all_plugins:
            args.all_plugins = True
            args.plugin = []
        else:
            args.plugin, _ = _resolve_plugins_for_scope(session.plugin_names, scope)
            args.all_plugins = False

    if not getattr(args, "filter", None) and not getattr(args, "all_filters", False):
        if session.all_filters:
            args.all_filters = True
            args.filter = []
        else:
            args.filter, _ = _resolve_filters_for_scope(session.filter_names, scope)
            args.all_filters = False

    if scope == "profile":
        if getattr(args, "preset", None) == "balanced":
            args.preset = session.profile_preset
        return args

    if scope == "surface":
        if getattr(args, "preset", None) == "balanced":
            args.preset = session.surface_preset
        return args

    if scope == "fusion":
        if getattr(args, "profile_preset", None) == "balanced":
            args.profile_preset = session.profile_preset
        if getattr(args, "surface_preset", None) == "balanced":
            args.surface_preset = session.surface_preset
    return args


def handle_prompt_set_command(
    command_text: str,
    session: PromptSessionState,
    *,
    on_message: Callable[[str, str], None] | None = None,
) -> bool:
    def _emit(message: str, color: str) -> None:
        if on_message is None:
            print(c(message, color))
            return
        on_message(message, color)

    tokens = command_text.strip().split(maxsplit=2)
    if len(tokens) != 3:
        _emit("Usage: set <plugins|filters|profile_preset|surface_preset> <value>", Colors.YELLOW)
        return True

    _, key, value = tokens
    key = key.strip().lower()
    value = value.strip()
    scope = _normalize_module(session.module)

    if key == "plugins":
        lower = value.lower()
        if lower == "all":
            session.all_plugins = True
            session.plugin_names = []
            _emit(f"Plugins set to: {session.plugins_label()} (module={scope})", Colors.GREEN)
            return True
        if lower in {"none", "off"}:
            session.all_plugins = False
            session.plugin_names = []
            _emit(f"Plugins set to: {session.plugins_label()} (module={scope})", Colors.GREEN)
            return True
        requested = _split_csv_values(value)
        if not requested:
            _emit("Provide at least one plugin id/alias.", Colors.YELLOW)
            return True
        selected, rejected = _resolve_plugins_for_scope(requested, scope)
        if rejected:
            _emit(
                f"Ignored incompatible/unknown plugins for module '{scope}': {', '.join(rejected)}",
                Colors.YELLOW,
            )
        if not selected:
            _emit(f"No compatible plugins selected for module '{scope}'.", Colors.RED)
            return True
        session.all_plugins = False
        session.plugin_names = selected
        _emit(f"Plugins set to: {session.plugins_label()} (module={scope})", Colors.GREEN)
        return True

    if key == "filters":
        lower = value.lower()
        if lower == "all":
            session.all_filters = True
            session.filter_names = []
            _emit(f"Filters set to: {session.filters_label()} (module={scope})", Colors.GREEN)
            return True
        if lower in {"none", "off"}:
            session.all_filters = False
            session.filter_names = []
            _emit(f"Filters set to: {session.filters_label()} (module={scope})", Colors.GREEN)
            return True
        requested = _split_csv_values(value)
        if not requested:
            _emit("Provide at least one filter id/alias.", Colors.YELLOW)
            return True
        selected, rejected = _resolve_filters_for_scope(requested, scope)
        if rejected:
            _emit(
                f"Ignored incompatible/unknown filters for module '{scope}': {', '.join(rejected)}",
                Colors.YELLOW,
            )
        if not selected:
            _emit(f"No compatible filters selected for module '{scope}'.", Colors.RED)
            return True
        session.all_filters = False
        session.filter_names = selected
        _emit(f"Filters set to: {session.filters_label()} (module={scope})", Colors.GREEN)
        return True

    if key == "profile_preset":
        if value not in PROFILE_PRESETS:
            _emit(f"Invalid profile preset: {value}", Colors.RED)
            return True
        session.profile_preset = value
        _emit(f"Profile preset set to: {value}", Colors.GREEN)
        return True

    if key == "surface_preset":
        if value not in SURFACE_PRESETS:
            _emit(f"Invalid surface preset: {value}", Colors.RED)
            return True
        session.surface_preset = value
        _emit(f"Surface preset set to: {value}", Colors.GREEN)
        return True

    _emit(f"Unknown set key: {key}", Colors.YELLOW)
    return True


def handle_prompt_use_command(
    command_text: str,
    session: PromptSessionState,
    *,
    on_message: Callable[[str, str], None] | None = None,
) -> bool:
    def _emit(message: str, color: str) -> None:
        if on_message is None:
            print(c(message, color))
            return
        on_message(message, color)

    tokens = command_text.strip().split(maxsplit=1)
    if len(tokens) != 2:
        _emit("Usage: use <profile|surface|fusion>", Colors.YELLOW)
        return True
    module = tokens[1].strip().lower()
    if module not in VALID_MODULES:
        _emit(f"Unknown module: {module}", Colors.YELLOW)
        return True
    session.module = module
    _emit(f"Active module: {module}", Colors.GREEN)

    if not session.all_plugins:
        selected_plugins, rejected_plugins = _resolve_plugins_for_scope(session.plugin_names, module)
        session.plugin_names = selected_plugins
        if rejected_plugins:
            _emit(
                f"Removed incompatible plugins for module '{module}': {', '.join(rejected_plugins)}",
                Colors.YELLOW,
            )

    if not session.all_filters:
        selected_filters, rejected_filters = _resolve_filters_for_scope(session.filter_names, module)
        session.filter_names = selected_filters
        if rejected_filters:
            _emit(
                f"Removed incompatible filters for module '{module}': {', '.join(rejected_filters)}",
                Colors.YELLOW,
            )

    return True
