#!/usr/bin/env python3
"""
scaffold_action_resource.py - Scaffolds Larian Patch 8 ActionResourceDefinitions schemas.

Generates:
1. Public/<ModFolder>/ActionResourceDefinitions/ActionResourceDefinitions.lsx
2. Appends localization handles to Localization/English/<ModName>.xml
"""

import argparse
import json
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import resolve_mod_dir
from bg3_core.larian_parsers import (
    generate_larian_handle,
    update_localization_xml,
)

EMPTY_ACTION_RESOURCES_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="ActionResourceDefinitions">
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


def resolve_mod_paths(mod_name_or_path: str, workspace_root: Path | None = None) -> tuple[Path, Path, Path, str]:
    candidate = resolve_mod_dir(mod_name_or_path, prefer_my_mods=True)
    if candidate is None or not candidate.is_dir():
        raise FileNotFoundError(f"Mod directory not found: '{mod_name_or_path}'")

    public_dir = candidate / "Public"
    if not public_dir.is_dir():
        raise FileNotFoundError(f"Missing 'Public/' directory in mod: '{candidate}'")

    subdirs = [d for d in public_dir.iterdir() if d.is_dir() and d.name != "Shared"]
    if not subdirs:
        raise FileNotFoundError(f"No mod folder found under '{public_dir}'")

    mod_folder_dir = subdirs[0]
    loc_file = candidate / "Localization" / "English" / f"{candidate.name}.xml"
    if not loc_file.exists():
        xml_files = list((candidate / "Localization" / "English").glob("*.xml")) if (candidate / "Localization" / "English").is_dir() else []
        if xml_files:
            loc_file = xml_files[0]

    return candidate, mod_folder_dir, loc_file, candidate.name


def scaffold_action_resource(
    mod_name_or_path: str,
    name: str,
    display_name: str | None = None,
    description: str | None = None,
    replenish_type: str = "ShortRest",
    max_level: int = 0,
    dice_type: int = 0,
    show_on_action_panel: bool = True,
    is_spell_resource: bool = False,
    party_action_resource: bool = False,
    resource_uuid: str | None = None,
    dry_run: bool = False,
) -> dict:
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    res_dir = mod_folder_dir / "ActionResourceDefinitions"
    res_file = res_dir / "ActionResourceDefinitions.lsx"

    allocated_uuid = resource_uuid.strip() if resource_uuid else str(uuid.uuid4())
    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} resource description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    # Load or create ActionResourceDefinitions.lsx
    if res_file.exists():
        res_tree = ET.parse(res_file)
        res_root = res_tree.getroot()
    else:
        res_root = ET.fromstring(EMPTY_ACTION_RESOURCES_LSX)

    res_children = res_root.find(".//node[@id='root']/children")
    if res_children is None:
        r_root_node = res_root.find(".//node[@id='root']")
        if r_root_node is None:
            r_reg = res_root.find(".//region[@id='ActionResourceDefinitions']")
            if r_reg is None:
                r_reg = ET.SubElement(res_root, "region", id="ActionResourceDefinitions")
            r_root_node = ET.SubElement(r_reg, "node", id="root")
        res_children = ET.SubElement(r_root_node, "children")

    # Check for existing node with same Name
    existing_node = None
    for rnode in res_children.findall("./node[@id='ActionResourceDefinition']"):
        for attr in rnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                existing_node = rnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        res_children.remove(existing_node)

    node = ET.SubElement(res_children, "node", id="ActionResourceDefinition")
    ET.SubElement(node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(node, "attribute", id="DiceType", type="uint32", value=str(dice_type))
    ET.SubElement(node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(node, "attribute", id="Error", type="FixedString", value="ActionResourceError_NotEnoughResources")
    ET.SubElement(node, "attribute", id="IsSpellResource", type="bool", value="true" if is_spell_resource else "false")
    ET.SubElement(node, "attribute", id="MaxLevel", type="uint32", value=str(max_level))
    ET.SubElement(node, "attribute", id="MaxValue", type="uint32", value="0")
    ET.SubElement(node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(node, "attribute", id="PartyActionResource", type="bool", value="true" if party_action_resource else "false")
    ET.SubElement(node, "attribute", id="ReplenishType", type="FixedString", value=replenish_type)
    ET.SubElement(node, "attribute", id="ShowOnActionResourcePanel", type="bool", value="true" if show_on_action_panel else "false")
    ET.SubElement(node, "attribute", id="UUID", type="guid", value=allocated_uuid)
    ET.SubElement(node, "attribute", id="UpdatesSpellPowerLevel", type="bool", value="false")

    if not dry_run:
        res_dir.mkdir(parents=True, exist_ok=True)
        res_file.write_text(prettify_xml(res_root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return {
        "success": True,
        "mod": mod_slug,
        "resource_name": name,
        "resource_uuid": allocated_uuid,
        "replenish_type": replenish_type,
        "max_level": max_level,
        "dice_type": dice_type,
        "show_on_action_panel": show_on_action_panel,
        "is_spell_resource": is_spell_resource,
        "display_name_handle": f"{disp_handle};1",
        "description_handle": f"{desc_handle};1",
        "action_resources_file": str(res_file),
        "localization_file": str(loc_file),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 ActionResourceDefinitions with atomic localization registration.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--name", required=True, help="Internal resource name (e.g. ShadowCharge)")
    parser.add_argument("--display-name", help="Display name in UI")
    parser.add_argument("--description", help="Description in tooltip")
    parser.add_argument("--replenish-type", choices=["Rest", "ShortRest", "Never", "Combat"], default="ShortRest", help="Replenish condition (default: ShortRest)")
    parser.add_argument("--max-level", type=int, default=0, help="Maximum resource tier/level (default: 0)")
    parser.add_argument("--dice-type", type=int, default=0, help="Die size if resource uses dice (4, 6, 8, 10, 12, default: 0)")
    parser.add_argument("--show-on-action-panel", action="store_true", default=True, help="Display on action bar resource panel (default: True)")
    parser.add_argument("--hide-from-action-panel", dest="show_on_action_panel", action="store_false", help="Hide from action bar resource panel")
    parser.add_argument("--is-spell-resource", action="store_true", help="Mark as spellcasting resource slot")
    parser.add_argument("--party-resource", action="store_true", help="Mark as shared party resource")
    parser.add_argument("--resource-uuid", help="Explicit UUID for this resource")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_action_resource(
            mod_name_or_path=args.mod,
            name=args.name,
            display_name=args.display_name,
            description=args.description,
            replenish_type=args.replenish_type,
            max_level=args.max_level,
            dice_type=args.dice_type,
            show_on_action_panel=args.show_on_action_panel,
            is_spell_resource=args.is_spell_resource,
            party_action_resource=args.party_resource,
            resource_uuid=args.resource_uuid,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded action resource '{args.name}'{tag}:")
            print(f"    Resource UUID: {res['resource_uuid']}")
            print(f"    Replenish: {res['replenish_type']}")
            print(f"    DisplayName Handle: {res['display_name_handle']}")
            print(f"    File: {res['action_resources_file']}")
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
