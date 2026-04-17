"""Plugin: public image/video/post-text reconnaissance engine."""

from __future__ import annotations

from plugins.media_recon_shared import resolve_media_recon_payload


PLUGIN_SPEC = {
    "id": "media_recon_engine",
    "title": "Media Recon Engine",
    "description": "Runs public image, thumbnail, video-endpoint, and post-text reconnaissance for profile intelligence.",
    "scopes": ["profile", "fusion"],
    "aliases": ["media_recon", "image_recon", "video_recon"],
    "version": "1.0",
}


def run(context: dict) -> dict:
    result = resolve_media_recon_payload(context)
    image_count = len(result.image_assets)
    video_count = len(result.video_assets)
    frame_count = len(result.frame_observations)
    stego_hits = sum(1 for item in result.image_assets if item.stego_flags)
    ocr_hits = sum(1 for item in result.image_assets if item.ocr_text.strip())
    text_fragments = result.text_signals.fragment_count

    if stego_hits:
        severity = "HIGH"
    elif image_count or video_count or text_fragments:
        severity = "MEDIUM"
    else:
        severity = "INFO"

    summary = (
        f"Media Recon Engine analyzed {image_count} public image asset(s), "
        f"{video_count} video endpoint(s), {frame_count} visual frame sample(s), and {text_fragments} text fragment(s); "
        f"OCR hit {ocr_hits} asset(s) and stego heuristics flagged {stego_hits} image(s)."
    )
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"images={image_count}",
            f"videos={video_count}",
            f"frames={frame_count}",
            f"text_fragments={text_fragments}",
            f"ocr_hits={ocr_hits}",
            f"stego_hits={stego_hits}",
        ],
        "data": result.as_dict(),
    }
