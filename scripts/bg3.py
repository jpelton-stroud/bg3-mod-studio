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

    return parser


def dispatch_command(args: argparse.Namespace, emitter: OutputEmitter) -> int:
    """Route parsed CLI arguments to the target implementation script."""
    cmd = args.command
    sub = args.subcommand

    if not cmd or not sub:
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

    if cmd == "mod":
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
