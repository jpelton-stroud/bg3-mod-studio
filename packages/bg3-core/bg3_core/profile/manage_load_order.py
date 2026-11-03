#!/usr/bin/env python3
"""manage_load_order.py.

--------------------
Inspects, activates, and validates Baldur's Gate 3 mods in the user's
`modsettings.lsx` load order profile without needing to open the in-game Mod Manager.

This module serves as the primary public facade for load order operations,
re-exporting functionality decomposed into:
- modsettings_io: XML parsing, path detection, backup, enable/disable
- sorter: topological sorting and auto-sorting
- quarantine: clean-room isolation, deduplication, and quarantine management
- cli_handlers: CLI parsing and subcommand dispatch
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

# Ensure package root is in sys.path when executed directly as a script
_pkg_root = Path(__file__).resolve().parent.parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from bg3_core.profile import cli_handlers as _cli
from bg3_core.profile.cli_handlers import (
    BOLD,
    CYAN,
    GREEN,
    RED,
    RESET,
    YELLOW,
)
from bg3_core.profile.modsettings_io import (
    CORE_GUSTAV_NAMES,
    CORE_SYSTEM_MODULES,
    CORE_SYSTEM_NAMES,
    CORE_SYSTEM_UUIDS,
    GUSTAV_DEV,
    _ensure_base_module,
    _extract_dependencies_from_xml_text,
    _extract_meta_from_xml_text,
    backup_file,
    create_default_modsettings,
    detect_modsettings_path,
    disable_mod,
    enable_mod,
    get_appdata_mods_dir,
    get_mod_metadata_from_workspace,
    parse_modsettings,
    resolve_all_dependencies,
    save_modsettings,
    validate_load_order,
)
from bg3_core.profile.quarantine import (
    clean_steam_data_paks,
    deduplicate_installed_paks,
    get_pak_module_info,
    isolate_load_order,
    quarantine_unrelated_paks,
    restore_quarantined_paks,
)
from bg3_core.profile.sorter import (
    auto_sort_load_order,
    topological_sort_mods,
)


def build_load_order_parser() -> argparse.ArgumentParser:
    """Build the argument parser for manage_load_order."""
    return _cli.build_load_order_parser()


def _resolve_subcommand_aliases(args: argparse.Namespace) -> None:
    """Map positional subcommands to explicit flag combinations."""
    _cli._resolve_subcommand_aliases(args)


def _resolve_modsettings_path(args: argparse.Namespace) -> Path:
    """Resolve and validate the modsettings.lsx file path."""
    return _cli._resolve_modsettings_path(args)


def _handle_create_default(modsettings_path: Path, args: argparse.Namespace) -> None:
    """Handle the --create-default action and exit."""
    _cli._handle_create_default(modsettings_path, args)


def _dispatch_auto_sort(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle topological load order sorting."""
    _cli._dispatch_auto_sort(modsettings_path, args, action_result)


def _dispatch_restore(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle restoring quarantined mod pak archives."""
    _cli._dispatch_restore(modsettings_path, args, action_result)


def _dispatch_dedup(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle deduplicating installed paks and cleaning redundant archives."""
    _cli._dispatch_dedup(modsettings_path, args, action_result)


def _collect_test_dependencies(mod_name: str, cli_test_deps: Sequence[str]) -> list[dict]:
    """Collect and resolve metadata for declared and CLI-specified test dependencies."""
    return _cli._collect_test_dependencies(mod_name, cli_test_deps)


def _dispatch_enable(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle enabling a mod, its declared dependencies, and test dependencies."""
    _cli._dispatch_enable(modsettings_path, args, action_result)


def _dispatch_disable(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle disabling a mod from active load order."""
    _cli._dispatch_disable(modsettings_path, args, action_result)


def _dispatch_validate(
    parsed: dict[str, Any],
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Validate current load order rules and display issues."""
    _cli._dispatch_validate(parsed, args, action_result)


def _dispatch_list(parsed: dict[str, Any], modsettings_path: Path) -> None:
    """Display active load order table to stdout."""
    _cli._dispatch_list(parsed, modsettings_path)


def main() -> None:
    _cli.main()


__all__ = [
    "BOLD",
    "CORE_GUSTAV_NAMES",
    "CORE_SYSTEM_MODULES",
    "CORE_SYSTEM_NAMES",
    "CORE_SYSTEM_UUIDS",
    "CYAN",
    "GREEN",
    "GUSTAV_DEV",
    "RED",
    "RESET",
    "YELLOW",
    "_collect_test_dependencies",
    "_dispatch_auto_sort",
    "_dispatch_dedup",
    "_dispatch_disable",
    "_dispatch_enable",
    "_dispatch_list",
    "_dispatch_restore",
    "_dispatch_validate",
    "_ensure_base_module",
    "_extract_dependencies_from_xml_text",
    "_extract_meta_from_xml_text",
    "_handle_create_default",
    "_resolve_modsettings_path",
    "_resolve_subcommand_aliases",
    "auto_sort_load_order",
    "backup_file",
    "build_load_order_parser",
    "clean_steam_data_paks",
    "create_default_modsettings",
    "deduplicate_installed_paks",
    "detect_modsettings_path",
    "disable_mod",
    "enable_mod",
    "get_appdata_mods_dir",
    "get_mod_metadata_from_workspace",
    "get_pak_module_info",
    "isolate_load_order",
    "main",
    "parse_modsettings",
    "quarantine_unrelated_paks",
    "resolve_all_dependencies",
    "restore_quarantined_paks",
    "save_modsettings",
    "topological_sort_mods",
    "validate_load_order",
]

if __name__ == "__main__":
    main()
