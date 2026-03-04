"""JSON reporter for orchestrated intelligence payloads."""

from __future__ import annotations

import json
from typing import Any


def render_json_report(payload: dict[str, Any]) -> str:
    """Render payload as pretty JSON text."""

    return json.dumps(payload, indent=2)
