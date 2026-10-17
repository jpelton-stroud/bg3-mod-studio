#!/usr/bin/env python3
"""
scaffold_class_description.py - Scaffolds Larian Patch 8 Class and Subclass definitions.

Generates:
1. Public/<ModFolder>/ClassDescriptions/ClassDescriptions.lsx
2. Public/<ModFolder>/Progressions/ProgressionDescriptions.lsx (companion UI descriptions)
3. Registers subclass in parent class's Progressions.lsx under SubClasses node
4. Appends localization handles to Localization/English/<ModName>.xml
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
from scripts.lib.larian_parsers import (
    PATCH_8_VERSION,
    generate_larian_handle,
    update_localization_xml,
)

# Standard vanilla class references in Baldur's Gate 3
VANILLA_PARENT_CLASSES = {
    "barbarian": {
        "guid": "d8cad572-04ae-4920-a372-30772ae38e55",
        "subclass_level": 3,
        "table_uuid": "60bb7dc1-7143-400e-ae34-7d8da6c8a782",
    },
    "bard": {
        "guid": "92cdc989-c760-4928-8684-25e22709e897",
        "subclass_level": 3,
        "table_uuid": "229c98da-2cd1-4a5e-a579-43c1687ed991",
    },
    "cleric": {
        "guid": "114e7aee-d1d4-4271-8414-3d42ee450cdd",
        "subclass_level": 1,
        "table_uuid": "64474b62-b4f5-46b3-b94a-c676c6da3116",
    },
    "druid": {
        "guid": "457e0a4e-92b1-4ec0-b0cc-bf606ea490ab",
        "subclass_level": 2,
        "table_uuid": "6e34618d-4040-4c65-815c-18c92e4ba13d",
    },
    "fighter": {
        "guid": "72764534-fb3d-4091-8850-ff6db1e3ca9c",
        "subclass_level": 3,
        "table_uuid": "ba4e707e-4bbd-4630-963b-ce2f2947f971",
    },
    "monk": {
        "guid": "e1e4a21f-9405-46ec-81a0-cc2fb6da4f74",
        "subclass_level": 3,
        "table_uuid": "fe1319a2-86be-469c-aab5-e3b0bd714e0e",
    },
    "paladin": {
        "guid": "ff4d9497-0c30-44d7-8677-627c2fa4b7ab",
        "subclass_level": 1,
        "table_uuid": "ba2afe85-acba-4ea1-a238-2b4543f47821",
    },
    "ranger": {
        "guid": "36be1680-e773-450c-b570-514d4ff740f5",
        "subclass_level": 3,
        "table_uuid": "0aa30731-4f33-4452-a1e1-9404662cb829",
    },
    "rogue": {
        "guid": "e8b01dc7-d222-4735-ad53-4170c22a1645",
        "subclass_level": 3,
        "table_uuid": "9a44e887-44da-4246-aab4-6e6017ec6acc",
    },
    "sorcerer": {
        "guid": "784001e2-96f7-4701-9d1b-944d0223754e",
        "subclass_level": 1,
        "table_uuid": "e2416b02-953d-422f-beca-90802c6cad3e",
    },
    "warlock": {
        "guid": "b4225a4b-4f9e-4789-a47c-774ea93842c3",
        "subclass_level": 1,
        "table_uuid": "a7a9b714-d4ee-46de-821b-0e3919e3f446",
    },
    "wizard": {
        "guid": "a86596b0-73cc-4621-9943-6d4e0d45255e",
        "subclass_level": 2,
        "table_uuid": "d77e6444-37dc-40c2-90ea-4c54964648a8",
    },
}

EMPTY_CLASS_DESCRIPTIONS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="ClassDescriptions">
        <node id="root">
            <children>
            </children>
        </node>
    </region>
</save>
"""

EMPTY_PROGRESSION_DESCRIPTIONS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="ProgressionDescriptions">
        <node id="root">
            <children>
            </children>
        </node>
    </region>
