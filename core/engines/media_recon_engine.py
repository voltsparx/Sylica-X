"""Dedicated media reconnaissance engine for staged public-media analysis."""

from __future__ import annotations

import asyncio
from collections import Counter
import io
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import urlparse

import aiohttp

from core.engine_manager import AsyncEngine
from core.engines.engine_base import EngineBase
from core.engines.engine_result import EngineResult
from core.collect.media_intel import _run_ocr
from core.collect.media_recon import (
    MediaFrameObservation,
    MediaReconCoverage,
    MediaReconFusionSummary,
    MediaReconResult,
    VideoEndpointObservation,
    _fetch_image_asset,
    _fetch_video_endpoint,
    _thumbnail_map,
    extract_media_targets,
    summarize_text_signals,
)


def _serialize_engine_result(item: EngineResult) -> dict[str, Any]:
    return {
        "name": item.name,
        "status": item.status,
        "error": item.error,
        "execution_time": round(float(item.execution_time), 4),
    }


def _host_from_url(value: str) -> str:
    try:
        parsed = urlparse(str(value or "").strip())
    except Exception:
        return ""
    return str(parsed.netloc or "").strip().lower()


def _dedupe_urls(values: list[str], *, limit: int) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(token)
        if len(ordered) >= limit:
            break
    return ordered


