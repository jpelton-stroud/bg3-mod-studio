#!/usr/bin/env python3
"""
scaffold_default_values.py - Scaffolds Larian Patch 8 Character Creation DefaultValues schemas.

Generates:
1. Public/<ModFolder>/DefaultValues/Abilities.lsx (starred ability recommendations)
2. Public/<ModFolder>/DefaultValues/Skills.lsx (default selected proficiencies)
3. Public/<ModFolder>/DefaultValues/Spells.lsx (default prepared spells/cantrips)
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
from bg3_core.larian_parsers import split_larian_items

VANILLA_CLASS_TABLES = {
    "barbarian": "60bb7dc1-7143-400e-ae34-7d8da6c8a782",
    "bard": "229c98da-2cd1-4a5e-a579-43c1687ed991",
    "cleric": "64474b62-b4f5-46b3-b94a-c676c6da3116",
    "druid": "6e34618d-4040-4c65-815c-18c92e4ba13d",
    "fighter": "ba4e707e-4bbd-4630-963b-ce2f2947f971",
    "monk": "fe1319a2-86be-469c-aab5-e3b0bd714e0e",
    "paladin": "ba2afe85-acba-4ea1-a238-2b4543f47821",
    "ranger": "0aa30731-4f33-4452-a1e1-9404662cb829",
    "rogue": "9a44e887-44da-4246-aab4-6e6017ec6acc",
    "sorcerer": "e2416b02-953d-422f-beca-90802c6cad3e",
    "warlock": "a7a9b714-d4ee-46de-821b-0e3919e3f446",
    "wizard": "d77e6444-37dc-40c2-90ea-4c54964648a8",
}

EMPTY_DEFAULT_VALUES_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="DefaultValues">
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


def lookup_table_uuid(mod_folder_dir: Path, class_name: str) -> str:
    key = class_name.strip().lower()
    if key in VANILLA_CLASS_TABLES:
        return VANILLA_CLASS_TABLES[key]

    class_desc_file = mod_folder_dir / "ClassDescriptions" / "ClassDescriptions.lsx"
    if class_desc_file.exists():
        tree = ET.parse(class_desc_file)
        root = tree.getroot()
        for cnode in root.findall(".//node[@id='ClassDescription']"):
            name_val = None
            table_val = None
            for attr in cnode.findall("./attribute"):
                if attr.get("id") == "Name":
                    name_val = attr.get("value")
                elif attr.get("id") == "ProgressionTableUUID":
                    table_val = attr.get("value")
            if name_val and name_val.lower() == key and table_val:
                return table_val

    return str(uuid.uuid4())


def append_default_value_node(file_path: Path, table_uuid: str, add_items: list[str], level: int = 1, dry_run: bool = False) -> str:
    allocated_uuid = str(uuid.uuid4())
    add_str = ";".join(add_items)

    if file_path.exists():
        tree = ET.parse(file_path)
        root = tree.getroot()
    else:
        root = ET.fromstring(EMPTY_DEFAULT_VALUES_LSX)

    children = root.find(".//node[@id='root']/children")
    if children is None:
        r_node = root.find(".//node[@id='root']")
        if r_node is None:
            reg = root.find(".//region[@id='DefaultValues']")
            if reg is None:
                reg = ET.SubElement(root, "region", id="DefaultValues")
            r_node = ET.SubElement(reg, "node", id="root")
        children = ET.SubElement(r_node, "children")

    # Check for existing node with same TableUUID and Level
    existing_node = None
    for dnode in children.findall("./node[@id='DefaultValue']"):
        match_table = False
        match_level = False
        for attr in dnode.findall("./attribute"):
            if attr.get("id") == "TableUUID" and attr.get("value") == table_uuid:
                match_table = True
            elif attr.get("id") == "Level" and attr.get("value") == str(level):
                match_level = True
        if match_table and match_level:
            existing_node = dnode
            break

    if existing_node is not None:
        children.remove(existing_node)

    dv_node = ET.SubElement(children, "node", id="DefaultValue")
    ET.SubElement(dv_node, "attribute", id="Add", type="LSString", value=add_str)
    ET.SubElement(dv_node, "attribute", id="Level", type="int32", value=str(level))
    ET.SubElement(dv_node, "attribute", id="TableUUID", type="guid", value=table_uuid)
    ET.SubElement(dv_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(prettify_xml(root), encoding="utf-8")

    return allocated_uuid


def scaffold_default_values(
    mod_name_or_path: str,
    class_name: str,
    abilities: str | None = None,
    skills: str | None = None,
    spells: str | None = None,
    table_uuid: str | None = None,
    level: int = 1,
    dry_run: bool = False,
) -> dict:
    workspace_root = Path(__file__).resolve().parents[2]
    mod_root, mod_folder_dir, mod_slug = resolve_mod_paths(mod_name_or_path, workspace_root)

    dv_dir = mod_folder_dir / "DefaultValues"
    resolved_table_uuid = table_uuid.strip() if table_uuid else lookup_table_uuid(mod_folder_dir, class_name)

    created_files: list[str] = []
    results: dict = {
        "success": True,
        "mod": mod_slug,
        "class_name": class_name,
        "table_uuid": resolved_table_uuid,
        "level": level,
        "files_updated": created_files,
        "dry_run": dry_run,
    }

    if abilities:
        items = split_larian_items(abilities)
        if items:
            f = dv_dir / "Abilities.lsx"
            append_default_value_node(f, resolved_table_uuid, items, level=level, dry_run=dry_run)
            created_files.append(str(f))
            results["abilities"] = items

    if skills:
        items = split_larian_items(skills)
        if items:
            f = dv_dir / "Skills.lsx"
            append_default_value_node(f, resolved_table_uuid, items, level=level, dry_run=dry_run)
            created_files.append(str(f))
            results["skills"] = items

    if spells:
        items = split_larian_items(spells)
        if items:
            f = dv_dir / "Spells.lsx"
            append_default_value_node(f, resolved_table_uuid, items, level=level, dry_run=dry_run)
            created_files.append(str(f))
            results["spells"] = items

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 Character Creation DefaultValues schemas (Abilities, Skills, Spells).")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--class", dest="class_name", required=True, help="Target class name (resolves TableUUID automatically)")
    parser.add_argument("--abilities", help="Comma-separated recommended abilities (e.g. 'Strength,Constitution' or 'Dexterity,Wisdom')")
    parser.add_argument("--skills", help="Comma-separated default skill proficiencies (e.g. 'Athletics,Intimidation')")
    parser.add_argument("--spells", help="Comma-separated default spells/cantrips (e.g. 'Target_ChillTouch,Target_EldritchBlast')")
    parser.add_argument("--table-uuid", help="Explicit ProgressionTableUUID override")
    parser.add_argument("--level", type=int, default=1, help="Level for default values (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_default_values(
            mod_name_or_path=args.mod,
            class_name=args.class_name,
            abilities=args.abilities,
            skills=args.skills,
            spells=args.spells,
            table_uuid=args.table_uuid,
            level=args.level,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded default values for '{args.class_name}'{tag}:")
            print(f"    Table UUID: {res['table_uuid']}")
            for f in res["files_updated"]:
                print(f"    Updated: {f}")
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
