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

"""Docker runtime manager for Silica-X.

Handles Docker detection, installation, image management, and container
launch for the --docker flag. Works on Linux (apt/dnf/pacman), macOS
(Homebrew or Docker Desktop), and Windows (winget or direct installer).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any


DOCKER_INSTALL_URLS: dict[str, str] = {
    "windows": "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe",
    "darwin": "https://desktop.docker.com/mac/main/amd64/Docker.dmg",
}

SILICA_X_IMAGE_NAME = "silica-x"
SILICA_X_IMAGE_TAG = "latest"
SILICA_X_IMAGE = f"{SILICA_X_IMAGE_NAME}:{SILICA_X_IMAGE_TAG}"

DOCKER_COMPOSE_RELATIVE = "docker/docker-compose.yml"
DOCKERFILE_RELATIVE = "docker/Dockerfile"


def detect_os() -> str:
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "darwin"
    if system == "windows":
        return "windows"
    return "unknown"


def detect_linux_distro() -> str:
    try:
        text = Path("/etc/os-release").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("ID="):
                return line.split("=", 1)[1].strip().strip('"').lower()
    except OSError:
        pass
    return ""


def detect_linux_package_manager() -> str:
    for package_manager in ("apt-get", "dnf", "yum", "pacman", "zypper"):
        if shutil.which(package_manager):
            return package_manager
    return ""


def find_docker_binary() -> str | None:
    return shutil.which("docker")


def find_docker_compose_binary() -> str | None:
    docker = find_docker_binary()
    if docker:
        try:
            result = subprocess.run(
                [docker, "compose", "version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return docker
        except Exception:
            pass
    return shutil.which("docker-compose")


def docker_daemon_running() -> bool:
    binary = find_docker_binary()
    if not binary:
        return False
    try:
        result = subprocess.run(
            [binary, "info"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def docker_image_exists(image: str = SILICA_X_IMAGE) -> bool:
    binary = find_docker_binary()
    if not binary:
        return False
    try:
        result = subprocess.run(
            [binary, "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def docker_status() -> dict[str, Any]:
    binary = find_docker_binary()
    compose = find_docker_compose_binary()
    running = docker_daemon_running() if binary else False
    image_built = docker_image_exists() if running else False
    os_name = detect_os()
    return {
        "os": os_name,
        "binary_found": binary is not None,
        "binary_path": binary,
        "compose_found": compose is not None,
        "daemon_running": running,
        "image_built": image_built,
        "image_name": SILICA_X_IMAGE,
    }


def _prompt_yes_no(question: str) -> bool:
    while True:
        try:
            answer = input(f"{question} (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False


def install_docker(*, prompt_user: bool = True) -> tuple[bool, str]:
    os_name = detect_os()
    if prompt_user:
        if not _prompt_yes_no(
            f"[Silica-X] Docker is not installed. Install Docker automatically on {os_name}?"
        ):
            return False, "Docker installation declined by user."
    print("[Silica-X] Installing Docker...")
    if os_name == "linux":
        return _install_docker_linux()
    if os_name == "darwin":
        return _install_docker_macos()
    if os_name == "windows":
        return _install_docker_windows()
    return (
        False,
        f"Unsupported OS for automatic Docker install: {os_name}. Install Docker manually from https://docs.docker.com/get-docker/",
    )


def _install_docker_linux() -> tuple[bool, str]:
    curl = shutil.which("curl")
    if curl:
        try:
            print("[Silica-X] Downloading Docker install script...")
            result = subprocess.run(
                "curl -fsSL https://get.docker.com | sh",
                shell=True,
                check=False,
                timeout=300,
            )
            if result.returncode == 0:
                username = os.environ.get("USER", "")
                if username:
                    subprocess.run(
                        ["usermod", "-aG", "docker", username],
                        check=False,
                        capture_output=True,
                    )
                return True, "Docker installed via get.docker.com script."
        except Exception:
            pass
    package_manager = detect_linux_package_manager()
    try:
        if package_manager == "apt-get":
            subprocess.run(["apt-get", "install", "-y", "docker.io"], check=True, timeout=180)
            return True, "Docker installed via apt-get."
        if package_manager in ("dnf", "yum"):
            subprocess.run([package_manager, "install", "-y", "docker"], check=True, timeout=180)
            subprocess.run(["systemctl", "enable", "--now", "docker"], check=False, timeout=30)
            return True, f"Docker installed via {package_manager}."
        if package_manager == "pacman":
            subprocess.run(["pacman", "-S", "--noconfirm", "docker"], check=True, timeout=180)
            subprocess.run(["systemctl", "enable", "--now", "docker"], check=False, timeout=30)
            return True, "Docker installed via pacman."
    except subprocess.CalledProcessError as exc:
        return False, f"Package manager install failed: {exc}"
    except Exception as exc:
        return False, f"Linux Docker install failed: {exc}"
    return False, "No supported package manager found. Install Docker manually: https://docs.docker.com/engine/install/"


def _install_docker_macos() -> tuple[bool, str]:
    brew = shutil.which("brew")
    if brew:
        try:
            print("[Silica-X] Installing Docker Desktop via Homebrew...")
            result = subprocess.run([brew, "install", "--cask", "docker"], check=False, timeout=300)
            if result.returncode == 0:
                return True, "Docker Desktop installed via Homebrew. Open Docker Desktop app to start the daemon."
        except Exception as exc:
            return False, f"Homebrew Docker install failed: {exc}"
    return False, "Homebrew not found. Install Docker Desktop manually from https://docs.docker.com/desktop/install/mac-install/"


def _install_docker_windows() -> tuple[bool, str]:
    winget = shutil.which("winget")
    if winget:
        try:
            print("[Silica-X] Installing Docker Desktop via winget...")
            result = subprocess.run(
                [winget, "install", "--id", "Docker.DockerDesktop", "-e", "--silent"],
                check=False,
                timeout=600,
            )
            if result.returncode == 0:
                return True, "Docker Desktop installed via winget. Restart may be required."
        except Exception:
            pass
    try:
        print("[Silica-X] Downloading Docker Desktop installer...")
        url = DOCKER_INSTALL_URLS["windows"]
        tmp_path = os.path.join(tempfile.gettempdir(), "DockerDesktopInstaller.exe")

        def _progress(count: int, block_size: int, total: int) -> None:
            if total > 0:
                pct = min(100, int(count * block_size * 100 / total))
                print(f"\r  Downloading... {pct}%", end="", flush=True)

        urllib.request.urlretrieve(url, tmp_path, _progress)
        print()
        result = subprocess.run([tmp_path, "install", "--quiet"], check=False, timeout=600)
        if result.returncode == 0:
            return True, "Docker Desktop installed. Restart your system to complete setup."
        return False, f"Installer exited with code {result.returncode}."
    except Exception as exc:
        return False, f"Windows Docker install failed: {exc}"


def ensure_daemon_running(*, prompt_user: bool = True) -> tuple[bool, str]:
    _ = prompt_user
    if docker_daemon_running():
        return True, "Docker daemon is already running."
    os_name = detect_os()
    print("[Silica-X] Docker daemon is not running.")
    if os_name == "linux":
        try:
            result = subprocess.run(["systemctl", "start", "docker"], check=False, capture_output=True, timeout=30)
            if result.returncode == 0 and docker_daemon_running():
                return True, "Docker daemon started via systemctl."
            result = subprocess.run(["service", "docker", "start"], check=False, capture_output=True, timeout=30)
            if result.returncode == 0 and docker_daemon_running():
                return True, "Docker daemon started via service command."
        except Exception as exc:
            return False, f"Failed to start Docker daemon: {exc}"
        return False, "Docker daemon could not be started. Run: sudo systemctl start docker"
    if os_name == "darwin":
        try:
            subprocess.run(["open", "-a", "Docker"], check=False, timeout=10)
            print("[Silica-X] Opening Docker Desktop... waiting up to 30 seconds.")
            import time

            for _ in range(15):
                time.sleep(2)
                if docker_daemon_running():
                    return True, "Docker Desktop started."
        except Exception:
            pass
        return False, "Docker Desktop did not start in time. Open Docker Desktop manually."
    if os_name == "windows":
        try:
            subprocess.run(["C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"], check=False, timeout=10)
            print("[Silica-X] Starting Docker Desktop... waiting up to 30 seconds.")
            import time

            for _ in range(15):
                time.sleep(2)
                if docker_daemon_running():
                    return True, "Docker Desktop started."
        except Exception:
            pass
        return False, "Docker Desktop did not start in time. Start Docker Desktop manually."
    return False, "Cannot start Docker daemon on this OS automatically."


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists() and (parent / "core").is_dir():
            return parent
    return Path.cwd()


def build_image(*, force_rebuild: bool = False) -> tuple[bool, str]:
    binary = find_docker_binary()
    if not binary:
        return False, "Docker binary not found."
    if not force_rebuild and docker_image_exists():
        return True, f"Image {SILICA_X_IMAGE} already exists. Use force_rebuild=True to rebuild."
    repo_root = _find_repo_root()
    dockerfile = repo_root / DOCKERFILE_RELATIVE
    if not dockerfile.exists():
        return False, f"Dockerfile not found at {dockerfile}."
    print(f"[Silica-X] Building Docker image {SILICA_X_IMAGE}...")
    print(f"[Silica-X] Build context: {repo_root}")
    print(f"[Silica-X] Dockerfile: {dockerfile}")
    print("[Silica-X] This may take several minutes on first build...")
    try:
        result = subprocess.run(
            [binary, "build", "-f", str(dockerfile), "-t", SILICA_X_IMAGE, str(repo_root)],
            check=False,
            timeout=900,
        )
        if result.returncode == 0:
            return True, f"Image {SILICA_X_IMAGE} built successfully."
        return False, f"Docker build failed with exit code {result.returncode}."
    except subprocess.TimeoutExpired:
        return False, "Docker build timed out after 15 minutes."
    except Exception as exc:
        return False, f"Docker build error: {exc}"


def launch_container(
    command: list[str],
    *,
    use_tor: bool = False,
    use_proxy: bool = False,
    interactive: bool = True,
    port_map: dict[int, int] | None = None,
    extra_env: dict[str, str] | None = None,
) -> int:
    binary = find_docker_binary()
    if not binary:
        print("[Silica-X] Docker binary not found. Cannot launch container.")
        return 1
    repo_root = _find_repo_root()
    output_dir = repo_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    env_vars: dict[str, str] = {"SILICA_X_DOCKER": "1"}
    if use_tor:
        env_vars["SILICA_X_TOR"] = "1"
    if use_proxy:
        env_vars["SILICA_X_PROXY"] = "1"
    if extra_env:
        env_vars.update(extra_env)
    docker_cmd = [binary, "run", "--rm"]
    if interactive:
        docker_cmd += ["-it"]
    docker_cmd += ["-v", f"{output_dir}:/app/output"]
    for key, value in env_vars.items():
        docker_cmd += ["-e", f"{key}={value}"]
    for host_port, container_port in (port_map or {}).items():
        docker_cmd += ["-p", f"{host_port}:{container_port}"]
    if use_tor:
        docker_cmd += ["--entrypoint", "/bin/bash"]
        docker_cmd += [SILICA_X_IMAGE]
        tor_command = " ".join(["silica-x"] + command)
        docker_cmd += ["-c", f"service tor start && sleep 2 && {tor_command}"]
    else:
        docker_cmd += [SILICA_X_IMAGE]
        docker_cmd += command
    try:
        result = subprocess.run(docker_cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n[Silica-X] Container interrupted.")
        return 130
    except Exception as exc:
        print(f"[Silica-X] Container launch failed: {exc}")
        return 1


def ensure_docker_ready(*, prompt_user: bool = True) -> tuple[bool, str]:
    binary = find_docker_binary()
    if binary is None:
        ok, msg = install_docker(prompt_user=prompt_user)
        if not ok:
            return False, msg
        binary = find_docker_binary()
        if binary is None:
            return False, "Docker install completed but binary still not found. Restart your terminal."
    ok, msg = ensure_daemon_running(prompt_user=prompt_user)
    if not ok:
        return False, msg
    if not docker_image_exists():
        print(f"[Silica-X] Image {SILICA_X_IMAGE} not found locally. Building now...")
        ok, msg = build_image()
        if not ok:
            return False, f"Image build failed: {msg}"
        print(f"[Silica-X] {msg}")
    return True, "Docker is ready."
