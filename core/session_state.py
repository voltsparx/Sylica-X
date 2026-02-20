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
    all_plugins: bool = False
    all_filters: bool = False
    profile_preset: str = "balanced"
    surface_preset: str = "balanced"

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

    def module_prompt(self) -> str:
        plugin_label = "all" if self.all_plugins else _compact_prompt_values(self.plugin_names)
        filter_label = "all" if self.all_filters else _compact_prompt_values(self.filter_names)
        return f"(console {self.module} plugins={plugin_label} filters={filter_label})>>"
