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

"""Standalone launcher for the shared live dashboard implementation."""

from __future__ import annotations

import argparse

from core.runner import DEFAULT_DASHBOARD_PORT, launch_live_dashboard


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m core.interface.live_server")
    parser.add_argument(
        "target",
        nargs="?",
        help="Target id (latest) to load from output/json/<target>-info-<timestamp>.json.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_DASHBOARD_PORT,
        help=f"Dashboard port (default: {DEFAULT_DASHBOARD_PORT}).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open browser.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    target = (args.target or "").strip()
    if not target:
        target = input("Enter target to view live results: ").strip()
    if not target:
        print("Target is required.")
        return 2

    launch_live_dashboard(
        target=target,
        port=args.port,
        open_browser=not args.no_browser,
        background=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
