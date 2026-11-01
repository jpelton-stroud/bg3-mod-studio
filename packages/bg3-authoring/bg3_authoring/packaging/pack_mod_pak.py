#!/usr/bin/env python3
"""
pack_mod_pak.py - Pure-Python LSPK v18 .pak package builder for Baldur's Gate 3 mods.

Packages mod files into standard Larian Package v18 (.pak) format with zlib
compression, enabling distribution and local Mod Manager installation without
requiring the official Toolkit or external Windows binaries.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Sequence

from bg3_core.env_paths import DIST_DIR, detect_bg3_appdata_dirs, get_env_var, resolve_mod_dir
from bg3_core.larian_parsers import compile_xml_bytes_to_loca
from bg3_core.lspk import LspkArchive
from bg3_core.lspk import build_lspk_archive as build_pak_archive

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
    "projects",
    "editor",
    "metadata",
    "__pycache__",
    ".git",
    "dist",
}


def should_include_file(rel_path: Path, include_projects: bool = False) -> bool:
    """Filters files for inclusion in release pak archive."""
    parts = [p.lower() for p in rel_path.parts]

    # Exclude root-level thumbnail.png (only Mods/*/mod_publish_logo.png or Projects/*/thumbnail.png belong in subfolders)
    if len(parts) == 1 and parts[0] == "thumbnail.png":
        return False

    # Exclude dotfiles and dotdirs (e.g. .test_deps.json, .gitignore)
    if any(p.startswith(".") for p in parts):
        return False

    for part in parts[:-1]:
        if part in EXCLUDED_DIRECTORIES:
            if part == "projects" and include_projects:
                continue
            return False

    name_lower = rel_path.name.lower()
    if name_lower in EXCLUDED_FILENAMES:
        return False

    if any(name_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
        return False

    return True


def collect_mod_files(mod_dir: Path, include_projects: bool = False) -> list[tuple[str, bytes]]:
    """
    Gathers all releasable files relative to mod root as (archive_name, payload_bytes).
    Automatically compiles Localization/<Lang>/*.xml into binary .loca payloads.
    """
    entries_map: dict[str, bytes] = {}
    for root, _, filenames in os.walk(mod_dir):
        root_path = Path(root)
        files_set = set(filenames)
        for fname in sorted(filenames):
            file_path = root_path / fname
            rel_path = file_path.relative_to(mod_dir)
            if not should_include_file(rel_path, include_projects):
                continue

            parts_lower = [p.lower() for p in rel_path.parts]
            if "localization" in parts_lower and fname.lower().endswith(".xml"):
                loca_rel = rel_path.with_suffix(".loca")
                archive_name = loca_rel.as_posix()
                entries_map[archive_name] = compile_xml_bytes_to_loca(file_path.read_bytes())
                continue

            if "localization" in parts_lower and fname.lower().endswith(".loca"):
                xml_equiv = Path(fname).with_suffix(".xml").name
                if xml_equiv in files_set:
                    continue

            archive_name = rel_path.as_posix()
            entries_map[archive_name] = file_path.read_bytes()

    return sorted(entries_map.items(), key=lambda x: x[0])




def verify_pak_archive(pak_bytes: bytes, original_files: Sequence[tuple[str, bytes | Path]]) -> bool:
    """Verifies that the generated pak can be completely parsed and extracted."""
    if LspkArchive is None:
        return True

    archive = LspkArchive(pak_bytes)
    if len(archive.files) != len(original_files):
        return False

    for entry in archive.files:
        extracted = archive.extract_file(entry)
        norm_name = entry["name"].replace("/", "\\")
        matched = False
        for a_name, item in original_files:
            if a_name.replace("/", "\\") == norm_name:
                orig_data = item.read_bytes() if isinstance(item, Path) else item
                if extracted == orig_data:
                    matched = True
                    break
        if not matched:
            return False

    return True


def detect_mods_dir() -> Path | None:
    """Detect Baldur's Gate 3 Mods directory in AppData across WSL, native Linux, and Windows."""
    env_override = get_env_var("BG3_USER_MODS_DIR")
    if not env_override:
        # Check BG3_LOCALAPPDATA
        bg3_local = get_env_var("BG3_LOCALAPPDATA")
        if bg3_local:
            candidate = Path(bg3_local) / "Mods"
            if candidate.is_dir() or candidate.parent.exists():
                return candidate
    if env_override:
        p = Path(env_override)
        if p.is_dir() or p.parent.exists():
            return p

    for appdata in detect_bg3_appdata_dirs():
        target = appdata / "Mods"
        if target.is_dir() or appdata.is_dir():
            return target

    return None


def get_mod_pak_filename(mod_dir: Path) -> str:
    """Inspect mod directory for meta.lsx and generate standard Toolkit pak filename (<Folder>_<UUID>.pak)."""
    meta_files = list(mod_dir.glob("Mods/*/meta.lsx")) or list(mod_dir.glob("Projects/*/meta.lsx"))
    if meta_files:
        try:
            content = meta_files[0].read_text(encoding="utf-8")
            mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
            target = mod_info.group(1) if mod_info else content
            folder_match = re.search(r'<attribute\s+id="Folder"\s+type="LSString"\s+value="([^"]*)"', target)
            uuid_match = re.search(r'<attribute\s+id="UUID"\s+type="(?:FixedString|guid|LSString)"\s+value="([^"]*)"', target)
            if folder_match:
                folder = folder_match.group(1)
                uuid_val = uuid_match.group(1) if uuid_match else ""
                if uuid_val and not folder.endswith(uuid_val):
                    return f"{folder}_{uuid_val}.pak"
                return f"{folder}.pak"
        except Exception:
            pass
    return f"{mod_dir.name}.pak"


def clean_local_pak(mod_dir: Path, dry_run: bool = False) -> dict:
    """
    Deletes locally published .pak file(s) for the specified mod from AppData Mods directory.
    """
    mods_dir = detect_mods_dir()
    if not mods_dir or not mods_dir.is_dir():
        return {
            "status": "success",
            "mod": mod_dir.name,
            "removed_count": 0,
            "removed_paks": [],
            "dry_run": dry_run,
        }

    # Extract mod identifiers
    candidates = {get_mod_pak_filename(mod_dir).lower(), f"{mod_dir.name}.pak".lower()}
    uuid_val = ""
    folder_val = ""
    meta_files = list(mod_dir.glob("Mods/*/meta.lsx")) or list(mod_dir.glob("Projects/*/meta.lsx"))
    if meta_files:
        try:
            content = meta_files[0].read_text(encoding="utf-8")
            mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
            target = mod_info.group(1) if mod_info else content
            folder_match = re.search(r'<attribute\s+id="Folder"\s+type="LSString"\s+value="([^"]*)"', target)
            uuid_match = re.search(r'<attribute\s+id="UUID"\s+type="(?:FixedString|guid|LSString)"\s+value="([^"]*)"', target)
            if folder_match:
                folder_val = folder_match.group(1).lower()
                candidates.add(f"{folder_val}.pak")
            if uuid_match:
                uuid_val = uuid_match.group(1).lower()
        except Exception:
            pass

    removed_paks = []
    for pak_path in mods_dir.glob("*.pak"):
        p_name = pak_path.name.lower()
        matched = False
        if p_name in candidates:
            matched = True
        elif uuid_val and uuid_val in p_name:
            matched = True
        elif folder_val and (p_name.startswith(f"{folder_val}_") or p_name == f"{folder_val}.pak"):
            matched = True

        if matched:
            removed_paks.append(str(pak_path))
            if not dry_run:
                try:
                    pak_path.unlink()
                except OSError as e:
                    raise OSError(f"Failed to delete local .pak at '{pak_path}': {e}") from e

    return {
        "status": "success",
        "mod": mod_dir.name,
        "removed_count": len(removed_paks),
        "removed_paks": removed_paks,
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pure-Python LSPK v18 .pak package builder for Baldur's Gate 3 mods."
    )
    parser.add_argument("--mod", required=True, help="Mod name/slug in my_mods/ or directory path.")
    parser.add_argument("--out", help="Output .pak file path (default: dist/<mod_slug>.pak).")
    parser.add_argument("--output-dir", help="Output directory for generated .pak file.")
    parser.add_argument(
        "--publish-local",
        action="store_true",
        help="Publish .pak directly to the local BG3 AppData Mods directory, replacing the Toolkit's 'Publish Local' step.",
    )
    parser.add_argument(
        "--clean-local",
        action="store_true",
        help="Purge local test .pak file(s) for this mod from the local BG3 AppData Mods directory.",
    )
    parser.add_argument(
        "--include-projects",
        action="store_true",
        help="Include Projects/ directory (normally excluded in release packages).",
    )
    parser.add_argument(
        "--uncompressed",
        action="store_true",
        help="Store files uncompressed instead of using standard zlib.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without modifying files on disk.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON summary.",
    )

    args = parser.parse_args()

    try:
        mod_dir = resolve_mod_dir(args.mod, prefer_my_mods=True)
        if mod_dir is None:
            raise FileNotFoundError(f"Mod directory not found: {args.mod}")
        mod_slug = mod_dir.name

        if args.clean_local:
            res = clean_local_pak(mod_dir, dry_run=args.dry_run)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                if res["removed_count"] > 0:
                    action_word = "Would remove" if args.dry_run else "Removed"
                    for p in res["removed_paks"]:
                        print(f"[✓] {action_word} local test .pak: {p}")
                else:
                    print(f"No local test .pak found for mod '{mod_slug}' in {detect_mods_dir()}.")
            return 0

        if args.publish_local:
            mods_dir = detect_mods_dir()
            if not mods_dir:
                raise FileNotFoundError(
                    "Could not detect Baldur's Gate 3 Mods directory in AppData. "
                    "Ensure BG3 has been run or set BG3_MODS_DIR environment variable."
                )
            pak_filename = get_mod_pak_filename(mod_dir)
            out_path = Path(args.out) if args.out else mods_dir / pak_filename
        elif args.output_dir:
            out_path = Path(args.output_dir) / f"{mod_slug}.pak"
        else:
            out_path = Path(args.out) if args.out else DIST_DIR / f"{mod_slug}.pak"

        files_to_pack = collect_mod_files(mod_dir, include_projects=args.include_projects)
        if not files_to_pack:
            raise ValueError(f"No valid mod files found to pack in '{mod_dir}'.")

        pak_bytes = build_pak_archive(files_to_pack, compress=not args.uncompressed)

        # Verification pass
        verified = verify_pak_archive(pak_bytes, files_to_pack)
        if not verified:
            raise RuntimeError("Generated .pak archive failed self-verification check.")

        # Safe atomic write
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_out = out_path.with_suffix(".pak.tmp")
        try:
            temp_out.write_bytes(pak_bytes)
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            temp_out.replace(out_path)
        except PermissionError as pe:
            if temp_out.exists():
                temp_out.unlink()
            raise PermissionError(
                f"Permission denied writing to '{out_path}'. "
                "Ensure Baldur's Gate 3 and the BG3 Toolkit are closed if they are locking the file."
            ) from pe
        except Exception:
            if temp_out.exists():
                temp_out.unlink()
            raise

        res = {
            "status": "success",
            "mod": mod_slug,
            "pak_file": str(out_path),
            "file_count": len(files_to_pack),
            "pak_size_bytes": len(pak_bytes),
            "compressed": not args.uncompressed,
            "verified": verified,
            "published_local": args.publish_local,
            "included_files": [f[0] for f in files_to_pack],
        }

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            size_kb = len(pak_bytes) / 1024
            target_desc = "published to local BG3 Mods directory" if args.publish_local else "packaged"
            print(f"[✓] Successfully {target_desc}: {out_path} ({size_kb:.1f} KB, {len(files_to_pack)} files)")
            print("    Verification: [✓] LSPK v18 checksum and extraction verified cleanly.")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
