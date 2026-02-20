"""Framework about/description block."""

from __future__ import annotations

from core.metadata import AUTHOR, CONTACT_EMAIL, PROJECT_NAME, REPOSITORY_URL, TAGLINE, VERSION


def build_about_text() -> str:
    return (
        f"{PROJECT_NAME} v{VERSION}\n"
        f"Author: {AUTHOR}\n"
        f"Contact: {CONTACT_EMAIL}\n"
        f"Repository: {REPOSITORY_URL}\n"
        f"Description: {TAGLINE}\n"
        "Capabilities: profile intelligence, domain-surface reconnaissance, fusion correlation,\n"
        "plugin/filter extension pipeline, HTML/JSON/CLI reporting, Tor/proxy routing controls."
    )
