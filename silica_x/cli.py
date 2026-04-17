"""Console entrypoint for Silica-X."""

from __future__ import annotations

import asyncio
import sys
from typing import Sequence

from core.runner import run


def main(argv: Sequence[str] | None = None) -> None:
    """Run the Silica-X CLI."""
    try:
        raise SystemExit(asyncio.run(run(argv)))
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # pragma: no cover - final entrypoint guard
        print(f"[!] Silica-X failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
