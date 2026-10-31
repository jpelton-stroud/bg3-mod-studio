#!/usr/bin/env python3
"""
query_mod_database.py - High-speed BiS gear, spell, and mechanics query engine.

Indexes Weapon.txt, Armor.txt, Object.txt, Passive.txt, and Status_BOOST.txt
across all cataloged community mods in mods/ (ignoring my_mods/).
Uses directory mtime caching ($XDG_CACHE_HOME/bg3/mod_database.json) for sub-10ms response times.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

from bg3_core.cli_common import ExitCode
from bg3_core.env_paths import get_cache_dir, get_subscribed_mods_dir
from bg3_core.larian_parsers import parse_loca_bytes

# Files to scan within mod directories
TARGET_STAT_FILES = {
    "weapon.txt": "Weapon",
    "armor.txt": "Armor",
    "object.txt": "Object",
    "passive.txt": "Passive",
    "passives.txt": "Passive",
    "status_boost.txt": "Status_BOOST",
    "spell_projectile.txt": "Spell",
    "spell_target.txt": "Spell",
    "spell_shout.txt": "Spell",
    "spell_zone.txt": "Spell",
    "spell_rush.txt": "Spell",
    "spell_teleportation.txt": "Spell",
    "spell_throw.txt": "Spell",
    "spell_wall.txt": "Spell",
    "spells.txt": "Spell",
}

HANDLE_REGEX = re.compile(r'(h[0-9a-fA-F]{32}|h[a-zA-Z0-9_]{30,40})(?:;\d+)?')
ENTRY_REGEX = re.compile(r'^new\s+entry\s+"([^"]+)"', re.IGNORECASE)
DATA_REGEX = re.compile(r'^data\s+"([^"]+)"\s+"([^"]*)"', re.IGNORECASE)
USING_REGEX = re.compile(r'^using\s+"([^"]+)"', re.IGNORECASE)
TYPE_REGEX = re.compile(r'^type\s+"([^"]+)"', re.IGNORECASE)


def infer_slot(entry_type: str, slot_val: str, using_val: str, entry_name: str) -> str:
    """Infers the equipment slot from slot data, base template, or entry name."""
    s = (slot_val or "").strip().lower()
    u = (using_val or "").strip().lower()
    n = (entry_name or "").strip().lower()

    if s:
        return slot_val.capitalize()

    if entry_type.lower() == "weapon" or "weapon" in u or "wpn_" in n:
        return "Weapon"

    if "amulet" in u or "amulet" in n:
        return "Amulet"
    if "ring" in u or "ring" in n:
        return "Ring"
    if "boot" in u or "boot" in n or "foot" in u:
        return "Boots"
    if "glove" in u or "glove" in n or "hand" in u or "gauntlet" in n:
        return "Gloves"
    if "head" in u or "helmet" in u or "hood" in n or "circlet" in n or "helm" in n:
        return "Helmet"
    if "cloak" in u or "cape" in u or "cloak" in n or "cape" in n:
        return "Cloak"
    if "body" in u or "armor" in u or "robe" in n or "tunic" in n or "plate" in n or "chest" in n:
        return "Breast"

    return entry_type.capitalize() if entry_type else "Other"


def load_localization_strings(mod_dir: Path) -> dict[str, str]:
    """Loads handle-to-string mappings from any XML or binary LOCA files in the mod."""
    strings = {}

    # 1. Parse binary .loca files if present
    for loca_file in mod_dir.rglob("*.loca"):
        try:
            entries = parse_loca_bytes(loca_file.read_bytes())
            strings.update(entries)
        except (OSError, ValueError, KeyError):
            pass

    # 2. Parse XML localization files
    for xml_file in mod_dir.rglob("*.xml"):
        # Ignore non-localization XMLs
        if "meta.lsx" in xml_file.name.lower() or xml_file.name.endswith(".lsx"):
            continue
        try:
            content = xml_file.read_text(encoding="utf-8", errors="replace")
            # Fast regex extraction for <content contentuid="h...">Text</content>
            for match in re.finditer(
                r'<content\s+contentuid="([^"]+)"[^>]*>(.*?)</content>',
                content,
                re.DOTALL,
            ):
                uid = match.group(1).strip()
                text = match.group(2).strip()
                # Clean up xml entities
                text = (
                    text.replace("&amp;", "&")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("&quot;", '"')
                )
                strings[uid] = text
        except (OSError, UnicodeDecodeError):
            continue
    return strings


def parse_mod_stat_entries(mod_dir: Path, mod_slug: str) -> list[dict]:
    """Parses stat files in a mod and returns normalized structured entries."""
    loc_map = load_localization_strings(mod_dir)
    entries = []

    # Find all .txt files
    for txt_path in mod_dir.rglob("*.txt"):
        filename_lower = txt_path.name.lower()
        if filename_lower in TARGET_STAT_FILES:
            category = TARGET_STAT_FILES[filename_lower]
        elif filename_lower.startswith("spell_") and filename_lower.endswith(".txt"):
            category = "Spell"
        else:
            continue

        try:
            content = txt_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        current_entry = None

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            entry_match = ENTRY_REGEX.match(line)
            if entry_match:
                if current_entry:
                    finalize_entry(current_entry, loc_map)
                    entries.append(current_entry)

                name = entry_match.group(1)
                current_entry = {
                    "id": name,
                    "mod": mod_slug,
                    "category": category,
                    "type": category,
                    "using": "",
                    "display_name": "",
                    "description": "",
                    "slot": "",
                    "rarity": "Common",
                    "boosts": "",
                    "passives": "",
                    "damage": "",
                    "damage_type": "",
                    "ac": "",
                    "source_file": str(txt_path.name),
                }
                continue

            if not current_entry:
                continue

            using_match = USING_REGEX.match(line)
            if using_match:
                current_entry["using"] = using_match.group(1)
                continue

            type_match = TYPE_REGEX.match(line)
            if type_match:
                current_entry["type"] = type_match.group(1)
                continue

            data_match = DATA_REGEX.match(line)
            if data_match:
                prop = data_match.group(1)
                val = data_match.group(2)

                prop_lower = prop.lower()
                if prop_lower == "displayname":
                    current_entry["_raw_display"] = val
                elif prop_lower == "description":
                    current_entry["_raw_desc"] = val
                elif prop_lower == "slot":
                    current_entry["slot"] = val
                elif prop_lower == "rarity":
                    current_entry["rarity"] = val
                elif prop_lower in ("boosts", "defaultboosts"):
                    current_entry["boosts"] = (
                        (current_entry["boosts"] + ";" + val).strip(";")
                        if current_entry["boosts"]
                        else val
                    )
                elif prop_lower in ("passivesonequip", "passives"):
                    current_entry["passives"] = (
                        (current_entry["passives"] + ";" + val).strip(";")
                        if current_entry["passives"]
                        else val
                    )
                elif prop_lower == "damage":
                    current_entry["damage"] = val
                elif prop_lower == "damage type":
                    current_entry["damage_type"] = val
                elif prop_lower == "armorclass":
                    current_entry["ac"] = val

        if current_entry:
            finalize_entry(current_entry, loc_map)
            entries.append(current_entry)

    return entries


def finalize_entry(entry: dict, loc_map: dict[str, str]) -> None:
    """Resolves handles to names/descriptions and infers slot."""
    # Resolve DisplayName
    raw_disp = entry.pop("_raw_display", "")
    disp_text = ""
    if raw_disp:
        m = HANDLE_REGEX.search(raw_disp)
        if m and m.group(1) in loc_map:
            disp_text = loc_map[m.group(1)]
        elif not m:
            disp_text = raw_disp

    if not disp_text:
        # Generate friendly name from entry ID
        clean = re.sub(r'^(I_|Tut_|OBJ_|WPN_|ARM_)', '', entry["id"])
        clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean)
        disp_text = clean.replace("_", " ").strip()

    entry["display_name"] = disp_text

    # Resolve Description
    raw_desc = entry.pop("_raw_desc", "")
    desc_text = ""
    if raw_desc:
        m = HANDLE_REGEX.search(raw_desc)
        if m and m.group(1) in loc_map:
            desc_text = loc_map[m.group(1)]
        elif not m:
            desc_text = raw_desc
    entry["description"] = desc_text

    # Infer Slot
    entry["slot"] = infer_slot(
        entry["type"],
        entry["slot"],
        entry["using"],
        entry["id"]
    )


def get_mods_directory(workspace_root: Optional[Path] = None) -> Path:
    subscribed = get_subscribed_mods_dir()
    if subscribed.is_dir():
        return subscribed
    if workspace_root:
        ws_mods = workspace_root / "mods"
        if ws_mods.is_dir():
            return ws_mods
    return subscribed


def get_cache_path(_workspace_root: Optional[Path] = None) -> Path:
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "mod_database.json"


def build_or_load_index(workspace_root: Optional[Path] = None, force_reindex: bool = False) -> list[dict]:
    """Loads database from cache, or incrementally updates cache based on directory mtime."""
    mods_dir = get_mods_directory(workspace_root)
    cache_file = get_cache_path(workspace_root)

    if not mods_dir.is_dir():
        return []

    # Get all active mod directories in mods/ (ignore hidden, ignore library.md)
    current_mods = {
        d.name: d for d in mods_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    }

    cached_data = None
    if not force_reindex and cache_file.exists():
        try:
            cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached_data = None

    if cached_data and "mod_mtimes" in cached_data and "entries" in cached_data:
        cached_mtimes = cached_data["mod_mtimes"]
        entries = cached_data["entries"]
        needs_update = False

        # Check for modified or new mods
        for mod_name, mod_path in current_mods.items():
            current_mtime = mod_path.stat().st_mtime
            if mod_name not in cached_mtimes or cached_mtimes[mod_name] != current_mtime:
                needs_update = True
                # Remove stale entries for this mod
                entries = [e for e in entries if e["mod"] != mod_name]
                # Re-parse this mod
                new_entries = parse_mod_stat_entries(mod_path, mod_name)
                entries.extend(new_entries)
                cached_mtimes[mod_name] = current_mtime

        # Check for deleted mods
        deleted_mods = set(cached_mtimes.keys()) - set(current_mods.keys())
        if deleted_mods:
            needs_update = True
            for m in deleted_mods:
                del cached_mtimes[m]
                entries = [e for e in entries if e["mod"] != m]

        if needs_update:
            cached_data = {
                "version": 1,
                "last_updated": time.time(),
                "mod_mtimes": cached_mtimes,
                "entries": entries,
            }
            cache_file.write_text(json.dumps(cached_data, indent=2), encoding="utf-8")

        return entries

    # Full rebuild
    all_entries = []
    mod_mtimes = {}

    for mod_name, mod_path in current_mods.items():
        mod_mtimes[mod_name] = mod_path.stat().st_mtime
        mod_entries = parse_mod_stat_entries(mod_path, mod_name)
        all_entries.extend(mod_entries)

    payload = {
        "version": 1,
        "last_updated": time.time(),
        "mod_mtimes": mod_mtimes,
        "entries": all_entries,
    }
    cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return all_entries


def filter_entries(
    entries: list[dict],
    slot: str | None = None,
    boost: str | None = None,
    passive: str | None = None,
    search: str | None = None,
    rarity: str | None = None,
    mod_filter: str | None = None,
    limit: int = 50,
) -> list[dict]:
    results = []

    slot_query = slot.strip().lower() if slot else None
    boost_query = boost.strip().lower() if boost else None
    passive_query = passive.strip().lower() if passive else None
    search_query = search.strip().lower() if search else None
    rarity_query = rarity.strip().lower() if rarity else None
    mod_query = mod_filter.strip().lower() if mod_filter else None

    for entry in entries:
        if mod_query and mod_query not in entry["mod"].lower():
            continue

        if slot_query and slot_query not in entry["slot"].lower():
            continue

        if rarity_query and rarity_query != entry["rarity"].lower():
            continue

        if boost_query and boost_query not in entry["boosts"].lower():
            continue

        if passive_query and passive_query not in entry["passives"].lower():
            continue

        if search_query:
            haystack = (
                f"{entry['id']} {entry['display_name']} {entry['description']} "
                f"{entry['boosts']} {entry['passives']} {entry['slot']}"
            ).lower()
            if search_query not in haystack:
                continue

        results.append(entry)
        if len(results) >= limit:
            break

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="High-speed BiS gear, spell, and mechanics database query engine."
    )
    parser.add_argument("search_pos", nargs="?", help="General search term across name, description, boosts, and passives (positional).")
    parser.add_argument("--search", dest="search_flag", help="General search term across name, description, boosts, and passives.")
    parser.add_argument("--slot", help="Filter by equipment slot (e.g. Amulet, Ring, Boots, Weapon, Cloak).")
    parser.add_argument("--boost", help="Filter by boost effect (e.g. SpellSaveDC, AC, CriticalHit, Necrotic).")
    parser.add_argument("--passive", help="Filter by passive effect (e.g. ExtraAttack, Lifedrinker).")
    parser.add_argument("--rarity", help="Filter by item rarity (e.g. Rare, VeryRare, Legendary).")
    parser.add_argument("--mod", help="Filter by mod slug/name in mods/.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results to display (default: 10).")
    parser.add_argument("--compact", action="store_true", help="Output compact records omitting raw file paths and empty fields.")
    parser.add_argument("--reindex", action="store_true", help="Force a complete rebuild of the mod database cache index.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")

    args = parser.parse_args()

    t0 = time.perf_counter()
    entries = build_or_load_index(force_reindex=args.reindex)
    load_time_ms = (time.perf_counter() - t0) * 1000

    search_query = args.search_flag or args.search_pos
    results = filter_entries(
        entries=entries,
        slot=args.slot,
        boost=args.boost,
        passive=args.passive,
        search=search_query,
        rarity=args.rarity,
        mod_filter=args.mod,
        limit=args.limit,
    )

    if args.json:
        if args.compact:
            clean_results = []
            for r in results:
                cr = {
                    "id": r.get("id"),
                    "display_name": r.get("display_name"),
                    "slot": r.get("slot"),
                    "rarity": r.get("rarity"),
                    "mod": r.get("mod"),
                    "boosts": r.get("boosts"),
                    "passives": r.get("passives"),
                }
                if r.get("damage"):
                    cr["damage"] = r["damage"]
                if r.get("damage_type"):
                    cr["damage_type"] = r["damage_type"]
                if r.get("ac"):
                    cr["ac"] = r["ac"]
                clean_results.append(cr)
            out_results = clean_results
        else:
            out_results = results

        print(json.dumps({
            "count": len(out_results),
            "total_indexed": len(entries),
            "load_time_ms": round(load_time_ms, 2),
            "results": out_results,
        }, indent=2))
        return 0


    print(f"BG3 Community Mod Database ({len(entries)} indexed entries, loaded in {load_time_ms:.1f}ms)")
    print("=" * 80)

    if not results:
        print("No matching equipment or mechanics found for the given criteria.")
        return 0

    for idx, r in enumerate(results, start=1):
        rarity_str = f"[{r['rarity']}]" if r['rarity'] else ""
        print(f"{idx}. {r['display_name']} ({r['id']}) {rarity_str}")
        print(f"   Slot: {r['slot']:<12} Mod: {r['mod']}")
        if r['boosts']:
            print(f"   Boosts: {r['boosts']}")
        if r['passives']:
            print(f"   Passives: {r['passives']}")
        if r['damage']:
            print(f"   Damage: {r['damage']} {r.get('damage_type', '')}")
        if r['ac']:
            print(f"   Armor Class: {r['ac']}")
        if r['description']:
            print(f"   Description: {r['description']}")
        print()

    return ExitCode.OK


if __name__ == "__main__":
    sys.exit(main())
