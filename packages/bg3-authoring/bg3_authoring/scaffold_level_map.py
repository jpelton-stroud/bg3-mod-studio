#!/usr/bin/env python3
"""
scaffold_level_map.py - Scaffolds Larian Patch 8 LevelMapValues schemas.

Generates Public/<ModFolder>/LevelMapValues/LevelMapValues.lsx for scaling dice, charges,
and damage values across levels 1–20.
"""

import argparse
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import resolve_mod_dir

EMPTY_LEVEL_MAP_VALUES_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="LevelMapValues">
        <node id="root">
            <children>
            </children>
        </node>
    </region>
</save>
"""


def prettify_xml(element: ET.Element) -> str:
    rough = ET.tostring(element, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    clean = "\n".join([line for line in reparsed.toprettyxml(indent="    ").split("\n") if line.strip()])
    return clean + "\n"


def resolve_mod_paths(mod_name_or_path: str, workspace_root: Path | None = None) -> tuple[Path, Path, str]:
    candidate = resolve_mod_dir(mod_name_or_path, prefer_my_mods=True)
    if candidate is None or not candidate.is_dir():
        raise FileNotFoundError(f"Mod directory not found: '{mod_name_or_path}'")

    public_dir = candidate / "Public"
    if not public_dir.is_dir():
        raise FileNotFoundError(f"Missing 'Public/' directory in mod: '{candidate}'")

    subdirs = [d for d in public_dir.iterdir() if d.is_dir() and d.name != "Shared"]
    if not subdirs:
        raise FileNotFoundError(f"No mod folder found under '{public_dir}'")

    return candidate, subdirs[0], candidate.name


def parse_level_mappings(levels_str: str) -> dict[int, str]:
    """
    Parses level mapping strings like '1=1d6,3=2d6,5=3d6' or '1=1;5=2;9=3'
    and forward-fills values across all levels 1 to 20.
    """
    explicit: dict[int, str] = {}
    tokens = re.split(r"[,;]\s*", levels_str.strip())
    for token in tokens:
        if not token:
            continue
        if "=" in token:
            lvl_str, val = token.split("=", 1)
            lvl = int(lvl_str.strip())
            explicit[lvl] = val.strip()

    if not explicit:
        raise ValueError("No valid level mappings found in format 'level=value' (e.g. '1=1d6,5=2d6').")

    # Forward-fill levels 1 to 20
    resolved: dict[int, str] = {}
    current_val = explicit.get(1, list(explicit.values())[0])
    for lvl in range(1, 21):
        if lvl in explicit:
            current_val = explicit[lvl]
        resolved[lvl] = current_val

    return resolved


def detect_dice_type(resolved_levels: dict[int, str]) -> int:
    for val in resolved_levels.values():
        match = re.search(r"d(\d+)", val, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def scaffold_level_map(
    mod_name_or_path: str,
    name: str,
    levels: str,
    preferred_dice_type: int | None = None,
    level_map_uuid: str | None = None,
    dry_run: bool = False,
) -> dict:
    mod_root, mod_folder_dir, mod_slug = resolve_mod_paths(mod_name_or_path)

    lm_dir = mod_folder_dir / "LevelMapValues"
    lm_file = lm_dir / "LevelMapValues.lsx"

    allocated_uuid = level_map_uuid.strip() if level_map_uuid else str(uuid.uuid4())
    resolved_levels = parse_level_mappings(levels)
    dice_type = preferred_dice_type if preferred_dice_type is not None else detect_dice_type(resolved_levels)

    if lm_file.exists():
        tree = ET.parse(lm_file)
        root = tree.getroot()
    else:
        root = ET.fromstring(EMPTY_LEVEL_MAP_VALUES_LSX)

    children = root.find(".//node[@id='root']/children")
    if children is None:
        r_node = root.find(".//node[@id='root']")
        if r_node is None:
            reg = root.find(".//region[@id='LevelMapValues']")
            if reg is None:
                reg = ET.SubElement(root, "region", id="LevelMapValues")
            r_node = ET.SubElement(reg, "node", id="root")
        children = ET.SubElement(r_node, "children")

    # Check for existing node with same Name or UUID
    existing_node = None
    for lnode in children.findall("./node[@id='LevelMapSeries']"):
        for attr in lnode.findall("./attribute"):
            if (attr.get("id") == "Name" and attr.get("value") == name) or (attr.get("id") == "UUID" and attr.get("value") == allocated_uuid):
                existing_node = lnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        children.remove(existing_node)

    series_node = ET.SubElement(children, "node", id="LevelMapSeries")
    for lvl in range(1, 21):
        ET.SubElement(series_node, "attribute", id=f"Level{lvl}", type="LSString", value=resolved_levels[lvl])
    ET.SubElement(series_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(series_node, "attribute", id="PreferredDiceType", type="uint32", value=str(dice_type))
    ET.SubElement(series_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        lm_dir.mkdir(parents=True, exist_ok=True)
        lm_file.write_text(prettify_xml(root), encoding="utf-8")

    return {
        "success": True,
        "mod": mod_slug,
        "name": name,
        "uuid": allocated_uuid,
        "preferred_dice_type": dice_type,
        "levels": resolved_levels,
        "file": str(lm_file),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 LevelMapValues scaling curves across levels 1–20.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--name", required=True, help="Internal curve name (e.g. SneakAttack, ShadowDice)")
    parser.add_argument("--levels", required=True, help="Level mappings (e.g. '1=1d6,3=2d6,5=3d6' or '1=1,5=2,9=3')")
    parser.add_argument("--dice-type", type=int, help="Override preferred dice type (0, 4, 6, 8, 10, 12)")
    parser.add_argument("--uuid", help="Explicit UUID for this level map")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_level_map(
            mod_name_or_path=args.mod,
            name=args.name,
            levels=args.levels,
            preferred_dice_type=args.dice_type,
            level_map_uuid=args.uuid,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded level map '{args.name}'{tag}:")
            print(f"    UUID: {res['uuid']}")
            print(f"    Dice Type: {res['preferred_dice_type']}")
            print(f"    Level 1: {res['levels'][1]} -> Level 20: {res['levels'][20]}")
            print(f"    File: {res['file']}")
        return ExitCode.SUCCESS

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            err_color = ConsoleColor(stream=sys.stderr)
            print(f"{err_color.red('[ERROR]')} {e}", file=sys.stderr)
        return ExitCode.GENERAL


if __name__ == "__main__":
    sys.exit(main())
