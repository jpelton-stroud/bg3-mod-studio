#!/usr/bin/env python3
"""Safely update a local BG3 mod's metadata and profile settings on mod.io."""

import argparse
import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import MY_MODS_DIR, REPO_ROOT, normalize_mod_key, resolve_mod_dir
from bg3_core.modio_client import (
    BG3_GAME_ID,
    ModioClient,
    ModioError,
    get_oauth_token,
)
from bg3_core.render_modio_description import render_mod_description

WORKSPACE_ROOT = REPO_ROOT
normalize_name = normalize_mod_key

COMMUNITY_OPTIONS = {
    "allow_mod_comments": 1,
    "allow_dependency": 1024,
    "allow_mod_use_in_collections": 131072,
}
NONCOMMERCIAL_CREDIT_OPTIONS = {
    "show_credits": 1,
    "original_or_permitted_assets": 2,
    "allow_redistribution_with_credit": 4,
    "allow_porting_with_credit": 8,
    "allow_patching_without_credit": 16,
    "allow_patching_with_credit": 32,
    "allow_patching_with_permission": 64,
    "allow_repackage_without_credit": 128,
    "allow_repackage_with_credit": 256,
    "allow_repackage_with_permission": 512,
}
COMMUNITY_OPTIONS_MASK = sum(COMMUNITY_OPTIONS.values())
CREDIT_OPTIONS_MASK = sum(NONCOMMERCIAL_CREDIT_OPTIONS.values())


def resolve_local_mod(query: str, mods_dir: Optional[Path] = None) -> Path:
    query_key = normalize_name(query.strip())
    if not query_key:
        raise ModioError("Provide a mod name or slug from my_mods/.")
    target_dir = Path(mods_dir) if mods_dir is not None else Path(os.environ.get("BG3_MODS_DIR", MY_MODS_DIR))
    if not target_dir.is_dir():
        raise ModioError(f"Mod directory does not exist: {target_dir}")

    resolved = resolve_mod_dir(query, roots=(target_dir,))
    if resolved and resolved.is_dir():
        return resolved

    matches = [
        path
        for path in target_dir.iterdir()
        if path.is_dir() and normalize_name(path.name) == query_key
    ]
    if not matches:
        raise ModioError(f"No exact local mod folder matches '{query}'.")
    if len(matches) != 1:
        raise ModioError(f"More than one local mod folder matches '{query}'.")
    return matches[0]


def read_readme_title(readme: Path) -> Optional[str]:
    for line in readme.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1)
    return None


def ensure_description_file(mod_dir: Path) -> Path:
    description_file = mod_dir / "modio_description.html"
    if not description_file.is_file():
        readme_file = mod_dir / "README.md"
        if not readme_file.is_file():
            raise ModioError(f"Cannot generate description; README is missing: {readme_file}")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                render_mod_description(str(mod_dir), write_file=True, as_json=True)
        except (OSError, ValueError) as error:
            raise ModioError(f"Could not generate mod.io description: {error}") from None
    if not description_file.is_file():
        raise ModioError(f"Description generator did not create {description_file}.")
    if not description_file.read_bytes():
        raise ModioError(f"Description file is empty: {description_file}")
    return description_file


def _as_items(payload: Dict[str, Any], label: str) -> List[Dict[str, Any]]:
    items = payload.get("data")
    if not isinstance(items, list):
        raise ModioError(f"mod.io returned an unexpected {label} response.")
    return [item for item in items if isinstance(item, dict)]


