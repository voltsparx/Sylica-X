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

"""Compatibility facade for capability matrix APIs used by intel modules."""

from __future__ import annotations

from core.intel_pack import (
    DEFAULT_CAPABILITY_PACK_ROOT,
    DEFAULT_SOURCE_MAP_PATH,
    build_capability_pack,
    build_capability_gap_report,
    build_runtime_inventory_snapshot,
    load_source_map,
    load_capability_index,
    map_sources_to_core_modules,
    recommend_capability_priorities,
    recommend_focus_modules,
    render_capability_markdown,
    scan_source_capabilities,
    write_capability_report,
    write_runtime_inventory_snapshot,
)

__all__ = [
    "DEFAULT_CAPABILITY_PACK_ROOT",
    "DEFAULT_SOURCE_MAP_PATH",
    "build_capability_pack",
    "build_capability_gap_report",
    "build_runtime_inventory_snapshot",
    "load_source_map",
    "load_capability_index",
    "map_sources_to_core_modules",
    "recommend_capability_priorities",
    "recommend_focus_modules",
    "render_capability_markdown",
    "scan_source_capabilities",
    "write_capability_report",
    "write_runtime_inventory_snapshot",
]
