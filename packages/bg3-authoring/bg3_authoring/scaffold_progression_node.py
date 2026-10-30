#!/usr/bin/env python3
"""
scaffold_progression_node.py - Generates and merges Larian v4.8 XML Progression and SpellList nodes.

Automates class/subclass level progression scripting in Progressions.lsx and
creates companion spell lists in Lists/SpellLists.lsx, ensuring valid Larian
XML schema and preventing level-up screen engine crashes.
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
from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import MY_MODS_DIR, resolve_mod_dir
from bg3_core.larian_parsers import split_larian_items

# Standard Vanilla Class Table UUIDs
CLASS_TABLE_UUIDS = {
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

SUBCLASS_TABLE_UUIDS = {
    "berserker": "b2a9d222-3e38-4f66-81a0-72185c51320b",
    "wildheart": "32879c22-4858-48e2-9756-a7f7a3873b7d",
    "lore": "d108c112-8a58-49a4-b11a-95d74d027f75",
    "valour": "49093221-f83f-4c63-8828-43a77b398217",
    "swords": "c4598bdb-fc07-40dd-a62c-90cc138bd76f",
    "battlemaster": "e668c3a1-2e57-46c0-9f56-8f8a41e87951",
    "eldritchknight": "d6bf0171-6349-4c9a-b73e-387a7728162a",
    "champion": "b3296827-4a76-4810-9657-68482441b70c",
    "devotion": "2b86d60e-7646-472b-a214-79d86716885c",
    "ancients": "4b66c63b-7552-4929-8013-6239619b0b12",
    "vengeance": "1482c616-e910-4b23-891c-8c563a8b5169",
    "oathbreaker": "7a82041c-9126-4405-b91e-26606503165b",
    "fiend": "2f907a95-332b-4718-885b-422a2a75313c",
    "greatoldone": "e9183948-4138-4605-8822-2c308941328b",
    "archfey": "71b95758-4116-432b-b039-310722761380",
    "hexblade": "662b1086-1848-465c-8114-563722456789",
}

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

EMPTY_SPELLLISTS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
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


def resolve_mod_public_dir(mod_path_or_slug: str, workspace_root: Path) -> tuple[Path, str]:
    """Finds mod's Public/<ModFolder> directory."""
    candidate = resolve_mod_dir(mod_path_or_slug, prefer_my_mods=True)
    if candidate is None or not candidate.is_dir():
        raise FileNotFoundError(f"Mod directory not found: '{mod_path_or_slug}'")

    public_dir = candidate / "Public"
    if not public_dir.is_dir():
        raise FileNotFoundError(f"Missing 'Public/' directory in mod: '{candidate}'")

    subdirs = [d for d in public_dir.iterdir() if d.is_dir() and d.name != "Shared"]
    if not subdirs:
        raise FileNotFoundError(f"No mod folder found under '{public_dir}'")

    return subdirs[0], candidate.name


def prettify_xml_element(elem: ET.Element) -> str:
    """Returns a cleanly indented XML string."""
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty = reparsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")
    lines = [line for line in pretty.splitlines() if line.strip()]
    return "\n".join(lines) + "\n"


def ensure_spell_list(
    spell_lists_file: Path,
    comment: str,
    spells: list[str],
    dry_run: bool = False,
) -> str:
    """Creates a new SpellList node in Lists/SpellLists.lsx and returns its UUID."""
    if spell_lists_file.exists():
        content = spell_lists_file.read_text(encoding="utf-8")
        tree = ET.fromstring(content)
    else:
        tree = ET.fromstring(EMPTY_SPELLLISTS_LSX)

    root_node = tree.find(".//region[@id='SpellLists']/node[@id='root']")
    if root_node is None:
        raise ValueError("Malformed SpellLists.lsx: missing root node.")

    children = root_node.find("children")
    if children is None:
        children = ET.SubElement(root_node, "children")

    list_uuid = str(uuid.uuid4())
    spell_str = ";".join(s.strip() for s in spells if s.strip())

    node = ET.SubElement(children, "node", id="SpellList")
    ET.SubElement(node, "attribute", id="Comment", type="LSString", value=comment)
    ET.SubElement(node, "attribute", id="Spells", type="LSString", value=spell_str)
    ET.SubElement(node, "attribute", id="UUID", type="guid", value=list_uuid)

    if not dry_run:
        spell_lists_file.parent.mkdir(parents=True, exist_ok=True)
        spell_lists_file.write_text(prettify_xml_element(tree), encoding="utf-8")

    return list_uuid


