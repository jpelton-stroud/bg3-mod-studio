#!/usr/bin/env python3
"""
scaffold_origin.py - Scaffolds Larian Patch 8 Origins/Origins.lsx schemas.

Generates playable origin character nodes in Public/<ModFolder>/Origins/Origins.lsx
with atomic localization handle allocation.
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
    split_larian_items,
    update_localization_xml,
)

EMPTY_ORIGINS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Origins">
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


def scaffold_origin(
    mod_name_or_path: str,
    name: str,
    display_name: str | None = None,
    description: str | None = None,
    class_equipment: str | None = None,
    class_uuid: str | None = None,
    race_uuid: str | None = None,
    body_type: int = 0,
    body_shape: int = 0,
    passives: str | None = None,
    origin_uuid: str | None = None,
    unique: bool = True,
    dry_run: bool = False,
) -> dict:
    workspace_root = Path(__file__).resolve().parents[2]
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path, workspace_root)

    origins_dir = mod_folder_dir / "Origins"
    origins_file = origins_dir / "Origins.lsx"

    allocated_uuid = origin_uuid.strip() if origin_uuid else str(uuid.uuid4())
    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} origin description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    passives_str = ";".join(split_larian_items(passives)) if passives else ""
    eqp_str = class_equipment if class_equipment else f"EQP_CC_{name}"
    cls_uuid = class_uuid.strip() if class_uuid else "00000000-0000-0000-0000-000000000000"
    rc_uuid = race_uuid.strip() if race_uuid else "00000000-0000-0000-0000-000000000000"

    if origins_file.exists():
        tree = ET.parse(origins_file)
        root = tree.getroot()
    else:
        root = ET.fromstring(EMPTY_ORIGINS_LSX)

    children = root.find(".//node[@id='root']/children")
    if children is None:
        r_node = root.find(".//node[@id='root']")
        if r_node is None:
            reg = root.find(".//region[@id='Origins']")
            if reg is None:
                reg = ET.SubElement(root, "region", id="Origins")
            r_node = ET.SubElement(reg, "node", id="root")
        children = ET.SubElement(r_node, "children")

    existing_node = None
    for onode in children.findall("./node[@id='Origin']"):
        for attr in onode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                existing_node = onode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        children.remove(existing_node)

    node = ET.SubElement(children, "node", id="Origin")
    ET.SubElement(node, "attribute", id="AppearanceTags", type="LSString", value="")
    ET.SubElement(node, "attribute", id="BodyShape", type="uint8", value=str(body_shape))
    ET.SubElement(node, "attribute", id="BodyType", type="uint8", value=str(body_type))
    ET.SubElement(node, "attribute", id="ClassEquipmentOverride", type="FixedString", value=eqp_str)
    ET.SubElement(node, "attribute", id="ClassUUID", type="guid", value=cls_uuid)
    ET.SubElement(node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(node, "attribute", id="GlobalTemplate", type="guid", value="00000000-0000-0000-0000-000000000000")
    ET.SubElement(node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(node, "attribute", id="Passives", type="LSString", value=passives_str)
    ET.SubElement(node, "attribute", id="RaceUUID", type="guid", value=rc_uuid)
    ET.SubElement(node, "attribute", id="SubClassUUID", type="guid", value="00000000-0000-0000-0000-000000000000")
    ET.SubElement(node, "attribute", id="SubRaceUUID", type="guid", value="00000000-0000-0000-0000-000000000000")
    ET.SubElement(node, "attribute", id="UUID", type="guid", value=allocated_uuid)
    ET.SubElement(node, "attribute", id="Unique", type="bool", value="true" if unique else "false")
    ET.SubElement(node, "attribute", id="VoiceTableUUID", type="guid", value="00000000-0000-0000-0000-000000000000")

    if not dry_run:
        origins_dir.mkdir(parents=True, exist_ok=True)
        origins_file.write_text(prettify_xml(root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return {
        "success": True,
        "mod": mod_slug,
        "name": name,
        "origin_uuid": allocated_uuid,
        "display_name_handle": f"{disp_handle};1",
        "description_handle": f"{desc_handle};1",
        "class_equipment": eqp_str,
        "file": str(origins_file),
        "localization_file": str(loc_file),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 Origins/Origins.lsx playable origin characters.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--name", required=True, help="Internal origin name (e.g. ShadeOrigin)")
    parser.add_argument("--display-name", help="Display name in game UI")
    parser.add_argument("--description", help="Description in character creation")
    parser.add_argument("--equipment", help="ClassEquipmentOverride preset name")
    parser.add_argument("--class-uuid", help="Default class GUID")
    parser.add_argument("--race-uuid", help="Default race GUID")
    parser.add_argument("--body-type", type=int, choices=[0, 1], default=0, help="0=Male, 1=Female (default: 0)")
    parser.add_argument("--body-shape", type=int, choices=[0, 1], default=0, help="0=Standard, 1=Strong (default: 0)")
    parser.add_argument("--passives", help="Comma-separated starting passive names")
    parser.add_argument("--uuid", help="Explicit UUID for this origin")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_origin(
            mod_name_or_path=args.mod,
            name=args.name,
            display_name=args.display_name,
            description=args.description,
            class_equipment=args.equipment,
            class_uuid=args.class_uuid,
            race_uuid=args.race_uuid,
            body_type=args.body_type,
            body_shape=args.body_shape,
            passives=args.passives,
            origin_uuid=args.uuid,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded origin character '{args.name}'{tag}:")
            print(f"    Origin UUID: {res['origin_uuid']}")
            print(f"    DisplayName Handle: {res['display_name_handle']}")
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
