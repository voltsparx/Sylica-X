# core/interface/banner.py

from core.foundation.colors import Colors
from core.foundation.metadata import AUTHOR, VERSION


def show_banner(anonymity_status="No Anonymization"):
    grey = Colors.GREY
    yellow = Colors.YELLOW
    cyan = Colors.CYAN
    reset = Colors.RESET

    print(f"{grey}       .d8888. d888888b db      d888888b  .o88b.  .d8b.{reset}          {grey}{yellow}db    db{reset}")
    print(f"{grey}       88'  YP   `88'   88        `88'   d8P  Y8 d8' `8b{reset}         {grey}{yellow}`8b  d8'{reset}")
    print(f"{grey}       `8bo.      88    88         88    8P      88ooo88{reset}          {grey}{yellow}`8bd8'{reset}")
    print(f"{grey}         `Y8b.    88    88         88    8b      88~~~88  C8888D{reset}  {grey}{yellow}.dPYb.{reset}")
    print(f"{grey}       db   8D   .88.   88booo.   .88.   Y8b  d8 88   88{reset}         {grey}{yellow}.8P  Y8.{reset}")
    print(f"{grey}       `8888Y' Y888888P Y88888P Y888888P  `Y88P' YP   YP{reset}         {grey}{yellow}YP    YP{reset}")
    print(f"{grey}                                                                          v{VERSION}{reset}")
    print("_________________________________________________________________________________")
    print(f"{cyan}    Automated Multi-OSINT Tool - Developed by {AUTHOR} (github.com/{AUTHOR}){reset}")
    print(f"{cyan}                      Current Anonymity: {anonymity_status}{reset}\n")

