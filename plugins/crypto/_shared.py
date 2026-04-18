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
#
# This file is part of Silica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

"""Shared helpers for cryptography plugin modules."""

from __future__ import annotations

from typing import Any


DEFAULT_CRYPTO_SOURCES: tuple[str, ...] = (
    "attachments",
    "results",
    "domain_result",
    "correlation",
    "issues",
    "intelligence_bundle",
    "target",
)
VALID_SOURCE_FIELDS: set[str] = set(DEFAULT_CRYPTO_SOURCES)
VALID_OUTPUT_ENCODINGS: set[str] = {"base64", "hex"}


def normalize_operation(raw_value: object) -> str:
    value = str(raw_value or "encrypt").strip().lower()
    if value in {"decrypt", "decode"}:
        return "decrypt"
    return "encrypt"


def normalize_output_encoding(raw_value: object, *, default: str = "base64") -> str:
    value = str(raw_value or default).strip().lower()
    if value in VALID_OUTPUT_ENCODINGS:
        return value
    return default


def _to_bool(raw_value: object, default: bool = False) -> bool:
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _to_int(raw_value: object, *, default: int, minimum: int, maximum: int) -> int:
    if isinstance(raw_value, bool):
        value = int(raw_value)
    elif isinstance(raw_value, int):
        value = raw_value
    elif isinstance(raw_value, float):
        value = int(raw_value)
    elif isinstance(raw_value, (str, bytes, bytearray)):
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return default
    else:
        return default
    return max(minimum, min(maximum, value))


def _normalize_source_fields(raw_value: object) -> tuple[str, ...]:
    if isinstance(raw_value, str):
        tokens = [part.strip().lower() for part in raw_value.split(",")]
    elif isinstance(raw_value, list):
        tokens = [str(part).strip().lower() for part in raw_value]
    else:
        return DEFAULT_CRYPTO_SOURCES
    resolved = [item for item in tokens if item in VALID_SOURCE_FIELDS]
    return tuple(dict.fromkeys(resolved)) if resolved else DEFAULT_CRYPTO_SOURCES


def resolve_crypto_config(context: dict[str, Any], *, crypto_kind: str) -> dict[str, Any]:
    raw_config = context.get("crypto_config")
    config_payload = raw_config if isinstance(raw_config, dict) else {}
    operation = normalize_operation(config_payload.get("operation", context.get("crypto_operation")))
    output_encoding = normalize_output_encoding(
        config_payload.get("output_encoding", context.get("crypto_output_encoding", context.get("crypto_output")))
    )
    max_items = _to_int(
        config_payload.get("max_items", context.get("crypto_max_items", context.get("crypto_limit", 12))),
        default=12,
        minimum=1,
        maximum=200,
    )
    strict_mode = _to_bool(
        config_payload.get(
            "strict_mode",
            config_payload.get("strict", context.get("crypto_strict_mode", context.get("crypto_strict"))),
        ),
        False,
    )
    source_fields = _normalize_source_fields(config_payload.get("source_fields", context.get("crypto_sources")))
    include_metadata = _to_bool(config_payload.get("include_metadata", context.get("crypto_include_metadata")), True)
    return {
        "crypto_kind": crypto_kind,
        "operation": operation,
        "output_encoding": output_encoding,
        "max_items": max_items,
        "strict_mode": strict_mode,
        "source_fields": list(source_fields),
        "include_metadata": include_metadata,
    }


def _extract_text_from_row(row: object) -> str | None:
    if isinstance(row, str):
        value = row.strip()
        return value or None
    if isinstance(row, bytes):
        value = row.decode("utf-8", errors="ignore").strip()
        return value or None
    if isinstance(row, dict):
        for key in ("content", "text", "body", "value", "payload", "name"):
            candidate = row.get(key)
            if isinstance(candidate, str):
                value = candidate.strip()
                if value:
                    return value
            if isinstance(candidate, bytes):
                value = candidate.decode("utf-8", errors="ignore").strip()
                if value:
                    return value
    return None


def extract_attachment_texts(context: dict[str, Any], *, limit: int = 8) -> list[str]:
    rows: list[str] = []
    for key in ("attachments", "evidence", "payloads", "notes"):
        raw = context.get(key)
        if not isinstance(raw, list):
            continue
        for row in raw:
            text = _extract_text_from_row(row)
            if text:
                rows.append(text)
            if len(rows) >= limit:
                return rows[:limit]
    if rows:
        return rows[:limit]

    fallback = str(context.get("target") or context.get("domain") or "").strip()
    if fallback:
        return [fallback]
    return ["silica-x"]


