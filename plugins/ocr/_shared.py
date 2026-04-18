"""Shared helpers for OCR image-scan plugins."""

from __future__ import annotations

from typing import Any

from core.collect.ocr_image_scan import OCRImageScanResult, collect_ocr_image_scan_blocking


def resolve_ocr_scan_payload(context: dict[str, Any]) -> OCRImageScanResult:
    """Reuse OCR scan data from context when available, otherwise collect it."""

    previous = context.get("previous_plugin_data")
    if isinstance(previous, dict):
        for key in ("ocr_extractor", "ocr_regex_filters", "ocr_batch_processor"):
            payload = previous.get(key)
            if isinstance(payload, dict) and payload.get("summary") and payload.get("items") is not None:
                return ocr_scan_result_from_dict(payload)

    result_payloads = [row for row in (context.get("plugins", []) or []) if isinstance(row, dict)]
    for plugin_payload in result_payloads:
        data = plugin_payload.get("data")
        if not isinstance(data, dict):
            continue
        if data.get("summary") and data.get("items") is not None:
            return ocr_scan_result_from_dict(data)

    raw_payload = context.get("ocr_scan")
    if isinstance(raw_payload, dict) and raw_payload.get("summary") and raw_payload.get("items") is not None:
        return ocr_scan_result_from_dict(raw_payload)

    return collect_ocr_image_scan_blocking(
        paths=list(context.get("image_paths", []) or []),
        urls=list(context.get("image_urls", []) or []),
        preprocess_mode=str(context.get("preprocess_mode") or "balanced"),
        timeout_seconds=int(context.get("timeout", 20) or 20),
        max_bytes=int(context.get("max_bytes", 15_000_000) or 15_000_000),
        max_edge=int(context.get("max_edge", 0) or 0) or None,
        threshold=context.get("threshold"),
        proxy_url=str(context.get("proxy_url") or "").strip() or None,
    )


def ocr_scan_result_from_dict(payload: dict[str, Any]) -> OCRImageScanResult:
    """Rehydrate an OCR scan result from a JSON-safe payload."""

    from core.collect.ocr_image_scan import (
        OCRImageScanResult,
        OCRScanFailure,
        OCRScanItem,
        OCRScanSource,
        OCRScanSummary,
    )

    sources_raw = payload.get("sources")
    items_raw = payload.get("items")
    failures_raw = payload.get("failures")
    engine_results_raw = payload.get("engine_results")

    sources = tuple(
        OCRScanSource(
            source=str(item.get("source") or ""),
            source_kind=str(item.get("source_kind") or "local_path"),
        )
        for item in (sources_raw if isinstance(sources_raw, list) else [])
        if isinstance(item, dict)
    )
    items = tuple(
        OCRScanItem(
            source=str(item.get("source") or ""),
            source_kind=str(item.get("source_kind") or "local_path"),
            display_name=str(item.get("display_name") or ""),
            content_type=str(item.get("content_type") or ""),
            size_bytes=int(item.get("size_bytes") or 0),
            sha256=str(item.get("sha256") or ""),
            width=int(item["width"]) if item.get("width") is not None else None,
            height=int(item["height"]) if item.get("height") is not None else None,
            preprocess_pipeline=tuple(str(value) for value in (item.get("preprocess_pipeline") or []) if str(value).strip()),
            raw_text=str(item.get("raw_text") or ""),
            ocr_engine=str(item.get("ocr_engine") or "none"),
            extracted_signals={
                str(key): [str(value) for value in values]
                for key, values in (item.get("extracted_signals") or {}).items()
                if isinstance(values, list)
            },
            language=str(item.get("language") or ""),
            confidence_hint=str(item.get("confidence_hint") or "low"),
            notes=tuple(str(value) for value in (item.get("notes") or []) if str(value).strip()),
        )
        for item in (items_raw if isinstance(items_raw, list) else [])
        if isinstance(item, dict)
    )
    failures = tuple(
        OCRScanFailure(
            source=str(item.get("source") or ""),
            source_kind=str(item.get("source_kind") or "local_path"),
            error=str(item.get("error") or ""),
        )
        for item in (failures_raw if isinstance(failures_raw, list) else [])
        if isinstance(item, dict)
    )
    summary_payload = payload.get("summary")
    summary_raw: dict[str, Any] = summary_payload if isinstance(summary_payload, dict) else {}
    summary = OCRScanSummary(
        image_count=int(summary_raw.get("image_count") or 0),
        processed_count=int(summary_raw.get("processed_count") or 0),
        failed_count=int(summary_raw.get("failed_count") or 0),
        ocr_hits=int(summary_raw.get("ocr_hits") or 0),
        signal_totals={str(key): int(value) for key, value in ((summary_raw.get("signal_totals") if isinstance(summary_raw.get("signal_totals"), dict) else {}) or {}).items()},
        languages={str(key): int(value) for key, value in ((summary_raw.get("languages") if isinstance(summary_raw.get("languages"), dict) else {}) or {}).items()},
        confidence_hints={str(key): int(value) for key, value in ((summary_raw.get("confidence_hints") if isinstance(summary_raw.get("confidence_hints"), dict) else {}) or {}).items()},
        engines={str(key): int(value) for key, value in ((summary_raw.get("engines") if isinstance(summary_raw.get("engines"), dict) else {}) or {}).items()},
        source_kinds={str(key): int(value) for key, value in ((summary_raw.get("source_kinds") if isinstance(summary_raw.get("source_kinds"), dict) else {}) or {}).items()},
    )
    return OCRImageScanResult(
        target=str(payload.get("target") or "ocr_scan"),
        sources=sources,
        items=items,
        failures=failures,
        summary=summary,
        notes=tuple(str(item) for item in (payload.get("notes") or []) if str(item).strip()),
        engine_health=dict(payload.get("engine_health") or {}),
        engine_results=tuple(
            {
                "name": str(item.get("name") or ""),
                "status": str(item.get("status") or ""),
                "error": item.get("error"),
                "execution_time": float(item.get("execution_time") or 0.0),
            }
            for item in (engine_results_raw if isinstance(engine_results_raw, list) else [])
            if isinstance(item, dict)
        ),
    )
