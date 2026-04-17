# OCR and Image Scan Infrastructure

## Status

Current state: shipped as a first-class OCR lane.  
Silica-X now ships a dedicated `ocr` / `ocr-scan` command, wizard OCR phase controls, OCR-only plugins and filters, structured extraction, and report parity across JSON, CLI, CSV, and HTML.  
The public-media reconnaissance lane still exists separately for profile-linked media and lightweight video/stego analysis.

Source planning note:

* `self-structuring/ocr-n-image/ocr-n-image-scan-infrastructure.txt`

## Goal

Provide an OCR-capable enrichment lane that can extract actionable OSINT signals from local or fetched images and feed those artifacts into existing Silica-X fusion/reporting flows.

Primary objectives:

* Extract raw text from images reliably
* Parse structured artifacts (emails, URLs, usernames, phone patterns)
* Support batch execution
* Integrate with wizard/extension controls
* Preserve output parity (JSON/CLI/CSV/HTML)

## Plugin Layout

Shipped package:

* `plugins/ocr/__init__.py`
* `plugins/ocr/ocr_extractor.py`
* `plugins/ocr/regex_filters.py`
* `plugins/ocr/batch_processor.py`

## Dependency Profile

Runtime dependencies:

* `Pillow`
* `pytesseract`
* optional: `langdetect`, `regex`

System dependency:

* Tesseract OCR binary installed on host/container

## Integration Model

Implemented integration points:

* Plugin discovery via existing `Signal Forge` (`core/extensions/signal_forge.py`)
* Selector compatibility via existing extension control plane (`auto/manual/hybrid`)
* Wizard integration via current guided orchestration path (`wizard`)
* Artifact rendering via existing output stack (`core/output.py`, `core/artifacts/html_report.py`, CSV companions)

## Data Contract

Per-image result payload:

* `image_path`
* `raw_text`
* `emails`
* `urls`
* `usernames`
* `phones` (optional extension)
* `language` (optional extension)
* `confidence_hint` (optional extension)

Batch payload:

* `image_count`
* `processed_count`
* `failed_count`
* `items[]` (per-image records)
* `summary` (aggregated indicators)

## Performance Notes

Recommended controls:

* batch sizing and bounded concurrency
* optional preprocess pipeline (grayscale/threshold/resize)
* deterministic caching for repeated image targets
* timeout/guardrails per image decode + OCR call

## Security and Safety

Minimum safeguards:

* file type allowlist for local image inputs
* strict path validation/sandbox boundaries for local file ingestion
* size limits to prevent memory pressure
* sanitized rendering in CLI/HTML outputs

## Implemented Components

1. `core/collect/ocr_image_scan.py`
2. `core/engines/ocr_image_scan_engine.py`
3. `plugins/ocr/ocr_extractor.py`
4. `plugins/ocr/regex_filters.py`
5. `plugins/ocr/batch_processor.py`
6. `filters/ocr_signal_classifier.py`
7. `ocr` / `ocr-scan` / `image-scan` CLI workflow
8. `wizard --ocr-phase` plus `--image-paths` and `--image-urls`
9. OCR-specific HTML and CSV companion sections

## Runtime Plugins Shipped Today

Current runtime plugins:

* `media_intel_core`
* `media_recon_engine`
* `post_signal_intel`
* `stego_signal_probe`

Current runtime scope:

* public image metadata extraction
* optional OCR on public images
* public post-text harvesting and signal extraction
* lightweight video endpoint + thumbnail reconnaissance
* heuristic stego-suspicion scoring

Still pending:

* deeper computer-vision classification beyond OCR-first extraction
* frame-by-frame video OCR/CV as a dedicated video lane
* optional language-hint routing into OCR backends
