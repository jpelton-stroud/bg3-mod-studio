#!/usr/bin/env python3
"""
sync_to_game_data.py
--------------------
Synchronizes custom Baldur's Gate 3 mods authored in `my_mods/` subdirectories
directly into the game's Data directory (C:\\Program Files (x86)\\Steam\\steamapps\\common\\Baldurs Gate 3\\Data)
for loading, editing, and publishing via the Baldur's Gate 3 Toolkit and mod.io.

Features:
- Idempotent and safe copy (only writes modified/new files)
- Automatically excludes development artifacts (README.md, task.md, .git, etc.)
- Mirrors localization XMLs to both Data/Localization/English and Data/Mods/<UUID>/Localization/English
- Ensures project thumbnails and publish logos are synchronized
- Supports --dry-run to preview changes
- Supports --watch for automatic live-syncing during development
"""

import argparse
import filecmp
import os
import shutil
import sys
import time
from pathlib import Path


DEFAULT_WSL_DATA_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Baldurs Gate 3/Data")
DEFAULT_WIN_DATA_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Baldurs Gate 3\Data")

EXCLUDED_FILENAMES = {
    "README.md",
    "task.md",
    ".gitignore",
    ".DS_Store",
    "Thumbs.db",
}

EXCLUDED_EXTENSIONS = {
    ".bak",
    ".tmp",
}


def load_env_defaults() -> dict:
    """Load key-value pairs from .env if present."""
    env = {}
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass
    return env


def get_default_data_dir() -> Path:
    env_vars = load_env_defaults()
    configured = os.environ.get("BG3_DATA_DIR") or env_vars.get("BG3_DATA_DIR")
    if configured:
        return Path(configured)
    if os.name == "nt":
        return DEFAULT_WIN_DATA_DIR
    return DEFAULT_WSL_DATA_DIR


def copy_file_if_different(src: Path, dst: Path, dry_run: bool = False) -> str:
    """
    Copies src to dst if dst does not exist or content differs.
    Returns: 'created', 'updated', or 'unchanged'.
    """
    if not dst.exists():
        action = "created"
    elif not filecmp.cmp(src, dst, shallow=False):
        action = "updated"
    else:
        return "unchanged"

    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return action


