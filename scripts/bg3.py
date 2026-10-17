#!/usr/bin/env python3
"""Baldur's Gate 3 Mod Studio — Unified 2026 CLI Suite.

Unified entrypoint providing structured noun-verb command execution, stream
discipline, and standard exit codes across the entire automation toolchain.

Usage:
    python3 scripts/bg3.py [--json] [--no-color] [--verbose] <command> <subcommand> [options...]
"""

from __future__ import annotations

import argparse
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
        "--author",
        help="Author name (defaults to configured environment author).",
    )
    scaffold_parser.add_argument(
        "--type",
        default="Standard",
        choices=["Standard", "Class", "Subclass", "Item", "Spell", "Cosmetic"],
        help="Mod template archetype (default: Standard).",
    )

    # bg3 mod add-dependency
    add_dep_parser = mod_subparsers.add_parser(
        "add-dependency",
        aliases=["add_dependency"],
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
    bump_group.add_argument("--patch", action="store_true", help="Increment patch version")
    bump_group.add_argument("--minor", action="store_true", help="Increment minor version")
    bump_group.add_argument("--major", action="store_true", help="Increment major version")
    bump_group.add_argument("--build", action="store_true", help="Increment build integer")
    bump_group.add_argument("--set", help="Explicit version string (e.g. 1.2.0.0)")

    # bg3 mod pack
    pack_parser = mod_subparsers.add_parser(
        "pack",
        help="Build a game-ready LSPK .pak archive from my_mods/<slug>",
        parents=[common_parser],
    )
    pack_parser.add_argument("mod", help="Mod slug or directory")
    pack_parser.add_argument("--output", help="Custom output directory or .pak file path")

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

    # bg3 mod sync-game
    sync_game_parser = mod_subparsers.add_parser(
        "sync-game",
        aliases=["sync_game"],
        help="Synchronize unpacked mod assets and compiled .loca to BG3 Data directory",
        parents=[common_parser],
    )
    sync_game_parser.add_argument("--mods", nargs="*", help="Specific mod slugs to synchronize")
    sync_game_parser.add_argument("--clean", action="store_true", help="Clean stale assets in Data/ directory")
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
        "--dry-run",
        action="store_true",
        help="Preview cleaned load order without saving.",
    )
    lo_clean_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Bypass interactive confirmation in non-interactive sessions.",
    )

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
        help="Perform non-interactive path, tool, and .env health check",
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

    if cmd != "run" and (not cmd or not sub):
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
                    import json
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
            target_args.append(args.mod_identifier)
            if args.strict:
                target_args.append("--strict")
            if args.fix:
                target_args.append("--fix")

        elif sub == "scaffold":
            script_target = SCRIPTS_DIR / "create_mod_scaffold.py"
            target_args.append(args.name)
            if args.author:
                target_args.extend(["--author", args.author] if "--author" in sys.argv else [args.author])
            if getattr(args, "type", None):
                target_args.extend(["--type", args.type])

        elif sub in ("add-dependency", "add_dependency"):
            script_target = SCRIPTS_DIR / "add_mod_dependency.py"
            target_args.append(args.mod)
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
                target_args.append(args.mod)
            if getattr(args, "patch", False):
                target_args.append("--patch")
            elif getattr(args, "minor", False):
                target_args.append("--minor")
            elif getattr(args, "major", False):
                target_args.append("--major")
            elif getattr(args, "build", False):
                target_args.append("--build")
            elif getattr(args, "set", None):
                target_args.extend(["--set", args.set])

        elif sub == "pack":
            script_target = SCRIPTS_DIR / "pack_mod_pak.py"
            target_args.append(args.mod)
            if getattr(args, "output", None):
                target_args.extend(["--output", args.output])

        elif sub in ("sync-loca", "sync_loca"):
            script_target = SCRIPTS_DIR / "sync_localization.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "check", False):
                target_args.append("--check")
            if getattr(args, "prune", False):
                target_args.append("--prune")

        elif sub in ("sync-game", "sync_game"):
            script_target = SCRIPTS_DIR / "sync_game_data.py"
            if getattr(args, "mods", None):
                target_args.extend(["--mods"] + args.mods)
            if getattr(args, "clean", False):
                target_args.append("--clean")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub == "patch":
            script_target = SCRIPTS_DIR / "generate_compat_patch.py"
            target_args.extend(["--mod1", args.mod1, "--mod2", args.mod2])
            if getattr(args, "name", None):
                target_args.extend(["--name", args.name])
            if getattr(args, "mode", None):
                target_args.extend(["--mode", args.mode])

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
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

    elif cmd == "modio":
        if sub == "search":
            script_target = SCRIPTS_DIR / "modio_search.py"
            target_args.extend(["--search", args.query, "--limit", str(args.limit)])
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

    elif cmd == "env":
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
