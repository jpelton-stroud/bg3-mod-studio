#!/usr/bin/env python3
"""
scripts/modio_sync.py

Synchronizes Baldur's Gate 3 mods documented in mods/library.md with the
authenticated user's mod.io subscribed mods using an OAuth 2.0 access token.

Features:
- Queries mod.io /v1/me/subscribed?game_id=6715 with pagination
- Detects newly subscribed mods and executes full extraction + documentation (process_mod)
- Checks existing documented mods for remote updates (MD5 hash / version comparison)
- Supports optional pruning (--prune) for documented mods no longer subscribed
- Supports dry-run inspection (--dry-run) and batch limiting (--limit)
"""

import argparse
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bg3_core.env_paths import MODS_DIR, REPO_ROOT, get_subscribed_mods_dir, normalize_mod_key
from bg3_core.library_catalog import (
    find_mod_folder,
    find_orphaned_folders,
    get_tracked_mods,
    parse_library_rows,
    prune_mod_from_library,
    safe_batch_delete_folders,
)
from bg3_core.modio_client import (
    BG3_GAME_ID,
    MODIO_API_HOST,
    USER_AGENT,
    ModioClient,
    ModioError,
    get_api_key,
    get_oauth_token,
)
from bg3_core.modio_extract import process_mod
from bg3_core.modio_update import check_and_apply_update
from bg3_core.update_library_catalog import write_library_catalog

WORKSPACE_ROOT = str(REPO_ROOT)
get_tracked_mods_from_library = get_tracked_mods





def fetch_subscribed_mods(oauth_token, game_id=BG3_GAME_ID, client=None):
    """
    Fetch all mods the authenticated user is subscribed to for the given game.
    Handles pagination automatically.
    """
    if client is None:
        client = ModioClient(oauth_token)
    return client.get_paged("/me/subscribed", params={"game_id": game_id})