def sync_mod(mod_path: Path, data_dir: Path, dry_run: bool = False) -> dict:
    """
    Synchronizes a single mod folder into Data/.
    """
    stats = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    mod_name = mod_path.name
    print(f"\n📦 Processing mod: {mod_name} ({mod_path})")

    # 1. Detect subdirectories: Projects, Mods, Public, Localization
    subdirs = ["Projects", "Mods", "Public"]
    for subdir in subdirs:
        src_sub = mod_path / subdir
        if not src_sub.exists():
            continue
        dst_sub = data_dir / subdir

        for root, dirs, files in os.walk(src_sub):
            rel_root = Path(root).relative_to(src_sub)
            for file in files:
                if file in EXCLUDED_FILENAMES or any(file.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                    stats["skipped"] += 1
                    continue

                src_file = Path(root) / file
                dst_file = dst_sub / rel_root / file

                action = copy_file_if_different(src_file, dst_file, dry_run)
                if action == "created":
                    stats["created"] += 1
                    print(f"  [+] Create: {dst_file.relative_to(data_dir)}")
                elif action == "updated":
                    stats["updated"] += 1
                    print(f"  [*] Update: {dst_file.relative_to(data_dir)}")
                else:
                    stats["unchanged"] += 1

    # 2. Handle Localization:
    # Source is typically my_mods/<mod>/Localization/English/<ModName>.xml
    src_loc = mod_path / "Localization"
    if src_loc.exists():
        # Destination A: Data/Localization/...
        dst_loc_a = data_dir / "Localization"
        for root, dirs, files in os.walk(src_loc):
            rel_root = Path(root).relative_to(src_loc)
            for file in files:
                if file.endswith(".xml") or file.endswith(".loca"):
                    src_file = Path(root) / file
                    # A. Data/Localization/<rel>
                    dst_file_a = dst_loc_a / rel_root / file
                    action_a = copy_file_if_different(src_file, dst_file_a, dry_run)
                    if action_a == "created":
                        stats["created"] += 1
                        print(f"  [+] Create: {dst_file_a.relative_to(data_dir)}")
                    elif action_a == "updated":
                        stats["updated"] += 1
                        print(f"  [*] Update: {dst_file_a.relative_to(data_dir)}")
                    else:
                        stats["unchanged"] += 1

                    # B. Also replicate into Data/Mods/<ModFolder_UUID>/Localization/<rel> if Mods/<UUID> exists
                    src_mods = mod_path / "Mods"
                    if src_mods.exists():
                        for mod_uuid_dir in src_mods.iterdir():
                            if mod_uuid_dir.is_dir():
                                dst_file_b = data_dir / "Mods" / mod_uuid_dir.name / "Localization" / rel_root / file
                                action_b = copy_file_if_different(src_file, dst_file_b, dry_run)
                                if action_b == "created":
                                    stats["created"] += 1
                                    print(f"  [+] Create (mod-local): {dst_file_b.relative_to(data_dir)}")
                                elif action_b == "updated":
                                    stats["updated"] += 1
                                    print(f"  [*] Update (mod-local): {dst_file_b.relative_to(data_dir)}")
                                else:
                                    stats["unchanged"] += 1

    # 3. Handle Root Thumbnail / Publish Logo fallback if present at mod root
    root_thumb = mod_path / "thumbnail.png"
    if root_thumb.exists():
        src_projects = mod_path / "Projects"
        if src_projects.exists():
            for proj_uuid in src_projects.iterdir():
                if proj_uuid.is_dir() and not (proj_uuid / "thumbnail.png").exists():
                    dst_thumb = data_dir / "Projects" / proj_uuid.name / "thumbnail.png"
                    act = copy_file_if_different(root_thumb, dst_thumb, dry_run)
                    if act in ("created", "updated"):
                        stats[act] += 1
                        print(f"  [{'+' if act == 'created' else '*'}] {act.capitalize()} (fallback): {dst_thumb.relative_to(data_dir)}")
                    else:
                        stats["unchanged"] += 1

        src_mods = mod_path / "Mods"
        if src_mods.exists():
            for mod_uuid in src_mods.iterdir():
                if mod_uuid.is_dir() and not (mod_uuid / "mod_publish_logo.png").exists():
                    dst_logo = data_dir / "Mods" / mod_uuid.name / "mod_publish_logo.png"
                    act = copy_file_if_different(root_thumb, dst_logo, dry_run)
                    if act in ("created", "updated"):
                        stats[act] += 1
                        print(f"  [{'+' if act == 'created' else '*'}] {act.capitalize()} (fallback): {dst_logo.relative_to(data_dir)}")
                    else:
                        stats["unchanged"] += 1

    return stats


LEGACY_PATTERNS = [
    "PactOfTheBladeUnleashed",
    "PaladinUnbound",
    "UnlockLevelCurveExtended",
]


def clean_legacy(data_dir: Path, dry_run: bool = False) -> int:
    """
    Finds and removes legacy mod folders and files from Steam Data/ directory.
    """
    removed_count = 0
    print("\n🧹 Scanning for legacy mod folders and files in Data/...")

    for subdir_name in ["Projects", "Mods", "Public"]:
        parent = data_dir / subdir_name
        if not parent.exists():
            continue
        for item in parent.iterdir():
            if any(pat in item.name for pat in LEGACY_PATTERNS):
                removed_count += 1
                if dry_run:
                    print(f"  [-] Legacy purge (preview): {item.relative_to(data_dir)}")
                else:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    print(f"  [-] Legacy purged: {item.relative_to(data_dir)}")

    # Check Localization/English/
    loc_dir = data_dir / "Localization" / "English"
    if loc_dir.exists():
        for item in loc_dir.iterdir():
            if any(pat in item.name for pat in LEGACY_PATTERNS):
                removed_count += 1
                if dry_run:
                    print(f"  [-] Legacy purge (preview): {item.relative_to(data_dir)}")
                else:
                    item.unlink()
                    print(f"  [-] Legacy purged: {item.relative_to(data_dir)}")

    if removed_count == 0:
        print("  No legacy mod files found.")
    return removed_count


def run_sync(
    source_dir: Path,
    data_dir: Path,
    mod_filter: list = None,
    dry_run: bool = False,
    clean: bool = False,
    bump_build: bool = False,
):
    if not source_dir.exists():
        print(f"❌ Error: Source directory does not exist: {source_dir}", file=sys.stderr)
        sys.exit(1)

    if not data_dir.exists():
        if dry_run:
            print(f"⚠️ Warning: Target Data directory does not exist (dry run): {data_dir}")
        else:
            print(f"❌ Error: Target Data directory does not exist: {data_dir}", file=sys.stderr)
            sys.exit(1)

    print(f"=== BG3 Custom Mod Sync ===")
    print(f"Source:      {source_dir.resolve()}")
    print(f"Destination: {data_dir.resolve()}")
    print(f"Mode:        {'DRY RUN (no files modified)' if dry_run else 'LIVE SYNC'}")

    if clean:
        clean_legacy(data_dir, dry_run)

    # Discover mods
    mod_folders = [d for d in source_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if mod_filter:
        mod_folders = [d for d in mod_folders if d.name in mod_filter]

    if not mod_folders:
        print("No mod directories found to synchronize.")
        return

    # Auto-bump build number if requested
    if bump_build:
        try:
            from bump_mod_version import bump_version
            for mod_path in sorted(mod_folders):
                bump_version(mod_path.name, action="build", dry_run=dry_run)
        except Exception as e:
            print(f"⚠️ Warning: Failed to auto-bump build version: {e}")

    total_stats = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for mod_path in sorted(mod_folders):
        stats = sync_mod(mod_path, data_dir, dry_run)
        for k, v in stats.items():
            total_stats[k] += v

    print("\n" + "=" * 40)
    print("Sync Summary:")
    print(f"  Files created:   {total_stats['created']}")
    print(f"  Files updated:   {total_stats['updated']}")
    print(f"  Files unchanged: {total_stats['unchanged']}")
    print(f"  Files skipped:   {total_stats['skipped']}")
    print("=" * 40 + "\n")


def watch_and_sync(source_dir: Path, data_dir: Path, mod_filter: list = None, interval: float = 2.0, clean: bool = False):
    print(f"👀 Watching {source_dir} for changes every {interval}s... Press Ctrl+C to stop.")
    try:
        while True:
            run_sync(source_dir, data_dir, mod_filter, dry_run=False, clean=clean)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Sync custom BG3 mods from my_mods/ to Steam Baldurs Gate 3/Data directory"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("my_mods"),
        help="Path to source directory containing mods (default: my_mods)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=get_default_data_dir(),
        help="Path to Baldurs Gate 3 Data directory",
    )
    parser.add_argument(
        "--mods",
        nargs="+",
        help="Specific mod names to sync (default: all subdirectories)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files that would be created or updated without modifying disk",
    )
    parser.add_argument(
        "--clean-legacy",
        action="store_true",
        default=True,
        help="Clean up legacy mod folders/files in Steam Data (default: True)",
    )
    parser.add_argument(
        "--no-clean-legacy",
        action="store_false",
        dest="clean_legacy",
        help="Disable automatic cleaning of legacy mod folders/files",
    )
    parser.add_argument(
        "--bump-build",
        action="store_true",
        help="Automatically increment build number (+1) in meta.lsx before syncing",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch source directory and sync continuously",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Watch interval in seconds (default: 2.0)",
    )

    args = parser.parse_args()

    if args.watch:
        watch_and_sync(args.source_dir, args.data_dir, args.mods, args.interval, clean=args.clean_legacy)
    else:
        run_sync(
            args.source_dir,
            args.data_dir,
            args.mods,
            args.dry_run,
            clean=args.clean_legacy,
            bump_build=args.bump_build,
        )


if __name__ == "__main__":
    main()
