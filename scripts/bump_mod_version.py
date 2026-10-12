#!/usr/bin/env python3
"""
bump_mod_version.py
-------------------
Inspects and updates semantic version numbers and Larian Version64 integers
atomically across both `Projects/<UUID>/meta.lsx` and `Mods/<UUID>/meta.lsx`.

Features:
- Encodes and decodes 64-bit integer versions: (major << 55) | (minor << 47) | (revision << 31) | build
- Supports semantic increments: --build, --patch, --minor, --major, or explicit --set
- Atomic double-update: updates both Projects/ and Mods/ meta.lsx in place
- Clean regex-based replacement preserving exact XML formatting and indentation
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MY_MODS_DIR = WORKSPACE_ROOT / "my_mods"


def calculate_version64(major: int = 1, minor: int = 0, revision: int = 0, build: int = 0) -> int:
    """Encode major.minor.revision.build into Larian Version64 integer."""
    return (major << 55) | (minor << 47) | (revision << 31) | (build & 0x7FFFFFFF)


def decode_version64(v: int) -> tuple[int, int, int, int]:
    """Decode Larian Version64 integer into (major, minor, revision, build)."""
    major = (v >> 55) & 0x1FF
    minor = (v >> 47) & 0xFF
    revision = (v >> 31) & 0xFFFF
    build = v & 0x7FFFFFFF
    return major, minor, revision, build


def format_version_tuple(tup: tuple[int, int, int, int]) -> str:
    return f"{tup[0]}.{tup[1]}.{tup[2]}.{tup[3]}"


def parse_version_str(ver_str: str) -> tuple[int, int, int, int]:
    parts = ver_str.strip().split(".")
    if len(parts) == 1:
        return int(parts[0]), 0, 0, 0
    elif len(parts) == 2:
        return int(parts[0]), int(parts[1]), 0, 0
    elif len(parts) == 3:
        return int(parts[0]), int(parts[1]), int(parts[2]), 0
    elif len(parts) == 4:
        return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    else:
        raise ValueError(f"Invalid version string format: '{ver_str}' (expected major.minor.revision.build)")


def find_mod_directories(mod_query: str = "") -> list[Path]:
    """Find mod directories in my_mods matching query or return all."""
    if not MY_MODS_DIR.exists():
        return []

    candidates = [d for d in MY_MODS_DIR.iterdir() if d.is_dir()]
    if not mod_query:
        return sorted(candidates)

    query_norm = mod_query.strip().lower().replace("-", "").replace("_", "")
    matches = []
    for d in candidates:
        name_norm = d.name.lower().replace("-", "").replace("_", "")
        if query_norm in name_norm:
            matches.append(d)
    return sorted(matches)


def get_meta_files(mod_dir: Path) -> list[Path]:
    """Find meta.lsx files in Projects/ and Mods/ subdirectories."""
    files = []
    for sub in ["Projects", "Mods"]:
        sub_dir = mod_dir / sub
        if sub_dir.exists():
            for p in sub_dir.glob("*/meta.lsx"):
                files.append(p)
    return files


def read_mod_version(meta_path: Path) -> tuple[int, int, int, int, int]:
    """Extract Version64 integer and decoded tuple from a meta.lsx file."""
    content = meta_path.read_text(encoding="utf-8")
    
    # Locate ModuleInfo node first to avoid matching dependencies or PublishVersion
    mod_info_match = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
    if mod_info_match:
        target_text = mod_info_match.group(1)
    else:
        target_text = content

    ver_match = re.search(r'<attribute\s+id="Version64"\s+type="int64"\s+value="(\d+)"\s*/>', target_text)
    if not ver_match:
        raise ValueError(f"Could not find Version64 attribute under ModuleInfo in {meta_path}")

    raw_val = int(ver_match.group(1))
    major, minor, rev, bld = decode_version64(raw_val)
    return major, minor, rev, bld, raw_val


def update_meta_version(meta_path: Path, new_v64: int, dry_run: bool = False) -> bool:
    """Updates Version64 under ModuleInfo in meta.lsx while preserving formatting."""
    content = meta_path.read_text(encoding="utf-8")

    def replacer(match):
        node_content = match.group(0)
        updated_node = re.sub(
            r'(<attribute\s+id="Version64"\s+type="int64"\s+value=")\d+("\s*/>)',
            rf"\g<1>{new_v64}\g<2>",
            node_content,
            count=1,
        )
        return updated_node

    new_content, count = re.subn(
        r'<node\s+id="ModuleInfo">.*?</node>',
        replacer,
        content,
        count=1,
        flags=re.DOTALL,
    )

    if count == 0:
        return False

    if not dry_run:
        meta_path.write_text(new_content, encoding="utf-8")
    return True


def bump_version(
    mod_name: str,
    action: str = "show",
    set_value: str = "",
    dry_run: bool = False,
    as_json: bool = False,
) -> dict:
    matched = find_mod_directories(mod_name)
    if not matched:
        raise ValueError(f"No mod found in my_mods/ matching query '{mod_name}'.")

    target_mod = matched[0]
    meta_files = get_meta_files(target_mod)
    if not meta_files:
        raise ValueError(f"No meta.lsx files found in {target_mod} under Projects/ or Mods/.")

    # Read current from first file
    major, minor, rev, bld, raw_val = read_mod_version(meta_files[0])
    old_version_str = format_version_tuple((major, minor, rev, bld))

    new_major, new_minor, new_rev, new_bld = major, minor, rev, bld

    if action == "build":
        new_bld += 1
    elif action == "patch":
        new_rev += 1
        new_bld = 0
    elif action == "minor":
        new_minor += 1
        new_rev = 0
        new_bld = 0
    elif action == "major":
        new_major += 1
        new_minor = 0
        new_rev = 0
        new_bld = 0
    elif action == "set":
        new_major, new_minor, new_rev, new_bld = parse_version_str(set_value)

    new_v64 = calculate_version64(new_major, new_minor, new_rev, new_bld)
    new_version_str = format_version_tuple((new_major, new_minor, new_rev, new_bld))

    updated_files = []
    if action != "show":
        for mf in meta_files:
            if update_meta_version(mf, new_v64, dry_run=dry_run):
                updated_files.append(str(mf.relative_to(WORKSPACE_ROOT)))

    result = {
        "mod_name": target_mod.name,
        "mod_dir": str(target_mod.relative_to(WORKSPACE_ROOT)),
        "action": action,
        "previous_version": old_version_str,
        "previous_version64": raw_val,
        "new_version": new_version_str,
        "new_version64": new_v64,
        "updated_files": updated_files,
        "dry_run": dry_run,
    }

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        if action == "show":
            print(f"Mod '{target_mod.name}' version: {old_version_str} (Version64: {raw_val})")
            for mf in meta_files:
                print(f"  └ {mf.relative_to(WORKSPACE_ROOT)}")
        else:
            action_desc = f"[DRY-RUN] Would update" if dry_run else "Successfully updated"
            print(f"{action_desc} '{target_mod.name}': {old_version_str} -> {new_version_str} (Version64: {new_v64})")
            for f in updated_files:
                print(f"  ✓ Updated {f}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate and bump semantic versions and Larian Version64 integers in BG3 mods."
    )
    parser.add_argument("--mod", required=True, help="Mod name or folder in my_mods/ (e.g. arcane-progression)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--show", action="store_true", help="Display current version without modifying")
    group.add_argument("--build", "-b", action="store_true", help="Increment build number (+1)")
    group.add_argument("--patch", "-p", action="store_true", help="Increment patch/revision (+1) and reset build")
    group.add_argument("--minor", "-m", action="store_true", help="Increment minor version (+1) and reset patch/build")
    group.add_argument("--major", action="store_true", help="Increment major version (+1) and reset minor/patch/build")
    group.add_argument("--set", type=str, help="Explicitly set version (e.g. 1.2.0.0)")

    parser.add_argument("--dry-run", action="store_true", help="Preview version changes without writing to disk")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    action = "show"
    set_val = ""
    if args.build:
        action = "build"
    elif args.patch:
        action = "patch"
    elif args.minor:
        action = "minor"
    elif args.major:
        action = "major"
    elif args.set:
        action = "set"
        set_val = args.set

    try:
        bump_version(
            mod_name=args.mod,
            action=action,
            set_value=set_val,
            dry_run=args.dry_run,
            as_json=args.json,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
