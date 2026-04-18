# ------------------------------------------------------------------------------
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
# ------------------------------------------------------------------------------

"""Read-only public media fetch, metadata, and OCR helpers for profile intelligence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import importlib.util
import io
from pathlib import Path
import re
import shutil
from typing import Any

import aiohttp


_MEDIA_FIELDS = (
    "avatar_url",
    "banner_url",
    "image_url",
    "image_urls",
    "media_urls",
    "post_image_urls",
    "reel_thumbnail_urls",
)
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
_OCR_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}")
_OCR_URL_RE = re.compile(r"https?://[^\s<>'\"]+")


def detect_image_tooling() -> dict[str, Any]:
    """Inspect optional OCR/image runtime dependencies available in the environment."""

    pillow_available = importlib.util.find_spec("PIL") is not None
    easyocr_available = importlib.util.find_spec("easyocr") is not None
    pytesseract_available = importlib.util.find_spec("pytesseract") is not None

    pytesseract_cmd = ""
    if pytesseract_available:
        try:
            import pytesseract

            pytesseract_cmd = str(getattr(getattr(pytesseract, "pytesseract", None), "tesseract_cmd", "") or "").strip()
        except Exception:
            pytesseract_available = False
            pytesseract_cmd = ""

    resolved_tesseract = _resolve_tesseract_binary(pytesseract_cmd)

    if easyocr_available:
        preferred_engine = "easyocr"
    elif pytesseract_available and resolved_tesseract:
        preferred_engine = "pytesseract"
    else:
        preferred_engine = "none"

    return {
        "pillow": {"available": pillow_available},
        "easyocr": {"available": easyocr_available},
        "pytesseract": {
            "available": pytesseract_available,
            "tesseract_cmd": pytesseract_cmd,
            "tesseract_binary_found": bool(resolved_tesseract),
            "tesseract_binary": resolved_tesseract,
        },
        "preferred_engine": preferred_engine,
    }


def _resolve_tesseract_binary(command_hint: str) -> str:
    hint = str(command_hint or "").strip().strip('"')
    candidates = [hint] if hint else []
    candidates.append("tesseract")
    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).is_file():
            return candidate
        resolved = str(shutil.which(candidate) or "").strip()
        if resolved:
            return resolved
    return ""


@dataclass(frozen=True)
class MediaAssetObservation:
    """Describe read-only intelligence extracted from one public media asset."""

    url: str
    content_type: str
    size_bytes: int
    sha256: str
    width: int | None
    height: int | None
    metadata: dict[str, Any]
    ocr_text: str
    ocr_engine: str
    extracted_signals: dict[str, list[str]]

    def as_dict(self) -> dict[str, Any]:
        """Render a JSON-safe media observation for plugin output and reporting."""

        return {
            "url": self.url,
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
        }


@dataclass(frozen=True)
class MediaIntelligenceResult:
    """Summarize read-only metadata and OCR extraction from public profile media."""

    target: str
    media_urls: tuple[str, ...]
    assets: tuple[MediaAssetObservation, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Render a JSON-safe result payload for plugin output and reporting."""

        return {
            "target": self.target,
            "media_urls": list(self.media_urls),
            "assets": [asset.as_dict() for asset in self.assets],
            "notes": list(self.notes),
        }


def _image_like_url(media_url: str) -> bool:
    lowered = str(media_url).strip().lower()
    return lowered.endswith(_IMAGE_SUFFIXES)


def extract_media_urls(profile_results: list[dict[str, Any]], *, target: str) -> tuple[str, ...]:
    """Extract candidate public image URLs from profile rows for read-only analysis."""

    urls: list[str] = []
    for row in profile_results:
        if not isinstance(row, dict):
            continue
        for field_name in _MEDIA_FIELDS:
            value = row.get(field_name)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                urls.append(value)
            elif isinstance(value, list):
                urls.extend(str(item).strip() for item in value if str(item).startswith(("http://", "https://")))
        for link_url in row.get("links", []) or []:
            token = str(link_url).strip()
            if token.startswith(("http://", "https://")) and _image_like_url(token):
                urls.append(token)

    ordered: list[str] = []
    seen: set[str] = set()
    for media_url in urls:
        lowered = media_url.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(media_url)
        if len(ordered) >= 12:
            break

    if not ordered and str(target).startswith(("http://", "https://")) and _image_like_url(str(target)):
        return (str(target),)
    return tuple(ordered)


