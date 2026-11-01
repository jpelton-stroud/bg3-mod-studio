#!/usr/bin/env python3
"""
sync_game_data.py
--------------------
Synchronizes custom Baldur's Gate 3 mods authored in `my_mods/` subdirectories
directly into the game's Data directory (C:\\Program Files (x86)\\Steam\\steamapps\\common\\Baldurs Gate 3\\Data)
for loading, editing, and publishing via the Baldur's Gate 3 Toolkit and mod.io.

Features:
- Idempotent and safe copy (only writes modified/new files)
- Automatically excludes development artifacts (README.md, task.md, .git, etc.)
- Mirrors localization XMLs to both Data/Localization/English and Data/Mods/<UUID>/Localization/English
- Supports --clean-mod to purge unpacked development files for clean-room testing
- Ensures project thumbnails and publish logos are synchronized
- Supports --dry-run to preview changes
- Supports --watch for automatic live-syncing during development
"""

import argparse
import filecmp
import json
import os
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bg3_core.env_paths import (
    detect_bg3_appdata_dirs,
    detect_data_dir,
    get_authored_mods_dir,
    get_env_var,
    normalize_mod_key,
    resolve_mod_dir,
)
from bg3_core.larian_parsers import compile_xml_bytes_to_loca

EXCLUDED_FILENAMES = {
    ".gitignore",
    ".gitkeep",
    "desktop.ini",
    ".ds_store",
    "thumbs.db",
    "readme.md",
    "task.md",
    "modio_description.md",
    "modio_description.html",
}

EXCLUDED_EXTENSIONS = {
    ".tmp",
    ".bak",
    ".py",
    ".pyc",
}

EXCLUDED_DIRECTORIES = {
    "__pycache__",
    ".git",
    "dist",
    "metadata",
}


def get_default_data_dir() -> Path:
    return detect_data_dir()


def write_bytes_if_different(data: bytes, dst: Path, dry_run: bool = False) -> str:
    """Writes bytes to dst if dst does not exist or content differs."""
    if not dst.exists():
        action = "created"
    elif dst.read_bytes() != data:
        action = "updated"
    else:
        return "unchanged"

    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    return action


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


BUILTIN_MODULES = {"Gustav", "GustavDev", "GustavX", "Shared", "SharedDev", "Engine", "PhotoMode"}

def check_mod_dependencies(mod_path: Path, data_dir: Path) -> list:
    """
    Validates that all dependencies declared in meta.lsx are resolvable in the game environment.
    Returns list of missing dependency descriptions.
    """
    missing: list[str] = []
    meta_files = list(mod_path.glob("Mods/*/meta.lsx"))
    if not meta_files:
        return missing

    user_mods_env = os.environ.get("BG3_USER_MODS_DIR")
    if user_mods_env:
        appdata_mods_dirs = [Path(user_mods_env)]
    else:
        appdata_mods_dirs = [d / "Mods" for d in detect_bg3_appdata_dirs()]

    for meta_file in meta_files:
        try:
            tree = ET.parse(meta_file)
            root = tree.getroot()
            dep_nodes = root.findall(".//node[@id='Dependencies']//node[@id='ModuleShortDesc']")
            for dep in dep_nodes:
                name_attr = dep.find("attribute[@id='Name']")
                folder_attr = dep.find("attribute[@id='Folder']")
                uuid_attr = dep.find("attribute[@id='UUID']")
                dep_name = name_attr.get("value") if name_attr is not None else ""
                dep_folder = (folder_attr.get("value") if folder_attr is not None else None) or dep_name or ""
                dep_uuid = uuid_attr.get("value", "").lower() if uuid_attr is not None else ""
                if not dep_name or dep_name in BUILTIN_MODULES:
                    continue

                in_data_mods = (data_dir / "Mods" / dep_folder).is_dir() if dep_folder else False
                in_data_pak = (
                    (data_dir / f"{dep_name}.pak").is_file()
                    or (data_dir / f"{dep_folder}.pak").is_file()
                    or (data_dir / "Mods" / f"{dep_name}.pak").is_file()
                    or (data_dir / "Mods" / f"{dep_folder}.pak").is_file()
                )
                in_appdata_pak = False
                for appdata_mods in appdata_mods_dirs:
                    if appdata_mods.is_dir():
                        norm_folder = normalize_mod_key(dep_folder)
                        norm_name = normalize_mod_key(dep_name)
                        for p in appdata_mods.glob("*.pak"):
                            p_stem = p.stem
                            p_norm = normalize_mod_key(p_stem)
                            if (dep_uuid and dep_uuid in p_stem.lower()) or p_norm == norm_folder or p_norm == norm_name:
                                in_appdata_pak = True
                                break
                    if in_appdata_pak:
                        break

                if not (in_data_mods or in_data_pak or in_appdata_pak):
                    missing.append(f"{dep_name} (folder: {dep_folder})")
        except Exception as e:
            print(f"  ⚠️ Warning: Failed to parse dependencies from {meta_file}: {e}")

    return missing


