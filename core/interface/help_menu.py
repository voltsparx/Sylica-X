"""Help menu renderers for flag mode and prompt mode."""

from __future__ import annotations

from core.foundation.colors import Colors, c
from core.foundation.metadata import PROJECT_NAME, VERSION, VERSION_THEME
from core.interface.symbols import symbol


def _rule(color: str = Colors.BLUE) -> None:
    print(c("=" * 72, color))


def _section(title: str, *, color: str = Colors.BLUE) -> None:
    print()
    _rule(color)
    print(c(f"  {symbol('major')} {title}", Colors.BOLD + color))
    _rule(color)


def _item(command: str, description: str) -> None:
    print(c(f"  {symbol('bullet')} {command:<20}", Colors.CYAN) + c(f"{description}", Colors.GREY))


def show_flag_help() -> None:
    print(c(f"\n{PROJECT_NAME} v{VERSION} [{VERSION_THEME}] Flag Help", Colors.BOLD + Colors.CYAN))
    print(c(f"{symbol('action')} Usage: python silica-x.py <command> [flags]", Colors.GREY))

    _section("Global")
    _item("--about", "Show framework description and exit.")
    _item("--explain", "Show plain-language command and extension guide and exit.")

    _section("Core Commands")
    _item("profile <username...>", "Scan usernames for profile intelligence.")
    _item("surface <domain>", "Scan a domain for surface exposure signals.")
    _item("fusion <username> <domain>", "Run profile and surface workflows together.")
    _item("orchestrate <mode> <target>", "Run policy-driven layered orchestration.")
    _item("plugins [--scope ...]", "List available plugins.")
    _item("filters [--scope ...]", "List available filters.")
    _item("modules [query flags]", "List/sync/query source-intel module catalog.")
    _item("history [--limit N]", "List previously scanned targets.")
    _item("quicktest [flags]", "Run one random built-in victim template and emit full reports.")
    _item("live <target> [--port]", "Open local live dashboard.")
    _item("anonymity [flags]", "Check or change Tor/proxy routing.")
    _item("wizard", "Run guided workflow questions.")
    _item("wizard --help", "Show full wizard flags (phases, presets, selectors, toggles).")
    _item("keywords", "Show prompt keyword shortcuts.")
    _item("about | explain | prompt | help", "Metadata, explainers, interactive mode, help.")

    _section("Extension + Routing")
    _item("--plugin / --all-plugins", "Enable one or all plugins (repeatable/comma-separated selectors).")
    _item("--filter / --all-filters", "Enable one or all filters (repeatable/comma-separated selectors).")
    _item("--extension-control <mode>", "auto | manual | hybrid (fail-fast conflict validation)")
    _item("wizard preflight", "Wizard validates extension compatibility before starting scans.")
    _item("--tor / --proxy", "Enable Tor/proxy routing.")
    _item("--no-tor / --no-proxy", "Disable Tor/proxy routing.")
    _item("--check / --prompt", "Diagnostics or guided anonymity setup.")

    _section("Output")
    _item("--html / --csv", "Write HTML and CSV artifacts.")
    _item("output/data output/html output/cli output/logs", "Default artifact directories.")
    print()


def show_prompt_help() -> None:
    print(c(f"\n{PROJECT_NAME} v{VERSION} [{VERSION_THEME}] Prompt Help", Colors.BOLD + Colors.CYAN))
    print(c(f"{symbol('action')} Type one command and press Enter.", Colors.GREY))

    _section("Prompt Commands")
    _item("scan <username>", "Quick profile alias.")
    _item("profile <username...>", "Run profile workflow.")
    _item("surface <domain>", "Run surface workflow.")
    _item("fusion <username> <domain>", "Run fusion workflow.")
    _item("orchestrate <mode> <target>", "Run layered orchestration.")
    _item("plugins | filters | modules", "Inventory and module intelligence catalog.")
    _item("history [--limit N]", "List previously scanned targets.")
    _item("quicktest [flags]", "Run one random built-in victim template.")
    _item("config", "Show prompt defaults and active module.")
    _item("anonymity [flags]", "Check or change Tor/proxy routing.")
    _item("wizard", "Guided workflow with prompts.")
    _item("keywords", "Show all prompt shortcut aliases.")
    _item("about | explain | help | clear | exit", "Metadata, docs, help, clear screen, quit.")

    _section("Prompt Controls")
    _item("use <profile|surface|fusion>", "Switch active module context.")
    _item("select module <profile|surface|fusion>", "Alias for `use` module switch by name.")
    _item("set plugins <none|all|a,b>", "Set module-compatible plugins (strict compatibility checks).")
    _item("set filters <none|all|a,b>", "Set module-compatible filters (strict compatibility checks).")
    _item("select plugins <a,b>", "Alias for `set plugins` (name-based selectors).")
    _item("select filters <a,b>", "Alias for `set filters` (name-based selectors).")
    _item("add plugins <a,b> / remove plugins <a,b>", "Incremental plugin control by name.")
    _item("add filters <a,b> / remove filters <a,b>", "Incremental filter control by name.")
    _item("set profile_preset <...>", "Default profile preset.")
    _item("set surface_preset <...>", "Default surface preset.")
    _item("set extension_control <...>", "Default control mode for active module.")
    _item("set orchestrate_extension_control <...>", "Default control mode for orchestrate.")

    _section("Prompt Format")
    print(c(f"  {symbol('feature')} (console <module> ec=<mode> plugins=<set> filters=<set>)>>", Colors.CYAN))
    print(c(f"  {symbol('tip')} Run 'keywords' to inspect all alias mappings.", Colors.GREY))
    print()


def show_help() -> None:
    # Backward-compatible wrapper
    show_prompt_help()
