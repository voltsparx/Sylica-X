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

"""silica_x source-intel module catalog and integration utilities."""

from modules.catalog import (
    DEFAULT_MODULES_ROOT,
    DEFAULT_SOURCE_ROOT,
    SORTABLE_FIELDS,
    build_module_catalog,
    ensure_module_catalog,
    load_module_catalog,
    query_module_catalog,
    select_module_entries,
    summarize_module_catalog,
    validate_module_catalog,
)

__all__ = [
    "DEFAULT_MODULES_ROOT",
    "DEFAULT_SOURCE_ROOT",
    "SORTABLE_FIELDS",
    "build_module_catalog",
    "ensure_module_catalog",
    "load_module_catalog",
    "query_module_catalog",
    "select_module_entries",
    "summarize_module_catalog",
    "validate_module_catalog",
]
