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

"""Tests for Docker runtime manager."""

from unittest.mock import patch

from core.setup.docker_runtime import (
    SILICA_X_IMAGE,
    detect_linux_distro,
    detect_linux_package_manager,
    detect_os,
    docker_daemon_running,
    docker_image_exists,
    docker_status,
    find_docker_binary,
)


def test_detect_os_returns_known_value() -> None:
    result = detect_os()
    assert result in {"linux", "darwin", "windows", "unknown"}


def test_detect_linux_distro_returns_string() -> None:
    result = detect_linux_distro()
    assert isinstance(result, str)


def test_detect_linux_package_manager_returns_string() -> None:
    result = detect_linux_package_manager()
    assert isinstance(result, str)


def test_find_docker_binary_returns_none_or_string() -> None:
    result = find_docker_binary()
    assert result is None or isinstance(result, str)


def test_docker_status_has_required_keys() -> None:
    status = docker_status()
    for key in ["os", "binary_found", "daemon_running", "image_built", "image_name"]:
        assert key in status, f"Missing key: {key}"


def test_docker_status_image_name_is_correct() -> None:
    status = docker_status()
    assert status["image_name"] == SILICA_X_IMAGE


def test_docker_daemon_running_returns_bool() -> None:
    result = docker_daemon_running()
    assert isinstance(result, bool)


def test_docker_image_exists_returns_bool() -> None:
    result = docker_image_exists()
    assert isinstance(result, bool)


@patch("core.setup.docker_runtime.find_docker_binary", return_value=None)
def test_docker_status_binary_not_found(mock_binary: object) -> None:
    _ = mock_binary
    status = docker_status()
    assert status["binary_found"] is False
    assert status["daemon_running"] is False


@patch("core.setup.docker_runtime.find_docker_binary", return_value="/usr/bin/docker")
@patch("core.setup.docker_runtime.docker_daemon_running", return_value=False)
def test_docker_status_daemon_not_running(mock_daemon: object, mock_binary: object) -> None:
    _ = (mock_daemon, mock_binary)
    status = docker_status()
    assert status["binary_found"] is True
    assert status["daemon_running"] is False