def add_or_merge_progression(
    progressions_file: Path,
    class_name: str,
    level: int,
    table_uuid: str,
    progression_type: int = 0,
    passives: list[str] | None = None,
    boosts: list[str] | None = None,
    selectors: list[str] | None = None,
    allow_improvement: bool = False,
    dry_run: bool = False,
) -> dict:
    """Adds a new Progression node or merges attributes into an existing node."""
    if progressions_file.exists():
        content = progressions_file.read_text(encoding="utf-8")
        tree = ET.fromstring(content)
    else:
        tree = ET.fromstring(EMPTY_PROGRESSIONS_LSX)

    root_node = tree.find(".//region[@id='Progressions']/node[@id='root']")
    if root_node is None:
        raise ValueError("Malformed Progressions.lsx: missing root node.")

    children = root_node.find("children")
    if children is None:
        children = ET.SubElement(root_node, "children")

    # Check if an exact progression node already exists for this Name and Level
    existing_node = None
    for p_node in children.findall("node[@id='Progression']"):
        lvl_attr = p_node.find("attribute[@id='Level']")
        name_attr = p_node.find("attribute[@id='Name']")
        if lvl_attr is not None and name_attr is not None:
            name_val = name_attr.get("value")
            if lvl_attr.get("value") == str(level) and name_val and name_val.lower() == class_name.lower():
                existing_node = p_node
                break

    action = "merged" if existing_node is not None else "created"
    node = existing_node if existing_node is not None else ET.SubElement(children, "node", id="Progression")

    def set_or_update_attr(attr_id: str, attr_type: str, new_value: str, delimiter: str = ";"):
        cur = node.find(f"attribute[@id='{attr_id}']")
        if cur is None:
            ET.SubElement(node, "attribute", id=attr_id, type=attr_type, value=new_value)
        else:
            old_val = cur.get("value", "").strip()
            if old_val:
                combined = f"{old_val}{delimiter}{new_value}"
            else:
                combined = new_value
            cur.set("value", combined)

    if existing_node is None:
        node_uuid = str(uuid.uuid4())
        ET.SubElement(node, "attribute", id="Level", type="uint8", value=str(level))
        ET.SubElement(node, "attribute", id="Name", type="LSString", value=class_name)
        ET.SubElement(node, "attribute", id="ProgressionType", type="uint8", value=str(progression_type))
        ET.SubElement(node, "attribute", id="TableUUID", type="guid", value=table_uuid)
        ET.SubElement(node, "attribute", id="UUID", type="guid", value=node_uuid)
    else:
        uuid_attr = node.find("attribute[@id='UUID']")
        node_uuid = (uuid_attr.get("value") if uuid_attr is not None else None) or str(uuid.uuid4())

    if passives:
        p_str = ";".join(p.strip() for p in passives if p.strip())
        set_or_update_attr("PassivesAdded", "LSString", p_str)

    if boosts:
        b_str = ";".join(b.strip() for b in boosts if b.strip())
        set_or_update_attr("Boosts", "LSString", b_str)

    if selectors:
        s_str = ";".join(s.strip() for s in selectors if s.strip())
        set_or_update_attr("Selectors", "LSString", s_str)

    if allow_improvement:
        cur_imp = node.find("attribute[@id='AllowImprovement']")
        if cur_imp is None:
            ET.SubElement(node, "attribute", id="AllowImprovement", type="bool", value="true")
        else:
            cur_imp.set("value", "true")

    if not dry_run:
        progressions_file.parent.mkdir(parents=True, exist_ok=True)
        progressions_file.write_text(prettify_xml_element(tree), encoding="utf-8")

    return {
        "action": action,
        "class": class_name,
        "level": level,
        "node_uuid": node_uuid,
        "table_uuid": table_uuid,
        "progression_type": progression_type,
        "file": str(progressions_file),
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold or merge Larian XML Progression and SpellList nodes into BG3 mods."
    )
    parser.add_argument("--mod", required=True, help="Mod name/slug in my_mods/ or directory path.")
    parser.add_argument("--class", dest="class_name", required=True, help="Target class or subclass name (e.g. Fighter, Wizard).")
    parser.add_argument("--level", type=int, required=True, help="Progression level (1 to 20).")
    parser.add_argument("--subclass", help="Optional subclass name (sets ProgressionType=1).")
    parser.add_argument("--multiclass", action="store_true", help="Mark progression node as multiclass entry (sets ProgressionType=2).")
    parser.add_argument("--table-uuid", help="Override standard TableUUID for custom class/subclass.")
    parser.add_argument("--passives", help="Comma-separated or semicolon-separated passive names to add.")
    parser.add_argument("--boosts", help="Comma-separated or semicolon-separated boost expressions to add.")
    parser.add_argument("--spells", help="Comma-separated spell names to create in SpellList and select.")
    parser.add_argument("--spell-count", type=int, default=1, help="Number of spells selectable (default: 1).")
    parser.add_argument("--feat", action="store_true", help="Grant feat / ability score improvement (AllowImprovement=true).")
    parser.add_argument("--dry-run", action="store_true", help="Preview generated nodes without modifying files.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")

    args = parser.parse_args()

    if args.level < 1 or args.level > 20:
        parser.error("Level must be between 1 and 20.")

    workspace_root = Path(__file__).resolve().parents[2]

    try:
        mod_public_dir, mod_slug = resolve_mod_public_dir(args.mod, workspace_root)
        progressions_file = mod_public_dir / "Progressions" / "Progressions.lsx"
        spell_lists_file = mod_public_dir / "Lists" / "SpellLists.lsx"

        # Determine TableUUID
        class_key = args.class_name.strip().lower()
        sub_key = args.subclass.strip().lower().replace(" ", "").replace("-", "").replace("_", "") if args.subclass else ""
        if args.table_uuid:
            table_uuid = args.table_uuid.strip()
        elif args.subclass:
            if sub_key in SUBCLASS_TABLE_UUIDS:
                table_uuid = SUBCLASS_TABLE_UUIDS[sub_key]
            else:
                raise ValueError(
                    f"Unknown subclass '{args.subclass}' for TableUUID lookup. Specify --table-uuid explicitly."
                )
        elif class_key in CLASS_TABLE_UUIDS:
            table_uuid = CLASS_TABLE_UUIDS[class_key]
        else:
            table_uuid = str(uuid.uuid4())

        if args.multiclass:
            progression_type = 2
        elif args.subclass:
            progression_type = 1
        else:
            progression_type = 0
        target_name = args.subclass if args.subclass else args.class_name

        # Parse lists using parenthesis-aware splitter
        passives_list = split_larian_items(args.passives) if args.passives else []
        boosts_list = split_larian_items(args.boosts) if args.boosts else []
        spells_list = split_larian_items(args.spells) if args.spells else []

        selectors_list = []
        spell_list_uuid = None

        if spells_list:
            comment = f"{target_name} Level {args.level} Spells"
            spell_list_uuid = ensure_spell_list(
                spell_lists_file=spell_lists_file,
                comment=comment,
                spells=spells_list,
                dry_run=args.dry_run,
            )
            selectors_list.append(f"SelectSpells({spell_list_uuid},{args.spell_count},0)")

        result = add_or_merge_progression(
            progressions_file=progressions_file,
            class_name=target_name,
            level=args.level,
            table_uuid=table_uuid,
            progression_type=progression_type,
            passives=passives_list,
            boosts=boosts_list,
            selectors=selectors_list,
            allow_improvement=args.feat,
            dry_run=args.dry_run,
        )

        result["mod"] = mod_slug
        if spell_list_uuid:
            result["spell_list_uuid"] = spell_list_uuid
            result["spell_lists_file"] = str(spell_lists_file)

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status_tag = color.green("[✓]")
            print(f"{status_tag} Successfully {result['action']} progression node for {target_name} Level {args.level}{tag}:")
            print(f"    Progressions file: {result['file']}")
            print(f"    Progression UUID: {result['node_uuid']}")
            print(f"    Table UUID: {result['table_uuid']}")
            if spell_list_uuid:
                print(f"    SpellList UUID: {spell_list_uuid} ({len(spells_list)} spells)")

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
