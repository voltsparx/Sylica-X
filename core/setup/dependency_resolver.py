"""Automatic startup dependency resolver for the Tesseract OCR binary."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request

MANUAL_TESSERACT_URL = "https://github.com/tesseract-ocr/tesseract"
WINDOWS_TESSERACT_URL = (
    "https://digi.bib.uni-mannheim.de/tesseract/"
    "tesseract-ocr-w64-setup-5.3.3.20231005.exe"
)
WINDOWS_INSTALL_DIR = r"C:\Program Files\Tesseract-OCR"
WINDOWS_INSTALL_PATH_ENTRY = WINDOWS_INSTALL_DIR


def _read_os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                data[key] = value
    except OSError:
        return {}
    return data


def _run_install_command(command: list[str]) -> bool:
    try:
        subprocess.run(command, check=True)
    except Exception as exc:
        print(f"[Silica-X] Automatic install failed: {exc}. Please install tesseract manually.")
        return False
    return True


def _print_manual_linux_message() -> None:
    print(
        "[Silica-X] Unsupported Linux distribution. Please install tesseract-ocr manually: "
        f"{MANUAL_TESSERACT_URL}"
    )


def _install_linux() -> bool:
    os_release = _read_os_release()
    distro_id = os_release.get("ID", "").lower()
    distro_like = os_release.get("ID_LIKE", "").lower()

    if distro_id in {"ubuntu", "debian"} or "ubuntu" in distro_like or "debian" in distro_like:
        return _run_install_command(["sudo", "apt-get", "install", "-y", "tesseract-ocr"])
    if distro_id == "fedora" or "fedora" in distro_like:
        return _run_install_command(["sudo", "dnf", "install", "-y", "tesseract"])
    if distro_id == "arch" or "arch" in distro_like:
        return _run_install_command(["sudo", "pacman", "-S", "--noconfirm", "tesseract"])

    _print_manual_linux_message()
    return False


def _install_macos() -> bool:
    if shutil.which("brew") is None:
        print(f"[Silica-X] Homebrew is required to install tesseract automatically: https://brew.sh")
        return False
    return _run_install_command(["brew", "install", "tesseract"])


def _download_progress(block_count: int, block_size: int, total_size: int) -> None:
    if total_size <= 0:
        print("[Silica-X] Downloading Tesseract installer...", flush=True)
        return
    downloaded = min(block_count * block_size, total_size)
    percent = int((downloaded / total_size) * 100)
    print(f"\r[Silica-X] Downloading Tesseract installer... {percent}%", end="", flush=True)
    if downloaded >= total_size:
        print("", flush=True)


def _install_windows() -> bool:
    installer_fd, installer_path = tempfile.mkstemp(suffix=".exe")
    os.close(installer_fd)
    try:
        urllib.request.urlretrieve(WINDOWS_TESSERACT_URL, installer_path, _download_progress)
        if os.path.exists(installer_path):
            print("", flush=True)
    except Exception as exc:
        print(f"[Silica-X] Automatic install failed: {exc}. Please install tesseract manually.")
        try:
            if os.path.exists(installer_path):
                os.remove(installer_path)
        except OSError:
            pass
        return False

    try:
        completed = _run_install_command([installer_path, "/S", f"/D={WINDOWS_INSTALL_DIR}"])
        if completed:
            current_path = os.environ.get("PATH", "")
            path_entries = current_path.split(os.pathsep) if current_path else []
            if WINDOWS_INSTALL_PATH_ENTRY not in path_entries:
                os.environ["PATH"] = (
                    f"{WINDOWS_INSTALL_PATH_ENTRY}{os.pathsep}{current_path}"
                    if current_path
                    else WINDOWS_INSTALL_PATH_ENTRY
                )
        return completed
    finally:
        try:
            if os.path.exists(installer_path):
                os.remove(installer_path)
        except OSError:
            pass


def resolve_tesseract() -> None:
    if shutil.which("tesseract") is not None:
        return

    print("[Silica-X] Tesseract OCR binary not found. Install it automatically? (y/n): ", end="", flush=True)
    try:
        response = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("")
        response = ""

    if response not in {"y", "yes"}:
        print("[Silica-X] Skipping tesseract install. OCR features will be unavailable.")
        return

    system_name = platform.system()
    installed = False

    if system_name == "Linux":
        installed = _install_linux()
    elif system_name == "Darwin":
        installed = _install_macos()
    elif system_name == "Windows":
        installed = _install_windows()
    else:
        print(f"[Silica-X] Unsupported operating system. Please install tesseract manually: {MANUAL_TESSERACT_URL}")
        return

    if not installed:
        return

    if shutil.which("tesseract") is not None:
        print("[Silica-X] Tesseract installed and verified successfully.")
        return

    print(
        "[Silica-X] Install completed but tesseract is still not on PATH. "
        "You may need to restart your terminal or add it to PATH manually."
    )
