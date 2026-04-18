"""Local and remote OCR image-scan helpers for dedicated media intelligence."""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
import hashlib
import io
import mimetypes
from pathlib import Path
import re
from typing import Any

import aiohttp

from core.collect.media_intel import _run_ocr
from core.intelligence.entity_builder import extract_name_candidates


ALLOWED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
PREPROCESS_MODES = ("off", "light", "balanced", "aggressive")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://[^\s<>'\"]+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s().]{6,}\d)")
_MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_.-]{2,32})")
_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z][A-Za-z0-9_]{1,31})")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{3,24}")
_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "been",
    "being",
    "build",
    "built",
    "contact",
    "email",
    "from",
    "have",
    "into",
    "more",
    "most",
    "page",
    "post",
    "profile",
    "public",
    "scan",
    "still",
    "text",
    "that",
    "their",
    "them",
    "they",
    "this",
    "with",
    "your",
}


@dataclass(frozen=True)
class OCRScanSource:
    """Normalized OCR input source."""

    source: str
    source_kind: str

    def as_dict(self) -> dict[str, str]:
        return {"source": self.source, "source_kind": self.source_kind}


@dataclass(frozen=True)
class OCRScanItem:
    """OCR intelligence extracted from one image source."""

    source: str
    source_kind: str
    display_name: str
    content_type: str
    size_bytes: int
    sha256: str
    width: int | None
    height: int | None
    preprocess_pipeline: tuple[str, ...]
    raw_text: str
    ocr_engine: str
    extracted_signals: dict[str, list[str]]
    language: str
    confidence_hint: str
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_kind": self.source_kind,
            "display_name": self.display_name,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "width": self.width,
            "height": self.height,
            "preprocess_pipeline": list(self.preprocess_pipeline),
            "raw_text": self.raw_text,
            "ocr_engine": self.ocr_engine,
            "extracted_signals": {key: list(values) for key, values in self.extracted_signals.items()},
            "language": self.language,
            "confidence_hint": self.confidence_hint,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class OCRScanFailure:
    """One OCR input that could not be processed."""

    source: str
    source_kind: str
    error: str

    def as_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "source_kind": self.source_kind,
            "error": self.error,
        }


@dataclass(frozen=True)
class OCRScanSummary:
    """Rollup summary for a batch OCR run."""

    image_count: int
    processed_count: int
    failed_count: int
    ocr_hits: int
    signal_totals: dict[str, int]
    languages: dict[str, int]
    confidence_hints: dict[str, int]
    engines: dict[str, int]
    source_kinds: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "image_count": self.image_count,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "ocr_hits": self.ocr_hits,
            "signal_totals": dict(self.signal_totals),
            "languages": dict(self.languages),
            "confidence_hints": dict(self.confidence_hints),
            "engines": dict(self.engines),
            "source_kinds": dict(self.source_kinds),
        }


@dataclass(frozen=True)
class OCRImageScanResult:
    """Full OCR batch result for reporting, plugins, and storage."""

    target: str
    sources: tuple[OCRScanSource, ...]
    items: tuple[OCRScanItem, ...]
    failures: tuple[OCRScanFailure, ...]
    summary: OCRScanSummary
    notes: tuple[str, ...]
    engine_health: dict[str, Any] | None = None
    engine_results: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "sources": [item.as_dict() for item in self.sources],
            "items": [item.as_dict() for item in self.items],
            "failures": [item.as_dict() for item in self.failures],
            "summary": self.summary.as_dict(),
            "notes": list(self.notes),
            "engine_health": dict(self.engine_health or {}),
            "engine_results": [dict(item) for item in self.engine_results],
        }


