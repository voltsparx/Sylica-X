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
# ──────────────────────────────────────────────────────────────

"""Operator configuration helpers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


_DEFAULT_OPERATOR_CONFIG: dict[str, Any] = {
    "silica_x": {
        "version": "10.1",
        "description": "Silica-X operator configuration",
    },
    "surface_probe": {
        "enabled": True,
        "default_preset": "quick_surface",
        "default_timeout_seconds": 300,
        "extra_flags": [],
        "require_root_for_stealth_sweep": True,
    },
    "subdomain_harvest": {
        "enabled": True,
        "passive_only": True,
        "default_timeout_seconds": 180,
        "config_file": None,
        "wordlist_file": None,
    },
    "domain_recon": {
        "enabled": True,
        "timeout_seconds": 30,
        "run_whois": True,
        "run_cert_transparency": True,
        "run_http_headers": True,
        "run_dns": True,
    },
    "ocr_pipeline": {
        "enabled": True,
        "preprocess_intensity": "balanced",
        "use_tesseract": True,
        "use_easyocr": True,
        "tesseract_lang": "eng",
        "tesseract_config": "--oem 3 --psm 6",
        "easyocr_langs": ["en"],
    },
    "media_recon": {
        "enabled": True,
        "run_ocr_on_images": True,
        "run_ocr_on_video_thumbnails": True,
        "max_images_per_run": 25,
        "timeout_seconds": 30,
    },
    "report": {
        "save_raw_scan_xml": True,
        "save_raw_harvest_output": True,
        "raw_output_directory": "output/raw",
        "include_surface_map_in_html": True,
        "include_media_intel_in_html": True,
        "include_domain_recon_in_html": True,
    },
}


def load_operator_config(config_path: str | None = None) -> dict[str, Any]:
    """Load operator configuration from YAML or return defaults."""

    if config_path is None:
        candidate = Path(__file__).resolve().parent.parent.parent / "config" / "silica_x_config.yml"
    else:
        candidate = Path(config_path)

    try:
        import yaml

        if not candidate.exists():
            return deepcopy(_DEFAULT_OPERATOR_CONFIG)
        with candidate.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
        if not isinstance(payload, dict):
            return deepcopy(_DEFAULT_OPERATOR_CONFIG)
        return payload
    except Exception:
        return deepcopy(_DEFAULT_OPERATOR_CONFIG)


def get_surface_probe_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config if isinstance(config, dict) else load_operator_config()
    return dict(payload.get("surface_probe", {}))


def get_subdomain_harvest_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config if isinstance(config, dict) else load_operator_config()
    return dict(payload.get("subdomain_harvest", {}))


def get_domain_recon_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config if isinstance(config, dict) else load_operator_config()
    return dict(payload.get("domain_recon", {}))


def get_ocr_pipeline_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config if isinstance(config, dict) else load_operator_config()
    return dict(payload.get("ocr_pipeline", {}))


def get_media_recon_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config if isinstance(config, dict) else load_operator_config()
    return dict(payload.get("media_recon", {}))


def get_report_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config if isinstance(config, dict) else load_operator_config()
    return dict(payload.get("report", {}))

