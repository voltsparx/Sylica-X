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

"""Central project metadata for Silica-X."""

from __future__ import annotations

from datetime import datetime, timezone


PROJECT_NAME = "Silica-X"
VERSION = "10.0"
VERSION_THEME = "Ember"
AUTHOR = "voltsparx"
AUTHOR_HANDLE = "voltsparx"
CONTACT_EMAIL = "voltsparx@gmail.com"
REPOSITORY_URL = f"https://github.com/{AUTHOR_HANDLE}/{PROJECT_NAME}"
TAGLINE = "OSINT orchestration, media intelligence, and Reporter-grade analysis artifacts"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def framework_signature() -> str:
    return f"{PROJECT_NAME} v{VERSION} [{VERSION_THEME}] by {AUTHOR} ({CONTACT_EMAIL})"


def about_block() -> str:
    return (
        f"{PROJECT_NAME} v{VERSION}\n"
        f"Theme: {VERSION_THEME}\n"
        f"Author: {AUTHOR}\n"
        f"Contact: {CONTACT_EMAIL}\n"
        f"Repo: {REPOSITORY_URL}\n"
        f"{TAGLINE}"
    )
