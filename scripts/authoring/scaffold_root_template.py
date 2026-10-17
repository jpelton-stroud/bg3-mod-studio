#!/usr/bin/env python3
"""
scaffold_root_template.py - Binds stat entries to physical 3D in-game RootTemplates in _merged.lsx.

Creates standard Larian GameObjects nodes linking 3D visual models, physics,
audio, and localized string handles directly to custom Weapon/Armor/Object stats.
"""

import argparse
import json
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.lib.cli_common import ConsoleColor, ExitCode

VISUAL_PRESETS = {
    "greatsword": {
        "uuid": "2798c9f8-b06b-44d4-9d6c-e6d98a66329a",
        "description": "Standard 2H Greatsword mesh",
        "icon": "Item_WPN_HUM_Greatsword_A_0",
    },
    "longsword": {
        "uuid": "1865323f-b428-4791-a0a1-478875024763",
        "description": "Standard 1H Longsword mesh",
        "icon": "Item_WPN_HUM_Longsword_A_0",
    },
    "dagger": {
        "uuid": "569b0f3d-abcd-4b01-aa0b-32d0fc18002d",
        "description": "Standard Dagger mesh",
        "icon": "Item_WPN_HUM_Dagger_A_0",
    },
    "shortbow": {
        "uuid": "a461e63d-4b9a-4160-b886-5b6863643d24",
        "description": "Standard Shortbow mesh",
        "icon": "Item_WPN_HUM_Shortbow_A_0",
    },
    "staff": {
        "uuid": "2fa18ee4-90df-4c0f-8596-8a6669bc06fb",
        "description": "Quarterstaff / Magic Staff mesh",
        "icon": "Item_WPN_HUM_Quarterstaff_A_0",
    },
    "plate": {
        "uuid": "96d66e76-35ae-493f-8012-e8a8a3a0e69a",
        "description": "Heavy Plate Armor body mesh",
        "icon": "Item_ARM_Plate_Body",
    },
    "leather": {
        "uuid": "a61a9914-7235-4ac5-8063-36473cc1dd9d",
        "description": "Light Leather / Padded body mesh",
        "icon": "Item_ARM_Padded_Body",
    },
    "robe": {
        "uuid": "16867d7f-9047-4959-b13c-c672b14193b2",
        "description": "Spellcaster Robe body mesh",
        "icon": "Item_ARM_Robe_Body",
    },
    "helmet": {
        "uuid": "362c6f56-ce20-41df-811f-47356ba1bb00",
        "description": "Standard Helmet / Headgear mesh",
        "icon": "Item_ARM_Helmet",
    },
    "boots": {
        "uuid": "33eb2212-eb7e-4029-9e8d-80674f762696",
        "description": "Standard Boots mesh",
        "icon": "Item_ARM_Boots",
    },
    "gloves": {
        "uuid": "896f8a20-7299-456e-95aa-b2b0ec64ff38",
        "description": "Standard Gloves / Gauntlets mesh",
        "icon": "Item_ARM_Gloves",
    },
    "cloak": {
        "uuid": "d68e5470-36e6-424a-b5f7-640f0980a373",
        "description": "Standard Cloak mesh",
        "icon": "Item_ARM_Cloak",
    },
    "amulet": {
        "uuid": "20612f0e-2dae-45c1-8398-94840a6af489",
        "description": "Amulet / Necklace jewelry mesh",
        "icon": "Item_ARM_Amulet",
    },
    "ring": {
        "uuid": "359f2ebc-37fe-4f8e-835f-ac894ecdcf96",
        "description": "Ring jewelry mesh",
        "icon": "Item_ARM_Ring",
    },
    "backpack": {
        "uuid": "054238e2-c513-4ae3-b7c1-d41c120281b3",
        "description": "Container / Backpack mesh",
        "icon": "Item_LOOT_GEN_Backpack_A",
    },
}

EMPTY_ROOT_TEMPLATES_LSX = """<?xml version="1.0" encoding="utf-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Templates">
        <node id="Templates">
            <children>
            </children>
        </node>
    </region>
</save>
"""


from scripts.lib.env_paths import MY_MODS_DIR, resolve_mod_dir


def resolve_mod_directories(mod_path_or_slug: str, workspace_root: Path) -> tuple[Path, Path, str]:
    candidate = resolve_mod_dir(mod_path_or_slug, prefer_my_mods=True)
    if candidate is None or not candidate.is_dir():
        raise FileNotFoundError(f"Mod directory not found: '{mod_path_or_slug}'")

    public_dir = candidate / "Public"
    if not public_dir.is_dir():
        raise FileNotFoundError(f"Missing 'Public/' in mod: '{candidate}'")

    subdirs = [d for d in public_dir.iterdir() if d.is_dir() and d.name != "Shared"]
    if not subdirs:
        raise FileNotFoundError(f"No mod folder found under '{public_dir}'")

    return candidate, subdirs[0], candidate.name


