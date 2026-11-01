#!/usr/bin/env python3
"""
scaffold_visuals.py
-------------------
Visual, 3D GameObject, and appearance asset scaffolding for Baldur's Gate 3:
root templates and character creation appearance visuals.
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

VISUAL_PRESETS: dict[str, dict[str, str]] = {
    "greatsword": {"uuid": "2798c9f8-b06b-44d4-9d6c-e6d98a66329a", "description": "Standard 2H Greatsword mesh", "icon": "Item_WPN_HUM_Greatsword_A_0"},
    "longsword": {"uuid": "1865323f-b428-4791-a0a1-478875024763", "description": "Standard 1H Longsword mesh", "icon": "Item_WPN_HUM_Longsword_A_0"},
    "dagger": {"uuid": "569b0f3d-abcd-4b01-aa0b-32d0fc18002d", "description": "Standard Dagger mesh", "icon": "Item_WPN_HUM_Dagger_A_0"},
    "shortbow": {"uuid": "a461e63d-4b9a-4160-b886-5b6863643d24", "description": "Standard Shortbow mesh", "icon": "Item_WPN_HUM_Shortbow_A_0"},
    "staff": {"uuid": "2fa18ee4-90df-4c0f-8596-8a6669bc06fb", "description": "Quarterstaff / Magic Staff mesh", "icon": "Item_WPN_HUM_Quarterstaff_A_0"},
    "plate": {"uuid": "96d66e76-35ae-493f-8012-e8a8a3a0e69a", "description": "Heavy Plate Armor body mesh", "icon": "Item_ARM_Plate_Body"},
    "leather": {"uuid": "a61a9914-7235-4ac5-8063-36473cc1dd9d", "description": "Light Leather / Padded body mesh", "icon": "Item_ARM_Padded_Body"},
    "robe": {"uuid": "16867d7f-9047-4959-b13c-c672b14193b2", "description": "Spellcaster Robe body mesh", "icon": "Item_ARM_Robe_Body"},
    "helmet": {"uuid": "362c6f56-ce20-41df-811f-47356ba1bb00", "description": "Standard Helmet / Headgear mesh", "icon": "Item_ARM_Helmet"},
    "boots": {"uuid": "33eb2212-eb7e-4029-9e8d-80674f762696", "description": "Standard Boots mesh", "icon": "Item_ARM_Boots"},
    "gloves": {"uuid": "896f8a20-7299-456e-95aa-b2b0ec64ff38", "description": "Standard Gloves / Gauntlets mesh", "icon": "Item_ARM_Gloves"},
    "cloak": {"uuid": "d68e5470-36e6-424a-b5f7-640f0980a373", "description": "Standard Cloak mesh", "icon": "Item_ARM_Cloak"},
    "amulet": {"uuid": "20612f0e-2dae-45c1-8398-94840a6af489", "description": "Amulet / Necklace jewelry mesh", "icon": "Item_ARM_Amulet"},
    "ring": {"uuid": "359f2ebc-37fe-4f8e-835f-ac894ecdcf96", "description": "Ring jewelry mesh", "icon": "Item_ARM_Ring"},
    "backpack": {"uuid": "054238e2-c513-4ae3-b7c1-d41c120281b3", "description": "Container / Backpack mesh", "icon": "Item_LOOT_GEN_Backpack_A"},
}


def scaffold_root_template(
    mod_name_or_path: str,
    name: str,
    preset: str = "greatsword",
    template_type: str = "item",
    stats: str | None = None,
    visual_resource: str | None = None,
    parent_template_id: str | None = None,
    display_name: str | None = None,
    description: str | None = None,
    icon: str | None = None,
    template_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Binds stat entries to physical 3D RootTemplates in _merged.lsx."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    templates_dir = mod_folder_dir / "RootTemplates"
    templates_file = templates_dir / "_merged.lsx"

    allocated_uuid = template_uuid.strip() if template_uuid else str(uuid.uuid4())
    p_info = VISUAL_PRESETS.get(preset.lower(), VISUAL_PRESETS["greatsword"])
    vis_res = visual_resource.strip() if visual_resource else p_info["uuid"]
    icon_name = icon.strip() if icon else p_info["icon"]
    stats_name = stats.strip() if stats else name
    parent_id = parent_template_id.strip() if parent_template_id else "00000000-0000-0000-0000-000000000000"

    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    if templates_file.exists():
        tree = ET.parse(templates_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx("Templates", root_node_id="Templates")

    children = get_or_create_root_children(root, "Templates", root_node_id="Templates")

    for gnode in list(children.findall("./node[@id='GameObjects']")):
        for attr in gnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                children.remove(gnode)
                break

    go_node = ET.SubElement(children, "node", id="GameObjects")
    ET.SubElement(go_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(go_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(go_node, "attribute", id="Icon", type="FixedString", value=icon_name)
    ET.SubElement(go_node, "attribute", id="LevelName", type="FixedString", value="")
    ET.SubElement(go_node, "attribute", id="MapKey", type="FixedString", value=allocated_uuid)
    ET.SubElement(go_node, "attribute", id="Name", type="LSString", value=name)
    ET.SubElement(go_node, "attribute", id="ParentTemplateId", type="FixedString", value=parent_id)
    ET.SubElement(go_node, "attribute", id="PhysicsTemplate", type="FixedString", value="")
    ET.SubElement(go_node, "attribute", id="Stats", type="FixedString", value=stats_name)
    ET.SubElement(go_node, "attribute", id="Type", type="FixedString", value=template_type)
    ET.SubElement(go_node, "attribute", id="VisualTemplate", type="FixedString", value=vis_res)

    if not dry_run:
        templates_dir.mkdir(parents=True, exist_ok=True)
        templates_file.write_text(prettify_xml(root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="root-template",
        uuid=allocated_uuid,
        file=str(templates_file),
        dry_run=dry_run,
        details={
            "stats": stats_name,
            "visual_resource": vis_res,
            "icon": icon_name,
            "display_name_handle": f"{disp_handle};1",
            "description_handle": f"{desc_handle};1",
        },
    )


def scaffold_appearance_visual(
    mod_name_or_path: str,
    name: str,
    visual_resource: str,
    race: str = "human",
    slot: str = "Hair",
    body_type: int = 0,
    body_shape: int = 0,
    display_name: str | None = None,
    visual_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold CharacterCreationAppearanceVisuals.lsx for custom cosmetics."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    cc_dir = mod_folder_dir / "CharacterCreation"
    cc_file = cc_dir / "CharacterCreationAppearanceVisuals.lsx"

    allocated_uuid = visual_uuid.strip() if visual_uuid else str(uuid.uuid4())
    resolved_race_uuid = race.strip()

    disp_text = display_name if display_name else name
    disp_handle = generate_larian_handle()

    if cc_file.exists():
        tree = ET.parse(cc_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx("CharacterCreationAppearanceVisuals")

    children = get_or_create_root_children(root, "CharacterCreationAppearanceVisuals")

    for node in list(children.findall("./node[@id='CharacterCreationAppearanceVisual']")):
        for attr in node.findall("./attribute"):
            if attr.get("id") == "UUID" and attr.get("value") == allocated_uuid:
                children.remove(node)
                break

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

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="appearance-visual",
        uuid=allocated_uuid,
        file=str(cc_file),
        dry_run=dry_run,
        details={
            "slot": slot,
            "visual_resource": visual_resource.strip(),
            "race_uuid": resolved_race_uuid,
            "body_type": body_type,
            "body_shape": body_shape,
            "display_name_handle": f"{disp_handle};1",
            "localization_file": str(loc_file),
        },
    )
