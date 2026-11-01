#!/usr/bin/env python3
"""
scaffold_mechanics.py
---------------------
Gameplay mechanics asset scaffolding for Baldur's Gate 3:
classes, subclasses, progressions, feats, action resources, spell lists,
level maps, default values, and stat entries.
"""

from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bg3_core.larian_parsers import (
    generate_larian_handle,
    split_larian_items,
    update_localization_xml,
)

from bg3_authoring.scaffold_common import (
    ScaffoldResult,
    create_empty_lsx,
    get_or_create_root_children,
    prettify_xml,
    resolve_mod_paths,
)

VANILLA_CLASS_TABLES: dict[str, str] = {
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

SUBCLASS_TABLE_UUIDS: dict[str, str] = {
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

VANILLA_PARENT_CLASSES: dict[str, dict[str, Any]] = {
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
# Class Scaffolding
# -----------------------------------------------------------------------------

def _resolve_parent_class_guid(
    parent_class: str | None, parent_guid: str | None
) -> tuple[str, bool]:
    if parent_class:
        key = parent_class.strip().lower()
        if key in VANILLA_PARENT_CLASSES:
            return VANILLA_PARENT_CLASSES[key]["guid"], True
        raise ValueError(
            f"Unknown vanilla parent class '{parent_class}'. Specify a valid preset or provide --parent-guid."
        )
    if parent_guid:
        resolved = parent_guid.strip()
        return resolved, (resolved != "00000000-0000-0000-0000-000000000000")
    return "00000000-0000-0000-0000-000000000000", False


def _build_class_description_node(
    children: ET.Element,
    name: str,
    class_uuid: str,
    table_uuid: str,
    parent_guid: str,
    is_subclass: bool,
    base_hp: int,
    hp_per_level: int,
    primary_ability: int,
    spell_casting_ability: int,
    disp_handle: str,
    desc_handle: str,
) -> None:
    # Purge any existing node with same Name
    for cnode in list(children.findall("./node[@id='ClassDescription']")):
        for attr in cnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                children.remove(cnode)
                break

    class_node = ET.SubElement(children, "node", id="ClassDescription")
    ET.SubElement(class_node, "attribute", id="BaseHp", type="int32", value=str(base_hp))
    ET.SubElement(class_node, "attribute", id="CharacterCreationPose", type="guid", value="0f07ec6e-4ef0-434e-9a51-1353260ccff8")
    ET.SubElement(class_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(class_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(class_node, "attribute", id="HpPerLevel", type="int32", value=str(hp_per_level))
    ET.SubElement(class_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(class_node, "attribute", id="ParentGuid", type="guid", value=parent_guid)
    ET.SubElement(class_node, "attribute", id="PrimaryAbility", type="uint8", value=str(primary_ability))
    ET.SubElement(class_node, "attribute", id="ProgressionTableUUID", type="guid", value=table_uuid)
    ET.SubElement(class_node, "attribute", id="SoundClassType", type="FixedString", value="Fighter" if not is_subclass else "")
    ET.SubElement(class_node, "attribute", id="SpellCastingAbility", type="uint8", value=str(spell_casting_ability))
    ET.SubElement(class_node, "attribute", id="UUID", type="guid", value=class_uuid)

    tags_node = ET.SubElement(class_node, "children")
    ET.SubElement(tags_node, "node", id="Tags")


def _build_progression_description_node(
    children: ET.Element,
    name: str,
    class_uuid: str,
    table_uuid: str,
    desc_node_uuid: str,
    disp_handle: str,
    desc_handle: str,
) -> None:
    for pnode in list(children.findall("./node[@id='ProgressionDescription']")):
        for attr in pnode.findall("./attribute"):
            if (attr.get("id") == "ExactMatch" and attr.get("value") == name) or (
                attr.get("id") == "ClassId" and attr.get("value") == class_uuid
            ):
                children.remove(pnode)
                break

    pd_node = ET.SubElement(children, "node", id="ProgressionDescription")
    ET.SubElement(pd_node, "attribute", id="ClassId", type="guid", value=class_uuid)
    ET.SubElement(pd_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(pd_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(pd_node, "attribute", id="ExactMatch", type="FixedString", value=name)
    ET.SubElement(pd_node, "attribute", id="ProgressionTableId", type="guid", value=table_uuid)
    ET.SubElement(pd_node, "attribute", id="UUID", type="guid", value=desc_node_uuid)


def _find_parent_progression_node(
    ps_root: ET.Element, target_table_uuid: str | None
) -> ET.Element | None:
    if not target_table_uuid:
        return None
    for pnode in ps_root.findall(".//node[@id='Progression']"):
        t_uuid = pnode.find("./attribute[@id='TableUUID']")
        lvl = pnode.find("./attribute[@id='Level']")
        if t_uuid is not None and lvl is not None:
            if t_uuid.get("value") == target_table_uuid and lvl.get("value") in ("1", "2", "3"):
                return pnode
    return None


def _append_subclass_guid(target_node: ET.Element, class_uuid: str) -> bool:
    subclasses_node = target_node.find(".//node[@id='SubClasses']")
    if subclasses_node is None:
        ch = target_node.find("./children")
        if ch is None:
            ch = ET.SubElement(target_node, "children")
        subclasses_node = ET.SubElement(ch, "node", id="SubClasses")

    sc_children = subclasses_node.find("./children")
    if sc_children is None:
        sc_children = ET.SubElement(subclasses_node, "children")

    for sc in sc_children.findall("./node[@id='SubClass']"):
        obj_attr = sc.find("./attribute[@id='Object']")
        if obj_attr is not None and obj_attr.get("value") == class_uuid:
            return False

    new_sc = ET.SubElement(sc_children, "node", id="SubClass")
    ET.SubElement(new_sc, "attribute", id="Object", type="guid", value=class_uuid)
    return True


def _register_subclass_in_parent(
    progressions_file: Path,
    parent_class: str | None,
    allocated_class_uuid: str,
    dry_run: bool,
) -> bool:
    if not progressions_file.exists():
        return False

    ps_tree = ET.parse(progressions_file)
    ps_root = ps_tree.getroot()
    target_table_uuid = VANILLA_CLASS_TABLES.get(parent_class.lower()) if parent_class else None
    target_node = _find_parent_progression_node(ps_root, target_table_uuid)
    if target_node is None:
        return False

    if _append_subclass_guid(target_node, allocated_class_uuid):
        if not dry_run:
            progressions_file.write_text(prettify_xml(ps_root), encoding="utf-8")
        return True
    return False


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
) -> ScaffoldResult:
    """Scaffold Patch 8 Class & Subclass definitions."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    class_desc_dir = mod_folder_dir / "ClassDescriptions"
    class_desc_file = class_desc_dir / "ClassDescriptions.lsx"
    prog_desc_dir = mod_folder_dir / "Progressions"
    prog_desc_file = prog_desc_dir / "ProgressionDescriptions.lsx"
    progressions_file = prog_desc_dir / "Progressions.lsx"

    allocated_class_uuid = class_uuid.strip() if class_uuid else str(uuid.uuid4())
    allocated_table_uuid = progression_table_uuid.strip() if progression_table_uuid else str(uuid.uuid4())
    prog_desc_node_uuid = str(uuid.uuid4())

    resolved_parent_guid, is_subclass = _resolve_parent_class_guid(parent_class, parent_guid)

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
    _build_class_description_node(
        cd_children, name, allocated_class_uuid, allocated_table_uuid,
        resolved_parent_guid, is_subclass, base_hp, hp_per_level,
        primary_ability, spell_casting_ability, disp_handle, desc_handle,
    )
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
    _build_progression_description_node(
        pd_children, name, allocated_class_uuid, allocated_table_uuid,
        prog_desc_node_uuid, disp_handle, desc_handle,
    )
    if not dry_run:
        prog_desc_dir.mkdir(parents=True, exist_ok=True)
        prog_desc_file.write_text(prettify_xml(pd_root), encoding="utf-8")

    # 3. Register in parent Progressions.lsx if subclass
    parent_registered = False
    if is_subclass and register_in_parent:
        parent_registered = _register_subclass_in_parent(
            progressions_file, parent_class, allocated_class_uuid, dry_run
        )

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="class",
        uuid=allocated_class_uuid,
        file=str(class_desc_file),
        dry_run=dry_run,
        details={
            "progression_table_uuid": allocated_table_uuid,
            "is_subclass": is_subclass,
            "parent_guid": resolved_parent_guid,
            "parent_registered": parent_registered,
            "display_name_handle": f"{disp_handle};1",
            "description_handle": f"{desc_handle};1",
            "class_descriptions_file": str(class_desc_file),
            "progression_descriptions_file": str(prog_desc_file),
            "localization_file": str(loc_file),
        },
    )


# -----------------------------------------------------------------------------
# Progression Scaffolding
# -----------------------------------------------------------------------------

def _build_progression_node(
    p_children: ET.Element,
    name: str,
    level: int,
    target_table_uuid: str,
    progression_uuid: str,
    progression_type: int,
    passives_added: str,
    selectors_str: str,
) -> None:
    for pnode in list(p_children.findall("./node[@id='Progression']")):
        match_table = False
        match_lvl = False
        for attr in pnode.findall("./attribute"):
            if attr.get("id") == "TableUUID" and attr.get("value") == target_table_uuid:
                match_table = True
            elif attr.get("id") == "Level" and attr.get("value") == str(level):
                match_lvl = True
        if match_table and match_lvl:
            p_children.remove(pnode)
            break

    prog_node = ET.SubElement(p_children, "node", id="Progression")
    ET.SubElement(prog_node, "attribute", id="AllowImprovement", type="bool", value="true" if level in (4, 8, 12, 16, 19) else "false")
    ET.SubElement(prog_node, "attribute", id="Level", type="uint8", value=str(level))
    ET.SubElement(prog_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(prog_node, "attribute", id="PassivesAdded", type="LSString", value=passives_added)
    ET.SubElement(prog_node, "attribute", id="ProgressionType", type="uint8", value=str(progression_type))
    ET.SubElement(prog_node, "attribute", id="Selectors", type="LSString", value=selectors_str)
    ET.SubElement(prog_node, "attribute", id="TableUUID", type="guid", value=target_table_uuid)
    ET.SubElement(prog_node, "attribute", id="UUID", type="guid", value=progression_uuid)


def _scaffold_companion_spell_list(
    spell_lists_dir: Path,
    spell_lists_file: Path,
    name: str,
    level: int,
    spells: str,
    dry_run: bool,
) -> tuple[str, str]:
    spell_list_uuid = str(uuid.uuid4())
    spell_items = ";".join(split_larian_items(spells))
    selector_str = f"SelectSpells({spell_list_uuid},1,0)"

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

    return spell_list_uuid, selector_str


def scaffold_progression(
    mod_name_or_path: str,
    name: str,
    level: int,
    table_uuid: str | None = None,
    progression_type: int = 0,
    passives: str | None = None,
    spells: str | None = None,
    selectors: str | None = None,
    _hp_formula: str = "1",
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold Larian v4.8 XML Progression and companion SpellList nodes."""
    _mod_root, mod_folder_dir, _loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

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

    spell_list_uuid = None
    if spells:
        spell_list_uuid, sel_str = _scaffold_companion_spell_list(
            spell_lists_dir, spell_lists_file, name, level, spells, dry_run
        )
        selectors_list.append(sel_str)

    selectors_str = ";".join(selectors_list)

    if progressions_file.exists():
        p_tree = ET.parse(progressions_file)
        p_root = p_tree.getroot()
    else:
        p_root = create_empty_lsx("Progressions")

    p_children = get_or_create_root_children(p_root, "Progressions")
    _build_progression_node(
        p_children, name, level, target_table_uuid, progression_uuid,
        progression_type, passives_added, selectors_str
    )

    if not dry_run:
        progressions_dir.mkdir(parents=True, exist_ok=True)
        progressions_file.write_text(prettify_xml(p_root), encoding="utf-8")

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="progression",
        uuid=progression_uuid,
        file=str(progressions_file),
        dry_run=dry_run,
        details={
            "level": level,
            "table_uuid": target_table_uuid,
            "progression_uuid": progression_uuid,
            "spell_list_uuid": spell_list_uuid,
            "passives": passives_added,
            "selectors": selectors_str,
        },
    )


# -----------------------------------------------------------------------------
# Feat Scaffolding
# -----------------------------------------------------------------------------

def _build_feat_node(
    children: ET.Element,
    name: str,
    feat_uuid: str,
    passives_str: str,
    requirements_str: str,
    selectors_str: str,
    can_be_picked_multiple_times: bool,
) -> None:
    for fnode in list(children.findall("./node[@id='Feat']")):
        for attr in fnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                children.remove(fnode)
                break

    feat_node = ET.SubElement(children, "node", id="Feat")
    ET.SubElement(feat_node, "attribute", id="CanBePickedMultipleTimes", type="bool", value="true" if can_be_picked_multiple_times else "false")
    ET.SubElement(feat_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(feat_node, "attribute", id="PassivesAdded", type="LSString", value=passives_str)
    ET.SubElement(feat_node, "attribute", id="Requirements", type="LSString", value=requirements_str)
    ET.SubElement(feat_node, "attribute", id="Selectors", type="LSString", value=selectors_str)
    ET.SubElement(feat_node, "attribute", id="UUID", type="guid", value=feat_uuid)


def _build_feat_description_node(
    children: ET.Element,
    name: str,
    feat_uuid: str,
    desc_node_uuid: str,
    disp_handle: str,
    desc_handle: str,
) -> None:
    for dnode in list(children.findall("./node[@id='FeatDescription']")):
        for attr in dnode.findall("./attribute"):
            if (attr.get("id") == "ExactMatch" and attr.get("value") == name) or (
                attr.get("id") == "FeatId" and attr.get("value") == feat_uuid
            ):
                children.remove(dnode)
                break

    feat_desc_node = ET.SubElement(children, "node", id="FeatDescription")
    ET.SubElement(feat_desc_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(feat_desc_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(feat_desc_node, "attribute", id="ExactMatch", type="FixedString", value=name)
    ET.SubElement(feat_desc_node, "attribute", id="FeatId", type="guid", value=feat_uuid)
    ET.SubElement(feat_desc_node, "attribute", id="UUID", type="guid", value=desc_node_uuid)


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
) -> ScaffoldResult:
    """Scaffold Patch 8 Feats and FeatDescriptions."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

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
    _build_feat_node(
        feats_children, name, allocated_feat_uuid, passives_str,
        requirements_str, selectors_str, can_be_picked_multiple_times
    )
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
    _build_feat_description_node(
        desc_children, name, allocated_feat_uuid, desc_node_uuid,
        disp_handle, desc_handle
    )
    if not dry_run:
        feat_descs_file.write_text(prettify_xml(desc_root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="feat",
        uuid=allocated_feat_uuid,
        file=str(feats_file),
        dry_run=dry_run,
        details={
            "display_name_handle": f"{disp_handle};1",
            "description_handle": f"{desc_handle};1",
            "passives": passives_str,
            "selectors": selectors_str,
            "requirements": requirements_str,
            "can_be_picked_multiple_times": can_be_picked_multiple_times,
            "feats_file": str(feats_file),
            "feat_descriptions_file": str(feat_descs_file),
            "localization_file": str(loc_file),
        },
    )


# -----------------------------------------------------------------------------
# Action Resource Scaffolding
# -----------------------------------------------------------------------------

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
    resource_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold ActionResourceDefinitions."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    res_dir = mod_folder_dir / "ActionResourceDefinitions"
    res_file = res_dir / "ActionResourceDefinitions.lsx"

    allocated_uuid = resource_uuid.strip() if resource_uuid else str(uuid.uuid4())
    disp_text = display_name if display_name else name
    desc_text = description if description else f"{name} resource description."
    disp_handle = generate_larian_handle()
    desc_handle = generate_larian_handle()

    if res_file.exists():
        tree = ET.parse(res_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx("ActionResourceDefinitions")

    children = get_or_create_root_children(root, "ActionResourceDefinitions")

    for rnode in list(children.findall("./node[@id='ActionResourceDefinition']")):
        for attr in rnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                children.remove(rnode)
                break

    r_node = ET.SubElement(children, "node", id="ActionResourceDefinition")
    ET.SubElement(r_node, "attribute", id="Description", type="TranslatedString", handle=f"{desc_handle};1", version="1")
    ET.SubElement(r_node, "attribute", id="DiceType", type="uint32", value=str(dice_type))
    ET.SubElement(r_node, "attribute", id="DisplayName", type="TranslatedString", handle=f"{disp_handle};1", version="1")
    ET.SubElement(r_node, "attribute", id="IsSpellResource", type="bool", value="true" if is_spell_resource else "false")
    ET.SubElement(r_node, "attribute", id="MaxLevel", type="uint32", value=str(max_level))
    ET.SubElement(r_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(r_node, "attribute", id="ReplenishType", type="FixedString", value=replenish_type)
    ET.SubElement(r_node, "attribute", id="ShowOnActionResourcePanel", type="bool", value="true" if show_on_action_panel else "false")
    ET.SubElement(r_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        res_dir.mkdir(parents=True, exist_ok=True)
        res_file.write_text(prettify_xml(root), encoding="utf-8")

    update_localization_xml(loc_file, [(disp_handle, disp_text), (desc_handle, desc_text)], dry_run=dry_run)

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="action-resource",
        uuid=allocated_uuid,
        file=str(res_file),
        dry_run=dry_run,
        details={
            "replenish_type": replenish_type,
            "max_level": max_level,
            "dice_type": dice_type,
            "show_on_action_panel": show_on_action_panel,
            "is_spell_resource": is_spell_resource,
            "display_name_handle": f"{disp_handle};1",
            "description_handle": f"{desc_handle};1",
            "file": str(res_file),
            "localization_file": str(loc_file),
        },
    )


# -----------------------------------------------------------------------------
# Spell & Passive List Scaffolding
# -----------------------------------------------------------------------------

def scaffold_spell_list(
    mod_name_or_path: str,
    spells: str | None = None,
    passives: str | None = None,
    items: str | None = None,
    comment: str | None = None,
    list_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold standalone SpellLists or PassiveLists."""
    _mod_root, mod_folder_dir, _loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    is_passive = bool(passives)
    target_items = passives or spells or items or ""
    parsed_items = split_larian_items(target_items) if target_items else []
    allocated_uuid = list_uuid.strip() if list_uuid else str(uuid.uuid4())
    comment_str = comment if comment else ("Custom Passive List" if is_passive else "Custom Spell List")

    lists_dir = mod_folder_dir / "Lists"
    target_file = lists_dir / ("PassiveLists.lsx" if is_passive else "SpellLists.lsx")
    region_name = "PassiveLists" if is_passive else "SpellLists"
    node_name = "PassiveList" if is_passive else "SpellList"
    attr_name = "Passives" if is_passive else "Spells"

    if target_file.exists():
        tree = ET.parse(target_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx(region_name)

    children = get_or_create_root_children(root, region_name)

    list_node = ET.SubElement(children, "node", id=node_name)
    ET.SubElement(list_node, "attribute", id="Comment", type="LSString", value=comment_str)
    ET.SubElement(list_node, "attribute", id=attr_name, type="LSString", value=";".join(parsed_items))
    ET.SubElement(list_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        lists_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(prettify_xml(root), encoding="utf-8")

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=comment_str,
        asset_type="spell-list",
        uuid=allocated_uuid,
        file=str(target_file),
        dry_run=dry_run,
        details={
            "type": "passives" if is_passive else "spells",
            "comment": comment_str,
            "items": parsed_items,
        },
    )


# -----------------------------------------------------------------------------
# Level Map Scaffolding
# -----------------------------------------------------------------------------

def _parse_level_map_curve(levels: str | None) -> dict[int, str]:
    resolved: dict[int, str] = {}
    if not levels:
        resolved[1] = "1d4"
        return resolved

    for entry in levels.split(","):
        entry = entry.strip()
        if "=" in entry:
            parts = entry.split("=", 1)
            try:
                lvl = int(parts[0].strip())
                val = parts[1].strip()
                resolved[lvl] = val
            except ValueError:
                continue
    if not resolved:
        resolved[1] = "1d4"
    return resolved


def scaffold_level_map(
    mod_name_or_path: str,
    name: str,
    levels: str | None = None,
    dice_type: int = 0,
    map_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold LevelMapValues scaling progression across levels 1-20."""
    _mod_root, mod_folder_dir, _loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    lm_dir = mod_folder_dir / "LevelMapValues"
    lm_file = lm_dir / "LevelMapValues.lsx"

    allocated_uuid = map_uuid.strip() if map_uuid else str(uuid.uuid4())
    resolved_levels = _parse_level_map_curve(levels)

    if lm_file.exists():
        tree = ET.parse(lm_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx("LevelMapValues")

    children = get_or_create_root_children(root, "LevelMapValues")

    for lmnode in list(children.findall("./node[@id='LevelMapSeries']")):
        for attr in lmnode.findall("./attribute"):
            if attr.get("id") == "Name" and attr.get("value") == name:
                children.remove(lmnode)
                break

    lm_node = ET.SubElement(children, "node", id="LevelMapSeries")
    ET.SubElement(lm_node, "attribute", id="Name", type="FixedString", value=name)
    ET.SubElement(lm_node, "attribute", id="PreferredDiceType", type="uint8", value=str(dice_type))
    ET.SubElement(lm_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    current_val = resolved_levels.get(1, "1d4")
    for lvl in range(1, 21):
        if lvl in resolved_levels:
            current_val = resolved_levels[lvl]
        attr_key = f"Level{lvl}"
        ET.SubElement(lm_node, "attribute", id=attr_key, type="LSString", value=current_val)

    if not dry_run:
        lm_dir.mkdir(parents=True, exist_ok=True)
        lm_file.write_text(prettify_xml(root), encoding="utf-8")

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="level-map",
        uuid=allocated_uuid,
        file=str(lm_file),
        dry_run=dry_run,
        details={
            "preferred_dice_type": dice_type,
            "levels": resolved_levels,
        },
    )


# -----------------------------------------------------------------------------
# Default Values Scaffolding
# -----------------------------------------------------------------------------

def _append_default_value_entry(
    file_path: Path,
    items: list[str],
    level: int,
    resolved_table: str,
    dry_run: bool,
) -> str:
    allocated_uuid = str(uuid.uuid4())
    if file_path.exists():
        tree = ET.parse(file_path)
        root = tree.getroot()
    else:
        root = create_empty_lsx("DefaultValues")

    children = get_or_create_root_children(root, "DefaultValues")

    for dnode in list(children.findall("./node[@id='DefaultValue']")):
        match_table = False
        match_lvl = False
        for attr in dnode.findall("./attribute"):
            if attr.get("id") == "TableUUID" and attr.get("value") == resolved_table:
                match_table = True
            elif attr.get("id") == "Level" and attr.get("value") == str(level):
                match_lvl = True
        if match_table and match_lvl:
            children.remove(dnode)
            break

    dv_node = ET.SubElement(children, "node", id="DefaultValue")
    ET.SubElement(dv_node, "attribute", id="Add", type="LSString", value=";".join(items))
    ET.SubElement(dv_node, "attribute", id="Level", type="int32", value=str(level))
    ET.SubElement(dv_node, "attribute", id="TableUUID", type="guid", value=resolved_table)
    ET.SubElement(dv_node, "attribute", id="UUID", type="guid", value=allocated_uuid)

    if not dry_run:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(prettify_xml(root), encoding="utf-8")
    return allocated_uuid


def scaffold_default_values(
    mod_name_or_path: str,
    class_name: str,
    level: int = 1,
    table_uuid: str | None = None,
    abilities: str | None = None,
    skills: str | None = None,
    spells: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold DefaultValues XML entries for starting abilities, skills, and spells."""
    _mod_root, mod_folder_dir, _loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    dv_dir = mod_folder_dir / "DefaultValues"
    resolved_table = (
        table_uuid.strip()
        if table_uuid
        else VANILLA_CLASS_TABLES.get(class_name.strip().lower(), str(uuid.uuid4()))
    )

    created_files: list[str] = []
    details: dict[str, Any] = {
        "class_name": class_name,
        "table_uuid": resolved_table,
        "level": level,
    }

    category_map = [
        ("abilities", abilities, "Abilities.lsx"),
        ("skills", skills, "Skills.lsx"),
        ("spells", spells, "Spells.lsx"),
    ]

    for cat_name, raw_val, file_name in category_map:
        if raw_val:
            parsed = split_larian_items(raw_val)
            if parsed:
                f = dv_dir / file_name
                _append_default_value_entry(f, parsed, level, resolved_table, dry_run)
                created_files.append(str(f))
                details[cat_name] = parsed

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=class_name,
        asset_type="default-values",
        uuid=resolved_table,
        file=created_files[0] if created_files else None,
        dry_run=dry_run,
        details=details,
    )


# -----------------------------------------------------------------------------
# Stat Entry Scaffolding
# -----------------------------------------------------------------------------

def _build_stat_entry_text(
    name: str,
    config: dict[str, Any],
    using: str | None,
    data_props: dict[str, str],
) -> str:
    lines = [f'new entry "{name}"', config["type_header"]]
    active_using = using if using is not None else config["default_using"]
    if active_using:
        lines.append(f'using "{active_using}"')

    for k, v in data_props.items():
        if v is not None:
            lines.append(f'data "{k}" "{v}"')
    lines.append("")
    return "\n".join(lines)


def scaffold_stat(
    mod_name_or_path: str,
    entry_type: str,
    name: str,
    using: str | None = None,
    display_name: str | None = None,
    description: str | None = None,
    properties: dict[str, str] | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Scaffold Larian stat entries and generate localization handles."""
    _mod_root, mod_folder_dir, loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

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
    loc_updates: list[tuple[str, str]] = []

    has_loca = clean_type in (
        "weapon", "armor", "amulet", "ring", "object", "passivedata",
        "status_boost", "spell_target", "spell_shout", "spell_projectile",
        "spell_zone", "spell_teleport", "spell_rush", "spell_path"
    )

    if has_loca:
        disp_handle = generate_larian_handle()
        disp_text = display_name if display_name else name
        loc_updates.append((disp_handle, disp_text))
        data_props["DisplayName"] = f"{disp_handle};1"

        if description or clean_type != "object":
            desc_handle = generate_larian_handle()
            desc_text = description if description else f"{name} description."
            loc_updates.append((desc_handle, desc_text))
            data_props["Description"] = f"{desc_handle};1"

    entry_text = _build_stat_entry_text(name, config, using, data_props)

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

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=name,
        asset_type="stat",
        file=str(target_file),
        dry_run=dry_run,
        details={
            "type": clean_type,
            "display_name_handle": f"{disp_handle};1" if disp_handle else None,
            "description_handle": f"{desc_handle};1" if desc_handle else None,
            "properties": data_props,
        },
    )