def _append_candidate(candidates: list[str], seen: set[str], value: object) -> bool:
    token = _extract_text_from_row(value)
    if token is None:
        return False
    compact = " ".join(token.split())
    if not compact:
        return False
    bounded = compact[:512]
    key = bounded.lower()
    if key in seen:
        return False
    seen.add(key)
    candidates.append(bounded)
    return True


def collect_crypto_payloads(
    context: dict[str, Any],
    *,
    source_fields: list[str],
    max_items: int,
) -> tuple[list[str], dict[str, int]]:
    candidates: list[str] = []
    seen: set[str] = set()
    source_counts: dict[str, int] = {field: 0 for field in source_fields}

    def add(source: str, value: object) -> None:
        if len(candidates) >= max_items:
            return
        if _append_candidate(candidates, seen, value):
            source_counts[source] = source_counts.get(source, 0) + 1

    for source in source_fields:
        if len(candidates) >= max_items:
            break

        if source == "attachments":
            for key in ("attachments", "evidence", "payloads", "notes"):
                raw = context.get(key)
                if not isinstance(raw, list):
                    continue
                for row in raw:
                    add(source, row)
                    if len(candidates) >= max_items:
                        break
            continue

        if source == "results":
            raw_results = context.get("results")
            if isinstance(raw_results, list):
                for row in raw_results:
                    if not isinstance(row, dict):
                        continue
                    for key in ("platform", "url", "bio"):
                        add(source, row.get(key))
                    mentions = row.get("mentions")
                    if isinstance(mentions, list):
                        for item in mentions:
                            add(source, item)
                    links = row.get("links")
                    if isinstance(links, list):
                        for item in links:
                            add(source, item)
                    contacts = row.get("contacts")
                    if isinstance(contacts, dict):
                        for key in ("emails", "phones"):
                            values = contacts.get(key)
                            if isinstance(values, list):
                                for item in values:
                                    add(source, item)
                    if len(candidates) >= max_items:
                        break
            continue

        if source == "domain_result":
            domain_result = context.get("domain_result")
            if isinstance(domain_result, dict):
                add(source, domain_result.get("target"))
                for key in ("resolved_addresses", "subdomains"):
                    values = domain_result.get(key)
                    if isinstance(values, list):
                        for item in values:
                            add(source, item)
                for key in ("https", "http"):
                    row = domain_result.get(key)
                    if isinstance(row, dict):
                        add(source, row.get("final_url"))
                        add(source, row.get("status"))
                        headers = row.get("headers")
                        if isinstance(headers, dict):
                            for header_key, header_value in list(headers.items())[:12]:
                                add(source, f"{header_key}:{header_value}")
            continue

        if source == "correlation":
            correlation = context.get("correlation")
            if isinstance(correlation, dict):
                for key in ("shared_links", "shared_emails", "shared_phones"):
                    values = correlation.get(key)
                    if isinstance(values, dict):
                        for correlation_key, correlation_values in values.items():
                            add(source, correlation_key)
                            if isinstance(correlation_values, list):
                                for item in correlation_values:
                                    add(source, item)
            continue

        if source == "issues":
            raw_issues = context.get("issues")
            if isinstance(raw_issues, list):
                for row in raw_issues:
                    if not isinstance(row, dict):
                        continue
                    for key in ("title", "evidence", "recommendation"):
                        add(source, row.get(key))
                    if len(candidates) >= max_items:
                        break
            continue

        if source == "intelligence_bundle":
            intelligence_bundle = context.get("intelligence_bundle")
            if isinstance(intelligence_bundle, dict):
                facets = intelligence_bundle.get("entity_facets")
                if isinstance(facets, dict):
                    for key in ("emails", "phones", "names"):
                        values = facets.get(key)
                        if isinstance(values, list):
                            for item in values:
                                add(source, item)
                scored_entities = intelligence_bundle.get("scored_entities")
                if isinstance(scored_entities, list):
                    for row in scored_entities[:24]:
                        if isinstance(row, dict):
                            add(source, row.get("value"))
            continue

        if source == "target":
            add(source, context.get("target"))
            add(source, context.get("domain"))

    if not candidates:
        add("target", context.get("target"))
        add("target", context.get("domain"))
    if not candidates:
        add("target", "silica-x")
    return candidates[:max_items], source_counts
