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

"""Scaffold new plugin/filter extension files."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from textwrap import dedent


HEADER = """# ──────────────────────────────────────────────────────────────
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
"""


def _slugify(value: str) -> str:
    token = re.sub(r"[^\w]+", "_", value.strip().lower())
    token = re.sub(r"_+", "_", token).strip("_")
    if not token:
        raise ValueError("Name is required.")
    return token


def _default_title(token: str) -> str:
    return token.replace("_", " ").strip().title()


def _parse_csv(value: str) -> list[str]:
    items = [item.strip() for item in (value or "").split(",")]
    return [item for item in items if item]


def _render_plugin(
    *,
    module_name: str,
    plugin_id: str,
    title: str,
    description: str,
    scopes: list[str],
    aliases: list[str],
    version: str,
) -> str:
    scopes_payload = ", ".join(f"\"{item}\"" for item in scopes)
    aliases_payload = ", ".join(f"\"{item}\"" for item in aliases)
    return dedent(
        f"""{HEADER}

        \"\"\"Plugin: {title}.\"\"\"

        from __future__ import annotations


        PLUGIN_SPEC = {{
            "id": "{plugin_id}",
            "title": "{title}",
            "description": "{description}",
            "scopes": [{scopes_payload}],
            "aliases": [{aliases_payload}],
            "version": "{version}",
        }}

        REQUIRES = []


        def run(context: dict) -> dict:
            \"\"\"Return extension payload.\"\"\"

            return {{
                "severity": "INFO",
                "summary": "TODO: describe what this plugin reports.",
                "highlights": [],
                "data": {{}},
            }}
        """
    ).lstrip()


def _render_filter(
    *,
    module_name: str,
    filter_id: str,
    title: str,
    description: str,
    scopes: list[str],
    aliases: list[str],
    version: str,
) -> str:
    scopes_payload = ", ".join(f"\"{item}\"" for item in scopes)
    aliases_payload = ", ".join(f"\"{item}\"" for item in aliases)
    return dedent(
        f"""{HEADER}

        \"\"\"Filter: {title}.\"\"\"

        from __future__ import annotations


        FILTER_SPEC = {{
            "id": "{filter_id}",
            "title": "{title}",
            "description": "{description}",
            "scopes": [{scopes_payload}],
            "aliases": [{aliases_payload}],
            "version": "{version}",
        }}


        def run(context: dict) -> dict:
            \"\"\"Return filter payload.\"\"\"

            return {{
                "severity": "INFO",
                "summary": "TODO: describe what this filter flags.",
                "highlights": [],
                "data": {{}},
            }}
        """
    ).lstrip()


def _write_file(path: Path, payload: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"File already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Silica-X plugins or filters.")
    sub = parser.add_subparsers(dest="kind", required=True)

    def _add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("name", help="Module name (snake-case recommended).")
        subparser.add_argument("--title", default="", help="Display title.")
        subparser.add_argument("--description", default="", help="One-line description.")
        subparser.add_argument(
            "--scopes",
            default="profile,surface,fusion",
            help="Comma-separated scopes (profile,surface,fusion).",
        )
        subparser.add_argument("--aliases", default="", help="Comma-separated aliases.")
        subparser.add_argument("--version", default="1.0", help="Version string.")
        subparser.add_argument("--force", action="store_true", help="Overwrite existing file.")

    plugin_parser = sub.add_parser("plugin", help="Create a plugin scaffold.")
    _add_common(plugin_parser)

    filter_parser = sub.add_parser("filter", help="Create a filter scaffold.")
    _add_common(filter_parser)

    args = parser.parse_args()
    module_name = _slugify(args.name)
    title = args.title.strip() or _default_title(module_name)
    description = args.description.strip() or "TODO: add description."
    scopes = _parse_csv(args.scopes) or ["profile", "surface", "fusion"]
    aliases = _parse_csv(args.aliases)
    version = str(args.version).strip() or "1.0"

    if args.kind == "plugin":
        payload = _render_plugin(
            module_name=module_name,
            plugin_id=module_name,
            title=title,
            description=description,
            scopes=scopes,
            aliases=aliases,
            version=version,
        )
        target = Path("plugins") / f"{module_name}.py"
    else:
        payload = _render_filter(
            module_name=module_name,
            filter_id=module_name,
            title=title,
            description=description,
            scopes=scopes,
            aliases=aliases,
            version=version,
        )
        target = Path("filters") / f"{module_name}.py"

    _write_file(target, payload, force=args.force)
    print(f"Created {args.kind} scaffold at {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
