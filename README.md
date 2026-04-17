# Silica-X v10.0

<strong>Theme: Ember</strong><br>
OSINT orchestration, media intelligence, and Reporter-grade artifacts for profile, surface, fusion, and OCR-led investigations.

<p align="center">
  <img src="https://raw.githubusercontent.com/voltsparx/Silica-X/refs/heads/main/docs/images/illustration/silica-x-icon.png" alt="Silica-X logo" width="420">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v10.0-F47C20?style=for-the-badge" alt="Version v10.0">
  <img src="https://img.shields.io/badge/theme-Ember-E86F1C?style=for-the-badge" alt="Theme Ember">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Versions">
  <img src="https://img.shields.io/badge/package-silica--x-CB6D1E?style=for-the-badge" alt="PyPI package name">
  <img src="https://img.shields.io/badge/import-silica__x-784421?style=for-the-badge" alt="Python import name">
  <img src="https://img.shields.io/badge/license-Proprietary-8B0000?style=for-the-badge" alt="License Proprietary">
</p>

Silica-X is a Python intelligence framework for authorized OSINT work. It combines profile reconnaissance, domain-surface analysis, fusion scoring, public-media reconnaissance, and OCR image scanning into one runtime with plugins, filters, engine policies, and categorized artifacts.

## What v10.0 changes

- Reporter is now the primary reporting layer for HTML and CLI summaries.
- Media reconnaissance and OCR image scanning are first-class lanes instead of side notes.
- HTML artifacts are organized as case views with graphs, categorized sections, extension drill-downs, vulnerability context, and a closing `Reporter Brief`.
- The docs tree and website are aligned to the current runtime instead of old release-planning notes.

## Core workflows

- `profile` scans usernames and public profiles across platform manifests.
- `surface` analyzes domain exposure, transport posture, and surface intelligence.
- `fusion` correlates profile and surface evidence into scored intelligence.
- `orchestrate` runs the policy-led orchestration pipeline directly.
- `ocr` runs dedicated OCR image scanning across local paths and remote URLs.
- media plugins add public image/video/post-text reconnaissance and stego-style triage.

## Install, run, import

```bash
pip install silica-x
silica-x
```

```python
import silica_x
```

From source:

```bash
git clone https://github.com/voltsparx/Silica-X.git
cd Silica-X
pip install -r requirements.txt
python silica-x.py
```

Optional extras:

```bash
pip install ".[reports]"
pip install ".[ocr]"
```

`pytesseract` is a Python wrapper, but OCR still depends on a reachable `tesseract` binary. Silica-X now reports which OCR/image backends were actually available during the run.

## Quick examples

```bash
silica-x profile alice --html
silica-x surface example.com --html
silica-x fusion alice example.com --html
silica-x ocr ./captures/poster.png --url https://example.com/image.png --html
silica-x profile alice --plugin media_recon_engine --plugin post_signal_intel --plugin stego_signal_probe --html
```

## Reporter outputs

Silica-X writes artifacts under `output/` and can emit:

- CLI summaries
- JSON payloads
- CSV exports plus companion CSV slices
- HTML Reporter case views
- SQLite case stores
- DOCX case documents
- PDF case documents
- run logs and framework logs

Reporter is designed to make the result easier to triage by grouping identity findings, reliability issues, correlation, vulnerabilities, plugin/filter signals, OCR/media lanes, and the final `Reporter Brief`.

In prompt mode, attachables can be configured as session defaults with commands like:

```text
enable plugins threat_conductor
enable filters contact_canonicalizer
enable modules source-pack-01-module-1
config
```

## Documentation

- [Docs Index](docs/README.md)
- [Operator Guide](docs/operator-guide.md)
- [Architecture](docs/architecture.md)
- [Extensions](docs/extensions.md)
- [Media Intelligence](docs/media-intelligence.md)
- [Reporter](docs/reporter.md)
- [Development](docs/development.md)
- [Website](docs/website/README.md)

## Safety

- Legal and authorized use only
- Respect platform terms, privacy, and local law
- Do not use Silica-X for stalking, harassment, or unauthorized surveillance

## Developer notes

Useful local checks:

```bash
python -m pytest -q
python -m ruff check .
python -m mypy
python -m compileall -q core filters modules plugins tests silica-x.py
```

Core package naming:

- package install name: `silica-x`
- CLI entrypoint: `silica-x`
- Python import path: `silica_x`

## Author

- Author: voltsparx
- Contact: voltsparx@gmail.com
- Repository: https://github.com/voltsparx/Silica-X
