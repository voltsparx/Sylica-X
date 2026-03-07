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

"""Security and privacy helpers for runtime hardening."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
import hashlib
import importlib
import os
from pathlib import Path
from types import ModuleType
from typing import Any

try:  # pragma: no cover - optional dependency
    _fernet: ModuleType | None = importlib.import_module("cryptography.fernet")
except Exception:  # pragma: no cover - optional dependency
    _fernet = None

_HAS_FERNET = _fernet is not None


def _fallback_encrypt_bytes(data: bytes, key: bytes) -> bytes:
    nonce = os.urandom(16)
    stream = hashlib.sha256(key + nonce).digest()
    payload = bytes(byte ^ stream[i % len(stream)] for i, byte in enumerate(data))
    return nonce + payload


def _fallback_decrypt_bytes(data: bytes, key: bytes) -> bytes:
    nonce = data[:16]
    payload = data[16:]
    stream = hashlib.sha256(key + nonce).digest()
    return bytes(byte ^ stream[i % len(stream)] for i, byte in enumerate(payload))


@dataclass
class SecurityManager:
    """Security utility entrypoint for Tor/routing/encryption workflows."""

    def setup_tor_chain(self, hops: int = 2) -> dict[str, Any]:
        hop_count = max(1, int(hops))
        chain = [f"socks5h://127.0.0.1:{9050 + index}" for index in range(hop_count)]
        return {"enabled": True, "hops": hop_count, "chain": chain}

    def generate_key(self) -> bytes:
        if _fernet is not None:
            return _fernet.Fernet.generate_key()
        return urlsafe_b64encode(os.urandom(32))

    def encrypt_output(self, file_path: str, key: bytes | None = None) -> str:
        source = Path(file_path)
        if not source.exists():
            raise FileNotFoundError(f"Output file not found: {source}")

        payload = source.read_bytes()
        key_material = key or self.generate_key()
        encrypted_path = source.with_suffix(source.suffix + ".enc")

        if _fernet is not None:
            encrypted = _fernet.Fernet(key_material).encrypt(payload)
        else:
            hashed = hashlib.sha256(key_material).digest()
            encrypted = urlsafe_b64encode(_fallback_encrypt_bytes(payload, hashed))

        encrypted_path.write_bytes(encrypted)
        return str(encrypted_path)

    def decrypt_output(self, file_path: str, key: bytes) -> bytes:
        encrypted_path = Path(file_path)
        encrypted = encrypted_path.read_bytes()
        if _fernet is not None:
            return _fernet.Fernet(key).decrypt(encrypted)
        hashed = hashlib.sha256(key).digest()
        return _fallback_decrypt_bytes(urlsafe_b64decode(encrypted), hashed)

    def sandbox_plugin(self, plugin: str | dict[str, Any]) -> dict[str, Any]:
        plugin_name = plugin if isinstance(plugin, str) else str(plugin.get("id") or plugin.get("name") or "plugin")
        return {
            "plugin": plugin_name,
            "allow_network": False,
            "allow_filesystem_write": False,
            "allow_subprocess": False,
            "status": "sandbox_profile_generated",
        }
