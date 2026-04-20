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

"""Tests for Tor runtime manager."""

from core.setup.tor_runtime import (
    TOR_SOCKS_HOST,
    TOR_SOCKS_PORT,
    detect_os,
    find_torrc,
    tor_full_status,
)


def test_detect_os_returns_known_value() -> None:
    result = detect_os()
    assert result in {"linux", "darwin", "windows", "unknown"}


def test_find_torrc_returns_path_or_none() -> None:
    result = find_torrc()
    assert result is None or hasattr(result, "exists")


def test_tor_full_status_has_required_keys() -> None:
    status = tor_full_status()
    for key in ["binary_found", "socks_reachable", "socks_host", "socks_port", "os_name"]:
        assert key in status, f"Missing key: {key}"


def test_tor_full_status_socks_host_correct() -> None:
    status = tor_full_status()
    assert status["socks_host"] == TOR_SOCKS_HOST


def test_tor_full_status_socks_port_correct() -> None:
    status = tor_full_status()
    assert status["socks_port"] == TOR_SOCKS_PORT


def test_tor_full_status_returns_bool_for_binary_found() -> None:
    status = tor_full_status()
    assert isinstance(status["binary_found"], bool)


def test_tor_full_status_returns_bool_for_socks_reachable() -> None:
    status = tor_full_status()
    assert isinstance(status["socks_reachable"], bool)
