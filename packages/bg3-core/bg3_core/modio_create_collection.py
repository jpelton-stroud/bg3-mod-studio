#!/usr/bin/env python3
"""Create or update a public Baldur's Gate 3 collection on mod.io."""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, TextIO, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import REPO_ROOT, get_library_catalog_path
from bg3_core.library_catalog import parse_library_rows
from bg3_core.modio_client import (
    BG3_GAME_ID,
    ModioClient,
    ModioError,
    get_oauth_token,
)

WORKSPACE_ROOT = REPO_ROOT
LIBRARY_PATH = get_library_catalog_path()
PAGE_SIZE = 100


@dataclass(frozen=True)
class ModEntry:
    name: str
    slug: str
    mod_id: int


def parse_catalog(library_path: Path) -> Tuple[List[ModEntry], List[str], int]:
    try:
        lines = library_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ModioError(f"Could not read the mod library at {library_path}: {error}") from None

    catalog: Dict[str, Dict[str, str]] = {}
    for row in parse_library_rows("\n".join(lines)):
        slug = row["slug"]
        if not slug:
            continue
        if slug in catalog:
            raise ModioError(f"The library lists the slug '{slug}' more than once.")
        catalog[slug] = row
    if not catalog:
        raise ModioError(f"No documented mod entries were found in {library_path}.")

    ids_by_slug: Dict[str, int] = {}
    warnings: List[str] = []
    for slug, row in catalog.items():
        raw_id = row["mod_id"].strip()
        if not raw_id:
            continue
        if not re.fullmatch(r"[0-9]+", raw_id) or int(raw_id) < 1:
            warnings.append(f"Library entry '{slug}' has no valid positive numeric Mod Id and was ignored.")
            continue
        ids_by_slug[slug] = int(raw_id)

    seen_ids: Dict[int, str] = {}
    for slug, mod_id in ids_by_slug.items():
        prior_slug = seen_ids.get(mod_id)
        if prior_slug is not None:
            raise ModioError(
                f"The library assigns Mod Id {mod_id} to both '{prior_slug}' and '{slug}'."
            )
        seen_ids[mod_id] = slug

    missing_count = len(catalog) - len(ids_by_slug)
    entries = [
        ModEntry(name=row["name"], slug=slug, mod_id=ids_by_slug[slug])
        for slug, row in catalog.items()
        if slug in ids_by_slug
    ]
    if missing_count:
        warnings.append(
            f"{missing_count} documented library entr{'y' if missing_count == 1 else 'ies'} "
            "without a valid Mod Id were excluded."
        )
    if not entries:
        raise ModioError("The library has no entries with valid numeric Mod Id values.")
    return entries, warnings, missing_count


