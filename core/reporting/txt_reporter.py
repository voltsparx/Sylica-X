"""Text reporter for orchestrated intelligence payloads."""

from __future__ import annotations

from typing import Any

from core.reporting.cli_view import render_cli_summary


def render_txt_report(fused_data: dict[str, Any], advisory: dict[str, Any]) -> str:
    """Render human-readable text report."""

    return render_cli_summary(fused_data, advisory)
