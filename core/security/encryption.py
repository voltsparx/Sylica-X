"""Lightweight encryption helpers for secure credential operations."""

from __future__ import annotations

import hashlib
import os


def derive_secret_key(secret: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Derive deterministic 32-byte key material from a secret."""

    use_salt = salt or os.urandom(16)
    material = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        use_salt,
        120_000,
        dklen=32,
    )
    return material, use_salt
