#!/usr/bin/env python3
"""manage_saves.py
----------------
Baldur's Gate 3 savegame discovery, audit, backup, and cleanup management tool.

Features:
- Discovers BG3 .lsv save files across Linux Proton, WSL, Windows, and macOS paths.
- Lists saves with timestamps, sizes, and optional metadata inspection.
- Safely archives/backups save games to timestamped ZIP packages.
- Prunes stale save games with configurable retention rules (--keep, --days, --save, --all).
- Protects the latest save game by default unless explicitly overridden (--force-all / --no-keep-latest).
- Supports directory-based save packages (removes parent folder + thumbnail WebP without leaving orphans).
- Supports --dry-run / -n for zero-risk previewing of deletions and reclaimed space.
- Supports --json output with structured envelope formatting.
- Strict confirmation guard: prompts in interactive TTYs; requires --yes / -y non-interactively.
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bg3_core.cli_common import (
    ConsoleColor,
    ExitCode,
    NonInteractiveConfirmationError,
    confirm_action,
    format_json_response,
)
from bg3_core.env_paths import get_xdg_data_home
from bg3_core.save_inspector import (
    extract_save_metadata,
    find_save_file,
    get_save_search_paths,
    prune_missing_mods_from_save,
)


def discover_save_games(search_dirs: Optional[Sequence[Path]] = None) -> List[Dict[str, Any]]:
    """Discover all .lsv save games across specified or standard BG3 directories.

    Returns a list of dict records sorted descending by modification time (newest first).
    """
    targets: List[Path] = []
    if search_dirs:
        targets.extend(search_dirs)
    else:
        targets.extend(get_save_search_paths())

    seen_files = set()
    records: List[Dict[str, Any]] = []

    for base_dir in targets:
        if not base_dir.is_dir():
            continue

        for lsv_file in base_dir.rglob("*.lsv"):
            real_path = lsv_file.resolve()
            if real_path in seen_files:
                continue
            seen_files.add(real_path)

            try:
                st = real_path.stat()
                mtime = st.st_mtime
                lsv_size = st.st_size
            except OSError:
                continue

            save_name = real_path.stem
            parent = real_path.parent

            # BG3 save directories usually match the save name:
            # e.g., Savegames/Story/<SaveName>/<SaveName>.lsv + <SaveName>.WebP
            is_dir_package = parent.name == save_name and parent.parent.name.lower() in ("story", "savegames")

            associated_files: List[Path] = [real_path]
            total_size = lsv_size

            if is_dir_package:
                package_dir = parent
                try:
                    for sibling in parent.iterdir():
                        if sibling != real_path and sibling.is_file():
                            associated_files.append(sibling.resolve())
                            total_size += sibling.stat().st_size
                except OSError:
                    pass
            else:
                package_dir = None
                # Check for sibling thumbnail with same stem
                for ext in (".webp", ".WebP", ".png"):
                    thumb = parent / f"{save_name}{ext}"
                    if thumb.is_file():
                        associated_files.append(thumb.resolve())
                        try:
                            total_size += thumb.stat().st_size
                        except OSError:
                            pass

            records.append({
                "name": save_name,
                "lsv_path": str(real_path),
                "package_dir": str(package_dir) if package_dir else None,
                "is_dir_package": is_dir_package,
                "associated_files": [str(p) for p in associated_files],
                "size_bytes": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2),
                "mtime": mtime,
                "modified": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })

    records.sort(key=lambda r: r["mtime"], reverse=True)
    for idx, r in enumerate(records):
        r["is_latest"] = (idx == 0)

    return records


def filter_saves_for_purge(
    all_saves: List[Dict[str, Any]],
    keep: int = 5,
    older_than_days: Optional[float] = None,
    target_save: Optional[str] = None,
    purge_all: bool = False,
    keep_latest: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Partition discovered saves into (to_purge, to_preserve) based on criteria.

    Args:
        all_saves: List of save dicts sorted newest-first.
        keep: Number of newest saves to preserve.
        older_than_days: Only purge saves older than N days.
        target_save: Exact name or filename of a single target save.
        purge_all: If True, candidate all saves for purge.
        keep_latest: If True, guarantees the newest save is never purged.
    """
    now = time.time()
    to_purge: List[Dict[str, Any]] = []
    to_preserve: List[Dict[str, Any]] = []

    for idx, save in enumerate(all_saves):
        # 1. Target specific save name
        if target_save:
            stem = Path(target_save).stem.lower()
            if save["name"].lower() == stem or Path(save["lsv_path"]).name.lower() == target_save.lower():
                if idx == 0 and keep_latest:
                    to_preserve.append(save)
                else:
                    to_purge.append(save)
            else:
                to_preserve.append(save)
            continue

        # 2. Latest save protection
        if idx == 0 and keep_latest:
            to_preserve.append(save)
            continue

        # 3. Purge all mode
        if purge_all:
            to_purge.append(save)
            continue

        # 4. Retention count threshold
        if idx < keep:
            to_preserve.append(save)
            continue

        # 5. Age threshold
        if older_than_days is not None:
            age_days = (now - save["mtime"]) / (24 * 3600)
            if age_days < older_than_days:
                to_preserve.append(save)
                continue

        to_purge.append(save)

    return to_purge, to_preserve


