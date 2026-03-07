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

"""Prompt session state helpers."""

from __future__ import annotations

from dataclasses import dataclass, field


def _compact_prompt_values(values: list[str], *, max_items: int = 2) -> str:
    if not values:
        return "none"
    if len(values) <= max_items:
        return ",".join(values)
    shown = ",".join(values[:max_items])
    remaining = len(values) - max_items
    return f"{shown},+{remaining}"


@dataclass
class PromptSessionState:
    module: str = "profile"
    plugin_names: list[str] = field(default_factory=list)
    filter_names: list[str] = field(default_factory=list)
    history: list[str] = field(default_factory=list)
    all_plugins: bool = False
    all_filters: bool = False
    profile_preset: str = "balanced"
    surface_preset: str = "balanced"
    profile_extension_control: str = "manual"
    surface_extension_control: str = "manual"
    fusion_extension_control: str = "manual"
    orchestrate_extension_control: str = "auto"

    def plugins_label(self) -> str:
        if self.all_plugins:
            return "all"
        if not self.plugin_names:
            return "none"
        return ",".join(self.plugin_names)

    def filters_label(self) -> str:
        if self.all_filters:
            return "all"
        if not self.filter_names:
            return "none"
        return ",".join(self.filter_names)

    def extension_control_for_module(self, module: str) -> str:
        normalized = str(module or "").strip().lower()
        if normalized == "surface":
            return self.surface_extension_control
        if normalized == "fusion":
            return self.fusion_extension_control
        return self.profile_extension_control

    def set_extension_control_for_module(self, module: str, value: str) -> None:
        normalized = str(module or "").strip().lower()
        lowered_value = str(value or "").strip().lower()
        if normalized == "surface":
            self.surface_extension_control = lowered_value
            return
        if normalized == "fusion":
            self.fusion_extension_control = lowered_value
            return
        self.profile_extension_control = lowered_value

    def module_prompt(self) -> str:
        control_label = self.extension_control_for_module(self.module)
        plugin_label = "all" if self.all_plugins else _compact_prompt_values(self.plugin_names)
        filter_label = "all" if self.all_filters else _compact_prompt_values(self.filter_names)
        return f"(console {self.module} ec={control_label} plugins={plugin_label} filters={filter_label})>>"
