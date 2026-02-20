"""Signal Sieve schema definitions for Silica-X."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FilterContext = dict[str, Any]


@dataclass(frozen=True)
class FilterSpec:
    filter_id: str
    title: str
    description: str
    scopes: tuple[str, ...]
    version: str = "1.0"
    author: str = "Silica-X"
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilterExecutionResult:
    filter_id: str
    title: str
    description: str
    scope: str
    summary: str
    severity: str
    highlights: tuple[str, ...]
    data: dict[str, Any]
