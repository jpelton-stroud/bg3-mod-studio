#!/usr/bin/env python3
"""
scaffold_feat.py - Scaffolds Larian Patch 8 Feats and FeatDescriptions schemas.

Generates:
1. Public/<ModFolder>/Feats/Feats.lsx (feat mechanics, passives, selectors, requirements)
2. Public/<ModFolder>/Feats/FeatDescriptions.lsx (companion UI titles and descriptions)
3. Appends localization handles to Localization/English/<ModName>.xml
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
    split_larian_items,
    update_localization_xml,
)

EMPTY_FEATS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Feats">
        <node id="root">
            <children>
            </children>
        </node>
    </region>
</save>
"""

EMPTY_FEAT_DESCRIPTIONS_LSX = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="FeatDescriptions">
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


def scaffold_feat(
    mod_name_or_path: str,
    name: str,
    display_name: str | None = None,
    description: str | None = None,
    passives: str | None = None,
    selectors: str | None = None,
    requirements: str | None = None,
    can_be_picked_multiple_times: bool = False,
    feat_uuid: str | None = None,
    dry_run: bool = False,
) -> dict:
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    feats_dir = mod_folder_dir / "Feats"
    feats_file = feats_dir / "Feats.lsx"
    feat_descs_file = feats_dir / "FeatDescriptions.lsx"

    allocated_feat_uuid = feat_uuid.strip() if feat_uuid else str(uuid.uuid4())
    desc_node_uuid = str(uuid.uuid4())

    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} feat description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    passives_str = ";".join(split_larian_items(passives)) if passives else ""
    selectors_str = ";".join(split_larian_items(selectors)) if selectors else ""
    requirements_str = ";".join(split_larian_items(requirements)) if requirements else ""

    # 1. Update Feats.lsx
    if feats_file.exists():
        feats_tree = ET.parse(feats_file)
        feats_root = feats_tree.getroot()
    else:
        feats_root = ET.fromstring(EMPTY_FEATS_LSX)

    feats_children = feats_root.find(".//node[@id='root']/children")
    if feats_children is None:
        f_root_node = feats_root.find(".//node[@id='root']")
        if f_root_node is None:
            f_reg = feats_root.find(".//region[@id='Feats']")
            if f_reg is None:
                f_reg = ET.SubElement(feats_root, "region", id="Feats")
            f_root_node = ET.SubElement(f_reg, "node", id="root")
        feats_children = ET.SubElement(f_root_node, "children")

    # Remove existing node if same Name exists
    existing_feat = None
    for fnode in feats_children.findall("./node[@id='Feat']"):
        for attr in fnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                existing_feat = fnode
                break
        if existing_feat is not None:
            break

    if existing_feat is not None:
        feats_children.remove(existing_feat)

    feat_node = ET.SubElement(feats_children, "node", id="Feat")
    ET.SubElement(feat_node, "attribute", id="CanBePickedMultipleTimes", type="bool", value="true" if can_be_picked_multiple_times else "false")
    ET.SubElement(feat_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(feat_node, "attribute", id="PassivesAdded", type="LSString", value=passives_str)
    ET.SubElement(feat_node, "attribute", id="Requirements", type="LSString", value=requirements_str)
    ET.SubElement(feat_node, "attribute", id="Selectors", type="LSString", value=selectors_str)
    ET.SubElement(feat_node, "attribute", id="UUID", type="guid", value=allocated_feat_uuid)

    if not dry_run:
        feats_dir.mkdir(parents=True, exist_ok=True)
        feats_file.write_text(prettify_xml(feats_root), encoding="utf-8")

    # 2. Update FeatDescriptions.lsx
    if feat_descs_file.exists():
        desc_tree = ET.parse(feat_descs_file)
        desc_root = desc_tree.getroot()
    else:
        desc_root = ET.fromstring(EMPTY_FEAT_DESCRIPTIONS_LSX)

    desc_children = desc_root.find(".//node[@id='root']/children")
    if desc_children is None:
        d_root_node = desc_root.find(".//node[@id='root']")
        if d_root_node is None:
            d_reg = desc_root.find(".//region[@id='FeatDescriptions']")
            if d_reg is None:
                d_reg = ET.SubElement(desc_root, "region", id="FeatDescriptions")
            d_root_node = ET.SubElement(d_reg, "node", id="root")
        desc_children = ET.SubElement(d_root_node, "children")

    existing_desc = None
    for dnode in desc_children.findall("./node[@id='FeatDescription']"):
        for attr in dnode.findall("./attribute"):
            if (attr.get("id") == "ExactMatch" and attr.get("value") == name) or (attr.get("id") == "FeatId" and attr.get("value") == allocated_feat_uuid):
                existing_desc = dnode
                break
        if existing_desc is not None:
            break

    if existing_desc is not None:
        desc_children.remove(existing_desc)

    feat_desc_node = ET.SubElement(desc_children, "node", id="FeatDescription")
    ET.SubElement(feat_desc_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(feat_desc_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(feat_desc_node, "attribute", id="ExactMatch", type="FixedString", value=name)
    ET.SubElement(feat_desc_node, "attribute", id="FeatId", type="guid", value=allocated_feat_uuid)
    ET.SubElement(feat_desc_node, "attribute", id="UUID", type="guid", value=desc_node_uuid)

    if not dry_run:
        feat_descs_file.write_text(prettify_xml(desc_root), encoding="utf-8")

    # 3. Update Localization XML
    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return {
        "success": True,
        "mod": mod_slug,
        "feat_name": name,
        "feat_uuid": allocated_feat_uuid,
        "display_name_handle": f"{disp_handle};1",
        "description_handle": f"{desc_handle};1",
        "passives": passives_str,
        "selectors": selectors_str,
        "requirements": requirements_str,
        "can_be_picked_multiple_times": can_be_picked_multiple_times,
        "feats_file": str(feats_file),
        "feat_descriptions_file": str(feat_descs_file),
        "localization_file": str(loc_file),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Patch 8 Feats and FeatDescriptions with atomic localization registration.")
    parser.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    parser.add_argument("--name", required=True, help="Internal feat name (e.g. NightInfiltrator)")
    parser.add_argument("--display-name", help="Display name in game UI")
    parser.add_argument("--description", help="Description in feat selection UI")
    parser.add_argument("--passives", help="Comma- or semicolon-separated passive names to grant")
    parser.add_argument("--selectors", help="Comma- or semicolon-separated selector expressions (e.g. SelectPassives(...))")
    parser.add_argument("--requirements", help="Feat requirements expression")
    parser.add_argument("--can-be-picked-multiple-times", action="store_true", help="Allow feat to be selected more than once")
    parser.add_argument("--feat-uuid", help="Explicit UUID for this feat")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    try:
        res = scaffold_feat(
            mod_name_or_path=args.mod,
            name=args.name,
            display_name=args.display_name,
            description=args.description,
            passives=args.passives,
            selectors=args.selectors,
            requirements=args.requirements,
            can_be_picked_multiple_times=args.can_be_picked_multiple_times,
            feat_uuid=args.feat_uuid,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            tag = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded feat '{args.name}'{tag}:")
            print(f"    Feat UUID: {res['feat_uuid']}")
            print(f"    DisplayName Handle: {res['display_name_handle']}")
            print(f"    Description Handle: {res['description_handle']}")
            print(f"    Files: {res['feats_file']}, {res['feat_descriptions_file']}")
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
