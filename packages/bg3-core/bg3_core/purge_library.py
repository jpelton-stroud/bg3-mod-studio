#!/usr/bin/env python3
"""
purge_library.py
----------------
Safely purges all mod specifications and data directories under `mods/`
and resets `mods/library.md` to the canonical empty catalog template.

Features:
- Deletes only direct child directories of `mods/` (skipping dotfiles and files).
- Resets `mods/library.md` to clean baseline header.
- Supports --dry-run (preview changes without deleting or rewriting).
- Supports --json (emit structured outcome).
- Supports --force (skip confirmation prompt when run interactively).
"""

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bg3_core.cli_common import (
    ConsoleColor,
    ExitCode,
    NonInteractiveConfirmationError,
    confirm_action,
)
from bg3_core.env_paths import get_subscribed_mods_dir
from bg3_core.library_catalog import purge_library_mods


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Purge all cataloged mods from mods/ and reset mods/library.md."
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Simulate deletion and show affected directories without modifying files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured results as JSON",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Execute purge without interactive confirmation",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Confirm deletion non-interactively in automated pipelines",
    )
    parser.add_argument(
        "--mods-dir",
        type=Path,
        default=None,
        help="Override path to mods directory (defaults to workspace mods/)",
    )
    parser.add_argument(
        "--library-path",
        type=Path,
        default=None,
        help="Override path to library.md (defaults to workspace mods/library.md)",
    )

    args = parser.parse_args()

    mods_dir = args.mods_dir.resolve() if args.mods_dir else get_subscribed_mods_dir().resolve()
    lib_path = (
        args.library_path.resolve()
        if args.library_path
        else (mods_dir / "library.md").resolve()
    )

    if not args.force and not args.dry_run:
        try:
            confirm_action(
                f"Delete all mod folders in '{mods_dir}' and reset '{lib_path}'?",
                default=False,
                non_interactive_yes=args.yes,
                force_non_interactive=args.json,
            )
        except NonInteractiveConfirmationError as exc:
            if args.json:
                print(json.dumps({"error": str(exc), "code": "CONFIRMATION_REQUIRED", "success": False}, indent=2))
            else:
                err_color = ConsoleColor(stream=sys.stderr)
                print(f"{err_color.red('[ERROR]')} {exc}", file=sys.stderr)
                print("Pass -y or --yes when running non-interactively.", file=sys.stderr)
            sys.exit(ExitCode.USAGE)

    result = purge_library_mods(
        mods_dir=mods_dir,
        library_path=lib_path,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return ExitCode.OK

    color = ConsoleColor(stream=sys.stdout)
    mode_prefix = f"{color.cyan('[DRY-RUN] ')}" if args.dry_run else ""
    print(f"\n{mode_prefix}{color.bold('Library Purge Summary')}")
    print(f"Target Directory: {result['mods_dir']}")
    print(f"Purged Mod Folders: {result['purged_count']}")
    if result["library_reset"]:
        print(f"Catalog Reset: {color.green('✓')} {result['library_path']}")

    for del_item in result.get("deleted_folders", []):
        status_label = del_item.get("status")
        msg = del_item.get("message", "")
        if status_label in ("deleted", "dry_run_deleted"):
            print(f"  {color.green('✓')} {msg}")
        else:
            print(f"  {color.yellow('!')} {msg}")

    print("")
    return ExitCode.OK


if __name__ == "__main__":
    sys.exit(main())
