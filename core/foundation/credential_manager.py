"""Credential/token manager with encrypted at-rest storage."""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass, field
import hashlib
import os
from typing import Callable

try:  # pragma: no cover - optional dependency
    from cryptography.fernet import Fernet, InvalidToken

    _HAS_FERNET = True
except Exception:  # pragma: no cover - optional dependency
    Fernet = None  # type: ignore[assignment]
    InvalidToken = Exception  # type: ignore[assignment]
    _HAS_FERNET = False


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
        if _HAS_FERNET:
            self._cipher = Fernet(self.key)
        else:
            self._cipher = _FallbackCipher(self.key)

    @staticmethod
    def generate_key() -> bytes:
        if _HAS_FERNET:
            return Fernet.generate_key()
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
        except (InvalidToken, UnicodeDecodeError):  # pragma: no cover - defensive guard
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
