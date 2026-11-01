#!/usr/bin/env python3
"""
scaffold_asset.py - Unified Larian Patch 8 Asset Scaffolding Engine.

Consolidates all asset authoring schemas into a single data-driven engine:
- Text stats: Weapons, Armor, Objects, Passives, Statuses, Spells, Interrupts
- Character creation: ClassDescriptions, Races, Origins, AppearanceVisuals
- Progression & mechanics: Progressions, Feats, LevelMapValues, DefaultValues, ActionResources
- Lists & Visuals: SpellLists, PassiveLists, RootTemplates (GameObjects), Icon UVs, Tags
"""

import argparse
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from xml.dom import minidom

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import resolve_mod_dir
from bg3_core.larian_parsers import (
    generate_larian_handle,
    split_larian_items,
    update_localization_xml,
)

# -----------------------------------------------------------------------------
# Shared Constants & Engine Registries
# -----------------------------------------------------------------------------

PATCH_8_VERSION_ATTRIBUTES = {
    "major": "4",
    "minor": "8",
    "revision": "0",
    "build": "700",
}

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
CLASS_TABLE_UUIDS = VANILLA_CLASS_TABLES

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

VANILLA_PARENT_CLASSES = {
    "barbarian": {"guid": "d8cad572-04ae-4920-a372-30772ae38e55", "subclass_level": 3, "table_uuid": "60bb7dc1-7143-400e-ae34-7d8da6c8a782"},
    "bard": {"guid": "92cdc989-c760-4928-8684-25e22709e897", "subclass_level": 3, "table_uuid": "229c98da-2cd1-4a5e-a579-43c1687ed991"},
    "cleric": {"guid": "114e7aee-d1d4-4271-8414-3d42ee450cdd", "subclass_level": 1, "table_uuid": "64474b62-b4f5-46b3-b94a-c676c6da3116"},
    "druid": {"guid": "457e0a4e-92b1-4ec0-b0cc-bf606ea490ab", "subclass_level": 2, "table_uuid": "6e34618d-4040-4c65-815c-18c92e4ba13d"},
    "fighter": {"guid": "72764534-fb3d-4091-8850-ff6db1e3ca9c", "subclass_level": 3, "table_uuid": "ba4e707e-4bbd-4630-963b-ce2f2947f971"},
    "monk": {"guid": "e1e4a21f-9405-46ec-81a0-cc2fb6da4f74", "subclass_level": 3, "table_uuid": "fe1319a2-86be-469c-aab5-e3b0bd714e0e"},
    "paladin": {"guid": "ff4d9497-0c30-44d7-8677-627c2fa4b7ab", "subclass_level": 1, "table_uuid": "ba2afe85-acba-4ea1-a238-2b4543f47821"},
    "ranger": {"guid": "36be1680-e773-450c-b570-514d4ff740f5", "subclass_level": 3, "table_uuid": "0aa30731-4f33-4452-a1e1-9404662cb829"},
    "rogue": {"guid": "e8b01dc7-d222-4735-ad53-4170c22a1645", "subclass_level": 3, "table_uuid": "9a44e887-44da-4246-aab4-6e6017ec6acc"},
    "sorcerer": {"guid": "784001e2-96f7-4701-9d1b-944d0223754e", "subclass_level": 1, "table_uuid": "e2416b02-953d-422f-beca-90802c6cad3e"},
    "warlock": {"guid": "b4225a4b-4f9e-4789-a47c-774ea93842c3", "subclass_level": 1, "table_uuid": "a7a9b714-d4ee-46de-821b-0e3919e3f446"},
    "wizard": {"guid": "a86596b0-73cc-4621-9943-6d4e0d45255e", "subclass_level": 2, "table_uuid": "d77e6444-37dc-40c2-90ea-4c54964648a8"},
}

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

VANILLA_RACE_UUIDS = VANILLA_PARENT_RACES

