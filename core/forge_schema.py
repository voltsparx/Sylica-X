"""Signal Forge schema definitions for Silica-X."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


PluginContext = dict[str, Any]
PluginRunFn = Callable[[PluginContext], dict[str, Any]]


@dataclass(frozen=True)
class PluginSpec:
    plugin_id: str
    title: str
    description: str
    scopes: tuple[str, ...]
    version: str = "1.0"
    author: str = "Silica-X"
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class PluginExecutionResult:
    plugin_id: str
    title: str
    description: str
    scope: str
    summary: str
    severity: str
    highlights: tuple[str, ...]
    data: dict[str, Any]
