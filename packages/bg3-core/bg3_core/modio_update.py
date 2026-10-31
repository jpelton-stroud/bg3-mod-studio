#!/usr/bin/env python3
"""
packages/bg3-core/bg3_core/modio_update.py

Inspects Baldur's Gate 3 mods on mod.io for updates, compares local unpacked
assets (meta.lsx MD5 hash and version) against mod.io release metadata,
applies updates when new releases are available, computes feature diffs,
and updates specs and library catalogs.
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import REPO_ROOT, get_subscribed_mods_dir
from bg3_core.library_catalog import get_tracked_mods as _get_tracked_mods
from bg3_core.modio_client import get_api_key, query_modio
from bg3_core.modio_extract import process_mod

WORKSPACE_ROOT = str(REPO_ROOT)


def get_tracked_mods(library_path: Optional[str | Path] = None) -> dict[str, dict[str, str]]:
    """
    Parses library.md and existing mod directories to identify tracked mods.
    Returns a dict mapping lowercase slug to mod details.
    """
    return _get_tracked_mods(
        library_path=library_path,
        include_filesystem=True,
    )


def get_local_mod_state(slug: str, mods_dir: Optional[str | Path] = None) -> dict[str, Any]:
    """
    Inspects local files for a mod to extract MD5 hash, version, and features.
    """
    if mods_dir is None:
        mods_dir = str(get_subscribed_mods_dir())

    mod_dir = os.path.join(mods_dir, slug)
    state: dict[str, Any] = {
        "exists": os.path.isdir(mod_dir),
        "slug": slug,
        "md5": None,
        "version": None,
        "version64": None,
        "mod_id": None,
        "features": {},
        "raw_spec": None,
    }

    if not state["exists"]:
        return state

    meta_lsx_path = os.path.join(mod_dir, "data", "meta.lsx")
    if os.path.exists(meta_lsx_path):
        try:
            tree = ET.parse(meta_lsx_path)
            root = tree.getroot()
            for node in root.findall(".//node[@id='ModuleInfo']/attribute"):
                attr_id = node.get("id")
                val = node.get("value")
                if attr_id == "MD5":
                    state["md5"] = val
                elif attr_id == "Version64":
                    state["version64"] = val
                elif attr_id == "PublishHandle":
                    state["mod_id"] = val
        except Exception:
            pass

    readme_path = os.path.join(mod_dir, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
                state["raw_spec"] = content

                v_match = re.search(r"\*\*Version\*\*:\s*([^\s\|]+)", content)
                if v_match:
                    state["version"] = v_match.group(1).strip()

                id_match = re.search(r"\*\*mod\.io ID\*\*:\s*`?(\d+)`?", content)
                if id_match:
                    state["mod_id"] = id_match.group(1).strip()

                # Parse existing feature table rows
                for row in re.findall(r"\|\s*\*\*([^*]+)\*\*<br>\*([^*]+)\*\s*\|\s*`([^`]+)`\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", content):
                    fname, ftype, fid, fstats, feffects = row
                    state["features"][fid.strip()] = {
                        "name": fname.strip(),
                        "type": ftype.strip(),
                        "base_stats": fstats.strip(),
                        "granted_effects": feffects.strip(),
                    }
        except Exception:
            pass

    return state


def extract_modfile_hash(metadata_blob: Optional[str]) -> Optional[str]:
    """Extract MD5 hash from modfile metadata_blob string: 'hash=<md5>;filesize=...'"""
    if not metadata_blob:
        return None
    match = re.search(r"hash=([a-f0-9]{32})", metadata_blob, re.IGNORECASE)
    return match.group(1).lower() if match else None


def compute_feature_diff(old_features: dict[str, Any], new_features: dict[str, Any]) -> str:
    """
    Compares previous features against new features and returns a human-readable
    summary of additions, modifications, and removals.
    """
    added = []
    removed = []
    modified = []

    old_ids = set(old_features.keys())
    new_ids = set(new_features.keys())

    for fid in new_ids - old_ids:
        f = new_features[fid]
        added.append(f"{f.get('name', fid)} ({f.get('type', 'Feature')})")

    for fid in old_ids - new_ids:
        f = old_features[fid]
        removed.append(f"{f.get('name', fid)} ({f.get('type', 'Feature')})")

    for fid in old_ids & new_ids:
        old_f = old_features[fid]
        new_f = new_features[fid]
        diffs = []
        if old_f.get("base_stats") != new_f.get("base_stats"):
            diffs.append("stats")
        if old_f.get("granted_effects") != new_f.get("granted_effects"):
            diffs.append("mechanics/effects")
        if diffs:
            modified.append(f"{new_f.get('name', fid)} ({', '.join(diffs)})")

    parts = []
    if added:
        if len(added) <= 3:
            parts.append(f"Added {len(added)} feature(s): {', '.join(added)}")
        else:
            parts.append(f"Added {len(added)} new features including {', '.join(added[:3])}...")
    if modified:
        if len(modified) <= 3:
            parts.append(f"Updated mechanics on: {', '.join(modified)}")
        else:
            parts.append(f"Updated mechanics on {len(modified)} features ({', '.join(modified[:2])}...)")
    if removed:
        parts.append(f"Removed {len(removed)} feature(s): {', '.join(removed[:2])}")

    if not parts:
        return "Internal script/asset updates; no feature definition changes detected."
    return "; ".join(parts)


def check_and_apply_update(
    query: str,
    api_key: Optional[str] = None,
    check_only: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """
    Main update controller for an individual mod query.
    1. Validates tracking in mods/library.md
    2. Queries mod.io for release metadata
    3. Compares hash and version against local state
    4. Downloads, unpacks, and updates spec if updated
    5. Returns structured status dictionary
    """
    if not api_key:
        api_key = get_api_key()
    if not api_key:
        return {
            "query": query,
            "status": "failed",
            "message": "MODIO_API_KEY environment variable is not set.",
        }

    tracked_mods = get_tracked_mods()

    # Resolve query target
    clean_q = query.strip()
    if "mod.io" in clean_q:
        target_slug = clean_q.rstrip("/").split("/")[-1].lower()
    else:
        target_slug = clean_q.lower()

    # Match slug or name in tracked mods
    matched_slug = None
    for s, info in tracked_mods.items():
        if target_slug == s or clean_q.lower() == info["name"].lower():
            matched_slug = s
            break

    # If query looks like an exact ID or slug, check by query
    local_state = None
    if matched_slug:
        local_state = get_local_mod_state(matched_slug)
    else:
        # Check if directory exists directly
        candidate_state = get_local_mod_state(target_slug)
        if candidate_state["exists"]:
            matched_slug = target_slug
            local_state = candidate_state

    # 1. Check if mod is tracked
    if not matched_slug or not local_state or not local_state["exists"]:
        return {
            "query": query,
            "slug": target_slug,
            "status": "not_tracked",
            "message": f"Mod '{query}' is not tracked in mods/library.md (use /bg3-document-mods to add)",
        }

    # 2. Fetch remote metadata from mod.io
    try:
        remote_meta = query_modio(matched_slug, api_key)
    except Exception as e:
        return {
            "query": query,
            "slug": matched_slug,
            "status": "failed",
            "message": f"Failed to query mod.io: {e}",
        }

    mod_name = remote_meta.get("name", matched_slug)
    remote_slug = remote_meta.get("name_id", matched_slug)
    modfile = remote_meta.get("modfile", {})
    if not modfile:
        return {
            "query": query,
            "slug": remote_slug,
            "mod_name": mod_name,
            "status": "failed",
            "message": "No active release modfile found on mod.io",
        }

    remote_version = modfile.get("version") or "1.0.0"
    remote_hash = extract_modfile_hash(modfile.get("metadata_blob"))
    remote_file_id = modfile.get("id")
    remote_changelog = (modfile.get("changelog") or "").strip()

    local_md5 = (local_state.get("md5") or "").lower()
    local_version = local_state.get("version")

    # 3. Determine if mod is updated
    has_update = False
    if force:
        has_update = True
    elif remote_hash and local_md5:
        if remote_hash != local_md5:
            has_update = True
    elif remote_version and local_version and remote_version != local_version:
        has_update = True

    # Determine clean version display (prefer semantic version over raw Version64 int)
    if remote_version and (not local_version or (local_version.isdigit() and len(local_version) > 10)):
        current_friendly_version = remote_version
    else:
        current_friendly_version = local_version or remote_version

    # Case A: Already up-to-date
    if not has_update:
        return {
            "query": query,
            "slug": remote_slug,
            "mod_name": mod_name,
            "status": "up_to_date",
            "version": current_friendly_version,
            "modfile_id": remote_file_id,
            "message": f"{remote_slug}: No updates found (current version: v{current_friendly_version})",
        }

    # Case B: Check-only mode with update available
    if check_only:
        return {
            "query": query,
            "slug": remote_slug,
            "mod_name": mod_name,
            "status": "update_available",
            "current_version": current_friendly_version,
            "new_version": remote_version,
            "modfile_id": remote_file_id,
            "changelog": remote_changelog or "No release changelog provided by author",
            "message": f"{remote_slug}: Update available (v{current_friendly_version} -> v{remote_version})",
        }

    # Case C: Apply update
    try:
        # Save old features for diffing
        old_features = local_state.get("features", {})

        # Execute extraction pipeline (downloads, unpacks, updates README and library)
        result = process_mod(remote_slug, write_spec=True, update_library=True)

        # Generate new features dict for diffing
        new_features = {}
        for f in result.get("features", []):
            new_features[f["identifier"]] = f

        # Determine change description (hybrid approach)
        if remote_changelog:
            change_description = remote_changelog
        else:
            change_description = compute_feature_diff(old_features, new_features)

        return {
            "query": query,
            "slug": remote_slug,
            "mod_name": mod_name,
            "status": "updated",
            "version": remote_version,
            "old_version": current_friendly_version,
            "change_description": change_description,
            "features_count": result.get("features_count", len(new_features)),
            "spec_path": f"mods/{remote_slug}/README.md",
            "message": f"{remote_slug}: Documentation updated to v{remote_version} — {change_description}",
        }
    except Exception as e:
        return {
            "query": query,
            "slug": remote_slug,
            "mod_name": mod_name,
            "status": "failed",
            "message": f"{remote_slug}: Failed to update documentation: {e}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="BG3 Mod Documentation Update Checker & Pipeline.")
    parser.add_argument("query_pos", nargs="?", help="Mod slug, name, ID, or URL (positional)")
    parser.add_argument("--query", "-q", dest="query_flag", help="Mod slug, name, ID, or URL to check/update")
    parser.add_argument("--all", action="store_true", help="Check/update all tracked mods in mods/library.md")
    parser.add_argument("--check-only", action="store_true", help="Only check for updates without downloading or modifying files")
    parser.add_argument("--force", action="store_true", help="Force re-extraction and documentation regeneration even if up-to-date")
    parser.add_argument("--list-tracked", action="store_true", help="List all tracked mods from mods/library.md")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    color = ConsoleColor(stream=sys.stdout)
    err_color = ConsoleColor(stream=sys.stderr)

    if args.list_tracked:
        tracked = get_tracked_mods()
        if args.json:
            print(json.dumps(list(tracked.values()), indent=2))
        else:
            print(f"{color.bold('Tracked BG3 Mods')} ({len(tracked)}):")
            for t in tracked.values():
                print(f" - [{t['category']}] {t['name']} ({t['slug']})")
        return ExitCode.OK

    query_val = args.query_flag or args.query_pos
    targets = []
    if query_val:
        targets.append(query_val)
    elif args.all or not query_val:
        # Default behavior: all tracked mods
        tracked = get_tracked_mods()
        targets = [t["slug"] for t in tracked.values()]

    if not targets:
        print(f"{err_color.red('[ERROR]')} No mods found to update.", file=sys.stderr)
        sys.exit(ExitCode.USAGE)

    api_key = get_api_key()
    results = []

    for tgt in targets:
        res = check_and_apply_update(
            tgt,
            api_key=api_key,
            check_only=args.check_only,
            force=args.force,
        )
        results.append(res)
        if not args.json:
            print(res["message"])

    if args.json:
        if len(results) == 1 and query_val:
            print(json.dumps(results[0], indent=2))
        else:
            print(json.dumps(results, indent=2))

    has_failures = any(r.get("status") == "failed" for r in results)
    return ExitCode.GENERAL if has_failures else ExitCode.OK


if __name__ == "__main__":
    sys.exit(main())
