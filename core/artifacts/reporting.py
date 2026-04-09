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

"""Compatibility shim for legacy imports."""

from __future__ import annotations

from typing import Any

from core.artifacts.html_report import generate_html as _generate_html
from core.artifacts.storage import sanitize_target
from core.reporting.report_generator import ReportGenerator as _BaseReportGenerator


def generate_html(*args: Any, **kwargs: Any) -> str:
    """Proxy to HTML generator (patchable in tests)."""

    return _generate_html(*args, **kwargs)


class ReportGenerator(_BaseReportGenerator):
    """Compat wrapper that routes HTML generation through this module."""

    def generate_html_dashboard(self, fused_data: dict[str, Any]) -> str:
        target_data = fused_data.get("target")
        if isinstance(target_data, dict):
            username = str(target_data.get("username") or "").strip()
            domain = str(target_data.get("domain") or "").strip()
            token = f"{username}_{domain}".strip("_")
            target = sanitize_target(token or "fused-target")
        else:
            target = sanitize_target(str(target_data or "fused-target"))

        output_stamp = fused_data.get("output_stamp") if isinstance(fused_data, dict) else None
        intelligence_bundle = (
            fused_data.get("intelligence_bundle")
            if isinstance(fused_data.get("intelligence_bundle"), dict)
            else (fused_data.get("fused_intel", {}) or {}).get("intelligence_bundle")
        )
        return generate_html(
            target=target,
            results=list(fused_data.get("results", []) or []),
            correlation=dict(fused_data.get("correlation", {}) or {}),
            issues=list(fused_data.get("issues", []) or []),
            issue_summary=dict(fused_data.get("issue_summary", {}) or {}),
            narrative=str(fused_data.get("narrative") or ""),
            domain_result=fused_data.get("domain_result") if isinstance(fused_data.get("domain_result"), dict) else None,
            mode=str(fused_data.get("mode") or "fusion"),
            plugin_results=list(fused_data.get("plugins", []) or []),
            plugin_errors=list(fused_data.get("plugin_errors", []) or []),
            filter_results=list(fused_data.get("filters", []) or []),
            filter_errors=list(fused_data.get("filter_errors", []) or []),
            intelligence_bundle=intelligence_bundle if isinstance(intelligence_bundle, dict) else {},
            output_stamp=output_stamp,
        )

__all__ = ["ReportGenerator", "generate_html"]
