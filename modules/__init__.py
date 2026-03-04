"""Silica source-intel module catalog and integration utilities."""

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
