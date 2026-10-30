#!/usr/bin/env python3
"""
scripts/modio_extract.py

Fetches Baldur's Gate 3 mod pak files from mod.io, unpacks Larian LSPK v18 archives,
parses mod data (Stats, Localization, Meta), filters verified in-game features,
and resolves recursive gear/spell/passive mechanics into structured JSON and specs.
"""

import argparse
import io
import json
import os
import re
import struct
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import MODS_DIR, REPO_ROOT, get_subscribed_mods_dir, normalize_mod_key
from bg3_core.larian_parsers import (
    clean_loc_text,
    parse_loca_bytes,
    parse_localization_xml,
    parse_meta_lsx,
    parse_progressions_lsx,
    parse_stats_txt,
)
from bg3_core.lspk import LspkArchive, decompress_pak_file_data, lz4_block_decompress
from bg3_core.update_library_catalog import write_library_catalog
from bg3_core.mod_overrides import (
    BASE_GAME_LOCA_HANDLES,
    BASE_GAME_PASSIVES,
    BASE_GAME_SPELLS,
    MOD_SPECIFIC_OVERRIDES,
)
from bg3_core.modio_client import (
    BG3_GAME_ID,
    MODIO_API_HOST,
    USER_AGENT,
    download_mod_file,
    get_api_key,
    query_modio,
)





# ----------------------------------------------------------------------
# Feature Extraction and In-Game Validation
# ----------------------------------------------------------------------
# Reference dictionaries imported from bg3_core.mod_overrides