def sync_library(
    oauth_token,
    api_key=None,
    dry_run=False,
    prune=False,
    limit=None,
    skip_updates=False,
    filter_query=None,
    library_path=None,
    mods_dir=None,
):
    """
    Core sync controller:
    1. Fetches remote subscriptions
    2. Categorizes against mods/library.md and detects orphaned folders
    3. Prunes unsubscribed mods from library.md and flags folders for deletion
    4. Updates existing mods with newer releases (unless skip_updates=True)
    5. Extracts and documents newly subscribed mods (up to limit)
    6. Regenerates catalog once if extractions occurred
    7. Executes batched deletion of all flagged mod folders (if prune=True)
    """
    if mods_dir is None:
        mods_dir = get_subscribed_mods_dir()
    else:
        mods_dir = Path(mods_dir)
    if library_path is None:
        library_path = str(mods_dir / "library.md")

    tracked_mods = get_tracked_mods_from_library(library_path)

    # 1. Fetch subscribed mods
    subscribed_mods = fetch_subscribed_mods(oauth_token, BG3_GAME_ID)
    subscribed_slug_map = {}
    for m in subscribed_mods:
        slug = m.get("name_id", "").lower()
        name = m.get("name", "").lower()
        if filter_query:
            q = filter_query.lower()
            if q not in slug and q not in name:
                continue
        if slug:
            subscribed_slug_map[slug] = m

    # 2. Categorize mods
    new_mods = []
    existing_mods = []
    for slug, m in subscribed_slug_map.items():
        if slug in tracked_mods:
            existing_mods.append((slug, m, tracked_mods[slug]))
        else:
            new_mods.append((slug, m))

    unsubscribed_tracked = []
    if not filter_query:
        for slug, info in tracked_mods.items():
            if slug not in subscribed_slug_map:
                unsubscribed_tracked.append((slug, info))

    active_slugs = set(subscribed_slug_map.keys()) | set(tracked_mods.keys())
    orphaned_folders = find_orphaned_folders(mods_dir, active_slugs) if not filter_query else []

    results = {
        "total_subscribed": len(subscribed_mods),
        "total_tracked": len(tracked_mods),
        "new_count": len(new_mods),
        "existing_count": len(existing_mods),
        "unsubscribed_count": len(unsubscribed_tracked),
        "orphaned_count": len(orphaned_folders),
        "actions": {
            "pruned": [],
            "deleted_folders": [],
            "updated": [],
            "up_to_date": [],
            "extracted": [],
            "skipped_new": [],
            "failed": [],
        },
    }

    folders_to_delete = []

    # 3. Handle Pruning & Folder Flagging
    if unsubscribed_tracked:
        for slug, info in unsubscribed_tracked:
            name = info.get("name", slug)
            mod_folder = find_mod_folder(slug, mods_dir)
            if mod_folder:
                folders_to_delete.append(mod_folder)

            if prune:
                if dry_run:
                    msg = f"[DRY-RUN] Would prune '{name}' ({slug}) from library.md"
                    if mod_folder:
                        msg += f" and flag 'mods/{mod_folder.name}' for deletion"
                    results["actions"]["pruned"].append({
                        "slug": slug,
                        "name": name,
                        "status": "dry_run_prune",
                        "folder": str(mod_folder) if mod_folder else None,
                        "message": msg,
                    })
                else:
                    success = prune_mod_from_library(library_path, slug)
                    if success:
                        msg = f"Pruned '{name}' ({slug}) from library.md"
                        if mod_folder:
                            msg += f" and flagged 'mods/{mod_folder.name}' for deletion"
                        results["actions"]["pruned"].append({
                            "slug": slug,
                            "name": name,
                            "status": "pruned",
                            "folder": str(mod_folder) if mod_folder else None,
                            "message": msg,
                        })
                    else:
                        results["actions"]["pruned"].append({
                            "slug": slug,
                            "name": name,
                            "status": "not_found",
                            "folder": str(mod_folder) if mod_folder else None,
                            "message": f"Row for '{name}' ({slug}) was not found in library.md",
                        })
            else:
                msg = f"Retained unsubscribed mod '{name}' ({slug})"
                if mod_folder:
                    msg += f" [folder: mods/{mod_folder.name}]"
                msg += " (use --prune to remove)"
                results["actions"]["pruned"].append({
                    "slug": slug,
                    "name": name,
                    "status": "retained",
                    "folder": str(mod_folder) if mod_folder else None,
                    "message": msg,
                })

    if orphaned_folders:
        for orphan in orphaned_folders:
            folders_to_delete.append(orphan)
            if prune:
                if dry_run:
                    results["actions"]["pruned"].append({
                        "slug": orphan.name,
                        "name": orphan.name,
                        "status": "dry_run_orphan",
                        "folder": str(orphan),
                        "message": f"[DRY-RUN] Would flag orphaned mod data folder 'mods/{orphan.name}' for deletion",
                    })
                else:
                    results["actions"]["pruned"].append({
                        "slug": orphan.name,
                        "name": orphan.name,
                        "status": "orphan_flagged",
                        "folder": str(orphan),
                        "message": f"Flagged orphaned mod data folder 'mods/{orphan.name}' for deletion",
                    })
            else:
                results["actions"]["pruned"].append({
                    "slug": orphan.name,
                    "name": orphan.name,
                    "status": "orphan_retained",
                    "folder": str(orphan),
                    "message": f"Retained orphaned mod data folder 'mods/{orphan.name}' (use --prune to remove)",
                })

    # 4. Check & Update Existing Subscribed Mods
    if not skip_updates:
        for slug, mod_meta, tracked_info in existing_mods:
            name = mod_meta.get("name", slug)
            try:
                update_res = check_and_apply_update(
                    slug,
                    api_key=api_key,
                    check_only=dry_run,
                    force=False,
                )
                status = update_res.get("status")
                if status == "update_available":
                    results["actions"]["updated"].append(update_res)
                elif status == "updated":
                    results["actions"]["updated"].append(update_res)
                elif status == "up_to_date":
                    results["actions"]["up_to_date"].append(update_res)
                else:
                    results["actions"]["failed"].append(update_res)
            except Exception as e:
                results["actions"]["failed"].append({
                    "slug": slug,
                    "name": name,
                    "status": "failed",
                    "message": f"Error updating {name}: {e}",
                })

    # 5. Extract and Document New Subscribed Mods (Sequential)
    new_to_process = new_mods
    if limit is not None and limit >= 0:
        new_to_process = new_mods[:limit]
        skipped = new_mods[limit:]
        for slug, m in skipped:
            results["actions"]["skipped_new"].append({
                "slug": slug,
                "name": m.get("name", slug),
                "status": "skipped_limit",
                "message": f"Skipped '{m.get('name', slug)}' due to --limit {limit}",
            })

    for idx, (slug, mod_meta) in enumerate(new_to_process, 1):
        name = mod_meta.get("name", slug)
        if dry_run:
            results["actions"]["extracted"].append({
                "slug": slug,
                "name": name,
                "status": "dry_run_extract",
                "message": f"[DRY-RUN] Would extract and document '{name}' ({slug})",
            })
            continue

        try:
            print(f"--> [{idx}/{len(new_to_process)}] Extracting and documenting '{name}' ({slug})...", flush=True)
            proc_res = process_mod(slug, write_spec=True, update_library=False)
            results["actions"]["extracted"].append({
                "slug": slug,
                "name": name,
                "status": "extracted",
                "features_count": proc_res.get("features_count", 0),
                "category": proc_res.get("category", "General"),
                "message": f"Extracted '{name}' ({slug}): {proc_res.get('features_count', 0)} features documented.",
            })
        except Exception as e:
            results["actions"]["failed"].append({
                "slug": slug,
                "name": name,
                "status": "failed",
                "message": f"Failed to extract '{name}' ({slug}): {e}",
            })

    # 6. Deferred Single-Pass Library Catalog Regeneration
    extracted_any = any(item.get("status") == "extracted" for item in results["actions"]["extracted"])
    if extracted_any and not dry_run:
        try:
            write_library_catalog(mods_dir, Path(library_path))
        except Exception as e:
            print(f"Warning: Failed to regenerate library catalog after extractions: {e}", file=sys.stderr)

    # 7. Batched Folder Deletion
    if folders_to_delete and prune:
        del_results = safe_batch_delete_folders(folders_to_delete, mods_dir=mods_dir, dry_run=dry_run)
        results["actions"]["deleted_folders"] = del_results
    elif folders_to_delete and not prune:
        results["actions"]["deleted_folders"] = [
            {
                "path": str(p),
                "name": p.name,
                "status": "retained",
                "message": f"Retained candidate mod folder 'mods/{p.name}' (use --prune to remove)",
            }
            for p in folders_to_delete
        ]

    return results


