"""Help menu renderers for flag mode and prompt mode."""

from __future__ import annotations

from core.colors import Colors, c


def show_flag_help() -> None:
    print(c("\nSilica-X v7.0 Flag Help\n", Colors.BOLD + Colors.CYAN))
    print("Usage: python silica-x.py <command> [flags]\n")

    print(c("Global Flags", Colors.BLUE))
    print("• --about - Show framework description and exit.")
    print("• --explain - Show plain-language command and extension guide and exit.\n")

    print(c("Core Commands", Colors.BLUE))
    print("• profile <username...> - Scan usernames for profile intelligence.")
    print("• surface <domain> - Scan a domain for surface exposure signals.")
    print("• fusion <username> <domain> - Run profile and surface workflows together.")
    print("• plugins [--scope ...] - List available plugins.")
    print("• filters [--scope ...] - List available filters.")
    print("• history [--limit N] - List previously scanned targets.")
    print("• live <target> [--port PORT] - Open the local live dashboard.")
    print("• anonymity [flags] - Check or change Tor and proxy routing.")
    print("• wizard [flags] - Run guided workflow questions.")
    print("• keywords - Show prompt keyword shortcuts.")
    print("• about - Show tool metadata.")
    print("• explain - Show simple command and extension explanations.")
    print("• prompt - Start interactive prompt mode.")
    print("• help - Show this help menu.\n")

    print("Common extension flags: --plugin --all-plugins --list-plugins --filter --all-filters --list-filters.")
    print("Common routing flags: --tor --no-tor --proxy --no-proxy --check --prompt.")
    print("Output paths: output/data output/html output/cli output/logs.\n")


def show_prompt_help() -> None:
    print(c("\nSilica-X v7.0 Prompt Help\n", Colors.BOLD + Colors.CYAN))
    print("Type one command and press Enter.\n")

    print(c("Prompt Commands", Colors.BLUE))
    print("• scan <username> - Run quick profile scan alias.")
    print("• profile <username...> - Run profile workflow.")
    print("• surface <domain> - Run surface workflow.")
    print("• fusion <username> <domain> - Run fusion workflow.")
    print("• plugins [--scope ...] - List plugins.")
    print("• filters [--scope ...] - List filters.")
    print("• history [--limit N] - List scanned targets.")
    print("• config - Show current prompt settings.")
    print("• use <profile|surface|fusion> - Switch active module.")
    print("• set plugins <none|all|id1,id2> - Set module-compatible plugins.")
    print("• set filters <none|all|id1,id2> - Set module-compatible filters.")
    print("• set profile_preset <quick|balanced|deep> - Set default profile preset.")
    print("• set surface_preset <quick|balanced|deep> - Set default surface preset.")
    print("• anonymity [flags] - Check or change Tor and proxy routing.")
    print("• wizard - Run guided workflow.")
    print("• banner - Show banner.")
    print("• explain - Show plain-language guide.")
    print("• keywords - Show shortcut keywords.")
    print("• about - Show tool metadata.")
    print("• clear - Clear terminal only.")
    print("• help - Show this help menu.")
    print("• exit - Close prompt.\n")

    print("Prompt format: (console <module> plugins=<set> filters=<set>)>>")
    print("Run 'keywords' to see full alias mappings.\n")


def show_help() -> None:
    # Backward-compatible wrapper
    show_prompt_help()