def backup_save_games(
    saves: List[Dict[str, Any]],
    dest_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Archive selected save games into a timestamped ZIP archive."""
    if not saves:
        return {
            "backup_path": None,
            "archived_count": 0,
            "total_bytes": 0,
            "status": "empty",
        }

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if dest_path is None:
        backup_dir = get_xdg_data_home() / "backups" / "saves"
        backup_dir.mkdir(parents=True, exist_ok=True)
        zip_file = backup_dir / f"bg3_saves_backup_{timestamp}.zip"
    else:
        if dest_path.is_dir() or not dest_path.suffix:
            dest_path.mkdir(parents=True, exist_ok=True)
            zip_file = dest_path / f"bg3_saves_backup_{timestamp}.zip"
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            zip_file = dest_path

    total_bytes = 0
    with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for save in saves:
            if save.get("is_dir_package") and save.get("package_dir"):
                p_dir = Path(save["package_dir"])
                if p_dir.is_dir():
                    for f in p_dir.iterdir():
                        if f.is_file():
                            arcname = f"{p_dir.name}/{f.name}"
                            zf.write(f, arcname=arcname)
                            total_bytes += f.stat().st_size
                    continue

            for f_str in save.get("associated_files", [save["lsv_path"]]):
                p = Path(f_str)
                if p.is_file():
                    zf.write(p, arcname=p.name)
                    total_bytes += p.stat().st_size

    return {
        "backup_path": str(zip_file),
        "archived_count": len(saves),
        "total_bytes": total_bytes,
        "size_mb": round(total_bytes / (1024 * 1024), 2),
        "status": "success",
    }


def purge_save_games(
    saves_to_purge: List[Dict[str, Any]],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Safely delete target save files or folders."""
    deleted_records: List[Dict[str, Any]] = []
    failed_records: List[Dict[str, Any]] = []
    reclaimed_bytes = 0

    for save in saves_to_purge:
        rec = {
            "name": save["name"],
            "lsv_path": save["lsv_path"],
            "size_bytes": save["size_bytes"],
        }

        if dry_run:
            rec["status"] = "preview_deleted"
            deleted_records.append(rec)
            reclaimed_bytes += save["size_bytes"]
            continue

        try:
            # If package dir exists and matches save name, delete the entire folder
            if save.get("is_dir_package") and save.get("package_dir"):
                p_dir = Path(save["package_dir"])
                if p_dir.is_dir():
                    shutil.rmtree(p_dir)
                    rec["status"] = "deleted"
                    deleted_records.append(rec)
                    reclaimed_bytes += save["size_bytes"]
                    continue

            # Fallback: remove associated files
            for f_str in save.get("associated_files", [save["lsv_path"]]):
                p = Path(f_str)
                if p.is_file():
                    p.unlink()

            rec["status"] = "deleted"
            deleted_records.append(rec)
            reclaimed_bytes += save["size_bytes"]

        except Exception as err:
            rec["status"] = "failed"
            rec["error"] = str(err)
            failed_records.append(rec)

    return {
        "purged_count": len(deleted_records),
        "failed_count": len(failed_records),
        "reclaimed_bytes": reclaimed_bytes,
        "reclaimed_mb": round(reclaimed_bytes / (1024 * 1024), 2),
        "dry_run": dry_run,
        "deleted_saves": deleted_records,
        "failed_saves": failed_records,
    }


def handle_list(args: argparse.Namespace) -> int:
    search_dirs = [Path(args.save_dir)] if getattr(args, "save_dir", None) else None
    saves = discover_save_games(search_dirs)

    if args.json:
        print(json.dumps(format_json_response(data={"saves": saves, "total_count": len(saves)}), indent=2))
        return ExitCode.OK

    color = ConsoleColor(stream=sys.stdout)
    print(f"\n{color.bold('Discovered BG3 Save Games:')} ({len(saves)} found)")
    print("=" * 80)
    if not saves:
        print("  No save games found in default or configured search paths.")
        print("")
        return ExitCode.OK

    print(f"  {'Save Name':<35} {'Size (MB)':<12} {'Modified':<20} {'Status'}")
    print("  " + "-" * 76)
    for s in saves:
        tag = f"{color.green('[LATEST]')}" if s.get("is_latest") else ""
        print(f"  {s['name']:<35} {s['size_mb']:<12} {s['modified']:<20} {tag}")
    print("")
    return ExitCode.OK


def handle_inspect(args: argparse.Namespace) -> int:
    save_arg = getattr(args, "save", None) or "latest"
    save_dir = getattr(args, "save_dir", None)
    color = ConsoleColor(stream=sys.stdout)
    err_color = ConsoleColor(stream=sys.stderr)

    try:
        save_file = find_save_file(save_arg, save_dir)
        meta = extract_save_metadata(save_file)

        if getattr(args, "audit", False):
            from bg3_authoring.diagnostics.inspect_save_game import audit_against_modsettings
            audit_result = audit_against_modsettings(meta["mods"], _REPO_ROOT)
            meta["audit"] = audit_result

        if args.json:
            print(json.dumps(format_json_response(data=meta), indent=2))
        else:
            print(f"\n{color.bold('BG3 Save Game Inspection:')} {save_file.name}")
            print("=" * 70)
            print(f"  Path:        {save_file}")
            print(f"  Size:        {meta['size_bytes'] / (1024*1024):.2f} MB")
            if meta.get("level_name"):
                print(f"  Level/Act:   {meta['level_name']}")
            print(f"  Active Mods: {len(meta.get('mods', []))}")
            if meta.get("mods"):
                print("\n  Recorded Mods:")
                for m in meta["mods"]:
                    print(f"    • {m.get('name', 'Unknown'):<30} (UUID: {m.get('uuid')})")
            print("")
        return ExitCode.OK

    except Exception as e:
        if args.json:
            print(json.dumps(format_json_response(status="error", error={"code": "INSPECT_ERROR", "message": str(e)}), indent=2))
        else:
            print(f"{err_color.red('[ERROR]')} {e}", file=sys.stderr)
        return ExitCode.GENERAL


def handle_backup(args: argparse.Namespace) -> int:
    search_dirs = [Path(args.save_dir)] if getattr(args, "save_dir", None) else None
    all_saves = discover_save_games(search_dirs)

    if getattr(args, "save", None):
        target = args.save.lower()
        saves_to_backup = [s for s in all_saves if s["name"].lower() == target or Path(s["lsv_path"]).name.lower() == target]
    else:
        saves_to_backup = all_saves

    if not saves_to_backup:
        err_msg = "No matching save games found to back up."
        if args.json:
            print(json.dumps(format_json_response(status="error", error={"code": "NO_SAVES_FOUND", "message": err_msg}), indent=2))
        else:
            print(f"Error: {err_msg}", file=sys.stderr)
        return ExitCode.NOINPUT

    dest = Path(args.dest) if getattr(args, "dest", None) else None
    result = backup_save_games(saves_to_backup, dest)

    if args.json:
        print(json.dumps(format_json_response(data=result), indent=2))
        return ExitCode.OK

    color = ConsoleColor(stream=sys.stdout)
    print(f"\n{color.green('✓')} {color.bold('Save Games Backup Complete:')}")
    print(f"  Archive:        {result['backup_path']}")
    print(f"  Archived Saves: {result['archived_count']}")
    print(f"  Total Size:     {result['size_mb']} MB\n")
    return ExitCode.OK


def handle_purge(args: argparse.Namespace) -> int:
    search_dirs = [Path(args.save_dir)] if getattr(args, "save_dir", None) else None
    all_saves = discover_save_games(search_dirs)

    if not all_saves:
        msg = "No save games found to purge."
        if args.json:
            print(json.dumps(format_json_response(data={"purged_count": 0, "message": msg}), indent=2))
        else:
            print(msg)
        return ExitCode.OK

    # Determine keep_latest
    # If --force-all or --no-keep-latest is set, disable keep_latest protection
    keep_latest = not (getattr(args, "force_all", False) or getattr(args, "no_keep_latest", False))
    purge_all = getattr(args, "all", False) or getattr(args, "force_all", False)

    to_purge, to_preserve = filter_saves_for_purge(
        all_saves=all_saves,
        keep=0 if purge_all else args.keep,
        older_than_days=getattr(args, "days", None),
        target_save=getattr(args, "save", None),
        purge_all=purge_all,
        keep_latest=keep_latest,
    )

    if not to_purge:
        msg = "No save games matched the purge criteria."
        if args.json:
            print(json.dumps(format_json_response(data={
                "purged_count": 0,
                "preserved_count": len(to_preserve),
                "reclaimed_bytes": 0,
                "message": msg,
            }), indent=2))
        else:
            print(f"[INFO] {msg} (Preserved: {len(to_preserve)})")
        return ExitCode.OK

    # Confirmation Gate
    if not args.dry_run:
        total_mb = round(sum(s["size_bytes"] for s in to_purge) / (1024 * 1024), 2)
        target_summary = f"{len(to_purge)} save game(s) ({total_mb} MB)"
        try:
            confirm_action(
                f"Permanently delete {target_summary}?",
                default=False,
                non_interactive_yes=args.yes,
                force_non_interactive=args.json,
            )
        except NonInteractiveConfirmationError as exc:
            if args.json:
                print(json.dumps(format_json_response(status="error", error={"code": "CONFIRMATION_REQUIRED", "message": str(exc)}), indent=2))
            else:
                err_color = ConsoleColor(stream=sys.stderr)
                print(f"{err_color.red('[ERROR]')} {exc}", file=sys.stderr)
                print("Pass -y or --yes when running non-interactively.", file=sys.stderr)
            return ExitCode.USAGE

    # Backup if requested
    backup_result = None
    if getattr(args, "backup", False) and not args.dry_run:
        backup_dir = Path(args.backup_dir) if getattr(args, "backup_dir", None) else None
        backup_result = backup_save_games(to_purge, backup_dir)

    purge_result = purge_save_games(to_purge, dry_run=args.dry_run)
    purge_result["preserved_count"] = len(to_preserve)
    purge_result["preserved_saves"] = [{"name": s["name"], "size_mb": s["size_mb"], "modified": s["modified"]} for s in to_preserve]
    if backup_result:
        purge_result["backup"] = backup_result

    if args.json:
        print(json.dumps(format_json_response(data=purge_result), indent=2))
        return ExitCode.OK if purge_result["failed_count"] == 0 else ExitCode.GENERAL

    color = ConsoleColor(stream=sys.stdout)
    mode_prefix = f"{color.cyan('[DRY-RUN] ')}" if args.dry_run else ""
    print(f"\n{mode_prefix}{color.bold('Save Games Purge Summary:')}")
    print(f"  Purged Saves:    {purge_result['purged_count']}")
    print(f"  Preserved Saves: {purge_result['preserved_count']}")
    print(f"  Reclaimed Space: {purge_result['reclaimed_mb']} MB")
    if backup_result:
        print(f"  Pre-Purge Backup: {backup_result['backup_path']}")

    if purge_result["deleted_saves"]:
        print(f"\n{color.bold('Affected Saves:')}")
        for s in purge_result["deleted_saves"]:
            st = s["status"]
            mb = round(s["size_bytes"] / (1024 * 1024), 2)
            print(f"  {color.green('✓')} {s['name']:<35} ({mb} MB) - {st}")

    if purge_result["failed_saves"]:
        print(f"\n{color.red('Failed Deletions:')}")
        for s in purge_result["failed_saves"]:
            print(f"  {color.red('✗')} {s['name']}: {s.get('error')}")

    print("")
    return ExitCode.OK if purge_result["failed_count"] == 0 else ExitCode.GENERAL


def handle_clean_missing(args: argparse.Namespace) -> int:
    """Clean/prune missing or uninstalled mods from a save game."""
    color = ConsoleColor()
    try:
        save_file = find_save_file(args.save, args.save_dir)
    except FileNotFoundError as err:
        if args.json:
            print(json.dumps(format_json_response(status="error", error={"message": str(err)}), indent=2))
        else:
            print(f"{color.red('Error:')} {err}", file=sys.stderr)
        return ExitCode.DATAERR

    out_path = Path(args.out).resolve() if getattr(args, "out", None) else None

    # If not dry run and in-place replacement, confirm unless --yes
    if not args.dry_run and out_path is None:
        try:
            confirm_action(
                f"Prune missing mods from save '{save_file.name}'? (A .bak backup will be preserved)",
                default=False,
                non_interactive_yes=getattr(args, "yes", False),
                force_non_interactive=args.json,
            )
        except NonInteractiveConfirmationError as err:
            if args.json:
                print(json.dumps(format_json_response(status="error", error={"message": str(err)}), indent=2))
            else:
                print(f"{color.red('Confirmation required:')} {err}", file=sys.stderr)
            return ExitCode.DATAERR

    try:
        ok, pruned = prune_missing_mods_from_save(
            save_path=save_file,
            output_path=out_path,
            dry_run=args.dry_run,
        )
    except Exception as err:
        if args.json:
            print(json.dumps(format_json_response(status="error", error={"message": str(err)}), indent=2))
        else:
            print(f"{color.red('Error pruning save:')} {err}", file=sys.stderr)
        return ExitCode.GENERAL

    target_destination = str(out_path if out_path else save_file)
    data = {
        "save_file": str(save_file),
        "target_output": target_destination,
        "dry_run": args.dry_run,
        "pruned_mods": pruned,
        "pruned_count": len(pruned),
    }

    if args.json:
        print(json.dumps(format_json_response(status="success" if ok else "error", data=data), indent=2))
    else:
        status_label = "[DRY-RUN] Would prune" if args.dry_run else "Successfully pruned"
        print(f"\n{color.bold('BG3 Save Game Rescue / Mod Pruning:')} ({status_label})")
        print(f"  Source Save:     {save_file}")
        print(f"  Output Save:     {target_destination}")
        print(f"  Pruned Mods:     {len(pruned)}")
        if pruned:
            print(f"\n{color.bold('Pruned Entries:')}")
            for m in pruned:
                print(f"  {color.green('✓')} {m}")
        else:
            print(f"  {color.cyan('ℹ')} No missing mods were detected in this save file.")
        print("")

    return ExitCode.OK


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="manage_saves.py",
        description="Baldur's Gate 3 savegame discovery, audit, backup, and cleanup management tool.",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured output in JSON format")

    subparsers = parser.add_subparsers(dest="command", help="Save management commands")

    # list
    p_list = subparsers.add_parser("list", help="List discovered BG3 save games")
    p_list.add_argument("--save-dir", help="Custom directory containing .lsv save files")
    p_list.add_argument("--json", action="store_true", help="Emit JSON output")

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect and audit a specific or latest save game")
    p_inspect.add_argument("save", nargs="?", help="Path or name of .lsv save file, or 'latest'")
    p_inspect.add_argument("--save-dir", help="Custom directory containing .lsv save files")
    p_inspect.add_argument("--audit", action="store_true", help="Audit save mods against active modsettings.lsx")
    p_inspect.add_argument("--json", action="store_true", help="Emit JSON output")

    # backup
    p_backup = subparsers.add_parser("backup", help="Archive save games into a ZIP backup")
    p_backup.add_argument("--save", help="Specific save game name to back up")
    p_backup.add_argument("--dest", help="Destination directory or ZIP archive path")
    p_backup.add_argument("--save-dir", help="Custom directory containing .lsv save files")
    p_backup.add_argument("--json", action="store_true", help="Emit JSON output")

    # purge
    p_purge = subparsers.add_parser("purge", help="Prune old or unneeded save games")
    p_purge.add_argument("--keep", type=int, default=5, help="Number of newest saves to preserve (default: 5)")
    p_purge.add_argument("--days", type=float, help="Purge saves older than specified days")
    p_purge.add_argument("--save", help="Specific save name to purge")
    p_purge.add_argument("--all", action="store_true", help="Purge all matching saves (preserves latest unless --force-all)")
    p_purge.add_argument("--force-all", action="store_true", help="Purge ALL saves including the latest save")
    p_purge.add_argument("--no-keep-latest", action="store_true", help="Disable latest save protection")
    p_purge.add_argument("--backup", action="store_true", help="Create a ZIP backup before purging")
    p_purge.add_argument("--backup-dir", help="Custom directory for pre-purge backup")
    p_purge.add_argument("--save-dir", help="Custom directory containing .lsv save files")
    p_purge.add_argument("--dry-run", "-n", action="store_true", help="Simulate purge without modifying files")
    p_purge.add_argument("--yes", "-y", action="store_true", help="Confirm deletion non-interactively")
    p_purge.add_argument("--json", action="store_true", help="Emit JSON output")

    # clean-missing
    p_clean = subparsers.add_parser("clean-missing", aliases=["clean_missing", "rescue"], help="Prune missing mods from a save game")
    p_clean.add_argument("save", nargs="?", help="Path or name of .lsv save file, or 'latest'")
    p_clean.add_argument("--save-dir", help="Custom directory containing .lsv save files")
    p_clean.add_argument("--out", help="Output path for cleaned .lsv file")
    p_clean.add_argument("--dry-run", "-n", action="store_true", help="Simulate pruning without modifying files")
    p_clean.add_argument("--yes", "-y", action="store_true", help="Confirm modification non-interactively")
    p_clean.add_argument("--json", action="store_true", help="Emit JSON output")

    args = parser.parse_args()

    if not args.command:
        parser.print_help(sys.stderr)
        return ExitCode.USAGE

    if args.command == "list":
        return handle_list(args)
    elif args.command == "inspect":
        return handle_inspect(args)
    elif args.command == "backup":
        return handle_backup(args)
    elif args.command == "purge":
        return handle_purge(args)
    elif args.command in ("clean-missing", "clean_missing", "rescue"):
        return handle_clean_missing(args)

    return ExitCode.USAGE


if __name__ == "__main__":
    sys.exit(main())