def _safe_excerpt(value: str, *, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def _frame_tags(*, width: int | None, height: int | None, brightness: float, contrast: float, ocr_excerpt: str) -> tuple[str, ...]:
    tags: list[str] = []
    if width and height and width > 0 and height > 0:
        if width > height:
            tags.append("landscape")
        elif height > width:
            tags.append("portrait")
        else:
            tags.append("square")
    if brightness < 70:
        tags.append("low_light")
    elif brightness > 180:
        tags.append("bright_scene")
    if contrast < 35:
        tags.append("low_contrast")
    elif contrast > 80:
        tags.append("high_contrast")
    if ocr_excerpt:
        tags.append("ocr_present")
    return tuple(tags)


def _build_frame_observation(
    image_handle: Any,
    *,
    source_url: str,
    origin_kind: str,
    frame_label: str,
) -> MediaFrameObservation:
    from PIL import ImageStat

    working = image_handle.convert("RGB")
    grayscale = working.convert("L")
    stat = ImageStat.Stat(grayscale)
    brightness = float(stat.mean[0]) if stat.mean else 0.0
    contrast = float(stat.stddev[0]) if stat.stddev else 0.0

    buffer = io.BytesIO()
    working.save(buffer, format="PNG")
    ocr_text, _ = _run_ocr(buffer.getvalue())
    excerpt = _safe_excerpt(ocr_text)
    return MediaFrameObservation(
        source_url=source_url,
        origin_kind=origin_kind,
        frame_label=frame_label,
        width=getattr(working, "width", None),
        height=getattr(working, "height", None),
        brightness_mean=round(brightness, 2),
        contrast_score=round(contrast, 2),
        ocr_excerpt=excerpt,
        tags=_frame_tags(
            width=getattr(working, "width", None),
            height=getattr(working, "height", None),
            brightness=brightness,
            contrast=contrast,
            ocr_excerpt=excerpt,
        ),
    )


async def _fetch_frame_source(
    session: aiohttp.ClientSession,
    media_url: str,
    *,
    origin_kind: str,
    timeout_seconds: int,
    proxy_url: str | None,
) -> MediaFrameObservation | None:
    try:
        from PIL import Image, ImageSequence
    except Exception:
        return None

    request_kwargs: dict[str, Any] = {
        "timeout": aiohttp.ClientTimeout(total=max(1, int(timeout_seconds))),
        "allow_redirects": True,
    }
    if proxy_url:
        request_kwargs["proxy"] = proxy_url

    async with session.get(media_url, **request_kwargs) as response:
        if response.status >= 400:
            return None
        media_bytes = await response.read()
        if not media_bytes:
            return None

    with Image.open(io.BytesIO(media_bytes)) as image_handle:
        label = "animated-preview" if getattr(image_handle, "is_animated", False) else "preview"
        if getattr(image_handle, "is_animated", False):
            first = next(iter(ImageSequence.Iterator(image_handle)))
            return _build_frame_observation(first, source_url=media_url, origin_kind=origin_kind, frame_label=label)
        return _build_frame_observation(image_handle, source_url=media_url, origin_kind=origin_kind, frame_label=label)


def _sample_video_frames(video_bytes: bytes, *, source_url: str, max_frames: int = 3) -> tuple[list[MediaFrameObservation], str | None]:
    try:
        import cv2
    except Exception:
        return [], "opencv_unavailable"

    suffix = Path(urlparse(source_url).path).suffix or ".mp4"
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(video_bytes)
            temp_path = handle.name

        capture = cv2.VideoCapture(temp_path)
        if not capture.isOpened():
            return [], "video_open_failed"
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            capture.release()
            return [], "video_frame_count_unavailable"

        sample_points = sorted({0, total_frames // 2, max(total_frames - 1, 0)})[: max(1, int(max_frames))]
        observations: list[MediaFrameObservation] = []
        try:
            from PIL import Image
        except Exception:
            capture.release()
            return [], "pillow_unavailable"

        for index, frame_id in enumerate(sample_points, start=1):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ok, frame = capture.read()
            if not ok:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_handle = Image.fromarray(rgb)
            observations.append(
                _build_frame_observation(
                    image_handle,
                    source_url=source_url,
                    origin_kind="video_frame",
                    frame_label=f"frame-{index}",
                )
            )
        capture.release()
        if not observations:
            return [], "video_frame_decode_failed"
        return observations, None
    except Exception as exc:
        return [], str(exc)
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


async def _fetch_video_frames(
    session: aiohttp.ClientSession,
    observation: VideoEndpointObservation,
    *,
    timeout_seconds: int,
    proxy_url: str | None,
    max_download_bytes: int,
) -> tuple[list[MediaFrameObservation], str | None]:
    request_kwargs: dict[str, Any] = {
        "timeout": aiohttp.ClientTimeout(total=max(1, int(timeout_seconds))),
        "allow_redirects": True,
    }
    if proxy_url:
        request_kwargs["proxy"] = proxy_url

    if observation.size_bytes and observation.size_bytes > max_download_bytes:
        return [], "video_too_large_for_frame_sampling"

    async with session.get(observation.url, **request_kwargs) as response:
        if response.status >= 400:
            return [], f"video_fetch_failed:{response.status}"
        payload = await response.content.read(max_download_bytes + 1)
        if len(payload) > max_download_bytes:
            return [], "video_payload_exceeded_limit"
    return _sample_video_frames(payload, source_url=observation.url)


class MediaReconEngine(EngineBase):
    """Stage-aware media reconnaissance engine with optional visual sampling."""

    def __init__(self) -> None:
        super().__init__()
        self._async_engine = AsyncEngine(monitor=self._monitor)

    async def run(self, tasks: Any, context: dict[str, Any] | None = None) -> list[Any]:
        return await self._async_engine.run(tasks, context=context)

    async def run_detailed(self, tasks: Any, context: dict[str, Any] | None = None) -> list[EngineResult]:
        return await self._async_engine.run_detailed(tasks, context=context)

    async def run_media_recon(
        self,
        profile_results: list[dict[str, Any]],
        *,
        target: str,
        timeout_seconds: int = 12,
        proxy_url: str | None = None,
        max_frame_sources: int = 6,
        max_video_frame_download_bytes: int = 12_000_000,
    ) -> MediaReconResult:
        targets = extract_media_targets(profile_results, target=target)
        text_signals = summarize_text_signals(target, targets.text_fragments)
        notes: list[str] = []
        engine_results: list[dict[str, Any]] = []

        if not targets.image_urls and not targets.thumbnail_urls and not targets.video_urls and not targets.text_fragments:
            empty_coverage = MediaReconCoverage(
                image_targets=0,
                image_assets=0,
                video_targets=0,
                video_assets=0,
                frame_observations=0,
                text_fragments=0,
                text_indicators=0,
                ocr_hits=0,
                stego_hits=0,
                host_count=0,
            )
            empty_fusion = MediaReconFusionSummary(
                host_distribution={},
                signal_totals={},
                extracted_identities=(),
                notable_patterns=("no_media_targets",),
            )
            return MediaReconResult(
                target=str(target),
                targets=targets,
                text_signals=text_signals,
                image_assets=(),
                video_assets=(),
                notes=("No public media or post-text targets were available for media reconnaissance.",),
                frame_observations=(),
                coverage=empty_coverage,
                fusion_summary=empty_fusion,
                engine_health=self.health_check(),
                engine_results=(),
            )

        connector = aiohttp.TCPConnector(limit=6, ttl_dns_cache=300)
        image_assets = []
        video_assets = []
        frame_observations: list[MediaFrameObservation] = []
        thumbnail_lookup = _thumbnail_map(targets)

        asset_kinds: dict[str, str] = {}
        for value in targets.image_urls:
            asset_kinds.setdefault(value, "image")
        for value in targets.thumbnail_urls:
            asset_kinds.setdefault(value, "video_thumbnail")

        runtime = {"max_workers": 6, "timeout": timeout_seconds}

        async with aiohttp.ClientSession(connector=connector) as session:
            image_task_factories = []
            for media_url, asset_kind in list(asset_kinds.items())[:12]:
                async def _task(media_url: str = media_url, asset_kind: str = asset_kind) -> Any:
                    return await _fetch_image_asset(
                        session,
                        media_url,
                        asset_kind=asset_kind,
                        timeout_seconds=timeout_seconds,
                        proxy_url=proxy_url,
                    )

                setattr(_task, "_silica_x_task_name", f"media-image:{asset_kind}:{media_url}")
                image_task_factories.append(_task)

            image_batch = await self._async_engine.run_detailed(image_task_factories, runtime)
            engine_results.extend(_serialize_engine_result(item) for item in image_batch)
            for item in image_batch:
                if item.status != "success":
                    if item.error:
                        notes.append(f"Image stage issue [{item.name}]: {item.error}")
                    continue
                payload = item.data.get("payload")
                if payload is not None:
                    image_assets.append(payload)

            video_task_factories = []
            for media_url in targets.video_urls[:8]:
                async def _video_task(media_url: str = media_url) -> Any:
                    return await _fetch_video_endpoint(
                        session,
                        media_url,
                        thumbnail_url=thumbnail_lookup.get(media_url),
                        timeout_seconds=timeout_seconds,
                        proxy_url=proxy_url,
                    )

                setattr(_video_task, "_silica_x_task_name", f"media-video:{media_url}")
                video_task_factories.append(_video_task)

            video_batch = await self._async_engine.run_detailed(video_task_factories, runtime)
            engine_results.extend(_serialize_engine_result(item) for item in video_batch)
            for item in video_batch:
                if item.status != "success":
                    if item.error:
                        notes.append(f"Video stage issue [{item.name}]: {item.error}")
                    continue
                payload = item.data.get("payload")
                if payload is not None:
                    video_assets.append(payload)

            frame_sources = _dedupe_urls(
                [*targets.thumbnail_urls, *[asset.url for asset in image_assets]],
                limit=max_frame_sources,
            )
            frame_task_factories = []
            for media_url in frame_sources:
                origin_kind = "video_thumbnail" if media_url in {item.thumbnail_url for item in video_assets if item.thumbnail_url} else "image_preview"

                async def _frame_task(media_url: str = media_url, origin_kind: str = origin_kind) -> Any:
                    return await _fetch_frame_source(
                        session,
                        media_url,
                        origin_kind=origin_kind,
                        timeout_seconds=timeout_seconds,
                        proxy_url=proxy_url,
                    )

                setattr(_frame_task, "_silica_x_task_name", f"media-frame:{origin_kind}:{media_url}")
                frame_task_factories.append(_frame_task)

            frame_batch = await self._async_engine.run_detailed(frame_task_factories, runtime)
            engine_results.extend(_serialize_engine_result(item) for item in frame_batch)
            for item in frame_batch:
                if item.status != "success":
                    continue
                payload = item.data.get("payload")
                if payload is not None:
                    frame_observations.append(payload)

            video_frame_targets = [item for item in video_assets if item.thumbnail_url is None][:2]
            for observation in video_frame_targets:
                frames, error = await _fetch_video_frames(
                    session,
                    observation,
                    timeout_seconds=timeout_seconds,
                    proxy_url=proxy_url,
                    max_download_bytes=max_video_frame_download_bytes,
                )
                if frames:
                    frame_observations.extend(frames)
                    engine_results.append(
                        {
                            "name": f"media-video-frames:{observation.url}",
                            "status": "success",
                            "error": None,
                            "execution_time": 0.0,
                        }
                    )
                elif error:
                    notes.append(f"Video frame extraction skipped for {observation.url}: {error}")
                    engine_results.append(
                        {
                            "name": f"media-video-frames:{observation.url}",
                            "status": "failed",
                            "error": error,
                            "execution_time": 0.0,
                        }
                    )

        image_assets = [item for item in image_assets if item is not None]
        video_assets = [item for item in video_assets if item is not None]

        ocr_hits = sum(1 for item in image_assets if item.ocr_text.strip())
        stego_hits = sum(1 for item in image_assets if item.stego_flags)
        text_indicators = (
            len(text_signals.emails)
            + len(text_signals.urls)
            + len(text_signals.phones)
            + len(text_signals.mentions)
            + len(text_signals.hashtags)
        )

        host_distribution: Counter[str] = Counter()
        for media_url in [*targets.image_urls, *targets.thumbnail_urls, *targets.video_urls]:
            host = _host_from_url(media_url)
            if host:
                host_distribution[host] += 1

        ocr_emails = {value for item in image_assets for value in item.extracted_signals.get("emails", [])}
        ocr_urls = {value for item in image_assets for value in item.extracted_signals.get("urls", [])}
        frame_text_hits = sum(1 for item in frame_observations if item.ocr_excerpt)
        overlap_flags: list[str] = []
        if stego_hits:
            overlap_flags.append("stego_suspicion_detected")
        if ocr_hits and text_signals.fragment_count:
            overlap_flags.append("ocr_and_post_text_present")
        if set(text_signals.emails) & ocr_emails:
            overlap_flags.append("cross_media_email_overlap")
        if frame_observations:
            overlap_flags.append("visual_frame_sampling_completed")
        if len(host_distribution) >= 3:
            overlap_flags.append("multi_host_media_spread")
        if video_assets:
            overlap_flags.append("video_lane_active")

        coverage = MediaReconCoverage(
            image_targets=len(targets.image_urls) + len(targets.thumbnail_urls),
            image_assets=len(image_assets),
            video_targets=len(targets.video_urls),
            video_assets=len(video_assets),
            frame_observations=len(frame_observations),
            text_fragments=text_signals.fragment_count,
            text_indicators=text_indicators,
            ocr_hits=ocr_hits + frame_text_hits,
            stego_hits=stego_hits,
            host_count=len(host_distribution),
        )
        fusion_summary = MediaReconFusionSummary(
            host_distribution=dict(host_distribution),
            signal_totals={
                "text_emails": len(text_signals.emails),
                "text_urls": len(text_signals.urls),
                "text_phones": len(text_signals.phones),
                "text_mentions": len(text_signals.mentions),
                "ocr_emails": len(ocr_emails),
                "ocr_urls": len(ocr_urls),
                "frame_text_hits": frame_text_hits,
            },
            extracted_identities=tuple(
                _dedupe_urls(
                    [
                        *text_signals.names,
                        *text_signals.mentions,
                        *text_signals.emails,
                    ],
                    limit=16,
                )
            ),
            notable_patterns=tuple(overlap_flags),
        )

        if image_assets:
            notes.append("Image lane collected public metadata, OCR, visual-frame profiling, and stego-suspicion heuristics.")
        if video_assets:
            notes.append("Video lane validated public endpoints and sampled thumbnails or small downloadable videos when possible.")
        if targets.text_fragments:
            notes.append("Post-text lane extracted structured OSINT cues from public profile and post-like text fields.")

        return MediaReconResult(
            target=str(target),
            targets=targets,
            text_signals=text_signals,
            image_assets=tuple(image_assets),
            video_assets=tuple(video_assets),
            notes=tuple(notes),
            frame_observations=tuple(frame_observations),
            coverage=coverage,
            fusion_summary=fusion_summary,
            engine_health=self.health_check(),
            engine_results=tuple(engine_results),
        )


def collect_media_recon_engine_blocking(
    profile_results: list[dict[str, Any]],
    *,
    target: str,
    timeout_seconds: int = 12,
    proxy_url: str | None = None,
) -> MediaReconResult:
    """Blocking wrapper for the dedicated media reconnaissance engine."""

    return asyncio.run(
        MediaReconEngine().run_media_recon(
            profile_results,
            target=target,
            timeout_seconds=timeout_seconds,
            proxy_url=proxy_url,
        )
    )
