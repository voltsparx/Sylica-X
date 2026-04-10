# ──────────────────────────────────────────────────────────────
# SPDX-License-Identifier: Proprietary
#
# Sylica-X Intelligence Framework
# Copyright (c) 2026 voltsparx
#
# Author     : voltsparx
# Repository : https://github.com/voltsparx/Sylica-X
# Contact    : voltsparx@gmail.com
# License    : See LICENSE file in the project root 
#
# This file is part of Sylica-X and is subject to the terms
# and conditions defined in the LICENSE file.
# ──────────────────────────────────────────────────────────────

"""Collection and scanning modules."""

from core.collect.vulnerability_intel import (
    build_nvd_query_parameters,
    lookup_service_vulnerabilities,
    severity_from_cvss,
)

__all__ = [
    "build_nvd_query_parameters",
    "lookup_service_vulnerabilities",
    "severity_from_cvss",
]
