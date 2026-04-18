"""Public media, post-text, and stego-suspicion reconnaissance helpers."""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
import hashlib
import io
import math
import re
from typing import Any

import aiohttp

from core.collect.media_intel import _extract_ocr_signals, _run_ocr
from core.intelligence.entity_builder import extract_name_candidates


_IMAGE_FIELDS = (
    "avatar_url",
    "avatar_urls",
    "banner_url",
    "banner_urls",
    "image_url",
    "image_urls",
    "media_urls",
    "post_image_urls",
    "gallery_urls",
)
_THUMBNAIL_FIELDS = (
    "thumbnail_url",
    "thumbnail_urls",
    "video_thumbnail_url",
    "video_thumbnail_urls",
    "reel_thumbnail_urls",
    "preview_image_urls",
)
_VIDEO_FIELDS = (
    "video_url",
    "video_urls",
    "post_video_urls",
    "clip_urls",
    "reel_urls",
    "stream_urls",
)
_TEXT_FIELD_TOKENS = (
    "bio",
    "about",
    "description",
    "headline",
    "summary",
    "caption",
    "title",
    "text",
    "post",
    "comment",
    "article",
)
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
_VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi")
_URL_RE = re.compile(r"https?://[^\s<>'\"]+")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s().]{6,}\d)")
_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z][A-Za-z0-9_]{1,31})")
_MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_.]{2,32})")
_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "analyst",
    "been",
    "being",
    "build",
    "built",
    "cloud",
    "from",
    "have",
    "into",
    "just",
    "more",
    "most",
    "over",
    "platform",
    "profile",
    "public",
    "security",
    "still",
    "that",
    "their",
    "them",
    "they",
    "this",
    "with",
    "your",
}


@dataclass(frozen=True)
class TextFragment:
    """One normalized public text fragment harvested from profile rows."""

    source: str
    field: str
    text: str

    def as_dict(self) -> dict[str, str]:
        return {"source": self.source, "field": self.field, "text": self.text}


@dataclass(frozen=True)
class TextSignalSummary:
    """Structured intelligence extracted from public post/profile text."""

    fragment_count: int
    emails: tuple[str, ...]
    urls: tuple[str, ...]
    phones: tuple[str, ...]
    mentions: tuple[str, ...]
    hashtags: tuple[str, ...]
    names: tuple[str, ...]
    keywords: tuple[str, ...]
    target_hit_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "fragment_count": self.fragment_count,
            "emails": list(self.emails),
            "urls": list(self.urls),
            "phones": list(self.phones),
            "mentions": list(self.mentions),
            "hashtags": list(self.hashtags),
            "names": list(self.names),
            "keywords": list(self.keywords),
            "target_hit_count": self.target_hit_count,
        }


@dataclass(frozen=True)
class MediaReconAsset:
    """Observed intelligence for one public image-like asset."""

    url: str
    asset_kind: str
    content_type: str
    size_bytes: int
    sha256: str
    width: int | None
    height: int | None
    metadata: dict[str, Any]
    ocr_text: str
    ocr_engine: str
    extracted_signals: dict[str, list[str]]
    entropy_score: float
    stego_score: float
    stego_flags: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "asset_kind": self.asset_kind,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "width": self.width,
            "height": self.height,
            "metadata": dict(self.metadata),
            "ocr_text": self.ocr_text,
            "ocr_engine": self.ocr_engine,
            "extracted_signals": {
                "emails": list(self.extracted_signals.get("emails", [])),
                "urls": list(self.extracted_signals.get("urls", [])),
            },
            "entropy_score": self.entropy_score,
            "stego_score": self.stego_score,
            "stego_flags": list(self.stego_flags),
        }


