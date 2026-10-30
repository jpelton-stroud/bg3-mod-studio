#!/usr/bin/env python3
"""
scaffold_appearance_visual.py - Scaffolds Larian Patch 8 CharacterCreationAppearanceVisuals.lsx schemas.

Generates cosmetic asset bindings (Hair, Head, Horns, Beard) in
Public/<ModFolder>/CharacterCreation/CharacterCreationAppearanceVisuals.lsx.
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

VANILLA_RACE_UUIDS = {
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

EMPTY_APPEARANCE_VISUALS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="CharacterCreationAppearanceVisuals">
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


def resolve_race_uuid(race_arg: str | None, mod_folder_dir: Path) -> str:
    if not race_arg:
        return "00000000-0000-0000-0000-000000000000"
    key = race_arg.strip().lower()
    if key in VANILLA_RACE_UUIDS:
        return VANILLA_RACE_UUIDS[key]

    races_file = mod_folder_dir / "Races" / "Races.lsx"
    if races_file.exists():
        tree = ET.parse(races_file)
        root = tree.getroot()
        for rnode in root.findall(".//node[@id='Race']"):
            name_val = None
            uuid_val = None
            for attr in rnode.findall("./attribute"):
                if attr.get("id") == "Name":
                    name_val = attr.get("value")
                elif attr.get("id") == "UUID":
                    uuid_val = attr.get("value")
            if name_val and name_val.lower() == key and uuid_val:
                return uuid_val

    if len(race_arg.strip()) == 36 and "-" in race_arg:
        return race_arg.strip()

    return "00000000-0000-0000-0000-000000000000"


def scaffold_appearance_visual(
    mod_name_or_path: str,
    name: str,
    visual_resource: str,
    slot: str = "Hair",
    race: str | None = None,
    body_type: int = 0,
    body_shape: int = 0,
    display_name: str | None = None,
    visual_uuid: str | None = None,
    dry_run: bool = False,
) -> dict:
    workspace_root = Path(__file__).resolve().parents[2]
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path, workspace_root)

    cc_dir = mod_folder_dir / "CharacterCreation"
    cc_file = cc_dir / "CharacterCreationAppearanceVisuals.lsx"

    allocated_uuid = visual_uuid.strip() if visual_uuid else str(uuid.uuid4())
    resolved_race_uuid = resolve_race_uuid(race, mod_folder_dir)
    disp_text = display_name if display_name else name
    disp_handle = generate_larian_handle()

    if cc_file.exists():
        tree = ET.parse(cc_file)
        root = tree.getroot()
    else:
        root = ET.fromstring(EMPTY_APPEARANCE_VISUALS_LSX)

    children = root.find(".//node[@id='root']/children")
    if children is None:
        r_node = root.find(".//node[@id='root']")
        if r_node is None:
            reg = root.find(".//region[@id='CharacterCreationAppearanceVisuals']")
            if reg is None:
                reg = ET.SubElement(root, "region", id="CharacterCreationAppearanceVisuals")
            r_node = ET.SubElement(reg, "node", id="root")
        children = ET.SubElement(r_node, "children")

    node = ET.SubElement(children, "node", id="CharacterCreationAppearanceVisual")
    ET.SubElement(node, "attribute", id="BodyShape", type="uint8", value=str(body_shape))
    ET.SubElement(node, "attribute", id="BodyType", type="uint8", value=str(body_type))
    ET.SubElement(node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(node, "attribute", id="RaceUUID", type="guid", value=resolved_race_uuid)
    ET.SubElement(node, "attribute", id="SlotName", type="FixedString", value=slot)
    ET.SubElement(node, "attribute", id="UUID", type="guid", value=allocated_uuid)
    ET.SubElement(node, "attribute", id="VisualResource", type="guid", value=visual_resource.strip())

    tags_node = ET.SubElement(node, "children")
    ET.SubElement(tags_node, "node", id="Tags")

    if not dry_run:
        cc_dir.mkdir(parents=True, exist_ok=True)
        cc_file.write_text(prettify_xml(root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text)], dry_run=dry_run)

    return {
        "success": True,
        "mod": mod_slug,
        "name": name,
        "slot": slot,
        "uuid": allocated_uuid,
        "visual_resource": visual_resource.strip(),
        "race_uuid": resolved_race_uuid,
        "body_type": body_type,
        "body_shape": body_shape,
        "display_name_handle": f"{disp_handle};1",
        "file": str(cc_file),
        "localization_file": str(loc_file),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 CharacterCreationAppearanceVisuals.lsx cosmetic assets.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--name", required=True, help="Internal cosmetic name (e.g. Shadow_Horns)")
    parser.add_argument("--visual-resource", required=True, help="VisualResource mesh/asset GUID")
    parser.add_argument("--slot", choices=["Hair", "Head", "Horns", "Body", "Tail", "Beard", "Piercing", "EyeColor", "Tattoo", "Makeup"], default="Hair", help="Cosmetic slot (default: Hair)")
    parser.add_argument("--race", help="Target race name or UUID (or omitted for all races)")
    parser.add_argument("--body-type", type=int, choices=[0, 1], default=0, help="0=Male, 1=Female (default: 0)")
    parser.add_argument("--body-shape", type=int, choices=[0, 1], default=0, help="0=Standard, 1=Strong (default: 0)")
    parser.add_argument("--display-name", help="Display name in character creator")
    parser.add_argument("--uuid", help="Explicit UUID for this visual entry")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_appearance_visual(
            mod_name_or_path=args.mod,
            name=args.name,
            visual_resource=args.visual_resource,
            slot=args.slot,
            race=args.race,
            body_type=args.body_type,
            body_shape=args.body_shape,
            display_name=args.display_name,
            visual_uuid=args.uuid,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded appearance visual '{args.name}' ({args.slot}){tag}:")
            print(f"    Visual UUID: {res['uuid']}")
            print(f"    Resource GUID: {res['visual_resource']}")
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
