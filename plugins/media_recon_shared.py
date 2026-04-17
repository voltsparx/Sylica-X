"""Shared helpers for media reconnaissance plugins."""

from __future__ import annotations

from typing import Any

from core.collect.media_recon import MediaReconResult, collect_profile_media_recon_blocking


def _rows_from_context(context: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in (context.get("results", []) or []) if isinstance(row, dict)]


def resolve_media_recon_payload(context: dict[str, Any]) -> MediaReconResult:
    """Reuse chained media-recon data when available, otherwise collect it."""

    previous = context.get("previous_plugin_data")
    if isinstance(previous, dict):
        payload = previous.get("media_recon_engine")
        if isinstance(payload, dict) and payload.get("targets") and payload.get("text_signals"):
            return media_recon_result_from_dict(payload)
    result_payloads = [row for row in (context.get("plugins", []) or []) if isinstance(row, dict)]
    for plugin_payload in result_payloads:
        if str(plugin_payload.get("id") or "").strip().lower() != "media_recon_engine":
            continue
        data = plugin_payload.get("data")
        if not isinstance(data, dict):
            continue
        return media_recon_result_from_dict(data)

    return collect_profile_media_recon_blocking(
        _rows_from_context(context),
        target=str(context.get("target") or ""),
        timeout_seconds=int(context.get("timeout", 12) or 12),
        proxy_url=str(context.get("proxy_url") or "").strip() or None,
    )


