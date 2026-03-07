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

"""Credential/token manager with encrypted at-rest storage."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass, field
import hashlib
import importlib
import os
from types import ModuleType
from typing import Callable, Protocol

try:  # pragma: no cover - optional dependency
    _fernet: ModuleType | None = importlib.import_module("cryptography.fernet")
except Exception:  # pragma: no cover - optional dependency
    _fernet = None

_HAS_FERNET = _fernet is not None
_INVALID_TOKEN_EXC: type[Exception] = _fernet.InvalidToken if _fernet is not None else ValueError


class _Cipher(Protocol):
    def encrypt(self, value: bytes) -> bytes: ...
    def decrypt(self, token: bytes) -> bytes: ...


def _normalize_key_material(key: bytes) -> bytes:
    if _HAS_FERNET:
        return key
    # Fallback mode uses deterministic hashing + XOR obfuscation.
    return hashlib.sha256(key).digest()


class _FallbackCipher:
    """Compatibility fallback when cryptography is unavailable.

    This is obfuscation-only and not equivalent to Fernet security guarantees.
    """

    def __init__(self, key: bytes) -> None:
        self.key = _normalize_key_material(key)

    def encrypt(self, value: bytes) -> bytes:
        nonce = os.urandom(16)
        stream = hashlib.sha256(self.key + nonce).digest()
        payload = bytes(byte ^ stream[i % len(stream)] for i, byte in enumerate(value))
        return urlsafe_b64encode(nonce + payload)

    def decrypt(self, token: bytes) -> bytes:
        raw = urlsafe_b64decode(token)
        nonce = raw[:16]
        payload = raw[16:]
        stream = hashlib.sha256(self.key + nonce).digest()
        return bytes(byte ^ stream[i % len(stream)] for i, byte in enumerate(payload))


@dataclass
class CredentialManager:
    """Stores service tokens and decrypts them on demand."""

    key: bytes
    tokens: dict[str, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if _fernet is not None:
            self._cipher: _Cipher = _fernet.Fernet(self.key)
        else:
            self._cipher = _FallbackCipher(self.key)

    @staticmethod
    def generate_key() -> bytes:
        if _fernet is not None:
            return _fernet.Fernet.generate_key()
        return urlsafe_b64encode(os.urandom(32))

    def store_token(self, service: str, token: str) -> None:
        service_key = service.strip().lower()
        if not service_key:
            raise ValueError("Service name is required.")
        if not token:
            raise ValueError("Token is required.")
        self.tokens[service_key] = self._cipher.encrypt(token.encode("utf-8"))

    def retrieve_token(self, service: str) -> str | None:
        service_key = service.strip().lower()
        encrypted = self.tokens.get(service_key)
        if encrypted is None:
            return None
        try:
            return self._cipher.decrypt(encrypted).decode("utf-8")
        except (_INVALID_TOKEN_EXC, UnicodeDecodeError):  # pragma: no cover - defensive guard
            return None

    def validate_token(
        self,
        service: str,
        validator: Callable[[str], bool] | None = None,
    ) -> bool:
        token = self.retrieve_token(service)
        if token is None:
            return False
        if validator is None:
            return bool(token.strip())
        try:
            return bool(validator(token))
        except Exception:  # pragma: no cover - external validator safety
            return False

    def rotate_token(self, service: str, new_token: str) -> None:
        self.store_token(service, new_token)

    def remove_token(self, service: str) -> bool:
        service_key = service.strip().lower()
        return self.tokens.pop(service_key, None) is not None

    def list_services(self) -> list[str]:
        return sorted(self.tokens.keys())
