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

"""Compatibility wrapper around consolidated output helpers.

This module intentionally re-exports selected output helpers so older imports
(`core.artifacts.output`) continue to work while the implementation lives in
`core.output`.
"""

from __future__ import annotations

from core.output import (
    append_framework_log,
    display_domain_results,
    display_ocr_results,
    display_results,
    list_scanned_targets,
    save_results,
)

__all__ = [
    "append_framework_log",
    "display_domain_results",
    "display_ocr_results",
    "display_results",
    "list_scanned_targets",
    "save_results",
]
