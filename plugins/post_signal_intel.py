"""Plugin: public post-text OSINT extraction from discovered profile content."""

from __future__ import annotations

from plugins.media_recon_shared import resolve_media_recon_payload


PLUGIN_SPEC = {
    "id": "post_signal_intel",
    "title": "Post Signal Intelligence",
    "description": "Extracts OSINT cues from public profile and post-like text fragments harvested during profile scans.",
    "scopes": ["profile", "fusion"],
    "aliases": ["post_intel", "text_intel", "caption_intel"],
    "version": "1.0",
}


def run(context: dict) -> dict:
    result = resolve_media_recon_payload(context)
    signals = result.text_signals
    indicators = len(signals.emails) + len(signals.urls) + len(signals.phones) + len(signals.hashtags) + len(signals.mentions)

    if indicators >= 5:
        severity = "MEDIUM"
    else:
        severity = "INFO"

    summary = (
        f"Post Signal Intelligence parsed {signals.fragment_count} public text fragment(s) and extracted "
        f"{len(signals.emails)} email(s), {len(signals.urls)} URL(s), {len(signals.phones)} phone hint(s), "
        f"{len(signals.mentions)} mention(s), and {len(signals.hashtags)} hashtag(s)."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"fragments={signals.fragment_count}",
            f"emails={len(signals.emails)}",
            f"urls={len(signals.urls)}",
            f"phones={len(signals.phones)}",
            f"keywords={len(signals.keywords)}",
        ],
        "data": {
            "target": result.target,
            "targets": result.targets.as_dict(),
            "text_signals": signals.as_dict(),
            "notes": list(result.notes),
        },
    }

