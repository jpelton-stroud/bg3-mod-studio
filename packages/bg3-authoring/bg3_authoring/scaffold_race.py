#!/usr/bin/env python3
"""
scaffold_race.py - Scaffolds Larian Patch 8 Races and RaceDescriptions schemas.

Generates:
1. Public/<ModFolder>/Races/Races.lsx (race mechanics, parent GUID, equipment)
2. Public/<ModFolder>/Races/RaceDescriptions.lsx (companion UI titles and descriptions)
3. Appends localization handles to Localization/English/<ModName>.xml
"""

import argparse
import json
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import resolve_mod_dir
from bg3_core.larian_parsers import (
    generate_larian_handle,
    update_localization_xml,
)

VANILLA_PARENT_RACES = {
    "human": "0eb594cb-8820-4bf6-a60a-38424c578767",
    "elf": "6c038dcb-7eb5-431d-9f4f-cf4f0f61006e",
    "drow": "4f5d1434-5175-4fa9-b7dc-ab24fba37929",
    "half-elf": "45f4ac15-3b07-42d4-9039-51b70a3ccd2e",
    "halfelf": "45f4ac15-3b07-42d4-9039-51b70a3ccd2e",
    "half-orc": "5c39a726-71c8-4748-ba87-024346bc32db",
    "halforc": "5c39a726-71c8-4748-ba87-024346bc32db",
    "halfling": "78e270a6-80ff-421a-af9d-ddf5a8fcde61",
    "dwarf": "0ab2874d-cfdc-4711-9f3a-15f4e30f5c72",
    "gnome": "f1b3f884-4029-4f0f-b158-1f9fe0ff5a0a",
    "tiefling": "b6dccbed-30f3-424b-a1e0-361637a52101",
    "githyanki": "bdf9e795-42e2-4c97-8e6b-89e274916995",
    "dragonborn": "97a06229-22b8-49f8-b342-9905dd502474",
}

EMPTY_RACES_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Races">
        <node id="root">
            <children>
            </children>
        </node>
    </region>