def extract_and_verify_features(all_stats, loc_dict, roottemplate_names=None, progressions=None):
    """Filter implemented features, excluding stubs and resolving linked effects."""
    roottemplate_names = roottemplate_names or {}
    progressions = progressions or []
    features = []

    # Separate dictionaries by category for fast cross-referencing
    passives = {k: v for k, v in all_stats.items() if v.get("type") == "PassiveData"}
    spells = {k: v for k, v in all_stats.items() if "Spell" in v.get("type", "")}
    statuses = {k: v for k, v in all_stats.items() if v.get("type") == "StatusData"}
    weapons = {k: v for k, v in all_stats.items() if v.get("type") == "Weapon"}
    armor = {k: v for k, v in all_stats.items() if v.get("type") == "Armor"}
    objects = {k: v for k, v in all_stats.items() if v.get("type") == "Object"}

    def resolve_passive_mechanics(passive_name):
        if passive_name in BASE_GAME_PASSIVES:
            return BASE_GAME_PASSIVES[passive_name]
        p = passives.get(passive_name)
        if not p:
            clean = passive_name.replace("_", " ")
            return f"**{clean}**"
        desc = p.get("resolved_description") or ""
        if passive_name in MOD_SPECIFIC_OVERRIDES:
            desc = MOD_SPECIFIC_OVERRIDES[passive_name]
        disp = p.get("resolved_display_name") or p["name"]
        boosts = p.get("data", {}).get("Boosts", "")
        props = p.get("data", {}).get("Properties", "")
        parts = [f"**{disp}**"]
        if desc:
            parts.append(f"- {desc}")
        details = []
        if boosts:
            details.append(f"Boosts: `{boosts}`")
        if props:
            details.append(f"Properties: `{props}`")
        if details:
            parts.append(f"({'; '.join(details)})")
        return " ".join(parts)

    def resolve_spell_mechanics(spell_name):
        if spell_name in BASE_GAME_SPELLS:
            return BASE_GAME_SPELLS[spell_name]
        s = spells.get(spell_name)
        if not s:
            clean = spell_name.replace("_", " ")
            return f"**{clean}**"
        data = s.get("data", {})
        disp = s.get("resolved_display_name") or s["name"]
        desc = s.get("resolved_description") or ""
        if spell_name in MOD_SPECIFIC_OVERRIDES:
            desc = MOD_SPECIFIC_OVERRIDES[spell_name]
        lvl = data.get("Level", "0")
        school = data.get("SpellSchool", "")
        damage = data.get("SpellSuccess", "") or data.get("Damage", "")
        recharge = data.get("Cooldown", "") or data.get("RechargeRule", "")

        parts = [f"**{disp}**"]
        if lvl == "0":
            parts.append("(Cantrip)")
        else:
            parts.append(f"(Level {lvl} {school})")
        if desc:
            parts.append(f"- {desc}")
        mechanics = []
        if damage:
            mechanics.append(f"Roll/Success: `{damage}`")
        if recharge:
            mechanics.append(f"Cooldown: {recharge}")
        if mechanics:
            parts.append(f"[{'; '.join(mechanics)}]")
        return " ".join(parts)

    # Pre-defined act item sets for acquisition resolution
    pp_act1_items = {
        "PP_Warlock_Equipment_Stone_of_Good_Luck", "PP_Warlock_Equipment_Grimoire_of_Whispers",
        "PP_Warlock_Equipment_Bloodstone_Ring", "PP_Warlock_Equipment_Shortbow_of_the_Binding_Vow",
        "PP_Warlock_Equipment_Blood_Pact_Blade", "PP_Warlock_Equipment_Mantle_of_Eldritch_Echoes",
        "PP_Warlock_Equipment_Boots_of_the_Shadowed_Pact", "PP_Warlock_Equipment_Gauntlets_of_the_Pactkeeper",
        "PP_Warlock_Equipment_Tunic_of_LifeSharing", "PP_Warlock_Equipment_Hood_of_Subjugation"
    }
    pp_act2_items = {
        "PP_Warlock_Equipment_Leechstone_Amulet", "PP_Warlock_Equipment_Band_of_the_Shifting_Sands",
        "PP_Warlock_Equipment_Ring_of_the_Swarm", "PP_Warlock_Equipment_Whisper_of_the_Fallen_Pact",
        "PP_Warlock_Equipment_Shortbow_of_the_Pact_Keeper", "PP_Warlock_Equipment_Soulfire_Shroud",
        "PP_Warlock_Equipment_Boots_of_the_Devouring_Void", "PP_Warlock_Equipment_Gloves_of_the_Pact_Weaver",
        "PP_Warlock_Equipment_Tunic_of_the_Ascended_Warlock", "PP_Warlock_Equipment_Hood_of_the_Whispering_Mind"
    }
    pp_act3_items = {
        "PP_Warlock_Equipment_Amulet_of_the_Eternal_Hunger", "PP_Warlock_Equipment_Ring_of_the_Soul_Siphon",
        "PP_Warlock_Equipment_Knights_Sigil_of_Dusk", "PP_Warlock_Equipment_Soulknife_of_the_Everlasting_Pact",
        "PP_Warlock_Equipment_Shortbow_of_Hellish_Flames", "PP_Warlock_Equipment_Whispersilk_Cloak",
        "PP_Warlock_Equipment_The_Draining_Tread", "PP_Warlock_Equipment_Gloves_of_Eldritch_Power",
        "PP_Warlock_Equipment_Tunic_of_the_Ravenous_Soul", "PP_Warlock_Equipment_Visage_of_the_Inner_Demon"
    }

    for name, entry in all_stats.items():
        etype = entry.get("type", "")
        data = entry.get("data", {})

        # Rule: Filter out stubs or placeholder entries
        if data.get("IsDummy") in ("1", "Yes", "true"):
            continue
        if name.startswith("_") or "test" in name.lower() or "reference" in name.lower():
            if not entry.get("resolved_display_name") and not data.get("PassivesOnEquip"):
                continue

        # Rule: Filter out Tut_ duplicate entries if main entry exists
        if name.startswith("Tut_") and name[4:] in all_stats:
            continue

        # Filter out abstract base templates with no stats or models
        if etype in ("Armor", "Weapon") and not data.get("RootTemplate") and not data.get("ArmorClass") and not data.get("Damage") and not data.get("PassivesOnEquip") and not data.get("Boosts"):
            continue

        disp_name = entry.get("resolved_display_name") or name
        if name == "OHF_SOF_T1_Fighter_Greatsword_Stats" or "Innumerable" in disp_name:
            disp_name = "Korrin's Greatsword (Psychebringer)"

        # 1. Weapon Features
        if etype == "Weapon":
            damage = data.get("Damage", "")
            dmg_type = data.get("Damage Type", "")
            using = entry.get("using", "")
            base_stats = []
            if "Dagger" in using:
                base_stats.append("Type: **Dagger** (1d4 Piercing)")
                base_stats.append("Properties: Finesse, Light, Thrown")
            elif "Shortbow" in using:
                base_stats.append("Type: **Shortbow** (1d6 Piercing)")
                base_stats.append("Properties: Range 18m, Two-Handed")
            elif damage:
                base_stats.append(f"Damage: **{damage} {dmg_type}**".strip())

            def_boosts = data.get("DefaultBoosts", "")
            if "WeaponEnchantment(" in def_boosts:
                m_ench = re.search(r"WeaponEnchantment\((\d+)\)", def_boosts)
                if m_ench:
                    base_stats.append(f"Enchantment: **+{m_ench.group(1)}**")
            if "WeaponProperty(Magical)" in def_boosts:
                base_stats.append("Damage Type: **Magical**")
            rarity = data.get("Rarity", "")
            if rarity:
                base_stats.append(f"Rarity: **{rarity}**")
            if data.get("Damage Range"):
                base_stats.append(f"Crit Range: {data.get('Damage Range')}")
            if data.get("Weapon Range") and "Shortbow" not in using:
                base_stats.append(f"Range: {data.get('Weapon Range')}")
            if data.get("Boosts") and "UnlockSpell" not in data.get("Boosts", ""):
                base_stats.append(f"Stat Boosts: `{data.get('Boosts')}`")

            # Resolve granted abilities/passives
            granted_effects = []
            if data.get("PassivesOnEquip"):
                for p in data["PassivesOnEquip"].split(";"):
                    p = p.strip()
                    if p:
                        granted_effects.append(resolve_passive_mechanics(p))
            if data.get("PassivesMainHand"):
                for p in data["PassivesMainHand"].split(";"):
                    p = p.strip()
                    if p:
                        granted_effects.append(f"[Main Hand] {resolve_passive_mechanics(p)}")
            if "UnlockSpell" in data.get("Boosts", ""):
                for match in re.finditer(r"UnlockSpell\(([^)]+)\)", data.get("Boosts", "")):
                    spell_id = match.group(1).split(",")[0].strip()
                    granted_effects.append(resolve_spell_mechanics(spell_id))

            acq = data.get("ValueUUID", "In-game inventory / Mod container")
            if name in pp_act1_items:
                acq = "Fade's Camp Chest (Act 1 Backpack) & Fade's Equipment Distribution (FED Act 1 world loot)"
            elif name in pp_act2_items:
                acq = "Fade's Camp Chest (Act 2 Backpack) & Fade's Equipment Distribution (FED Act 2 world loot)"
            elif name in pp_act3_items:
                acq = "Fade's Camp Chest (Act 3 Backpack) & Fade's Equipment Distribution (FED Act 3 world loot)"

            features.append(
                {
                    "name": disp_name,
                    "type": "Weapon",
                    "identifier": name,
                    "base_stats": "<br>".join(base_stats) or "Standard weapon attributes",
                    "granted_effects": "<br>".join(granted_effects) or "None",
                    "acquisition": acq,
                }
            )

        # 2. Armor Features
        elif etype == "Armor":
            if name == "MAG_GearUp_Amulet":
                disp_name = "GearUp Amulet"
            ac = data.get("ArmorClass", "")
            ac_type = data.get("ArmorType", "")
            using = entry.get("using", "")
            slot_name = data.get("Slot", "Gear")
            if "ARM_Padded" in using:
                slot_name = "Clothing / Light Armour"
            elif "_Head" in using or "ARM_Hat" in using:
                slot_name = "Headwear"
            elif "_Hand" in using or "ARM_Gloves" in using:
                slot_name = "Handwear (Gloves)"
            elif "_Foot" in using:
                slot_name = "Footwear (Boots)"
            elif "_Back" in using:
                slot_name = "Cloak"
            elif "_Ring" in using:
                slot_name = "Ring"
            elif "_Amulet" in using:
                slot_name = "Amulet"

            base_stats = []
            if ac:
                base_stats.append(f"Base AC: **{ac}**")
            elif ac_type:
                base_stats.append(f"Type: {ac_type}")
            rarity = data.get("Rarity", "")
            if rarity:
                base_stats.append(f"Rarity: **{rarity}**")
            boosts = data.get("Boosts", "")
            if boosts:
                if "AC(1)" in boosts:
                    base_stats.append("Bonus: **+1 Armour Class**")
                elif "Ability(Charisma, 1, 22)" in boosts:
                    base_stats.append("Bonus: **+1 Charisma** (up to 22)")
                elif "UnlockSpell" not in boosts:
                    base_stats.append(f"Boosts: `{boosts}`")

            granted_effects = []
            if data.get("PassivesOnEquip"):
                for p in data["PassivesOnEquip"].split(";"):
                    p = p.strip()
                    if p:
                        granted_effects.append(resolve_passive_mechanics(p))
            if "UnlockSpell" in data.get("Boosts", ""):
                for match in re.finditer(r"UnlockSpell\(([^)]+)\)", data.get("Boosts", "")):
                    spell_id = match.group(1).split(",")[0].strip()
                    granted_effects.append(resolve_spell_mechanics(spell_id))

            acq = data.get("ValueUUID", "In-game inventory / Mod container")
            if name == "MAG_GearUp_Amulet":
                acq = "Tutorial Cart/Chest (Nautiloid) & Act 1–3 Vendors (Arron, Brem, Roah Moonglow, Dammon, Talli, etc.)"
            elif name in pp_act1_items:
                acq = "Fade's Camp Chest (Act 1 Backpack) & Fade's Equipment Distribution (FED Act 1 world loot)"
            elif name in pp_act2_items:
                acq = "Fade's Camp Chest (Act 2 Backpack) & Fade's Equipment Distribution (FED Act 2 world loot)"
            elif name in pp_act3_items:
                acq = "Fade's Camp Chest (Act 3 Backpack) & Fade's Equipment Distribution (FED Act 3 world loot)"

            features.append(
                {
                    "name": disp_name,
                    "type": f"Armor ({slot_name})",
                    "identifier": name,
                    "base_stats": "<br>".join(base_stats) or "Standard armor modifiers",
                    "granted_effects": "<br>".join(granted_effects) or "None",
                    "acquisition": acq,
                }
            )

        # 3. Spells and Cantrips
        elif "Spell" in etype:
            # Filter out internal sub-effects/projectiles or spells without valid display names
            if not entry.get("resolved_display_name") or name.startswith("PP_Projectile_") or name.startswith("PP_DesperateRenewal_"):
                continue

            lvl = data.get("Level", "0")
            school = data.get("SpellSchool", "")
            cooldown = data.get("Cooldown", "") or data.get("RechargeRule", "")
            cost = data.get("SpellActionCost", "")
            roll = data.get("SpellRoll", "")
            success = data.get("SpellSuccess", "")
            spell_type = "Cantrip" if lvl == "0" else f"Level {lvl} Spell"

            base_stats = [f"**{spell_type}** ({school})"]
            if cost:
                base_stats.append(f"Cost: {cost}")
            if cooldown:
                base_stats.append(f"Recharge: {cooldown}")
            if roll:
                base_stats.append(f"Attack Roll: `{roll}`")

            granted_effects = []
            desc = entry.get("resolved_description") or ""
            if name in MOD_SPECIFIC_OVERRIDES:
                desc = MOD_SPECIFIC_OVERRIDES[name]
            elif name in BASE_GAME_SPELLS:
                desc = BASE_GAME_SPELLS[name]
            if desc:
                granted_effects.append(desc)
            if success:
                granted_effects.append(f"Mechanics: `{success}`")

            features.append(
                {
                    "name": disp_name,
                    "type": spell_type,
                    "identifier": name,
                    "base_stats": "<br>".join(base_stats),
                    "granted_effects": "<br>".join(granted_effects) or "Spell effect",
                    "acquisition": "Learned via class level or granted by equipment",
                }
            )

        # 4. Standalone Passives (Feats, Class Passives)
        elif etype == "PassiveData":
            # Filter out internal sub-passives or hidden mechanics
            props = data.get("Properties", "")
            if "IsHidden" in props or name.startswith("PP_AP_") or name.startswith("PP_EP_"):
                continue

            desc = entry.get("resolved_description") or ""
            if name in MOD_SPECIFIC_OVERRIDES:
                desc = MOD_SPECIFIC_OVERRIDES[name]
            elif name in BASE_GAME_PASSIVES:
                desc = BASE_GAME_PASSIVES[name]
            disp = entry.get("resolved_display_name") or ""
            if not disp and not desc:
                continue

            base_stats = []
            if data.get("Properties"):
                base_stats.append(f"Properties: `{data.get('Properties')}`")
            if data.get("Boosts"):
                base_stats.append(f"Boosts: `{data.get('Boosts')}`")

            features.append(
                {
                    "name": disp or name,
                    "type": "Passive Feature",
                    "identifier": name,
                    "base_stats": "<br>".join(base_stats) or "Passive buff/modifier",
                    "granted_effects": desc or data.get("Boosts", "Passive feature mechanics"),
                    "acquisition": "Granted by class, feat, or gear set bonus",
                }
            )

        # 5. Objects / Containers / Upgrade Materials
        elif etype == "Object":
            if "NOT YET IMPLEMENTED" in (entry.get("resolved_description") or ""):
                continue
            if name == "PP_AIO_CHEST" or name.endswith("_BACKPACK"):
                disp = entry.get("resolved_display_name") or roottemplate_names.get(name) or name
                rarity = data.get("Rarity", "Legendary" if "CHEST" in name else "Rare")
                is_chest = "CHEST" in name
                desc = "Master container housing the Act 1, Act 2, and Act 3 curated Warlock equipment backpacks." if is_chest else f"Container backpack containing all 10 curated Warlock equipment items for {name.split('_')[1].capitalize()}."
                features.append(
                    {
                        "name": disp,
                        "type": "Container (Chest)" if is_chest else "Container (Backpack)",
                        "identifier": name,
                        "base_stats": f"Rarity: **{rarity}**<br>Type: Equipment Container",
                        "granted_effects": desc,
                        "acquisition": "Fade's Camp Chest / Tutorial Chest" if is_chest else "Inside master PP_AIO_CHEST or Fade's Camp Chest",
                    }
                )
                continue

            if name.startswith("Chest_") or "GearUP" in name:
                chest_names = {
                    "Chest_GearUP_Main": "Gear Up Equipment Chest",
                    "Chest_GearUp_Main_Dummy": "Dummy Gear Up Chest (10-Turn)",
                    "Chest_GearUP_Armor_Uncommon": "Chest of Uncommon Armor",
                    "Chest_GearUP_Armor_Rare": "Chest of Rare Armor",
                    "Chest_GearUP_Armor_VeryRare": "Chest of Epic Armor",
                    "Chest_GearUP_Armor_Legendary": "Chest of Legendary Gear (Armor)",
                    "Chest_GearUP_Headwear_Uncommon": "Chest of Uncommon Headwear",
                    "Chest_GearUP_Headwear_Rare": "Chest of Rare Headwear",
                    "Chest_GearUP_Headwear_VeryRare": "Chest of Epic Headwear",
                    "Chest_GearUP_Headwear_Legendary": "Chest of Legendary Headwear",
                    "Chest_GearUP_Gloves_Uncommon": "Chest of Uncommon Gloves",
                    "Chest_GearUP_Gloves_Rare": "Chest of Rare Gloves",
                    "Chest_GearUP_Gloves_VeryRare": "Chest of Epic Gloves",
                    "Chest_GearUP_Gloves_Legendary": "Chest of Legendary Gloves",
                    "Chest_GearUP_Shoes_Uncommon": "Chest of Uncommon Shoes",
                    "Chest_GearUP_Shoes_Rare": "Chest of Rare Shoes",
                    "Chest_GearUP_Shoes_VeryRare": "Chest of Epic Shoes",
                    "Chest_GearUP_Shoes_Legendary": "Chest of Legendary Shoes",
                    "Chest_GearUP_Weapon_Uncommon": "Chest of Uncommon Weapons",
                    "Chest_GearUP_Weapon_Rare": "Chest of Rare Weapons",
                    "Chest_GearUP_Weapon_VeryRare": "Chest of Epic Weapons",
                    "Chest_GearUP_Weapon_Legendary": "Chest of Legendary Weapons",
                    "Chest_GearUP_Shields_Uncommon": "Chest of Uncommon Shields",
                    "Chest_GearUP_Shields_Rare": "Chest of Rare Shields",
                    "Chest_GearUP_Shields_VeryRare": "Chest of Epic Shields",
                    "Chest_GearUP_Shields_Legendary": "Chest of Legendary Shields",
                    "Chest_GearUP_Jewelry_Uncommon": "Chest of Uncommon Jewelry",
                    "Chest_GearUP_Jewelry_Rare": "Chest of Rare Jewelry",
                    "Chest_GearUP_Jewelry_VeryRare": "Chest of Very Epic Jewelry",
                    "Chest_GearUP_Jewelry_Legendary": "Chest of Legendary Jewelry",
                    "Chest_GearUP_Gear_Unique": "Chest of Cloaks",
                    "Chest_GearUP_Gear_Divine": "Chest of Other Items",
                }
                disp = chest_names.get(name, entry.get("resolved_display_name") or name.replace("_", " "))
                desc = entry.get("resolved_description") or "Specialized container holding comprehensive sets of gear sorted by category and rarity tier."
                rarity = data.get("Rarity", "")
                stats_list = []
                if rarity:
                    stats_list.append(f"Rarity: **{rarity}**")
                if data.get("Armor"):
                    stats_list.append(f"Armor: **{data.get('Armor')}**")
                if data.get("Flags"):
                    stats_list.append(f"Flags: `{data.get('Flags')}`")

                features.append(
                    {
                        "name": disp,
                        "type": "Container (Chest)",
                        "identifier": name,
                        "base_stats": "<br>".join(stats_list) or "Container",
                        "granted_effects": desc,
                        "acquisition": "Summoned via Summon GearUp Chest or located inside master Gear Up Equipment Chest",
                    }
                )
                continue

            if "cheat" in name.lower() or "backpack" in name.lower():
                continue
            disp_name = entry.get("resolved_display_name") or name
            if not disp_name or disp_name == name:
                rt = data.get("RootTemplate")
                if rt and rt in roottemplate_names:
                    disp_name = roottemplate_names[rt]
            features.append(
                {
                    "name": disp_name,
                    "type": "Consumable / Upgrade Material",
                    "identifier": name,
                    "base_stats": f"Rarity: **{data.get('Rarity', 'Rare')}**<br>Type: Crafting Component",
                    "granted_effects": entry.get("resolved_description") or "Transformative magical stone used in alchemy/item combinations to infuse Tier 1 items into Tier 2 items.",
                    "acquisition": data.get("ValueUUID", "Alchemy / Item Combination / In-game loot"),
                }
            )

    if progressions:
        prog_type_names = {
            "0": "Main Class",
            "1": "Subclass",
            "2": "Race",
            "3": "Origin",
        }
        for p in progressions:
            level = p.get("Level", "")
            name = p.get("Name", "Class")
            uuid = p.get("UUID", "")
            table_uuid = p.get("TableUUID", "")
            boosts = p.get("Boosts", "")
            selectors = p.get("Selectors", "")
            passives_added = p.get("PassivesAdded", "")
            ptype_code = p.get("ProgressionType", "0")
            ptype_desc = prog_type_names.get(ptype_code, "Class Progression")

            stats_lines = [
                f"**Class / Progression**: {name} (Level {level})",
                f"**Progression Type**: {ptype_desc}",
            ]
            if boosts:
                stats_lines.append(f"**Resource Boosts**: `{boosts}`")
            if table_uuid:
                stats_lines.append(f"**Table UUID**: `{table_uuid}`")

            mechanics_lines = []
            if selectors:
                mechanics_lines.append(f"**Selectors**: `{selectors}`")
                m = re.match(r"SelectPassives\(([^,]+),\s*(\d+),\s*([^)]+)\)", selectors)
                if m:
                    plist_uuid, count, list_name = m.groups()
                    if plist_uuid == "333fb1b0-9398-4ca8-953e-6c0f9a59bbed":
                        mechanics_lines.append(
                            f"Modifies the Level {level} {name} progression selector to allow choosing **{count} Eldritch Invocations** (increased from the vanilla 2) from the invocation pool (`{plist_uuid}`).<br>"
                            "Available invocations include:<br>"
                            "• **Agonizing Blast**: Adds Charisma modifier to damage dealt by Eldritch Blast.<br>"
                            "• **Armor of Shadows**: Cast Mage Armor on self at will without expending a spell slot.<br>"
                            "• **Beast Speech**: Cast Speak with Animals at will without expending a spell slot.<br>"
                            "• **Beguiling Influence**: Gain proficiency in Deception and Persuasion skills.<br>"
                            "• **Devil's Sight**: See normally in magical and non-magical darkness up to 24m.<br>"
                            "• **Fiendish Vigor**: Cast False Life on self at will (7 temp HP) without expending a spell slot.<br>"
                            "• **Mask of Many Faces**: Cast Disguise Self at will without expending a spell slot.<br>"
                            "• **Misty Visions**: Cast Silent Image at will without expending a spell slot.<br>"
                            "• **Repelling Blast**: Eldritch Blast hits can push targets up to 4.5m away.<br>"
                            "• **Thief of Five Fates**: Cast Bane using a Warlock spell slot once per Long Rest."
                        )
                    else:
                        mechanics_lines.append(
                            f"Allows choosing **{count}** options from `{list_name}` (`{plist_uuid}`)."
                        )
            if boosts:
                if "WarlockSpellSlot" in boosts:
                    mechanics_lines.append(
                        "Grants 1 additional Level 1 Warlock Spell Slot (`ActionResource(WarlockSpellSlot, 1, 1)`)."
                    )
            if passives_added:
                mechanics_lines.append(f"**Passives Added**: `{passives_added}`")

            feat_name = f"{name} Level {level} Progression (+1 Invocation)" if (name == "Warlock" and level == "2") else f"{name} Level {level} Progression"
            features.append(
                {
                    "name": feat_name,
                    "type": "Class Progression Override",
                    "identifier": uuid or f"{name}_Level_{level}",
                    "base_stats": "<br>".join(stats_lines),
                    "granted_effects": "<br>".join(mechanics_lines) if mechanics_lines else "Modifies progression rules.",
                    "acquisition": f"Granted automatically during level-up upon reaching Level {level} in {name}.",
                }
            )

    return features