def media_recon_result_from_dict(payload: dict[str, Any]) -> MediaReconResult:
    """Rehydrate a media recon result from plugin-chain JSON-safe data."""

    from core.collect.media_recon import (
        MediaFrameObservation,
        MediaReconAsset,
        MediaReconCoverage,
        MediaReconFusionSummary,
        MediaReconTargets,
        TextFragment,
        TextSignalSummary,
        VideoEndpointObservation,
    )

    targets_raw = payload.get("targets") if isinstance(payload.get("targets"), dict) else {}
    text_signals_raw = payload.get("text_signals") if isinstance(payload.get("text_signals"), dict) else {}

    targets = MediaReconTargets(
        image_urls=tuple(str(item) for item in (targets_raw.get("image_urls") or []) if str(item).strip()),
        thumbnail_urls=tuple(str(item) for item in (targets_raw.get("thumbnail_urls") or []) if str(item).strip()),
        video_urls=tuple(str(item) for item in (targets_raw.get("video_urls") or []) if str(item).strip()),
        text_fragments=tuple(
            TextFragment(
                source=str(item.get("source") or ""),
                field=str(item.get("field") or ""),
                text=str(item.get("text") or ""),
            )
            for item in (targets_raw.get("text_fragments") or [])
            if isinstance(item, dict)
        ),
    )
    text_signals = TextSignalSummary(
        fragment_count=int(text_signals_raw.get("fragment_count") or 0),
        emails=tuple(str(item) for item in (text_signals_raw.get("emails") or []) if str(item).strip()),
        urls=tuple(str(item) for item in (text_signals_raw.get("urls") or []) if str(item).strip()),
        phones=tuple(str(item) for item in (text_signals_raw.get("phones") or []) if str(item).strip()),
        mentions=tuple(str(item) for item in (text_signals_raw.get("mentions") or []) if str(item).strip()),
        hashtags=tuple(str(item) for item in (text_signals_raw.get("hashtags") or []) if str(item).strip()),
        names=tuple(str(item) for item in (text_signals_raw.get("names") or []) if str(item).strip()),
        keywords=tuple(str(item) for item in (text_signals_raw.get("keywords") or []) if str(item).strip()),
        target_hit_count=int(text_signals_raw.get("target_hit_count") or 0),
    )
    image_assets = tuple(
        MediaReconAsset(
            url=str(item.get("url") or ""),
            asset_kind=str(item.get("asset_kind") or "image"),
            content_type=str(item.get("content_type") or ""),
            size_bytes=int(item.get("size_bytes") or 0),
            sha256=str(item.get("sha256") or ""),
            width=int(item["width"]) if item.get("width") is not None else None,
            height=int(item["height"]) if item.get("height") is not None else None,
            metadata=dict(item.get("metadata") or {}),
            ocr_text=str(item.get("ocr_text") or ""),
            ocr_engine=str(item.get("ocr_engine") or "none"),
            extracted_signals={
                "emails": [str(value) for value in ((item.get("extracted_signals") or {}).get("emails") or [])],
                "urls": [str(value) for value in ((item.get("extracted_signals") or {}).get("urls") or [])],
            },
            entropy_score=float(item.get("entropy_score") or 0.0),
            stego_score=float(item.get("stego_score") or 0.0),
            stego_flags=tuple(str(value) for value in (item.get("stego_flags") or []) if str(value).strip()),
        )
        for item in (payload.get("image_assets") or [])
        if isinstance(item, dict)
    )
    video_assets = tuple(
        VideoEndpointObservation(
            url=str(item.get("url") or ""),
            content_type=str(item.get("content_type") or ""),
            status_code=int(item.get("status_code") or 0),
            size_bytes=int(item.get("size_bytes") or 0),
            final_url=str(item.get("final_url") or ""),
            thumbnail_url=str(item.get("thumbnail_url") or "") or None,
            extracted_signals={
                "emails": [str(value) for value in ((item.get("extracted_signals") or {}).get("emails") or [])],
                "urls": [str(value) for value in ((item.get("extracted_signals") or {}).get("urls") or [])],
            },
            notes=tuple(str(value) for value in (item.get("notes") or []) if str(value).strip()),
        )
        for item in (payload.get("video_assets") or [])
        if isinstance(item, dict)
    )
    frame_observations = tuple(
        MediaFrameObservation(
            source_url=str(item.get("source_url") or ""),
            origin_kind=str(item.get("origin_kind") or "image_preview"),
            frame_label=str(item.get("frame_label") or ""),
            width=int(item["width"]) if item.get("width") is not None else None,
            height=int(item["height"]) if item.get("height") is not None else None,
            brightness_mean=float(item.get("brightness_mean") or 0.0),
            contrast_score=float(item.get("contrast_score") or 0.0),
            ocr_excerpt=str(item.get("ocr_excerpt") or ""),
            tags=tuple(str(value) for value in (item.get("tags") or []) if str(value).strip()),
        )
        for item in (payload.get("frame_observations") or [])
        if isinstance(item, dict)
    )
    coverage_raw = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    fusion_raw = payload.get("fusion_summary") if isinstance(payload.get("fusion_summary"), dict) else {}
    coverage = (
        MediaReconCoverage(
            image_targets=int(coverage_raw.get("image_targets") or 0),
            image_assets=int(coverage_raw.get("image_assets") or 0),
            video_targets=int(coverage_raw.get("video_targets") or 0),
            video_assets=int(coverage_raw.get("video_assets") or 0),
            frame_observations=int(coverage_raw.get("frame_observations") or 0),
            text_fragments=int(coverage_raw.get("text_fragments") or 0),
            text_indicators=int(coverage_raw.get("text_indicators") or 0),
            ocr_hits=int(coverage_raw.get("ocr_hits") or 0),
            stego_hits=int(coverage_raw.get("stego_hits") or 0),
            host_count=int(coverage_raw.get("host_count") or 0),
        )
        if coverage_raw
        else None
    )
    fusion_summary = (
        MediaReconFusionSummary(
            host_distribution={str(key): int(value) for key, value in (fusion_raw.get("host_distribution") or {}).items()},
            signal_totals={str(key): int(value) for key, value in (fusion_raw.get("signal_totals") or {}).items()},
            extracted_identities=tuple(str(item) for item in (fusion_raw.get("extracted_identities") or []) if str(item).strip()),
            notable_patterns=tuple(str(item) for item in (fusion_raw.get("notable_patterns") or []) if str(item).strip()),
        )
        if fusion_raw
        else None
    )
    return MediaReconResult(
        target=str(payload.get("target") or ""),
        targets=targets,
        text_signals=text_signals,
        image_assets=image_assets,
        video_assets=video_assets,
        frame_observations=frame_observations,
        coverage=coverage,
        fusion_summary=fusion_summary,
        engine_health=dict(payload.get("engine_health") or {}),
        engine_results=tuple(
            {
                "name": str(item.get("name") or ""),
                "status": str(item.get("status") or ""),
                "error": item.get("error"),
                "execution_time": float(item.get("execution_time") or 0.0),
            }
            for item in (payload.get("engine_results") or [])
            if isinstance(item, dict)
        ),
        notes=tuple(str(item) for item in (payload.get("notes") or []) if str(item).strip()),
    )