</save>
"""

EMPTY_RACE_DESCRIPTIONS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="RaceDescriptions">
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


def resolve_mod_paths(mod_name_or_path: str, workspace_root: Path) -> tuple[Path, Path, Path, str]:
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


def scaffold_race(
    mod_name_or_path: str,
    name: str,
    display_name: str | None = None,
    description: str | None = None,
    parent_race: str | None = None,
    parent_guid: str | None = None,
    race_uuid: str | None = None,
    progression_table_uuid: str | None = None,
    race_equipment: str | None = None,
    dry_run: bool = False,
) -> dict:
    workspace_root = Path(__file__).resolve().parents[2]
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path, workspace_root)

    races_dir = mod_folder_dir / "Races"
    races_file = races_dir / "Races.lsx"
    race_descs_file = races_dir / "RaceDescriptions.lsx"

    allocated_uuid = race_uuid.strip() if race_uuid else str(uuid.uuid4())
    allocated_table_uuid = progression_table_uuid.strip() if progression_table_uuid else str(uuid.uuid4())
    desc_node_uuid = str(uuid.uuid4())

    resolved_parent_guid = "00000000-0000-0000-0000-000000000000"
    is_subrace = False

    if parent_race:
        key = parent_race.strip().lower()
        if key in VANILLA_PARENT_RACES:
            resolved_parent_guid = VANILLA_PARENT_RACES[key]
            is_subrace = True
        else:
            raise ValueError(f"Unknown vanilla parent race '{parent_race}'. Specify valid parent or --parent-guid.")
    elif parent_guid:
        resolved_parent_guid = parent_guid.strip()
        is_subrace = (resolved_parent_guid != "00000000-0000-0000-0000-000000000000")

    equipment_val = race_equipment if race_equipment else (f"EQP_CC_{name}" if not is_subrace else "")
    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} race description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    # 1. Update Races.lsx
    if races_file.exists():
        r_tree = ET.parse(races_file)
        r_root = r_tree.getroot()
    else:
        r_root = ET.fromstring(EMPTY_RACES_LSX)

    r_children = r_root.find(".//node[@id='root']/children")
    if r_children is None:
        r_root_node = r_root.find(".//node[@id='root']")
        if r_root_node is None:
            r_reg = r_root.find(".//region[@id='Races']")
            if r_reg is None:
                r_reg = ET.SubElement(r_root, "region", id="Races")
            r_root_node = ET.SubElement(r_reg, "node", id="root")
        r_children = ET.SubElement(r_root_node, "children")

    existing_node = None
    for rnode in r_children.findall("./node[@id='Race']"):
        for attr in rnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                existing_node = rnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        r_children.remove(existing_node)

    race_node = ET.SubElement(r_children, "node", id="Race")
    ET.SubElement(race_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(race_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(race_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(race_node, "attribute", id="ParentGuid", type="guid", value=resolved_parent_guid)
    ET.SubElement(race_node, "attribute", id="ProgressionTableUUID", type="guid", value=allocated_table_uuid)
    ET.SubElement(race_node, "attribute", id="RaceEquipment", type="FixedString", value=equipment_val)
    ET.SubElement(race_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    tags_node = ET.SubElement(race_node, "children")
    ET.SubElement(tags_node, "node", id="Tags")

    if not dry_run:
        races_dir.mkdir(parents=True, exist_ok=True)
        races_file.write_text(prettify_xml(r_root), encoding="utf-8")

    # 2. Update RaceDescriptions.lsx
    if race_descs_file.exists():
        rd_tree = ET.parse(race_descs_file)
        rd_root = rd_tree.getroot()
    else:
        rd_root = ET.fromstring(EMPTY_RACE_DESCRIPTIONS_LSX)

    rd_children = rd_root.find(".//node[@id='root']/children")
    if rd_children is None:
        rd_root_node = rd_root.find(".//node[@id='root']")
        if rd_root_node is None:
            rd_reg = rd_root.find(".//region[@id='RaceDescriptions']")
            if rd_reg is None:
                rd_reg = ET.SubElement(rd_root, "region", id="RaceDescriptions")
            rd_root_node = ET.SubElement(rd_reg, "node", id="root")
        rd_children = ET.SubElement(rd_root_node, "children")

    existing_desc = None
    for dnode in rd_children.findall("./node[@id='RaceDescription']"):
        for attr in dnode.findall("./attribute"):
            if (attr.get("id") == "ExactMatch" and attr.get("value") == name) or (attr.get("id") == "RaceId" and attr.get("value") == allocated_uuid):
                existing_desc = dnode
                break
        if existing_desc is not None:
            break

    if existing_desc is not None:
        rd_children.remove(existing_desc)

    race_desc_node = ET.SubElement(rd_children, "node", id="RaceDescription")
    ET.SubElement(race_desc_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(race_desc_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(race_desc_node, "attribute", id="ExactMatch", type="FixedString", value=name)
    ET.SubElement(race_desc_node, "attribute", id="RaceId", type="guid", value=allocated_uuid)
    ET.SubElement(race_desc_node, "attribute", id="UUID", type="guid", value=desc_node_uuid)

    if not dry_run:
        race_descs_file.write_text(prettify_xml(rd_root), encoding="utf-8")

    # 3. Update Localization XML
    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return {
        "success": True,
        "mod": mod_slug,
        "name": name,
        "race_uuid": allocated_uuid,
        "table_uuid": allocated_table_uuid,
        "is_subrace": is_subrace,
        "parent_guid": resolved_parent_guid,
        "display_name_handle": f"{disp_handle};1",
        "description_handle": f"{desc_handle};1",
        "races_file": str(races_file),
        "race_descriptions_file": str(race_descs_file),
        "localization_file": str(loc_file),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 Races.lsx and RaceDescriptions.lsx custom races and subraces.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--name", required=True, help="Internal race/subrace name (e.g. ShadowElf)")
    parser.add_argument("--display-name", help="Display name in game UI")
    parser.add_argument("--description", help="Description in character creation")
    parser.add_argument("--parent-race", help="Vanilla parent race preset (e.g. elf, drow, tiefling)")
    parser.add_argument("--parent-guid", help="Explicit parent race GUID if not using vanilla preset")
    parser.add_argument("--race-uuid", help="Explicit UUID for this race")
    parser.add_argument("--table-uuid", help="Explicit ProgressionTableUUID for this race")
    parser.add_argument("--equipment", help="Starting CC equipment preset name")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_race(
            mod_name_or_path=args.mod,
            name=args.name,
            display_name=args.display_name,
            description=args.description,
            parent_race=args.parent_race,
            parent_guid=args.parent_guid,
            race_uuid=args.race_uuid,
            progression_table_uuid=args.table_uuid,
            race_equipment=args.equipment,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded race '{args.name}'{tag}:")
            print(f"    Race UUID: {res['race_uuid']}")
            print(f"    Table UUID: {res['table_uuid']}")
            print(f"    Subrace: {res['is_subrace']} (Parent GUID: {res['parent_guid']})")
            print(f"    Files: {res['races_file']}, {res['race_descriptions_file']}")
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