def print_summary(results, dry_run=False, prune=False):
    """Pretty prints the sync results to stdout."""
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"\n========================================================")
    print(f"{prefix}BG3 Mod Library Sync Summary")
    print(f"========================================================")
    print(f"Total Subscribed on mod.io : {results['total_subscribed']}")
    print(f"Currently in library.md    : {results['total_tracked']}")
    print(f"  - Active & Documented    : {results['existing_count']}")
    print(f"  - Newly Subscribed       : {results['new_count']}")
    print(f"  - Tracked but Unsubscribed: {results['unsubscribed_count']}")
    if results.get("orphaned_count", 0) > 0:
        print(f"  - Orphaned Mod Folders   : {results['orphaned_count']}")
    print(f"--------------------------------------------------------")

    actions = results["actions"]

    if actions["extracted"]:
        print(f"\n[Newly Subscribed Mods ({len(actions['extracted'])})]")
        for item in actions["extracted"]:
            feat_info = f" ({item.get('features_count')} features)" if "features_count" in item else ""
            print(f"  + {item.get('name')}: {item.get('message')}{feat_info}")

    if actions["skipped_new"]:
        print(f"\n[Skipped New Subscriptions (Limit Reached: {len(actions['skipped_new'])})]")
        for item in actions["skipped_new"]:
            print(f"  ~ {item.get('name')}: {item.get('message')}")

    if actions["updated"]:
        print(f"\n[Updated Existing Mods ({len(actions['updated'])})]")
        for item in actions["updated"]:
            print(f"  * {item.get('mod_name', item.get('slug'))}: {item.get('message')}")

    if actions["up_to_date"]:
        print(f"\n[Up-to-Date Existing Mods ({len(actions['up_to_date'])})]")
        for item in actions["up_to_date"]:
            print(f"  ✓ {item.get('mod_name', item.get('slug'))}: {item.get('message')}")

    if actions["pruned"]:
        label = "Pruned Unsubscribed & Orphaned Mods" if prune else "Unsubscribed & Orphaned Mods Retained"
        print(f"\n[{label} ({len(actions['pruned'])})]")
        for item in actions["pruned"]:
            print(f"  - {item.get('name')}: {item.get('message')}")

    if actions.get("deleted_folders") and prune:
        label = "Deleted Mod Data Folders" if not dry_run else "Mod Data Folders Flagged for Deletion"
        print(f"\n[{label} ({len(actions['deleted_folders'])})]")
        for item in actions["deleted_folders"]:
            prefix_char = "x" if not dry_run else "~"
            print(f"  {prefix_char} {item.get('name')}: {item.get('message')}")

    if actions["failed"]:
        print(f"\n[Errors / Failures ({len(actions['failed'])})]")
        for item in actions["failed"]:
            print(f"  ! {item.get('name', item.get('slug'))}: {item.get('message')}")

    print(f"========================================================\n")


def main():
    parser = argparse.ArgumentParser(
        description="Sync BG3 mods/library.md with your mod.io subscribed mods."
    )
    parser.add_argument(
        "--token",
        "-t",
        help="mod.io OAuth 2.0 Personal Access Token (defaults to MODIO_OAUTH_TOKEN env or .env)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Inspect and report sync actions without downloading, unpacking, or writing files",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove unsubscribed mods from mods/library.md and batch-delete applicable mod data folders and orphaned directories in mods/",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Maximum number of new subscribed mods to extract and document",
    )
    parser.add_argument(
        "--filter",
        "-f",
        help="Filter subscribed mods by name or slug substring",
    )
    parser.add_argument(
        "--skip-updates",
        action="store_true",
        help="Skip checking/updating existing documented mods",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as machine-readable JSON",
    )

    args = parser.parse_args()

    oauth_token = get_oauth_token(args.token)
    if not oauth_token:
        print(
            "Error: No mod.io Personal Access Token (PAT) found.\n"
            "Please provide --token <TOKEN>, export MODIO_PAT, or set MODIO_PAT in ~/.config/bg3/env.",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = get_api_key()
    if not api_key:
        print(
            "Error: MODIO_API_KEY is not set.\n"
            "Please export MODIO_API_KEY or set MODIO_API_KEY in ~/.config/bg3/env.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        results = sync_library(
            oauth_token=oauth_token,
            api_key=api_key,
            dry_run=args.dry_run,
            prune=args.prune,
            limit=args.limit,
            skip_updates=args.skip_updates,
            filter_query=args.filter,
        )
    except Exception as e:
        print(f"Fatal Sync Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_summary(results, dry_run=args.dry_run, prune=args.prune)


if __name__ == "__main__":
    main()
