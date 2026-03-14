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

"""Prompt command parsing and session-state mutation helpers."""

from __future__ import annotations

import argparse
from typing import Callable

from core.interface.cli_config import EXTENSION_CONTROL_MODES, PROFILE_PRESETS, PROMPT_KEYWORDS, SURFACE_PRESETS
from core.foundation.colors import Colors, c
from core.extensions.control_plane import merge_scan_modes, resolve_extension_control
from core.extensions.selector_keys import selector_keys
from core.foundation.session_state import PromptSessionState
from core.extensions.signal_forge import list_plugin_descriptors
from core.extensions.signal_sieve import list_filter_descriptors
from core.utils.info_templates import get_info_template


VALID_MODULES = {"profile", "surface", "fusion"}
PROFILE_ALIASES = {"profile", "scan", "persona", "social"}
SURFACE_ALIASES = {"surface", "domain", "asset"}
FUSION_ALIASES = {"fusion", "full", "combo"}
ORCHESTRATE_ALIASES = {"orchestrate", "orch"}


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


def _prompt_explicit_flags(args: argparse.Namespace) -> set[str]:
    raw = getattr(args, "_explicit_flags", ())
    if not isinstance(raw, (list, tuple, set)):
        return set()
    explicit: set[str] = set()
    for value in raw:
        flag = str(value).strip().lower()
        if flag.startswith("--"):
            explicit.add(flag)
    return explicit


def _scope_for_args(args: argparse.Namespace, session: PromptSessionState) -> str | None:
    command = str(getattr(args, "command", "")).strip().lower()
    scope = _module_for_command(command)
    if scope is not None:
        return scope
    if command in ORCHESTRATE_ALIASES:
        selected_mode = str(getattr(args, "mode", session.module) or session.module)
        return _normalize_module(selected_mode)
    return None


def _default_orchestrate_profile(session: PromptSessionState, scope: str) -> str:
    if scope == "surface":
        return session.surface_preset
    return session.profile_preset


