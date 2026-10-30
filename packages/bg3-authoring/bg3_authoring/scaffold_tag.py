#!/usr/bin/env python3
"""
scaffold_tag.py - Scaffolds Larian Patch 8 Tags/<UUID>.lsx schemas.

Generates individual Tag LSX definitions in Public/<ModFolder>/Tags/<UUID>.lsx
for class, subclass, race, and dialogue reactivity.
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

EMPTY_TAG_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Tags">
        <node id="root">
            <children>
                <node id="Categories">
                    <children>
                    </children>
                </node>
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


def scaffold_tag(
    mod_name_or_path: str,
    name: str,
    description: str | None = None,
    display_name: str | None = None,
    categories: list[str] | None = None,
    tag_uuid: str | None = None,
    dry_run: bool = False,
) -> dict:
    workspace_root = Path(__file__).resolve().parents[2]
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path, workspace_root)

    tags_dir = mod_folder_dir / "Tags"
    allocated_uuid = tag_uuid.strip() if tag_uuid else str(uuid.uuid4())
    tag_file = tags_dir / f"{allocated_uuid}.lsx"

    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} tag description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    cats = categories if categories else ["Dialog", "CharacterSheet"]

    root = ET.fromstring(EMPTY_TAG_LSX)
    root_node = root.find(".//node[@id='root']")
    if root_node is None:
        raise ValueError("Invalid tag template structure")

    ET.SubElement(root_node, "attribute", id="Description", type="LSString", value=desc_text)
    ET.SubElement(root_node, "attribute", id="DisplayDescription", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(root_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(root_node, "attribute", id="Icon", type="FixedString", value="")
    ET.SubElement(root_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(root_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    categories_children = root.find(".//node[@id='Categories']/children")
    if categories_children is not None:
        for cat in cats:
            cnode = ET.SubElement(categories_children, "node", id="Category")
            ET.SubElement(cnode, "attribute", id="Name", type="LSString", value=cat)

    if not dry_run:
        tags_dir.mkdir(parents=True, exist_ok=True)
        tag_file.write_text(prettify_xml(root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return {
        "success": True,
        "mod": mod_slug,
        "name": name,
        "uuid": allocated_uuid,
        "categories": cats,
        "display_name_handle": f"{disp_handle};1",
        "description_handle": f"{desc_handle};1",
        "file": str(tag_file),
        "localization_file": str(loc_file),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 Tags/<UUID>.lsx dialogue and identity tags.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--name", required=True, help="Tag internal name (e.g. SHADOW_STALKER)")
    parser.add_argument("--display-name", help="Display name in character sheet")
    parser.add_argument("--description", help="Description for tag")
    parser.add_argument("--category", action="append", help="Tag category (e.g. Class, Subclass, Dialog, CharacterSheet). Can specify multiple.")
    parser.add_argument("--uuid", help="Explicit UUID for this tag")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_tag(
            mod_name_or_path=args.mod,
            name=args.name,
            description=args.description,
            display_name=args.display_name,
            categories=args.category,
            tag_uuid=args.uuid,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded tag '{args.name}'{tag}:")
            print(f"    Tag UUID: {res['uuid']}")
            print(f"    Categories: {', '.join(res['categories'])}")
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
