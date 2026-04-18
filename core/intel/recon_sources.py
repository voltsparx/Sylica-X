"""Generic source-study helpers for local recon architecture references under temp/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
import re
import shlex

from core.collect.domain_intel import normalize_domain
from core.foundation.recon_modes import normalize_recon_mode

DEFAULT_TEMP_ROOT = Path("temp")

_PIPE_SPLIT_RE = re.compile(r"\s*\|\s*")
_OPTION_RE = re.compile(r"options\.([a-z_]+)")

_SOURCE_OPTION_LABELS: dict[str, str] = {
    "allow_deadly": "Allow highly intrusive modules",
    "current_preset": "Show the merged recipe before execution",
    "current_preset_full": "Show the full resolved recipe/config",
    "dry_run": "Build a module plan without executing the scan",
    "install_all_deps": "Install dependencies for all modules",
    "list_flags": "List available module flags",
    "list_module_options": "List module-specific options",
    "list_modules": "List scan and internal modules",
    "list_output_modules": "List output modules",
    "list_presets": "List built-in recipes",
    "module_help": "Show help for a specific module",
    "version": "Show source runtime version",
    "yes": "Skip interactive scan confirmation",
}

_RECIPE_TO_silica_x: dict[str, dict[str, Any]] = {
    "subdomain-enum": {
        "surface_preset": "deep",
        "recon_mode": "passive",
        "include_ct": True,
        "include_rdap": True,
        "coverage": "Passive subdomain expansion and ownership enrichment",
    },
    "fast": {
        "surface_preset": "quick",
        "recon_mode": "passive",
        "include_ct": True,
        "include_rdap": False,
        "coverage": "Fast low-noise discovery against the exact target",
    },
    "cloud-enum": {
        "surface_preset": "balanced",
        "recon_mode": "hybrid",
        "include_ct": True,
        "include_rdap": True,
        "coverage": "Cloud-facing surface discovery with ownership context",
    },
    "tech-detect": {
        "surface_preset": "balanced",
        "recon_mode": "active",
        "include_ct": False,
        "include_rdap": False,
        "coverage": "HTTP-led technology and exposure profiling",
    },
    "web-basic": {
        "surface_preset": "balanced",
        "recon_mode": "active",
        "include_ct": False,
        "include_rdap": False,
        "coverage": "Light web surface inspection",
    },
    "web-thorough": {
        "surface_preset": "deep",
        "recon_mode": "active",
        "include_ct": False,
        "include_rdap": False,
        "coverage": "Deeper active web reconnaissance",
    },
    "web-screenshots": {
        "surface_preset": "balanced",
        "recon_mode": "active",
        "include_ct": False,
        "include_rdap": False,
        "coverage": "Web target validation before analyst follow-up",
    },
    "spider": {
        "surface_preset": "balanced",
        "recon_mode": "active",
        "include_ct": False,
        "include_rdap": False,
        "coverage": "Active HTTP collection with recursive-follow ideas",
    },
    "spider-intense": {
        "surface_preset": "deep",
        "recon_mode": "active",
        "include_ct": False,
        "include_rdap": False,
        "coverage": "Deeper recursive web exploration pattern",
    },
    "baddns-intense": {
        "surface_preset": "deep",
        "recon_mode": "active",
        "include_ct": True,
        "include_rdap": True,
        "coverage": "Higher-effort DNS and exposure verification",
    },
    "kitchen-sink": {
        "surface_preset": "max",
        "recon_mode": "hybrid",
        "include_ct": True,
        "include_rdap": True,
        "coverage": "Maximum mixed-lane attack-surface collection",
    },
}

_NATIVE_CAPABILITIES: dict[str, str] = {
    "subdomain-enum": "Subdomain discovery and prioritization",
    "passive": "Passive ownership and discovery mode",
    "active": "Active HTTP and DNS verification mode",
    "cloud-enum": "Cloud-facing asset visibility enrichment",
    "web-basic": "HTTP exposure, redirect, and header profiling",
    "web-thorough": "Deeper active web coverage pattern",
}

_PARTIAL_CAPABILITIES: dict[str, str] = {
    "tech-detect": "Technology hints are inferred through HTTP behavior and headers, not a full fingerprint stack",
    "spider": "Recursive web discovery is represented as follow-up guidance, not crawler parity",
    "web-screenshots": "Silica-X validates web targets but does not capture screenshots natively",
    "baddns": "DNS takeover review is represented as prioritization hints, not dedicated takeover modules",
    "portscan": "Packet-crafting engines exist for ARP, SYN, TCP connect, UDP, FIN, NULL, XMAS, and OS fingerprint research, but live execution parity is still being integrated",
    "service-enum": "Read-only packet crafting and banner-intelligence controls exist, but full protocol fingerprint execution remains an incremental buildout",
}

_UNSUPPORTED_CAPABILITIES: dict[str, str] = {
    "code-enum": "Repository mining and code-search modules are not native in the surface engine",
    "email-enum": "Dedicated email enumeration is outside the current surface lane",
    "web-paramminer": "Parameter mining and fuzzing are not implemented",
    "deadly": "Highly intrusive modules are intentionally not mirrored",
    "aggressive": "High-noise brute-force and fuzz lanes are intentionally not mirrored",
    "download": "File and repository download workflows are not mirrored",
    "iis-shortnames": "Dedicated IIS shortname checks are not implemented",
}


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _iter_temp_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(item for item in root.iterdir() if item.is_dir())


def _detect_console_shell_root(root: Path = DEFAULT_TEMP_ROOT) -> Path | None:
    for path in _iter_temp_dirs(root):
        driver = path / "lib" / "msf" / "ui" / "console" / "driver.rb"
        dispatcher = path / "lib" / "rex" / "ui" / "text" / "dispatcher_shell.rb"
        if driver.exists() and dispatcher.exists():
            return path
        for nested in path.rglob("driver.rb"):
            if nested.as_posix().endswith("lib/msf/ui/console/driver.rb"):
                return nested.parents[5]
    return None


def _detect_graph_registry_root(root: Path = DEFAULT_TEMP_ROOT) -> Path | None:
    for path in _iter_temp_dirs(root):
        if (path / "cmd").exists() and (path / "engine" / "plugins").exists() and (path / "internal").exists():
            return path
    return None


def _detect_recursive_modules_root(root: Path = DEFAULT_TEMP_ROOT) -> Path | None:
    for path in _iter_temp_dirs(root):
        if not (path / "docs" / "modules" / "list_of_modules.md").exists():
            continue
        has_recipes = any(item.is_dir() and any(item.glob("*.yml")) for item in path.rglob("presets"))
        has_cli = any(item.name == "cli.py" for item in path.rglob("cli.py"))
        if has_recipes and has_cli:
            return path
    return None


def _clean_value(value: str) -> str:
    return value.strip().strip("`").strip()


def _parse_markdown_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        parts = [_clean_value(part) for part in _PIPE_SPLIT_RE.split(line.strip("|"))]
        if len(parts) < 2 or parts[0].lower() == "module":
            continue
        rows.append(parts)
    return rows


def _parse_simple_recipe(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": path.stem,
        "description": "",
        "include": [],
        "flags": [],
        "modules": [],
        "exclude_modules": [],
        "output_modules": [],
        "config_hints": [],
    }
    section: str | None = None
    list_sections = {"include", "flags", "modules", "exclude_modules", "output_modules"}

    for raw_line in _safe_read(path).splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            item = stripped[2:].split("#", maxsplit=1)[0].strip().strip("'\"")
            if item and section in list_sections:
                cast_list = data[section]
                if isinstance(cast_list, list):
                    cast_list.append(item)
            elif item and section == "config":
                hints = data["config_hints"]
                if isinstance(hints, list):
                    hints.append(item)
            continue
        if ":" not in stripped:
            if section == "config":
                hints = data["config_hints"]
                if isinstance(hints, list):
                    hints.append(stripped)
            continue
        key, _, remainder = stripped.partition(":")
        key = key.strip()
        value = remainder.strip().strip("'\"")
        if key == "description":
            data["description"] = value
            section = None
            continue
        if key in list_sections:
            section = key
            if value:
                cast_list = data[key]
                if isinstance(cast_list, list):
                    cast_list.append(value)
            continue
        if key == "config":
            section = "config"
            continue
        if section == "config":
            hints = data["config_hints"]
            if isinstance(hints, list):
                hints.append(stripped)
    return data


def _match_search(text: str, search: str) -> bool:
    query = str(search or "").strip().lower()
    return not query or query in text.lower()


def _find_first_dir(root: Path, name: str) -> Path | None:
    for item in root.rglob(name):
        if item.is_dir():
            return item
    return None


def _find_first_file(root: Path, name: str) -> Path | None:
    for item in root.rglob(name):
        if item.is_file():
            return item
    return None


@lru_cache(maxsize=1)
def load_recursive_module_reference(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else _detect_recursive_modules_root() or DEFAULT_TEMP_ROOT
    modules_path = base / "docs" / "modules" / "list_of_modules.md"
    recipes_dir = _find_first_dir(base, "presets")
    cli_path = _find_first_file(base, "cli.py")

    module_rows: list[dict[str, Any]] = []
    flag_to_modules: dict[str, list[str]] = {}
    for row in _parse_markdown_rows(_safe_read(modules_path)):
        if len(row) < 8:
            continue
        module_flags = [item.strip() for item in row[4].split(",") if item.strip()]
        consumes = [item.strip() for item in row[5].split(",") if item.strip()]
        produces = [item.strip() for item in row[6].split(",") if item.strip()]
        module = {
            "name": row[0],
            "type": row[1],
            "needs_api_key": row[2].lower() == "yes",
            "description": row[3],
            "flags": module_flags,
            "consumes": consumes,
            "produces": produces,
            "author": row[7],
        }
        module_rows.append(module)
        for flag in module_flags:
            flag_to_modules.setdefault(flag, []).append(str(module["name"]))

    recipes: list[dict[str, Any]] = []
    if recipes_dir and recipes_dir.exists():
        for recipe_path in sorted(recipes_dir.glob("*.yml")):
            recipes.append(_parse_simple_recipe(recipe_path))

    commands: list[dict[str, str]] = []
    if cli_path is not None:
        raw_cli = _safe_read(cli_path)
        for option in sorted(set(_OPTION_RE.findall(raw_cli))):
            label = _SOURCE_OPTION_LABELS.get(option)
            if label:
                commands.append({"id": option, "title": label})

    flags: list[dict[str, Any]] = [
        {"name": name, "count": len(modules), "modules": sorted(modules)}
        for name, modules in sorted(flag_to_modules.items(), key=lambda item: (-len(item[1]), item[0]))
    ]

    return {
        "profile": "recursive-modules",
        "path": str(base),
        "module_count": len(module_rows),
        "recipe_count": len(recipes),
        "flag_count": len(flags),
        "architecture": [
            "Event-driven and recursive scan model",
            "Recipe-driven scan composition",
            "Module flags for passive, active, safe, and aggressive selection",
            "Parallel module execution with queue-like event flow",
        ],
        "commands": commands,
        "modules": module_rows,
        "recipes": recipes,
        "flags": flags,
    }


@lru_cache(maxsize=1)
def load_graph_registry_reference(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else _detect_graph_registry_root() or DEFAULT_TEMP_ROOT
    cmd_dir = base / "cmd"
    engine_dir = base / "engine"
    plugin_dir = engine_dir / "plugins"

    commands = [path.name for path in sorted(cmd_dir.iterdir()) if path.is_dir()] if cmd_dir.exists() else []
    plugin_families = [path.name for path in sorted(plugin_dir.iterdir()) if path.is_dir()] if plugin_dir.exists() else []
    engine_components = [
        name
        for name in ("api", "dispatcher", "plugins", "pubsub", "registry", "sessions", "types")
        if (engine_dir / name).exists()
    ]

    return {
        "profile": "graph-registry",
        "path": str(base),
        "command_count": len(commands),
        "commands": commands,
        "engine_components": engine_components,
        "plugin_families": plugin_families,
        "architecture": [
            "Attack-surface mapping with open-source and active reconnaissance",
            "Dedicated registry, dispatcher, and session subsystems",
            "Separate command binaries for enumeration, tracking, visualization, and engine tasks",
            "Plugin families for brute force, scrape, DNS, enrich, and service discovery",
        ],
    }


@lru_cache(maxsize=1)
def load_console_shell_reference(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else _detect_console_shell_root() or DEFAULT_TEMP_ROOT
    return {
        "profile": "console-shell",
        "path": str(base),
        "architecture": [
            "Console-first driver and dispatcher shell pattern",
            "Banner, inventory, and prompt-centered operator workflow",
            "Interactive command routing with shell-like session UX",
        ],
    }


def load_source_inventory(temp_root: str | Path = DEFAULT_TEMP_ROOT) -> dict[str, Any]:
    base = Path(temp_root)
    profiles: list[dict[str, Any]] = []

    recursive_root = _detect_recursive_modules_root(base)
    if recursive_root is not None:
        recursive = load_recursive_module_reference(str(recursive_root))
        profiles.append(
            {
                "name": "recursive-modules",
                "path": recursive["path"],
                "summary": "Recursive event-driven collection with recipes, flags, and broad module coverage",
                "module_count": recursive["module_count"],
                "recipe_count": recursive["recipe_count"],
                "command_count": len(recursive["commands"]),
            }
        )

    graph_root = _detect_graph_registry_root(base)
    if graph_root is not None:
        graph = load_graph_registry_reference(str(graph_root))
        profiles.append(
            {
                "name": "graph-registry",
                "path": graph["path"],
                "summary": "Attack-surface engine with command families, registry control, and plugin lanes",
                "command_count": graph["command_count"],
                "engine_component_count": len(graph["engine_components"]),
                "plugin_family_count": len(graph["plugin_families"]),
            }
        )

    console_root = _detect_console_shell_root(base)
    if console_root is not None:
        console = load_console_shell_reference(str(console_root))
        profiles.append(
            {
                "name": "console-shell",
                "path": console["path"],
                "summary": "Console UX reference for prompt, inventory, spinner, and shell-style interaction",
            }
        )

    other_dirs: list[dict[str, Any]] = []
    if base.exists():
        matched = {Path(str(row.get("path", ""))).resolve() for row in profiles if isinstance(row, dict) and row.get("path")}
        for path in _iter_temp_dirs(base):
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path
            if resolved in matched:
                continue
            other_dirs.append({"name": path.name, "path": str(path)})

    return {
        "temp_root": str(base),
        "profiles": profiles,
        "other_dirs": other_dirs,
    }


def _modules_for_recipe(reference: dict[str, Any], recipe_name: str) -> list[dict[str, Any]]:
    recipe = next((row for row in reference.get("recipes", []) if row.get("name") == recipe_name), None)
    if not isinstance(recipe, dict):
        return []
    requested_names = {str(name) for name in recipe.get("modules", []) if str(name).strip()}
    requested_flags = {str(flag) for flag in recipe.get("flags", []) if str(flag).strip()}

    modules: list[dict[str, Any]] = []
    for row in reference.get("modules", []):
        if not isinstance(row, dict):
            continue
        row_name = str(row.get("name", "")).strip()
        row_flags = {str(flag) for flag in row.get("flags", []) if str(flag).strip()}
        if row_name in requested_names or requested_flags.intersection(row_flags):
            modules.append(row)
    return modules


def build_surface_recipe_plan(
    *,
    domain: str,
    recipe_name: str = "subdomain-enum",
    modules: list[str] | None = None,
    require_flags: list[str] | None = None,
    exclude_flags: list[str] | None = None,
    recon_mode: str | None = None,
    reference_root: str | Path | None = None,
) -> dict[str, Any]:
    normalized_domain = normalize_domain(domain)
    if not normalized_domain:
        raise ValueError("Invalid domain for the surface kit plan.")

    reference = load_recursive_module_reference(reference_root)
    recipe = next((row for row in reference.get("recipes", []) if row.get("name") == recipe_name), None)
    if not isinstance(recipe, dict):
        raise ValueError(f"Unknown surface recipe: {recipe_name}")

    selected_modules = _modules_for_recipe(reference, recipe_name)
    requested_module_names = {str(name).strip() for name in (modules or []) if str(name).strip()}
    required_flag_names = {str(name).strip() for name in (require_flags or []) if str(name).strip()}
    excluded_flag_names = {str(name).strip() for name in (exclude_flags or []) if str(name).strip()}

    if requested_module_names:
        selected_modules = [row for row in selected_modules if str(row.get("name", "")) in requested_module_names]
    if required_flag_names:
        selected_modules = [
            row
            for row in selected_modules
            if required_flag_names.issubset({str(flag) for flag in row.get("flags", [])})
        ]
    if excluded_flag_names:
        selected_modules = [
            row
            for row in selected_modules
            if not excluded_flag_names.intersection({str(flag) for flag in row.get("flags", [])})
        ]

    selected_flags = sorted(
        {
            str(flag)
            for row in selected_modules
            if isinstance(row, dict)
            for flag in row.get("flags", [])
            if str(flag).strip()
        }
    )

    recipe_defaults = dict(_RECIPE_TO_silica_x.get(recipe_name, {}))
    resolved_recon_mode = normalize_recon_mode(recon_mode or str(recipe_defaults.get("recon_mode", "hybrid")))
    surface_preset = str(recipe_defaults.get("surface_preset", "balanced"))
    include_ct = bool(recipe_defaults.get("include_ct", True))
    include_rdap = bool(recipe_defaults.get("include_rdap", True))

    native_capabilities = [text for flag, text in _NATIVE_CAPABILITIES.items() if flag in selected_flags]
    partial_capabilities = [text for flag, text in _PARTIAL_CAPABILITIES.items() if flag in selected_flags]
    unsupported_capabilities = [text for flag, text in _UNSUPPORTED_CAPABILITIES.items() if flag in selected_flags]
    unsupported_modules = sorted(
        str(row.get("name", ""))
        for row in selected_modules
        if {"deadly", "aggressive", "code-enum", "service-enum", "download", "email-enum"}.intersection(
            {str(flag) for flag in row.get("flags", [])}
        )
    )

    command_preview = shlex.join(
        [
            "python",
            "silica-x.py",
            "surface",
            normalized_domain,
            "--preset",
            surface_preset,
            "--recon-mode",
            resolved_recon_mode,
            "--ct" if include_ct else "--no-ct",
            "--rdap" if include_rdap else "--no-rdap",
        ]
    )

    return {
        "profile": "surface-kit",
        "target": normalized_domain,
        "recipe": {
            "name": recipe_name,
            "description": str(recipe.get("description", "")),
            "flags": list(recipe.get("flags", [])),
            "includes": list(recipe.get("include", [])),
        },
        "selected_module_count": len(selected_modules),
        "selected_flags": selected_flags,
        "selected_modules_preview": [str(row.get("name", "")) for row in selected_modules[:20]],
        "native_capabilities": native_capabilities,
        "partial_capabilities": partial_capabilities,
        "unsupported_capabilities": unsupported_capabilities,
        "unsupported_modules_preview": unsupported_modules[:20],
        "silica_x_mapping": {
            "surface_preset": surface_preset,
            "recon_mode": resolved_recon_mode,
            "include_ct": include_ct,
            "include_rdap": include_rdap,
            "coverage": str(recipe_defaults.get("coverage", "General recipe-to-surface translation")),
        },
        "execution_preview": command_preview,
        "notes": [
            "This is a native Silica-X translation of source-derived recipe intent, not a foreign engine port.",
            "Supported coverage maps into Silica-X passive, active, and hybrid surface collection lanes.",
            "Unsupported module families remain analyst follow-up areas until dedicated Silica-X engines are added.",
        ],
    }


def filter_recipe_modules(
    *,
    search: str = "",
    limit: int = 25,
    reference_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    reference = load_recursive_module_reference(reference_root)
    rows = []
    for row in reference.get("modules", []):
        if not isinstance(row, dict):
            continue
        haystack = " ".join(
            [
                str(row.get("name", "")),
                str(row.get("description", "")),
                " ".join(str(item) for item in row.get("flags", [])),
                " ".join(str(item) for item in row.get("produces", [])),
            ]
        )
        if _match_search(haystack, search):
            rows.append(row)
    return rows[: max(1, int(limit))]


def filter_recipes(
    *,
    search: str = "",
    limit: int = 25,
    reference_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    reference = load_recursive_module_reference(reference_root)
    rows = [
        row
        for row in reference.get("recipes", [])
        if isinstance(row, dict)
        and _match_search(
            " ".join(
                [
                    str(row.get("name", "")),
                    str(row.get("description", "")),
                    " ".join(str(item) for item in row.get("flags", [])),
                ]
            ),
            search,
        )
    ]
    return rows[: max(1, int(limit))]


def filter_recipe_flags(
    *,
    search: str = "",
    limit: int = 25,
    reference_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    reference = load_recursive_module_reference(reference_root)
    rows = [
        row
        for row in reference.get("flags", [])
        if isinstance(row, dict) and _match_search(str(row.get("name", "")), search)
    ]
    return rows[: max(1, int(limit))]
