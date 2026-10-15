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
import sys
import urllib.error
import urllib.parse
import urllib.request

# Ensure scripts directory is in python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

if __package__:
    from .library_catalog import parse_library_rows
    from .modio_extract import (
        get_api_key,
        process_mod,
        BG3_GAME_ID,
        MODIO_API_HOST,
    )
    from .modio_update import (
        get_tracked_mods,
        check_and_apply_update,
    )
else:
    from library_catalog import parse_library_rows
    from modio_extract import (
        get_api_key,
        process_mod,
        BG3_GAME_ID,
        MODIO_API_HOST,
    )
    from modio_update import (
        get_tracked_mods,
        check_and_apply_update,
    )


def get_oauth_token(cli_token=None):
    """Resolve mod.io Personal Access Token (PAT) or OAuth token from CLI, env, or .env file."""
    if cli_token:
        return cli_token.strip()

    env_token = os.environ.get("MODIO_PAT") or os.environ.get("MODIO_OAUTH_TOKEN")
    if env_token:
        return env_token.strip()

    env_file = os.path.join(WORKSPACE_ROOT, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MODIO_PAT=") or line.startswith("MODIO_OAUTH_TOKEN="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val

    # Check home .config/modio/env fallback
    home_env = os.path.expanduser("~/.config/modio/env")
    if os.path.exists(home_env):
        with open(home_env, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MODIO_PAT=") or line.startswith("MODIO_OAUTH_TOKEN="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val

    return None


def fetch_subscribed_mods(oauth_token, game_id=BG3_GAME_ID):
    """
    Fetch all mods the authenticated user is subscribed to for the given game.
    Handles pagination automatically.
    """
    base_url = "https://api.mod.io/v1/me/subscribed"
    limit = 100
    offset = 0
    all_mods = []
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Accept": "application/json",
        "User-Agent": "BG3ModDocPipeline/1.0",
    }

    while True:
        params = {
            "game_id": game_id,
            "_limit": limit,
            "_offset": offset,
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"mod.io API HTTP {e.code} error: {e.reason} - {err_body}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to mod.io: {e}")

        items = data.get("data", [])
        all_mods.extend(items)
        total = data.get("result_total", 0)

        if offset + len(items) >= total or not items:
            break
        offset += len(items)

    return all_mods


def get_tracked_mods_from_library(library_path):
    """
    Parses mods/library.md directly to identify mods currently in the catalog.
    Does not scan the filesystem directory to avoid detecting pruned/orphaned directories.
    """
    tracked = {}
    if os.path.exists(library_path):
        with open(library_path, "r", encoding="utf-8") as f:
            rows = parse_library_rows(f.read())
        for row in rows:
            slug = row["slug"]
            feature_match = re.match(r"(\d+)\s+implemented\b", row["features_documented"], re.IGNORECASE)
            if feature_match is None:
                raise ValueError(f"Invalid Features Documented value for library entry '{slug}'.")
            tracked[slug.lower()] = {
                "mod_id": row["mod_id"],
                "name": row["name"],
                "slug": slug,
                "category": row["category"],
                "description": row["description"],
                "features_count": int(feature_match.group(1)),
                "spec_path": os.path.join(WORKSPACE_ROOT, "mods", slug, "README.md"),
            }
    return tracked


def prune_mod_from_library(library_path, slug):
    """Remove a mod's row from mods/library.md by slug."""
    if not os.path.exists(library_path):
        return False

    with open(library_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = rf"^\|[^|\n]*\|[^|\n]*\|\s*`?{re.escape(slug)}`?\s*\|[^\n]*\n?"
    new_content, count = re.subn(pattern, "", content, flags=re.IGNORECASE | re.MULTILINE)
    if count == 0:
        legacy_pattern = rf"^\|[^\n]*\({re.escape(slug)}/README\.md\)[^\n]*\n?"
        new_content, count = re.subn(
            legacy_pattern, "", content, flags=re.IGNORECASE | re.MULTILINE
        )

    if count > 0:
        with open(library_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False


def sync_library(
    oauth_token,
    api_key=None,
    dry_run=False,
    prune=False,
    limit=None,
    skip_updates=False,
    filter_query=None,
):
    """
    Core sync controller:
    1. Fetches remote subscriptions
    2. Categorizes against mods/library.md
    3. Handles pruning of unsubscribed mods (if prune=True)
    4. Updates existing mods with newer releases (unless skip_updates=True)
    5. Extracts and documents newly subscribed mods (up to limit)
    """
    library_path = os.path.join(WORKSPACE_ROOT, "mods", "library.md")
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

    results = {
        "total_subscribed": len(subscribed_mods),
        "total_tracked": len(tracked_mods),
        "new_count": len(new_mods),
        "existing_count": len(existing_mods),
        "unsubscribed_count": len(unsubscribed_tracked),
        "actions": {
            "pruned": [],
            "updated": [],
            "up_to_date": [],
            "extracted": [],
            "skipped_new": [],
            "failed": [],
        },
    }

    # 3. Handle Pruning
    if unsubscribed_tracked:
        for slug, info in unsubscribed_tracked:
            name = info.get("name", slug)
            if prune:
                if dry_run:
                    results["actions"]["pruned"].append({
                        "slug": slug,
                        "name": name,
                        "status": "dry_run_prune",
                        "message": f"[DRY-RUN] Would prune '{name}' ({slug}) from library.md",
                    })
                else:
                    success = prune_mod_from_library(library_path, slug)
                    if success:
                        results["actions"]["pruned"].append({
                            "slug": slug,
                            "name": name,
                            "status": "pruned",
                            "message": f"Pruned '{name}' ({slug}) from library.md",
                        })
                    else:
                        results["actions"]["pruned"].append({
                            "slug": slug,
                            "name": name,
                            "status": "not_found",
                            "message": f"Row for '{name}' ({slug}) was not found in library.md",
                        })
            else:
                results["actions"]["pruned"].append({
                    "slug": slug,
                    "name": name,
                    "status": "retained",
                    "message": f"Retained unsubscribed mod '{name}' ({slug}) (use --prune to remove)",
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

    # 5. Extract and Document New Subscribed Mods
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
            proc_res = process_mod(slug, write_spec=True, update_library=True)
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
        label = "Pruned Unsubscribed Mods" if prune else "Unsubscribed Mods Retained in Library"
        print(f"\n[{label} ({len(actions['pruned'])})]")
        for item in actions["pruned"]:
            print(f"  - {item.get('name')}: {item.get('message')}")

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
        help="Remove documented mods from mods/library.md that are no longer subscribed",
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
            "Please provide --token <TOKEN>, export MODIO_PAT, or set MODIO_PAT in .env.",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = get_api_key()
    if not api_key:
        print(
            "Error: MODIO_API_KEY is not set.\n"
            "Please export MODIO_API_KEY or set MODIO_API_KEY in .env.",
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
