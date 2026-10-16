#!/usr/bin/env python3
"""
inject_treasure_table.py - Injects custom mod items into BG3 treasure tables and vendor inventories.

Mod items can be merged into standard in-game drop containers (Tutorial Chest,
Camp Chest, vendors) via TreasureTable.txt subtable merges without requiring
script extender hooks.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

CONTAINER_ALIASES = {
    "tutorial_chest": {
        "table": "TUT_Chest_Potions",
        "description": "Tutorial Chest on the Nautiloid (Prologue)",
    },
    "camp_chest": {
        "table": "CAMP_Chest_Supplies",
        "description": "Camp Supply Chest (Available at any camp)",
    },
    "vendor_arron": {
        "table": "DEN_Entrance_Merchant",
        "description": "Arron (Druid Grove entrance vendor)",
    },
    "vendor_dammon": {
        "table": "DEN_Blacksmith",
        "description": "Dammon the Infernal Blacksmith (Druid Grove / Last Light)",
    },
    "vendor_mattis": {
        "table": "DEN_Thieflings_Mattis",
        "description": "Mattis (Tiefling child vendor in Druid Grove)",
    },
    "vendor_roah": {
        "table": "GOB_Roah",
        "description": "Roah Moonglow (Zhentarim trader in Shattered Sanctum)",
    },
    "vendor_derryth": {
        "table": "UND_Derryth",
        "description": "Derryth Bonecloak (Underdark Myconid Colony)",
    },
    "vendor_blurg": {
        "table": "UND_SocietyOfBrilliance_Blurg",
        "description": "Blurg (Society of Brilliance in Myconid Colony)",
    },
    "vendor_quartermaster_talli": {
        "table": "HAV_Quartermaster",
        "description": "Quartermaster Talli (Last Light Inn)",
    },
}

STANDARD_HEADER = 'treasure itemtypes "Common","Uncommon","Rare","Epic","Legendary","Divine","Unique"\n'


if __package__:
    from .lib.env_paths import MY_MODS_DIR, resolve_mod_dir
else:
    from lib.env_paths import MY_MODS_DIR, resolve_mod_dir


def resolve_mod_stats_dir(mod_path_or_slug: str, workspace_root: Path) -> tuple[Path, str]:
    """Resolves target mod and its Public/<ModFolder>/Stats/Generated/Data directory."""
    candidate = resolve_mod_dir(mod_path_or_slug, prefer_my_mods=True)
    if candidate is None or not candidate.is_dir():
        raise FileNotFoundError(f"Mod directory not found: '{mod_path_or_slug}'")

    public_dir = candidate / "Public"
    if not public_dir.is_dir():
        raise FileNotFoundError(f"Missing 'Public/' directory in mod: '{candidate}'")

    # Find mod content directory inside Public/
    subdirs = [d for d in public_dir.iterdir() if d.is_dir() and d.name != "Shared"]
    if not subdirs:
        raise FileNotFoundError(f"No mod folder found under '{public_dir}'")

    mod_folder = subdirs[0]
    data_dir = mod_folder / "Stats" / "Generated" / "Data"
    return data_dir, candidate.name


def format_item_name(item: str, ensure_prefix: bool = True) -> str:
    """Formats the item name, ensuring standard 'I_' prefix if needed."""
    item = item.strip()
    if ensure_prefix and not item.startswith("I_") and not item.startswith("OBJ_"):
        return f"I_{item}"
    return item


def inject_into_treasure_table(
    table_file: Path,
    table_id: str,
    item_category: str,
    count: int = 1,
    subtable_ratio: str = "1,1",
    start_level: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Injects an item entry into TreasureTable.txt."""
    existed = table_file.exists()
    content = table_file.read_text(encoding="utf-8") if existed else ""

    item_line = f'object category "{item_category}",{count},0,0,0,0,0,0,0'

    # Check if this item is already present in this table
    pattern = rf'new treasuretable\s+"{re.escape(table_id)}"'
    has_table = bool(re.search(pattern, content, re.IGNORECASE))

    if has_table:
        # Check if item is already in content
        if item_line in content:
            return {
                "status": "already_present",
                "table": table_id,
                "item": item_category,
                "file": str(table_file),
                "modified": False,
            }

        # Append a mergeable block (CanMerge 1)
        block = f'\nnew treasuretable "{table_id}"\nCanMerge 1\nnew subtable "{subtable_ratio}"\n'
        if start_level is not None:
            block += f'StartLevel "{start_level}"\n'
        block += f"{item_line}\n"

        new_content = content.rstrip() + "\n" + block
    else:
        # New table entry
        block = ""
        if not content.strip():
            block += STANDARD_HEADER + "\n"
        block += f'new treasuretable "{table_id}"\n'
        block += "CanMerge 1\n"
        block += f'new subtable "{subtable_ratio}"\n'
        if start_level is not None:
            block += f'StartLevel "{start_level}"\n'
        block += f"{item_line}\n"

        new_content = content.rstrip() + ("\n\n" if content.strip() else "") + block

    if not dry_run:
        table_file.parent.mkdir(parents=True, exist_ok=True)
        table_file.write_text(new_content, encoding="utf-8")

    return {
        "status": "injected",
        "table": table_id,
        "item": item_category,
        "count": count,
        "subtable_ratio": subtable_ratio,
        "start_level": start_level,
        "file": str(table_file),
        "modified": True,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Inject custom mod items into BG3 treasure tables and vendor inventories."
    )
    parser.add_argument("--mod", help="Target mod name/slug in my_mods/ or directory path.")
    parser.add_argument("--item", help="Item identifier (e.g. MAG_Sword_01 or I_MAG_Sword_01).")
    parser.add_argument(
        "--container",
        help="Container alias (e.g. tutorial_chest, camp_chest, vendor_arron) or raw table ID.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Quantity to drop per subtable roll (default: 1).",
    )
    parser.add_argument(
        "--ratio",
        default="1,1",
        help="Subtable roll ratio (default: '1,1' for 100%% drop chance).",
    )
    parser.add_argument(
        "--start-level",
        type=int,
        default=None,
        help="Optional minimum character level for item to appear in container/vendor.",
    )
    parser.add_argument(
        "--raw-item-name",
        action="store_true",
        help="Do not automatically prepend 'I_' to the item name.",
    )
    parser.add_argument(
        "--list-containers",
        action="store_true",
        help="List available container aliases and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying TreasureTable.txt.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON for agent and tooling integration.",
    )

    args = parser.parse_args()

    if args.list_containers:
        if args.json:
            print(json.dumps(CONTAINER_ALIASES, indent=2))
        else:
            print("Available Container & Vendor Aliases:")
            print("-" * 65)
            for alias, info in CONTAINER_ALIASES.items():
                print(f"  {alias:<26} -> {info['table']:<28} ({info['description']})")
        return 0

    if not args.mod or not args.item:
        parser.error("--mod and --item are required unless using --list-containers.")

    container_key = (args.container or "tutorial_chest").lower()
    table_id = CONTAINER_ALIASES.get(container_key, {}).get("table", args.container or "TUT_Chest_Potions")

    workspace_root = Path(__file__).resolve().parent.parent

    try:
        data_dir, mod_name = resolve_mod_stats_dir(args.mod, workspace_root)
        table_file = data_dir / "TreasureTable.txt"
        formatted_item = format_item_name(args.item, ensure_prefix=not args.raw_item_name)

        result = inject_into_treasure_table(
            table_file=table_file,
            table_id=table_id,
            item_category=formatted_item,
            count=args.count,
            subtable_ratio=args.ratio,
            start_level=args.start_level,
            dry_run=args.dry_run,
        )
        result["mod"] = mod_name

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["status"] == "already_present":
                print(f"[-] Item '{result['item']}' is already present in table '{result['table']}' in {table_file}.")
            else:
                dry_tag = " [DRY-RUN]" if args.dry_run else ""
                print(f"[✓] Successfully injected item '{result['item']}' into '{result['table']}' ({table_file}){dry_tag}")
        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