def _paged_items(client: ModioClient, path: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    if hasattr(client, "get_paged"):
        return client.get_paged(path, params=params, page_size=PAGE_SIZE)
    offset = 0
    items: List[Dict[str, Any]] = []
    while True:
        page_params = {**params, "_limit": PAGE_SIZE, "_offset": offset}
        payload = client.request("GET", path, params=page_params)
        page = payload.get("data")
        if not isinstance(page, list) or any(not isinstance(item, dict) for item in page):
            raise ModioError("mod.io returned an unexpected paginated response.")
        items.extend(page)

        total = payload.get("result_total")
        if total is not None:
            if not isinstance(total, int) or total < 0:
                raise ModioError("mod.io returned an invalid result_total.")
            if offset + len(page) >= total:
                break
        elif len(page) < PAGE_SIZE:
            break
        if not page:
            break
        offset += len(page)
    return items


def fetch_user_collections(client: ModioClient) -> List[Dict[str, Any]]:
    items = _paged_items(client, "/me/collections", {"game_id": BG3_GAME_ID})
    collections = []
    for item in items:
        game_id = item.get("game_id")
        if game_id is not None and str(game_id) != str(BG3_GAME_ID):
            continue
        collection_id = item.get("id")
        if isinstance(collection_id, int) and collection_id > 0:
            collections.append(item)
    return collections


def fetch_collection_mods(client: ModioClient, collection_id: int) -> Dict[int, str]:
    items = _paged_items(
        client,
        f"/games/{BG3_GAME_ID}/collections/{collection_id}/mods",
        {},
    )
    mods: Dict[int, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        mod_obj = item.get("mod")
        mod = mod_obj if isinstance(mod_obj, dict) else item
        mod_id = mod.get("id")
        if not isinstance(mod_id, int) or mod_id < 1:
            raise ModioError("A collection mod response did not include a valid mod ID.")
        mods[mod_id] = str(mod.get("name") or f"Mod {mod_id}")
    return mods


def validate_selected_mods(client: ModioClient, entries: Sequence[ModEntry]) -> None:
    for entry in entries:
        profile = client.request(
            "GET",
            f"/games/{BG3_GAME_ID}/mods/{entry.mod_id}",
        )
        if profile.get("id") != entry.mod_id:
            raise ModioError(
                f"Mod.io returned a mismatched profile for '{entry.name}' (ID {entry.mod_id})."
            )
        game_id = profile.get("game_id")
        if game_id is not None and str(game_id) != str(BG3_GAME_ID):
            raise ModioError(f"'{entry.name}' (ID {entry.mod_id}) is not a Baldur's Gate 3 mod.")


def validate_collection(client: ModioClient, collection_id: int) -> Dict[str, Any]:
    collection = client.request(
        "GET",
        f"/games/{BG3_GAME_ID}/collections/{collection_id}",
    )
    if collection.get("id") != collection_id:
        raise ModioError(f"mod.io returned a mismatched collection for ID {collection_id}.")
    game_id = collection.get("game_id")
    if game_id is not None and str(game_id) != str(BG3_GAME_ID):
        raise ModioError(f"Collection {collection_id} is not associated with Baldur's Gate 3.")
    return collection


def select_mods(
    entries: Sequence[ModEntry],
    input_fn: Callable[[str], str],
    output: TextIO,
) -> List[ModEntry]:
    for index, entry in enumerate(entries, start=1):
        print(f"{index}. {entry.name} (ID {entry.mod_id})", file=output)
    answer = input_fn("Select mod numbers separated by commas, or 'all': ").strip().casefold()
    if answer == "all":
        return list(entries)
    if not answer:
        raise ModioError("Select at least one documented mod.")
    selected_indices = []
    for value in answer.split(","):
        try:
            index = int(value.strip())
        except ValueError:
            raise ModioError(f"Invalid mod selection '{value.strip()}'.") from None
        if index < 1 or index > len(entries):
            raise ModioError(f"Mod selection {index} is outside the listed range.")
        if index not in selected_indices:
            selected_indices.append(index)
    return [entries[index - 1] for index in selected_indices]


def choose_collection(
    collections: Sequence[Dict[str, Any]],
    input_fn: Callable[[str], str],
    output: TextIO,
) -> Optional[Dict[str, Any]]:
    print("Collections you can update:", file=output)
    for index, collection in enumerate(collections, start=1):
        name = collection.get("name") or f"Collection {collection['id']}"
        print(
            f"{index}. {name} (ID {collection['id']})",
            file=output,
        )
    answer = input_fn("Enter a collection number, or 'c' to create a new collection: ").strip().casefold()
    if answer == "c":
        return None
    try:
        index = int(answer)
    except ValueError:
        raise ModioError("Enter a listed collection number or 'c'.") from None
    if index < 1 or index > len(collections):
        raise ModioError("The selected collection number is outside the listed range.")
    return collections[index - 1]


def build_changes(
    selected: Sequence[ModEntry],
    current_mods: Dict[int, str],
    strategy: str,
) -> Tuple[List[ModEntry], List[Tuple[int, str]]]:
    selected_ids = {entry.mod_id for entry in selected}
    to_add = [entry for entry in selected if entry.mod_id not in current_mods]
    to_remove = (
        [(mod_id, name) for mod_id, name in current_mods.items() if mod_id not in selected_ids]
        if strategy == "replace"
        else []
    )
    return to_add, sorted(to_remove, key=lambda item: item[0])


def show_preview(
    selected: Sequence[ModEntry],
    to_add: Sequence[ModEntry],
    to_remove: Sequence[Tuple[int, str]],
    collection_name: str,
    collection_summary: Optional[str],
    creating: bool,
    output: TextIO,
) -> None:
    print("\nChange preview:", file=output)
    print(
        f"Collection: {collection_name}"
        + (" (new, Public)" if creating else ""),
        file=output,
    )
    if creating:
        print(f"Description: {collection_summary}", file=output)
    print(f"Selected documented mods: {len(selected)}", file=output)
    print("Mods to add:", file=output)
    if to_add:
        for entry in to_add:
            print(f"  + {entry.name} (ID {entry.mod_id})", file=output)
    else:
        print("  (none)", file=output)
    print("Mods to remove:", file=output)
    if to_remove:
        for mod_id, name in to_remove:
            print(f"  - {name} (ID {mod_id})", file=output)
    else:
        print("  (none)", file=output)


def apply_changes(
    client: ModioClient,
    collection_id: int,
    to_add: Sequence[ModEntry],
    to_remove: Sequence[Tuple[int, str]],
) -> Dict[str, Any]:
    operations: Dict[str, Any] = {}
    if to_add:
        fields = [("mods[]", str(entry.mod_id)) for entry in to_add]
        try:
            client.request(
                "POST",
                f"/games/{BG3_GAME_ID}/collections/{collection_id}/mods",
                fields=fields,
            )
            operations["add_mods"] = {
                "status": "success",
                "mod_ids": [entry.mod_id for entry in to_add],
            }
        except ModioError as error:
            operations["add_mods"] = {
                "status": "failed",
                "mod_ids": [entry.mod_id for entry in to_add],
                "error": str(error),
            }
    else:
        operations["add_mods"] = {"status": "skipped", "reason": "No missing selected mods."}

    if to_remove and operations["add_mods"]["status"] == "failed":
        operations["remove_mods"] = {
            "status": "skipped",
            "reason": "Add failed; existing collection contents were preserved.",
        }
    elif to_remove:
        failures = []
        removed = []
        for mod_id, _name in to_remove:
            try:
                client.request(
                    "DELETE",
                    f"/games/{BG3_GAME_ID}/collections/{collection_id}/mods/{mod_id}",
                )
                removed.append(mod_id)
            except ModioError as error:
                failures.append({"mod_id": mod_id, "error": str(error)})
        operations["remove_mods"] = {
            "status": "failed" if failures else "success",
            "removed_mod_ids": removed,
            "failures": failures,
        }
    else:
        operations["remove_mods"] = {"status": "skipped", "reason": "No unselected mods to remove."}

    success = all(
        operation["status"] in ("success", "skipped")
        for operation in operations.values()
    )
    return {
        "status": "success" if success else "partial_failure",
        "collection_id": collection_id,
        "operations": operations,
    }


def _required_input(label: str, input_fn: Callable[[str], str]) -> str:
    value = input_fn(f"{label}: ").strip()
    if not value:
        raise ModioError(f"{label} cannot be empty.")
    return value


def run_workflow(
    client: ModioClient,
    library_path: Path = LIBRARY_PATH,
    dry_run: bool = False,
    input_fn: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
) -> Dict[str, Any]:
    entries, warnings, _missing_count = parse_catalog(library_path)
    for warning in warnings:
        print(f"Warning: {warning}", file=output)

    selected = select_mods(entries, input_fn, output)
    validate_selected_mods(client, selected)
    collections = fetch_user_collections(client)
    target = choose_collection(collections, input_fn, output)

    creating = target is None
    if target is None:
        collection_name = _required_input("New collection name", input_fn)
        collection_summary = _required_input("New collection description", input_fn)
        strategy = "add"
        current_mods: Dict[int, str] = {}
        collection_id = None
    else:
        collection_id = target["id"]
        collection = validate_collection(client, collection_id)
        collection_name = str(collection.get("name") or target.get("name") or f"Collection {collection_id}")
        collection_summary = None
        current_mods = fetch_collection_mods(client, collection_id)
        answer = input_fn(
            "Update strategy: add missing selected mods only [a], or replace the collection [r]: "
        ).strip().casefold()
        if answer not in ("a", "r"):
            raise ModioError("Choose 'a' for add-only or 'r' to replace the selected collection contents.")
        strategy = "add" if answer == "a" else "replace"

    to_add, to_remove = build_changes(selected, current_mods, strategy)
    show_preview(
        selected,
        to_add,
        to_remove,
        collection_name,
        collection_summary,
        creating,
        output,
    )
    if dry_run:
        print("\nDry run: no changes were sent to mod.io.", file=output)
        return {"status": "dry_run"}

    confirmation = input_fn("Type 'yes' to confirm these API changes: ").strip().casefold()
    if confirmation != "yes":
        print("Cancelled; no changes were sent to mod.io.", file=output)
        return {"status": "cancelled"}

    if creating:
        created = client.request(
            "POST",
            f"/games/{BG3_GAME_ID}/collections",
            fields=[
                ("name", collection_name),
                ("summary", collection_summary or ""),
                ("visible", "1"),
            ],
        )
        new_id = created.get("id")
        if not isinstance(new_id, int) or new_id < 1:
            raise ModioError("mod.io did not return a valid ID for the created collection.")
        collection_id = new_id
        print(
            f"Created public collection '{collection_name}' (ID {collection_id}); verifying it.",
            file=output,
        )
        validate_collection(client, new_id)
    if collection_id is None:
        raise ModioError("No collection ID was available for the selected operation.")
    result = apply_changes(client, collection_id, to_add, to_remove)
    for operation, outcome in result["operations"].items():
        if outcome["status"] == "success":
            print(f"{operation}: succeeded.", file=output)
        elif outcome["status"] == "failed":
            print(f"{operation}: failed: {outcome}", file=output)
        else:
            print(f"{operation}: {outcome['status']} ({outcome.get('reason', '')})", file=output)
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create or update a public BG3 mod.io collection from mods/library.md."
    )
    parser.add_argument(
        "--library",
        type=Path,
        default=LIBRARY_PATH,
        help="Path to the mod library Markdown file (default: mods/library.md).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the collection change preview without sending any API writes.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )
    args = parser.parse_args(argv)

    err_color = ConsoleColor(stream=sys.stderr)
    token = get_oauth_token()
    if not token:
        msg = "MODIO_PAT environment variable or .env entry is required; token is never accepted as an argument."
        if args.json:
            print(json.dumps({"error": msg, "success": False}, indent=2))
        else:
            print(f"{err_color.red('[ERROR]')} {msg}", file=sys.stderr)
        return ExitCode.NOPERM

    try:
        result = run_workflow(
            ModioClient(token),
            library_path=args.library,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        return ExitCode.GENERAL if result.get("status") == "partial_failure" else ExitCode.OK
    except ModioError as error:
        if args.json:
            print(json.dumps({"error": str(error), "success": False}, indent=2))
        else:
            print(f"{err_color.red('[ERROR]')} {error}", file=sys.stderr)
        return ExitCode.USAGE
    except (EOFError, KeyboardInterrupt):
        print(f"\n{err_color.yellow('Cancelled before completing the collection workflow.')}", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
