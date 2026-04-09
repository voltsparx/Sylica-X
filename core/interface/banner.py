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

from core.foundation.colors import Colors, c
from core.foundation.metadata import AUTHOR, PROJECT_NAME, VERSION, VERSION_THEME


def show_banner(anonymity_status: str = "No Anonymization") -> None:
    left_right_lines = [
        ("       .d8888. d888888b db      d888888b  .o88b.  .d8b.", "          db    db"),
        ("       88'  YP   `88'   88        `88'   d8P  Y8 d8' `8b", "         `8b  d8'"),
        ("       `8bo.      88    88         88    8P      88ooo88", "          `8bd8'"),
        ("         `Y8b.    88    88         88    8b      88~~~88  C8888D", "  .dPYb."),
        ("       db   8D   .88.   88booo.   .88.   Y8b  d8 88   88", "         .8P  Y8."),
        ("       `8888Y' Y888888P Y88888P Y888888P  `Y88P' YP   YP", "         YP    YP"),
    ]
    for left, right in left_right_lines:
        print(c(left, Colors.GREY) + c(right, Colors.YELLOW))

    print(c(f"                                                                          v{VERSION} [{VERSION_THEME}]", Colors.GREY))
    print("_" * 89)
    print(c(f"    {PROJECT_NAME} hybrid console by {AUTHOR} (github.com/{AUTHOR})", Colors.CYAN))
    print(c("    Hybrid console lanes: dispatch | registry | event-flow | fusion", Colors.GREY))
    print(c(f"    Current anonymity: {anonymity_status}", Colors.CYAN))
    print(c("    Type `help` for commands, `show config` for context, `exit` to quit.", Colors.GREY))
    print()
