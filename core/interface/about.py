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

"""Framework about/description block."""

from __future__ import annotations

from core.foundation.metadata import AUTHOR, CONTACT_EMAIL, PROJECT_NAME, REPOSITORY_URL, TAGLINE, VERSION, VERSION_THEME


def build_about_text() -> str:
    return (
        f"{PROJECT_NAME} v{VERSION}\n"
        f"Theme: {VERSION_THEME}\n"
        f"Author: {AUTHOR}\n"
        f"Contact: {CONTACT_EMAIL}\n"
        f"Repository: {REPOSITORY_URL}\n"
        f"Description: {TAGLINE}\n"
        "Capabilities: profile intelligence, domain-surface reconnaissance, fusion correlation,\n"
        "digital footprint mapping, plugin/filter extension pipeline, HTML/JSON/CLI reporting,\n"
        "Tor/proxy routing controls."
    )
