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

"""Tor runtime manager for Silica-X.

Provides OS-aware Tor installation, configuration deployment,
and service lifecycle management. Wraps core/collect/anonymity.py
for higher-level orchestration.
"""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any


TOR_CONFIG_RELATIVE = "docker/torrc.silica_x"
TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050


def detect_os() -> str:
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "darwin"
    if system == "windows":
        return "windows"
    return "unknown"


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def find_torrc() -> Path | None:
    repo_root = _find_repo_root()
    candidate = repo_root / TOR_CONFIG_RELATIVE
    if candidate.exists():
        return candidate
    return None


def deploy_torrc(destination: str | None = None) -> tuple[bool, str]:
    torrc = find_torrc()
    if torrc is None:
        return False, f"Silica-X torrc not found at {TOR_CONFIG_RELATIVE}."
    if destination is None:
        os_name = detect_os()
        if os_name == "linux":
            destination = "/etc/tor/torrc"
        elif os_name == "darwin":
            destination = "/usr/local/etc/tor/torrc"
        elif os_name == "windows":
            destination = r"C:\Users\Public\tor\torrc"
        else:
            return False, "Cannot determine torrc destination for this OS."
    try:
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil as _shutil

        _shutil.copy2(str(torrc), str(dest_path))
        return True, f"torrc deployed to {destination}."
    except PermissionError:
        return False, f"Permission denied writing to {destination}. Try running with sudo."
    except Exception as exc:
        return False, f"Failed to deploy torrc: {exc}"


def install_tor(*, prompt_user: bool = True) -> tuple[bool, str]:
    from core.collect.anonymity import install_tor as _install_tor

    if prompt_user:
        try:
            answer = input("[Silica-X] Tor is not installed. Install Tor automatically? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False, "Tor installation declined."
        if answer not in {"y", "yes"}:
            return False, "Tor installation declined by user."
    return _install_tor()


def tor_full_status() -> dict[str, Any]:
    from core.collect.anonymity import probe_tor_status

    status = probe_tor_status()
    torrc = find_torrc()
    return {
        "binary_found": status.binary_found,
        "binary_path": status.binary_path,
        "socks_reachable": status.socks_reachable,
        "socks_host": TOR_SOCKS_HOST,
        "socks_port": TOR_SOCKS_PORT,
        "install_supported": status.install_supported,
        "os_name": status.os_name,
        "silica_x_torrc": str(torrc) if torrc else None,
        "notes": list(status.notes),
    }


def ensure_tor_ready(*, prompt_user: bool = True) -> tuple[bool, str]:
    from core.collect.anonymity import probe_tor_status, start_tor

    status = probe_tor_status()
    if not status.binary_found:
        ok, msg = install_tor(prompt_user=prompt_user)
        if not ok:
            return False, msg
        status = probe_tor_status()
        if not status.binary_found:
            return False, "Tor installed but binary still not found. Restart terminal."
    if status.socks_reachable:
        return True, "Tor is already running."
    print("[Silica-X] Starting Tor...")
    ok, msg = start_tor(status.binary_path)
    if not ok:
        return False, f"Failed to start Tor: {msg}"
    status = probe_tor_status()
    if not status.socks_reachable:
        return False, "Tor started but SOCKS endpoint is not reachable."
    return True, "Tor is running."
