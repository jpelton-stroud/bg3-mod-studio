#!/usr/bin/env python3
"""Baldur's Gate 3 Mod Studio — Unified 2026 CLI Suite.

Unified entrypoint providing structured noun-verb command execution, stream
discipline, and standard exit codes across the entire automation toolchain.

Usage:
    python3 scripts/bg3.py [--json] [--no-color] [--verbose] <command> <subcommand> [options...]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.cli_common import (
    ConsoleColor,
    ExitCode,
    NonInteractiveConfirmationError,
    OutputEmitter,
    confirm_action,
)

SCRIPTS_DIR = Path(__file__).resolve().parent


class JsonCompliantArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that emits JSON error envelopes when --json flag is present."""

    def error(self, message: str) -> None:
        if "--json" in sys.argv:
            emitter = OutputEmitter(json_mode=True)
            emitter.error(
                message=message,
                code="USAGE_ERROR",
                remediation="Run 'bg3 --help' or 'bg3 <command> --help' for syntax.",
                exit_code=ExitCode.USAGE,
                exit_process=True,
            )
        super().error(message)


def build_parser() -> argparse.ArgumentParser:
    """Build the unified CLI argument parser with noun-verb subcommand tree."""
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON payloads on stdout exclusively.",
    )
    common_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI terminal colors and text formatting.",
    )
    common_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed diagnostic messages on stderr.",
    )
    common_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to custom environment configuration file.",
    )

    parser = JsonCompliantArgumentParser(
        prog="bg3",
        description="Baldur's Gate 3 Mod Studio — Unified 2026 CLI Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="Commands",
        metavar="<command>",
        parser_class=JsonCompliantArgumentParser,
    )

    # -------------------------------------------------------------------------
    # 'mod' command group
    # -------------------------------------------------------------------------
    mod_parser = subparsers.add_parser(
        "mod",
        help="Mod authoring, validation, and collision detection",
        parents=[common_parser],
    )
    mod_subparsers = mod_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    # bg3 mod conflict
    conflict_parser = mod_subparsers.add_parser(
        "conflict",
        help="Detect stat, progression, or root template collisions between mods",
        parents=[common_parser],
    )
    conflict_parser.add_argument(
        "candidate",
        nargs="?",
        help="Candidate mod name, directory, or path to inspect.",
    )
    conflict_parser.add_argument(
        "--against-library",
        action="store_true",
        help="Compare candidate against all cataloged mods in mods/.",
    )
    conflict_parser.add_argument(
        "--mod2",
        help="Second mod path or identifier to compare against directly.",
    )
    conflict_parser.add_argument(
        "--all",
        action="store_true",
        help="Cross-check all active mods across my_mods/ and mods/.",
    )

    # bg3 mod validate
    validate_parser = mod_subparsers.add_parser(
        "validate",
        help="Validate mod folder structure, meta.lsx, and localization entries",
        parents=[common_parser],
    )
    validate_parser.add_argument(
        "mod_identifier",
        help="Target mod slug, folder name, or directory path to validate.",
    )
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on non-critical warnings.",
    )
    validate_parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt automated remediation for missing UUIDs or sync issues.",
    )

    # bg3 mod scaffold
    scaffold_parser = mod_subparsers.add_parser(
        "scaffold",
        help="Scaffold a new mod workspace in my_mods/",
        parents=[common_parser],
    )
    scaffold_parser.add_argument(
        "name",
        help="Display name or slug for the new mod.",
    )
    scaffold_parser.add_argument(
        "--slug",
        help="Custom folder slug (default: derived from name).",
    )
    scaffold_parser.add_argument(
        "--uuid",
        help="Explicit ModuleUUID GUID.",
    )
    scaffold_parser.add_argument(
        "--author",
        help="Author name (defaults to configured environment author).",
    )
    scaffold_parser.add_argument(
        "--description",
        help="In-game and mod.io description.",
    )
    scaffold_parser.add_argument(
        "--version",
        default="1.0.0.0",
        help="Initial semantic Version64 (default: 1.0.0.0).",
    )
    scaffold_parser.add_argument(
        "--unlock-level-curve",
        action="store_true",
        help="Add UnlockLevelCurve compatibility and progression boost table.",
    )
    scaffold_parser.add_argument(
        "--dependency",
        action="append",
        default=[],
        help="Dependency mod slug or UUID to register in meta.lsx.",
    )
    scaffold_parser.add_argument(
        "--output-dir",
        help="Custom output directory (defaults to my_mods/<slug>).",
    )
    scaffold_parser.add_argument(
        "--type",
        default="Standard",
        choices=["Standard", "Class", "Subclass", "Item", "Spell", "Cosmetic"],
        help="Mod template archetype (default: Standard).",
    )
    scaffold_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview generated files without writing to disk.",
    )

    # bg3 mod add-dependency
    add_dep_parser = mod_subparsers.add_parser(
        "add-dependency",
        help="Append dependencies or test dependencies to a custom mod",
        parents=[common_parser],
    )
    add_dep_parser.add_argument("mod", help="Target mod name or slug")
    add_dep_parser.add_argument("dependencies", nargs="*", help="Dependency mod slugs or names")
    add_dep_parser.add_argument("--dep", action="append", default=[], help="Explicit dependency slug")
    add_dep_parser.add_argument("--test-dep", action="append", default=[], help="Explicit test dependency slug")
    add_dep_parser.add_argument("--test-only", action="store_true", help="Mark dependencies as test-only")
    add_dep_parser.add_argument("--dry-run", action="store_true", help="Preview metadata changes without saving")

    # bg3 mod bump-version
    bump_parser = mod_subparsers.add_parser(
        "bump-version",
        aliases=["bump_version"],
        help="Increment semantic Version64 across meta.lsx and README.md",
        parents=[common_parser],
    )
    bump_parser.add_argument("mod", nargs="?", help="Mod slug or directory")
    bump_group = bump_parser.add_mutually_exclusive_group()
    bump_group.add_argument("--patch", "-p", action="store_true", help="Increment patch version")
    bump_group.add_argument("--minor", "-m", action="store_true", help="Increment minor version")
    bump_group.add_argument("--major", action="store_true", help="Increment major version")
    bump_group.add_argument("--build", "-b", action="store_true", help="Increment build integer")
    bump_group.add_argument("--show", action="store_true", help="Display current version without modifying")
    bump_group.add_argument("--set", help="Explicit version string (e.g. 1.2.0.0)")
    bump_parser.add_argument("--dry-run", action="store_true", help="Preview version changes without writing to disk")

    # bg3 mod pack
    pack_parser = mod_subparsers.add_parser(
        "pack",
        help="Build a game-ready LSPK .pak archive from my_mods/<slug>",
        parents=[common_parser],
    )
    pack_parser.add_argument("mod", help="Mod slug or directory")
    pack_parser.add_argument("--out", "--output", dest="output", help="Output .pak file path")
    pack_parser.add_argument("--output-dir", help="Output directory for generated .pak file")
    pack_parser.add_argument("--publish-local", action="store_true", help="Publish .pak directly to local BG3 Mods directory")
    pack_parser.add_argument("--clean-local", action="store_true", help="Purge local test .pak file(s) for this mod")
    pack_parser.add_argument("--include-projects", action="store_true", help="Include Projects/ directory")
    pack_parser.add_argument("--uncompressed", action="store_true", help="Store files uncompressed")
    pack_parser.add_argument("--dry-run", action="store_true", help="Preview operations without modifying files")

    # bg3 mod sync-loca
    loca_parser = mod_subparsers.add_parser(
        "sync-loca",
        aliases=["sync_loca"],
        help="Audit, prune, or compile Localization XML handles",
        parents=[common_parser],
    )
    loca_parser.add_argument("mod", help="Mod slug or directory")
    loca_parser.add_argument("--check", action="store_true", help="Check for orphaned or missing handles")
    loca_parser.add_argument("--prune", action="store_true", help="Prune orphaned localization handles")
    loca_parser.add_argument("--backup", action="store_true", help="Backup localization files before modifying")
    loca_parser.add_argument("--compile", action="store_true", help="Compile localization XML to binary .loca")
    loca_parser.add_argument("--sync-languages", action="store_true", help="Synchronize handles across language files")
    loca_parser.add_argument("--dry-run", action="store_true", help="Preview localization actions")

    # bg3 mod sync-game
    sync_game_parser = mod_subparsers.add_parser(
        "sync-game",
        aliases=["sync_game"],
        help="Synchronize unpacked mod assets and compiled .loca to BG3 Data directory",
        parents=[common_parser],
    )
    sync_game_parser.add_argument("--mods", nargs="*", help="Specific mod slugs to synchronize")
    sync_game_parser.add_argument("--source-dir", help="Source directory containing mods (default: my_mods)")
    sync_game_parser.add_argument("--data-dir", help="Baldur's Gate 3 Data directory path")
    sync_game_parser.add_argument("--clean-legacy", action="store_true", help="Clean up legacy mod folders/files in Steam Data")
    sync_game_parser.add_argument("--no-clean-legacy", action="store_true", help="Disable automatic cleaning of legacy mod folders")
    sync_game_parser.add_argument("--clean-custom", action="store_true", help="Purge custom studio mods from Steam Data")
    sync_game_parser.add_argument("--clean-mod", help="Purge a specific custom mod's loose files from Steam Data")
    sync_game_parser.add_argument("--bump-build", action="store_true", help="Increment build number (+1) in meta.lsx")
    sync_game_parser.add_argument("--watch", action="store_true", help="Watch source directory and sync continuously")
    sync_game_parser.add_argument("--interval", type=float, default=2.0, help="Watch interval in seconds")
    sync_game_parser.add_argument("--dry-run", action="store_true", help="Preview file sync operations")

    # bg3 mod patch
    patch_parser = mod_subparsers.add_parser(
        "patch",
        help="Generate compatibility override patch or Compatibility Framework config",
        parents=[common_parser],
    )
    patch_parser.add_argument("--mod1", required=True, help="First mod slug or directory")
    patch_parser.add_argument("--mod2", required=True, help="Second mod slug or directory")
    patch_parser.add_argument("--name", help="Patch mod name")
    patch_parser.add_argument("--mode", choices=["standalone", "cf"], default="standalone", help="Patch format")
    patch_parser.add_argument("--dry-run", action="store_true", help="Preview generated patch files")

    # bg3 mod diagnose-logs
    diag_parser = mod_subparsers.add_parser(
        "diagnose-logs",
        aliases=["diagnose_logs"],
        help="Diagnose BG3 Toolkit runtime logs and triage errors",
        parents=[common_parser],
    )
    diag_parser.add_argument("--mod", help="Target mod name or slug")
    diag_parser.add_argument("--toolkit-dir", help="Path to BG3 Toolkit directory")
    diag_parser.add_argument("--type", choices=["general", "crash", "assert", "all"], default="general")
    diag_parser.add_argument("--severity", choices=["error", "warning", "info", "all"], default="error")
    diag_parser.add_argument("--subsystem", help="Filter by engine subsystem")
    diag_parser.add_argument("--limit", type=int, default=50, help="Max entries to report")
    diag_parser.add_argument("-f", "--follow", action="store_true", help="Follow logs live")
    diag_parser.add_argument("--list-logs", action="store_true", help="List available log files")
    diag_parser.add_argument("--info", action="store_true", help="Show log metadata")

    # bg3 mod inspect-save
    inspect_save_parser = mod_subparsers.add_parser(
        "inspect-save",
        aliases=["inspect_save"],
        help="Inspect Baldur's Gate 3 save games and audit mod dependencies",
        parents=[common_parser],
    )
    inspect_save_parser.add_argument("save", nargs="?", help="Path to .lsv save game file")
    inspect_save_parser.add_argument("--save-dir", help="Custom save directory")
    inspect_save_parser.add_argument("--audit", action="store_true", help="Audit active mods against save requirements")

    # bg3 mod inject-treasure
    inject_parser = mod_subparsers.add_parser(
        "inject-treasure",
        aliases=["inject_treasure"],
        help="Inject mod item into world container treasure tables",
        parents=[common_parser],
    )
    inject_parser.add_argument("--mod", required=True, help="Target mod name or slug")
    inject_parser.add_argument("--item", required=True, help="Stat entry name or root template map key")
    inject_parser.add_argument("--container", help="Container or table name (e.g. TUT_Chest_Potions)")
    inject_parser.add_argument("--count", type=int, default=1, help="Drop count")
    inject_parser.add_argument("--ratio", type=int, default=1, help="Drop ratio frequency")
    inject_parser.add_argument("--start-level", type=int, default=1, help="Min character level")
    inject_parser.add_argument("--raw-item-name", action="store_true", help="Treat item name as raw stat entry")
    inject_parser.add_argument("--list-containers", action="store_true", help="List common container tables")
    inject_parser.add_argument("--dry-run", action="store_true", help="Preview table modifications")

    # bg3 mod render-desc
    render_desc_parser = mod_subparsers.add_parser(
        "render-desc",
        aliases=["render_desc"],
        help="Render mod.io HTML description from README.md",
        parents=[common_parser],
    )
    render_desc_parser.add_argument("mod", help="Target mod name or slug")
    render_desc_parser.add_argument("--write", action="store_true", help="Write modio_description.html to mod dir")

    # -------------------------------------------------------------------------
    # 'loadorder' command group
    # -------------------------------------------------------------------------
    lo_parser = subparsers.add_parser(
        "loadorder",
        help="Player profile modsettings.lsx load order management",
        parents=[common_parser],
    )
    lo_subparsers = lo_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    lo_list_parser = lo_subparsers.add_parser(
        "list",
        help="List active mods in the current modsettings.lsx profile",
        parents=[common_parser],
    )
    lo_list_parser.add_argument(
        "--profile",
        help="Specify custom profile name or directory.",
    )

    lo_sync_parser = lo_subparsers.add_parser(
        "sync",
        help="Synchronize my_mods into the active load order profile",
        parents=[common_parser],
    )
    lo_sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing modsettings.lsx.",
    )
    lo_sync_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Bypass interactive confirmation in non-interactive sessions.",
    )

    lo_clean_parser = lo_subparsers.add_parser(
        "clean",
        help="Remove missing or invalid mod entries from load order",
        parents=[common_parser],
    )
    lo_clean_parser.add_argument(
        "--path",
        help="Explicit path to modsettings.lsx.",
    )
    lo_clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleaned load order without saving.",
    )
    lo_clean_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Bypass interactive confirmation in non-interactive sessions.",
    )

    # bg3 loadorder enable
    lo_enable_parser = lo_subparsers.add_parser(
        "enable",
        aliases=["activate"],
        help="Enable a mod in active load order",
        parents=[common_parser],
    )
    lo_enable_parser.add_argument("mod", help="Mod name, slug, or UUID to enable")
    lo_enable_parser.add_argument("--order", type=int, help="Target 1-indexed load order position")
    lo_enable_parser.add_argument("--with-deps", action="store_true", default=True, help="Automatically enable declared dependencies")
    lo_enable_parser.add_argument("--no-deps", action="store_false", dest="with_deps", help="Do not automatically enable dependencies")
    lo_enable_parser.add_argument("--test-dep", action="append", default=[], help="Activate test dependency ahead of mod")
    lo_enable_parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    lo_enable_parser.add_argument("--dry-run", action="store_true", help="Preview modifications without saving")

    # bg3 loadorder disable
    lo_disable_parser = lo_subparsers.add_parser(
        "disable",
        help="Disable a mod in active load order",
        parents=[common_parser],
    )
    lo_disable_parser.add_argument("mod", help="Mod name, slug, or UUID to disable")
    lo_disable_parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    lo_disable_parser.add_argument("--dry-run", action="store_true", help="Preview modifications without saving")

    # bg3 loadorder validate
    lo_val_parser = lo_subparsers.add_parser(
        "validate",
        help="Validate active load order against dependency and ordering rules",
        parents=[common_parser],
    )
    lo_val_parser.add_argument("--path", help="Explicit path to modsettings.lsx")

    # bg3 loadorder isolate
    lo_iso_parser = lo_subparsers.add_parser(
        "isolate",
        help="Clean-room isolation: disable all mods except target mod and dependencies",
        parents=[common_parser],
    )
    lo_iso_parser.add_argument("mod", help="Target mod name or slug to isolate")
    lo_iso_parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    lo_iso_parser.add_argument("--dry-run", action="store_true", help="Preview modifications without saving")
    lo_iso_parser.add_argument("-y", "--yes", action="store_true", help="Confirm non-interactively")

    # -------------------------------------------------------------------------
    # 'modio' command group
    # -------------------------------------------------------------------------
    modio_parser = subparsers.add_parser(
        "modio",
        help="Mod.io integration (search, sync, extract, update)",
        parents=[common_parser],
    )
    modio_subparsers = modio_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    modio_search_parser = modio_subparsers.add_parser(
        "search",
        help="Search Baldur's Gate 3 community mods on mod.io",
        parents=[common_parser],
    )
    modio_search_parser.add_argument(
        "query",
        help="Search keywords or intent.",
    )
    modio_search_parser.add_argument(
        "-p", "--platform",
        choices=["pc", "mac", "ps5", "xbox", "all"],
        default="all",
        help="Target platform filter (default: all).",
    )
    modio_search_parser.add_argument(
        "--include-tracked",
        action="store_true",
        help="Include already tracked mods in search results.",
    )
    modio_search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum results to return (default: 10).",
    )

    modio_sync_parser = modio_subparsers.add_parser(
        "sync",
        help="Synchronize tracked mods from mod.io",
        parents=[common_parser],
    )
    modio_sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview updates without downloading or extracting.",
    )
    modio_sync_parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove unsubscribed mods from library.md and delete applicable mod folders.",
    )
    modio_sync_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of new subscribed mods to extract and document.",
    )
    modio_sync_parser.add_argument(
        "--filter",
        help="Filter subscribed mods by name or slug substring.",
    )
    modio_sync_parser.add_argument(
        "--skip-updates",
        action="store_true",
        help="Skip checking/updating existing documented mods.",
    )
    modio_sync_parser.add_argument(
        "--token", "-t",
        help="mod.io OAuth 2.0 Personal Access Token.",
    )
    modio_sync_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Bypass interactive confirmation in non-interactive sessions.",
    )

    # bg3 modio extract
    modio_extract_parser = modio_subparsers.add_parser(
        "extract",
        help="Download and extract mod.io .pak archive and document in library",
        parents=[common_parser],
    )
    modio_extract_parser.add_argument("query", nargs="?", help="Mod slug, name, or URL")
    modio_extract_parser.add_argument("--pak", help="Local .pak file path to extract")
    modio_extract_parser.add_argument("-o", "--output-dir", help="Output directory")
    modio_extract_parser.add_argument("--write-spec", action="store_true", help="Generate README specification")
    modio_extract_parser.add_argument("--update-library", action="store_true", help="Update mods/library.md entry")

    # bg3 modio update
    modio_update_parser = modio_subparsers.add_parser(
        "update",
        help="Check and update tracked mods from mod.io",
        parents=[common_parser],
    )
    modio_update_parser.add_argument("query", nargs="?", help="Specific mod slug or directory")
    modio_update_parser.add_argument("--all", action="store_true", help="Check all tracked mods")
    modio_update_parser.add_argument("--check-only", action="store_true", help="Report updates without downloading")
    modio_update_parser.add_argument("--force", action="store_true", help="Force redownload even if up-to-date")
    modio_update_parser.add_argument("--list-tracked", action="store_true", help="List all tracked mods")

    # bg3 modio update-metadata
    modio_meta_parser = modio_subparsers.add_parser(
        "update-metadata",
        aliases=["update_metadata"],
        help="Update mod.io tags, metadata, and visibility",
        parents=[common_parser],
    )
    modio_meta_parser.add_argument("--mod", required=True, help="Target mod name or slug")
    modio_meta_parser.add_argument("--tags", nargs="*", help="Tags to assign on mod.io")
    modio_meta_parser.add_argument("--confirm", action="store_true", help="Apply updates without prompting")

    # bg3 modio create-collection
    modio_coll_parser = modio_subparsers.add_parser(
        "create-collection",
        aliases=["create_collection"],
        help="Generate or update public mod.io collection from library.md",
        parents=[common_parser],
    )
    modio_coll_parser.add_argument("--library", default="mods/library.md", help="Path to library.md")
    modio_coll_parser.add_argument("--dry-run", action="store_true", help="Preview collection payload")

    # bg3 modio purge
    modio_purge_parser = modio_subparsers.add_parser(
        "purge",
        help="Purge local mod folders and reset library.md",
        parents=[common_parser],
    )
    modio_purge_parser.add_argument("-n", "--dry-run", action="store_true", help="Preview purge operations")
    modio_purge_parser.add_argument("-f", "--force", action="store_true", help="Force deletion without prompt")
    modio_purge_parser.add_argument("-y", "--yes", action="store_true", help="Confirm non-interactively")
    modio_purge_parser.add_argument("--mods-dir", help="Custom mods directory")
    modio_purge_parser.add_argument("--library-path", help="Custom library.md path")

    # bg3 modio update-catalog
    modio_cat_parser = modio_subparsers.add_parser(
        "update-catalog",
        aliases=["update_catalog"],
        help="Regenerate mods/library.md catalog from mods/ README files",
        parents=[common_parser],
    )
    modio_cat_parser.add_argument("--write", action="store_true", help="Write regenerated catalog to library.md")
    modio_cat_parser.add_argument("--check", action="store_true", help="Check for drift without writing")
    modio_cat_parser.add_argument("--stdout", action="store_true", help="Output catalog to stdout")

    # -------------------------------------------------------------------------
    # 'scaffold' command group
    # -------------------------------------------------------------------------
    scaffold_grp_parser = subparsers.add_parser(
        "scaffold",
        help="Scaffold mod assets, stat entries, progressions, and templates",
        parents=[common_parser],
    )
    scaffold_grp_subparsers = scaffold_grp_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    # bg3 scaffold stat
    sc_stat = scaffold_grp_subparsers.add_parser("stat", help="Scaffold Larian stat entries with string handles", parents=[common_parser])
    sc_stat.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_stat.add_argument("--type", required=True, help="Stat type: Weapon, Armor, PassiveData, Spell_*, etc.")
    sc_stat.add_argument("--name", required=True, help="Internal stat identifier")
    sc_stat.add_argument("--display-name", help="In-game display name")
    sc_stat.add_argument("--description", help="In-game description")
    sc_stat.add_argument("--using", help="Base stat entry to inherit from")
    sc_stat.add_argument("--props", nargs="*", help="Key-value property pairs (e.g. Damage=1d8)")
    sc_stat.add_argument("--dry-run", action="store_true", help="Preview generated stat entry")

    # bg3 scaffold progression
    sc_prog = scaffold_grp_subparsers.add_parser("progression", help="Scaffold Class/Subclass progression node", parents=[common_parser])
    sc_prog.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_prog.add_argument("--class", dest="class_name", required=True, help="Target Class name (e.g. Paladin)")
    sc_prog.add_argument("--level", type=int, required=True, help="Progression level (1-20)")
    sc_prog.add_argument("--subclass", help="Subclass name if applicable")
    sc_prog.add_argument("--table-uuid", help="Explicit ProgressionTableUUID")
    sc_prog.add_argument("--passives", nargs="*", help="Passives to award")
    sc_prog.add_argument("--boosts", nargs="*", help="Boosts to award")
    sc_prog.add_argument("--spells", nargs="*", help="Spells/selectors to award")
    sc_prog.add_argument("--spell-count", type=int, default=1, help="Spell selector count")
    sc_prog.add_argument("--feat", action="store_true", help="Award feat at this level")
    sc_prog.add_argument("--dry-run", action="store_true", help="Preview progression LSX node")

    # bg3 scaffold root-template
    sc_root = scaffold_grp_subparsers.add_parser("root-template", aliases=["root_template"], help="Scaffold physical item RootTemplate", parents=[common_parser])
    sc_root.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_root.add_argument("--item", required=True, help="Item root template name")
    sc_root.add_argument("--visual-preset", help="Visual preset archetype")
    sc_root.add_argument("--parent-template", help="Parent template UUID")
    sc_root.add_argument("--display-handle", help="Display name handle")
    sc_root.add_argument("--description-handle", help="Description handle")
    sc_root.add_argument("--icon", help="Icon name")
    sc_root.add_argument("--no-link-stat", action="store_true", help="Do not link Stats property")
    sc_root.add_argument("--list-presets", action="store_true", help="List available visual presets")
    sc_root.add_argument("--dry-run", action="store_true", help="Preview root template XML")

    # bg3 scaffold icon-uvs
    sc_icons = scaffold_grp_subparsers.add_parser("icon-uvs", aliases=["icon_uvs"], help="Generate atlas icon coordinates and LSX definitions", parents=[common_parser])
    sc_icons.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_icons.add_argument("--icon-names", nargs="*", help="List of icon names")
    sc_icons.add_argument("--icons-dir", help="Directory containing source icons")
    sc_icons.add_argument("--atlas-name", help="Atlas texture name")
    sc_icons.add_argument("--atlas-uuid", help="Atlas resource UUID")
    sc_icons.add_argument("--icon-size", type=int, default=64, help="Icon dimension in pixels")
    sc_icons.add_argument("--atlas-size", type=int, default=2048, help="Atlas texture dimension")
    sc_icons.add_argument("--dry-run", action="store_true", help="Preview icon UV LSX definitions")

    # -------------------------------------------------------------------------
    # 'query' command group
    # -------------------------------------------------------------------------
    query_parser = subparsers.add_parser(
        "query",
        help="Query high-speed BiS gear, spell, and mechanics database",
        parents=[common_parser],
    )
    query_parser.add_argument("search", nargs="?", help="General search term across name, description, boosts, and passives")
    query_parser.add_argument("--slot", help="Filter by equipment slot (Amulet, Ring, Boots, Weapon, Cloak)")
    query_parser.add_argument("--boost", help="Filter by boost effect (SpellSaveDC, AC, CriticalHit)")
    query_parser.add_argument("--passive", help="Filter by passive effect (ExtraAttack, Lifedrinker)")
    query_parser.add_argument("--rarity", help="Filter by item rarity (Rare, VeryRare, Legendary)")
    query_parser.add_argument("--mod", help="Filter by mod slug/name")
    query_parser.add_argument("--limit", type=int, default=10, help="Maximum results to display")
    query_parser.add_argument("--compact", action="store_true", help="Output compact records")
    query_parser.add_argument("--reindex", action="store_true", help="Force rebuild of index")

    # -------------------------------------------------------------------------
    # 'build' command group
    # -------------------------------------------------------------------------
    build_parser = subparsers.add_parser(
        "build",
        aliases=["sim"],
        help="Character build theorycrafting and combat simulation",
        parents=[common_parser],
    )
    build_subparsers = build_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )
    sim_parser = build_subparsers.add_parser(
        "simulate",
        aliases=["sim"],
        help="Simulate Level 20 character build stats, spell slots, AC, and Turn 1 DPR",
        parents=[common_parser],
    )
    sim_parser.add_argument("--classes", help="Class distribution (e.g. 'Paladin 12, Warlock 8')")
    sim_parser.add_argument("--stats", help="Base ability scores (e.g. 'STR 16, CHA 16')")
    sim_parser.add_argument("--gear", nargs="*", help="Equipped cataloged items")
    sim_parser.add_argument("--dpr-sequence", help="Turn 1 attack sequence")
    sim_parser.add_argument("--target-ac", type=int, default=18, help="Target enemy Armor Class")
    sim_parser.add_argument("--haste", action="store_true", help="Include Haste additional action")
    sim_parser.add_argument("--advantage", action="store_true", help="Roll attacks with Advantage")

    # -------------------------------------------------------------------------
    # 'tools' command group
    # -------------------------------------------------------------------------
    tools_parser = subparsers.add_parser(
        "tools",
        help="Tool registry discovery, verification, and inspection",
        parents=[common_parser],
    )
    tools_subparsers = tools_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )
    tools_list_parser = tools_subparsers.add_parser("list", help="List studio automation tools", parents=[common_parser])
    tools_list_parser.add_argument("--category", help="Filter by category")
    tools_list_parser.add_argument("--categories", action="store_true", help="List all tool categories and descriptions")
    tools_list_parser.add_argument("--full", action="store_true", help="Include full schemas, flags, and examples")

    tools_search_parser = tools_subparsers.add_parser("search", help="Search studio tools by intent or keyword", parents=[common_parser])
    tools_search_parser.add_argument("query", help="Keyword or intent")

    tools_info_parser = tools_subparsers.add_parser("info", help="Inspect tool documentation and flags", parents=[common_parser])
    tools_info_parser.add_argument("tool_name", help="Tool name or command")

    tools_verify_parser = tools_subparsers.add_parser("verify", help="Verify tool syntax and registry integrity", parents=[common_parser])
    tools_verify_parser.add_argument("--audit-skills", action="store_true", help="Audit skill references")

    # -------------------------------------------------------------------------
    # 'env' command group
    # -------------------------------------------------------------------------
    env_parser = subparsers.add_parser(
        "env",
        help="Studio environment configuration and path diagnostics",
        parents=[common_parser],
    )
    env_subparsers = env_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    env_subparsers.add_parser(
        "check",
        help="Perform non-interactive path, tool, and environment health check",
        parents=[common_parser],
    )

    env_subparsers.add_parser(
        "paths",
        help="Display canonical XDG Base Directory specification paths and status",
        parents=[common_parser],
    )

    env_setup_parser = env_subparsers.add_parser(
        "setup",
        help="Run environment setup wizard",
        parents=[common_parser],
    )
    env_setup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview configuration changes without writing to disk.",
    )

    # -------------------------------------------------------------------------
    # 'run' universal runner for all scripts/ tools
    # -------------------------------------------------------------------------
    run_parser = subparsers.add_parser(
        "run",
        help="Execute any studio automation script from scripts/ with stream discipline",
        parents=[common_parser],
    )
    run_parser.add_argument(
        "tool",
        help="Script name (e.g. add_mod_dependency.py or add_mod_dependency)",
    )
    run_parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded directly to the tool",
    )

    return parser