@dataclass(frozen=True)
class VideoEndpointObservation:
    """Lightweight metadata observed for one public video endpoint."""

    url: str
    content_type: str
    status_code: int
    size_bytes: int
    final_url: str
    thumbnail_url: str | None
    extracted_signals: dict[str, list[str]]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "content_type": self.content_type,
            "status_code": self.status_code,
            "size_bytes": self.size_bytes,
            "final_url": self.final_url,
            "thumbnail_url": self.thumbnail_url,
            "extracted_signals": {
                "emails": list(self.extracted_signals.get("emails", [])),
                "urls": list(self.extracted_signals.get("urls", [])),
            },
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class MediaFrameObservation:
    """Visual/frame-level observation derived from a public image or video source."""

    source_url: str
    origin_kind: str
    frame_label: str
    width: int | None
    height: int | None
    brightness_mean: float
    contrast_score: float
    ocr_excerpt: str
    tags: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "origin_kind": self.origin_kind,
            "frame_label": self.frame_label,
            "width": self.width,
            "height": self.height,
            "brightness_mean": self.brightness_mean,
            "contrast_score": self.contrast_score,
            "ocr_excerpt": self.ocr_excerpt,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class MediaReconCoverage:
    """Coverage counters describing what the media engine actually processed."""

    image_targets: int
    image_assets: int
    video_targets: int
    video_assets: int
    frame_observations: int
    text_fragments: int
    text_indicators: int
    ocr_hits: int
    stego_hits: int
    host_count: int

    def as_dict(self) -> dict[str, int]:
        return {
            "image_targets": self.image_targets,
            "image_assets": self.image_assets,
            "video_targets": self.video_targets,
            "video_assets": self.video_assets,
            "frame_observations": self.frame_observations,
            "text_fragments": self.text_fragments,
            "text_indicators": self.text_indicators,
            "ocr_hits": self.ocr_hits,
            "stego_hits": self.stego_hits,
            "host_count": self.host_count,
        }


@dataclass(frozen=True)
class MediaReconFusionSummary:
    """Cross-media rollup across OCR, text, frames, and hosts."""

    host_distribution: dict[str, int]
    signal_totals: dict[str, int]
    extracted_identities: tuple[str, ...]
    notable_patterns: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "host_distribution": dict(self.host_distribution),
            "signal_totals": dict(self.signal_totals),
            "extracted_identities": list(self.extracted_identities),
            "notable_patterns": list(self.notable_patterns),
        }


@dataclass(frozen=True)
class MediaReconTargets:
    """Deduplicated public media/text targets harvested from profile rows."""

    image_urls: tuple[str, ...]
    thumbnail_urls: tuple[str, ...]
    video_urls: tuple[str, ...]
    text_fragments: tuple[TextFragment, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "image_urls": list(self.image_urls),
            "thumbnail_urls": list(self.thumbnail_urls),
            "video_urls": list(self.video_urls),
            "text_fragments": [fragment.as_dict() for fragment in self.text_fragments],
        }


@dataclass(frozen=True)
class MediaReconResult:
    """Combined public media/text reconnaissance result."""

    target: str
    targets: MediaReconTargets
    text_signals: TextSignalSummary
    image_assets: tuple[MediaReconAsset, ...]
    video_assets: tuple[VideoEndpointObservation, ...]
    notes: tuple[str, ...]
    frame_observations: tuple[MediaFrameObservation, ...] = ()
    coverage: MediaReconCoverage | None = None
    fusion_summary: MediaReconFusionSummary | None = None
    engine_health: dict[str, Any] | None = None
    engine_results: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "targets": self.targets.as_dict(),
            "text_signals": self.text_signals.as_dict(),
            "image_assets": [asset.as_dict() for asset in self.image_assets],
            "video_assets": [asset.as_dict() for asset in self.video_assets],
            "frame_observations": [item.as_dict() for item in self.frame_observations],
            "coverage": self.coverage.as_dict() if self.coverage is not None else {},
            "fusion_summary": self.fusion_summary.as_dict() if self.fusion_summary is not None else {},
            "engine_health": dict(self.engine_health or {}),
            "engine_results": [dict(item) for item in self.engine_results],
            "notes": list(self.notes),
        }


def _clean_text(value: Any, *, limit: int = 500) -> str:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        return ""
    return normalized[:limit]


def _append_unique_text(values: list[str], raw: str, *, limit: int = 16) -> None:
    normalized = _clean_text(raw)
    if not normalized:
        return
    lowered = normalized.casefold()
    if lowered in {item.casefold() for item in values}:
        return
    values.append(normalized)
    if len(values) > limit:
        del values[limit:]


def _append_unique_url(values: list[str], raw: str, *, limit: int = 16) -> None:
    candidate = str(raw or "").strip()
    if not candidate.startswith(("http://", "https://")):
        return
    lowered = candidate.lower()
    if lowered in {item.lower() for item in values}:
        return
    values.append(candidate)
    if len(values) > limit:
        del values[limit:]


