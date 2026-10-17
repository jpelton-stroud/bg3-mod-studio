#!/usr/bin/env python3
"""
scaffold_spell_list.py - Scaffolds Larian Patch 8 SpellLists.lsx and PassiveLists.lsx.

Generates standalone selector lists in Public/<ModFolder>/Lists/ for progression nodes,
feats, and class descriptions.
"""

import argparse
import json
import os
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.lib.cli_common import ConsoleColor, ExitCode
from scripts.lib.env_paths import resolve_mod_dir
from scripts.lib.larian_parsers import PATCH_8_VERSION, split_larian_items

EMPTY_SPELL_LISTS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="SpellLists">
        <node id="root">
            <children>
            </children>
        </node>
    </region>
</save>
"""

EMPTY_PASSIVE_LISTS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="PassiveLists">
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


def resolve_mod_paths(mod_name_or_path: str, workspace_root: Path) -> tuple[Path, Path, str]:
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


def scaffold_list(
    mod_name_or_path: str,
    list_type: str = "spells",
    comment: str | None = None,
    items: str | None = None,
    list_uuid: str | None = None,
    dry_run: bool = False,
) -> dict:
    workspace_root = Path(__file__).resolve().parents[2]
    mod_root, mod_folder_dir, mod_slug = resolve_mod_paths(mod_name_or_path, workspace_root)

    lists_dir = mod_folder_dir / "Lists"
    is_passive = (list_type.lower() == "passives" or list_type.lower() == "passive")
    target_file = lists_dir / ("PassiveLists.lsx" if is_passive else "SpellLists.lsx")
    empty_template = EMPTY_PASSIVE_LISTS_LSX if is_passive else EMPTY_SPELL_LISTS_LSX
    region_id = "PassiveLists" if is_passive else "SpellLists"
    node_id = "PassiveList" if is_passive else "SpellList"
    item_attr = "Passives" if is_passive else "Spells"

    allocated_uuid = list_uuid.strip() if list_uuid else str(uuid.uuid4())
    parsed_items = split_larian_items(items) if items else []
    items_str = ";".join(parsed_items)
    comment_str = comment if comment else f"Custom {region_id} entry"

    if target_file.exists():
        tree = ET.parse(target_file)
        root = tree.getroot()
    else:
        root = ET.fromstring(empty_template)

    children = root.find(".//node[@id='root']/children")
    if children is None:
        r_node = root.find(".//node[@id='root']")
        if r_node is None:
            reg = root.find(f".//region[@id='{region_id}']")
            if reg is None:
                reg = ET.SubElement(root, "region", id=region_id)
            r_node = ET.SubElement(reg, "node", id="root")
        children = ET.SubElement(r_node, "children")

    # Check for existing node with same Comment or UUID
    existing_node = None
    for lnode in children.findall(f"./node[@id='{node_id}']"):
        for attr in lnode.findall("./attribute"):
            if (attr.get("id") == "UUID" and attr.get("value") == allocated_uuid) or (comment and attr.get("id") == "Comment" and attr.get("value") == comment):
                existing_node = lnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        children.remove(existing_node)

    list_node = ET.SubElement(children, "node", id=node_id)
    ET.SubElement(list_node, "attribute", id="Comment", type="LSString", value=comment_str)
    ET.SubElement(list_node, "attribute", id=item_attr, type="LSString", value=items_str)
    ET.SubElement(list_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        lists_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(prettify_xml(root), encoding="utf-8")

    return {
        "success": True,
        "mod": mod_slug,
        "type": "passives" if is_passive else "spells",
        "uuid": allocated_uuid,
        "comment": comment_str,
        "items": parsed_items,
        "file": str(target_file),
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 SpellLists.lsx and PassiveLists.lsx selector lists.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--comment", help="Documentation label/comment for the list")
    parser.add_argument("--spells", help="Comma- or semicolon-separated spell names (creates/updates SpellLists.lsx)")
    parser.add_argument("--passives", help="Comma- or semicolon-separated passive names (creates/updates PassiveLists.lsx)")
    parser.add_argument("--uuid", help="Explicit UUID for this list")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        if args.passives and not args.spells:
            list_type = "passives"
            items = args.passives
        else:
            list_type = "spells"
            items = args.spells

        res = scaffold_list(
            mod_name_or_path=args.mod,
            list_type=list_type,
            comment=args.comment,
            items=items,
            list_uuid=args.uuid,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded {res['type']} list{tag}:")
            print(f"    UUID: {res['uuid']}")
            print(f"    Comment: {res['comment']}")
            print(f"    Items ({len(res['items'])}): {', '.join(res['items'])}")
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
