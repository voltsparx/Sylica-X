# core/utils.py
from importlib.util import find_spec


try:
    RICH_AVAILABLE = find_spec("rich.console") is not None
except Exception:
    RICH_AVAILABLE = False
