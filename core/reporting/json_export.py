"""JSON export helpers for orchestrator payloads."""

from __future__ import annotations

from typing import Any


def build_json_payload(
    target: str,
    mode: str,
    fused_data: dict[str, Any],
    advisory: dict[str, Any],
    lifecycle: dict[str, Any],
) -> dict[str, Any]:
    """Build export payload without mutating source dictionaries."""

    return {
        "target": target,
        "mode": mode,
        "fused": dict(fused_data),
        "advisory": dict(advisory),
        "lifecycle": dict(lifecycle),
    }