def link_stat_root_template(mod_dir: Path, stat_name: str, map_key: str, dry_run: bool = False) -> str | None:
    """Injects or updates data "RootTemplate" "<map_key>" in the item's stat block."""
    stats_root = mod_dir / "Public"
    if not stats_root.is_dir():
        return None

    for txt_file in sorted(stats_root.rglob("*.txt")):
        try:
            content = txt_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        pattern = rf'(new\s+entry\s+"{re.escape(stat_name)}"\s*\n(?:(?!new\s+entry\s+").*\n?)*)'
        m = re.search(pattern, content, re.IGNORECASE)
        if not m:
            continue

        block = m.group(1)
        rt_pattern = r'(data\s+"RootTemplate"\s+")([^"]*)(")'
        if re.search(rt_pattern, block, re.IGNORECASE):
            new_block = re.sub(rt_pattern, rf'\g<1>{map_key}\g<3>', block, count=1, flags=re.IGNORECASE)
        else:
            stripped_block = block.rstrip("\n")
            new_block = f'{stripped_block}\ndata "RootTemplate" "{map_key}"\n'

        if new_block != block and not dry_run:
            new_content = content[: m.start(1)] + new_block + content[m.end(1) :]
            txt_file.write_text(new_content, encoding="utf-8")
        return str(txt_file)
    return None


def lookup_stat_handles(mod_dir: Path, stat_name: str) -> tuple[str, str]:
    """Finds DisplayName and Description string handles in Stats files for the given stat."""
    display_handle = ""
    desc_handle = ""

    stats_dir = mod_dir / "Public"
    for txt_file in stats_dir.rglob("*.txt"):
        try:
            content = txt_file.read_text(encoding="utf-8", errors="replace")
            # Find entry block
            pattern = rf'new\s+entry\s+"{re.escape(stat_name)}"'
            m = re.search(pattern, content, re.IGNORECASE)
            if not m:
                continue

            # Parse lines of this entry until next entry or EOF
            block = content[m.start():]
            end_match = re.search(r'\nnew\s+entry\s+"', block[1:])
            if end_match:
                block = block[:end_match.start() + 1]

            for line in block.splitlines():
                line = line.strip()
                dm = re.match(r'data\s+"DisplayName"\s+"([^"]+)"', line, re.IGNORECASE)
                if dm:
                    raw = dm.group(1).split(";")[0]
                    display_handle = raw
                dem = re.match(r'data\s+"Description"\s+"([^"]+)"', line, re.IGNORECASE)
                if dem:
                    raw = dem.group(1).split(";")[0]
                    desc_handle = raw
        except Exception:
            continue

    return display_handle, desc_handle


def prettify_xml_element(elem: ET.Element) -> str:
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty = reparsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")
    lines = [line for line in pretty.splitlines() if line.strip()]
    return "\n".join(lines) + "\n"


