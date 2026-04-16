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

"""ANSI color helpers used across CLI rendering."""

from __future__ import annotations

import os
import sys


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    WHITE = "\033[38;5;255m"
    SILVER = "\033[38;5;250m"
    GREY = "\033[38;5;245m"
    DARK_GREY = "\033[38;5;240m"

    EMBER = "\033[38;5;208m"
    AMBER = "\033[38;5;215m"
    YELLOW = EMBER
    CYAN = "\033[38;5;215m"
    BLUE = "\033[38;5;208m"
    MAGENTA = "\033[38;5;209m"

    GREEN = "\033[38;5;214m"
    RED = "\033[38;5;196m"
    ORANGE = "\033[38;5;202m"

    # Backward-compatible aliases
    GRAY = GREY
    DARK_GRAY = DARK_GREY
    LIGHT_GREY = SILVER
    LIGHT_GRAY = SILVER
    DEFAULT = RESET


def _colors_enabled() -> bool:
    force = os.getenv("FORCE_COLOR", "").strip().lower()
    if force in {"1", "true", "yes", "on"}:
        return True
    if os.getenv("NO_COLOR") is not None:
        return False
    stream = getattr(sys, "stdout", None)
    return bool(stream and hasattr(stream, "isatty") and stream.isatty())


def c(text: object, color: str | None) -> str:
    """Apply ANSI color to text when supported by runtime/terminal."""
    rendered = str(text)
    if not color or not _colors_enabled():
        return rendered
    return f"{color}{rendered}{Colors.RESET}"


def bold(text: object) -> str:
    return c(text, Colors.BOLD)


def dim(text: object) -> str:
    return c(text, Colors.DIM)