def dispatch_command(args: argparse.Namespace, emitter: OutputEmitter) -> int:
    """Route parsed CLI arguments to the target implementation script."""
    cmd = args.command
    sub = getattr(args, "subcommand", None)

    if not cmd or (cmd not in ("run", "query") and not sub):
        emitter.error(
            message="Missing required command and action. Run 'bg3 --help' for available commands.",
            code="MISSING_COMMAND",
            exit_code=ExitCode.USAGE,
            exit_process=False,
        )
        return ExitCode.USAGE

    # Build underlying invocation
    script_target: Optional[Path] = None
    target_args: List[str] = []

    if cmd == "run":
        tool_name = args.tool
        if not tool_name.endswith(".py"):
            target = SCRIPTS_DIR / f"{tool_name}.py"
        else:
            target = SCRIPTS_DIR / tool_name

        if not target.is_file():
            reg_path = SCRIPTS_DIR / "registry.json"
            if reg_path.is_file():
                try:
                    with open(reg_path, "r", encoding="utf-8") as f:
                        reg_data = json.load(f)
                    for t in reg_data.get("tools", []):
                        t_name = t.get("name", "")
                        t_cmd = t.get("command", "")
                        if tool_name in (t_name, t_cmd, t_name.replace(".py", "")):
                            target = SCRIPTS_DIR / t_name
                            break
                except Exception:
                    pass

        script_target = target
        if getattr(args, "extra_args", None):
            target_args.extend(args.extra_args)

    elif cmd == "mod":
        if sub == "conflict":
            script_target = SCRIPTS_DIR / "check_mod_conflicts.py"
            if args.all:
                target_args.append("--all")
            elif args.mod2 and args.candidate:
                target_args.extend(["--mod1", args.candidate, "--mod2", args.mod2])
            elif args.candidate:
                target_args.extend(["--candidate", args.candidate])
                if args.against_library:
                    target_args.append("--against-library")
            else:
                emitter.error(
                    message="bg3 mod conflict requires a candidate mod or --all.",
                    code="INVALID_ARGUMENTS",
                    exit_code=ExitCode.USAGE,
                    exit_process=False,
                )
                return ExitCode.USAGE

        elif sub == "validate":
            script_target = SCRIPTS_DIR / "validate_mod.py"
            if getattr(args, "mod_identifier", None):
                target_args.append(args.mod_identifier)
            if getattr(args, "all", False):
                target_args.append("--all")
            if getattr(args, "strict", False):
                target_args.append("--strict")
            if getattr(args, "fix", False):
                target_args.append("--fix")

        elif sub == "scaffold":
            script_target = SCRIPTS_DIR / "create_mod_scaffold.py"
            target_args.extend(["--name", args.name])
            if getattr(args, "slug", None):
                target_args.extend(["--slug", args.slug])
            if getattr(args, "uuid", None):
                target_args.extend(["--uuid", args.uuid])
            if getattr(args, "author", None):
                target_args.extend(["--author", args.author])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "version", None):
                target_args.extend(["--version", args.version])
            if getattr(args, "unlock_level_curve", False):
                target_args.append("--unlock-level-curve")
            for dep in getattr(args, "dependency", []):
                target_args.extend(["--dependency", dep])
            if getattr(args, "output_dir", None):
                target_args.extend(["--output-dir", args.output_dir])
            if getattr(args, "type", None):
                target_args.extend(["--type", args.type])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub == "add-dependency":
            script_target = SCRIPTS_DIR / "add_mod_dependency.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "dependencies", None):
                target_args.extend(args.dependencies)
            for d in getattr(args, "dep", []):
                target_args.extend(["--dep", d])
            for td in getattr(args, "test_dep", []):
                target_args.extend(["--test-dep", td])
            if getattr(args, "test_only", False):
                target_args.append("--test-only")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("bump-version", "bump_version"):
            script_target = SCRIPTS_DIR / "bump_mod_version.py"
            if getattr(args, "mod", None):
                target_args.extend(["--mod", args.mod])
            if getattr(args, "patch", False):
                target_args.append("--patch")
            elif getattr(args, "minor", False):
                target_args.append("--minor")
            elif getattr(args, "major", False):
                target_args.append("--major")
            elif getattr(args, "build", False):
                target_args.append("--build")
            elif getattr(args, "show", False):
                target_args.append("--show")
            elif getattr(args, "set", None):
                target_args.extend(["--set", args.set])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub == "pack":
            script_target = SCRIPTS_DIR / "pack_mod_pak.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "output", None):
                target_args.extend(["--out", args.output])
            if getattr(args, "output_dir", None):
                target_args.extend(["--output-dir", args.output_dir])
            if getattr(args, "publish_local", False):
                target_args.append("--publish-local")
            if getattr(args, "clean_local", False):
                target_args.append("--clean-local")
            if getattr(args, "include_projects", False):
                target_args.append("--include-projects")
            if getattr(args, "uncompressed", False):
                target_args.append("--uncompressed")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("sync-loca", "sync_loca"):
            script_target = SCRIPTS_DIR / "sync_localization.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "check", False):
                target_args.append("--check")
            if getattr(args, "prune", False):
                target_args.append("--prune")
            if getattr(args, "backup", False):
                target_args.append("--backup")
            if getattr(args, "compile", False):
                target_args.append("--compile")
            if getattr(args, "sync_languages", False):
                target_args.append("--sync-languages")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("sync-game", "sync_game"):
            script_target = SCRIPTS_DIR / "sync_game_data.py"
            if getattr(args, "mods", None):
                target_args.extend(["--mods"] + args.mods)
            if getattr(args, "source_dir", None):
                target_args.extend(["--source-dir", args.source_dir])
            if getattr(args, "data_dir", None):
                target_args.extend(["--data-dir", args.data_dir])
            if getattr(args, "clean_legacy", False):
                target_args.append("--clean-legacy")
            if getattr(args, "no_clean_legacy", False):
                target_args.append("--no-clean-legacy")
            if getattr(args, "clean_custom", False):
                target_args.append("--clean-custom")
            if getattr(args, "clean_mod", None):
                target_args.extend(["--clean-mod", args.clean_mod])
            if getattr(args, "bump_build", False):
                target_args.append("--bump-build")
            if getattr(args, "watch", False):
                target_args.append("--watch")
            if getattr(args, "interval", None) is not None:
                target_args.extend(["--interval", str(args.interval)])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub == "patch":
            script_target = SCRIPTS_DIR / "generate_compat_patch.py"
            target_args.extend(["--mod1", args.mod1, "--mod2", args.mod2])
            if getattr(args, "name", None):
                target_args.extend(["--name", args.name])
            if getattr(args, "mode", None):
                target_args.extend(["--mode", args.mode])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("diagnose-logs", "diagnose_logs"):
            script_target = SCRIPTS_DIR / "diagnose_toolkit_logs.py"
            if getattr(args, "mod", None):
                target_args.extend(["--mod", args.mod])
            if getattr(args, "toolkit_dir", None):
                target_args.extend(["--toolkit-dir", args.toolkit_dir])
            if getattr(args, "type", None):
                target_args.extend(["--type", args.type])
            if getattr(args, "severity", None):
                target_args.extend(["--severity", args.severity])
            if getattr(args, "subsystem", None):
                target_args.extend(["--subsystem", args.subsystem])
            if getattr(args, "limit", None) is not None:
                target_args.extend(["--limit", str(args.limit)])
            if getattr(args, "follow", False):
                target_args.append("--follow")
            if getattr(args, "list_logs", False):
                target_args.append("--list-logs")
            if getattr(args, "info", False):
                target_args.append("--info")

        elif sub in ("inspect-save", "inspect_save"):
            script_target = SCRIPTS_DIR / "inspect_save_game.py"
            if getattr(args, "save", None):
                target_args.extend(["--save", args.save])
            if getattr(args, "save_dir", None):
                target_args.extend(["--save-dir", args.save_dir])
            if getattr(args, "audit", False):
                target_args.append("--audit")

        elif sub in ("inject-treasure", "inject_treasure"):
            script_target = SCRIPTS_DIR / "inject_treasure_table.py"
            target_args.extend(["--mod", args.mod, "--item", args.item])
            if getattr(args, "container", None):
                target_args.extend(["--container", args.container])
            if getattr(args, "count", None) is not None:
                target_args.extend(["--count", str(args.count)])
            if getattr(args, "ratio", None) is not None:
                target_args.extend(["--ratio", str(args.ratio)])
            if getattr(args, "start_level", None) is not None:
                target_args.extend(["--start-level", str(args.start_level)])
            if getattr(args, "raw_item_name", False):
                target_args.append("--raw-item-name")
            if getattr(args, "list_containers", False):
                target_args.append("--list-containers")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("render-desc", "render_desc"):
            script_target = SCRIPTS_DIR / "render_modio_description.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "write", False):
                target_args.append("--write")

    elif cmd == "loadorder":
        script_target = SCRIPTS_DIR / "manage_load_order.py"
        if sub == "list":
            target_args.append("--list")
            if getattr(args, "profile", None):
                target_args.extend(["--profile", args.profile])
        elif sub == "sync":
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Sync my_mods into active load order profile?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            target_args.append("--sync")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "clean":
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Clean invalid mods from load order profile?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            target_args.append("--clean")
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub in ("enable", "activate"):
            target_args.extend(["--enable", args.mod])
            if getattr(args, "order", None) is not None:
                target_args.extend(["--order", str(args.order)])
            if not getattr(args, "with_deps", True):
                target_args.append("--no-deps")
            for td in getattr(args, "test_dep", []):
                target_args.extend(["--test-dep", td])
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "disable":
            target_args.extend(["--disable", args.mod])
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "validate":
            target_args.append("--validate")
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
        elif sub == "isolate":
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Isolate mod in load order (all other mods will be disabled)?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            target_args.extend(["--isolate", args.mod])
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

    elif cmd == "modio":
        if sub == "search":
            script_target = SCRIPTS_DIR / "modio_search.py"
            target_args.extend(["--query", args.query, "--limit", str(args.limit)])
            if getattr(args, "platform", None):
                target_args.extend(["--platform", args.platform])
            if getattr(args, "include_tracked", False):
                target_args.append("--include-tracked")
        elif sub == "sync":
            script_target = SCRIPTS_DIR / "modio_sync.py"
            if getattr(args, "prune", False) and not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Prune unsubscribed mods from library and disk?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE

            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
            if getattr(args, "prune", False):
                target_args.append("--prune")
            if getattr(args, "limit", None) is not None:
                target_args.extend(["--limit", str(args.limit)])
            if getattr(args, "filter", None):
                target_args.extend(["--filter", args.filter])
            if getattr(args, "skip_updates", False):
                target_args.append("--skip-updates")
            if getattr(args, "token", None):
                target_args.extend(["--token", args.token])
        elif sub == "extract":
            script_target = SCRIPTS_DIR / "modio_extract.py"
            if getattr(args, "query", None):
                target_args.extend(["--query", args.query])
            if getattr(args, "pak", None):
                target_args.extend(["--pak", args.pak])
            if getattr(args, "output_dir", None):
                target_args.extend(["--output-dir", args.output_dir])
            if getattr(args, "write_spec", False):
                target_args.append("--write-spec")
            if getattr(args, "update_library", False):
                target_args.append("--update-library")
        elif sub == "update":
            script_target = SCRIPTS_DIR / "modio_update.py"
            if getattr(args, "query", None):
                target_args.extend(["--query", args.query])
            if getattr(args, "all", False):
                target_args.append("--all")
            if getattr(args, "check_only", False):
                target_args.append("--check-only")
            if getattr(args, "force", False):
                target_args.append("--force")
            if getattr(args, "list_tracked", False):
                target_args.append("--list-tracked")
        elif sub in ("update-metadata", "update_metadata"):
            script_target = SCRIPTS_DIR / "modio_update_metadata.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "tags", None):
                target_args.extend(["--tags", ",".join(args.tags) if isinstance(args.tags, list) else args.tags])
            if getattr(args, "confirm", False):
                target_args.append("--confirm")
        elif sub in ("create-collection", "create_collection"):
            script_target = SCRIPTS_DIR / "modio_create_collection.py"
            if getattr(args, "library", None):
                target_args.extend(["--library", args.library])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "purge":
            script_target = SCRIPTS_DIR / "purge_library.py"
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Purge all cataloged mods from mods/ and reset mods/library.md?",
                        non_interactive_yes=getattr(args, "yes", False) or getattr(args, "force", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y, --yes, or -f when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
            if getattr(args, "force", False):
                target_args.append("--force")
            if getattr(args, "mods_dir", None):
                target_args.extend(["--mods-dir", args.mods_dir])
            if getattr(args, "library_path", None):
                target_args.extend(["--library-path", args.library_path])
        elif sub in ("update-catalog", "update_catalog"):
            script_target = SCRIPTS_DIR / "update_library_catalog.py"
            if getattr(args, "write", False):
                target_args.append("--write")
            if getattr(args, "check", False):
                target_args.append("--check")
            if getattr(args, "stdout", False):
                target_args.append("--stdout")

    elif cmd == "scaffold":
        if sub == "stat":
            script_target = SCRIPTS_DIR / "scaffold_stat_entry.py"
            target_args.extend(["--mod", args.mod, "--type", args.type, "--name", args.name])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "using", None):
                target_args.extend(["--using", args.using])
            if getattr(args, "props", None):
                target_args.extend(["--props", ",".join(args.props) if isinstance(args.props, list) else args.props])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "progression":
            script_target = SCRIPTS_DIR / "scaffold_progression_node.py"
            target_args.extend(["--mod", args.mod, "--class", args.class_name, "--level", str(args.level)])
            if getattr(args, "subclass", None):
                target_args.extend(["--subclass", args.subclass])
            if getattr(args, "table_uuid", None):
                target_args.extend(["--table-uuid", args.table_uuid])
            if getattr(args, "passives", None):
                target_args.extend(["--passives", ",".join(args.passives) if isinstance(args.passives, list) else args.passives])
            if getattr(args, "boosts", None):
                target_args.extend(["--boosts", ",".join(args.boosts) if isinstance(args.boosts, list) else args.boosts])
            if getattr(args, "spells", None):
                target_args.extend(["--spells", ",".join(args.spells) if isinstance(args.spells, list) else args.spells])
            if getattr(args, "spell_count", None) is not None:
                target_args.extend(["--spell-count", str(args.spell_count)])
            if getattr(args, "feat", False):
                target_args.append("--feat")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub in ("root-template", "root_template"):
            script_target = SCRIPTS_DIR / "scaffold_root_template.py"
            target_args.extend(["--mod", args.mod, "--item", args.item])
            if getattr(args, "visual_preset", None):
                target_args.extend(["--visual-preset", args.visual_preset])
            if getattr(args, "parent_template", None):
                target_args.extend(["--parent-template", args.parent_template])
            if getattr(args, "display_handle", None):
                target_args.extend(["--display-handle", args.display_handle])
            if getattr(args, "description_handle", None):
                target_args.extend(["--description-handle", args.description_handle])
            if getattr(args, "icon", None):
                target_args.extend(["--icon", args.icon])
            if getattr(args, "no_link_stat", False):
                target_args.append("--no-link-stat")
            if getattr(args, "list_presets", False):
                target_args.append("--list-presets")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub in ("icon-uvs", "icon_uvs"):
            script_target = SCRIPTS_DIR / "scaffold_icon_uvs.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "icon_names", None):
                target_args.extend(["--icon-names", ",".join(args.icon_names) if isinstance(args.icon_names, list) else args.icon_names])
            if getattr(args, "icons_dir", None):
                target_args.extend(["--icons-dir", args.icons_dir])
            if getattr(args, "atlas_name", None):
                target_args.extend(["--atlas-name", args.atlas_name])
            if getattr(args, "atlas_uuid", None):
                target_args.extend(["--atlas-uuid", args.atlas_uuid])
            if getattr(args, "icon_size", None) is not None:
                target_args.extend(["--icon-size", str(args.icon_size)])
            if getattr(args, "atlas_size", None) is not None:
                target_args.extend(["--atlas-size", str(args.atlas_size)])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

    elif cmd == "query":
        script_target = SCRIPTS_DIR / "query_mod_database.py"
        if getattr(args, "search", None):
            target_args.extend(["--search", args.search])
        if getattr(args, "slot", None):
            target_args.extend(["--slot", args.slot])
        if getattr(args, "boost", None):
            target_args.extend(["--boost", args.boost])
        if getattr(args, "passive", None):
            target_args.extend(["--passive", args.passive])
        if getattr(args, "rarity", None):
            target_args.extend(["--rarity", args.rarity])
        if getattr(args, "mod", None):
            target_args.extend(["--mod", args.mod])
        if getattr(args, "limit", None) is not None:
            target_args.extend(["--limit", str(args.limit)])
        if getattr(args, "compact", False):
            target_args.append("--compact")
        if getattr(args, "reindex", False):
            target_args.append("--reindex")

    elif cmd in ("build", "sim"):
        script_target = SCRIPTS_DIR / "simulate_build_synergy.py"
        if getattr(args, "classes", None):
            target_args.extend(["--classes", args.classes])
        if getattr(args, "stats", None):
            target_args.extend(["--stats", args.stats])
        if getattr(args, "gear", None):
            target_args.extend(["--gear", ",".join(args.gear) if isinstance(args.gear, list) else args.gear])
        if getattr(args, "dpr_sequence", None):
            target_args.extend(["--dpr-sequence", args.dpr_sequence])
        if getattr(args, "target_ac", None) is not None:
            target_args.extend(["--target-ac", str(args.target_ac)])

    elif cmd == "tools":
        script_target = SCRIPTS_DIR / "tools.py"
        if sub == "list":
            target_args.append("--list")
            if getattr(args, "category", None):
                target_args.extend(["--category", args.category])
            if getattr(args, "categories", False):
                target_args.append("--categories")
            if getattr(args, "full", False):
                target_args.append("--full")
        elif sub == "search":
            target_args.extend(["--search", args.query])
        elif sub == "info":
            target_args.extend(["--info", args.tool_name])
        elif sub == "verify":
            target_args.append("--verify")
            if getattr(args, "audit_skills", False):
                target_args.append("--audit-skills")

    elif cmd == "env":
        if sub == "paths":
            from scripts.lib.env_paths import (
                get_xdg_cache_home,
                get_xdg_config_home,
                get_xdg_data_home,
                get_xdg_state_home,
            )
            cfg = get_xdg_config_home()
            cache = get_xdg_cache_home()
            data = get_xdg_data_home()
            state = get_xdg_state_home()
            paths_data = {
                "XDG_CONFIG_HOME": {"path": str(cfg), "exists": cfg.exists()},
                "XDG_CACHE_HOME": {"path": str(cache), "exists": cache.exists()},
                "XDG_DATA_HOME": {"path": str(data), "exists": data.exists()},
                "XDG_STATE_HOME": {"path": str(state), "exists": state.exists()},
            }
            if args.json:
                print(json.dumps(paths_data, indent=2))
            else:
                color = emitter.color
                print(f"\n{color.bold('=== XDG Base Directory Paths ===')}")
                for var, info in paths_data.items():
                    status = color.green("[exists]") if info["exists"] else color.yellow("[not created]")
                    print(f"{color.bold(f'{var:17}')}: {info['path']} {status}")
                print("")
            return ExitCode.OK

        script_target = SCRIPTS_DIR / "setup_environment.py"
        if sub == "check":
            target_args.append("--check")
        elif sub == "setup":
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

    if not script_target or not script_target.is_file():
        emitter.error(
            message=f"Handler script not found for command '{cmd} {sub}'.",
            code="COMMAND_NOT_FOUND",
            exit_code=ExitCode.UNAVAILABLE,
            exit_process=False,
        )
        return ExitCode.UNAVAILABLE

    # Propagate global --config flag if specified
    if getattr(args, "config", None):
        target_args.extend(["--config", str(args.config)])

    # Propagate global --json flag if requested
    if args.json:
        target_args.append("--json")

    cmd_line = [sys.executable, str(script_target)] + target_args
    emitter.log(f"Executing: {' '.join(cmd_line)}", level="INFO")

    proc = subprocess.run(cmd_line)
    return proc.returncode


def main() -> None:
    """CLI execution entrypoint."""
    if "--no-color" in sys.argv:
        os.environ["NO_COLOR"] = "1"

    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(ExitCode.USAGE)

    args = parser.parse_args()

    color = ConsoleColor(stream=sys.stderr, force_color=False)
    emitter = OutputEmitter(json_mode=args.json, color=color)

    try:
        ret = dispatch_command(args, emitter)
        sys.exit(ret)
    except KeyboardInterrupt:
        emitter.error(
            message="Operation aborted by user.",
            code="SIGINT",
            exit_code=130,
            exit_process=True,
        )
    except Exception as exc:
        emitter.error(
            message=f"Unhandled internal error: {exc}",
            code="INTERNAL_ERROR",
            exit_code=ExitCode.GENERAL,
            exit_process=True,
        )


if __name__ == "__main__":
    main()