</save>
"""

EMPTY_PROGRESSIONS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Progressions">
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


def scaffold_class_description(
    mod_name_or_path: str,
    name: str,
    display_name: str | None = None,
    description: str | None = None,
    parent_class: str | None = None,
    parent_guid: str | None = None,
    class_uuid: str | None = None,
    progression_table_uuid: str | None = None,
    base_hp: int = 8,
    hp_per_level: int = 5,
    primary_ability: int = 1,
    spell_casting_ability: int = 0,
    register_in_parent: bool = False,
    dry_run: bool = False,
) -> dict:
    workspace_root = Path(__file__).resolve().parents[2]
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path, workspace_root)

    class_desc_dir = mod_folder_dir / "ClassDescriptions"
    prog_desc_dir = mod_folder_dir / "Progressions"
    class_desc_file = class_desc_dir / "ClassDescriptions.lsx"
    prog_desc_file = prog_desc_dir / "ProgressionDescriptions.lsx"
    progressions_file = prog_desc_dir / "Progressions.lsx"

    allocated_class_uuid = class_uuid.strip() if class_uuid else str(uuid.uuid4())
    allocated_table_uuid = progression_table_uuid.strip() if progression_table_uuid else str(uuid.uuid4())
    prog_desc_uuid = str(uuid.uuid4())

    # Resolve parent GUID and subclass status
    resolved_parent_guid = "00000000-0000-0000-0000-000000000000"
    is_subclass = False
    parent_info = None

    if parent_class:
        key = parent_class.strip().lower()
        if key in VANILLA_PARENT_CLASSES:
            parent_info = VANILLA_PARENT_CLASSES[key]
            resolved_parent_guid = parent_info["guid"]
            is_subclass = True
        else:
            raise ValueError(f"Unknown vanilla parent class '{parent_class}'. Specify valid class or --parent-guid.")
    elif parent_guid:
        resolved_parent_guid = parent_guid.strip()
        is_subclass = (resolved_parent_guid != "00000000-0000-0000-0000-000000000000")

    # Generate localization handles
    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} class description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    # 1. Update ClassDescriptions.lsx
    if class_desc_file.exists():
        tree = ET.parse(class_desc_file)
        root = tree.getroot()
    else:
        root = ET.fromstring(EMPTY_CLASS_DESCRIPTIONS_LSX)

    children = root.find(".//node[@id='root']/children")
    if children is None:
        root_node = root.find(".//node[@id='root']")
        if root_node is None:
            reg = root.find(".//region[@id='ClassDescriptions']")
            if reg is None:
                reg = ET.SubElement(root, "region", id="ClassDescriptions")
            root_node = ET.SubElement(reg, "node", id="root")
        children = ET.SubElement(root_node, "children")

    # Check for existing entry with same Name
    existing_node = None
    for node in children.findall(".//node[@id='ClassDescription']"):
        for attr in node.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                existing_node = node
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        children.remove(existing_node)

    class_node = ET.SubElement(children, "node", id="ClassDescription")
    ET.SubElement(class_node, "attribute", id="BaseHp", type="int32", value=str(base_hp))
    ET.SubElement(class_node, "attribute", id="CharacterCreationPose", type="guid", value="0f07ec6e-4ef0-434e-9a51-1353260ccff8")
    ET.SubElement(class_node, "attribute", id="ClassEquipment", type="FixedString", value=f"EQP_CC_{name}" if not is_subclass else "")
    ET.SubElement(class_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(class_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(class_node, "attribute", id="HpPerLevel", type="int32", value=str(hp_per_level))
    ET.SubElement(class_node, "attribute", id="LearningStrategy", type="uint8", value="1")
    ET.SubElement(class_node, "attribute", id="MustPrepareSpells", type="bool", value="false")
    ET.SubElement(class_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(class_node, "attribute", id="ParentGuid", type="guid", value=resolved_parent_guid)
    ET.SubElement(class_node, "attribute", id="PrimaryAbility", type="uint8", value=str(primary_ability))
    ET.SubElement(class_node, "attribute", id="ProgressionTableUUID", type="guid", value=allocated_table_uuid)
    ET.SubElement(class_node, "attribute", id="SoundClassType", type="FixedString", value=parent_class.capitalize() if parent_class else name)
    ET.SubElement(class_node, "attribute", id="SpellCastingAbility", type="uint8", value=str(spell_casting_ability))
    ET.SubElement(class_node, "attribute", id="UUID", type="guid", value=allocated_class_uuid)

    tags_node = ET.SubElement(class_node, "children")
    ET.SubElement(tags_node, "node", id="Tags")

    if not dry_run:
        class_desc_dir.mkdir(parents=True, exist_ok=True)
        class_desc_file.write_text(prettify_xml(root), encoding="utf-8")

    # 2. Update ProgressionDescriptions.lsx
    if prog_desc_file.exists():
        prog_tree = ET.parse(prog_desc_file)
        prog_root = prog_tree.getroot()
    else:
        prog_root = ET.fromstring(EMPTY_PROGRESSION_DESCRIPTIONS_LSX)

    prog_children = prog_root.find(".//node[@id='root']/children")
    if prog_children is None:
        p_root_node = prog_root.find(".//node[@id='root']")
        if p_root_node is None:
            p_reg = prog_root.find(".//region[@id='ProgressionDescriptions']")
            if p_reg is None:
                p_reg = ET.SubElement(prog_root, "region", id="ProgressionDescriptions")
            p_root_node = ET.SubElement(p_reg, "node", id="root")
        prog_children = ET.SubElement(p_root_node, "children")

    desc_node = ET.SubElement(prog_children, "node", id="ProgressionDescription")
    ET.SubElement(desc_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(desc_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(desc_node, "attribute", id="ExactMatch", type="FixedString", value=name)
    ET.SubElement(desc_node, "attribute", id="Hidden", type="bool", value="false")
    ET.SubElement(desc_node, "attribute", id="ProgressionId", type="guid", value="00000000-0000-0000-0000-000000000000")
    ET.SubElement(desc_node, "attribute", id="ProgressionTableId", type="guid", value=allocated_table_uuid)
    ET.SubElement(desc_node, "attribute", id="Type", type="FixedString", value="SubClass" if is_subclass else "Class")
    ET.SubElement(desc_node, "attribute", id="UUID", type="guid", value=prog_desc_uuid)

    if not dry_run:
        prog_desc_dir.mkdir(parents=True, exist_ok=True)
        prog_desc_file.write_text(prettify_xml(prog_root), encoding="utf-8")

    # 3. Subclass registration into parent Progressions.lsx
    parent_registered = False
    if is_subclass and register_in_parent:
        if progressions_file.exists():
            ps_tree = ET.parse(progressions_file)
            ps_root = ps_tree.getroot()
        else:
            ps_root = ET.fromstring(EMPTY_PROGRESSIONS_LSX)

        ps_children = ps_root.find(".//node[@id='root']/children")
        if ps_children is None:
            ps_root_node = ps_root.find(".//node[@id='root']")
            ps_children = ET.SubElement(ps_root_node, "children")

        subclass_level = parent_info["subclass_level"] if parent_info else 3
        parent_table_uuid = parent_info["table_uuid"] if parent_info else ""

        # Find matching progression node for parent class at subclass choice level
        target_prog_node = None
        for pnode in ps_children.findall(".//node[@id='Progression']"):
            p_table = None
            p_level = None
            for attr in pnode.findall("./attribute"):
                if attr.get("id") == "TableUUID":
                    p_table = attr.get("value")
                elif attr.get("id") == "Level":
                    p_level = attr.get("value")
            if (p_table and parent_table_uuid and p_table.lower() == parent_table_uuid.lower()) or (p_level == str(subclass_level)):
                target_prog_node = pnode
                break

        if target_prog_node is None:
            # Create stub progression node for parent class at subclass level
            target_prog_node = ET.SubElement(ps_children, "node", id="Progression")
            ET.SubElement(target_prog_node, "attribute", id="Boosts", type="LSString", value="")
            ET.SubElement(target_prog_node, "attribute", id="Level", type="uint8", value=str(subclass_level))
            ET.SubElement(target_prog_node, "attribute", id="Name", type="FixedString", value=parent_class.capitalize() if parent_class else "ParentClass")
            ET.SubElement(target_prog_node, "attribute", id="PassivesAdded", type="LSString", value="")
            ET.SubElement(target_prog_node, "attribute", id="ProgressionType", type="uint8", value="0")
            ET.SubElement(target_prog_node, "attribute", id="TableUUID", type="guid", value=parent_table_uuid if parent_table_uuid else str(uuid.uuid4()))
            ET.SubElement(target_prog_node, "attribute", id="UUID", type="guid", value=str(uuid.uuid4()))

        # Locate or create SubClasses node
        subclasses_node = None
        children_tag = target_prog_node.find("./children")
        if children_tag is None:
            children_tag = ET.SubElement(target_prog_node, "children")

        subclasses_node = children_tag.find("./node[@id='SubClasses']")
        if subclasses_node is None:
            subclasses_node = ET.SubElement(children_tag, "node", id="SubClasses")

        sc_children = subclasses_node.find("./children")
        if sc_children is None:
            sc_children = ET.SubElement(subclasses_node, "children")

        # Check if already present
        already_present = False
        for sc in sc_children.findall("./node[@id='SubClass']"):
            for attr in sc.findall("./attribute"):
                if attr.get("id") == "Object" and attr.get("value") == allocated_class_uuid:
                    already_present = True
                    break

        if not already_present:
            new_sc = ET.SubElement(sc_children, "node", id="SubClass")
            ET.SubElement(new_sc, "attribute", id="Object", type="guid", value=allocated_class_uuid)

        parent_registered = True
        if not dry_run:
            progressions_file.write_text(prettify_xml(ps_root), encoding="utf-8")

    # 4. Localization XML handles
    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return {
        "success": True,
        "mod": mod_slug,
        "class_name": name,
        "class_uuid": allocated_class_uuid,
        "progression_table_uuid": allocated_table_uuid,
        "is_subclass": is_subclass,
        "parent_guid": resolved_parent_guid,
        "parent_registered": parent_registered,
        "display_name_handle": f"{disp_handle};1",
        "description_handle": f"{desc_handle};1",
        "class_descriptions_file": str(class_desc_file),
        "progression_descriptions_file": str(prog_desc_file),
        "localization_file": str(loc_file),
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 Class & Subclass descriptions with atomic localization and companion schemas.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--name", required=True, help="Internal class/subclass name (e.g. ShadowStalker)")
    parser.add_argument("--display-name", help="Display name in game UI")
    parser.add_argument("--description", help="Description in character creation & level-up tree")
    parser.add_argument("--parent-class", help="Vanilla parent class preset (e.g. rogue, wizard, paladin)")
    parser.add_argument("--parent-guid", help="Explicit parent class GUID if not using vanilla preset")
    parser.add_argument("--class-uuid", help="Explicit UUID for this class/subclass")
    parser.add_argument("--table-uuid", help="Explicit ProgressionTableUUID for this class/subclass")
    parser.add_argument("--base-hp", type=int, default=8, help="Base HP at level 1 (default: 8)")
    parser.add_argument("--hp-per-level", type=int, default=5, help="HP gain per level (default: 5)")
    parser.add_argument("--primary-ability", type=int, default=1, help="Primary ability score enum (default: 1)")
    parser.add_argument("--spell-ability", type=int, default=0, help="Spellcasting ability enum (default: 0)")
    parser.add_argument("--register-in-parent", action="store_true", default=True, help="Inject subclass GUID into parent's Progressions.lsx node (default: True)")
    parser.add_argument("--no-register-in-parent", dest="register_in_parent", action="store_false", help="Do not inject subclass into parent's Progressions.lsx")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_class_description(
            mod_name_or_path=args.mod,
            name=args.name,
            display_name=args.display_name,
            description=args.description,
            parent_class=args.parent_class,
            parent_guid=args.parent_guid,
            class_uuid=args.class_uuid,
            progression_table_uuid=args.table_uuid,
            base_hp=args.base_hp,
            hp_per_level=args.hp_per_level,
            primary_ability=args.primary_ability,
            spell_casting_ability=args.spell_ability,
            register_in_parent=args.register_in_parent,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded class description for '{args.name}'{tag}:")
            print(f"    Class UUID: {res['class_uuid']}")
            print(f"    Table UUID: {res['progression_table_uuid']}")
            print(f"    Subclass: {res['is_subclass']} (Parent GUID: {res['parent_guid']})")
            if res["parent_registered"]:
                print(f"    Parent Progressions SubClass registration: Injected")
            print(f"    Files: {res['class_descriptions_file']}, {res['progression_descriptions_file']}")
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
