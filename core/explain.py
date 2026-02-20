"""Human-readable explain output for commands, plugins, and filters."""

from __future__ import annotations

from core.metadata import PROJECT_NAME, VERSION
from core.signal_forge import list_plugin_descriptors
from core.signal_sieve import list_filter_descriptors


COMMAND_EXPLANATIONS: dict[str, str] = {
    "profile": "Checks usernames across platform manifests, extracts public signals, and correlates matches.",
    "surface": "Scans domain-facing assets (HTTP/HTTPS, CT, RDAP, headers) and summarizes exposure risk.",
    "fusion": "Runs profile + surface flows together and outputs one combined intelligence bundle.",
    "keywords": "Lists prompt keyword aliases that map casual words to core commands.",
    "plugins": "Lists available internal plugins and their compatible workflow scopes.",
    "filters": "Lists available internal filters and their compatible workflow scopes.",
    "history": "Shows previously scanned targets from local HTML report inventory.",
    "anonymity": "Checks or updates Tor/proxy routing for current session execution.",
    "live": "Starts the local dashboard for a saved target result bundle.",
    "wizard": "Guided step-by-step interactive workflow that builds profile/surface/fusion runs.",
    "about": "Shows framework identity, authorship, and core tool description.",
    "explain": "Shows plain-language command/plugin/filter explanations for quick onboarding.",
}


def build_explain_text() -> str:
    plugins = list_plugin_descriptors(scope=None)
    filters = list_filter_descriptors(scope=None)

    lines: list[str] = []
    lines.append(f"{PROJECT_NAME} v{VERSION} - Explain Mode")
    lines.append("")
    lines.append("What this tool does:")
    lines.append(
        "- Collects public OSINT signals from usernames and domains, then fuses correlation, exposure, and reporting."
    )
    lines.append("")
    lines.append("Global flags:")
    lines.append("- --about: print tool description and identity block.")
    lines.append("- --explain: print this explain guide and exit.")
    lines.append("")
    lines.append("Commands:")
    for command, description in sorted(COMMAND_EXPLANATIONS.items()):
        lines.append(f"- {command}: {description}")
    lines.append("")
    lines.append("Plugins:")
    for row in sorted(plugins, key=lambda item: str(item.get("id", ""))):
        scopes = ", ".join(row.get("scopes", []))
        lines.append(f"- {row.get('id')}: {row.get('description')} (scopes: {scopes})")
    lines.append("")
    lines.append("Filters:")
    for row in sorted(filters, key=lambda item: str(item.get("id", ""))):
        scopes = ", ".join(row.get("scopes", []))
        lines.append(f"- {row.get('id')}: {row.get('description')} (scopes: {scopes})")
    lines.append("")
    lines.append("Prompt-only controls:")
    lines.append("- banner: print the banner again.")
    lines.append("- clear: clear terminal only (banner stays hidden until you run banner).")
    lines.append("- use profile|surface|fusion: switch active module context.")
    lines.append("- set plugins ... / set filters ...: module-compatible defaults, supports aliases, comma-separated.")
    lines.append("- Prompt format: (console <module> plugins=<set> filters=<set>)>>")
    lines.append("")
    lines.append("Flag parity notes:")
    lines.append("- profile/surface/fusion share plugin/filter flags: --plugin, --all-plugins, --list-plugins.")
    lines.append("- profile/surface/fusion share filter flags: --filter, --all-filters, --list-filters.")
    lines.append("- explain command and --explain flag produce the same explain output.")
    return "\n".join(lines)