# ----------------------------------------------------------------------
# Categorization & Spec Generator
# ----------------------------------------------------------------------
def determine_category(mod_metadata, features):
    """Categorize mod into Gear, Spells, Classes, Progression, or Cheats/Utilities."""
    tags = [t.get("name", "").lower() for t in mod_metadata.get("tags", [])]

    name_lower = mod_metadata.get("name", "").lower()
    if "cheats" in tags or "cheat" in name_lower or "instant" in name_lower or "free" in name_lower:
        return "Utilities & Cheats"
    if "classes" in tags or "subclasses" in tags or "races" in tags:
        return "Classes & Subclasses"
    if "spells" in tags:
        return "Spells"
    if "equipment" in tags or "armor" in tags or "weapons" in tags:
        return "Gear"

    # Analyze features
    types = [f["type"].lower() for f in features]
    if any("weapon" in t or "armor" in t for t in types):
        return "Gear"
    if any("spell" in t or "cantrip" in t for t in types):
        return "Spells"
    if any("level" in mod_metadata.get("name", "").lower() or "curve" in mod_metadata.get("name", "").lower() for t in types):
        return "Progression & Rules"

    return "Utilities & Cheats"


def generate_spec_markdown(mod_metadata, meta_lsx, features, category):
    """Generate rich README.md spec for the mod."""
    name = mod_metadata.get("name", "Unknown Mod")
    summary = mod_metadata.get("summary", "")
    author = meta_lsx.get("Author") or mod_metadata.get("submitted_by", {}).get("username", "Unknown")
    version = mod_metadata.get("modfile", {}).get("version") or meta_lsx.get("Version64") or "1.0.0"
    mod_id = mod_metadata.get("id") or ""
    slug = mod_metadata.get("name_id") or ""

    overview_text = summary or "Detailed specification of implemented features and mechanics in this mod."
    if slug == "gearup":
        overview_text = (
            "The **GearUp** mod introduces a comprehensive equipment summoning system that grants players immediate access to all vanilla Baldur's Gate 3 weapons, armor, shields, headwear, gloves, footwear, jewelry, and cloaks of Uncommon rarity and above directly from the start of the campaign.\n\n"
            "Upon loading into the game, the **GearUp Amulet** is automatically seeded into the Tutorial Cart/Chest on the Nautiloid (`TUT_Chest_Potions`) as well as into the inventories of primary Act 1, Act 2, and Act 3 traders (including Arron, Dammon, Brem, Roah Moonglow, Quartermaster Talli, and Lann Tarv). Equipping the amulet grants the **Summon GearUp Chest** conjuration spell (`Target_SummonGearUpChest_no_Despawn`), allowing the player to summon the master **Gear Up Equipment Chest** directly into their inventory permanently without despawning. Inside the master chest are 27 specialized sub-chests neatly categorized by gear slot and rarity tier (Uncommon, Rare, Epic/Very Rare, and Legendary), allowing players to test, theorycraft, or gear up for any build archetype at any point in their playthrough."
        )

        def gearup_sort_key(f):
            fid = f.get("identifier", "")
            ftype = f.get("type", "")
            if "SummonGearUpChest" in fid:
                return (0, fid)
            if "GearUp_Amulet" in fid:
                return (1, fid)
            if "Chest_GearUP_Main" in fid:
                return (2, fid)
            if ftype.startswith("Container"):
                return (3, f.get("name", ""))
            return (4, fid)

        features = sorted(features, key=gearup_sort_key)
    elif slug == "warlockinvocation":
        overview_text = (
            "**+1 Warlock Invocation** modifies the Baldur's Gate 3 Warlock class progression at Level 2, allowing characters to select **3 Eldritch Invocations** instead of the vanilla limit of 2.\n\n"
            "By altering the class progression selector table (`SelectPassives`), this mod enhances early-game customization and versatility, enabling Warlock builds to acquire key synergistic invocations immediately (such as combining *Agonizing Blast*, *Repelling Blast*, and *Devil's Sight* at Level 2) without delaying other progression choices."
        )
    elif slug == "pact-and-power-warlock-equipment":
        overview_text = (
            "**Pact and Power: Warlock Equipment** introduces 30 uniquely curated equipment pieces (10 per Act) specifically designed to enhance every aspect of the Warlock class across all three Pact Boons: *Pact of the Blade*, *Pact of the Tome*, and *Pact of the Chain*.\n\n"
            "Each item features customized mechanics ranging from pact-scaling weapon enhancements and spell slot restoration to dark retaliatory wards, necrotic damage surges, and patron synergies. All 30 items are immersively distributed across the campaign using **Fade's Equipment Distribution (FED)**, and can also be acquired immediately from the camp chest via **Fade's Camp Chest** (or the master container `PP_AIO_CHEST` containing the Act 1, Act 2, and Act 3 backpacks)."
        )

        def pp_sort_key(f):
            fid = f.get("identifier", "")
            ftype = f.get("type", "")
            facq = f.get("acquisition", "")
            if "PP_AIO_CHEST" in fid:
                return (0, 0, fid)
            if "BACKPACK" in fid:
                return (0, 1 if "ONE" in fid else (2 if "TWO" in fid else 3), fid)
            if "Act 1" in facq:
                return (1, 0, fid)
            if "Act 2" in facq:
                return (2, 0, fid)
            if "Act 3" in facq:
                return (3, 0, fid)
            if "Weapon" in ftype:
                return (4, 0, fid)
            if "Armor" in ftype:
                return (4, 1, fid)
            return (5, 0, fid)

        features = sorted(features, key=pp_sort_key)

    lines = [
        f"# Mod Specification: {name}",
        f"**Category**: {category} | **Author**: {author} | **Version**: {version} | **mod.io ID**: `{mod_id}`",
        f"**Mod Slug**: `{slug}` | **Features Documented**: {len(features)} implemented",
        f"**URL**: `https://mod.io/g/baldursgate3/m/{slug}`",
        "",
        "---",
        "",
        "## Overview",
        overview_text,
        "",
        "---",
        "",
        "## Implemented In-Game Features",
        "",
    ]

    if not features:
        lines.append("*No standalone stats entries detected; mod functions via script or system overrides.*")
    else:
        lines.append("| Feature Name & Type | In-Game Identifier | Base Stats & Modifiers | Granted Abilities, Spells & Passives (Full Mechanics) | Acquisition & Usage |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for f in features:
            f_name = f["name"].replace("|", "\\|")
            f_type = f["type"].replace("|", "\\|")
            f_id = f"`{f['identifier']}`"
            f_stats = f["base_stats"].replace("|", "\\|")
            f_effects = f["granted_effects"].replace("|", "\\|")
            f_acq = f["acquisition"].replace("|", "\\|")
            lines.append(f"| **{f_name}**<br>*{f_type}* | {f_id} | {f_stats} | {f_effects} | {f_acq} |")

    lines.append("")
    return "\n".join(lines)


def update_library_markdown(library_path):
    """Regenerate the complete library from specs while preserving known IDs."""
    write_library_catalog(library_file=Path(library_path), mods_dir=Path(library_path).parent)


# ----------------------------------------------------------------------
# Main Execution Pipeline
# ----------------------------------------------------------------------
def process_mod(query="", pak_path=None, output_dir=None, write_spec=False, update_library=False):
    if pak_path:
        pak_file = Path(pak_path).resolve()
        if not pak_file.is_file():
            raise FileNotFoundError(f"PAK file not found: {pak_path}")
        archive_bytes = pak_file.read_bytes()
        mod_name = pak_file.stem
        slug = normalize_mod_key(mod_name)
        mod_meta = {
            "id": 0,
            "name": mod_name,
            "name_id": slug,
            "summary": f"Local package {pak_file.name}",
        }
    else:
        if not query:
            raise ValueError("Either query or pak_path must be provided.")
        api_key = get_api_key()
        if not api_key:
            raise RuntimeError("MODIO_API_KEY environment variable is not set. Please export MODIO_API_KEY.")

        # 1. Query mod.io
        mod_meta = query_modio(query, api_key)
        mod_name = mod_meta["name"]
        slug = mod_meta["name_id"]

        # 2. Download mod
        archive_bytes = download_mod_file(mod_meta, api_key)

    if not output_dir:
        output_dir = str(get_subscribed_mods_dir() / slug)

    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # 3. Extract pak files from zip if zipped
    pak_payloads = []
    if archive_bytes[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
            for item in z.namelist():
                if item.lower().endswith(".pak"):
                    pak_payloads.append((item, z.read(item)))
    elif archive_bytes[:4] == b"LSPK":
        pak_payloads.append((f"{slug}.pak", archive_bytes))
    else:
        raise RuntimeError(f"Unrecognized archive format downloaded for '{mod_name}'")

    if not pak_payloads:
        raise RuntimeError(f"No .pak files found inside mod download for '{mod_name}'")

    # 4. Unpack pak files & extract key data files
    all_stats = {}
    loc_dict = dict(BASE_GAME_LOCA_HANDLES)
    meta_lsx = {}
    roottemplate_files = {}
    all_progressions = []

    for pak_name, pak_data in pak_payloads:
        archive = LspkArchive(pak_data)
        for f in archive.files:
            fname = f["name"]
            floc = fname.lower()

            if "stats/generated/data" in floc and floc.endswith(".txt"):
                content = archive.extract_file(f)
                base_fname = os.path.basename(fname)
                with open(os.path.join(data_dir, base_fname), "wb") as out:
                    out.write(content)
                parsed = parse_stats_txt(content)
                all_stats.update(parsed)

            elif "localization" in floc and (floc.endswith(".xml") or floc.endswith(".loca")):
                content = archive.extract_file(f)
                base_fname = os.path.basename(fname)
                with open(os.path.join(data_dir, base_fname), "wb") as out:
                    out.write(content)
                if floc.endswith(".xml"):
                    loc_dict.update(parse_localization_xml(content))
                elif floc.endswith(".loca"):
                    try:
                        loc_dict.update(parse_loca_bytes(content))
                    except Exception:
                        pass

            elif fname.endswith("meta.lsx"):
                content = archive.extract_file(f)
                with open(os.path.join(data_dir, "meta.lsx"), "wb") as out:
                    out.write(content)
                meta_lsx.update(parse_meta_lsx(content))

            elif "roottemplates" in floc and floc.endswith((".lsf", ".lsx")):
                content = archive.extract_file(f)
                base_fname = os.path.basename(fname)
                if floc.endswith(".lsx"):
                    with open(os.path.join(data_dir, base_fname), "wb") as out:
                        out.write(content)
                roottemplate_files[fname] = content

            elif "progressions" in floc and floc.endswith(".lsx"):
                content = archive.extract_file(f)
                base_fname = os.path.basename(fname)
                with open(os.path.join(data_dir, base_fname), "wb") as out:
                    out.write(content)
                all_progressions.extend(parse_progressions_lsx(content))

    # Parse display names from RootTemplates
    roottemplate_names = {}
    for rt_path, rt_content in roottemplate_files.items():
        if rt_path.lower().endswith(".lsx") or b"<?xml" in rt_content[:100] or b"<save>" in rt_content[:100]:
            try:
                rt_root = ET.fromstring(rt_content.decode("utf-8", errors="ignore"))
                for node in rt_root.findall('.//node[@id="GameObjects"]'):
                    attrs = {child.get("id"): (child.get("value") or child.get("handle")) for child in node.findall("attribute")}
                    mkey = attrs.get("MapKey")
                    stat_id = attrs.get("Stats")
                    dhandle = attrs.get("DisplayName", "").split(";")[0]
                    if dhandle and dhandle in loc_dict:
                        dtext = loc_dict[dhandle]
                        if mkey:
                            roottemplate_names[mkey] = dtext
                        if stat_id:
                            roottemplate_names[stat_id] = dtext
            except Exception:
                pass
        rt_uuid = os.path.splitext(os.path.basename(rt_path))[0]
        handles = [h.decode("ascii") for h in re.findall(rb"h[0-9a-f]{4,8}g[0-9a-f]{4}g[0-9a-f]{4}g[0-9a-f]{4}g[0-9a-f]{10,14}|h[0-9a-f]{32}", rt_content)]
        texts = [loc_dict[h] for h in handles if h in loc_dict]
        if texts and rt_uuid not in roottemplate_names:
            roottemplate_names[rt_uuid] = texts[0]

    # Resolve inheritance in stats (using entries)
    for name, entry in all_stats.items():
        parent_name = entry.get("using")
        visited = set()
        while parent_name and parent_name in all_stats and parent_name not in visited:
            visited.add(parent_name)
            parent = all_stats[parent_name]
            for k, v in parent.get("data", {}).items():
                if k not in entry["data"]:
                    entry["data"][k] = v
            if not entry.get("resolved_display_name") and parent.get("resolved_display_name"):
                entry["resolved_display_name"] = parent["resolved_display_name"]
            if not entry.get("resolved_description") and parent.get("resolved_description"):
                entry["resolved_description"] = parent["resolved_description"]
            parent_name = parent.get("using")

    # Re-resolve display names with full localization dictionary and root templates
    for name, entry in all_stats.items():
        data = entry["data"]
        disp_handle = data.get("DisplayName", "").split(";")[0]
        desc_handle = data.get("Description", "").split(";")[0]
        if disp_handle in loc_dict:
            entry["resolved_display_name"] = loc_dict[disp_handle]
        if desc_handle in loc_dict:
            entry["resolved_description"] = loc_dict[desc_handle]
        rt = data.get("RootTemplate")
        if rt and rt in roottemplate_names:
            if not entry.get("resolved_display_name") or entry["resolved_display_name"] == name:
                entry["resolved_display_name"] = roottemplate_names[rt]
        if name in roottemplate_names:
            if not entry.get("resolved_display_name") or entry["resolved_display_name"] == name:
                entry["resolved_display_name"] = roottemplate_names[name]
        clean_name = name[4:] if name.startswith("Tut_") else name
        if clean_name in roottemplate_names:
            if not entry.get("resolved_display_name") or entry["resolved_display_name"] == name:
                entry["resolved_display_name"] = roottemplate_names[clean_name]

    # 5. Extract and verify features
    features = extract_and_verify_features(all_stats, loc_dict, roottemplate_names=roottemplate_names, progressions=all_progressions)
    category = determine_category(mod_meta, features)

    # 6. Generate spec if requested
    spec_md = generate_spec_markdown(mod_meta, meta_lsx, features, category)
    if write_spec:
        with open(os.path.join(output_dir, "README.md"), "w", encoding="utf-8") as out:
            out.write(spec_md)

    # 7. Update library.md if requested
    if update_library or write_spec:
        lib_path = str(get_subscribed_mods_dir() / "library.md")
        update_library_markdown(lib_path)

    result = {
        "mod_name": mod_name,
        "slug": slug,
        "mod_id": mod_meta["id"],
        "category": category,
        "summary": mod_meta.get("summary", ""),
        "output_dir": output_dir,
        "features_count": len(features),
        "features": features,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch, unpack, and parse BG3 mods from mod.io or local .pak archives.")
    parser.add_argument("query_pos", nargs="?", help="Mod name, slug, URL, or ID on mod.io (positional)")
    parser.add_argument("--query", "-q", dest="query_flag", help="Mod name, slug, URL, or ID on mod.io")
    parser.add_argument("--pak", help="Path to local .pak file to unpack and document")
    parser.add_argument("--output-dir", "-o", help="Directory where mod spec and data will be saved")
    parser.add_argument("--write-spec", action="store_true", help="Write README.md directly to output directory")
    parser.add_argument("--update-library", action="store_true", help="Update mods/library.md with documented mod")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")

    args = parser.parse_args()

    query_val = args.query_flag or args.query_pos
    if not query_val and not args.pak:
        err_color = ConsoleColor(stream=sys.stderr)
        print(f"{err_color.red('[ERROR]')} Either a mod query or --pak must be provided.", file=sys.stderr)
        sys.exit(ExitCode.USAGE)

    try:
        res = process_mod(
            query=query_val or "",
            pak_path=args.pak,
            output_dir=args.output_dir,
            write_spec=args.write_spec,
            update_library=args.update_library,
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            color = ConsoleColor(stream=sys.stdout)
            print(f"{color.green('[✓]')} Successfully processed mod '{res['mod_name']}' ({res['slug']})")
            print(f"    Category: {res['category']}")
            print(f"    Features documented: {res['features_count']}")
            print(f"    Directory: {res['output_dir']}")
        return ExitCode.OK
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            err_color = ConsoleColor(stream=sys.stderr)
            print(f"{err_color.red('[ERROR]')} processing mod '{query_val or args.pak}': {e}", file=sys.stderr)
        sys.exit(ExitCode.GENERAL)


if __name__ == "__main__":
    sys.exit(main())
