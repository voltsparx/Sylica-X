"""Dedicated OCR image-scan engine for local and remote media inputs."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

import aiohttp

from core.engine_manager import AsyncEngine
from core.engines.engine_base import EngineBase
from core.engines.engine_result import EngineResult
from core.collect.ocr_image_scan import (
    OCRImageScanResult,
    OCRScanFailure,
    OCRScanItem,
    _confidence_hint,
    _detect_language,
    _extract_dimensions,
    build_ocr_scan_summary,
    extract_ocr_text_signals,
    fetch_remote_image_payload,
    load_local_image_payload,
    preprocess_image_payload,
    resolve_ocr_sources,
)


def _serialize_engine_result(item: EngineResult) -> dict[str, Any]:
    return {
        "name": item.name,
        "status": item.status,
        "error": item.error,
        "execution_time": round(float(item.execution_time), 4),
    }


class OCRImageScanEngine(EngineBase):
    """Stage-aware OCR image scanner with bounded local and remote ingestion."""

    def __init__(self) -> None:
        super().__init__()
        self._async_engine = AsyncEngine(monitor=self._monitor)

    async def run(self, tasks: Any, context: dict[str, Any] | None = None) -> list[Any]:
        return await self._async_engine.run(tasks, context=context)

    async def run_detailed(self, tasks: Any, context: dict[str, Any] | None = None) -> list[EngineResult]:
        return await self._async_engine.run_detailed(tasks, context=context)

    def _analyze_payload_with_pipeline(
        self,
        *,
        payload: bytes,
        source: str,
        source_kind: str,
        content_type: str,
        preprocess_mode: str,
        max_edge: int | None,
        threshold: int | None,
    ) -> OCRScanItem:
        from core.collect.ocr_pipeline import run_ocr_pipeline

        processed_payload, pipeline, preprocess_notes = preprocess_image_payload(
            payload,
            preprocess_mode=preprocess_mode,
            max_edge=max_edge,
            threshold=threshold,
        )
        width, height = _extract_dimensions(processed_payload)
        pipeline_result = run_ocr_pipeline(
            processed_payload,
            preprocess_intensity="off",
        )
        normalized_text = str(pipeline_result.get("merged_text", "") or "").strip()[:2400]
        merged = pipeline_result.get("merged", {}) if isinstance(pipeline_result.get("merged"), dict) else {}
        ocr_engine = str(merged.get("primary_engine", "none") or "none")
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
            confidence_hint=_confidence_hint(
                raw_text=normalized_text,
                signals=signals,
                ocr_engine=ocr_engine,
            ),
            notes=tuple(notes),
        )

    async def _process_local_source(
        self,
        source: str,
        *,
        preprocess_mode: str,
        max_bytes: int,
        max_edge: int | None,
        threshold: int | None,
    ) -> OCRScanItem:
        payload, content_type, normalized_source = await asyncio.to_thread(
            load_local_image_payload,
            source,
            max_bytes=max_bytes,
        )
        return await asyncio.to_thread(
            self._analyze_payload_with_pipeline,
            payload=payload,
            source=normalized_source,
            source_kind="local_path",
            content_type=content_type,
            preprocess_mode=preprocess_mode,
            max_edge=max_edge,
            threshold=threshold,
        )

    async def _process_remote_source(
        self,
        session: aiohttp.ClientSession,
        source: str,
        *,
        preprocess_mode: str,
        timeout_seconds: int,
        proxy_url: str | None,
        max_bytes: int,
        max_edge: int | None,
        threshold: int | None,
    ) -> OCRScanItem:
        payload, content_type = await fetch_remote_image_payload(
            session,
            source,
            timeout_seconds=timeout_seconds,
            proxy_url=proxy_url,
            max_bytes=max_bytes,
        )
        return await asyncio.to_thread(
            self._analyze_payload_with_pipeline,
            payload=payload,
            source=source,
            source_kind="remote_url",
            content_type=content_type,
            preprocess_mode=preprocess_mode,
            max_edge=max_edge,
            threshold=threshold,
        )

    async def run_ocr_scan(
        self,
        *,
        paths: list[str],
        urls: list[str],
        preprocess_mode: str = "balanced",
        timeout_seconds: int = 20,
        max_concurrency: int = 4,
        max_bytes: int = 15_000_000,
        max_edge: int | None = None,
        threshold: int | None = None,
        proxy_url: str | None = None,
    ) -> OCRImageScanResult:
        sources = resolve_ocr_sources(paths=paths, urls=urls)
        if not sources:
            empty_summary = build_ocr_scan_summary(source_count=0, items=(), failures=())
            return OCRImageScanResult(
                target="ocr_scan",
                sources=(),
                items=(),
                failures=(),
                summary=empty_summary,
                notes=("No local image paths or remote image URLs were provided.",),
                engine_health=self.health_check(),
                engine_results=(),
            )

        connector = aiohttp.TCPConnector(limit=max(1, int(max_concurrency)), ttl_dns_cache=300)
        runtime = {"max_workers": max(1, int(max_concurrency)), "timeout": timeout_seconds}
        notes: list[str] = []
        failures: list[OCRScanFailure] = []
        items: list[OCRScanItem] = []
        engine_results: list[dict[str, Any]] = []

        async with aiohttp.ClientSession(connector=connector) as session:
            task_factories = []
            for source in sources:
                if source.source_kind == "remote_url":
                    async def _task(source: str = source.source) -> Any:
                        return await self._process_remote_source(
                            session,
                            source,
                            preprocess_mode=preprocess_mode,
                            timeout_seconds=timeout_seconds,
                            proxy_url=proxy_url,
                            max_bytes=max_bytes,
                            max_edge=max_edge,
                            threshold=threshold,
                        )

                    task_name = f"ocr-remote:{source.source}"
                else:
                    async def _task(source: str = source.source) -> Any:
                        return await self._process_local_source(
                            source,
                            preprocess_mode=preprocess_mode,
                            max_bytes=max_bytes,
                            max_edge=max_edge,
                            threshold=threshold,
                        )

                    task_name = f"ocr-local:{Path(source.source).name}"
                setattr(_task, "_silica_x_task_name", task_name)
                task_factories.append((source, _task))

            batch = await self._async_engine.run_detailed(
                [task for _source, task in task_factories],
                runtime,
            )

        for (source, _task), result in zip(task_factories, batch):
            engine_results.append(_serialize_engine_result(result))
            if result.status != "success":
                failures.append(
                    OCRScanFailure(
                        source=source.source,
                        source_kind=source.source_kind,
                        error=str(result.error or result.status),
                    )
                )
                continue
            payload = result.data.get("payload")
            if isinstance(payload, OCRScanItem):
                items.append(payload)
                continue
            failures.append(
                OCRScanFailure(
                    source=source.source,
                    source_kind=source.source_kind,
                    error="Unexpected OCR payload type.",
                )
            )

        summary = build_ocr_scan_summary(
            source_count=len(sources),
            items=tuple(items),
            failures=tuple(failures),
        )
        if items:
            notes.append(
                "OCR image scan processed local or remote images with preprocessing, structured extraction, and batch rollups."
            )
        if failures:
            notes.append(f"{len(failures)} source(s) failed validation, fetch, decode, or OCR processing.")

        return OCRImageScanResult(
            target="ocr_scan",
            sources=sources,
            items=tuple(items),
            failures=tuple(failures),
            summary=summary,
            notes=tuple(notes),
            engine_health=self.health_check(),
            engine_results=tuple(engine_results),
        )
