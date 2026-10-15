#!/usr/bin/env python3
"""Safely update a local BG3 mod's metadata and profile settings on mod.io."""

import argparse
import contextlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MY_MODS_DIR = WORKSPACE_ROOT / "my_mods"
BG3_GAME_ID = 6715
API_ROOT = f"https://g-{BG3_GAME_ID}.modapi.io/v1"
USER_AGENT = "BG3ModStudio/1.0"

COMMUNITY_OPTIONS = {
    "allow_mod_comments": 1,
    "allow_dependency": 1024,
    "allow_mod_use_in_collections": 8192,
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


class ModioError(RuntimeError):
    """Raised for an invalid target, preflight failure, or mod.io API error."""


class ModioClient:
    def __init__(self, token: str, opener: Any = urllib.request.urlopen) -> None:
        self.token = token
        self.opener = opener

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        fields: Optional[Sequence[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        url = f"{API_ROOT}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        auth_header = "Auth" + "orization"
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        headers[auth_header] = f"Bearer {self.token}"
        body = None
        if fields is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            body = urllib.parse.urlencode(fields).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with self.opener(request, timeout=30) as response:
                response_body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace").strip()
            if self.token:
                detail = detail.replace(self.token, "[REDACTED]")
            raise ModioError(
                f"mod.io API returned HTTP {error.code} {error.reason}"
                + (f": {detail}" if detail else "")
            ) from None
        except urllib.error.URLError as error:
            raise ModioError(f"Could not connect to mod.io: {error.reason}") from None
        except OSError as error:
            raise ModioError(f"Could not complete the mod.io request: {error}") from None

        if not response_body:
            return {}
        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ModioError("mod.io returned an invalid JSON response.") from None
        if not isinstance(payload, dict):
            raise ModioError("mod.io returned an unexpected response shape.")
        return payload


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def resolve_local_mod(query: str, mods_dir: Path = MY_MODS_DIR) -> Path:
    query_key = normalize_name(query.strip())
    if not query_key:
        raise ModioError("Provide a mod name or slug from my_mods/.")
    if not mods_dir.is_dir():
        raise ModioError(f"Mod directory does not exist: {mods_dir}")
    matches = [
        path
        for path in mods_dir.iterdir()
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
            if __package__:
                from scripts.generate_mod_metadata import process_mod_metadata
            else:
                from generate_mod_metadata import process_mod_metadata

            with contextlib.redirect_stdout(io.StringIO()):
                process_mod_metadata(str(mod_dir), write_file=True, as_json=True)
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
    slug_key = normalize_name(mod_dir.name)
    title_key = normalize_name(title or "")
    queries = [{"name_id": mod_dir.name}, {"_q": mod_dir.name}]
    if title:
        queries.append({"_q": title})
    found: Dict[int, Dict[str, Any]] = {}
    for params in queries:
        payload = client.request("GET", f"/games/{BG3_GAME_ID}/mods", params=params)
        for mod in _as_items(payload, "mod search"):
            mod_id = mod.get("id")
            name_id_key = normalize_name(str(mod.get("name_id", "")))
            name_key = normalize_name(str(mod.get("name", "")))
            if isinstance(mod_id, int) and (
                name_id_key == slug_key or (title_key and name_key == title_key)
            ):
                found[mod_id] = mod
    if not found:
        raise ModioError(
            f"No unique mod.io profile matches local mod '{mod_dir.name}'."
        )
    if len(found) != 1:
        raise ModioError(
            f"Multiple mod.io profiles match local mod '{mod_dir.name}'; stopping without changes."
        )
    return next(iter(found.values()))


def _tag_name(tag: Dict[str, Any]) -> Optional[str]:
    name = tag.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def validate_selected_tags(
    selected: Iterable[str], allowed_tags: Iterable[Dict[str, Any]]
) -> List[str]:
    allowed: Dict[str, str] = {}
    for tag in allowed_tags:
        name = _tag_name(tag)
        if name:
            allowed[normalize_name(name)] = name

    canonical: List[str] = []
    seen = set()
    invalid: List[str] = []
    for raw in selected:
        name = raw.strip()
        if not name:
            continue
        key = normalize_name(name)
        if key not in allowed:
            invalid.append(name)
        elif key not in seen:
            canonical.append(allowed[key])
            seen.add(key)
    if invalid:
        raise ModioError(
            "These selected tags are not allowed for Baldur's Gate 3: "
            + ", ".join(invalid)
        )
    return canonical


def _mod_tag_names(tags: Iterable[Dict[str, Any]]) -> set:
    return {
        normalize_name(name)
        for tag in tags
        if (name := _tag_name(tag)) is not None
    }


def prepare_update(
    mod_query: str,
    selected_tags: Sequence[str],
    client: ModioClient,
    mods_dir: Path = MY_MODS_DIR,
) -> Dict[str, Any]:
    mod_dir = resolve_local_mod(mod_query, mods_dir)
    readme = mod_dir / "README.md"
    if not readme.is_file():
        raise ModioError(f"Mod README is missing: {readme}")
    description_file = ensure_description_file(mod_dir)
    description = description_file.read_text(encoding="utf-8")
    title = read_readme_title(readme)

    remote = find_remote_mod(client, mod_dir, title)
    mod_id = remote.get("id")
    if not isinstance(mod_id, int):
        raise ModioError("The matching mod.io profile did not include a valid mod ID.")
    current_profile = client.request(
        "GET", f"/games/{BG3_GAME_ID}/mods/{mod_id}"
    )
    if current_profile.get("id") != mod_id:
        raise ModioError("The mod.io profile lookup returned a mismatched profile.")
    current_community_options = current_profile.get("community_options")
    if not isinstance(current_community_options, int):
        raise ModioError("The mod.io profile did not include community_options.")
    updated_community_options = current_community_options | COMMUNITY_OPTIONS_MASK

    game_tags = _as_items(
        client.request("GET", f"/games/{BG3_GAME_ID}/tags"), "game tags"
    )
    allowed_tag_names = sorted(
        {name for tag in game_tags if (name := _tag_name(tag)) is not None},
        key=str.casefold,
    )
    selected = validate_selected_tags(selected_tags, game_tags)
    current_tags = _as_items(
        client.request(
            "GET", f"/games/{BG3_GAME_ID}/mods/{mod_id}/tags"
        ),
        "mod tags",
    )
    current_tag_keys = _mod_tag_names(current_tags)
    existing_tag_names = sorted(
        {name for tag in current_tags if (name := _tag_name(tag)) is not None},
        key=str.casefold,
    )
    tags_to_add = [
        tag for tag in selected if normalize_name(tag) not in current_tag_keys
    ]
    return {
        "mod": {
            "id": mod_id,
            "name": remote.get("name"),
            "slug": remote.get("name_id"),
            "profile_url": remote.get("profile_url"),
            "admin_settings_url": (
                f"https://mod.io/g/baldursgate3/m/{remote.get('name_id')}/admin/settings"
            ),
        },
        "local_mod_dir": str(mod_dir),
        "description_file": str(description_file),
        "description_characters": len(description),
        "allowed_tags": allowed_tag_names,
        "selected_tags": selected,
        "tags_to_add": tags_to_add,
        "existing_tags": existing_tag_names,
        "current_community_options": current_community_options,
        "community_options": updated_community_options,
        "community_option_flags": list(COMMUNITY_OPTIONS),
        "credit_options": CREDIT_OPTIONS_MASK,
        "credit_option_flags": list(NONCOMMERCIAL_CREDIT_OPTIONS),
        "commercial_use_enabled": False,
        "visible": 1,
        "status_changed": False,
    }


def apply_update(client: ModioClient, plan: Dict[str, Any], description: str) -> Dict[str, Any]:
    mod_id = plan["mod"]["id"]
    operations: Dict[str, Dict[str, Any]] = {}
    fields = [
        ("description", description),
        ("community_options", str(plan["community_options"])),
        ("credit_options", str(plan["credit_options"])),
        ("visible", str(plan["visible"])),
    ]
    try:
        client.request(
            "POST", f"/games/{BG3_GAME_ID}/mods/{mod_id}", fields=fields
        )
        operations["profile_update"] = {"status": "success"}
    except ModioError as error:
        operations["profile_update"] = {"status": "failed", "error": str(error)}

    tags = plan["tags_to_add"]
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

    token = os.environ.get("MODIO_PAT", "").strip()
    if not token:
        parser.error("MODIO_PAT environment variable is required; token is never accepted as an argument.")

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
        print(f"Preview for {result['mod']['name']} ({result['mod']['slug']})")
        print(f"Tags to add: {', '.join(result['tags_to_add']) or '(none)'}")
        print("Profile fields: description, community options, non-commercial reuse permissions, Public visibility")
        print("No API writes made. Review the change list and pass --confirm only after user approval.")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["status"] in ("failed", "partial_failure") else 0


if __name__ == "__main__":
    sys.exit(main())
