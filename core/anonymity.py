"""Tor detection, installation guidance, and startup orchestration."""

from __future__ import annotations

import platform
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


TOR_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050
SUPPORTED_INSTALL_OS = {"Windows", "Linux"}
STARTUP_WAIT_SECONDS = 12.0

WINDOWS_TOR_CANDIDATES = (
    Path(r"C:\Program Files\Tor Browser\Browser\TorBrowser\Tor\tor.exe"),
    Path(r"C:\Program Files (x86)\Tor Browser\Browser\TorBrowser\Tor\tor.exe"),
    Path(r"C:\Tor\tor.exe"),
)


@dataclass(frozen=True)
class TorStatus:
    os_name: str
    binary_found: bool
    binary_path: str | None
    socks_reachable: bool
    install_supported: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def supported_os(self) -> bool:
        return self.os_name in SUPPORTED_INSTALL_OS


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _detect_tor_binary(os_name: str) -> tuple[bool, str | None, list[str]]:
    notes: list[str] = []
    found = shutil.which("tor")
    if found:
        return True, found, notes

    if os_name == "Windows":
        for candidate in WINDOWS_TOR_CANDIDATES:
            if candidate.exists():
                return True, str(candidate), notes
        notes.append("Tor binary not found in PATH or common Tor Browser locations.")
    elif os_name == "Linux":
        notes.append("Tor binary not found in PATH. Try installing package 'tor'.")
    else:
        notes.append("This OS is not auto-managed for Tor install/start.")

    return False, None, notes


def probe_tor_status() -> TorStatus:
    os_name = platform.system() or "Unknown"
    binary_found, binary_path, notes = _detect_tor_binary(os_name)
    socks_reachable = _is_port_open(TOR_HOST, TOR_SOCKS_PORT)
    if socks_reachable:
        notes.append(f"Tor SOCKS endpoint reachable at {TOR_HOST}:{TOR_SOCKS_PORT}.")
    else:
        notes.append(f"Tor SOCKS endpoint not reachable at {TOR_HOST}:{TOR_SOCKS_PORT}.")

    return TorStatus(
        os_name=os_name,
        binary_found=binary_found,
        binary_path=binary_path,
        socks_reachable=socks_reachable,
        install_supported=os_name in SUPPORTED_INSTALL_OS,
        notes=tuple(notes),
    )


def _run_install_command(commands: list[list[str]]) -> tuple[bool, str]:
    failures: list[str] = []
    for command in commands:
        try:
            proc = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            failures.append(f"command not found: {' '.join(command)}")
            continue
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(f"{' '.join(command)} failed: {exc}")
            continue

        if proc.returncode == 0:
            return True, f"success: {' '.join(command)}"
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        reason = stderr or stdout or f"exit={proc.returncode}"
        failures.append(f"{' '.join(command)} -> {reason}")

    return False, "; ".join(failures) or "all install commands failed"


def install_tor() -> tuple[bool, str]:
    os_name = platform.system() or "Unknown"
    if os_name == "Windows":
        commands = [
            ["winget", "install", "-e", "--id", "TorProject.TorBrowser", "--silent"],
        ]
        return _run_install_command(commands)

    if os_name == "Linux":
        if shutil.which("apt-get"):
            commands = [["sudo", "apt-get", "install", "-y", "tor"]]
        elif shutil.which("dnf"):
            commands = [["sudo", "dnf", "install", "-y", "tor"]]
        elif shutil.which("pacman"):
            commands = [["sudo", "pacman", "-Sy", "--noconfirm", "tor"]]
        elif shutil.which("zypper"):
            commands = [["sudo", "zypper", "--non-interactive", "install", "tor"]]
        else:
            return False, "No supported Linux package manager detected (apt/dnf/pacman/zypper)."
        return _run_install_command(commands)

    return False, f"Automatic install is unsupported on {os_name}."


def _start_with_system_services(os_name: str) -> tuple[bool, str]:
    if os_name == "Linux":
        commands = [
            ["sudo", "systemctl", "start", "tor"],
            ["systemctl", "--user", "start", "tor"],
            ["sudo", "service", "tor", "start"],
            ["service", "tor", "start"],
        ]
    elif os_name == "Windows":
        # Common service name installed by Expert Bundle.
        commands = [
            ["sc", "start", "tor"],
        ]
    else:
        return False, f"Service startup unsupported on {os_name}."

    return _run_install_command(commands)


def _spawn_tor_binary(binary_path: str) -> tuple[bool, str]:
    command = [binary_path]
    if platform.system() == "Windows":
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
        try:
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            return True, f"spawned process: {' '.join(command)}"
        except Exception as exc:  # pragma: no cover - defensive
            return False, str(exc)

    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, f"spawned process: {' '.join(command)}"
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)


def wait_for_tor(timeout_seconds: float = STARTUP_WAIT_SECONDS) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _is_port_open(TOR_HOST, TOR_SOCKS_PORT, timeout=0.8):
            return True
        time.sleep(0.5)
    return False


def start_tor(binary_path: str | None = None) -> tuple[bool, str]:
    if _is_port_open(TOR_HOST, TOR_SOCKS_PORT):
        return True, f"Tor already running on {TOR_HOST}:{TOR_SOCKS_PORT}."

    os_name = platform.system() or "Unknown"
    service_ok, service_msg = _start_with_system_services(os_name)
    if service_ok and wait_for_tor():
        return True, f"Tor started via service manager ({service_msg})."

    candidate = binary_path or shutil.which("tor")
    if not candidate and os_name == "Windows":
        for path in WINDOWS_TOR_CANDIDATES:
            if path.exists():
                candidate = str(path)
                break

    if not candidate:
        return False, f"Tor start failed; no tor binary found. Service attempt: {service_msg}"

    spawn_ok, spawn_msg = _spawn_tor_binary(candidate)
    if not spawn_ok:
        return False, f"Tor start failed via binary: {spawn_msg}"
    if wait_for_tor():
        return True, f"Tor started via binary ({spawn_msg})."
    return False, "Tor process launched but SOCKS endpoint did not become reachable."