def find_remote_mod(client: ModioClient, mod_dir: Path, title: Optional[str]) -> Dict[str, Any]:
    slug = mod_dir.name
    # 1. Search authenticated user mods first (includes drafts and hidden mods)
    try:
        user_mods_payload = client.request(
            "GET", "/me/mods", params={"game_id": BG3_GAME_ID, "name_id": slug}
        )
        for mod in _as_items(user_mods_payload, "user mods"):
            if mod.get("name_id") == slug:
                return mod
    except ModioError:
        pass

    if title:
        try:
            user_mods_title = client.request(
                "GET", "/me/mods", params={"game_id": BG3_GAME_ID, "_q": title}
            )
            for mod in _as_items(user_mods_title, "user mods"):
                if mod.get("name_id") == slug or (title and mod.get("name") == title):
                    return mod
        except ModioError:
            pass

    # 2. Check public game mods catalog
    try:
        catalog_payload = client.request(
            "GET", f"/games/{BG3_GAME_ID}/mods", params={"name_id": slug}
        )
        for mod in _as_items(catalog_payload, "catalog mods"):
            if mod.get("name_id") == slug:
                return mod
    except ModioError:
        pass

    if title:
        try:
            catalog_title = client.request(
                "GET", f"/games/{BG3_GAME_ID}/mods", params={"name": title}
            )
            for mod in _as_items(catalog_title, "catalog mods"):
                if mod.get("name") == title or mod.get("name_id") == slug:
                    return mod
        except ModioError:
            pass

    raise ModioError(f"No unique mod.io profile matches local mod '{mod_dir.name}'.")


