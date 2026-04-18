#!/usr/bin/env python3

"""Offline-friendly smoke suite for core Silica-X command surfaces."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def _run(label: str, args: list[str], *, expect: int = 0) -> subprocess.CompletedProcess[str]:
    print(f"[smoke] {label}: {' '.join(args)}")
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    combined = f"{result.stdout}\n{result.stderr}".strip()
    if "Traceback" in combined:
        raise RuntimeError(f"{label} produced a traceback:\n{combined}")
    if result.returncode != expect:
        raise RuntimeError(
            f"{label} returned {result.returncode}, expected {expect}.\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def _make_ocr_fixture(path: Path) -> None:
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(f"Pillow is required for the OCR smoke fixture: {exc}") from exc

    image = Image.new("RGB", (860, 260), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 50), "Silica-X Smoke", fill="black")
    draw.text((30, 110), "mail: smoke@example.com", fill="black")
    draw.text((30, 170), "url: https://example.com", fill="black")
    image.save(path)


def _assert_any_files(root: Path, pattern: str, label: str) -> None:
    matches = list(root.rglob(pattern))
    if not matches:
        raise RuntimeError(f"{label} expected at least one artifact matching {pattern} under {root}")


def main() -> int:
    smoke_root = Path(tempfile.mkdtemp(prefix="silica-x-smoke-"))
    try:
        artifact_root = smoke_root / "artifacts"
        ocr_fixture = smoke_root / "ocr-smoke.png"
        _make_ocr_fixture(ocr_fixture)

        basic_commands = [
            ("about", [PYTHON, "silica-x.py", "--about"], 0),
            ("doctor", [PYTHON, "silica-x.py", "doctor", "--json"], 0),
            ("module-entrypoint-about", [PYTHON, "-m", "silica_x", "--about"], 0),
            ("plugin-inventory", [PYTHON, "silica-x.py", "plugins", "--scope", "ocr"], 0),
            ("filter-inventory", [PYTHON, "silica-x.py", "filters", "--scope", "fusion"], 0),
            ("module-inventory", [PYTHON, "silica-x.py", "modules", "--scope", "surface", "--limit", "2"], 0),
            ("framework-inventory", [PYTHON, "silica-x.py", "frameworks", "--framework", "recursive-modules", "--limit", "2"], 0),
            ("surface-kit-dry-run", [PYTHON, "silica-x.py", "surface-kit", "example.com", "--preset", "subdomain-enum", "--dry-run"], 0),
            ("invalid-command", [PYTHON, "silica-x.py", "bogus"], 2),
            ("ocr-no-source", [PYTHON, "silica-x.py", "ocr"], 2),
        ]
        for label, args, code in basic_commands:
            _run(label, args, expect=code)

        quicktest_dir = artifact_root / "quicktest"
        quicktest_dir.mkdir(parents=True, exist_ok=True)
        _run(
            "quicktest-rich-artifacts",
            [
                PYTHON,
                "silica-x.py",
                "quicktest",
                "--template",
                "atlas-mercier",
                "--out-type",
                "json,html,csv,sql,docx,pdf",
                "--out-print",
                str(quicktest_dir),
            ],
        )
        output_root = quicktest_dir / "output"
        _assert_any_files(output_root, "*.json", "quicktest json")
        _assert_any_files(output_root, "*.html", "quicktest html")
        _assert_any_files(output_root, "*.csv", "quicktest csv")
        _assert_any_files(output_root, "*.sqlite3", "quicktest sql")
        _assert_any_files(output_root, "*.docx", "quicktest docx")
        _assert_any_files(output_root, "*.pdf", "quicktest pdf")

        ocr_dir = artifact_root / "ocr"
        ocr_dir.mkdir(parents=True, exist_ok=True)
        _run(
            "ocr-rich-artifacts",
            [
                PYTHON,
                "silica-x.py",
                "ocr",
                str(ocr_fixture),
                "--plugin",
                "ocr_extractor",
                "--filter",
                "ocr_signal_classifier",
                "--module",
                "source-pack-01-module-1",
                "--out-type",
                "json,html,csv,sql,docx,pdf",
                "--out-print",
                str(ocr_dir),
            ],
        )
        ocr_output_root = ocr_dir / "output"
        _assert_any_files(ocr_output_root, "*.json", "ocr json")
        _assert_any_files(ocr_output_root, "*.html", "ocr html")
        _assert_any_files(ocr_output_root, "*.csv", "ocr csv")
        _assert_any_files(ocr_output_root, "*.sqlite3", "ocr sql")
        _assert_any_files(ocr_output_root, "*.docx", "ocr docx")
        _assert_any_files(ocr_output_root, "*.pdf", "ocr pdf")

        cli_entrypoint = shutil.which("silica-x")
        if cli_entrypoint:
            _run("installed-entrypoint-about", [cli_entrypoint, "--about"], expect=0)
        else:
            print("[smoke] installed-entrypoint-about: skipped (silica-x not on PATH)")

        print(f"[smoke] success: artifacts written under {artifact_root}")
        return 0
    finally:
        # Keep artifacts for inspection when the suite is launched manually.
        print(f"[smoke] temp root: {smoke_root}")


if __name__ == "__main__":
    raise SystemExit(main())