def _dedupe(values: list[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token:
            continue
        lowered = token.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(token)
    return tuple(ordered)


def resolve_ocr_sources(
    *,
    paths: list[str] | None = None,
    urls: list[str] | None = None,
) -> tuple[OCRScanSource, ...]:
    """Normalize and deduplicate OCR input sources."""

    resolved: list[OCRScanSource] = []
    seen: set[tuple[str, str]] = set()

    for raw_path in paths or []:
        path = str(raw_path or "").strip()
        if not path:
            continue
        key = ("local_path", path.casefold())
        if key in seen:
            continue
        seen.add(key)
        resolved.append(OCRScanSource(source=path, source_kind="local_path"))

    for raw_url in urls or []:
        url = str(raw_url or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        key = ("remote_url", url.casefold())
        if key in seen:
            continue
        seen.add(key)
        resolved.append(OCRScanSource(source=url, source_kind="remote_url"))

    return tuple(resolved)


def _normalize_local_path(raw_path: str) -> Path:
    path = Path(str(raw_path or "").strip()).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    return path


def _validate_local_image_path(path: Path, *, max_bytes: int) -> None:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise ValueError(f"Unsupported image suffix: {suffix or '<none>'}")
    size_bytes = int(path.stat().st_size)
    if size_bytes <= 0:
        raise ValueError("Input file is empty.")
    if size_bytes > max_bytes:
        raise ValueError(f"Input file exceeds max-bytes guardrail ({max_bytes}).")


def load_local_image_payload(
    raw_path: str,
    *,
    max_bytes: int,
) -> tuple[bytes, str, str]:
    """Read and validate a local image path."""

    path = _normalize_local_path(raw_path)
    _validate_local_image_path(path, max_bytes=max_bytes)
    payload = path.read_bytes()
    content_type = str(mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    return payload, content_type, str(path)


async def fetch_remote_image_payload(
    session: aiohttp.ClientSession,
    media_url: str,
    *,
    timeout_seconds: int,
    proxy_url: str | None,
    max_bytes: int,
) -> tuple[bytes, str]:
    """Fetch a remote image within bounded limits."""

    request_kwargs: dict[str, Any] = {
        "timeout": aiohttp.ClientTimeout(total=max(1, int(timeout_seconds))),
        "allow_redirects": True,
    }
    if proxy_url:
        request_kwargs["proxy"] = proxy_url

    async with session.get(media_url, **request_kwargs) as response:
        if response.status >= 400:
            raise ValueError(f"HTTP {response.status}")
        payload = await response.content.read(max_bytes + 1)
        if not payload:
            raise ValueError("Remote image returned no content.")
        if len(payload) > max_bytes:
            raise ValueError(f"Remote image exceeds max-bytes guardrail ({max_bytes}).")
        content_type = str(response.headers.get("Content-Type") or "application/octet-stream")
    return payload, content_type


def _extract_dimensions(payload: bytes) -> tuple[int | None, int | None]:
    try:
        from PIL import Image
    except Exception:
        return None, None

    try:
        with Image.open(io.BytesIO(payload)) as image_handle:
            return int(image_handle.width), int(image_handle.height)
    except Exception:
        return None, None


def preprocess_image_payload(
    payload: bytes,
    *,
    preprocess_mode: str,
    max_edge: int | None,
    threshold: int | None,
) -> tuple[bytes, tuple[str, ...], tuple[str, ...]]:
    """Apply lightweight OCR-friendly preprocessing when Pillow is available."""

    normalized_mode = str(preprocess_mode or "balanced").strip().lower()
    if normalized_mode not in PREPROCESS_MODES:
        normalized_mode = "balanced"
    if normalized_mode == "off" and not max_edge and threshold is None:
        return payload, (), ()

    try:
        from PIL import Image, ImageOps
    except Exception:
        return payload, (), ("Pillow unavailable; preprocessing skipped.",)

    try:
        with Image.open(io.BytesIO(payload)) as image_handle:
            working = ImageOps.exif_transpose(image_handle)
            operations: list[str] = []

            if normalized_mode in {"light", "balanced", "aggressive"}:
                working = working.convert("RGB")
            if normalized_mode in {"balanced", "aggressive"}:
                working = ImageOps.autocontrast(working)
                operations.append("autocontrast")
                working = working.convert("L")
                operations.append("grayscale")
            elif normalized_mode == "light":
                working = working.convert("L")
                operations.append("grayscale")

            effective_threshold = threshold
            if effective_threshold is None and normalized_mode == "aggressive":
                effective_threshold = 168
            if effective_threshold is not None:
                cutoff = max(0, min(255, int(effective_threshold)))
                grayscale = working.convert("L")
                working = grayscale.point(lambda value: 255 if value >= cutoff else 0)
                operations.append(f"threshold_{cutoff}")

            if max_edge is not None and int(max_edge) > 0:
                limit = int(max_edge)
                working.thumbnail((limit, limit))
                operations.append(f"max_edge_{limit}")

            buffer = io.BytesIO()
            working.save(buffer, format="PNG")
            return buffer.getvalue(), tuple(operations), ()
    except Exception as exc:
        return payload, (), (f"Preprocessing skipped: {exc}",)


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D+", "", str(raw))
    if len(digits) < 7:
        return ""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


def _detect_language(raw_text: str) -> str:
    text = " ".join(str(raw_text or "").split())
    if len(text) < 24:
        return ""
    try:
        from langdetect import LangDetectException, detect
    except Exception:
        return ""
    try:
        return str(detect(text) or "").strip().lower()
    except LangDetectException:
        return ""
    except Exception:
        return ""


def _top_keywords(raw_text: str, *, limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for token in _WORD_RE.findall(str(raw_text or "").lower()):
        if token in _STOPWORDS:
            continue
        counter[token] += 1
    return [token for token, _count in counter.most_common(limit)]


def extract_ocr_text_signals(raw_text: str) -> dict[str, list[str]]:
    """Extract structured OSINT indicators from OCR text."""

    text = str(raw_text or "")
    signals = {
        "emails": sorted({value.lower() for value in _EMAIL_RE.findall(text)})[:20],
        "urls": sorted({value for value in _URL_RE.findall(text)})[:20],
        "phones": sorted({_normalize_phone(value) for value in _PHONE_RE.findall(text) if _normalize_phone(value)})[:20],
        "mentions": sorted({value.lower() for value in _MENTION_RE.findall(text)})[:20],
        "hashtags": sorted({value.lower() for value in _HASHTAG_RE.findall(text)})[:20],
        "names": [],
        "keywords": _top_keywords(text),
    }
    names: list[str] = []
    for candidate in extract_name_candidates(text):
        if candidate.lower() in {item.lower() for item in names}:
            continue
        names.append(candidate)
        if len(names) >= 12:
            break
    signals["names"] = names
    return signals


def _confidence_hint(*, raw_text: str, signals: dict[str, list[str]], ocr_engine: str) -> str:
    signal_count = sum(len(values) for values in signals.values())
    text_length = len(" ".join(str(raw_text or "").split()))
    if not raw_text.strip() or ocr_engine == "none":
        return "low"
    if signal_count >= 3 or text_length >= 140:
        return "high"
    if signal_count >= 1 or text_length >= 36:
        return "medium"
    return "low"


def analyze_ocr_image_payload(
    *,
    payload: bytes,
    source: str,
    source_kind: str,
    content_type: str,
    preprocess_mode: str,
    max_edge: int | None,
    threshold: int | None,
) -> OCRScanItem:
    """Convert one image payload into OCR intelligence."""

    processed_payload, pipeline, preprocess_notes = preprocess_image_payload(
        payload,
        preprocess_mode=preprocess_mode,
        max_edge=max_edge,
        threshold=threshold,
    )
    width, height = _extract_dimensions(processed_payload)
    raw_text, ocr_engine = _run_ocr(processed_payload)
    normalized_text = str(raw_text or "").strip()[:2400]
    signals = extract_ocr_text_signals(normalized_text)
    language = _detect_language(normalized_text)
    notes = list(preprocess_notes)
    if ocr_engine == "none":
        notes.append("No optional OCR engine was available for this image.")
    elif not normalized_text:
        notes.append("OCR engine ran but produced no text.")

    display_name = Path(source).name if source_kind == "local_path" else source
    return OCRScanItem(
        source=source,
        source_kind=source_kind,
        display_name=display_name,
        content_type=content_type,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        width=width,
        height=height,
        preprocess_pipeline=tuple(pipeline),
        raw_text=normalized_text,
        ocr_engine=ocr_engine,
        extracted_signals=signals,
        language=language,
        confidence_hint=_confidence_hint(raw_text=normalized_text, signals=signals, ocr_engine=ocr_engine),
        notes=tuple(notes),
    )


def build_ocr_scan_summary(
    *,
    source_count: int,
    items: tuple[OCRScanItem, ...],
    failures: tuple[OCRScanFailure, ...],
) -> OCRScanSummary:
    """Build rollup counters for an OCR scan batch."""

    signal_totals: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    confidence_hints: Counter[str] = Counter()
    engines: Counter[str] = Counter()
    source_kinds: Counter[str] = Counter()
    ocr_hits = 0

    for item in items:
        if item.raw_text.strip():
            ocr_hits += 1
        for key, values in item.extracted_signals.items():
            signal_totals[key] += len(values)
        if item.language:
            languages[item.language] += 1
        confidence_hints[item.confidence_hint] += 1
        engines[item.ocr_engine] += 1
        source_kinds[item.source_kind] += 1

    for failure in failures:
        source_kinds[failure.source_kind] += 1

    return OCRScanSummary(
        image_count=source_count,
        processed_count=len(items),
        failed_count=len(failures),
        ocr_hits=ocr_hits,
        signal_totals=dict(signal_totals),
        languages=dict(languages),
        confidence_hints=dict(confidence_hints),
        engines=dict(engines),
        source_kinds=dict(source_kinds),
    )


async def collect_ocr_image_scan(
    *,
    paths: list[str] | None = None,
    urls: list[str] | None = None,
    preprocess_mode: str = "balanced",
    timeout_seconds: int = 20,
    max_bytes: int = 15_000_000,
    max_edge: int | None = None,
    threshold: int | None = None,
    proxy_url: str | None = None,
) -> OCRImageScanResult:
    """Blocking-friendly wrapper that routes OCR scans through the engine."""

    from core.engines.ocr_image_scan_engine import OCRImageScanEngine

    engine = OCRImageScanEngine()
    return await engine.run_ocr_scan(
        paths=paths or [],
        urls=urls or [],
        preprocess_mode=preprocess_mode,
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
        max_edge=max_edge,
        threshold=threshold,
        proxy_url=proxy_url,
    )


def collect_ocr_image_scan_blocking(
    *,
    paths: list[str] | None = None,
    urls: list[str] | None = None,
    preprocess_mode: str = "balanced",
    timeout_seconds: int = 20,
    max_bytes: int = 15_000_000,
    max_edge: int | None = None,
    threshold: int | None = None,
    proxy_url: str | None = None,
) -> OCRImageScanResult:
    """Blocking wrapper for OCR image scanning."""

    return asyncio.run(
        collect_ocr_image_scan(
            paths=paths,
            urls=urls,
            preprocess_mode=preprocess_mode,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
            max_edge=max_edge,
            threshold=threshold,
            proxy_url=proxy_url,
        )
    )
