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

"""Human-readable explain output for commands, plugins, and filters."""

from __future__ import annotations

from core.foundation.metadata import PROJECT_NAME, VERSION, VERSION_THEME
from core.interface.symbols import symbol
from core.extensions.signal_forge import list_plugin_descriptors
from core.extensions.signal_sieve import list_filter_descriptors


COMMAND_EXPLANATIONS: dict[str, str] = {
    "profile": "Checks usernames across platform manifests, extracts public signals, and correlates matches.",
    "surface": "Scans domain-facing assets (HTTP/HTTPS, CT, RDAP, headers) and summarizes exposure risk.",
    "fusion": "Runs profile + surface flows together and outputs one combined intelligence bundle.",
    "orchestrate": (
        "Runs the policy-driven layered pipeline (capabilities -> filters -> fusion -> reporting) "
        "using entity contracts."
    ),
    "keywords": "Lists prompt keyword aliases that map casual words to core commands.",
    "plugins": "Lists available internal plugins and their compatible workflow scopes.",
    "filters": "Lists available internal filters and their compatible workflow scopes.",
    "templates": "Lists bundled info-templates (curated plugin/filter/module arrangements; consent-only targets).",
    "modules": (
        "Builds/lists the source-intel module catalog from intel-sources with "
        "scope/kind/search/tag/score controls, plus pagination and integrity validation."
    ),
    "quicktest": (
        "Runs one random built-in victim template (5 total) and generates full JSON/CLI/CSV/HTML reports "
        "without live network collection."
    ),
    "history": "Shows previously scanned targets from local output/json and output/html artifacts.",
    "anonymity": "Checks or updates Tor/proxy routing for current session execution.",
    "live": "Starts the local dashboard for a saved target result bundle.",
    "out-type": "Sets the persisted output formats (cli, html, csv, json).",
    "out-print": "Sets the output base directory for this session (affects output/...).",
    "default-out-print": "Sets the persisted default output base directory.",
    "wizard": (
        "Guided interactive workflow that can run profile/surface/fusion phases with "
        "preset + extension-control selection and compatibility preflight checks."
    ),
    "about": "Shows framework identity, authorship, and core tool description.",
    "explain": "Shows plain-language command/plugin/filter explanations for quick onboarding.",
}


def build_explain_text() -> str:
    plugins = list_plugin_descriptors(scope=None)
    filters = list_filter_descriptors(scope=None)

    lines: list[str] = []
    lines.append(f"{symbol('major')} {PROJECT_NAME} v{VERSION} [{VERSION_THEME}] - Explain Mode")
    lines.append("-" * 36)
    lines.append("")
    lines.append(f"{symbol('major')} What this tool does")
    lines.append(
        f"{symbol('bullet')} Collects public OSINT signals from usernames and domains, then fuses correlation, exposure, and reporting."
    )
    lines.append("")
    lines.append(f"{symbol('major')} Global flags")
    lines.append(f"{symbol('bullet')} --about: print tool description and identity block.")
    lines.append(f"{symbol('bullet')} --explain: print this explain guide and exit.")
    lines.append("")
    lines.append(f"{symbol('major')} Commands")
    for command, description in sorted(COMMAND_EXPLANATIONS.items()):
        lines.append(f"{symbol('bullet')} {command}: {description}")
    lines.append("")
    lines.append(f"{symbol('major')} Plugins")
    core_plugins = [
        row for row in plugins if str(row.get("plugin_group") or "").strip().lower() != "cryptography"
    ]
    crypto_plugins = [
        row for row in plugins if str(row.get("plugin_group") or "").strip().lower() == "cryptography"
    ]
    lines.append(f"{symbol('tip')} Core Plugin Set ({len(core_plugins)})")
    for row in sorted(core_plugins, key=lambda item: str(item.get("id", ""))):
        scopes = ", ".join(row.get("scopes", []))
        lines.append(f"{symbol('feature')} {row.get('id')}: {row.get('description')} (scopes: {scopes})")
    if crypto_plugins:
        lines.append(f"{symbol('tip')} Cryptography Plugin Set ({len(crypto_plugins)})")
        for row in sorted(crypto_plugins, key=lambda item: str(item.get("id", ""))):
            scopes = ", ".join(row.get("scopes", []))
            crypto_kind = str(row.get("crypto_kind") or "").strip().lower()
            kind_suffix = f", crypto-kind: {crypto_kind}" if crypto_kind else ""
            lines.append(f"{symbol('feature')} {row.get('id')}: {row.get('description')} (scopes: {scopes}{kind_suffix})")
        lines.append(
            f"{symbol('tip')} Crypto output includes config labels and source coverage in CLI/HTML reports."
        )
    lines.append("")
    lines.append(f"{symbol('major')} Filters")
    for row in sorted(filters, key=lambda item: str(item.get("id", ""))):
        scopes = ", ".join(row.get("scopes", []))
        lines.append(f"{symbol('feature')} {row.get('id')}: {row.get('description')} (scopes: {scopes})")
    lines.append("")
    lines.append(f"{symbol('major')} Prompt-only controls")
    lines.append(f"{symbol('bullet')} banner: print the banner again.")
    lines.append(f"{symbol('bullet')} clear: clear terminal only (banner stays hidden until you run banner).")
    lines.append(f"{symbol('bullet')} use profile|surface|fusion: switch active module context.")
    lines.append(f"{symbol('bullet')} select module <name>: alias for use command module switch.")
    lines.append(f"{symbol('bullet')} set plugins ... / set filters ...: module-compatible defaults, supports aliases, comma-separated.")
    lines.append(f"{symbol('bullet')} set template <id>: apply a bundled info-template to plugin/filter defaults.")
    lines.append(f"{symbol('bullet')} select plugins ... / select filters ...: name-based aliases for set controls.")
    lines.append(f"{symbol('bullet')} select template <id>: alias for set template.")
    lines.append(f"{symbol('bullet')} add/remove plugins ...: incremental plugin control by selector name.")
    lines.append(f"{symbol('bullet')} add/remove filters ...: incremental filter control by selector name.")
    lines.append(f"{symbol('bullet')} set extension_control ...: module default for --extension-control auto|manual|hybrid.")
    lines.append(f"{symbol('bullet')} set orchestrate_extension_control ...: default --extension-control for orchestrate.")
    lines.append(f"{symbol('bullet')} Prompt format: (console <module> ec=<mode> plugins=<set> filters=<set>)>>")
    lines.append("")
    lines.append(f"{symbol('major')} Flag parity notes")
    lines.append(f"{symbol('bullet')} profile/surface/fusion share plugin/filter flags: --plugin, --list-plugins.")
    lines.append(f"{symbol('bullet')} profile/surface/fusion share filter flags: --filter, --list-filters.")
    lines.append(f"{symbol('bullet')} --info-template applies a curated plugin/filter/module arrangement.")
    lines.append(f"{symbol('bullet')} extension controls: --extension-control auto|manual|hybrid with conflict validation.")
    lines.append(f"{symbol('bullet')} explain command and --explain flag produce the same explain output.")
    lines.append(
        f"{symbol('bullet')} wizard supports phase toggles, preset selection, extension preflight validation, and seeded/non-seeded execution."
    )
    lines.append(
        f"{symbol('bullet')} OCR/image infrastructure is documented in docs/ocr-image-scan-infrastructure.md (roadmap track)."
    )
    return "\n".join(lines)