def extract_allowed_tag_map(game_tags: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    allowed: Dict[str, str] = {}
    for item in game_tags:
        for t in item.get("tags", []):
            if isinstance(t, str) and t.strip():
                allowed[normalize_name(t.strip())] = t.strip()
        name = item.get("name")
        if isinstance(name, str) and name.strip() and not item.get("tags"):
            allowed.setdefault(normalize_name(name.strip()), name.strip())
        tag_val = item.get("tag")
        if isinstance(tag_val, str) and tag_val.strip():
            allowed.setdefault(normalize_name(tag_val.strip()), tag_val.strip())
    return allowed


def validate_selected_tags(
    selected: Iterable[str], allowed_tags: Iterable[Dict[str, Any]]
) -> List[str]:
    allowed = extract_allowed_tag_map(allowed_tags)
    canonical: List[str] = []
    seen = set()
    invalid: List[str] = []
    for tag in selected:
        tag_str = tag.strip()
        if not tag_str:
            continue
        key = normalize_name(tag_str)
        if key in allowed:
            canonical_name = allowed[key]
            if canonical_name not in seen:
                seen.add(canonical_name)
                canonical.append(canonical_name)
        else:
            invalid.append(tag_str)
    if invalid:
        allowed_list = sorted(set(allowed.values()), key=str.casefold)
        raise ModioError(
            f"Invalid tags requested: {', '.join(invalid)}. Allowed: {', '.join(allowed_list)}"
        )
    return canonical


def current_tags_for_mod(mod: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    for entry in mod.get("tags", []):
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            tags.append(entry["name"])
        elif isinstance(entry, str):
            tags.append(entry)
    return tags


def prepare_update(
    mod_query: str,
    selected_tags: Sequence[str],
    client: ModioClient,
    mods_dir: Path = MY_MODS_DIR,
) -> Dict[str, Any]:
    mod_dir = resolve_local_mod(mod_query, mods_dir=mods_dir)
    readme_file = mod_dir / "README.md"
    readme_title = read_readme_title(readme_file) if readme_file.is_file() else None
    description_file = ensure_description_file(mod_dir)
    remote = find_remote_mod(client, mod_dir, readme_title)
    mod_id = remote.get("id")
    if not isinstance(mod_id, int):
        raise ModioError(f"Matched mod profile for '{mod_dir.name}' is missing an ID.")

    game_tags = _as_items(
        client.request("GET", f"/games/{BG3_GAME_ID}/tags"), "game tags"
    )
    allowed_tag_names = sorted(
        extract_allowed_tag_map(game_tags).values(),
        key=str.casefold,
    )
    selected = validate_selected_tags(selected_tags, game_tags)
    current_tags = current_tags_for_mod(remote)
    current_tag_keys = {normalize_name(tag) for tag in current_tags}
    tags_to_add = [
        tag for tag in selected if normalize_name(tag) not in current_tag_keys
    ]
    target_slug = mod_dir.name
    current_slug = remote.get("name_id")
    slug_to_update = target_slug if current_slug != target_slug else None
    return {
        "mod": {
            "id": mod_id,
            "name": remote.get("name"),
            "slug": current_slug,
            "target_slug": target_slug,
            "slug_to_update": slug_to_update,
            "profile_url": remote.get("profile_url"),
            "admin_settings_url": (
                f"https://mod.io/g/baldursgate3/m/{target_slug or current_slug}/admin/settings"
            ),
        },
        "local_mod_dir": str(mod_dir),
        "description_file": str(description_file),
        "tags_to_add": tags_to_add,
        "current_tags": current_tags,
        "allowed_tags": allowed_tag_names,
        "community_options": COMMUNITY_OPTIONS_MASK,
        "maturity_option": 0,
        "noncommercial_credit_options": CREDIT_OPTIONS_MASK,
        "visible": 1,
    }


def apply_update(client: ModioClient, plan: Dict[str, Any], description: str) -> Dict[str, Any]:
    mod_id = plan["mod"]["id"]
    operations: Dict[str, Any] = {}
    fields = [
        ("description", description),
        ("community_options", str(plan["community_options"])),
        ("maturity_option", str(plan["maturity_option"])),
        ("credit_options", str(plan["noncommercial_credit_options"])),
        ("visible", str(plan["visible"])),
    ]
    try:
        response = client.request(
            "POST",
            f"/games/{BG3_GAME_ID}/mods/{mod_id}",
            fields=fields,
            multipart=True,
        )
        operations["profile_update"] = {"status": "success"}
        if isinstance(response, dict) and response.get("name_id"):
            plan["mod"]["slug"] = response["name_id"]
            plan["mod"]["profile_url"] = response.get(
                "profile_url",
                f"https://mod.io/g/baldursgate3/m/{response['name_id']}",
            )
            plan["mod"]["admin_settings_url"] = (
                f"https://mod.io/g/baldursgate3/m/{response['name_id']}/admin/settings"
            )
    except ModioError as error:
        operations["profile_update"] = {"status": "failed", "error": str(error)}

    tags = plan.get("tags_to_add", [])
    if tags:
        tag_fields = [("tags[]", tag) for tag in tags]
        try:
            client.request(
                "POST",
                f"/games/{BG3_GAME_ID}/mods/{mod_id}/tags",
                fields=tag_fields,
            )
            operations["add_tags"] = {"status": "success", "tags": tags}
        except ModioError as error:
            operations["add_tags"] = {
                "status": "failed",
                "tags": tags,
                "error": str(error),
            }
    else:
        operations["add_tags"] = {"status": "skipped", "reason": "No new approved tags."}
    return {
        "status": (
            "success"
            if all(result["status"] in ("success", "skipped") for result in operations.values())
            else "partial_failure"
        ),
        "mod": plan["mod"],
        "operations": operations,
    }


def parse_tags(values: Optional[Sequence[str]]) -> List[str]:
    return [
        tag.strip()
        for value in (values or [])
        for tag in value.split(",")
        if tag.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or update the mod.io profile for a local Baldur's Gate 3 mod. "
            "Writes require --confirm after interactive user approval."
        )
    )
    parser.add_argument("--mod", required=True, help="Exact mod folder name or slug within my_mods/")
    parser.add_argument(
        "--tags",
        action="append",
        default=[],
        help="Approved tag(s), comma-separated; may be repeated",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Perform API writes; only pass after the user explicitly confirms the preview",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    args = parser.parse_args()

    token = get_oauth_token()
    if not token:
        parser.error("MODIO_PAT environment variable or .env entry is required; token is never accepted as an argument.")

    client = ModioClient(token)
    try:
        plan = prepare_update(args.mod, parse_tags(args.tags), client)
        if args.confirm:
            description = Path(plan["description_file"]).read_text(encoding="utf-8")
            result = apply_update(client, plan, description)
        else:
            result = {"status": "preview", **plan}
    except (ModioError, OSError, UnicodeError) as error:
        result = {"status": "failed", "error": str(error)}

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif result["status"] == "preview":
        color = ConsoleColor(stream=sys.stdout)
        print(f"{color.bold('Preview for')} {result['mod']['name']} ({result['mod']['slug']})")
        print(f"Tags to add: {', '.join(result['tags_to_add']) or '(none)'}")
        print("Profile fields: description, community options, non-commercial reuse permissions, Public visibility")
        print(color.yellow("No API writes made. Review the change list and pass --confirm only after user approval."))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return ExitCode.GENERAL if result["status"] in ("failed", "partial_failure") else ExitCode.OK


if __name__ == "__main__":
    sys.exit(main())
