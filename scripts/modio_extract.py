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

BG3_GAME_ID = 6715
MODIO_API_HOST = "g-6715.modapi.io"


def get_api_key():
    """Retrieve MODIO_API_KEY from environment or .env file."""
    key = os.environ.get("MODIO_API_KEY")
    if key:
        return key.strip()

    # Check project .env
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_file = os.path.join(workspace_root, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MODIO_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    # Check home .config/modio/env
    home_env = os.path.expanduser("~/.config/modio/env")
    if os.path.exists(home_env):
        with open(home_env, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MODIO_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    return None


# ----------------------------------------------------------------------
# Pure-Python LZ4 Block Decompressor
# ----------------------------------------------------------------------
def lz4_block_decompress(compressed_data, uncompressed_size):
    """Decompresses standard LZ4 raw block data without external C libraries."""
    src = io.BytesIO(compressed_data)
    dst = bytearray()

    while len(dst) < uncompressed_size:
        token_b = src.read(1)
        if not token_b:
            break
        token = token_b[0]

        # 1. Literals
        literal_len = (token >> 4) & 0x0F
        if literal_len == 15:
            while True:
                extra = src.read(1)
                if not extra:
                    break
                b = extra[0]
                literal_len += b
                if b != 255:
                    break

        lit = src.read(literal_len)
        dst.extend(lit)

        if len(dst) >= uncompressed_size:
            break

        # 2. Match offset
        offset_b = src.read(2)
        if not offset_b or len(offset_b) < 2:
            break
        offset = struct.unpack("<H", offset_b)[0]
        if offset == 0:
            break

        # 3. Match length
        match_len = (token & 0x0F) + 4
        if match_len == 19:
            while True:
                extra = src.read(1)
                if not extra:
                    break
                b = extra[0]
                match_len += b
                if b != 255:
                    break

        for _ in range(match_len):
            dst.append(dst[-offset])

    return bytes(dst)


def decompress_pak_file_data(pak_bytes, offset, disk_size, uncomp_size, flags):
    """Decompress file data from pak archive based on compression flags."""
    raw = pak_bytes[offset : offset + disk_size]
    method = flags & 0x0F

    if method == 0 or disk_size == uncomp_size:
        return raw
    elif method == 1:
        import zlib
        return zlib.decompress(raw)
    elif method == 2:
        # LZ4 compression
        try:
            return lz4_block_decompress(raw, uncomp_size)
        except Exception:
            # If prefixed by 4-byte chunk size
            if len(raw) > 4:
                try:
                    return lz4_block_decompress(raw[4:], uncomp_size)
                except Exception:
                    pass
            return raw
    return raw


# ----------------------------------------------------------------------
# LSPK Archive Unpacker (Larian Package v18)
# ----------------------------------------------------------------------
class LspkArchive:
    def __init__(self, data_bytes):
        self.data = data_bytes
        self.files = []
        self._parse_header_and_filelist()

    def _parse_header_and_filelist(self):
        if len(self.data) < 40 or self.data[:4] != b"LSPK":
            raise ValueError("Not a valid LSPK package (magic mismatch)")

        version, file_list_offset, file_list_size, flags, priority = struct.unpack_from(
            "<IQIBB", self.data, 4
        )

        file_list_raw = self.data[file_list_offset : file_list_offset + file_list_size]
        if len(file_list_raw) < 8:
            return

        num_files, comp_size = struct.unpack_from("<II", file_list_raw, 0)
        lz4_payload = file_list_raw[8 : 8 + comp_size]
        expected_size = num_files * 272

        try:
            decomp = lz4_block_decompress(lz4_payload, expected_size)
        except Exception as e:
            decomp = file_list_raw[8:]

        for i in range(num_files):
            entry_bytes = decomp[i * 272 : (i + 1) * 272]
            if len(entry_bytes) < 272:
                break
            name = entry_bytes[:256].split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
            offset_low, offset_high, part, file_flags, size_disk, size_uncomp = struct.unpack_from(
                "<IHBBII", entry_bytes, 256
            )
            offset = offset_low | (offset_high << 32)
            self.files.append(
                {
                    "name": name.replace("\\", "/"),
                    "offset": offset,
                    "disk_size": size_disk,
                    "uncomp_size": size_uncomp,
                    "flags": file_flags,
                }
            )

    def extract_file(self, entry):
        return decompress_pak_file_data(
            self.data,
            entry["offset"],
            entry["disk_size"],
            entry["uncomp_size"],
            entry["flags"],
        )


# ----------------------------------------------------------------------
# mod.io API Client
# ----------------------------------------------------------------------
def query_modio(query_or_slug, api_key):
    """Search mod.io for BG3 mod by name, slug, URL, or ID."""
    clean_query = query_or_slug.strip()

    # If URL: https://mod.io/g/baldursgate3/m/<slug>
    if "mod.io" in clean_query:
        parts = clean_query.rstrip("/").split("/")
        clean_query = parts[-1]

    # Try exact slug or ID match first
    if clean_query.isdigit():
        slug_candidates = [clean_query]
        is_id = True
    else:
        is_id = False
        candidates = [
            clean_query.lower(),
            clean_query.lower().replace(" ", "-"),
            clean_query.lower().replace(" ", ""),
        ]
        slug_candidates = []
        for c in candidates:
            if re.match(r"^[a-z0-9-]+$", c) and c not in slug_candidates:
                slug_candidates.append(c)

    for cand in slug_candidates:
        params = {"api_key": api_key}
        if is_id:
            params["id"] = cand
        else:
            params["name_id"] = cand

        url = f"https://{MODIO_API_HOST}/v1/games/{BG3_GAME_ID}/mods?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "BG3ModDocPipeline/1.0"})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("data") and len(data["data"]) > 0:
                    return data["data"][0]
        except Exception:
            pass

    # Fallback to general search query
    clean_q_alpha = re.sub(r"[^a-z0-9]", "", clean_query.lower())
    search_queries = [clean_query]
    if clean_q_alpha and clean_q_alpha != clean_query.lower():
        search_queries.append(clean_q_alpha)

    results = []
    for q_term in search_queries:
        params = {"api_key": api_key, "_q": q_term}
        url = f"https://{MODIO_API_HOST}/v1/games/{BG3_GAME_ID}/mods?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "BG3ModDocPipeline/1.0"})

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                batch = data.get("data", [])
                if batch:
                    results.extend(batch)
        except Exception:
            pass

        # Select best match: exact name match, slug match, or alphanumeric match
        for m in results:
            m_name = m.get("name", "").lower()
            m_slug = m.get("name_id", "").lower()
            if (
                m_name == clean_query.lower()
                or m_slug == clean_query.lower()
                or re.sub(r"[^a-z0-9]", "", m_name) == clean_q_alpha
                or re.sub(r"[^a-z0-9]", "", m_slug) == clean_q_alpha
            ):
                return m

    if not results:
        raise RuntimeError(f"No mods found on mod.io matching: '{query_or_slug}'")

    query_tokens = set(re.findall(r"\w+", clean_query.lower()))
    if query_tokens:
        def match_score(mod_entry):
            name_tokens = set(re.findall(r"\w+", mod_entry.get("name", "").lower()))
            slug_tokens = set(re.findall(r"\w+", mod_entry.get("name_id", "").lower()))
            all_tokens = name_tokens | slug_tokens
            overlap = len(query_tokens.intersection(all_tokens))
            is_all = 1 if query_tokens.issubset(all_tokens) else 0
            norm_match = 1 if re.sub(r"[^a-z0-9]", "", mod_entry.get("name", "").lower()) == clean_q_alpha else 0
            return (norm_match, is_all, overlap)

        results_sorted = sorted(results, key=match_score, reverse=True)
        if results_sorted and match_score(results_sorted[0])[2] > 0:
            return results_sorted[0]

    return results[0]


def download_mod_file(mod_metadata, api_key):
    """Download mod archive (.zip or .pak) from mod.io."""
    modfile = mod_metadata.get("modfile")
    if not modfile or not modfile.get("download", {}).get("binary_url"):
        raise RuntimeError(f"Mod '{mod_metadata.get('name')}' has no active file download available.")

    download_url = modfile["download"]["binary_url"]
    sep = "&" if "?" in download_url else "?"
    signed_url = f"{download_url}{sep}api_key={api_key}"

    req = urllib.request.Request(signed_url, headers={"User-Agent": "BG3ModDocPipeline/1.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


# ----------------------------------------------------------------------
# Game Data Parsers (Stats, Localization, Meta)
# ----------------------------------------------------------------------
def clean_loc_text(text):
    """Strip Larian markup tags like <LSTag ...>text</LSTag> from localized text."""
    if not text:
        return ""
    # Strip opening and closing LSTags
    clean = re.sub(r"</?LSTag[^>]*>", "", text)
    return clean.strip()


def parse_localization_xml(xml_bytes):
    """Parse english.xml into a handle -> text dictionary."""
    loc_dict = {}
    if not xml_bytes:
        return loc_dict
    try:
        root = ET.fromstring(xml_bytes.decode("utf-8", errors="ignore"))
        for elem in root.findall(".//content"):
            handle = elem.get("contentuid")
            text = elem.text
            if handle and text:
                loc_dict[handle] = clean_loc_text(text)
    except Exception:
        pass
    return loc_dict


def parse_stats_txt(txt_bytes, loc_dict=None):
    """Parse Larian stats text (new entry / data lines)."""
    loc_dict = loc_dict or {}
    text = txt_bytes.decode("utf-8", errors="ignore")
    entries = {}
    current_entry = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        entry_match = re.match(r'^new\s+entry\s+"([^"]+)"', line, re.I)
        if entry_match:
            name = entry_match.group(1)
            current_entry = {
                "name": name,
                "type": "",
                "using": "",
                "data": {},
            }
            entries[name] = current_entry
            continue

        if not current_entry:
            continue

        type_match = re.match(r'^type\s+"([^"]+)"', line, re.I)
        if type_match:
            current_entry["type"] = type_match.group(1)
            continue

        using_match = re.match(r'^using\s+"([^"]+)"', line, re.I)
        if using_match:
            current_entry["using"] = using_match.group(1)
            continue

        data_match = re.match(r'^data\s+"([^"]+)"\s+"([^"]*)"', line, re.I)
        if data_match:
            key, val = data_match.group(1), data_match.group(2)
            current_entry["data"][key] = val

    # Resolve display names and descriptions
    for name, entry in entries.items():
        data = entry["data"]
        disp_handle = data.get("DisplayName", "").split(";")[0]
        desc_handle = data.get("Description", "").split(";")[0]
        entry["resolved_display_name"] = loc_dict.get(disp_handle, data.get("DisplayName", ""))
        entry["resolved_description"] = loc_dict.get(desc_handle, data.get("Description", ""))

    return entries


def parse_meta_lsx(lsx_bytes):
    """Parse meta.lsx for mod UUID, author, version, and description."""
    meta = {}
    if not lsx_bytes:
        return meta
    try:
        text = lsx_bytes.decode("utf-8", errors="ignore")
        root = ET.fromstring(text)
        for node in root.findall(".//node[@id='ModuleInfo']//attribute"):
            attr_id = node.get("id")
            val = node.get("value")
            if attr_id and val:
                meta[attr_id] = val
    except Exception:
        pass
    return meta


def parse_progressions_lsx(lsx_bytes):
    """Parse Progressions.lsx for progression nodes."""
    progressions = []
    if not lsx_bytes:
        return progressions
    try:
        text = lsx_bytes.decode("utf-8", errors="ignore")
        root = ET.fromstring(text)
        for node in root.findall(".//node[@id='Progression']"):
            p = {}
            for attr in node.findall("./attribute"):
                attr_id = attr.get("id")
                val = attr.get("value")
                if attr_id and val is not None:
                    p[attr_id] = val
            if p:
                progressions.append(p)
    except Exception:
        pass
    return progressions


# ----------------------------------------------------------------------
# Feature Extraction and In-Game Validation
# ----------------------------------------------------------------------
BASE_GAME_PASSIVES = {
    "ARM_MagicalPlate_1_Passive": "**Magical Plate** - Incoming damage is reduced by 1.",
    "ARM_SuperiorPlate_1_Passive": "**Magical Plate** - Incoming damage is reduced by 1.",
    "ARM_SuperiorPlate_2_Passive": "**Superior Magical Plate** - Incoming damage is reduced by 2.",
    "ARM_MartialArtsLethality_2_Passive": "**Martial Arts Lethality** - Unarmed attacks gain a +2 bonus to attack rolls and damage.",
    "DEN_HellridersPride_Passive": "**Pride of Hell** - When you heal a creature, it gains Resistance against Bludgeoning, Piercing, and Slashing damage dealt by weapon attacks for 2 turns.",
    "UNI_MassHealRing_Passive": "**The Whispering Promise** - When you heal a creature, it gains a +1d4 bonus to Attack Rolls and Saving Throws for 2 turns.",
    "MAG_Violence_ViolenceOnDash_Passive": "**Linebreaker** - When dashing or taking a similar action in combat, gain 2 turns of Wrath (+1 damage to melee weapon attacks per turn remaining).",
    "MAG_Violence_LowHP_Violence_Passive": "**Bloodlust** - When hit points fall below 50%, gain 3 turns of Wrath (+1 damage to melee weapon attacks per turn remaining).",
    "MAG_Violence_ViolenceOnDamaged_Passive": "**Wrath on Damaged** - When the wearer takes damage, gain 1 turn of Wrath.",
    "MAG_Rage_TempHPOnExit_Passive": "**Rage Discharge** - When Rage ends, gain temporary hit points.",
    "MAG_Monk_Magic_Boots_Passive": "**Kushigo Boots** - Adds Wisdom Modifier to unarmed attack damage.",
    "MAG_Monk_Magic_Gloves_Passive": "**Kushigo Gloves** - Deals an additional 1d4 damage with Throw attacks and unarmed strikes.",
    "MAG_Monk_Magic_Hat_Passive": "**Kushigo Hat** - Gain +1 bonus to Ki Save DC.",
    "MAG_Thunder_Reverberation_Gloves_Passive": "**Belligerent Skies** - Dealing Thunder, Lightning, or Radiant damage inflicts 2 turns of Reverberation (-1 penalty to Str, Dex, and Con saving throws per turn; at 5 stacks deals 1d4 Thunder damage and knocks Prone).",
    "MAG_Thunder_ReverberationOnStatusApply_Boots_Passive": "**Stormy Clamour** - Inflicting a condition upon a hostile creature applies 2 turns of Reverberation.",
    "MAG_Thunder_InflictDazeOnReverberatedCreature_Cloak_Passive": "**Thunderskin Cloak** - When a creature with Reverberation damages the wearer, it must succeed a Constitution saving throw or become Dazed.",
    "MAG_Infernal_Metal_Boots_AntiDisplacement_Passive": "**Helldusk Stride** - Cannot be forcibly moved by a foe's spells or actions, and ignores Difficult Terrain.",
    "MAG_Barbarian_Armor_BoneSpike_Passive": "**Bonespike Garb** - Gain +15 Temporary Hit Points upon entering Rage; melee attackers take Piercing damage equal to your Constitution modifier.",
    "MAG_Barbarian_Helmet_BoneSpike_Passive": "**Bonespike Helmet** - Hostile creatures within 3m must make a Wisdom save when you Rage or take Psychic damage. Gain +2 to Intimidation.",
    "MAG_Barbarian_Gloves_BoneSpike_Passive": "**Bonespike Gloves** - Attacks ignore Slashing, Piercing, and Bludgeoning Resistance.",
    "MAG_Barbarian_Armor_RageSupport_Passive": "**Raging Vigor** - While raging, gain additional bonuses to saving throws and temporary hit points.",
    "MAG_Radiant_RadiatingOrb_Ring_Passive": "**Coruscation Ring** - Dealing spell damage while illuminated inflicts 2 turns of Radiating Orb (-1 penalty to Attack Rolls per turn remaining).",
    "MAG_Radiant_RadiatingOrb_Gloves_Passive": "**Luminous Gloves** - Dealing Radiant damage inflicts 2 turns of Radiating Orb on the target.",
    "MAG_Radiant_RadiatingOrb_Melee_OnDamage_Passive": "**Luminous Strike** - Melee attacks dealing Radiant damage inflict Radiating Orb.",
    "MAG_Radiant_Radiating_Helmet_Passive": "**Holy Lance Helm** - When an attacker misses the wearer, they must succeed a Dexterity saving throw or take 1d4 Radiant damage.",
    "MAG_Healer_HealSelf_Passive": "**Wapira's Crown** - When healing another creature, the wearer regains 1d6 hit points.",
    "UND_SocietyOfBrilliance_DarkvisionRing_Passive": "**Darkvision & Mind Shielding** - Gain Darkvision up to 12m and Advantage on Saving Throws against being Charmed.",
    "UND_SocietyOfBrilliance_PullingRing_Passive": "**Telekinetic Pull** - Pulls surrounding targets closer on spell cast or thunder damage.",
    "UND_SocietyOfBrilliance_MagicMissileNecklace_Passive": "**Psychic Spark** - Cast Magic Missile with 1 additional dart.",
    "UND_Tower_StaffBlessMystra_Passive": "**Bless of Mystra** - Bless grants an additional +1d4 to attack rolls and saving throws (+2d4 total), and an additional +2d4 to spell attack rolls.",
    "UNI_DarkUrge_Stealth_Expertise_Passive": "**The Shadow Itself** - Once per turn, when you kill an enemy, become Invisible for 2 turns.",
    "DevilsSight": "**Devil's Sight** - Can see normally in darkness, both magical and non-magical, up to a distance of 24m.",
    "MaskOfManyFaces": "**Mask of Many Faces** - Cast Disguise Self at will without expending a spell slot.",
    "MAG_Frost_GenerateFrostOnDamage_Gloves_Passive": "**Winter's Clutches** - Dealing Cold damage inflicts 2 turns of Encrusted with Frost (-3m movement speed; at 7 stacks, DC 12 Con save or take 2d8 Cold damage and become Frozen).",
    "MAG_Frost_GenerateFrostOnStatusApply_Hat_Passive": "**Coldbrim Hat** - Once per turn, any condition inflicted upon a target also applies 2 turns of Encrusted with Frost.",
    "MAG_Frost_IceSurfaceProneImmunity_Boots_Passive": "**Hoarfrost Stride** - Cannot slip on ice surfaces and immune to falling Prone on icy terrain.",
    "MAG_Frost_GenerateSurfaceOnColdDamage_Ring_Passive": "**Snowburst Ring** - Dealing Cold damage creates a 4.5m radius circle of ice surface centered on the target.",
    "MAG_ChargedLightning_Charge_OnSpellDamage_Passive": "**Lightning Charges (Spellsparkler)** - Dealing spell or cantrip damage grants 2 Lightning Charges (+1 bonus to Attack rolls and damage; at 5 charges, consume all to deal 1d8 bonus Lightning damage).",
    "MAG_ChargedLightning_Electrocute_Armor_Passive": "**Protecty Sparkswall** - Gain +1 AC and +1 to all Saving Throws while having Lightning Charges.",
    "MAG_Cold_IncreaseColdDamageOnCast_Passive": "**Heart of Ice (Mourning Frost)** - Dealing Cold damage deals an additional +1 Cold damage.",
    "MAG_Cold_ChilledOnSpellDamage_Passive": "**Insidious Cold (Mourning Frost)** - Dealing Cold damage with a spell has a chance to inflict Chilled (vulnerability to Cold, resistance to Fire).",
    "MAG_ArcaneEnchantment_Lesser_Passive": "**Arcane Enchantment** - Gain a +1 bonus to Spell Save DC and spell attack rolls.",
    "MAG_Legendary_Chromatic_Spellslot_Passive": "**Arcane Battery (Markoheshkir)** - The next spell cast does not consume a spell slot (Once per Long Rest).",
    "MAG_StrengthBonusToWeaponDamage_Passive": "**Titanstring Strength** - Deals additional damage equal to your Strength modifier.",
    "MAG_AdvantageOnReactionAttack_Passive": "**Reaction Advantage** - Gain Advantage on Opportunity Attacks.",
    "PolearmMaster_AttackOfOpportunity": "**Polearm Master: Opportunity Attack** - You can make an Opportunity Attack when a hostile creature enters your reach.",
    "MAG_ZOC_ForceConduit_Halberd_Passive": "**Skinburster** - Hitting with a melee weapon attack grants 2 turns of Force Conduit (-1 Physical damage taken per turn remaining).",
    "MAG_ZOC_ForceConduit_HeavyArmor_Passive": "**Rippling Force Mail** - Gain Force Conduit when hit by a melee weapon attack.",
    "MAG_ZOC_ForceConduitWhileSurounded_Boots_Passive": "**Force Conduit on Surround** - Gain Force Conduit when surrounded by two or more enemies.",
    "MAG_ZOC_AdvantageOnMeleeAttackWhileSurounded_Gloves_Passive": "**Daredevil Advantage** - Gain Advantage on melee weapon attack rolls when surrounded by enemies.",
    "MAG_ZOC_RampartAura_Amulet_Passive": "**Rampart Aura** - Fortifies defenses and grants Force Conduit.",
    "MAG_Critical_CriticalExecution_Passive": "**Killer's Sweetheart** - When you kill a creature, your next Attack Roll is guaranteed to be a Critical Hit (Once per Long Rest).",
    "MAG_Critical_CriticalSwiftness_Passive": "**Critical Swiftness** - Scoring a critical hit grants additional movement speed until the end of your turn.",
    "MAG_Frightened_Immunity_Passive": "**Bravery** - Immune to being Frightened.",
    "MAG_JumpBoost_Passive": "**Swiresy Leap** - Jump distance is increased by 1.5m.",
    "MAG_LC_Cyric_FearImmunity_Amulet_Passive": "**Courageous Heart** - Immune to Fear and Frightened effects.",
    "MAG_MagicalDurability_Passive": "**Magical Durability** - The wearer gains a +2 bonus to all Saving Throws.",
    "MAG_Sarevok_HornedHelmet_DeathbringerSight_Passive": "**Deathbringer Sight** - Can see in the dark up to 3m. Number needed to roll a Critical Hit reduced by 1. Immune to being Frightened.",
    "MAG_HomingWeapon_Passive": "**Returning Weapon** - When thrown, automatically returns to the wielder's hand.",
    "MAG_UndeadTurning_Weapon_Passive": "**Turning Undead** - Weapon hits on undead creatures have a chance to Turn them.",
    "Absorb_Elements_Passive": "**Absorb Elements** - Reaction: Take half damage from an incoming elemental attack (Acid, Cold, Fire, Lightning, Thunder) and deal an extra 1d6 damage of that type on your next melee attack.",
    "Absorb_Elements_Technical_Passive": "**Absorb Elements** - Elemental damage absorption reaction trigger.",
    "MAG_Interrupt_MAG_Interrupt_AbsorbElements_Resource_Passive": "**Absorb Elements Resource** - Manages reaction resource for elemental absorption.",
    "Background_Entertainer": "**Entertainer** - Grants Proficiency in Acrobatics and Performance skills.",
    "Overwhelm": "**Overwhelm** - The number needed to roll a Critical Hit while attacking is reduced by 1."
}

BASE_GAME_LOCA_HANDLES = {
    "h7335fb51g4da9g4257gb154g03949f63e18e": "Detect Thoughts",
    "h0f0fd40aga4f2g444eg8d1ag9ad1351a8515": "Focus your mind to read the thoughts of certain creatures while talking to them.",
    "h7302adc0g3508g4e39gb1fcg8486e3427ddf": "Web",
    "hdc6ddc78g6009g4b69ga59dg31a8043ccecc": "Cover an area in thick, sticky webbing that slows creatures within and possibly Entangles them.",
    "h50cad90fg8a5eg486cg85e3g4b0b969ceedc": "Charm Person (Subtle Domination)",
    "hbaa77d4dg08b2g41fbg9e12gcd106093fc73": "Phantasmal Force",
    "hebec5d12ga353g43bfg8296ge553f7f40a17": "Deal 1d6 Psychic damage each turn to a creature. The damage type changes to whatever type it took most recently.",
}

BASE_GAME_SPELLS = {
    "Projectile_Fly": "**Fly** (Level 3 Transmutation) - Grant a creature the ability to fly until a Long Rest (18m flying movement distance).",
    "Projectile_MAG_Barbarian_BrutalLeap": "**Brutal Leap** - Leap aggressively onto a target area, dealing Bludgeoning damage and potentially knocking creatures Prone.",
    "Rush_MAG_Barbarian_Armor_Trample": "**Trample** - Charge forward, knocking creatures Prone and dealing Bludgeoning damage.",
    "Shout_BootsOfSpeed": "**Click Heels** - Double movement speed and impose Disadvantage on enemy opportunity attacks for 1 turn (Bonus Action).",
    "Shout_Enlarge_Duergar": "**Enlarge** - Grow larger, dealing an extra 1d4 damage on weapon attacks and gaining Advantage on Strength checks and saves.",
    "Shout_MAG_ArmorOfAgathys_3": "**Armor of Agathys** (Level 3 Abjuration) - Gain 15 temporary hit points and deal 15 Cold damage to melee attackers.",
    "Shout_MAG_Harpers_HarmonizingRapier_Perfrom": "**Harmonize (Perform)** - Harmonize with your weapon, granting a +1 bonus to Performance.",
    "Shout_MAG_Harpers_SingingSword_Container": "**Sing / Shriek (Phalar Aluve)** - Sing buffs allies (+1d4 Attack rolls and saves); Shriek debuffs enemies (-1d4 saves, extra 1d4 Thunder damage taken).",
    "Shout_MAG_Monk_Restore_Ki_Lesser": "**Ki Restoration** - Harness spiritual energy to restore 2 Ki points (Once per Long Rest).",
    "Shout_MAG_PassWithoutTrace": "**Pass Without Trace** (Level 2 Abjuration) - Veil of shadows giving +10 bonus to Stealth checks for all nearby companions.",
    "Shout_MAG_PullingShout": "**Telekinetic Pull** - Pull nearby creatures or objects within 9m towards you.",
    "Shout_MAG_Restore_ChannelDivinity": "**Eternal Devotion** - Regain 1 expended Channel Divinity charge (Once per Short Rest).",
    "Shout_MAG_SpellSlotRestoration": "**Spell Slot Restoration** - Regain an expended Level 1, 2, or 3 spell slot (Once per Long Rest).",
    "Shout_UND_Invisibility_ShadowOfMenzoberranzan": "**Shrouded in Shadow** - Turn Invisible for 2 turns (Requires Concentration).",
    "Target_HideousLaughter": "**Tasha's Hideous Laughter** (Level 1 Enchantment) - Leave a creature Prone with uncontrollable laughter for up to 10 turns (DC Wis save).",
    "Target_MAG_Smite_Wrathful": "**Wrathful Smite** (Level 1 Evocation) - Deals weapon damage + 1d6 Psychic damage and potentially Frightens the target (Wisdom save).",
    "Target_MinorIllusion": "**Minor Illusion** (Cantrip) - Creates an illusion that distracts nearby creatures.",
    "Target_ViciousMockery": "**Vicious Mockery** (Cantrip) - Deals 1d4 Psychic damage and gives Disadvantage on target's next attack roll (Wisdom save).",
    "Teleportation_MAG_Revivify": "**Revivify** (Level 3 Necromancy) - Revive a fallen companion with 1 hit point.",
    "PP_Target_SubtleDomination": "**Subtle Domination** (Level 1 Enchantment) - Charm a humanoid creature (DC 13 Wisdom saving throw). While Charmed, the target cannot attack the caster and the caster has Advantage on Charisma checks against them (Duration: 10 turns, Recharge: Once per Long Rest).",
    "PP_Target_Web": "**Web** (Level 2 Conjuration) - Cast a 4m radius sticky web that slows creatures within and inflicts the Enwebbed condition on a failed Dexterity save (Duration: 10 turns, Recharge: Once per Long Rest).",
    "PP_Shout_DetectThoughts": "**Detect Thoughts** (Level 2 Divination) - Open your mind to read the thoughts of creatures during dialogue, gaining Advantage on dialogue insight checks (Duration: Until Long Rest, Recharge: Once per Long Rest).",
    "PP_Target_PhantasmalForce": "**Phantasmal Force** (Level 2 Illusion) - Deceive a creature into perceiving an illusion that deals 1d6 Psychic damage each turn for 10 turns, adapting to the damage type it took most recently (DC Int save, Recharge: Once per Short Rest).",
}

MOD_SPECIFIC_OVERRIDES = {
    # Custom Mod Spells
    "Target_OHF_SOF_Infused_Survival_Instinct": "Infuse a creature with psionic force. If it reaches 0 hit points, it heals 3d10 HP instead of falling Unconscious (Recharge: Once per combat).",
    "Target_OHF_SOF_AssassinStep": "Teleport from shadow to shadow up to 18m as a Bonus Action and gain Advantage on your next melee attack (Recharge: Once per combat).",
    "Target_OHF_SOF_IceStorm": "Level 4 Evocation - Deals 2d8 Bludgeoning + 4d6 Cold damage in a 6m radius cylinder; leaves an icy surface (Recharge: Once per Short Rest).",
    "Target_OHF_SOF_SleetStorm": "Level 3 Conjuration - Summons an icy storm (9m radius) that creates a slippery ice surface, douses fires, and disrupts concentration (Recharge: Once per Short Rest).",
    "Target_OHF_SOF_T1_Target_Slash_New": "Ulrick's Lacerate - Slash a target dealing weapon damage and inflict Bleeding for 4 turns on a failed Con saving throw (Recharge: Once per turn).",
    "Target_OHF_SOF_T2_Target_Slash_New": "Ulrick's Infused Lacerate - Slash a target dealing weapon damage and inflict Bleeding for 4 turns on a failed Con saving throw (DC Maneuver + 2).",
    "Target_OHF_SOF_T1_CreateWater": "Create Water - Douse fires and create a water surface in a 4m area, making creatures Wet (Vulnerable to Cold and Lightning) [Cooldown: Once per Short Rest].",
    "Target_OHF_SOF_T2_CreateWater": "Infused Create Water - Douse fires and create a water surface in a 6m area, making creatures Wet [Cooldown: Once per Combat].",
    "Target_OHF_SOF_T1_MAG_Critical_Critical_Combo": "Ulrick's Advantage - Scoring a critical hit grants Advantage on your next melee weapon attack roll.",
    "Zone_OHF_SOF_T1_Cleave": "Ulrick's Cleave - Swing your weapon in a cone, dealing weapon damage to up to 3 targets (Recharge: Once per turn).",
    "Zone_OHF_SOF_T2_Cleave": "Ulrick's Infused Cleave - Enhanced wide cone cleave dealing full weapon damage to all enemies in range.",
    "Rush_OHF_SOF_T1_SpringAttack": "Ulrick's Rush Attack - Charge forward up to 9m, hitting targets for weapon damage and knocking them Off-Balanced on failed Str save (Recharge: Once per combat).",
    "Rush_OHF_SOF_T2_SpringAttack": "Ulrick's Infused Rush Attack - Charge forward, dealing weapon damage + max(Dex, Str) and knocking enemies Off-Balanced (DC Maneuver + 2).",
    "Shout_OHF_SOF_T1_FoeSlayer": "Ulrick's Foeslayer - The number you need to roll a Critical Hit is reduced by 1 (stacks). Gain a +2 bonus to melee weapon attacks (Recharge: Once per Short Rest).",
    "Shout_OHF_SOF_T2_FoeSlayer": "Infused Ulrick's Foeslayer - The number you need to roll a Critical Hit is reduced by 2 (stacks). Gain a +4 bonus to melee weapon attacks.",
    "Shout_OHF_SOF_T2_Channel_Divinity": "Infused Eternal Devotion - Regain 1 expended Channel Divinity charge (Recharge: Once per Short Rest).",
    "Shout_OHF_SOF_T2_Pulling_Shout": "Telekinetic Pull - Pull all nearby enemies within 9m towards your position.",
    "Shout_OHF_SOF_T1_Immovable": "Korrin's Stone Footing - Anchor yourself into the ground, gaining immunity to forced movement and Prone for 3 turns (Recharge: Once per combat).",
    # Pact and Power: Warlock Equipment Spells
    "PP_Target_WeaponAction_BloodPrice": "Plunge the blade into a creature, dealing main weapon melee damage + Proficiency Bonus + 1d6 Necrotic damage, and regaining hit points equal to half the total damage dealt (Cantrip Weapon Action).",
    "PP_Target_ChainsOfSubmission": "Ethereal chains bind a humanoid target for 3 turns (Wisdom save vs Spell DC). Target is held immobile and incapacitated (unable to move, act, or react). Attacks made from within 3m are guaranteed Critical Hits (Level 2 Enchantment, Recharge: Once per Long Rest).",
    "PP_Target_WeaponAction_Pactbreaker_Curse": "Strike a creature, dealing main weapon melee damage + Proficiency Bonus + 1d6 Psychic damage. Target must succeed a Wisdom saving throw vs Spell DC or suffer a -1 penalty to Attack Rolls for 2 turns (Cantrip Weapon Action).",
    "PP_Shout_EchoesOfSelf": "Create 3 defensive echoes for 10 turns, granting a +2 bonus to Armour Class and Resistance to Force damage. Whenever you evade an attack, one echo disappears (Level 2 Illusion, Recharge: Once per Long Rest).",
    "PP_Shout_WarlockSpellRestoration": "Tap into patron power to immediately restore 1 expended Warlock Spell Slot of Level 1–5 (Cantrip, Recharge: Once per Long Rest).",
    "PP_Shout_CloakOfFlies": "Surround yourself with a 2m aura of buzzing flies for 10 turns. Grants Advantage on Intimidation checks, but Disadvantage on all other Charisma checks. Any creature starting its turn in the aura takes Poison damage equal to your Charisma Modifier (Cantrip, Recharge: Once per Long Rest).",
    "PP_Shout_VolcanicBlast": "For 3 turns, gain Resistance to Fire damage, and fire spells deal an additional 2d6 Fire damage. Also triggers a fiery shockwave igniting flammable surfaces and dealing 2d6 Fire damage (Cantrip, Recharge: Once per Long Rest).",
    "PP_Shout_DemonicSurge": "Channel demonic fury for 3 turns, gaining temporary hit points equal to your Warlock Level + Charisma Modifier, and causing all weapon and spell attacks to deal an additional 1d6 Psychic damage (Cantrip, Recharge: Once per Short Rest).",
    "PP_Target_VoidStep_FollowUp": "Teleport next to any creature within 9m. Afterwards, gain Voidwalker's Resilience for 3 turns, adding +1d4 Force damage to weapon attacks and regaining 1d6 hit points (Conjuration follow-up).",
    # Custom Mod Passives
    "OHF_SOF_T1_Monk_Freedom": "Thalassa's Freedom - Immune to being Enwebbed and immune to slipping on ice surfaces (Night Walkers effect).",
    "OHF_SOF_T1_Monk_Mobility": "Thalassa's Mobility - Increases Movement Speed by 3m and Acrobatics by +2.",
    "OHF_SOF_T2_Monk_Spiteful_Thunder": "(Set Bonus) Thalassa's Infused Spiteful Thunder - When you inflict Reverberation or Thunder damage, deal an additional 1d4 Thunder damage and knock targets back 3m.",
    "OHF_SOF_T1_ThrowingDamage": "Jàegah's Pitcher - Deals an additional 1d4 damage on Throw attacks.",
    "OHF_SOF_T1_Inflict_Bleeding": "Jàegah's Scissors - Attacks with this weapon have a chance to inflict Bleeding on hit.",
    "OHF_SOF_T2_Inflict_Bleeding": "Jàegah's Infused Scissors - Attacks with this weapon have a high chance to inflict Bleeding (100% on Critical Hit).",
    "OHF_SOF_T1_Warlock_SetBonus": "(Set Bonus) Thalindra's Beguiling Personality - Your cantrips deal additional damage equal to your Charisma Modifier.",
    "OHF_SOF_T1_Warlock_FastMovement": "Thalindra's Repositioning - Increases Movement Speed by 3m and Jump Distance by 1.5m.",
    "OHF_SOF_AuraOfMurder": "(Set Bonus) Aura of Murder - Hostile creatures within 2m become Vulnerable to Piercing damage, unless they are already resistant or immune to it.",
    "OHF_SOF_T2_FirstBlood_Passive": "Lunarshade's Infused First Blood - Deals an additional 1d8 damage to targets that still have all their hit points.",
    "OHF_SOF_T2_FastMovement_Passive": "Lunarshade's Infused Mobility - Increases Movement Speed by 6m and Acrobatics by +4.",
    "OHF_SOF_T1_Paladin_Craterous_Wounds": "Ulrick's Craterous Wounds - Whenever you score a Critical Hit, deal an additional 1d6 Force damage.",
    "OHF_SOF_T2_Paladin_Craterous_Wounds": "Ulrick's Infused Craterous Wounds - Whenever you score a Critical Hit, deal an additional 1d10 Force damage.",
    "OHF_SOF_T1_Fighter_ForceConduit_Attack": "Korrin's Relentless Force - Melee weapon hits grant 2 turns of Force Conduit (-1 Physical damage taken per turn remaining).",
    "OHF_SOF_T1_Fighter_ForceConduit_Turn": "Korrin's Conduit - Shrouds the wearer with Force Conduit at the start of their turn in combat.",
    "OHF_SOF_Infused_UND_SocietyOfBrilliance_PullingRing_Passive": "Infused Saviour's Allure - Pulls surrounding enemies within 9m towards the caster when casting a spell.",
    # Pact and Power: Warlock Equipment Passives
    "PP_Lifebound_Aura_Passive": "A shimmering aura envelops your familiar, increasing its maximum hit points by an amount equal to your Warlock Level (Toggled).",
    "PP_Packkeeper_Aura_Text_Passive": "Emanate an aura in a 3m radius. Enemies within the aura suffer a 1d4 penalty to Attack Rolls and Saving Throws, and take 1d4 Necrotic damage if they start their turn within it (Toggled).",
    "PP_Shadowfell_Infusion_Passive": "When casting Arms of Hadar, it deals an additional 1d4 Necrotic damage.",
    "PP_BloodPact_Enhancement_Passive": "While your Pact Weapon or Hexed Weapon is active, melee weapon attacks deal an additional 1d4 Necrotic damage (Once per turn).",
    "PP_WhispersOfVoid_Passive": "If you have Pact of the Tome, your spells deal an additional 1d4 Necrotic damage on hit (Toggled).",
    "PP_FortunateFumble_Passive": "Gain a +1 bonus to Ability Checks and Saving Throws.",
    "PP_PactEmpoweredAim_Passive": "Gain a +1 bonus to Spell Attack Rolls and Spell Save DC.",
    "PP_TormentorInsight_Passive": "Gain a +1d4 bonus to Insight Checks.",
    "PP_AscendedPact_Text_Passive": "Grants patron enhancements based on chosen pact:<br>• **Pact of the Blade**: Weapon attacks deal +1d4 Necrotic damage (+2d4 with Deepened Pact).<br>• **Pact of the Chain**: Familiars within 18m gain bonus HP equal to Warlock Level + Charisma Modifier and +1d4 to Saving Throws (familiar deals +1d6 Necrotic with Deepened Pact).<br>• **Pact of the Tome**: Spells have a 10% chance (20% with Deepened Pact) to inflict Pact Siphon for 3 turns, dealing 1d6 Necrotic per turn (2d6 with Deepened Pact) and healing the warlock for damage dealt.",
    "PP_BindingThreads_Passive": "Gain a +1 bonus to Attack Rolls and Spell Save DC.",
    "PP_VoidStep_Passive": "After casting Hunger of Hadar, unlock Void Step, allowing you to teleport next to a creature within 9m and gain Voidwalker's Resilience (+1d4 Force damage, 1d6 HP regen).",
    "PP_SoulfireRetaliation_Passive": "Reaction: When struck by a melee attack, deal 2d6 Necrotic damage to the attacker. Attacker must succeed a DC 15 Dexterity saving throw or take 1d4 Necrotic damage at the start of each turn for 3 turns (Once per Long Rest).",
    "PP_CloakOfFlies_Passive": "Unlocks the Cloak of Flies cantrip (2m aura dealing Charisma Modifier Poison damage per turn, Advantage on Intimidation, Disadvantage on other Charisma checks).",
    "PP_VolcanicBlase_Passive": "For 3 turns, gain Resistance to Fire damage, and fire spells deal an additional 2d6 Fire damage.",
    "PP_Leechstone_Passive": "When taking spell damage while below 50% hit points, gain temporary hit points equal to half your Warlock Level + Charisma Modifier (Once per Long Rest).",
    "PP_Hellish_Resistance": "Gain Resistance to Fire and Necrotic damage.",
    "PP_SurgeOfBrimstone": "At the start of combat, the first spell cast that deals Fire or Necrotic damage deals an additional 2d4 damage of that type.",
    "PP_SearingRebuke_Passive": "Reaction: When struck by an enemy, cast a 3rd-level Hellish Rebuke dealing 4d10 Fire damage (Once per Long Rest).",
    "PP_EverlastingPact_Text_Passive": "Grants unique benefits based on chosen pact:<br>• **Pact of the Blade**: Weapon attacks deal an extra 2d6 Psychic damage (Once per turn) and wielder gains Resistance to Psychic damage.<br>• **Pact of the Chain**: Familiars within 18m gain +2 Armour Class, +2 Attack Rolls, and temporary hit points equal to twice your Warlock Level.<br>• **Pact of the Tome**: Gain +2 to Spell Attack Rolls and Spell Save DC, and cantrips deal an additional 1d8 Psychic damage (Once per turn).",
    "PP_FeastOnTheWounded_Passive": "When hitting a creature below maximum hit points, deal an additional 1d8 Necrotic damage (Once per turn).",
    "PP_Focused_Eldritch_Force_Passive": "Eldritch Blast attacks have Advantage and deal an additional 1d8 Force damage (Once per attack).",
    "PP_Soulrender_Passive": "When killing a creature with a Necrotic, Psychic, or Radiant spell, gain an additional Action this turn (Once per Short Rest).",
    "PP_Twilights_Edge": "When casting a cantrip, make a weapon attack as a Bonus Action (Toggled, Once per Short Rest).",
    "PP_Desperate_Renewal_Passive": "When hit points drop below 40%, unleash a wave of necrotic energy in a 5m radius dealing 2d8 Necrotic damage to enemies (allies take half) (Once per Short Rest).",
    "PP_Devour_Essence_Passive": "After killing 3 enemies, restore an expended Warlock Spell Slot.",
    "PP_Insatiable_Passive": "At the start of combat, take 2d10 Necrotic damage but gain Armour Class equal to your Charisma Modifier (maximum +5) until combat ends.",
    "PP_WhisperSilk_Passive": "When damaging a creature afflicted by Hex, the critical hit roll threshold against that creature is reduced by 1 (Stacks).",
}


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
    mod_id = mod_metadata.get("id")
    slug = mod_metadata.get("name_id")

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


def update_library_markdown(library_path, mod_name, slug, category, summary, features_count):
    """Ensure mods/library.md contains categorized sections and update the mod's entry."""
    categories = [
        "Gear",
        "Spells",
        "Classes & Subclasses",
        "Progression & Rules",
        "Utilities & Cheats",
    ]

    if not os.path.exists(library_path):
        content = "# Baldur's Gate 3 Mod Library\n\nThis library catalogs documented Baldur's Gate 3 mods, their in-game features, and specifications for build crafting.\n\n"
        for cat in categories:
            content += f"## {cat}\n\n| Mod Name | Description | Features Documented | Spec Link |\n| :--- | :--- | :--- | :--- |\n\n"
    else:
        with open(library_path, "r", encoding="utf-8") as f:
            content = f.read()

    # Ensure all category headers exist
    for cat in categories:
        if f"## {cat}" not in content:
            content += f"\n## {cat}\n\n| Mod Name | Description | Features Documented | Spec Link |\n| :--- | :--- | :--- | :--- |\n"

    # Remove existing entry if present across any category to prevent duplicates
    entry_pattern = rf"\| \*\*\[?{re.escape(mod_name)}(?:\]\([^)]*\))?\]?\*\*.*?\n"
    content = re.sub(entry_pattern, "", content)

    # Build new row
    clean_summary = summary.replace("|", "\\|").replace("\n", " ").strip()
    new_row = f"| **[{mod_name}]({slug}/README.md)** | {clean_summary} | {features_count} implemented | [View Spec]({slug}/README.md) |\n"

    # Insert under target category table
    cat_header = f"## {category}"
    if cat_header in content:
        header_idx = content.find(cat_header)
        next_header_idx = content.find("\n## ", header_idx + len(cat_header))
        if next_header_idx == -1:
            next_header_idx = len(content)

        section = content[header_idx:next_header_idx]
        lines = section.splitlines(keepends=True)
        insert_idx = len(lines)
        for i, l in enumerate(lines):
            if l.startswith("| :---"):
                insert_idx = i + 1
            elif l.startswith("|") and insert_idx <= i + 1:
                insert_idx = i + 1

        lines.insert(insert_idx, new_row)
        content = content[:header_idx] + "".join(lines) + content[next_header_idx:]

    with open(library_path, "w", encoding="utf-8") as f:
        f.write(content)


# ----------------------------------------------------------------------
# Main Execution Pipeline
# ----------------------------------------------------------------------
def process_mod(query, output_dir=None, write_spec=False, update_library=False):
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("MODIO_API_KEY environment variable is not set. Please export MODIO_API_KEY.")

    # 1. Query mod.io
    mod_meta = query_modio(query, api_key)
    mod_name = mod_meta["name"]
    slug = mod_meta["name_id"]

    if not output_dir:
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        output_dir = os.path.join(workspace_root, "mods", slug)

    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # 2. Download mod
    archive_bytes = download_mod_file(mod_meta, api_key)

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

    # 7. Update mods/library.md if requested
    if update_library or write_spec:
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        lib_path = os.path.join(workspace_root, "mods", "library.md")
        update_library_markdown(lib_path, mod_name, slug, category, mod_meta.get("summary", ""), len(features))

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
    parser = argparse.ArgumentParser(description="Fetch, unpack, and parse BG3 mods from mod.io.")
    parser.add_argument("--query", "-q", required=True, help="Mod name, slug, URL, or ID")
    parser.add_argument("--output-dir", "-o", help="Directory where mod spec and data will be saved")
    parser.add_argument("--write-spec", action="store_true", help="Write README.md directly to output directory")
    parser.add_argument("--update-library", action="store_true", help="Update mods/library.md with documented mod")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")

    args = parser.parse_args()

    try:
        res = process_mod(
            args.query,
            output_dir=args.output_dir,
            write_spec=args.write_spec,
            update_library=args.update_library,
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Successfully processed mod '{res['mod_name']}' ({res['slug']})")
            print(f"Category: {res['category']}")
            print(f"Features documented: {res['features_count']}")
            print(f"Directory: {res['output_dir']}")
    except Exception as e:
        print(f"Error processing mod '{args.query}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