def scaffold_root_template_node(
    templates_file: Path,
    item_stat_name: str,
    parent_template_uuid: str,
    display_handle: str = "",
    desc_handle: str = "",
    icon: str = "",
    dry_run: bool = False,
) -> dict:
    if templates_file.exists():
        content = templates_file.read_text(encoding="utf-8")
        tree = ET.fromstring(content)
    else:
        tree = ET.fromstring(EMPTY_ROOT_TEMPLATES_LSX)

    templates_node = tree.find(".//region[@id='Templates']/node[@id='Templates']")
    if templates_node is None:
        raise ValueError("Malformed _merged.lsx: missing Templates node.")

    children = templates_node.find("children")
    if children is None:
        children = ET.SubElement(templates_node, "children")

    root_name = item_stat_name if item_stat_name.startswith("I_") else f"I_{item_stat_name}"

    # Check if a template for this item already exists
    existing = None
    for go in children.findall("node[@id='GameObjects']"):
        s_attr = go.find("attribute[@id='Stats']")
        if s_attr is not None and s_attr.get("value") == item_stat_name:
            existing = go
            break

    action = "updated" if existing is not None else "created"
    node = existing if existing is not None else ET.SubElement(children, "node", id="GameObjects")

    map_key = str(uuid.uuid4()) if existing is None else node.find("attribute[@id='MapKey']").get("value")

    def set_attr(attr_id: str, attr_type: str, val: str, extra_attrs: dict = None):
        cur = node.find(f"attribute[@id='{attr_id}']")
        if cur is None:
            cur = ET.SubElement(node, "attribute", id=attr_id, type=attr_type)
        cur.set("type", attr_type)
        if extra_attrs:
            for k, v in extra_attrs.items():
                cur.set(k, v)
        if val is not None:
            cur.set("value", val)

    if desc_handle:
        set_attr("Description", "TranslatedString", None, {"handle": desc_handle, "version": "1"})
    if display_handle:
        set_attr("DisplayName", "TranslatedString", None, {"handle": display_handle, "version": "1"})

    set_attr("Icon", "FixedString", icon or "Item_LOOT_GEN_Backpack_A")
    set_attr("LevelName", "FixedString", "")
    set_attr("MapKey", "FixedString", map_key)
    set_attr("Name", "LSString", root_name)
    set_attr("ParentTemplateId", "FixedString", parent_template_uuid)
    set_attr("Stats", "FixedString", item_stat_name)
    set_attr("Type", "FixedString", "item")
    set_attr("_OriginalFileVersion_", "int64", "144115188075855912")

    if not dry_run:
        templates_file.parent.mkdir(parents=True, exist_ok=True)
        templates_file.write_text(prettify_xml_element(tree), encoding="utf-8")

    return {
        "action": action,
        "item_name": item_stat_name,
        "root_template_name": root_name,
        "map_key": map_key,
        "parent_template_id": parent_template_uuid,
        "display_handle": display_handle,
        "description_handle": desc_handle,
        "icon": icon,
        "file": str(templates_file),
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Bind stat entries to in-game 3D RootTemplates in Public/<Mod>/RootTemplates/_merged.lsx."
    )
    parser.add_argument("--mod", required=True, help="Mod name/slug in my_mods/ or directory path.")
    parser.add_argument("--item", required=True, help="Stat entry name from Weapon.txt, Armor.txt, or Object.txt.")
    parser.add_argument(
        "--visual-preset",
        choices=list(VISUAL_PRESETS.keys()),
        help=f"Standard 3D visual mesh preset ({', '.join(VISUAL_PRESETS.keys())}).",
    )
    parser.add_argument("--parent-template", help="Custom ParentTemplateId GUID override.")
    parser.add_argument("--display-handle", help="DisplayName handle (e.g. h...;1). Defaults to auto-lookup.")
    parser.add_argument("--description-handle", help="Description handle (e.g. h...;1). Defaults to auto-lookup.")
    parser.add_argument("--icon", help="Icon resource name (e.g. Item_WPN_HUM_Greatsword_A_0).")
    parser.add_argument("--no-link-stat", action="store_true", help="Do not automatically write data \"RootTemplate\" back into the stat entry.")
    parser.add_argument("--list-presets", action="store_true", help="List available visual presets and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without modifying files.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")

    args = parser.parse_args()

    if args.list_presets:
        if args.json:
            print(json.dumps(VISUAL_PRESETS, indent=2))
        else:
            print("Available 3D Visual Mesh Presets:")
            print("-" * 75)
            for k, v in VISUAL_PRESETS.items():
                print(f"  {k:<14} -> {v['uuid']} ({v['description']})")
        return 0

    workspace_root = Path(__file__).resolve().parents[2]

    try:
        mod_dir, public_mod_dir, mod_slug = resolve_mod_directories(args.mod, workspace_root)
        templates_file = public_mod_dir / "RootTemplates" / "_merged.lsx"

        # Determine ParentTemplate UUID and Icon
        parent_uuid = args.parent_template
        icon = args.icon

        if args.visual_preset:
            preset_data = VISUAL_PRESETS[args.visual_preset]
            if not parent_uuid:
                parent_uuid = preset_data["uuid"]
            if not icon:
                icon = preset_data["icon"]

        if not parent_uuid:
            # Fallback to general object
            parent_uuid = VISUAL_PRESETS["backpack"]["uuid"]
            if not icon:
                icon = VISUAL_PRESETS["backpack"]["icon"]

        # Lookup handles if not explicitly supplied
        disp_h = args.display_handle or ""
        desc_h = args.description_handle or ""
        if not disp_h or not desc_h:
            found_disp, found_desc = lookup_stat_handles(mod_dir, args.item)
            if not disp_h:
                disp_h = found_disp
            if not desc_h:
                desc_h = found_desc

        result = scaffold_root_template_node(
            templates_file=templates_file,
            item_stat_name=args.item,
            parent_template_uuid=parent_uuid,
            display_handle=disp_h,
            desc_handle=desc_h,
            icon=icon,
            dry_run=args.dry_run,
        )
        result["mod"] = mod_slug
        linked_stat_file = None
        if not args.no_link_stat:
            linked_stat_file = link_stat_root_template(
                mod_dir=mod_dir,
                stat_name=args.item,
                map_key=result["map_key"],
                dry_run=args.dry_run,
            )
        result["linked_stat_file"] = linked_stat_file

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            dry_str = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status_tag = color.green("[✓]")
            print(f"{status_tag} Successfully {result['action']} RootTemplate for '{args.item}'{dry_str}:")
            print(f"    Target File: {result['file']}")
            print(f"    MapKey (UUID): {result['map_key']}")
            print(f"    RootTemplate Name: {result['root_template_name']}")
            print(f"    ParentTemplateId: {result['parent_template_id']}")
            if result["icon"]:
                print(f"    Icon: {result['icon']}")

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
