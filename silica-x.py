#!/usr/bin/env python3

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

import asyncio
import sys

from core.runner import run


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run()))
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"[!] Silica-X failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
