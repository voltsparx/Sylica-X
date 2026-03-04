"""Console symbol helpers with Unicode-safe fallbacks."""

from __future__ import annotations

import sys


def _supports_unicode_stdout() -> bool:
    encoding = str(getattr(sys.stdout, "encoding", "") or "").lower()
    return "utf" in encoding


_UNICODE_SYMBOLS: dict[str, str] = {
    "bullet": "[•]",
    "action": "[→]",
    "ok": "[✓]",
    "error": "[✗]",
    "tip": "[★]",
    "feature": "[✦]",
    "warn": "[!]",
    "major": "[═]",
    "minor": "[─]",
}

_ASCII_SYMBOLS: dict[str, str] = {
    "bullet": "[*]",
    "action": "[>]",
    "ok": "[+]",
    "error": "[x]",
    "tip": "[i]",
    "feature": "[*]",
    "warn": "[!]",
    "major": "[=]",
    "minor": "[-]",
}


def symbol(name: str) -> str:
    """Return a console symbol by logical key."""

    key = str(name or "").strip().lower()
    mapping = _UNICODE_SYMBOLS if _supports_unicode_stdout() else _ASCII_SYMBOLS
    return mapping.get(key, f"[{key}]")

