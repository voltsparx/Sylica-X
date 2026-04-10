# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Sylica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Sylica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Sylica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

from core.foundation.colors import Colors, c
from core.foundation.metadata import AUTHOR, PROJECT_NAME, VERSION, VERSION_THEME
from core.foundation.research_scope import AUTHORIZED_RESEARCH_NOTICE


def show_banner(anonymity_status: str = "No Anonymization") -> None:
    banner_lines = (
        ".d8888. db    db db      d888888b  .o88b.  .d8b.          db    db",
        "88'  YP `8b  d8' 88        `88'   d8P  Y8 d8' `8b         `8b  d8'",
        "`8bo.    `8bd8'  88         88    8P      88ooo88          `8bd8' ",
        "  `Y8b.    88    88         88    8b      88~~~88  C8888D  .dPYb. ",
        "db   8D    88    88booo.   .88.   Y8b  d8 88   88         .8P  Y8.",
        "`8888Y'    YP    Y88888P Y888888P  `Y88P' YP   YP         YP    YP",
    )
    for line in banner_lines:
        print(c(f"       {line}", Colors.GREY))

    print(c(f"                                                                          v{VERSION} [{VERSION_THEME}]", Colors.GREY))
    print("_" * 89)
    print(c(f"    {PROJECT_NAME} hybrid console by {AUTHOR} (github.com/{AUTHOR})", Colors.CYAN))
    print(c("    Hybrid console lanes: dispatch | registry | event-flow | fusion", Colors.GREY))
    print(c(f"    Current anonymity: {anonymity_status}", Colors.CYAN))
    for notice_line in AUTHORIZED_RESEARCH_NOTICE:
        print(c(f"    {notice_line}", Colors.GREY))
    print(c("    Type `help` for commands, `show config` for context, `exit` to quit.", Colors.GREY))
    print()
