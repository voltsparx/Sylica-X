#!/usr/bin/env python3
import asyncio

from core.runner import run


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run()))
    except KeyboardInterrupt:
        raise SystemExit(130)
