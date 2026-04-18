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
# ──────────────────────────────────────────────────────────────

"""Media and public-post intelligence helpers."""

from __future__ import annotations

import aiohttp
import asyncio
import hashlib
import io
from typing import Any


_ENGLISH_STOPWORDS = {
    "the",
    "a",
    "is",
    "in",
    "on",
    "of",
    "to",
    "and",
    "for",
    "it",
    "this",
    "that",
    "with",
    "you",
    "are",
    "was",
    "be",
    "have",
    "at",
    "but",
}


def _dedupe(values: list[str]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _empty_post_intel(source_label: str = "unknown") -> dict[str, Any]:
    return {
        "source_label": source_label,
        "post_count": 0,
        "total_words": 0,
        "avg_words_per_post": 0.0,
        "all_emails": [],
        "all_urls": [],
        "all_phones": [],
        "all_mentions": [],
        "all_hashtags": [],
        "all_ips": [],
        "signal_density": 0.0,
        "per_post": [],
    }


def _empty_image_intel(image_url_count: int = 0) -> dict[str, Any]:
    return {
        "image_url_count": image_url_count,
        "assets_fetched": 0,
        "assets_with_ocr_text": 0,
        "all_emails": [],
        "all_urls": [],
        "all_phones": [],
        "all_mentions": [],
        "assets": [],
    }


def _empty_video_intel() -> dict[str, Any]:
    return {
        "thumbnail_intelligence": _empty_image_intel(),
        "metadata_intelligence": _empty_post_intel("video_metadata"),
        "combined_emails": [],
        "combined_urls": [],
        "combined_mentions": [],
        "combined_hashtags": [],
        "video_count": 0,
    }


async def collect_post_text_intelligence(
    post_texts: list[str],
    source_label: str = "unknown",
) -> dict[str, Any]:
    """Extract intelligence signals from public post text."""

    from core.collect.ocr_pipeline import extract_ocr_signals

    if not post_texts:
        return _empty_post_intel(source_label)

    per_post: list[dict[str, Any]] = []
    all_emails: list[str] = []
    all_urls: list[str] = []
    all_phones: list[str] = []
    all_mentions: list[str] = []
    all_hashtags: list[str] = []
    all_ips: list[str] = []
    total_words = 0
    total_signals = 0

    for index, raw_text in enumerate(post_texts):
        text = str(raw_text or "")
        words = [token for token in text.split() if token]
        total_words += len(words)
        signals = extract_ocr_signals(text)
        lower_words = [token.lower().strip(".,!?;:()[]{}\"'") for token in words]
        english_matches = sum(1 for token in lower_words if token in _ENGLISH_STOPWORDS)
        _language_hint = "en" if words and (english_matches / max(1, len(words))) > 0.30 else "unknown"
        per_post.append({"index": index, "word_count": len(words), "signals": signals})
        all_emails.extend(signals.get("emails", []))
        all_urls.extend(signals.get("urls", []))
        all_phones.extend(signals.get("phones", []))
        all_mentions.extend(signals.get("mentions", []))
        all_hashtags.extend(signals.get("hashtags", []))
        all_ips.extend(signals.get("ips", []))
        total_signals += int(signals.get("signal_count", 0) or 0)

    post_count = len(post_texts)
    return {
        "source_label": source_label,
        "post_count": post_count,
        "total_words": total_words,
        "avg_words_per_post": float(total_words / post_count) if post_count else 0.0,
        "all_emails": _dedupe(all_emails),
        "all_urls": _dedupe(all_urls),
        "all_phones": _dedupe(all_phones),
        "all_mentions": _dedupe(all_mentions),
        "all_hashtags": _dedupe(all_hashtags),
        "all_ips": _dedupe(all_ips),
        "signal_density": float(total_signals / post_count) if post_count else 0.0,
        "per_post": per_post,
    }


async def collect_image_asset_intelligence(
    image_urls: list[str],
    session: aiohttp.ClientSession,
    run_ocr: bool = True,
    preprocess_intensity: str = "balanced",
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """Collect image-asset intelligence and optional OCR."""

    from core.collect.ocr_pipeline import run_ocr_pipeline

    if not image_urls:
        return _empty_image_intel(0)

    assets: list[dict[str, Any]] = []
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    all_emails: list[str] = []
    all_urls: list[str] = []
    all_phones: list[str] = []
    all_mentions: list[str] = []
    assets_with_ocr_text = 0
    assets_fetched = 0

    for image_url in image_urls[:25]:
        asset = {
            "url": image_url,
            "content_type": "",
            "width": 0,
            "height": 0,
            "size_bytes": 0,
            "sha256": "",
            "ocr_result": None,
            "fetch_error": None,
        }
        try:
            async with session.get(
                image_url,
                timeout=aiohttp.ClientTimeout(total=max(1, int(timeout_seconds))),
                allow_redirects=True,
            ) as response:
                content_type = str(response.headers.get("Content-Type", "") or "").split(";", 1)[0].strip().lower()
                if content_type not in allowed_types:
                    asset["fetch_error"] = "unsupported content type"
                    assets.append(asset)
                    continue
                payload = await response.content.read(5_000_001)
                if len(payload) > 5_000_000:
                    asset["fetch_error"] = "image exceeds 5MB limit"
                    assets.append(asset)
                    continue
                if not payload:
                    asset["fetch_error"] = "empty image payload"
                    assets.append(asset)
                    continue
        except Exception as exc:
            asset["fetch_error"] = str(exc)
            assets.append(asset)
            continue

        try:
            from PIL import Image

            with Image.open(io.BytesIO(payload)) as image_handle:
                width, height = image_handle.size
        except Exception:
            width, height = 0, 0

        assets_fetched += 1
        asset.update(
            {
                "content_type": content_type,
                "width": int(width),
                "height": int(height),
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
        if run_ocr:
            ocr_result = run_ocr_pipeline(
                payload,
                preprocess_intensity=preprocess_intensity,
            )
            asset["ocr_result"] = ocr_result
            if str(ocr_result.get("merged_text", "") or "").strip():
                assets_with_ocr_text += 1
            signals = ocr_result.get("signals", {}) if isinstance(ocr_result, dict) else {}
            all_emails.extend(signals.get("emails", []) or [])
            all_urls.extend(signals.get("urls", []) or [])
            all_phones.extend(signals.get("phones", []) or [])
            all_mentions.extend(signals.get("mentions", []) or [])
        assets.append(asset)

    return {
        "image_url_count": len(image_urls),
        "assets_fetched": assets_fetched,
        "assets_with_ocr_text": assets_with_ocr_text,
        "all_emails": _dedupe(all_emails),
        "all_urls": _dedupe(all_urls),
        "all_phones": _dedupe(all_phones),
        "all_mentions": _dedupe(all_mentions),
        "assets": assets,
    }


async def collect_video_frame_intelligence(
    video_thumbnail_urls: list[str],
    video_metadata_texts: list[str],
    session: aiohttp.ClientSession,
    run_ocr_on_thumbnails: bool = True,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """Collect thumbnail and metadata intelligence for videos and reels."""

    thumbnail_intelligence = await collect_image_asset_intelligence(
        video_thumbnail_urls,
        session,
        run_ocr=run_ocr_on_thumbnails,
        timeout_seconds=timeout_seconds,
    )
    metadata_intelligence = await collect_post_text_intelligence(
        video_metadata_texts,
        source_label="video_metadata",
    )

    image_hashtags: list[str] = []
    for asset in thumbnail_intelligence.get("assets", []) or []:
        if not isinstance(asset, dict):
            continue
        ocr_result = asset.get("ocr_result")
        if isinstance(ocr_result, dict):
            signals = ocr_result.get("signals", {}) if isinstance(ocr_result.get("signals"), dict) else {}
            image_hashtags.extend(signals.get("hashtags", []) or [])

    combined_emails = _dedupe(
        list(thumbnail_intelligence.get("all_emails", []) or [])
        + list(metadata_intelligence.get("all_emails", []) or [])
    )
    combined_urls = _dedupe(
        list(thumbnail_intelligence.get("all_urls", []) or [])
        + list(metadata_intelligence.get("all_urls", []) or [])
    )
    combined_mentions = _dedupe(
        list(thumbnail_intelligence.get("all_mentions", []) or [])
        + list(metadata_intelligence.get("all_mentions", []) or [])
    )
    combined_hashtags = _dedupe(
        image_hashtags + list(metadata_intelligence.get("all_hashtags", []) or [])
    )

    return {
        "thumbnail_intelligence": thumbnail_intelligence,
        "metadata_intelligence": metadata_intelligence,
        "combined_emails": combined_emails,
        "combined_urls": combined_urls,
        "combined_mentions": combined_mentions,
        "combined_hashtags": combined_hashtags,
        "video_count": max(len(video_thumbnail_urls), len(video_metadata_texts)),
    }


async def run_public_media_recon(
    target: str,
    image_urls: list[str] | None = None,
    video_thumbnail_urls: list[str] | None = None,
    post_texts: list[str] | None = None,
    video_metadata_texts: list[str] | None = None,
    run_ocr: bool = True,
    preprocess_intensity: str = "balanced",
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Run the public media intelligence workflow."""

    image_urls = image_urls or []
    video_thumbnail_urls = video_thumbnail_urls or []
    post_texts = post_texts or []
    video_metadata_texts = video_metadata_texts or []

    connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        image_task = (
            collect_image_asset_intelligence(
                image_urls,
                session,
                run_ocr=run_ocr,
                preprocess_intensity=preprocess_intensity,
                timeout_seconds=timeout_seconds,
            )
            if image_urls
            else asyncio.sleep(0, result=_empty_image_intel())
        )
        video_task = (
            collect_video_frame_intelligence(
                video_thumbnail_urls,
                video_metadata_texts,
                session,
                run_ocr_on_thumbnails=run_ocr,
                timeout_seconds=timeout_seconds,
            )
            if video_thumbnail_urls
            else asyncio.sleep(0, result=_empty_video_intel())
        )
        post_task = (
            collect_post_text_intelligence(post_texts)
            if post_texts
            else asyncio.sleep(0, result=_empty_post_intel())
        )
        image_intel, video_intel, post_text_intel = await asyncio.gather(image_task, video_task, post_task)

    master_signal_map = {
        "emails": _dedupe(
            list(image_intel.get("all_emails", []) or [])
            + list(video_intel.get("combined_emails", []) or [])
            + list(post_text_intel.get("all_emails", []) or [])
        ),
        "urls": _dedupe(
            list(image_intel.get("all_urls", []) or [])
            + list(video_intel.get("combined_urls", []) or [])
            + list(post_text_intel.get("all_urls", []) or [])
        ),
        "phones": _dedupe(
            list(image_intel.get("all_phones", []) or [])
            + list(post_text_intel.get("all_phones", []) or [])
        ),
        "mentions": _dedupe(
            list(image_intel.get("all_mentions", []) or [])
            + list(video_intel.get("combined_mentions", []) or [])
            + list(post_text_intel.get("all_mentions", []) or [])
        ),
        "hashtags": _dedupe(
            list(video_intel.get("combined_hashtags", []) or [])
            + list(post_text_intel.get("all_hashtags", []) or [])
        ),
        "ips": _dedupe(
            list(post_text_intel.get("all_ips", []) or [])
            + list((video_intel.get("metadata_intelligence") or {}).get("all_ips", []) or [])
        ),
    }

    return {
        "target": target,
        "image_intel": image_intel,
        "video_intel": video_intel,
        "post_text_intel": post_text_intel,
        "master_signal_map": master_signal_map,
        "total_images_processed": int(image_intel.get("assets_fetched", 0) or 0),
        "total_videos_processed": int(video_intel.get("video_count", 0) or 0),
        "total_posts_processed": int(post_text_intel.get("post_count", 0) or 0),
        "ocr_enabled": bool(run_ocr),
    }

