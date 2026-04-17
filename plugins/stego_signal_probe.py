"""Plugin: lightweight stego-suspicion heuristics for public image assets."""

from __future__ import annotations

from plugins.media_recon_shared import resolve_media_recon_payload


PLUGIN_SPEC = {
    "id": "stego_signal_probe",
    "title": "Stego Signal Probe",
    "description": "Scores public image assets for lightweight stego-suspicion indicators such as entropy and container density.",
    "scopes": ["profile", "fusion"],
    "aliases": ["stego_probe", "stago_probe", "image_stego"],
    "version": "1.0",
}


def run(context: dict) -> dict:
    result = resolve_media_recon_payload(context)
    flagged = [item for item in result.image_assets if item.stego_flags]
    highest = max((item.stego_score for item in flagged), default=0.0)

    if highest >= 0.75:
        severity = "HIGH"
    elif flagged:
        severity = "MEDIUM"
    else:
        severity = "INFO"

    summary = (
        f"Stego Signal Probe reviewed {len(result.image_assets)} public image asset(s) and "
        f"flagged {len(flagged)} asset(s) with heuristic stego indicators."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"images={len(result.image_assets)}",
            f"flagged={len(flagged)}",
            f"highest_score={highest:.2f}",
        ],
        "data": {
            "target": result.target,
            "flagged_assets": [item.as_dict() for item in flagged],
            "image_assets": [item.as_dict() for item in result.image_assets],
            "notes": list(result.notes),
        },
    }
