"""Compatibility facade for capability matrix APIs used by intel modules."""

from __future__ import annotations

from core.reverse_engineering import (
    DEFAULT_CAPABILITY_PACK_ROOT,
    DEFAULT_SOURCE_MAP_PATH,
    build_capability_pack,
    build_capability_gap_report,
    load_source_map,
    load_capability_index,
    map_sources_to_core_modules,
    recommend_capability_priorities,
    recommend_focus_modules,
    render_capability_markdown,
    scan_source_capabilities,
    write_capability_report,
)

__all__ = [
    "DEFAULT_CAPABILITY_PACK_ROOT",
    "DEFAULT_SOURCE_MAP_PATH",
    "build_capability_pack",
    "build_capability_gap_report",
    "load_source_map",
    "load_capability_index",
    "map_sources_to_core_modules",
    "recommend_capability_priorities",
    "recommend_focus_modules",
    "render_capability_markdown",
    "scan_source_capabilities",
    "write_capability_report",
]
