"""Plugin: ROT13 attachment cipher helper."""

from __future__ import annotations

from typing import Any

from plugins.crypto._shared import collect_crypto_payloads, resolve_crypto_config


PLUGIN_SPEC = {
    "id": "crypto_rot13_attachment",
    "title": "ROT13 Attachment Cipher",
    "description": "Applies ROT13 transform on attachment-like payloads for reversible text masking.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["rot13_plugin", "rot13_crypto", "crypto_rot13"],
    "version": "1.0",
}


_ROT13_TABLE = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
)


def _rot13(value: str) -> str:
    return value.translate(_ROT13_TABLE)


def run(context: dict[str, Any]) -> dict[str, Any]:
    config = resolve_crypto_config(context, crypto_kind="rot13")
    operation = str(config.get("operation") or "encrypt")
    rows, source_counts = collect_crypto_payloads(
        context,
        source_fields=list(config.get("source_fields", [])),
        max_items=int(config.get("max_items", 12)),
    )

    transformed = [_rot13(row) for row in rows]
    summary = f"ROT13 {operation}ed {len(transformed)} payload(s)."
    return {
        "severity": "INFO",
        "summary": summary,
        "highlights": [
            f"operation={operation}",
            f"sources={','.join(config.get('source_fields', []))}",
            f"count={len(transformed)}",
            "rot13 is symmetric (encode == decode)",
        ],
        "data": {
            "crypto_kind": "rot13",
            "operation": operation,
            "payloads": transformed,
            "payload_count": len(transformed),
            "source_summary": source_counts,
            "crypto_profile": config,
        },
    }
