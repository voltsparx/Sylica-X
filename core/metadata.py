"""Central project metadata for Silica-X."""

from __future__ import annotations

from datetime import datetime, timezone


PROJECT_NAME = "Silica-X"
VERSION = "7.0"
AUTHOR = "voltsparx"
AUTHOR_HANDLE = "voltsparx"
CONTACT_EMAIL = "voltsparx@gmail.com"
REPOSITORY_URL = f"https://github.com/{AUTHOR_HANDLE}/{PROJECT_NAME}"
TAGLINE = "Framework for cross-referencing OSINT data to support analysis work"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def framework_signature() -> str:
    return f"{PROJECT_NAME} v{VERSION} by {AUTHOR} ({CONTACT_EMAIL})"


def about_block() -> str:
    return (
        f"{PROJECT_NAME} v{VERSION}\n"
        f"Author: {AUTHOR}\n"
        f"Contact: {CONTACT_EMAIL}\n"
        f"Repo: {REPOSITORY_URL}\n"
        f"{TAGLINE}"
    )
