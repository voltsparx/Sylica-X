"""Plugin: XOR attachment encryption/decryption helper."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any

from plugins.crypto._shared import collect_crypto_payloads, resolve_crypto_config


PLUGIN_SPEC = {
    "id": "crypto_xor_attachment",
    "title": "XOR Attachment Cipher",
    "description": "Applies XOR transform on attachment-like payloads for reversible obfuscation.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["xor_plugin", "xor_crypto", "crypto_xor"],
    "version": "1.0",
}


def _xor_bytes(payload: bytes, key_bytes: bytes) -> bytes:
    return bytes(byte ^ key_bytes[index % len(key_bytes)] for index, byte in enumerate(payload))


def _encode_blob(blob: bytes, *, output_encoding: str) -> str:
    if output_encoding == "hex":
        return blob.hex()
    return urlsafe_b64encode(blob).decode("utf-8")


def _decode_blob(token: str, *, output_encoding: str) -> bytes:
    if output_encoding == "hex":
        return bytes.fromhex(token)
    return urlsafe_b64decode(token.encode("utf-8"))


def run(context: dict[str, Any]) -> dict[str, Any]:
    config = resolve_crypto_config(context, crypto_kind="xor")
    operation = str(config.get("operation") or "encrypt")
    output_encoding = str(config.get("output_encoding") or "base64")
    rows, source_counts = collect_crypto_payloads(
        context,
        source_fields=list(config.get("source_fields", [])),
        max_items=int(config.get("max_items", 12)),
    )
    key_text = str(context.get("crypto_key") or "silica-x").strip() or "silica-x"
    key_bytes = key_text.encode("utf-8")

    payloads: list[str] = []
    failed = 0
    for row in rows:
        try:
            if operation == "decrypt":
                encoded = _decode_blob(row, output_encoding=output_encoding)
                payloads.append(_xor_bytes(encoded, key_bytes).decode("utf-8", errors="replace"))
            else:
                raw = _xor_bytes(row.encode("utf-8"), key_bytes)
                payloads.append(_encode_blob(raw, output_encoding=output_encoding))
        except Exception:
            failed += 1

    strict_mode = bool(config.get("strict_mode"))
    severity = "HIGH" if strict_mode and failed else ("WARN" if failed else "INFO")
    summary = f"XOR {operation}ed {len(payloads)} payload(s); failed={failed}."
    return {
        "severity": severity,
        "summary": summary,
        "highlights": [
            f"operation={operation}",
            f"encoding={output_encoding}",
            f"sources={','.join(config.get('source_fields', []))}",
            f"ok={len(payloads)}",
            f"failed={failed}",
        ],
        "data": {
            "crypto_kind": "xor",
            "operation": operation,
            "payloads": payloads,
            "key_length": len(key_bytes),
            "failed": failed,
            "payload_count": len(payloads),
            "source_summary": source_counts,
            "crypto_profile": config,
        },
    }