def _split_csv_values(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _dedupe_names(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def _scan_mode_for_scope(session: PromptSessionState, scope: str) -> str:
    normalized_scope = _normalize_module(scope)
    if normalized_scope == "surface":
        return session.surface_preset
    if normalized_scope == "fusion":
        return merge_scan_modes(session.profile_preset, session.surface_preset)
    return session.profile_preset


def _validate_extension_combo(
    *,
    scope: str,
    session: PromptSessionState,
    plugins: list[str],
    filters: list[str],
) -> list[str]:
    plan = resolve_extension_control(
        scope=scope,
        scan_mode=_scan_mode_for_scope(session, scope),
        control_mode="manual",
        requested_plugins=plugins,
        requested_filters=filters,
        include_all_plugins=False,
        include_all_filters=False,
    )
    return list(plan.errors)


def _descriptor_lookup(descriptors: list[dict[str, object]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for descriptor in descriptors:
        descriptor_id = str(descriptor.get("id", "")).strip().lower()
        if not descriptor_id:
            continue
        for key in selector_keys(descriptor_id):
            lookup.setdefault(key, descriptor_id)

        title = str(descriptor.get("title", "")).strip()
        if title:
            for key in selector_keys(title):
                lookup.setdefault(key, descriptor_id)

        aliases = descriptor.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                for key in selector_keys(str(alias)):
                    lookup.setdefault(key, descriptor_id)
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
        keys = selector_keys(raw_name)
        if not keys:
            continue
        matched: str | None = None
        for key in keys:
            matched = by_key.get(key)
            if matched is not None:
                break
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


def _mutate_selection(
    *,
    session: PromptSessionState,
    scope: str,
    kind: str,
    action: str,
    value: str,
    emit: Callable[[str, str], None],
) -> bool:
    if session.extension_control_for_module(scope) == "auto":
        emit(
            f"Cannot {action} {kind} for module '{scope}' while extension_control=auto. "
            "Use `set extension_control manual` or `set extension_control hybrid` first.",
            Colors.RED,
        )
        return True

    requested = _split_csv_values(value)
    if not requested:
        emit(f"Provide at least one {kind[:-1]} selector (id/alias/name).", Colors.YELLOW)
        return True

    if kind == "plugins":
        selected, rejected = _resolve_plugins_for_scope(requested, scope)
        if rejected:
            emit(
                f"Plugin selection blocked for module '{scope}'. "
                f"Incompatible or unknown selectors: {', '.join(rejected)}",
                Colors.RED,
            )
            emit("Use `plugins --scope ...` to inspect compatible selectors.", Colors.YELLOW)
            return True
        current = _dedupe_names(session.plugin_names)
        if action == "add":
            updated = _dedupe_names([*current, *selected])
        else:
            remove_set = set(_dedupe_names(selected))
            updated = [item for item in current if item not in remove_set]
        errors = _validate_extension_combo(
            scope=scope,
            session=session,
            plugins=updated,
            filters=session.filter_names,
        )
        if errors:
            for item in errors:
                emit(f"Plugin selection blocked: {item}", Colors.RED)
            return True
        session.plugin_names = updated
        emit(f"Plugins set to: {session.plugins_label()} (module={scope})", Colors.GREEN)
        return True

    selected, rejected = _resolve_filters_for_scope(requested, scope)
    if rejected:
        emit(
            f"Filter selection blocked for module '{scope}'. "
            f"Incompatible or unknown selectors: {', '.join(rejected)}",
            Colors.RED,
        )
        emit("Use `filters --scope ...` to inspect compatible selectors.", Colors.YELLOW)
        return True
    current = _dedupe_names(session.filter_names)
    if action == "add":
        updated = _dedupe_names([*current, *selected])
    else:
        remove_set = set(_dedupe_names(selected))
        updated = [item for item in current if item not in remove_set]
    errors = _validate_extension_combo(
        scope=scope,
        session=session,
        plugins=session.plugin_names,
        filters=updated,
    )
    if errors:
        for item in errors:
            emit(f"Filter selection blocked: {item}", Colors.RED)
        return True
    session.filter_names = updated
    emit(f"Filters set to: {session.filters_label()} (module={scope})", Colors.GREEN)
    return True


def apply_prompt_defaults(args: argparse.Namespace, session: PromptSessionState) -> argparse.Namespace:
    command = str(getattr(args, "command", "")).strip().lower()
    scope = _scope_for_args(args, session)
    if scope is None:
        return args

    explicit_flags = _prompt_explicit_flags(args)

    if not getattr(args, "plugin", None):
        args.plugin, _ = _resolve_plugins_for_scope(session.plugin_names, scope)

    if not getattr(args, "filter", None):
        args.filter, _ = _resolve_filters_for_scope(session.filter_names, scope)

    if hasattr(args, "extension_control") and "--extension-control" not in explicit_flags:
        if command in ORCHESTRATE_ALIASES:
            args.extension_control = session.orchestrate_extension_control
        else:
            args.extension_control = session.extension_control_for_module(scope)

    if command in PROFILE_ALIASES:
        if "--preset" not in explicit_flags:
            args.preset = session.profile_preset
        return args

    if command in SURFACE_ALIASES:
        if "--preset" not in explicit_flags:
            args.preset = session.surface_preset
        return args

    if command in FUSION_ALIASES:
        if "--profile-preset" not in explicit_flags:
            args.profile_preset = session.profile_preset
        if "--surface-preset" not in explicit_flags:
            args.surface_preset = session.surface_preset
        return args

    if command in ORCHESTRATE_ALIASES:
        if "--profile" not in explicit_flags:
            args.profile = _default_orchestrate_profile(session, scope)
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
        _emit(
            "Usage: set <template|plugins|filters|profile_preset|surface_preset|extension_control|orchestrate_extension_control> <value>",
            Colors.YELLOW,
        )
        return True

    _, key, value = tokens
    key = key.strip().lower().replace("-", "_")
    if key in {"ext", "extension", "control"}:
        key = "extension_control"
    if key == "orchestrate_control":
        key = "orchestrate_extension_control"
    value = value.strip()
    scope = _normalize_module(session.module)

    if key in {"template", "info_template"}:
        if session.extension_control_for_module(scope) == "auto":
            _emit(
                f"Cannot set template for module '{scope}' while extension_control=auto. "
                "Use `set extension_control manual` or `set extension_control hybrid` first.",
                Colors.RED,
            )
            return True
        lower = value.lower()
        if lower in {"none", "off"}:
            session.plugin_names = []
            session.filter_names = []
            _emit(f"Template cleared; plugins/filters reset (module={scope}).", Colors.GREEN)
            return True
        try:
            template = get_info_template(value, scope=scope)
        except ValueError as exc:
            _emit(str(exc), Colors.RED)
            return True
        template_plugins = list(template.get("plugins", ()))
        template_filters = list(template.get("filters", ()))
        errors = _validate_extension_combo(
            scope=scope,
            session=session,
            plugins=template_plugins,
            filters=template_filters,
        )
        if errors:
            for item in errors:
                _emit(f"Template selection blocked: {item}", Colors.RED)
            return True
        session.plugin_names = template_plugins
        session.filter_names = template_filters
        _emit(
            f"Template applied: {template.get('id')} "
            f"(plugins={len(template_plugins)} filters={len(template_filters)}) (module={scope})",
            Colors.GREEN,
        )
        module_tags = template.get("module_tags", ())
        if module_tags:
            _emit(f"Module tags: {', '.join(module_tags)}", Colors.YELLOW)
        _emit(str(template.get("notes", "")), Colors.GREY)
        return True

    if key == "plugins":
        if session.extension_control_for_module(scope) == "auto":
            _emit(
                f"Cannot set plugins for module '{scope}' while extension_control=auto. "
                "Use `set extension_control manual` or `set extension_control hybrid` first.",
                Colors.RED,
            )
            return True
        lower = value.lower()
        if lower == "all":
            _emit(
                "Bulk plugin selection is disabled. Use explicit selectors or `set template <id>` instead.",
                Colors.RED,
            )
            return True
        if lower in {"none", "off"}:
            session.plugin_names = []
            _emit(f"Plugins set to: {session.plugins_label()} (module={scope})", Colors.GREEN)
            return True
        requested = _split_csv_values(value)
        if not requested:
            _emit("Provide at least one plugin selector (id/alias/name).", Colors.YELLOW)
            return True
        selected, rejected = _resolve_plugins_for_scope(requested, scope)
        if rejected:
            _emit(
                f"Plugin selection blocked for module '{scope}'. "
                f"Incompatible or unknown selectors: {', '.join(rejected)}",
                Colors.RED,
            )
            _emit("Use `plugins --scope ...` to inspect compatible selectors.", Colors.YELLOW)
            return True
        if not selected:
            _emit(f"No compatible plugins selected for module '{scope}'.", Colors.RED)
            return True
        errors = _validate_extension_combo(
            scope=scope,
            session=session,
            plugins=selected,
            filters=session.filter_names,
        )
        if errors:
            for item in errors:
                _emit(f"Plugin selection blocked: {item}", Colors.RED)
            return True
        session.plugin_names = selected
        _emit(f"Plugins set to: {session.plugins_label()} (module={scope})", Colors.GREEN)
        return True

    if key == "filters":
        if session.extension_control_for_module(scope) == "auto":
            _emit(
                f"Cannot set filters for module '{scope}' while extension_control=auto. "
                "Use `set extension_control manual` or `set extension_control hybrid` first.",
                Colors.RED,
            )
            return True
        lower = value.lower()
        if lower == "all":
            _emit(
                "Bulk filter selection is disabled. Use explicit selectors or `set template <id>` instead.",
                Colors.RED,
            )
            return True
        if lower in {"none", "off"}:
            session.filter_names = []
            _emit(f"Filters set to: {session.filters_label()} (module={scope})", Colors.GREEN)
            return True
        requested = _split_csv_values(value)
        if not requested:
            _emit("Provide at least one filter selector (id/alias/name).", Colors.YELLOW)
            return True
        selected, rejected = _resolve_filters_for_scope(requested, scope)
        if rejected:
            _emit(
                f"Filter selection blocked for module '{scope}'. "
                f"Incompatible or unknown selectors: {', '.join(rejected)}",
                Colors.RED,
            )
            _emit("Use `filters --scope ...` to inspect compatible selectors.", Colors.YELLOW)
            return True
        if not selected:
            _emit(f"No compatible filters selected for module '{scope}'.", Colors.RED)
            return True
        errors = _validate_extension_combo(
            scope=scope,
            session=session,
            plugins=session.plugin_names,
            filters=selected,
        )
        if errors:
            for item in errors:
                _emit(f"Filter selection blocked: {item}", Colors.RED)
            return True
        session.filter_names = selected
        _emit(f"Filters set to: {session.filters_label()} (module={scope})", Colors.GREEN)
        return True

    if key == "profile_preset":
        normalized_value = value.lower()
        if normalized_value not in PROFILE_PRESETS:
            _emit(f"Invalid profile preset: {value}", Colors.RED)
            return True
        session.profile_preset = normalized_value
        _emit(f"Profile preset set to: {normalized_value}", Colors.GREEN)
        return True

    if key == "surface_preset":
        normalized_value = value.lower()
        if normalized_value not in SURFACE_PRESETS:
            _emit(f"Invalid surface preset: {value}", Colors.RED)
            return True
        session.surface_preset = normalized_value
        _emit(f"Surface preset set to: {normalized_value}", Colors.GREEN)
        return True

    if key == "extension_control":
        normalized_value = value.lower()
        if normalized_value not in EXTENSION_CONTROL_MODES:
            _emit(f"Invalid extension control mode: {value}", Colors.RED)
            return True
        if normalized_value == "auto" and (bool(session.plugin_names) or bool(session.filter_names)):
            _emit(
                f"Cannot set extension_control=auto for module '{scope}' while plugins/filters are configured. "
                "Reset them first with `set plugins none` and `set filters none`.",
                Colors.RED,
            )
            return True
        session.set_extension_control_for_module(scope, normalized_value)
        _emit(f"Extension control set to: {normalized_value} (module={scope})", Colors.GREEN)
        return True

    if key == "orchestrate_extension_control":
        normalized_value = value.lower()
        if normalized_value not in EXTENSION_CONTROL_MODES:
            _emit(f"Invalid orchestrate extension control mode: {value}", Colors.RED)
            return True
        if normalized_value == "auto" and (bool(session.plugin_names) or bool(session.filter_names)):
            _emit(
                "Cannot set orchestrate_extension_control=auto while plugins/filters are configured. "
                "Reset them first with `set plugins none` and `set filters none`.",
                Colors.RED,
            )
            return True
        session.orchestrate_extension_control = normalized_value
        _emit(f"Orchestrate extension control set to: {normalized_value}", Colors.GREEN)
        return True

    _emit(f"Unknown set key: {key}", Colors.YELLOW)
    return True


def handle_prompt_control_command(
    command_text: str,
    session: PromptSessionState,
    *,
    on_message: Callable[[str, str], None] | None = None,
) -> bool:
    """Handle prompt selection controls: select/add/remove for module/plugins/filters."""

    def _emit(message: str, color: str) -> None:
        if on_message is None:
            print(c(message, color))
            return
        on_message(message, color)

    tokens = command_text.strip().split(maxsplit=2)
    if not tokens:
        return False

    verb = tokens[0].strip().lower()
    if verb not in {"select", "add", "remove"}:
        return False
    if len(tokens) < 3:
        _emit("Usage: select|add|remove <module|plugins|filters> <value>", Colors.YELLOW)
        return True

    target = tokens[1].strip().lower().replace("-", "_")
    value = tokens[2].strip()
    if target in {"module", "mode"}:
        if verb != "select":
            _emit("Only `select module <profile|surface|fusion>` is supported for module controls.", Colors.YELLOW)
            return True
        return handle_prompt_use_command(f"use {value}", session, on_message=on_message)

    if target in {"template", "info_template", "info-template"}:
        if verb != "select":
            _emit("Only `select template <id>` is supported for template controls.", Colors.YELLOW)
            return True
        return handle_prompt_set_command(f"set template {value}", session, on_message=on_message)

    if target in {"plugins", "plugin"}:
        if verb == "select":
            return handle_prompt_set_command(f"set plugins {value}", session, on_message=on_message)
        scope = _normalize_module(session.module)
        return _mutate_selection(
            session=session,
            scope=scope,
            kind="plugins",
            action=verb,
            value=value,
            emit=_emit,
        )

    if target in {"filters", "filter"}:
        if verb == "select":
            return handle_prompt_set_command(f"set filters {value}", session, on_message=on_message)
        scope = _normalize_module(session.module)
        return _mutate_selection(
            session=session,
            scope=scope,
            kind="filters",
            action=verb,
            value=value,
            emit=_emit,
        )

    _emit(f"Unknown control target: {target}", Colors.YELLOW)
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

    selected_plugins, rejected_plugins = _resolve_plugins_for_scope(session.plugin_names, module)
    session.plugin_names = selected_plugins
    if rejected_plugins:
        _emit(
            f"Removed incompatible plugins for module '{module}': {', '.join(rejected_plugins)}",
            Colors.YELLOW,
        )

    selected_filters, rejected_filters = _resolve_filters_for_scope(session.filter_names, module)
    session.filter_names = selected_filters
    if rejected_filters:
        _emit(
            f"Removed incompatible filters for module '{module}': {', '.join(rejected_filters)}",
            Colors.YELLOW,
        )

    return True

