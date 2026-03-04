"""Plugin: AES attachment encryption/decryption helper."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
import hashlib
import os
from typing import Any

from plugins.crypto._shared import collect_crypto_payloads, resolve_crypto_config


PLUGIN_SPEC = {
    "id": "crypto_aes_attachment",
    "title": "AES Attachment Cipher",
    "description": "Encrypts or decrypts attachment-like text payloads using AES-CFB.",
    "scopes": ["profile", "surface", "fusion"],
    "aliases": ["aes_plugin", "aes_crypto", "crypto_aes"],
    "version": "1.0",
}


def _derive_key(key_raw: object) -> bytes:
    if isinstance(key_raw, bytes) and key_raw:
        return hashlib.sha256(key_raw).digest()
    token = str(key_raw or "").strip()
    if token:
        try:
            return hashlib.sha256(urlsafe_b64decode(token.encode("utf-8"))).digest()
        except Exception:
            return hashlib.sha256(token.encode("utf-8")).digest()
    return os.urandom(32)


def _encode_ciphertext(blob: bytes, *, output_encoding: str) -> str:
    if output_encoding == "hex":
        return blob.hex()
    return urlsafe_b64encode(blob).decode("utf-8")


def _decode_ciphertext(token: str, *, output_encoding: str) -> bytes:
    if output_encoding == "hex":
        return bytes.fromhex(token)
    return urlsafe_b64decode(token.encode("utf-8"))


def _encrypt_rows(rows: list[str], key: bytes, *, output_encoding: str) -> list[str]:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    payloads: list[str] = []
    for row in rows:
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encrypted = cipher.encryptor().update(row.encode("utf-8"))
        payloads.append(_encode_ciphertext(iv + encrypted, output_encoding=output_encoding))
    return payloads


def _decrypt_rows(rows: list[str], key: bytes, *, output_encoding: str) -> tuple[list[str], int]:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    decrypted_rows: list[str] = []
    failed = 0
    for row in rows:
        try:
            blob = _decode_ciphertext(row, output_encoding=output_encoding)
            iv = blob[:16]
            encrypted = blob[16:]
            cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
            plaintext = cipher.decryptor().update(encrypted).decode("utf-8", errors="replace")
            decrypted_rows.append(plaintext)
        except Exception:
            failed += 1
    return decrypted_rows, failed


def run(context: dict[str, Any]) -> dict[str, Any]:
    config = resolve_crypto_config(context, crypto_kind="aes")
    operation = str(config.get("operation") or "encrypt")
    output_encoding = str(config.get("output_encoding") or "base64")
    rows, source_counts = collect_crypto_payloads(
        context,
        source_fields=list(config.get("source_fields", [])),
        max_items=int(config.get("max_items", 12)),
    )
    key = _derive_key(context.get("crypto_key"))

    try:
        if operation == "decrypt":
            payloads, failed = _decrypt_rows(rows, key, output_encoding=output_encoding)
            strict_mode = bool(config.get("strict_mode"))
            severity = "HIGH" if strict_mode and failed else ("WARN" if failed else "INFO")
            summary = f"AES decrypted {len(payloads)} payload(s); failed={failed}."
            highlights = [
                f"operation={operation}",
                f"encoding={output_encoding}",
                f"sources={','.join(config.get('source_fields', []))}",
                f"ok={len(payloads)}",
                f"failed={failed}",
            ]
        else:
            payloads = _encrypt_rows(rows, key, output_encoding=output_encoding)
            severity = "INFO"
            summary = f"AES encrypted {len(payloads)} payload(s)."
            highlights = [
                f"operation={operation}",
                f"encoding={output_encoding}",
                f"sources={','.join(config.get('source_fields', []))}",
                f"count={len(payloads)}",
            ]
            failed = 0
    except Exception as exc:
        return {
            "severity": "WARN",
            "summary": "AES plugin unavailable. Install `cryptography` for AES operations.",
            "highlights": [
                f"error={exc}",
                f"operation={operation}",
                f"encoding={output_encoding}",
            ],
            "data": {
                "crypto_kind": "aes",
                "operation": operation,
                "payloads": [],
                "crypto_profile": config,
                "source_summary": source_counts,
            },
        }

    return {
        "severity": severity,
        "summary": summary,
        "highlights": highlights,
        "data": {
            "crypto_kind": "aes",
            "operation": operation,
            "payloads": payloads,
            "key_hint": urlsafe_b64encode(hashlib.sha256(key).digest()[:12]).decode("utf-8"),
            "failed": failed,
            "payload_count": len(payloads),
            "source_summary": source_counts,
            "crypto_profile": config,
        },
    }