def _looks_like_image_url(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return lowered.endswith(_IMAGE_SUFFIXES) or any(token in lowered for token in ("/image", "/images/", "avatar", "banner"))


def _looks_like_video_url(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    if lowered.endswith(_IMAGE_SUFFIXES):
        return False
    return lowered.endswith(_VIDEO_SUFFIXES) or any(token in lowered for token in ("/video", "/videos/", "/reel", "/clip", "watch?v="))


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D+", "", str(raw))
    if len(digits) < 7:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


def _top_keywords(texts: list[str], *, target: str, limit: int = 8) -> tuple[str, ...]:
    target_tokens = {token.casefold() for token in re.findall(r"[A-Za-z0-9_]{3,}", str(target or ""))}
    counter: Counter[str] = Counter()
    for text in texts:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,24}", text.lower()):
            if token in _STOPWORDS or token in target_tokens:
                continue
            counter[token] += 1
    ranked = [token for token, count in counter.most_common() if count >= 1]
    return tuple(ranked[:limit])


def _estimate_entropy(payload: bytes) -> float:
    if not payload:
        return 0.0
    total = len(payload)
    counts = Counter(payload)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _extract_image_details(media_bytes: bytes) -> tuple[int | None, int | None, dict[str, Any]]:
    try:
        from PIL import ExifTags, Image
    except Exception:
        return None, None, {"metadata_status": "pillow_unavailable"}

    try:
        with Image.open(io.BytesIO(media_bytes)) as image_handle:
            width, height = image_handle.size
            metadata: dict[str, Any] = {
                "format": str(getattr(image_handle, "format", "") or ""),
                "mode": str(getattr(image_handle, "mode", "") or ""),
                "info_keys": sorted(str(key) for key in getattr(image_handle, "info", {}).keys()),
            }
            exif: Any = getattr(image_handle, "getexif", lambda: {})()
            if exif:
                exif_items: dict[str, str] = {}
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    exif_items[str(tag_name)] = _clean_text(value, limit=120)
                metadata["exif"] = exif_items
            return width, height, metadata
    except Exception as exc:
        return None, None, {"metadata_status": f"unavailable: {exc}"}


def _score_stego_suspicion(
    *,
    media_bytes: bytes,
    width: int | None,
    height: int | None,
    metadata: dict[str, Any],
    content_type: str,
) -> tuple[float, tuple[str, ...], float]:
    entropy = round(_estimate_entropy(media_bytes), 4)
    flags: list[str] = []
    boost = 0.0

    if entropy >= 7.85:
        flags.append("high_entropy_payload")
        boost += 0.24

    if width and height and width > 0 and height > 0:
        pixels = max(1, width * height)
        bytes_per_pixel = len(media_bytes) / pixels
        aspect_ratio = max(width / height, height / width)
        if bytes_per_pixel >= 4.25:
            flags.append("dense_byte_distribution")
            boost += 0.22
        if aspect_ratio >= 4.0:
            flags.append("extreme_aspect_ratio")
            boost += 0.12

    info_keys = metadata.get("info_keys", [])
    if isinstance(info_keys, list) and len(info_keys) >= 4:
        flags.append("rich_embedded_metadata")
        boost += 0.14

    exif_items = metadata.get("exif", {})
    if isinstance(exif_items, dict) and len(exif_items) >= 10:
        flags.append("heavy_exif_footprint")
        boost += 0.12

    lowered_type = str(content_type or "").lower()
    if "png" in lowered_type and entropy >= 7.6:
        flags.append("png_container_entropy")
        boost += 0.14

    score = min(1.0, round(0.08 + boost, 4))
    return score, tuple(flags), entropy


def _iter_nested_values(node: Any, *, path: str = "", depth: int = 0) -> list[tuple[str, Any]]:
    if depth > 2:
        return []
    items: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            child_path = f"{path}.{key}" if path else str(key)
            items.extend(_iter_nested_values(value, path=child_path, depth=depth + 1))
        return items
    if isinstance(node, list):
        for index, value in enumerate(node[:8]):
            child_path = f"{path}[{index}]"
            items.extend(_iter_nested_values(value, path=child_path, depth=depth + 1))
        return items
    return [(path, node)]


def extract_media_targets(profile_results: list[dict[str, Any]], *, target: str) -> MediaReconTargets:
    """Harvest image/video URLs and public post-like text from profile rows."""

    image_urls: list[str] = []
    thumbnail_urls: list[str] = []
    video_urls: list[str] = []
    text_fragments: list[TextFragment] = []
    seen_fragments: set[tuple[str, str, str]] = set()

    for row in profile_results:
        if not isinstance(row, dict):
            continue
        platform = str(row.get("platform") or "profile").strip() or "profile"

        for field_name in _IMAGE_FIELDS:
            value = row.get(field_name)
            if isinstance(value, str):
                _append_unique_url(image_urls, value)
            elif isinstance(value, list):
                for item in value:
                    _append_unique_url(image_urls, item)

        for field_name in _THUMBNAIL_FIELDS:
            value = row.get(field_name)
            if isinstance(value, str):
                _append_unique_url(thumbnail_urls, value)
            elif isinstance(value, list):
                for item in value:
                    _append_unique_url(thumbnail_urls, item)

        for field_name in _VIDEO_FIELDS:
            value = row.get(field_name)
            if isinstance(value, str):
                _append_unique_url(video_urls, value)
            elif isinstance(value, list):
                for item in value:
                    _append_unique_url(video_urls, item)

        for link_url in row.get("links", []) or []:
            token = str(link_url).strip()
            if _looks_like_image_url(token):
                _append_unique_url(image_urls, token)
            if _looks_like_video_url(token):
                _append_unique_url(video_urls, token)

        for path, value in _iter_nested_values(row):
            if not isinstance(value, str):
                continue
            leaf = path.rsplit(".", maxsplit=1)[-1].lower()
            if "[" in leaf:
                leaf = leaf.split("[", maxsplit=1)[0]
            if any(token in leaf for token in _TEXT_FIELD_TOKENS):
                text = _clean_text(value)
                if not text:
                    continue
                if text.startswith(("http://", "https://")):
                    continue
                if leaf.endswith("_url") or leaf.endswith("_urls"):
                    continue
                item = (platform, leaf, text)
                if item in seen_fragments:
                    continue
                seen_fragments.add(item)
                text_fragments.append(TextFragment(source=platform, field=leaf, text=text))
            elif str(value).startswith(("http://", "https://")):
                if _looks_like_image_url(value):
                    _append_unique_url(image_urls, value)
                if _looks_like_video_url(value):
                    _append_unique_url(video_urls, value)

    if not image_urls and str(target).startswith(("http://", "https://")) and _looks_like_image_url(str(target)):
        image_urls.append(str(target))
    if not video_urls and str(target).startswith(("http://", "https://")) and _looks_like_video_url(str(target)):
        video_urls.append(str(target))

    return MediaReconTargets(
        image_urls=tuple(image_urls[:12]),
        thumbnail_urls=tuple(thumbnail_urls[:8]),
        video_urls=tuple(video_urls[:8]),
        text_fragments=tuple(text_fragments[:18]),
    )


def summarize_text_signals(target: str, fragments: tuple[TextFragment, ...]) -> TextSignalSummary:
    """Convert harvested public text into structured OSINT cues."""

    texts = [fragment.text for fragment in fragments]
    corpus = "\n".join(texts)
    emails = tuple(sorted({value.lower() for value in _EMAIL_RE.findall(corpus)})[:20])
    urls = tuple(sorted({value for value in _URL_RE.findall(corpus)})[:20])
    phones = tuple(sorted({_normalize_phone(value) for value in _PHONE_RE.findall(corpus) if _normalize_phone(value)})[:20])
    mentions = tuple(sorted({value.lower() for value in _MENTION_RE.findall(corpus)})[:20])
    hashtags = tuple(sorted({value.lower() for value in _HASHTAG_RE.findall(corpus)})[:20])

    name_candidates: list[str] = []
    for text in texts:
        for candidate in extract_name_candidates(text):
            if candidate.lower() in {item.lower() for item in name_candidates}:
                continue
            name_candidates.append(candidate)
            if len(name_candidates) >= 12:
                break
        if len(name_candidates) >= 12:
            break

    target_pattern = re.compile(re.escape(str(target or "").strip()), re.IGNORECASE) if str(target or "").strip() else None
    target_hit_count = sum(len(target_pattern.findall(text)) for text in texts) if target_pattern is not None else 0

    return TextSignalSummary(
        fragment_count=len(texts),
        emails=emails,
        urls=urls,
        phones=phones,
        mentions=mentions,
        hashtags=hashtags,
        names=tuple(name_candidates),
        keywords=_top_keywords(texts, target=target),
        target_hit_count=target_hit_count,
    )


async def _fetch_image_asset(
    session: aiohttp.ClientSession,
    media_url: str,
    *,
    asset_kind: str,
    timeout_seconds: int,
    proxy_url: str | None,
) -> MediaReconAsset | None:
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
        content_type = str(response.headers.get("Content-Type") or "")

    width, height, metadata = _extract_image_details(media_bytes)
    ocr_text, ocr_engine = _run_ocr(media_bytes)
    stego_score, stego_flags, entropy_score = _score_stego_suspicion(
        media_bytes=media_bytes,
        width=width,
        height=height,
        metadata=metadata,
        content_type=content_type,
    )
    return MediaReconAsset(
        url=media_url,
        asset_kind=asset_kind,
        content_type=content_type,
        size_bytes=len(media_bytes),
        sha256=hashlib.sha256(media_bytes).hexdigest(),
        width=width,
        height=height,
        metadata=metadata,
        ocr_text=ocr_text[:1200],
        ocr_engine=ocr_engine,
        extracted_signals=_extract_ocr_signals(ocr_text),
        entropy_score=entropy_score,
        stego_score=stego_score,
        stego_flags=stego_flags,
    )


async def _fetch_video_endpoint(
    session: aiohttp.ClientSession,
    media_url: str,
    *,
    thumbnail_url: str | None,
    timeout_seconds: int,
    proxy_url: str | None,
) -> VideoEndpointObservation | None:
    request_kwargs: dict[str, Any] = {
        "timeout": aiohttp.ClientTimeout(total=max(1, int(timeout_seconds))),
        "allow_redirects": True,
    }
    if proxy_url:
        request_kwargs["proxy"] = proxy_url

    response: aiohttp.ClientResponse | None = None
    status_code = 0
    final_url = media_url
    headers: dict[str, str] = {}
    notes: list[str] = []

    try:
        response = await session.head(media_url, **request_kwargs)
    except Exception:
        response = None

    if response is not None:
        async with response:
            status_code = response.status
            final_url = str(response.url)
            headers = {str(key): str(value) for key, value in response.headers.items()}

    if status_code in {0, 403, 405, 501}:
        range_kwargs = dict(request_kwargs)
        range_kwargs["headers"] = {"Range": "bytes=0-0"}
        try:
            async with session.get(media_url, **range_kwargs) as ranged:
                status_code = ranged.status
                final_url = str(ranged.url)
                headers = {str(key): str(value) for key, value in ranged.headers.items()}
                if status_code < 400:
                    notes.append("Video endpoint validated with a single-byte range request.")
        except Exception as exc:
            notes.append(f"Video endpoint probe skipped: {exc}")
            return None

    if status_code >= 400:
        return None

    content_type = str(headers.get("Content-Type") or "")
    content_length = int(str(headers.get("Content-Length") or "0").strip() or 0)
    extracted_signals = {
        "emails": sorted({value.lower() for value in _EMAIL_RE.findall(media_url)})[:20],
        "urls": sorted({value for value in _URL_RE.findall(media_url)})[:20],
    }
    if thumbnail_url:
        notes.append("Thumbnail URL was linked for visual follow-up.")
    return VideoEndpointObservation(
        url=media_url,
        content_type=content_type,
        status_code=status_code,
        size_bytes=content_length,
        final_url=final_url,
        thumbnail_url=thumbnail_url,
        extracted_signals=extracted_signals,
        notes=tuple(notes),
    )


def _thumbnail_map(targets: MediaReconTargets) -> dict[str, str]:
    thumbnails = list(targets.thumbnail_urls)
    mapping: dict[str, str] = {}
    for index, video_url in enumerate(targets.video_urls):
        if index < len(thumbnails):
            mapping[video_url] = thumbnails[index]
    return mapping


async def collect_profile_media_recon(
    profile_results: list[dict[str, Any]],
    *,
    target: str,
    timeout_seconds: int = 12,
    proxy_url: str | None = None,
) -> MediaReconResult:
    """Run public media reconnaissance across image, thumbnail, video, and post-text inputs."""

    from core.engines.media_recon_engine import MediaReconEngine

    engine = MediaReconEngine()
    return await engine.run_media_recon(
        profile_results,
        target=target,
        timeout_seconds=timeout_seconds,
        proxy_url=proxy_url,
    )


def collect_profile_media_recon_blocking(
    profile_results: list[dict[str, Any]],
    *,
    target: str,
    timeout_seconds: int = 12,
    proxy_url: str | None = None,
) -> MediaReconResult:
    """Blocking wrapper for plugin-oriented public media reconnaissance."""

    return asyncio.run(
        collect_profile_media_recon(
            profile_results,
            target=target,
            timeout_seconds=timeout_seconds,
            proxy_url=proxy_url,
        )
    )