def sync_mod(mod_path: Path, data_dir: Path, dry_run: bool = False, quiet: bool = False) -> dict:
    """
    Synchronizes a single mod folder into Data/.
    """
    stats: dict[str, int] = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0, "compiled_loca": 0}
    mod_name = mod_path.name
    if not quiet:
        print(f"\n📦 Processing mod: {mod_name} ({mod_path})")

    # Check dependencies before syncing
    missing_deps = check_mod_dependencies(mod_path, data_dir)
    if missing_deps and not quiet:
        print(f"  ⚠️  WARNING: Mod '{mod_name}' has unresolved dependencies:")
        for m in missing_deps:
            print(f"      - {m}")
        print("      Opening this mod in the Toolkit will cause a SILENT CRASH unless these dependencies are installed!")

    # 1. Detect subdirectories: Projects, Mods, Public, Editor
    subdirs = ["Projects", "Mods", "Public", "Editor"]
    for subdir in subdirs:
        src_sub = mod_path / subdir
        if not src_sub.exists():
            continue
        dst_sub = data_dir / subdir

        for root, dirs, files in os.walk(src_sub):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRECTORIES and not d.startswith(".")]
            rel_root = Path(root).relative_to(src_sub)
            for file in files:
                file_lower = file.lower()
                if file_lower in EXCLUDED_FILENAMES or any(file_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                    stats["skipped"] += 1
                    continue

                src_file = Path(root) / file
                dst_file = dst_sub / rel_root / file

                action = copy_file_if_different(src_file, dst_file, dry_run)
                if action == "created":
                    stats["created"] += 1
                    if not quiet:
                        print(f"  [+] Create: {dst_file.relative_to(data_dir)}")
                elif action == "updated":
                    stats["updated"] += 1
                    if not quiet:
                        print(f"  [*] Update: {dst_file.relative_to(data_dir)}")
                else:
                    stats["unchanged"] += 1

    # 2. Handle Localization:
    # Strictly mod-local: Data/Mods/<ModFolder_UUID>/Localization/<rel>
    # Note: NEVER write loose XMLs to Data/Localization/English/ or Data/Mods/.../Localization/
    # because Larian's TranslatedStringRepository::LoadFromXmlFile crashes during module unload
    # with EXCEPTION_ACCESS_VIOLATION (null FileSystem pointer at offset 0x70).
    # Automatically compile .xml files into binary .loca files and copy any pre-existing .loca files.
    src_loc = mod_path / "Localization"
    if src_loc.exists():
        src_mods = mod_path / "Mods"
        if src_mods.exists():
            for mod_uuid_dir in src_mods.iterdir():
                if mod_uuid_dir.is_dir():
                    dst_loc_mod = data_dir / "Mods" / mod_uuid_dir.name / "Localization"
                    for root, _dirs, files in os.walk(src_loc):
                        rel_root = Path(root).relative_to(src_loc)
                        files_set = set(files)
                        for file in sorted(files):
                            src_file = Path(root) / file
                            if file.endswith(".xml"):
                                loca_name = Path(file).with_suffix(".loca").name
                                dst_file = dst_loc_mod / rel_root / loca_name
                                try:
                                    loca_bytes = compile_xml_bytes_to_loca(src_file.read_bytes())
                                    action = write_bytes_if_different(loca_bytes, dst_file, dry_run)
                                    stats["compiled_loca"] += 1
                                    if action == "created":
                                        stats["created"] += 1
                                        if not quiet:
                                            print(f"  [+] Compile .loca: {dst_file.relative_to(data_dir)}")
                                    elif action == "updated":
                                        stats["updated"] += 1
                                        if not quiet:
                                            print(f"  [*] Compile .loca: {dst_file.relative_to(data_dir)}")
                                    else:
                                        stats["unchanged"] += 1

                                    # Emit standard lowercase language loca (e.g. english.loca) for Larian engine runtime
                                    lang_loca_name = f"{rel_root.name.lower()}.loca"
                                    if lang_loca_name != loca_name.lower():
                                        lang_dst_file = dst_loc_mod / rel_root / lang_loca_name
                                        write_bytes_if_different(loca_bytes, lang_dst_file, dry_run)
                                except Exception as e:
                                    if not quiet:
                                        print(f"  ⚠️ Warning: Failed to compile {src_file.name} to .loca: {e}")
                            elif file.endswith(".loca"):
                                # Only copy raw .loca if a matching .xml wasn't just compiled
                                xml_equivalent = Path(file).with_suffix(".xml").name
                                if xml_equivalent in files_set:
                                    continue
                                dst_file = dst_loc_mod / rel_root / file
                                action = copy_file_if_different(src_file, dst_file, dry_run)
                                if action == "created":
                                    stats["created"] += 1
                                    if not quiet:
                                        print(f"  [+] Create (mod-local): {dst_file.relative_to(data_dir)}")
                                elif action == "updated":
                                    stats["updated"] += 1
                                    if not quiet:
                                        print(f"  [*] Update (mod-local): {dst_file.relative_to(data_dir)}")
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
                        if not quiet:
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
                        if not quiet:
                            print(f"  [{'+' if act == 'created' else '*'}] {act.capitalize()} (fallback): {dst_logo.relative_to(data_dir)}")
                    else:
                        stats["unchanged"] += 1

    result: dict[str, Any] = dict(stats)
    result["missing_dependencies"] = missing_deps
    return result


LEGACY_PATTERNS = [
    "PactOfTheBladeUnleashed",
    "PaladinUnbound",
    "UnlockLevelCurveExtended",
]


def clean_legacy(data_dir: Path, dry_run: bool = False, quiet: bool = False) -> int:
    """
    Finds and removes legacy mod folders and files from Steam Data/ directory.
    """
    removed_count = 0
    if not quiet:
        print("\n🧹 Scanning for legacy mod folders and files in Data/...")

    for subdir_name in ["Projects", "Mods", "Public", "Editor/Mods"]:
        parent = data_dir / subdir_name
        if not parent.exists():
            continue
        for item in parent.iterdir():
            if any(pat in item.name for pat in LEGACY_PATTERNS):
                removed_count += 1
                if dry_run:
                    if not quiet:
                        print(f"  [-] Legacy purge (preview): {item.relative_to(data_dir)}")
                else:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    if not quiet:
                        print(f"  [-] Legacy purged: {item.relative_to(data_dir)}")

    # Check Localization/English/
    loc_dir = data_dir / "Localization" / "English"
    if loc_dir.exists():
        for item in loc_dir.iterdir():
            if any(pat in item.name for pat in LEGACY_PATTERNS):
                removed_count += 1
                if dry_run:
                    if not quiet:
                        print(f"  [-] Legacy purge (preview): {item.relative_to(data_dir)}")
                else:
                    item.unlink()
                    if not quiet:
                        print(f"  [-] Legacy purged: {item.relative_to(data_dir)}")

    if removed_count == 0 and not quiet:
        print("  No legacy mod files found.")
    return removed_count


def get_custom_mod_prefixes(source_dir: Path | None = None) -> list[str]:
    """Dynamically collects mod directory and folder prefixes from my_mods/."""
    prefixes: list[str] = []
    root = source_dir or Path(get_env_var("BG3_MODS_DIR") or get_authored_mods_dir())
    if root.is_dir():
        for mod_folder in root.iterdir():
            if not mod_folder.is_dir() or mod_folder.name.startswith("."):
                continue
            prefixes.append(mod_folder.name)
            mods_sub = mod_folder / "Mods"
            if mods_sub.is_dir():
                for sub in mods_sub.iterdir():
                    if sub.is_dir():
                        prefixes.append(sub.name)
                        prefixes.append(sub.name.split("_")[0])
    return sorted(set(prefixes))


def clean_mod_data(mod_path: Path, data_dir: Path, dry_run: bool = False, quiet: bool = False) -> dict:
    """
    Purges a specific custom mod's loose files from Data/ (Projects, Mods, Public, Editor/Mods, Localization).
    Does NOT touch base game files or other mods.
    """
    removed_paths = []
    if not data_dir.exists():
        return {
            "status": "success",
            "mod": mod_path.name,
            "removed_count": 0,
            "removed_paths": [],
            "dry_run": dry_run,
        }

    # 1. Identify all folder names / UUIDs associated with this mod
    folder_names = set()
    for sub_rel in ["Mods", "Projects", "Public", "Editor/Mods"]:
        sub_dir = mod_path / Path(sub_rel)
        if sub_dir.is_dir():
            for child in sub_dir.iterdir():
                if child.is_dir():
                    folder_names.add(child.name)
                    folder_names.add(child.name.split("_")[0])

    folder_names.add(mod_path.name)

    # Filter out empty or unsafe names
    safe_folder_names = set()
    for name in folder_names:
        clean_name = name.strip()
        if not clean_name or clean_name in BUILTIN_MODULES:
            continue
        if any(clean_name.lower().startswith(b.lower()) for b in BUILTIN_MODULES):
            continue
        safe_folder_names.add(clean_name)

    if not safe_folder_names:
        if not quiet:
            print(f"  ⚠️ No safe mod folder names resolved for '{mod_path.name}'.")
        return {"status": "success", "mod": mod_path.name, "removed_count": 0, "removed_paths": [], "dry_run": dry_run}

    if not quiet:
        print(f"\n🧹 Purging loose Data files for mod '{mod_path.name}'...")

    # 2. Remove matching subdirectories in Projects, Mods, Public, Editor/Mods
    for subdir_name in ["Projects", "Mods", "Public", "Editor/Mods"]:
        parent = data_dir / Path(subdir_name)
        if not parent.exists():
            continue
        for item in parent.iterdir():
            is_match = False
            for safe_name in safe_folder_names:
                if item.name == safe_name or item.name.startswith(f"{safe_name}_"):
                    is_match = True
                    break
                if normalize_mod_key(item.name) == normalize_mod_key(safe_name):
                    is_match = True
                    break
            if is_match and item.name not in BUILTIN_MODULES and not any(item.name.lower().startswith(b.lower()) for b in BUILTIN_MODULES):
                rel_str = str(item.relative_to(data_dir))
                removed_paths.append(rel_str)
                if dry_run:
                    if not quiet:
                        print(f"  [-] Data purge (preview): {rel_str}")
                else:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    if not quiet:
                        print(f"  [-] Data purged: {rel_str}")

    # 3. Check and clean loose XMLs / .loca in Data/Localization/English/
    loc_dir = data_dir / "Localization" / "English"
    if loc_dir.exists():
        for item in loc_dir.iterdir():
            if any(pat.lower() in item.name.lower() for pat in safe_folder_names):
                rel_str = str(item.relative_to(data_dir))
                removed_paths.append(rel_str)
                if dry_run:
                    if not quiet:
                        print(f"  [-] Localization purge (preview): {rel_str}")
                else:
                    item.unlink()
                    if not quiet:
                        print(f"  [-] Localization purged: {rel_str}")

    if not quiet and not removed_paths:
        print(f"  No loose Data files found for mod '{mod_path.name}'.")

    return {
        "status": "success",
        "mod": mod_path.name,
        "removed_count": len(removed_paths),
        "removed_paths": removed_paths,
        "dry_run": dry_run,
    }


def clean_custom_mods(data_dir: Path, dry_run: bool = False, keep_mods: list[Any] | None = None, quiet: bool = False, source_dir: Path | None = None) -> int:
    """
    Purges custom studio mods from Data/ without touching eldritch-blast baseline or base game files.
    """
    removed_count = 0
    keep_set = set(keep_mods or [])
    custom_prefixes = get_custom_mod_prefixes(source_dir)
    if not quiet:
        print("\n🧹 Scanning for custom studio mod folders/files in Data/...")

    for subdir_name in ["Projects", "Mods", "Public", "Editor/Mods"]:
        parent = data_dir / Path(subdir_name)
        if not parent.exists():
            continue
        for item in parent.iterdir():
            if "eldritch-blast" in item.name.lower():
                continue
            if any(item.name.startswith(p) for p in custom_prefixes):
                if any(item.name.startswith(k) for k in keep_set):
                    continue
                removed_count += 1
                if dry_run:
                    if not quiet:
                        print(f"  [-] Custom purge (preview): {item.relative_to(data_dir)}")
                else:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    if not quiet:
                        print(f"  [-] Custom purged: {item.relative_to(data_dir)}")

    # Check and clean loose XMLs in Data/Localization/English/
    loc_dir = data_dir / "Localization" / "English"
    if loc_dir.exists():
        for item in loc_dir.iterdir():
            if "eldritch-blast" in item.name.lower():
                continue
            if any(item.name.startswith(p) for p in custom_prefixes):
                removed_count += 1
                if dry_run:
                    if not quiet:
                        print(f"  [-] Custom localization purge (preview): {item.relative_to(data_dir)}")
                else:
                    item.unlink()
                    if not quiet:
                        print(f"  [-] Custom localization purged: {item.relative_to(data_dir)}")

    # Check and clean any loose XMLs in Data/Mods/*/Localization
    mods_dir = data_dir / "Mods"
    if mods_dir.exists():
        for m_folder in mods_dir.iterdir():
            if m_folder.is_dir():
                m_loc = m_folder / "Localization"
                if m_loc.exists():
                    for xml_file in list(m_loc.rglob("*.xml")):
                        removed_count += 1
                        if dry_run:
                            if not quiet:
                                print(f"  [-] Loose XML purge (preview): {xml_file.relative_to(data_dir)}")
                        else:
                            xml_file.unlink()
                            if not quiet:
                                print(f"  [-] Loose XML purged: {xml_file.relative_to(data_dir)}")

    if removed_count == 0 and not quiet:
        print("  No custom studio mod files found to clean.")
    return removed_count


def matches_mod_filter(mod_dir: Path, filters: list[str]) -> bool:
    """Matches mod directory by slug, PascalCase name, or <ModName>_<UUID> folder name."""
    candidates = {normalize_mod_key(mod_dir.name), mod_dir.name.lower()}
    mods_sub = mod_dir / "Mods"
    if mods_sub.is_dir():
        for child in mods_sub.iterdir():
            if child.is_dir():
                candidates.add(child.name.lower())
                candidates.add(normalize_mod_key(child.name.split("_")[0]))
    for f in filters:
        f_low = f.strip().lower()
        f_norm = normalize_mod_key(f)
        if f_low in candidates or f_norm in candidates or any(f_norm and f_norm in c for c in candidates):
            return True
    return False


def run_sync(
    source_dir: Path,
    data_dir: Path,
    mod_filter: list[Any] | None = None,
    dry_run: bool = False,
    clean: bool = False,
    clean_custom: bool = False,
    bump_build: bool = False,
    json_mode: bool = False,
) -> None:
    if not source_dir.exists():
        msg = f"Source directory does not exist: {source_dir}"
        if json_mode:
            print(json.dumps({"error": msg, "success": False}, indent=2))
        else:
            print(f"❌ Error: {msg}", file=sys.stderr)
        sys.exit(1)

    if not data_dir.exists():
        if dry_run:
            if not json_mode:
                print(f"⚠️ Warning: Target Data directory does not exist (dry run): {data_dir}")
        else:
            msg = f"Target Data directory does not exist: {data_dir}"
            if json_mode:
                print(json.dumps({"error": msg, "success": False}, indent=2))
            else:
                print(f"❌ Error: {msg}", file=sys.stderr)
            sys.exit(1)

    if not json_mode:
        print("=== BG3 Custom Mod Sync ===")
        print(f"Source:      {source_dir.resolve()}")
        print(f"Destination: {data_dir.resolve()}")
        print(f"Mode:        {'DRY RUN (no files modified)' if dry_run else 'LIVE SYNC'}")

    if clean and data_dir.exists():
        clean_legacy(data_dir, dry_run, quiet=json_mode)

    if clean_custom and data_dir.exists():
        clean_custom_mods(data_dir, dry_run, quiet=json_mode)

    # Discover mods
    mod_folders = [d for d in source_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if mod_filter:
        mod_folders = [d for d in mod_folders if matches_mod_filter(d, mod_filter)]

    if not mod_folders:
        if json_mode:
            print(json.dumps({"status": "no_mods_matched", "mods_synced": [], "summary": {}}, indent=2))
        else:
            print("No mod directories found to synchronize.")
        return

    # Auto-bump build number if requested
    if bump_build:
        try:
            from bg3_core.bump_mod_version import bump_version
            for mod_path in sorted(mod_folders):
                bump_version(mod_path.name, action="build", dry_run=dry_run)
        except Exception as e:
            if not json_mode:
                print(f"⚠️ Warning: Failed to auto-bump build version: {e}")

    total_stats = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0, "compiled_loca": 0}
    per_mod_results = []
    for mod_path in sorted(mod_folders):
        stats = sync_mod(mod_path, data_dir, dry_run, quiet=json_mode)
        for k in total_stats:
            total_stats[k] += stats.get(k, 0)
        per_mod_results.append({"mod": mod_path.name, **stats})

    if json_mode:
        print(json.dumps({
            "status": "success",
            "source_dir": str(source_dir.resolve()),
            "data_dir": str(data_dir.resolve()),
            "dry_run": dry_run,
            "mods_synced": [m["mod"] for m in per_mod_results],
            "summary": total_stats,
            "results": per_mod_results,
        }, indent=2))
    else:
        print("\n" + "=" * 40)
        print("Sync Summary:")
        print(f"  Files created:   {total_stats['created']}")
        print(f"  Files updated:   {total_stats['updated']}")
        print(f"  Files unchanged: {total_stats['unchanged']}")
        print(f"  Files skipped:   {total_stats['skipped']}")
        print(f"  Compiled .loca:  {total_stats['compiled_loca']}")
        print("=" * 40 + "\n")


def watch_and_sync(source_dir: Path, data_dir: Path, mod_filter: list[Any] | None = None, interval: float = 2.0, clean: bool = False, clean_custom: bool = False) -> None:
    print(f"👀 Watching {source_dir} for changes every {interval}s... Press Ctrl+C to stop.")
    try:
        while True:
            run_sync(source_dir, data_dir, mod_filter, dry_run=False, clean=clean, clean_custom=clean_custom)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync custom BG3 mods from my_mods/ to Steam Baldurs Gate 3/Data directory"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(os.environ.get("BG3_MODS_DIR") or get_authored_mods_dir()),
        help="Path to source directory containing mods (default: $BG3_STUDIO_DIR/Mods/authored or $BG3_MODS_DIR)",
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
        help="Specific mod slugs or names to sync (default: all subdirectories)",
    )
    parser.add_argument(
        "--mod",
        help="Single mod slug or name to sync (alias for --mods)",
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
        "--clean-custom",
        action="store_true",
        help="Purge all custom studio mods from Steam Data (protects base game and eldritch-blast)",
    )
    parser.add_argument(
        "--clean-mod",
        help="Purge a specific custom mod's loose files from Steam Data/ (Projects, Mods, Public, Editor/Mods, Localization) and exit",
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON summary",
    )

    args = parser.parse_args()

    if args.clean_mod:
        mod_dir = resolve_mod_dir(args.clean_mod, prefer_my_mods=True)
        if not mod_dir:
            candidate = args.source_dir / args.clean_mod
            if candidate.is_dir():
                mod_dir = candidate
        if not mod_dir:
            msg = f"Mod '{args.clean_mod}' not found in my_mods/ or library."
            if args.json:
                print(json.dumps({"error": msg, "success": False}, indent=2))
            else:
                print(f"❌ Error: {msg}", file=sys.stderr)
            sys.exit(1)
        res = clean_mod_data(mod_dir, args.data_dir, dry_run=args.dry_run, quiet=args.json)
        if args.json:
            print(json.dumps(res, indent=2))
        sys.exit(0)

    mod_filter = list(args.mods or [])
    if args.mod:
        mod_filter.append(args.mod)

    if args.watch:
        watch_and_sync(args.source_dir, args.data_dir, mod_filter or None, args.interval, clean=args.clean_legacy, clean_custom=args.clean_custom)
    else:
        run_sync(
            args.source_dir,
            args.data_dir,
            mod_filter or None,
            args.dry_run,
            clean=args.clean_legacy,
            clean_custom=args.clean_custom,
            bump_build=args.bump_build,
            json_mode=args.json,
        )


if __name__ == "__main__":
    main()
