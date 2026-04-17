# Development

The repository is intended to be maintainable, not only feature-rich.

## Stability posture

- package metadata is aligned on `v10.0`
- HTML reporting is centralized through Reporter
- docs and website now describe the current runtime instead of old release notes
- media and OCR lanes are wired into the main project surface

## Useful checks

```bash
python -m pytest -q
python -m ruff check .
python -m mypy
python -m compileall -q core filters modules plugins tests silica-x.py
```

## Areas that matter most in maintenance

- keep engine contracts stable
- keep plugin/filter scope metadata accurate
- keep Reporter output and JSON payloads consistent
- keep website copy synced with actual runtime behavior
