# Media Intelligence

Silica-X v10.0 treats public-media reconnaissance as a first-class intelligence lane.

## Included capabilities

- image metadata and OCR-aware processing
- public post-text extraction and heuristic intelligence
- lightweight public-video endpoint and thumbnail reconnaissance
- stego-style signal probing and suspicion scoring
- dedicated OCR image scanning for local paths and remote URLs

## Runtime lanes

- `media_recon_engine`
- `post_signal_intel`
- `stego_signal_probe`
- dedicated `ocr` command and OCR extension set

## Practical split

Media reconnaissance and OCR are related but separate:

- media reconnaissance focuses on public-media discovery and intelligence context
- OCR focuses on text recovery and structured extraction from images

## Output behavior

Reporter surfaces media and OCR runs alongside the rest of the case so the operator can review images, text recovery, failures, and signal totals without leaving the main report.
