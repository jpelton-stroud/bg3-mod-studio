#!/usr/bin/env python3
"""
scaffold_character.py
---------------------
Character, race, origin, and dialogue tag asset scaffolding for Baldur's Gate 3:
races, subraces, origins, and tag definitions.
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from typing import Any

from bg3_core.larian_parsers import generate_larian_handle, update_localization_xml

from bg3_authoring.scaffold_common import (
    ScaffoldResult,
    create_empty_lsx,
    get_or_create_root_children,
    prettify_xml,
    resolve_mod_paths,
)

VANILLA_PARENT_RACES: dict[str, str] = {
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
VANILLA_RACE_UUIDS = VANILLA_PARENT_RACES


def _resolve_parent_race_guid(
    parent_race: str | None, parent_guid: str | None
) -> tuple[str, bool]:
    if parent_race:
        key = parent_race.strip().lower()
        if key in VANILLA_PARENT_RACES:
            return VANILLA_PARENT_RACES[key], True
        raise ValueError(
            f"Unknown vanilla parent race '{parent_race}'. Specify a valid preset or provide --parent-guid."
        )
    if parent_guid:
        resolved = parent_guid.strip()
        return resolved, (resolved != "00000000-0000-0000-0000-000000000000")
    return "00000000-0000-0000-0000-000000000000", False


def _build_race_node(
    children: ET.Element,
    name: str,
    allocated_uuid: str,
    allocated_table_uuid: str,
    resolved_parent_guid: str,
    disp_handle: str,
    desc_handle: str,
) -> None:
    for rnode in list(children.findall("./node[@id='Race']")):
        for attr in rnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                children.remove(rnode)
                break

    race_node = ET.SubElement(children, "node", id="Race")
    ET.SubElement(race_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(race_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(race_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(race_node, "attribute", id="ParentGuid", type="guid", value=resolved_parent_guid)
    ET.SubElement(race_node, "attribute", id="ProgressionTableUUID", type="guid", value=allocated_table_uuid)
    ET.SubElement(race_node, "attribute", id="UUID", type="guid", value=allocated_uuid)


def _build_race_description_node(
    children: ET.Element,
    name: str,
    allocated_uuid: str,
    desc_node_uuid: str,
    disp_handle: str,
    desc_handle: str,
) -> None:
    for rdnode in list(children.findall("./node[@id='RaceDescription']")):
        for attr in rdnode.findall("./attribute"):
            if (attr.get("id") == "ExactMatch" and attr.get("value") == name) or (
                attr.get("id") == "RaceId" and attr.get("value") == allocated_uuid
            ):
                children.remove(rdnode)
                break

    rd_node = ET.SubElement(children, "node", id="RaceDescription")
    ET.SubElement(rd_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(rd_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(rd_node, "attribute", id="ExactMatch", type="FixedString", value=name)
    ET.SubElement(rd_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(rd_node, "attribute", id="RaceId", type="guid", value=allocated_uuid)
    ET.SubElement(rd_node, "attribute", id="UUID", type="guid", value=desc_node_uuid)


def scaffold_race(
    mod_name_or_path: str,
    name: str,
    display_name: str | None = None,
    description: str | None = None,
    parent_race: str | None = None,
    parent_guid: str | None = None,
    race_uuid: str | None = None,
    progression_table_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold Races.lsx and RaceDescriptions.lsx for custom races/subraces."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    races_dir = mod_folder_dir / "Races"
    races_file = races_dir / "Races.lsx"
    race_descs_file = races_dir / "RaceDescriptions.lsx"

    allocated_uuid = race_uuid.strip() if race_uuid else str(uuid.uuid4())
    allocated_table_uuid = progression_table_uuid.strip() if progression_table_uuid else str(uuid.uuid4())
    desc_node_uuid = str(uuid.uuid4())

    resolved_parent_guid, is_subrace = _resolve_parent_race_guid(parent_race, parent_guid)

    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} race description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    # 1. Update Races.lsx
    if races_file.exists():
        r_tree = ET.parse(races_file)
        r_root = r_tree.getroot()
    else:
        r_root = create_empty_lsx("Races")

    r_children = get_or_create_root_children(r_root, "Races")
    _build_race_node(
        r_children, name, allocated_uuid, allocated_table_uuid,
        resolved_parent_guid, disp_handle, desc_handle
    )
    if not dry_run:
        races_dir.mkdir(parents=True, exist_ok=True)
        races_file.write_text(prettify_xml(r_root), encoding="utf-8")

    # 2. Update RaceDescriptions.lsx
    if race_descs_file.exists():
        rd_tree = ET.parse(race_descs_file)
        rd_root = rd_tree.getroot()
    else:
        rd_root = create_empty_lsx("RaceDescriptions")

    rd_children = get_or_create_root_children(rd_root, "RaceDescriptions")
    _build_race_description_node(
        rd_children, name, allocated_uuid, desc_node_uuid,
        disp_handle, desc_handle
    )
    if not dry_run:
        race_descs_file.write_text(prettify_xml(rd_root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="race",
        uuid=allocated_uuid,
        file=str(races_file),
        dry_run=dry_run,
        details={
            "table_uuid": allocated_table_uuid,
            "is_subrace": is_subrace,
            "parent_guid": resolved_parent_guid,
            "display_name_handle": f"{disp_handle};1",
            "description_handle": f"{desc_handle};1",
            "races_file": str(races_file),
            "race_descriptions_file": str(race_descs_file),
            "localization_file": str(loc_file),
        },
    )


def scaffold_origin(
    mod_name_or_path: str,
    name: str,
    display_name: str | None = None,
    description: str | None = None,
    class_uuid: str | None = None,
    race_uuid: str | None = None,
    origin_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold Origins.lsx character presets."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    origins_dir = mod_folder_dir / "Origins"
    origins_file = origins_dir / "Origins.lsx"

    allocated_uuid = origin_uuid.strip() if origin_uuid else str(uuid.uuid4())
    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} origin description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    c_guid = class_uuid.strip() if class_uuid else "00000000-0000-0000-0000-000000000000"
    r_guid = race_uuid.strip() if race_uuid else "00000000-0000-0000-0000-000000000000"

    if origins_file.exists():
        tree = ET.parse(origins_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx("Origins")

    children = get_or_create_root_children(root, "Origins")

    for onode in list(children.findall("./node[@id='Origin']")):
        for attr in onode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                children.remove(onode)
                break

    origin_node = ET.SubElement(children, "node", id="Origin")
    ET.SubElement(origin_node, "attribute", id="ClassUUID", type="guid", value=c_guid)
    ET.SubElement(origin_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(origin_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(origin_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(origin_node, "attribute", id="RaceUUID", type="guid", value=r_guid)
    ET.SubElement(origin_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        origins_dir.mkdir(parents=True, exist_ok=True)
        origins_file.write_text(prettify_xml(root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="origin",
        uuid=allocated_uuid,
        file=str(origins_file),
        dry_run=dry_run,
        details={
            "display_name_handle": f"{disp_handle};1",
            "description_handle": f"{desc_handle};1",
            "origins_file": str(origins_file),
            "localization_file": str(loc_file),
        },
    )


def scaffold_tag(
    mod_name_or_path: str,
    name: str,
    description: str | None = None,
    display_name: str | None = None,
    categories: list[str] | None = None,
    tag_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold Tags/<UUID>.lsx dialogue and identity tags."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    tags_dir = mod_folder_dir / "Tags"
    allocated_uuid = tag_uuid.strip() if tag_uuid else str(uuid.uuid4())
    tag_file = tags_dir / f"{allocated_uuid}.lsx"

    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} tag description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()
    cats = categories if categories else ["Dialog", "CharacterSheet"]

    root = create_empty_lsx("Tags")
    root_node = root.find(".//node[@id='root']")
    if root_node is None:
        raise ValueError("Invalid tag root structure")

    ET.SubElement(root_node, "attribute", id="Description", type="LSString", value=desc_text)
    ET.SubElement(root_node, "attribute", id="DisplayDescription", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(root_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(root_node, "attribute", id="Icon", type="FixedString", value="")
    ET.SubElement(root_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(root_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    categories_node = ET.SubElement(root_node, "children")
    cat_node_wrapper = ET.SubElement(categories_node, "node", id="Categories")
    cat_children = ET.SubElement(cat_node_wrapper, "children")
    for cat in cats:
        cnode = ET.SubElement(cat_children, "node", id="Category")
        ET.SubElement(cnode, "attribute", id="Name", type="LSString", value=cat)

    if not dry_run:
        tags_dir.mkdir(parents=True, exist_ok=True)
        tag_file.write_text(prettify_xml(root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="tag",
        uuid=allocated_uuid,
        file=str(tag_file),
        dry_run=dry_run,
        details={
            "categories": cats,
            "display_name_handle": f"{disp_handle};1",
            "description_handle": f"{desc_handle};1",
            "localization_file": str(loc_file),
        },
    )
