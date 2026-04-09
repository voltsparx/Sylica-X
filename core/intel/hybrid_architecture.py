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

"""Silica-X hybrid architecture descriptors for runtime inventory and docs."""

from __future__ import annotations

from copy import deepcopy

from core.foundation.metadata import PROJECT_NAME, VERSION, VERSION_THEME


_HYBRID_ARCHITECTURE: dict[str, object] = {
    "identity": "silica-x-hybrid",
    "project": PROJECT_NAME,
    "version": VERSION,
    "theme": VERSION_THEME,
    "tagline": "Silica-X native console, registry, event-flow, and fusion architecture.",
    "engines": ("async", "thread", "process", "hybrid", "fusion"),
    "lanes": (
        {
            "id": "console-dispatch",
            "label": "Console Dispatch",
            "summary": "Prompt routing, startup identity, help hints, and session-aware console UX.",
            "native_modules": (
                "core/runner.py",
                "core/interface/banner.py",
                "core/interface/help_menu.py",
                "core/foundation/session_state.py",
            ),
        },
        {
            "id": "registry-session",
            "label": "Registry + Session Control",
            "summary": "Module catalog, plugin/filter discovery, selectors, presets, and runtime state management.",
            "native_modules": (
                "modules/catalog.py",
                "core/extensions/plugin_manager.py",
                "core/extensions/signal_forge.py",
                "core/extensions/signal_sieve.py",
            ),
        },
        {
            "id": "event-flow",
            "label": "Event Flow",
            "summary": "Collection pipelines, queue-like distribution, and staged scan lifecycle orchestration.",
            "native_modules": (
                "core/collect/scanner.py",
                "core/collect/domain_intel.py",
                "core/orchestrator.py",
                "core/engine_manager.py",
            ),
        },
        {
            "id": "fusion-graph",
            "label": "Fusion + Reporting",
            "summary": "Entity correlation, confidence scoring, graph synthesis, and multi-format analyst outputs.",
            "native_modules": (
                "core/engines/fusion_engine.py",
                "core/intelligence/intelligence_engine.py",
                "core/artifacts/output.py",
                "core/artifacts/reporting.py",
            ),
        },
    ),
    "inspiration": (
        {
            "id": "metasploit-ui",
            "source": "temp/only-ui-architecture/metasploit-framework-master",
            "patterns": (
                "module-aware console prompt",
                "startup banner + inventory rhythm",
                "rotating spinner feedback",
                "friendly unknown-command recovery",
            ),
        },
        {
            "id": "amass-registry",
            "source": "temp/amass",
            "patterns": (
                "registry + dispatcher composition",
                "session manager topology",
                "plugin-backed engine startup",
            ),
        },
        {
            "id": "bbot-event-flow",
            "source": "temp/bbot",
            "patterns": (
                "event-driven scan lifecycle",
                "parallel module lanes",
                "queue-oriented workload distribution",
            ),
        },
    ),
}


def build_hybrid_architecture_snapshot() -> dict[str, object]:
    """Return the Silica-X hybrid architecture snapshot."""

    return deepcopy(_HYBRID_ARCHITECTURE)


def hybrid_inventory_metrics(snapshot: dict[str, object] | None = None) -> dict[str, int]:
    """Return numeric hybrid inventory metrics for boot diagnostics."""

    current = snapshot or build_hybrid_architecture_snapshot()
    lanes = current.get("lanes", ())
    inspiration = current.get("inspiration", ())
    engines = current.get("engines", ())
    return {
        "lane_count": len(lanes) if isinstance(lanes, tuple | list) else 0,
        "inspiration_count": len(inspiration) if isinstance(inspiration, tuple | list) else 0,
        "engine_count": len(engines) if isinstance(engines, tuple | list) else 0,
    }


def render_hybrid_inventory_lines(snapshot: dict[str, object] | None = None) -> tuple[str, ...]:
    """Render short inventory lines suitable for CLI startup output."""

    current = snapshot or build_hybrid_architecture_snapshot()
    lanes = current.get("lanes", ())
    lane_ids = []
    if isinstance(lanes, tuple | list):
        lane_ids = [str(item.get("id", "")) for item in lanes if isinstance(item, dict)]

    inspirations = current.get("inspiration", ())
    inspiration_ids = []
    if isinstance(inspirations, tuple | list):
        inspiration_ids = [str(item.get("id", "")) for item in inspirations if isinstance(item, dict)]

    engines = current.get("engines", ())
    engine_labels = [str(item) for item in engines] if isinstance(engines, tuple | list) else []

    return (
        f"Hybrid: {' | '.join(lane_ids)}",
        f"Patterns: {' | '.join(inspiration_ids)}",
        f"Engines: {' | '.join(engine_labels)}",
    )