VISUAL_PRESETS = {
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

STAT_TYPE_CONFIG: dict[str, dict[str, Any]] = {
    "weapon": {"file": "Weapon.txt", "type_header": 'type "Weapon"', "default_using": "_BaseWeapon", "defaults": {"Damage Type": "Slashing", "Damage": "1d8", "ValueLevel": "1", "Rarity": "Rare", "DefaultBoosts": "WeaponEnchantment(1)"}},
    "armor": {"file": "Armor.txt", "type_header": 'type "Armor"', "default_using": "_Armor", "defaults": {"Slot": "Breast", "ArmorClass": "15", "ArmorType": "Leather", "Rarity": "Rare"}},
    "amulet": {"file": "Armor.txt", "type_header": 'type "Armor"', "default_using": "_Armor", "defaults": {"Slot": "Amulet", "Rarity": "Rare"}},
    "ring": {"file": "Armor.txt", "type_header": 'type "Armor"', "default_using": "_Armor", "defaults": {"Slot": "Ring", "Rarity": "Rare"}},
    "object": {"file": "Object.txt", "type_header": 'type "Object"', "default_using": "_Object", "defaults": {"Rarity": "Common", "Weight": "0.5"}},
    "passivedata": {"file": "Passive.txt", "type_header": 'type "PassiveData"', "default_using": None, "defaults": {"Icon": "PassiveFeature_Generic", "Properties": "Highlighted"}},
    "status_boost": {"file": "Status_BOOST.txt", "type_header": 'type "StatusData"', "default_using": None, "defaults": {"StatusType": "BOOST", "Icon": "Generic_Boost"}},
    "spell_target": {"file": "Spell_Target.txt", "type_header": 'type "SpellData"', "default_using": None, "defaults": {"SpellType": "Target", "Level": "3", "SpellSchool": "Evocation", "TargetRadius": "18"}},
    "spell_shout": {"file": "Spell_Shout.txt", "type_header": 'type "SpellData"', "default_using": None, "defaults": {"SpellType": "Shout", "Level": "3", "SpellSchool": "Abjuration"}},
    "spell_projectile": {"file": "Spell_Projectile.txt", "type_header": 'type "SpellData"', "default_using": None, "defaults": {"SpellType": "Projectile", "Level": "3", "SpellSchool": "Evocation", "TargetRadius": "18"}},
    "spell_zone": {"file": "Spell_Zone.txt", "type_header": 'type "SpellData"', "default_using": None, "defaults": {"SpellType": "Zone", "Level": "3", "SpellSchool": "Evocation"}},
    "spell_teleport": {"file": "Spell_Teleport.txt", "type_header": 'type "SpellData"', "default_using": None, "defaults": {"SpellType": "Teleport", "Level": "2", "SpellSchool": "Conjuration", "TargetRadius": "18"}},
    "spell_rush": {"file": "Spell_Rush.txt", "type_header": 'type "SpellData"', "default_using": None, "defaults": {"SpellType": "Rush", "Level": "1", "SpellSchool": "Transmutation", "TargetRadius": "9"}},
    "spell_path": {"file": "Spell_Path.txt", "type_header": 'type "SpellData"', "default_using": None, "defaults": {"SpellType": "Path", "Level": "1", "SpellSchool": "Conjuration", "TargetRadius": "18"}},
    "interrupt": {"file": "Interrupt.txt", "type_header": 'type "InterruptData"', "default_using": None, "defaults": {"InterruptType": "Spell", "Conditions": "Self()"}},
    "equipment": {"file": "Equipment.txt", "type_header": 'type "Equipment"', "default_using": None, "defaults": {"InitialLoadout": "Yes"}},
    "character": {"file": "Character.txt", "type_header": 'type "Character"', "default_using": "_Hero", "defaults": {"StrengthMax": "30", "DexterityMax": "30", "ConstitutionMax": "30", "IntelligenceMax": "30", "WisdomMax": "30", "CharismaMax": "30"}},
}

# -----------------------------------------------------------------------------
# XML & Path Core Plumbing
# -----------------------------------------------------------------------------

def prettify_xml(element: ET.Element) -> str:
    """Returns a cleanly indented XML string."""
    rough = ET.tostring(element, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    clean = "\n".join([line for line in reparsed.toprettyxml(indent="    ").split("\n") if line.strip()])
    return clean + "\n"


def resolve_mod_paths(mod_name_or_path: str, workspace_root: Path | None = None) -> tuple[Path, Path, Path, str]:
    """Resolves mod root directory, Public/<ModFolder> directory, and English localization XML path."""
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


def create_empty_lsx(region_id: str, root_node_id: str = "root") -> ET.Element:
    """Creates a standard Larian v4.8 LSX root element with region and empty children."""
    root = ET.Element("save")
    ET.SubElement(root, "version", **PATCH_8_VERSION_ATTRIBUTES)
    reg = ET.SubElement(root, "region", id=region_id)
    r_node = ET.SubElement(reg, "node", id=root_node_id)
    ET.SubElement(r_node, "children")
    return root


def get_or_create_root_children(root: ET.Element, region_id: str, root_node_id: str = "root") -> ET.Element:
    """Safely traverses or builds the <region>/<node id='...'>/<children> hierarchy."""
    children = root.find(f".//region[@id='{region_id}']/node[@id='{root_node_id}']/children")
    if children is not None:
        return children

    children = root.find(f".//node[@id='{root_node_id}']/children")
    if children is not None:
        return children

    r_node = root.find(f".//node[@id='{root_node_id}']")
    if r_node is None:
        reg = root.find(f".//region[@id='{region_id}']")
        if reg is None:
            reg = ET.SubElement(root, "region", id=region_id)
        r_node = ET.SubElement(reg, "node", id=root_node_id)

    children = ET.SubElement(r_node, "children")
    return children


# -----------------------------------------------------------------------------
# Asset Scaffolding Implementations
# -----------------------------------------------------------------------------

def scaffold_class(
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
    register_in_parent: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold Patch 8 Class & Subclass definitions."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    class_desc_dir = mod_folder_dir / "ClassDescriptions"
    class_desc_file = class_desc_dir / "ClassDescriptions.lsx"
    prog_desc_dir = mod_folder_dir / "Progressions"
    prog_desc_file = prog_desc_dir / "ProgressionDescriptions.lsx"
    progressions_file = prog_desc_dir / "Progressions.lsx"

    allocated_class_uuid = class_uuid.strip() if class_uuid else str(uuid.uuid4())
    allocated_table_uuid = progression_table_uuid.strip() if progression_table_uuid else str(uuid.uuid4())
    prog_desc_node_uuid = str(uuid.uuid4())

    resolved_parent_guid = "00000000-0000-0000-0000-000000000000"
    is_subclass = False

    if parent_class:
        key = parent_class.strip().lower()
        if key in VANILLA_PARENT_CLASSES:
            preset = VANILLA_PARENT_CLASSES[key]
            resolved_parent_guid = preset["guid"]
            is_subclass = True
        else:
            raise ValueError(f"Unknown vanilla parent class '{parent_class}'. Specify a valid preset or provide --parent-guid.")
    elif parent_guid:
        resolved_parent_guid = parent_guid.strip()
        is_subclass = (resolved_parent_guid != "00000000-0000-0000-0000-000000000000")

    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} class description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    # 1. Update ClassDescriptions.lsx
    if class_desc_file.exists():
        cd_tree = ET.parse(class_desc_file)
        cd_root = cd_tree.getroot()
    else:
        cd_root = create_empty_lsx("ClassDescriptions")

    cd_children = get_or_create_root_children(cd_root, "ClassDescriptions")

    existing_node = None
    for cnode in cd_children.findall("./node[@id='ClassDescription']"):
        for attr in cnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                existing_node = cnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        cd_children.remove(existing_node)

    class_node = ET.SubElement(cd_children, "node", id="ClassDescription")
    ET.SubElement(class_node, "attribute", id="BaseHp", type="int32", value=str(base_hp))
    ET.SubElement(class_node, "attribute", id="CharacterCreationPose", type="guid", value="0f07ec6e-4ef0-434e-9a51-1353260ccff8")
    ET.SubElement(class_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(class_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(class_node, "attribute", id="HpPerLevel", type="int32", value=str(hp_per_level))
    ET.SubElement(class_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(class_node, "attribute", id="ParentGuid", type="guid", value=resolved_parent_guid)
    ET.SubElement(class_node, "attribute", id="PrimaryAbility", type="uint8", value=str(primary_ability))
    ET.SubElement(class_node, "attribute", id="ProgressionTableUUID", type="guid", value=allocated_table_uuid)
    ET.SubElement(class_node, "attribute", id="SoundClassType", type="FixedString", value="Fighter" if not is_subclass else "")
    ET.SubElement(class_node, "attribute", id="SpellCastingAbility", type="uint8", value=str(spell_casting_ability))
    ET.SubElement(class_node, "attribute", id="UUID", type="guid", value=allocated_class_uuid)

    tags_node = ET.SubElement(class_node, "children")
    ET.SubElement(tags_node, "node", id="Tags")

    if not dry_run:
        class_desc_dir.mkdir(parents=True, exist_ok=True)
        class_desc_file.write_text(prettify_xml(cd_root), encoding="utf-8")

    # 2. Update ProgressionDescriptions.lsx
    if prog_desc_file.exists():
        pd_tree = ET.parse(prog_desc_file)
        pd_root = pd_tree.getroot()
    else:
        pd_root = create_empty_lsx("ProgressionDescriptions")

    pd_children = get_or_create_root_children(pd_root, "ProgressionDescriptions")

    existing_pd = None
    for pnode in pd_children.findall("./node[@id='ProgressionDescription']"):
        for attr in pnode.findall("./attribute"):
            if (attr.get("id") == "ExactMatch" and attr.get("value") == name) or (attr.get("id") == "ClassId" and attr.get("value") == allocated_class_uuid):
                existing_pd = pnode
                break
        if existing_pd is not None:
            break

    if existing_pd is not None:
        pd_children.remove(existing_pd)

    pd_node = ET.SubElement(pd_children, "node", id="ProgressionDescription")
    ET.SubElement(pd_node, "attribute", id="ClassId", type="guid", value=allocated_class_uuid)
    ET.SubElement(pd_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(pd_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(pd_node, "attribute", id="ExactMatch", type="FixedString", value=name)
    ET.SubElement(pd_node, "attribute", id="ProgressionTableId", type="guid", value=allocated_table_uuid)
    ET.SubElement(pd_node, "attribute", id="UUID", type="guid", value=prog_desc_node_uuid)

    if not dry_run:
        prog_desc_dir.mkdir(parents=True, exist_ok=True)
        prog_desc_file.write_text(prettify_xml(pd_root), encoding="utf-8")

    # 3. Register in parent Progressions.lsx if subclass
    parent_registered = False
    if is_subclass and register_in_parent and progressions_file.exists():
        ps_tree = ET.parse(progressions_file)
        ps_root = ps_tree.getroot()
        target_table_uuid = VANILLA_CLASS_TABLES.get(parent_class.lower()) if parent_class else None
        target_node = None
        for pnode in ps_root.findall(".//node[@id='Progression']"):
            t_uuid = None
            lvl = None
            for attr in pnode.findall("./attribute"):
                if attr.get("id") == "TableUUID":
                    t_uuid = attr.get("value")
                elif attr.get("id") == "Level":
                    lvl = attr.get("value")
            if target_table_uuid and t_uuid == target_table_uuid and (lvl in ("1", "2", "3")):
                target_node = pnode
                break

        if target_node is not None:
            subclasses_node = target_node.find(".//node[@id='SubClasses']")
            if subclasses_node is None:
                ch = target_node.find("./children")
                if ch is None:
                    ch = ET.SubElement(target_node, "children")
                subclasses_node = ET.SubElement(ch, "node", id="SubClasses")

            sc_children = subclasses_node.find("./children")
            if sc_children is None:
                sc_children = ET.SubElement(subclasses_node, "children")

            already_present = any(
                attr.get("id") == "Object" and attr.get("value") == allocated_class_uuid
                for sc in sc_children.findall("./node[@id='SubClass']")
                for attr in sc.findall("./attribute")
            )
            if not already_present:
                new_sc = ET.SubElement(sc_children, "node", id="SubClass")
                ET.SubElement(new_sc, "attribute", id="Object", type="guid", value=allocated_class_uuid)
                parent_registered = True
                if not dry_run:
                    progressions_file.write_text(prettify_xml(ps_root), encoding="utf-8")

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


def scaffold_progression(
    mod_name_or_path: str,
    name: str,
    level: int,
    table_uuid: str | None = None,
    progression_type: int = 0,
    passives: str | None = None,
    spells: str | None = None,
    selectors: str | None = None,
    hp_formula: str = "1",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold Larian v4.8 XML Progression and companion SpellList nodes."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    progressions_dir = mod_folder_dir / "Progressions"
    progressions_file = progressions_dir / "Progressions.lsx"
    spell_lists_dir = mod_folder_dir / "Lists"
    spell_lists_file = spell_lists_dir / "SpellLists.lsx"

    target_table_uuid = table_uuid.strip() if table_uuid else CLASS_TABLE_UUIDS.get(name.lower(), SUBCLASS_TABLE_UUIDS.get(name.lower()))
    if not target_table_uuid:
        target_table_uuid = str(uuid.uuid4())

    progression_uuid = str(uuid.uuid4())
    passives_added = ";".join(split_larian_items(passives)) if passives else ""
    selectors_list = split_larian_items(selectors) if selectors else []

    # 1. Update Progressions.lsx
    if progressions_file.exists():
        p_tree = ET.parse(progressions_file)
        p_root = p_tree.getroot()
    else:
        p_root = create_empty_lsx("Progressions")

    p_children = get_or_create_root_children(p_root, "Progressions")

    # Remove existing node if TableUUID and Level match
    existing_node = None
    for pnode in p_children.findall("./node[@id='Progression']"):
        match_table = False
        match_lvl = False
        for attr in pnode.findall("./attribute"):
            if attr.get("id") == "TableUUID" and attr.get("value") == target_table_uuid:
                match_table = True
            elif attr.get("id") == "Level" and attr.get("value") == str(level):
                match_lvl = True
        if match_table and match_lvl:
            existing_node = pnode
            break

    if existing_node is not None:
        p_children.remove(existing_node)

    prog_node = ET.SubElement(p_children, "node", id="Progression")
    ET.SubElement(prog_node, "attribute", id="AllowImprovement", type="bool", value="true" if level in (4, 8, 12, 16, 19) else "false")
    ET.SubElement(prog_node, "attribute", id="Level", type="uint8", value=str(level))
    ET.SubElement(prog_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(prog_node, "attribute", id="PassivesAdded", type="LSString", value=passives_added)
    ET.SubElement(prog_node, "attribute", id="ProgressionType", type="uint8", value=str(progression_type))
    ET.SubElement(prog_node, "attribute", id="TableUUID", type="guid", value=target_table_uuid)
    ET.SubElement(prog_node, "attribute", id="UUID", type="guid", value=progression_uuid)

    # 2. Companion SpellList generation if spells specified
    spell_list_uuid = None
    if spells:
        spell_list_uuid = str(uuid.uuid4())
        spell_items = ";".join(split_larian_items(spells))
        selectors_list.append(f"SelectSpells({spell_list_uuid},1,0)")

        if spell_lists_file.exists():
            sl_tree = ET.parse(spell_lists_file)
            sl_root = sl_tree.getroot()
        else:
            sl_root = create_empty_lsx("SpellLists")

        sl_children = get_or_create_root_children(sl_root, "SpellLists")
        sl_node = ET.SubElement(sl_children, "node", id="SpellList")
        ET.SubElement(sl_node, "attribute", id="Comment", type="LSString", value=f"{name} Level {level} Spells")
        ET.SubElement(sl_node, "attribute", id="Spells", type="LSString", value=spell_items)
        ET.SubElement(sl_node, "attribute", id="UUID", type="guid", value=spell_list_uuid)

        if not dry_run:
            spell_lists_dir.mkdir(parents=True, exist_ok=True)
            spell_lists_file.write_text(prettify_xml(sl_root), encoding="utf-8")

    selectors_str = ";".join(selectors_list)
    ET.SubElement(prog_node, "attribute", id="Selectors", type="LSString", value=selectors_str)

    if not dry_run:
        progressions_dir.mkdir(parents=True, exist_ok=True)
        progressions_file.write_text(prettify_xml(p_root), encoding="utf-8")

    return {
        "success": True,
        "mod": mod_slug,
        "name": name,
        "level": level,
        "table_uuid": target_table_uuid,
        "progression_uuid": progression_uuid,
        "spell_list_uuid": spell_list_uuid,
        "passives": passives_added,
        "selectors": selectors_str,
        "file": str(progressions_file),
        "dry_run": dry_run,
    }


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
) -> dict[str, Any]:
    """Scaffold Patch 8 Feats and FeatDescriptions."""
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
        feats_root = create_empty_lsx("Feats")

    feats_children = get_or_create_root_children(feats_root, "Feats")

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
        desc_root = create_empty_lsx("FeatDescriptions")

    desc_children = get_or_create_root_children(desc_root, "FeatDescriptions")

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


def scaffold_action_resource(
    mod_name_or_path: str,
    name: str,
    display_name: str | None = None,
    description: str | None = None,
    replenish_type: str = "ShortRest",
    max_level: int = 0,
    dice_type: int = 0,
    show_on_action_panel: bool = True,
    is_spell_resource: bool = False,
    party_action_resource: bool = False,
    resource_uuid: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold ActionResourceDefinitions schemas."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    res_dir = mod_folder_dir / "ActionResourceDefinitions"
    res_file = res_dir / "ActionResourceDefinitions.lsx"

    allocated_uuid = resource_uuid.strip() if resource_uuid else str(uuid.uuid4())
    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} resource description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    if res_file.exists():
        res_tree = ET.parse(res_file)
        res_root = res_tree.getroot()
    else:
        res_root = create_empty_lsx("ActionResourceDefinitions")

    res_children = get_or_create_root_children(res_root, "ActionResourceDefinitions")

    existing_node = None
    for rnode in res_children.findall("./node[@id='ActionResourceDefinition']"):
        for attr in rnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                existing_node = rnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        res_children.remove(existing_node)

    node = ET.SubElement(res_children, "node", id="ActionResourceDefinition")
    ET.SubElement(node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(node, "attribute", id="DiceType", type="uint32", value=str(dice_type))
    ET.SubElement(node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(node, "attribute", id="Error", type="FixedString", value="ActionResourceError_NotEnoughResources")
    ET.SubElement(node, "attribute", id="IsSpellResource", type="bool", value="true" if is_spell_resource else "false")
    ET.SubElement(node, "attribute", id="MaxLevel", type="uint32", value=str(max_level))
    ET.SubElement(node, "attribute", id="MaxValue", type="uint32", value="0")
    ET.SubElement(node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(node, "attribute", id="PartyActionResource", type="bool", value="true" if party_action_resource else "false")
    ET.SubElement(node, "attribute", id="ReplenishType", type="FixedString", value=replenish_type)
    ET.SubElement(node, "attribute", id="ShowOnActionResourcePanel", type="bool", value="true" if show_on_action_panel else "false")
    ET.SubElement(node, "attribute", id="UUID", type="guid", value=allocated_uuid)
    ET.SubElement(node, "attribute", id="UpdatesSpellPowerLevel", type="bool", value="false")

    if not dry_run:
        res_dir.mkdir(parents=True, exist_ok=True)
        res_file.write_text(prettify_xml(res_root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return {
        "success": True,
        "mod": mod_slug,
        "resource_name": name,
        "resource_uuid": allocated_uuid,
        "replenish_type": replenish_type,
        "max_level": max_level,
        "dice_type": dice_type,
        "show_on_action_panel": show_on_action_panel,
        "is_spell_resource": is_spell_resource,
        "display_name_handle": f"{disp_handle};1",
        "description_handle": f"{desc_handle};1",
        "action_resources_file": str(res_file),
        "localization_file": str(loc_file),
        "dry_run": dry_run,
    }


def scaffold_spell_list(
    mod_name_or_path: str,
    list_type: str = "spells",
    comment: str | None = None,
    items: str | None = None,
    list_uuid: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold SpellLists.lsx and PassiveLists.lsx selector lists."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    lists_dir = mod_folder_dir / "Lists"
    is_passive = (list_type.lower() in ("passives", "passive"))
    target_file = lists_dir / ("PassiveLists.lsx" if is_passive else "SpellLists.lsx")
    region_id = "PassiveLists" if is_passive else "SpellLists"
    node_id = "PassiveList" if is_passive else "SpellList"
    item_attr = "Passives" if is_passive else "Spells"

    allocated_uuid = list_uuid.strip() if list_uuid else str(uuid.uuid4())
    parsed_items = split_larian_items(items) if items else []
    items_str = ";".join(parsed_items)
    comment_str = comment if comment else f"Custom {region_id} entry"

    if target_file.exists():
        tree = ET.parse(target_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx(region_id)

    children = get_or_create_root_children(root, region_id)

    existing_node = None
    for lnode in children.findall(f"./node[@id='{node_id}']"):
        for attr in lnode.findall("./attribute"):
            if (attr.get("id") == "UUID" and attr.get("value") == allocated_uuid) or (comment and attr.get("id") == "Comment" and attr.get("value") == comment):
                existing_node = lnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        children.remove(existing_node)

    list_node = ET.SubElement(children, "node", id=node_id)
    ET.SubElement(list_node, "attribute", id="Comment", type="LSString", value=comment_str)
    ET.SubElement(list_node, "attribute", id=item_attr, type="LSString", value=items_str)
    ET.SubElement(list_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        lists_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(prettify_xml(root), encoding="utf-8")

    return {
        "success": True,
        "mod": mod_slug,
        "type": "passives" if is_passive else "spells",
        "uuid": allocated_uuid,
        "comment": comment_str,
        "items": parsed_items,
        "file": str(target_file),
        "dry_run": dry_run,
    }


def scaffold_level_map(
    mod_name_or_path: str,
    name: str,
    levels: str,
    preferred_dice_type: int | None = None,
    level_map_uuid: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold LevelMapValues scaling curves across levels 1–20."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    lm_dir = mod_folder_dir / "LevelMapValues"
    lm_file = lm_dir / "LevelMapValues.lsx"

    allocated_uuid = level_map_uuid.strip() if level_map_uuid else str(uuid.uuid4())

    # Parse level mappings
    explicit: dict[int, str] = {}
    tokens = re.split(r"[,;]\s*", levels.strip())
    for token in tokens:
        if "=" in token:
            lvl_str, val = token.split("=", 1)
            explicit[int(lvl_str.strip())] = val.strip()

    if not explicit:
        raise ValueError("No valid level mappings found in format 'level=value' (e.g. '1=1d6,5=2d6').")

    resolved_levels: dict[int, str] = {}
    curr = explicit.get(1, list(explicit.values())[0])
    for lvl in range(1, 21):
        if lvl in explicit:
            curr = explicit[lvl]
        resolved_levels[lvl] = curr

    dice_type = preferred_dice_type
    if dice_type is None:
        dice_type = 0
        for val in resolved_levels.values():
            m = re.search(r"d(\d+)", val, re.IGNORECASE)
            if m:
                dice_type = int(m.group(1))
                break

    if lm_file.exists():
        tree = ET.parse(lm_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx("LevelMapValues")

    children = get_or_create_root_children(root, "LevelMapValues")

    existing_node = None
    for lnode in children.findall("./node[@id='LevelMapSeries']"):
        for attr in lnode.findall("./attribute"):
            if (attr.get("id") == "Name" and attr.get("value") == name) or (attr.get("id") == "UUID" and attr.get("value") == allocated_uuid):
                existing_node = lnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        children.remove(existing_node)

    series_node = ET.SubElement(children, "node", id="LevelMapSeries")
    for lvl in range(1, 21):
        ET.SubElement(series_node, "attribute", id=f"Level{lvl}", type="LSString", value=resolved_levels[lvl])
    ET.SubElement(series_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(series_node, "attribute", id="PreferredDiceType", type="uint32", value=str(dice_type))
    ET.SubElement(series_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        lm_dir.mkdir(parents=True, exist_ok=True)
        lm_file.write_text(prettify_xml(root), encoding="utf-8")

    return {
        "success": True,
        "mod": mod_slug,
        "name": name,
        "uuid": allocated_uuid,
        "preferred_dice_type": dice_type,
        "levels": resolved_levels,
        "file": str(lm_file),
        "dry_run": dry_run,
    }


def scaffold_default_values(
    mod_name_or_path: str,
    class_name: str,
    abilities: str | None = None,
    skills: str | None = None,
    spells: str | None = None,
    table_uuid: str | None = None,
    level: int = 1,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold Character Creation DefaultValues schemas."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    dv_dir = mod_folder_dir / "DefaultValues"
    resolved_table = table_uuid.strip() if table_uuid else VANILLA_CLASS_TABLES.get(class_name.strip().lower(), str(uuid.uuid4()))

    created_files: list[str] = []
    results: dict[str, Any] = {
        "success": True,
        "mod": mod_slug,
        "class_name": class_name,
        "table_uuid": resolved_table,
        "level": level,
        "files_updated": created_files,
        "dry_run": dry_run,
    }

    def _append_dv(file_path: Path, items: list[str]) -> str:
        allocated_uuid = str(uuid.uuid4())
        if file_path.exists():
            tree = ET.parse(file_path)
            root = tree.getroot()
        else:
            root = create_empty_lsx("DefaultValues")

        children = get_or_create_root_children(root, "DefaultValues")

        existing_node = None
        for dnode in children.findall("./node[@id='DefaultValue']"):
            mt = any(a.get("id") == "TableUUID" and a.get("value") == resolved_table for a in dnode.findall("./attribute"))
            ml = any(a.get("id") == "Level" and a.get("value") == str(level) for a in dnode.findall("./attribute"))
            if mt and ml:
                existing_node = dnode
                break

        if existing_node is not None:
            children.remove(existing_node)

        dv_node = ET.SubElement(children, "node", id="DefaultValue")
        ET.SubElement(dv_node, "attribute", id="Add", type="LSString", value=";".join(items))
        ET.SubElement(dv_node, "attribute", id="Level", type="int32", value=str(level))
        ET.SubElement(dv_node, "attribute", id="TableUUID", type="guid", value=resolved_table)
        ET.SubElement(dv_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

        if not dry_run:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(prettify_xml(root), encoding="utf-8")
        return allocated_uuid

    if abilities:
        items = split_larian_items(abilities)
        if items:
            f = dv_dir / "Abilities.lsx"
            _append_dv(f, items)
            created_files.append(str(f))
            results["abilities"] = items

    if skills:
        items = split_larian_items(skills)
        if items:
            f = dv_dir / "Skills.lsx"
            _append_dv(f, items)
            created_files.append(str(f))
            results["skills"] = items

    if spells:
        items = split_larian_items(spells)
        if items:
            f = dv_dir / "Spells.lsx"
            _append_dv(f, items)
            created_files.append(str(f))
            results["spells"] = items

    return results


def scaffold_stat(
    mod_name_or_path: str,
    entry_type: str,
    name: str,
    using: str | None = None,
    display_name: str | None = None,
    description: str | None = None,
    properties: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold Larian stat entries and generate localization handles."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    clean_type = entry_type.strip().lower()
    config = STAT_TYPE_CONFIG.get(clean_type)
    if not config:
        valid_types = ", ".join(STAT_TYPE_CONFIG.keys())
        raise ValueError(f"Unknown stat entry type '{entry_type}'. Valid types: {valid_types}")

    stats_dir = mod_folder_dir / "Stats" / "Generated" / "Data"
    target_file = stats_dir / config["file"]

    data_props: dict[str, str] = dict(config["defaults"])
    if properties:
        data_props.update(properties)

    disp_handle = None
    desc_handle = None
    loc_updates = []

    if clean_type in ("weapon", "armor", "amulet", "ring", "object", "passivedata", "status_boost", "spell_target", "spell_shout", "spell_projectile", "spell_zone", "spell_teleport", "spell_rush", "spell_path"):
        disp_handle = generate_larian_handle()
        disp_text = display_name if display_name else name
        loc_updates.append((disp_handle, disp_text))
        if clean_type == "passivedata":
            data_props["DisplayName"] = f"{disp_handle};1"
        else:
            data_props["DisplayName"] = f"{disp_handle};1"

        if description or clean_type not in ("object",):
            desc_handle = generate_larian_handle()
            desc_text = description if description else f"{name} description."
            loc_updates.append((desc_handle, desc_text))
            data_props["Description"] = f"{desc_handle};1"

    lines = [f'new entry "{name}"', config["type_header"]]
    active_using = using if using is not None else config["default_using"]
    if active_using:
        lines.append(f'using "{active_using}"')

    for k, v in data_props.items():
        if v is not None:
            lines.append(f'data "{k}" "{v}"')
    lines.append("")
    entry_text = "\n".join(lines)

    if not dry_run:
        stats_dir.mkdir(parents=True, exist_ok=True)
        if target_file.exists():
            existing = target_file.read_text(encoding="utf-8")
            pattern = rf'new\s+entry\s+"{re.escape(name)}".*?(?=\nnew\s+entry|\Z)'
            if re.search(pattern, existing, re.DOTALL):
                new_content = re.sub(pattern, entry_text.strip(), existing, flags=re.DOTALL)
            else:
                new_content = existing.rstrip() + "\n\n" + entry_text
            target_file.write_text(new_content, encoding="utf-8")
        else:
            target_file.write_text(entry_text, encoding="utf-8")

    if loc_updates:
        update_localization_xml(loc_file, loc_updates, dry_run=dry_run)

    return {
        "status": "created",
        "success": True,
        "mod": mod_slug,
        "entry_name": name,
        "name": name,
        "type": clean_type,
        "file": str(target_file),
        "stat_file": str(target_file),
        "display_name_handle": f"{disp_handle};1" if disp_handle else None,
        "description_handle": f"{desc_handle};1" if desc_handle else None,
        "properties": data_props,
        "dry_run": dry_run,
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
) -> dict[str, Any]:
    """Binds stat entries to physical 3D RootTemplates in _merged.lsx."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

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

    existing_node = None
    for gnode in children.findall("./node[@id='GameObjects']"):
        for attr in gnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                existing_node = gnode
                break
        if existing_node is not None:
            break

    if existing_node is not None:
        children.remove(existing_node)

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

    return {
        "success": True,
        "mod": mod_slug,
        "name": name,
        "uuid": allocated_uuid,
        "stats": stats_name,
        "visual_resource": vis_res,
        "icon": icon_name,
        "display_name_handle": f"{disp_handle};1",
        "description_handle": f"{desc_handle};1",
        "file": str(templates_file),
        "dry_run": dry_run,
    }


def scaffold_icon_uvs(
    mod_name_or_path: str,
    atlas_name: str,
    icons: list[str],
    icon_size: int = 64,
    atlas_width: int = 2048,
    atlas_height: int = 2048,
    atlas_uuid: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Calculates UV coordinates and scaffolds GUI/Icons.lsx for texture atlas grids."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    gui_dir = mod_folder_dir / "GUI"
    icons_file = gui_dir / "Icons.lsx"

    allocated_atlas_uuid = atlas_uuid.strip() if atlas_uuid else str(uuid.uuid4())
    cols = atlas_width // icon_size
    rows = atlas_height // icon_size
    max_icons = cols * rows

    if len(icons) > max_icons:
        raise ValueError(f"Too many icons ({len(icons)}) for atlas size {atlas_width}x{atlas_height} (max {max_icons}).")

    mappings = []
    for idx, name in enumerate(icons):
        col = idx % cols
        row = idx // cols
        u1 = (col * icon_size) / atlas_width
        u2 = ((col + 1) * icon_size) / atlas_width
        v1 = (row * icon_size) / atlas_height
        v2 = ((row + 1) * icon_size) / atlas_height
        mappings.append({
            "name": name,
            "col": col,
            "row": row,
            "u1": round(u1, 6),
            "u2": round(u2, 6),
            "v1": round(v1, 6),
            "v2": round(v2, 6),
        })

    root = ET.Element("save")
    ET.SubElement(root, "version", **PATCH_8_VERSION_ATTRIBUTES)

    reg_info = ET.SubElement(root, "region", id="TextureAtlasInfo")
    node_info_root = ET.SubElement(reg_info, "node", id="root")
    children_info = ET.SubElement(node_info_root, "children")

    node_icon_size = ET.SubElement(children_info, "node", id="TextureAtlasIconSize")
    ET.SubElement(node_icon_size, "attribute", id="Height", type="int64", value=str(icon_size))
    ET.SubElement(node_icon_size, "attribute", id="Width", type="int64", value=str(icon_size))

    node_path = ET.SubElement(children_info, "node", id="TextureAtlasPath")
    ET.SubElement(node_path, "attribute", id="Path", type="LSString", value=f"Assets/Textures/Icons/{atlas_name}.dds")
    ET.SubElement(node_path, "attribute", id="UUID", type="FixedString", value=allocated_atlas_uuid)

    node_tex_size = ET.SubElement(children_info, "node", id="TextureAtlasTextureSize")
    ET.SubElement(node_tex_size, "attribute", id="Height", type="int64", value=str(atlas_height))
    ET.SubElement(node_tex_size, "attribute", id="Width", type="int64", value=str(atlas_width))

    reg_uv = ET.SubElement(root, "region", id="IconUVList")
    node_uv_root = ET.SubElement(reg_uv, "node", id="root")
    children_uv = ET.SubElement(node_uv_root, "children")

    for m in mappings:
        uv_node = ET.SubElement(children_uv, "node", id="IconUV")
        ET.SubElement(uv_node, "attribute", id="MapKey", type="FixedString", value=m["name"])
        ET.SubElement(uv_node, "attribute", id="U1", type="float", value=str(m["u1"]))
        ET.SubElement(uv_node, "attribute", id="U2", type="float", value=str(m["u2"]))
        ET.SubElement(uv_node, "attribute", id="V1", type="float", value=str(m["v1"]))
        ET.SubElement(uv_node, "attribute", id="V2", type="float", value=str(m["v2"]))

    if not dry_run:
        gui_dir.mkdir(parents=True, exist_ok=True)
        icons_file.write_text(prettify_xml(root), encoding="utf-8")

    return {
        "success": True,
        "mod": mod_slug,
        "atlas_name": atlas_name,
        "atlas_uuid": allocated_atlas_uuid,
        "icon_size": icon_size,
        "total_icons": len(mappings),
        "file": str(icons_file),
        "mappings": mappings,
        "dry_run": dry_run,
    }


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
) -> dict[str, Any]:
    """Scaffold Races.lsx and RaceDescriptions.lsx custom races and subraces."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

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
            raise ValueError(f"Unknown vanilla parent race '{parent_race}'.")
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
        r_root = create_empty_lsx("Races")

    r_children = get_or_create_root_children(r_root, "Races")

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
        rd_root = create_empty_lsx("RaceDescriptions")

    rd_children = get_or_create_root_children(rd_root, "RaceDescriptions")

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
) -> dict[str, Any]:
    """Scaffold Origins/Origins.lsx playable origin characters."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

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
        root = create_empty_lsx("Origins")

    children = get_or_create_root_children(root, "Origins")

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
) -> dict[str, Any]:
    """Scaffold CharacterCreationAppearanceVisuals.lsx cosmetic assets."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    cc_dir = mod_folder_dir / "CharacterCreation"
    cc_file = cc_dir / "CharacterCreationAppearanceVisuals.lsx"

    allocated_uuid = visual_uuid.strip() if visual_uuid else str(uuid.uuid4())
    resolved_race_uuid = VANILLA_RACE_UUIDS.get(race.strip().lower(), "00000000-0000-0000-0000-000000000000") if race else "00000000-0000-0000-0000-000000000000"
    disp_text = display_name if display_name else name
    disp_handle = generate_larian_handle()

    if cc_file.exists():
        tree = ET.parse(cc_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx("CharacterCreationAppearanceVisuals")

    children = get_or_create_root_children(root, "CharacterCreationAppearanceVisuals")

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


def scaffold_tag(
    mod_name_or_path: str,
    name: str,
    description: str | None = None,
    display_name: str | None = None,
    categories: list[str] | None = None,
    tag_uuid: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold Tags/<UUID>.lsx dialogue and identity tags."""
    mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

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


# -----------------------------------------------------------------------------
# Unified Dispatcher
# -----------------------------------------------------------------------------

ASSET_HANDLERS = {
    "class": scaffold_class,
    "class-description": scaffold_class,
    "progression": scaffold_progression,
    "feat": scaffold_feat,
    "action-resource": scaffold_action_resource,
    "spell-list": scaffold_spell_list,
    "level-map": scaffold_level_map,
    "default-values": scaffold_default_values,
    "stat": scaffold_stat,
    "root-template": scaffold_root_template,
    "icon-uvs": scaffold_icon_uvs,
    "race": scaffold_race,
    "origin": scaffold_origin,
    "appearance": scaffold_appearance_visual,
    "appearance-visual": scaffold_appearance_visual,
    "tag": scaffold_tag,
}


def scaffold_asset(asset_type: str, **kwargs: Any) -> dict[str, Any]:
    """Unified entrypoint to scaffold any supported Baldur's Gate 3 asset type."""
    key = asset_type.strip().lower()
    handler = ASSET_HANDLERS.get(key)
    if not handler:
        valid_keys = ", ".join(sorted(ASSET_HANDLERS.keys()))
        raise ValueError(f"Unknown asset type '{asset_type}'. Valid types: {valid_keys}")
    return handler(**kwargs)


# -----------------------------------------------------------------------------
# Command Line Interface
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified Larian Patch 8 Asset Scaffolding Engine.")
    subparsers = parser.add_subparsers(dest="asset_type", required=True, help="Asset type to scaffold")

    # Class
    p_class = subparsers.add_parser("class", help="Scaffold class or subclass definition")
    p_class.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    p_class.add_argument("--name", required=True, help="Internal class/subclass name")
    p_class.add_argument("--display-name", help="Display name in game UI")
    p_class.add_argument("--description", help="Description in character creation & level-up tree")
    p_class.add_argument("--parent-class", help="Vanilla parent class preset (e.g. rogue, wizard)")
    p_class.add_argument("--parent-guid", help="Explicit parent class GUID")
    p_class.add_argument("--class-uuid", help="Explicit UUID for this class/subclass")
    p_class.add_argument("--table-uuid", help="Explicit ProgressionTableUUID")
    p_class.add_argument("--base-hp", type=int, default=8, help="Base HP at level 1")
    p_class.add_argument("--hp-per-level", type=int, default=5, help="HP gain per level")
    p_class.add_argument("--primary-ability", type=int, default=1, help="Primary ability score enum")
    p_class.add_argument("--spell-ability", type=int, default=0, help="Spellcasting ability enum")
    p_class.add_argument("--register-in-parent", action="store_true", default=True, help="Inject into parent Progressions.lsx")
    p_class.add_argument("--no-register-in-parent", dest="register_in_parent", action="store_false")
    p_class.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    p_class.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # Progression
    p_prog = subparsers.add_parser("progression", help="Scaffold level progression node")
    p_prog.add_argument("--mod", required=True)
    p_prog.add_argument("--name", "--class", dest="name", required=True, help="Target class or progression name")
    p_prog.add_argument("--level", type=int, required=True)
    p_prog.add_argument("--table-uuid")
    p_prog.add_argument("--progression-type", type=int, default=0)
    p_prog.add_argument("--multiclass", action="store_true", help="Mark progression node as multiclass entry (sets ProgressionType=2)")
    p_prog.add_argument("--subclass", help="Optional subclass name (sets ProgressionType=1)")
    p_prog.add_argument("--passives")
    p_prog.add_argument("--spells")
    p_prog.add_argument("--selectors")
    p_prog.add_argument("--dry-run", action="store_true")
    p_prog.add_argument("--json", action="store_true")

    # Feat
    p_feat = subparsers.add_parser("feat", help="Scaffold feat definition")
    p_feat.add_argument("--mod", required=True)
    p_feat.add_argument("--name", required=True)
    p_feat.add_argument("--display-name")
    p_feat.add_argument("--description")
    p_feat.add_argument("--passives")
    p_feat.add_argument("--selectors")
    p_feat.add_argument("--requirements")
    p_feat.add_argument("--can-be-picked-multiple-times", action="store_true")
    p_feat.add_argument("--feat-uuid")
    p_feat.add_argument("--dry-run", action="store_true")
    p_feat.add_argument("--json", action="store_true")

    # Action Resource
    p_ar = subparsers.add_parser("action-resource", help="Scaffold action resource definition")
    p_ar.add_argument("--mod", required=True)
    p_ar.add_argument("--name", required=True)
    p_ar.add_argument("--display-name")
    p_ar.add_argument("--description")
    p_ar.add_argument("--replenish-type", default="ShortRest")
    p_ar.add_argument("--max-level", type=int, default=0)
    p_ar.add_argument("--dice-type", type=int, default=0)
    p_ar.add_argument("--party-action-resource", action="store_true")
    p_ar.add_argument("--uuid")
    p_ar.add_argument("--dry-run", action="store_true")
    p_ar.add_argument("--json", action="store_true")

    # Spell List
    p_sl = subparsers.add_parser("spell-list", help="Scaffold spell list or passive list")
    p_sl.add_argument("--mod", required=True)
    p_sl.add_argument("--comment")
    p_sl.add_argument("--spells", nargs="*")
    p_sl.add_argument("--passives", nargs="*")
    p_sl.add_argument("--uuid")
    p_sl.add_argument("--dry-run", action="store_true")
    p_sl.add_argument("--json", action="store_true")

    # Level Map
    p_lm = subparsers.add_parser("level-map", help="Scaffold level map scaling curve")
    p_lm.add_argument("--mod", required=True)
    p_lm.add_argument("--name", required=True)
    p_lm.add_argument("--levels", required=True)
    p_lm.add_argument("--dice-type", type=int)
    p_lm.add_argument("--uuid")
    p_lm.add_argument("--dry-run", action="store_true")
    p_lm.add_argument("--json", action="store_true")

    # Default Values
    p_dv = subparsers.add_parser("default-values", help="Scaffold character creation default values")
    p_dv.add_argument("--mod", required=True)
    p_dv.add_argument("--class-name", "--class", dest="class_name", required=True)
    p_dv.add_argument("--abilities")
    p_dv.add_argument("--skills")
    p_dv.add_argument("--spells")
    p_dv.add_argument("--table-uuid")
    p_dv.add_argument("--level", type=int, default=1)
    p_dv.add_argument("--dry-run", action="store_true")
    p_dv.add_argument("--json", action="store_true")

    # Stat
    p_stat = subparsers.add_parser("stat", help="Scaffold stat entry in txt files")
    p_stat.add_argument("--mod", required=True)
    p_stat.add_argument("--type", required=True)
    p_stat.add_argument("--name", required=True)
    p_stat.add_argument("--using")
    p_stat.add_argument("--display-name")
    p_stat.add_argument("--description")
    p_stat.add_argument("--properties", "--props", dest="properties", nargs="*")
    p_stat.add_argument("--dry-run", action="store_true")
    p_stat.add_argument("--json", action="store_true")

    # Root Template
    p_rt = subparsers.add_parser("root-template", help="Scaffold 3D root template GameObject in _merged.lsx")
    p_rt.add_argument("--mod", required=True)
    p_rt.add_argument("--name", "--item", dest="name", required=True)
    p_rt.add_argument("--preset", "--visual-preset", dest="preset", default="greatsword")
    p_rt.add_argument("--template-type", default="item")
    p_rt.add_argument("--stats")
    p_rt.add_argument("--visual-resource")
    p_rt.add_argument("--parent-template-id")
    p_rt.add_argument("--display-name")
    p_rt.add_argument("--description")
    p_rt.add_argument("--icon")
    p_rt.add_argument("--uuid")
    p_rt.add_argument("--dry-run", action="store_true")
    p_rt.add_argument("--json", action="store_true")

    # Icon UVs
    p_icon = subparsers.add_parser("icon-uvs", help="Calculate icon UVs on texture atlas")
    p_icon.add_argument("--mod", required=True)
    p_icon.add_argument("--atlas-name", default="Icons")
    p_icon.add_argument("--icons", "--icon-names", dest="icons", nargs="*")
    p_icon.add_argument("--icon-size", type=int, default=64)
    p_icon.add_argument("--atlas-size", type=int)
    p_icon.add_argument("--atlas-width", type=int, default=2048)
    p_icon.add_argument("--atlas-height", type=int, default=2048)
    p_icon.add_argument("--uuid", "--atlas-uuid", dest="uuid")
    p_icon.add_argument("--dry-run", action="store_true")
    p_icon.add_argument("--json", action="store_true")

    # Race
    p_race = subparsers.add_parser("race", help="Scaffold race and subrace definitions")
    p_race.add_argument("--mod", required=True)
    p_race.add_argument("--name", required=True)
    p_race.add_argument("--display-name")
    p_race.add_argument("--description")
    p_race.add_argument("--parent-race")
    p_race.add_argument("--parent-guid")
    p_race.add_argument("--race-uuid")
    p_race.add_argument("--table-uuid")
    p_race.add_argument("--equipment")
    p_race.add_argument("--dry-run", action="store_true")
    p_race.add_argument("--json", action="store_true")

    # Origin
    p_orig = subparsers.add_parser("origin", help="Scaffold playable origin character")
    p_orig.add_argument("--mod", required=True)
    p_orig.add_argument("--name", required=True)
    p_orig.add_argument("--display-name")
    p_orig.add_argument("--description")
    p_orig.add_argument("--equipment")
    p_orig.add_argument("--class-uuid")
    p_orig.add_argument("--race-uuid")
    p_orig.add_argument("--body-type", type=int, choices=[0, 1], default=0)
    p_orig.add_argument("--body-shape", type=int, choices=[0, 1], default=0)
    p_orig.add_argument("--passives")
    p_orig.add_argument("--uuid")
    p_orig.add_argument("--dry-run", action="store_true")
    p_orig.add_argument("--json", action="store_true")

    # Appearance
    p_app = subparsers.add_parser("appearance", aliases=["appearance-visual"], help="Scaffold character creation appearance visuals")
    p_app.add_argument("--mod", required=True)
    p_app.add_argument("--name", required=True)
    p_app.add_argument("--visual-resource", required=True)
    p_app.add_argument("--slot", default="Hair")
    p_app.add_argument("--race")
    p_app.add_argument("--body-type", type=int, choices=[0, 1], default=0)
    p_app.add_argument("--body-shape", type=int, choices=[0, 1], default=0)
    p_app.add_argument("--display-name")
    p_app.add_argument("--uuid")
    p_app.add_argument("--dry-run", action="store_true")
    p_app.add_argument("--json", action="store_true")

    # Tag
    p_tag = subparsers.add_parser("tag", help="Scaffold dialogue and identity tag")
    p_tag.add_argument("--mod", required=True)
    p_tag.add_argument("--name", required=True)
    p_tag.add_argument("--display-name")
    p_tag.add_argument("--description")
    p_tag.add_argument("--category", action="append")
    p_tag.add_argument("--uuid")
    p_tag.add_argument("--dry-run", action="store_true")
    p_tag.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        atype = args.asset_type
        if atype in ("class", "class-description"):
            res = scaffold_class(
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
        elif atype == "progression":
            prog_type = 2 if getattr(args, "multiclass", False) else (1 if getattr(args, "subclass", None) else args.progression_type)
            prog_name = args.subclass if getattr(args, "subclass", None) else args.name
            res = scaffold_progression(
                mod_name_or_path=args.mod,
                name=prog_name,
                level=args.level,
                table_uuid=args.table_uuid,
                progression_type=prog_type,
                passives=args.passives,
                spells=args.spells,
                selectors=args.selectors,
                dry_run=args.dry_run,
            )
        elif atype == "feat":
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
        elif atype == "action-resource":
            res = scaffold_action_resource(
                mod_name_or_path=args.mod,
                name=args.name,
                display_name=args.display_name,
                description=args.description,
                replenish_type=args.replenish_type,
                max_level=args.max_level,
                dice_type=args.dice_type,
                party_action_resource=args.party_action_resource,
                resource_uuid=args.uuid,
                dry_run=args.dry_run,
            )
        elif atype == "spell-list":
            if args.passives and not args.spells:
                ltype = "passives"
                items = ",".join(args.passives) if isinstance(args.passives, list) else args.passives
            else:
                ltype = "spells"
                items = ",".join(args.spells) if isinstance(args.spells, list) else args.spells
            res = scaffold_spell_list(
                mod_name_or_path=args.mod,
                list_type=ltype,
                comment=args.comment,
                items=items,
                list_uuid=args.uuid,
                dry_run=args.dry_run,
            )
        elif atype == "level-map":
            res = scaffold_level_map(
                mod_name_or_path=args.mod,
                name=args.name,
                levels=args.levels,
                preferred_dice_type=args.dice_type,
                level_map_uuid=args.uuid,
                dry_run=args.dry_run,
            )
        elif atype == "default-values":
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
        elif atype == "stat":
            prop_dict: dict[str, str] = {}
            if args.properties:
                for raw_prop in args.properties:
                    for item in split_larian_items(raw_prop, separators=(",",)):
                        if "=" in item:
                            k, v = item.split("=", 1)
                            prop_dict[k.strip()] = v.strip()
                        elif " " in item:
                            k, v = item.split(" ", 1)
                            prop_dict[k.strip()] = v.strip()
            res = scaffold_stat(
                mod_name_or_path=args.mod,
                entry_type=args.type,
                name=args.name,
                using=args.using,
                display_name=args.display_name,
                description=args.description,
                properties=prop_dict,
                dry_run=args.dry_run,
            )
        elif atype == "root-template":
            res = scaffold_root_template(
                mod_name_or_path=args.mod,
                name=args.name,
                preset=args.preset,
                template_type=args.template_type,
                stats=args.stats,
                visual_resource=args.visual_resource,
                parent_template_id=args.parent_template_id,
                display_name=args.display_name,
                description=args.description,
                icon=args.icon,
                template_uuid=args.uuid,
                dry_run=args.dry_run,
            )
        elif atype == "icon-uvs":
            icons_list = []
            if args.icons:
                for item in args.icons:
                    icons_list.extend(split_larian_items(item, separators=(",",)))
            w = args.atlas_size if getattr(args, "atlas_size", None) else args.atlas_width
            h = args.atlas_size if getattr(args, "atlas_size", None) else args.atlas_height
            res = scaffold_icon_uvs(
                mod_name_or_path=args.mod,
                atlas_name=args.atlas_name,
                icons=icons_list,
                icon_size=args.icon_size,
                atlas_width=w,
                atlas_height=h,
                atlas_uuid=args.uuid,
                dry_run=args.dry_run,
            )
        elif atype == "race":
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
        elif atype == "origin":
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
        elif atype in ("appearance", "appearance-visual"):
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
        elif atype == "tag":
            res = scaffold_tag(
                mod_name_or_path=args.mod,
                name=args.name,
                description=args.description,
                display_name=args.display_name,
                categories=args.category,
                tag_uuid=args.uuid,
                dry_run=args.dry_run,
            )
        else:
            raise ValueError(f"Unsupported asset type: '{atype}'")

        color = ConsoleColor(stream=sys.stdout)
        if getattr(args, "json", False):
            print(json.dumps(res, indent=2))
        else:
            tag_str = color.yellow(" [DRY-RUN]") if res.get("dry_run") else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded {atype} '{res.get('name') or res.get('class_name') or res.get('resource_name')}'{tag_str}:")
            for k, v in res.items():
                if k not in ("success", "mod", "dry_run"):
                    print(f"    {k}: {v}")
        return ExitCode.SUCCESS

    except Exception as e:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            err_color = ConsoleColor(stream=sys.stderr)
            print(f"{err_color.red('[ERROR]')} {e}", file=sys.stderr)
        return ExitCode.GENERAL


if __name__ == "__main__":
    sys.exit(main())