def _extract_image_metadata(media_bytes: bytes) -> tuple[int | None, int | None, dict[str, Any], str]:
    try:
        from PIL import ExifTags, Image
    except Exception:
        return None, None, {"metadata_status": "pillow_unavailable"}, "none"

    try:
        with Image.open(io.BytesIO(media_bytes)) as image_handle:
            width, height = image_handle.size
            metadata: dict[str, Any] = {
                "format": str(getattr(image_handle, "format", "") or ""),
                "mode": str(getattr(image_handle, "mode", "") or ""),
            }
            exif: Any = getattr(image_handle, "getexif", lambda: {})()
            if exif:
                tag_map = {}
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    tag_map[str(tag_name)] = str(value)
                metadata["exif"] = tag_map
            return width, height, metadata, "pillow"
    except Exception as exc:
        return None, None, {"metadata_status": f"unavailable: {exc}"}, "none"


def _run_ocr(media_bytes: bytes) -> tuple[str, str]:
    easyocr_module: Any | None
    pillow_image_module: Any | None
    try:
        import easyocr
        from PIL import Image
    except Exception:
        easyocr_module = None
        pillow_image_module = None
    else:
        easyocr_module = easyocr
        pillow_image_module = Image

    if easyocr_module is not None and pillow_image_module is not None:
        try:
            reader = easyocr_module.Reader(["en"], gpu=False, verbose=False)
            with pillow_image_module.open(io.BytesIO(media_bytes)) as image_handle:
                results = reader.readtext(image_handle)
            text = " ".join(str(row[1]).strip() for row in results if len(row) >= 2).strip()
            if text:
                return text[:1200], "easyocr"
        except Exception:
            pass

    pytesseract_module: Any | None
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return "", "none"
    else:
        pytesseract_module = pytesseract

    try:
        with Image.open(io.BytesIO(media_bytes)) as image_handle:
            text = str(pytesseract_module.image_to_string(image_handle) or "").strip()
        return text[:1200], "pytesseract" if text else "none"
    except Exception:
        return "", "none"


def _extract_ocr_signals(ocr_text: str) -> dict[str, list[str]]:
    emails = sorted({match.lower() for match in _OCR_EMAIL_RE.findall(ocr_text)})
    urls = sorted({match for match in _OCR_URL_RE.findall(ocr_text)})
    return {"emails": emails[:20], "urls": urls[:20]}


async def _fetch_media_asset(
    session: aiohttp.ClientSession,
    media_url: str,
    *,
    timeout_seconds: int,
    proxy_url: str | None,
) -> MediaAssetObservation | None:
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
    width, height, metadata, _ = _extract_image_metadata(media_bytes)
    ocr_text, ocr_engine = _run_ocr(media_bytes)
    return MediaAssetObservation(
        url=media_url,
        content_type=content_type,
        size_bytes=len(media_bytes),
        sha256=hashlib.sha256(media_bytes).hexdigest(),
        width=width,
        height=height,
        metadata=metadata,
        ocr_text=ocr_text,
        ocr_engine=ocr_engine,
        extracted_signals=_extract_ocr_signals(ocr_text),
    )


async def collect_profile_media_intelligence(
    profile_results: list[dict[str, Any]],
    *,
    target: str,
    timeout_seconds: int = 10,
    proxy_url: str | None = None,
) -> MediaIntelligenceResult:
    """Fetch public media URLs and extract read-only OCR and metadata signals."""

    media_urls = extract_media_urls(profile_results, target=target)
    if not media_urls:
        return MediaIntelligenceResult(
            target=str(target),
            media_urls=(),
            assets=(),
            notes=("No public media URLs were available for OCR or metadata extraction.",),
        )

    connector = aiohttp.TCPConnector(limit=4, ttl_dns_cache=300)
    notes: list[str] = []
    assets: list[MediaAssetObservation] = []
    async with aiohttp.ClientSession(connector=connector) as session:
        for media_url in media_urls[:8]:
            try:
                asset = await _fetch_media_asset(
                    session,
                    media_url,
                    timeout_seconds=timeout_seconds,
                    proxy_url=proxy_url,
                )
                if asset is not None:
                    assets.append(asset)
            except Exception as exc:  # pragma: no cover - defensive media guard
                notes.append(f"Media fetch skipped for {media_url}: {exc}")

    if assets and any(asset.ocr_engine != "none" for asset in assets):
        notes.append("Optional OCR engines were used only on public image content and degrade gracefully if unavailable.")
    elif assets:
        notes.append("Image metadata extraction succeeded; OCR remained unavailable because no optional OCR engine was installed.")

    return MediaIntelligenceResult(
        target=str(target),
        media_urls=tuple(media_urls),
        assets=tuple(assets[:12]),
        notes=tuple(notes),
    )


def collect_profile_media_intelligence_blocking(
    profile_results: list[dict[str, Any]],
    *,
    target: str,
    timeout_seconds: int = 10,
    proxy_url: str | None = None,
) -> MediaIntelligenceResult:
    """Run public-media intelligence from blocking plugin code in a read-only manner."""

    return asyncio.run(
        collect_profile_media_intelligence(
            profile_results,
            target=target,
            timeout_seconds=timeout_seconds,
            proxy_url=proxy_url,
        )
    )
