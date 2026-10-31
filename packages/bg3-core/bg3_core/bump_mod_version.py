#!/usr/bin/env python3
"""
bump_mod_version.py
-------------------
Inspects and updates semantic version numbers and Larian Version64 integers
atomically across `Mods/<UUID>/meta.lsx` (and legacy `Projects/<UUID>/meta.lsx`),
and keeps `my_mods/<slug>/README.md` in sync so documentation and metadata never drift.

Features:
- Encodes and decodes 64-bit integer versions: (major << 55) | (minor << 47) | (revision << 31) | build
- Supports semantic increments: --build, --patch, --minor, --major, or explicit --set
- Atomic update across meta.lsx and README.md
- Clean regex-based replacement preserving exact XML and Markdown formatting
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

from bg3_core.env_paths import MY_MODS_DIR, REPO_ROOT, resolve_mod_dir
from bg3_core.larian_parsers import (
    calculate_version64,
    decode_version64,
    format_version_tuple,
    parse_version_str,
)

WORKSPACE_ROOT = REPO_ROOT


def find_mod_directories(mod_query: str = "") -> List[Path]:
    """Find mod directories in my_mods matching query or return all."""
    if not mod_query:
        if not MY_MODS_DIR.exists():
            return []
        return sorted([d for d in MY_MODS_DIR.iterdir() if d.is_dir()])

    try:
        target = resolve_mod_dir(mod_query)
        if target and target.is_dir():
            return [target]
    except Exception:
        pass

    if not MY_MODS_DIR.exists():
        return []

    query_norm = mod_query.strip().lower().replace("-", "").replace("_", "")
    matches = []
    for d in MY_MODS_DIR.iterdir():
        if d.is_dir():
            name_norm = d.name.lower().replace("-", "").replace("_", "")
            if query_norm in name_norm:
                matches.append(d)
    return sorted(matches)


def get_meta_files(mod_dir: Path) -> List[Path]:
    """Find meta.lsx files in Mods/ (and legacy Projects/ with ModuleInfo) to update Version64."""
    files = []
    # Always include runtime module descriptors in Mods/
    mods_dir = mod_dir / "Mods"
    if mods_dir.exists():
        for p in mods_dir.glob("*/meta.lsx"):
            files.append(p)

    # Only include Projects/ if it contains ModuleInfo (legacy scaffold)
    proj_dir = mod_dir / "Projects"
    if proj_dir.exists():
        for p in proj_dir.glob("*/meta.lsx"):
            try:
                if '<node id="ModuleInfo">' in p.read_text(encoding="utf-8"):
                    files.append(p)
            except Exception:
                pass
    return files


def read_mod_version(meta_path: Path) -> Tuple[int, int, int, int, int]:
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

    def replacer(match: re.Match[str]) -> str:
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


def update_readme_version(mod_dir: Path, new_version_str: str, dry_run: bool = False) -> bool:
    """Update version line in README.md if present to avoid documentation drift."""
    readme_path = mod_dir / "README.md"
    if not readme_path.is_file():
        return False

    content = readme_path.read_text(encoding="utf-8")
    pattern = r'(?i)(-\s*\*\*Version:\*\*\s*[`"]?|\*{0,2}Version:?\*{0,2}\s*[:=]?\s*[`"]?)(\d+(?:\.\d+)*)([`"]?)'
    new_content, count = re.subn(
        pattern,
        rf"\g<1>{new_version_str}\g<3>",
        content,
        count=1,
    )
    if count == 0 or new_content == content:
        return False

    if not dry_run:
        readme_path.write_text(new_content, encoding="utf-8")
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

    def _rel_path(p: Path, base: Path) -> str:
        try:
            return str(p.relative_to(base))
        except ValueError:
            return str(p)

    updated_files = []
    if action != "show":
        for mf in meta_files:
            if update_meta_version(mf, new_v64, dry_run=dry_run):
                updated_files.append(_rel_path(mf, WORKSPACE_ROOT))
        if update_readme_version(target_mod, new_version_str, dry_run=dry_run):
            updated_files.append(_rel_path(target_mod / "README.md", WORKSPACE_ROOT))

    result = {
        "mod_name": target_mod.name,
        "mod_dir": _rel_path(target_mod, WORKSPACE_ROOT),
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
                print(f"  └ {_rel_path(mf, WORKSPACE_ROOT)}")
        else:
            action_desc = "[DRY-RUN] Would update" if dry_run else "Successfully updated"
            print(f"{action_desc} '{target_mod.name}': {old_version_str} -> {new_version_str} (Version64: {new_v64})")
            for f in updated_files:
                print(f"  ✓ Updated {f}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-generate and bump semantic versions and Larian Version64 integers in BG3 mods."
    )
    parser.add_argument("--mod", required=True, help="Mod name or folder in my_mods/ (e.g. paladins-call)")
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
