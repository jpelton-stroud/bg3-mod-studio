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

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.env_paths import MODS_DIR, REPO_ROOT
from scripts.lib.library_catalog import purge_library_mods

GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def main():
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

    mods_dir = args.mods_dir.resolve() if args.mods_dir else Path(MODS_DIR).resolve()
    lib_path = (
        args.library_path.resolve()
        if args.library_path
        else (mods_dir / "library.md").resolve()
    )

    if not args.force and not args.dry_run and sys.stdin.isatty():
        print(f"{YELLOW}{BOLD}Warning:{RESET} This will delete all mod folders in '{mods_dir}' and reset '{lib_path}'.")
        confirm = input("Are you sure you want to proceed? (y/N): ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Purge operation aborted.")
            sys.exit(0)

    result = purge_library_mods(
        mods_dir=mods_dir,
        library_path=lib_path,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    mode_prefix = f"{CYAN}[DRY-RUN] {RESET}" if args.dry_run else ""
    print(f"\n{mode_prefix}{BOLD}Library Purge Summary{RESET}")
    print(f"Target Directory: {result['mods_dir']}")
    print(f"Purged Mod Folders: {result['purged_count']}")
    if result["library_reset"]:
        print(f"Catalog Reset: {GREEN}✓{RESET} {result['library_path']}")

    for del_item in result.get("deleted_folders", []):
        status_label = del_item.get("status")
        msg = del_item.get("message", "")
        if status_label in ("deleted", "dry_run_deleted"):
            print(f"  {GREEN}✓{RESET} {msg}")
        else:
            print(f"  {YELLOW}!{RESET} {msg}")

    print("")


if __name__ == "__main__":
    main()
