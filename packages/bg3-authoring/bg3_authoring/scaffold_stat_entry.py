#!/usr/bin/env python3
"""
scaffold_stat_entry.py - Scaffolds Larian stat entries and generates localization handles.

Generates 100% engine-compliant stat boilerplate for Weapons, Armor, Objects,
Passives, Statuses, and Spells, while allocating valid localization handles
and registering them into Localization/English/<ModName>.xml.
"""

import argparse
import json
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import MY_MODS_DIR, resolve_mod_dir
from bg3_core.larian_parsers import (
    generate_larian_handle,
    split_larian_items,
    update_localization_xml,
)

# Mapping of entry types to their file and default schema
TYPE_CONFIG = {
    "weapon": {
        "file": "Weapon.txt",
        "type_header": 'type "Weapon"',
        "default_using": "_BaseWeapon",
        "defaults": {
            "Damage Type": "Slashing",
            "Damage": "1d8",
            "ValueLevel": "1",
            "Rarity": "Rare",
            "DefaultBoosts": "WeaponEnchantment(1)",
        },
    },
    "armor": {
        "file": "Armor.txt",
        "type_header": 'type "Armor"',
        "default_using": "_Armor",
        "defaults": {
            "Slot": "Breast",
            "ArmorClass": "15",
            "ArmorType": "Leather",
            "Rarity": "Rare",
        },
    },
    "amulet": {
        "file": "Armor.txt",
        "type_header": 'type "Armor"',
        "default_using": "_Armor",
        "defaults": {
            "Slot": "Amulet",
            "Rarity": "Rare",
        },
    },
    "ring": {
        "file": "Armor.txt",
        "type_header": 'type "Armor"',
        "default_using": "_Armor",
        "defaults": {
            "Slot": "Ring",
            "Rarity": "Rare",
        },
    },
    "object": {
        "file": "Object.txt",
        "type_header": 'type "Object"',
        "default_using": "_Object",
        "defaults": {
            "Rarity": "Common",
            "Weight": "0.5",
        },
    },
    "passivedata": {
        "file": "Passive.txt",
        "type_header": 'type "PassiveData"',
        "default_using": None,
        "defaults": {
            "Icon": "PassiveFeature_Generic",
            "Properties": "Highlighted",
        },
    },
    "status_boost": {
        "file": "Status_BOOST.txt",
        "type_header": 'type "StatusData"',
        "default_using": None,
        "defaults": {
            "StatusType": "BOOST",
            "Icon": "Generic_Boost",
        },
    },
    "spell_target": {
        "file": "Spell_Target.txt",
        "type_header": 'type "SpellData"',
        "default_using": None,
        "defaults": {
            "SpellType": "Target",
            "Level": "3",
            "SpellSchool": "Evocation",
            "TargetRadius": "18",
        },
    },
    "spell_shout": {
        "file": "Spell_Shout.txt",
        "type_header": 'type "SpellData"',
        "default_using": None,
        "defaults": {
            "SpellType": "Shout",
            "Level": "3",
            "SpellSchool": "Abjuration",
        },
    },
    "spell_projectile": {
        "file": "Spell_Projectile.txt",
        "type_header": 'type "SpellData"',
        "default_using": None,
        "defaults": {
            "SpellType": "Projectile",
            "Level": "3",
            "SpellSchool": "Evocation",
            "TargetRadius": "18",
        },
    },
    "spell_zone": {
        "file": "Spell_Zone.txt",
        "type_header": 'type "SpellData"',
        "default_using": None,
        "defaults": {
            "SpellType": "Zone",
            "Level": "3",
            "SpellSchool": "Evocation",
        },
    },
    "spell_teleport": {
        "file": "Spell_Teleport.txt",
        "type_header": 'type "SpellData"',
        "default_using": None,
        "defaults": {
            "SpellType": "Teleport",
            "Level": "2",
            "SpellSchool": "Conjuration",
            "TargetRadius": "18",
        },
    },
    "spell_rush": {
        "file": "Spell_Rush.txt",
        "type_header": 'type "SpellData"',
        "default_using": None,
        "defaults": {
            "SpellType": "Rush",
            "Level": "1",
            "SpellSchool": "Transmutation",
            "TargetRadius": "9",
        },
    },
    "spell_path": {
        "file": "Spell_Path.txt",
        "type_header": 'type "SpellData"',
        "default_using": None,
        "defaults": {
            "SpellType": "Path",
            "Level": "1",
            "SpellSchool": "Conjuration",
            "TargetRadius": "18",
        },
    },
    "interrupt": {
        "file": "Interrupt.txt",
        "type_header": 'type "InterruptData"',
        "default_using": None,
        "defaults": {
            "InterruptType": "Spell",
            "Conditions": "Self()",
        },
    },
    "equipment": {
        "file": "Equipment.txt",
        "type_header": 'type "Equipment"',
        "default_using": None,
        "defaults": {
            "InitialLoadout": "Yes",
        },
    },
    "character": {
        "file": "Character.txt",
        "type_header": 'type "Character"',
        "default_using": "_Hero",
        "defaults": {
            "StrengthMax": "30",
            "DexterityMax": "30",
            "ConstitutionMax": "30",
            "IntelligenceMax": "30",
            "WisdomMax": "30",
            "CharismaMax": "30",
        },
    },
    "status_effect": {
        "file": "Status_EFFECT.txt",
        "type_header": 'type "StatusData"',
        "default_using": None,
        "defaults": {
            "StatusType": "EFFECT",
            "Icon": "Generic_Effect",
        },
    },
    "status_polymorph": {
        "file": "Status_POLYMORPH.txt",
        "type_header": 'type "StatusData"',
        "default_using": None,
        "defaults": {
            "StatusType": "POLYMORPH",
            "Icon": "Generic_Polymorph",
        },
    },
    "status_heal": {
        "file": "Status_HEAL.txt",
        "type_header": 'type "StatusData"',
        "default_using": None,
        "defaults": {
            "StatusType": "HEAL",
            "Icon": "Generic_Heal",
        },
    },
    "status_downed": {
        "file": "Status_DOWNED.txt",
        "type_header": 'type "StatusData"',
        "default_using": None,
        "defaults": {
            "StatusType": "DOWNED",
            "Icon": "Generic_Downed",
        },
    },
    "status_invisible": {
        "file": "Status_INVISIBLE.txt",
        "type_header": 'type "StatusData"',
        "default_using": None,
        "defaults": {
            "StatusType": "INVISIBLE",
            "Icon": "Generic_Invisible",
        },
    },
}


def resolve_mod_directories(mod_name_or_path: str, workspace_root: Path) -> tuple[Path, Path, Path, str]:
    """
    Resolves:
    - mod root
    - stats directory: Public/<ModFolder>/Stats/Generated/Data
    - localization xml file: Localization/English/<ModName>.xml
    - mod name
    """
    candidate = resolve_mod_dir(mod_name_or_path, prefer_my_mods=True)
    if candidate is None or not candidate.is_dir():
        raise FileNotFoundError(f"Mod directory not found: '{mod_name_or_path}'")

    public_dir = candidate / "Public"
    if not public_dir.is_dir():
        raise FileNotFoundError(f"Missing 'Public/' in mod: '{candidate}'")

    subdirs = [d for d in public_dir.iterdir() if d.is_dir() and d.name != "Shared"]
    if not subdirs:
        raise FileNotFoundError(f"No mod folder found under '{public_dir}'")

    stats_dir = subdirs[0] / "Stats" / "Generated" / "Data"
    loc_dir = candidate / "Localization" / "English"

    loc_file = None
    if loc_dir.is_dir():
        xmls = list(loc_dir.glob("*.xml"))
        if xmls:
            loc_file = xmls[0]

    if not loc_file:
        loc_file = loc_dir / f"{candidate.name}.xml"

    return candidate, stats_dir, loc_file, candidate.name


def scaffold_entry(
    mod_name_or_path: str,
    entry_type: str,
    entry_name: str,
    display_name: str | None = None,
    description: str | None = None,
    using: str | None = None,
    props: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict:
    workspace_root = Path(__file__).resolve().parents[2]
    type_key = entry_type.strip().lower()
    if type_key not in TYPE_CONFIG:
        raise ValueError(
            f"Unsupported entry type '{entry_type}'. Supported: {', '.join(TYPE_CONFIG.keys())}"
        )

    config = TYPE_CONFIG[type_key]
    mod_dir, stats_dir, loc_file, resolved_name = resolve_mod_directories(mod_name_or_path, workspace_root)
    stat_file = stats_dir / config["file"]

    # Check for duplicate
    if stat_file.exists():
        existing_content = stat_file.read_text(encoding="utf-8", errors="replace")
        if re.search(rf'new\s+entry\s+"{re.escape(entry_name)}"', existing_content):
            raise ValueError(f"Entry '{entry_name}' already exists in {stat_file.name}")
    else:
        existing_content = ""

    # Generate handles for DisplayName and Description
    loc_records = []
    h_display = None
    h_desc = None

    if display_name:
        h_display = generate_larian_handle()
        loc_records.append((h_display, display_name))

    if description:
        h_desc = generate_larian_handle()
        loc_records.append((h_desc, description))

    # Build stat lines
    lines = [f'new entry "{entry_name}"', config["type_header"]]

    chosen_using = using if using is not None else config["default_using"]
    if chosen_using:
        lines.append(f'using "{chosen_using}"')

    # Add display name and description handles
    if h_display:
        lines.append(f'data "DisplayName" "{h_display};1"')
    if h_desc:
        lines.append(f'data "Description" "{h_desc};1"')

    # Add default properties
    for k, v in config["defaults"].items():
        if props and k in props:
            continue
        lines.append(f'data "{k}" "{v}"')

    # Add custom extra props
    if props:
        for k, v in props.items():
            lines.append(f'data "{k}" "{v}"')

    entry_block = "\n".join(lines) + "\n"

    if not dry_run:
        # Update XML
        if loc_records:
            update_localization_xml(loc_file, loc_records, dry_run=False)

        # Update stats file
        stats_dir.mkdir(parents=True, exist_ok=True)
        new_stat_content = existing_content.rstrip()
        if new_stat_content:
            new_stat_content += "\n\n"
        new_stat_content += entry_block
        stat_file.write_text(new_stat_content, encoding="utf-8")

    return {
        "status": "created",
        "mod": resolved_name,
        "entry_name": entry_name,
        "type": entry_type,
        "stat_file": str(stat_file),
        "localization_file": str(loc_file),
        "display_name": display_name,
        "display_name_handle": f"{h_display};1" if h_display else None,
        "description": description,
        "description_handle": f"{h_desc};1" if h_desc else None,
        "raw_entry": entry_block.strip(),
        "dry_run": dry_run,
    }


def parse_props(props_str: str | None) -> dict[str, str]:
    if not props_str:
        return {}
    res = {}
    for item in split_larian_items(props_str, separators=(",",)):
        if "=" in item:
            k, v = item.split("=", 1)
            res[k.strip()] = v.strip()
    return res


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold Larian stat entries with automatic localization handle allocation."
    )
    parser.add_argument("--mod", required=True, help="Mod name/slug in my_mods/ or directory path.")
    parser.add_argument(
        "--type",
        required=True,
        help=f"Entry type ({', '.join(TYPE_CONFIG.keys())}).",
    )
    parser.add_argument("--name", required=True, help="Unique identifier for the stat entry.")
    parser.add_argument("--display-name", help="In-game display name for localization.")
    parser.add_argument("--description", help="In-game description for localization.")
    parser.add_argument("--using", help="Base stat entry to inherit from (e.g. _BaseWeapon).")
    parser.add_argument(
        "--props",
        help="Comma-separated custom properties (e.g. 'Rarity=Legendary,Boosts=AC(2)').",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview entry without writing.")
    parser.add_argument("--json", action="store_true", help="Output JSON payload.")

    args = parser.parse_args()

    try:
        custom_props = parse_props(args.props)
        result = scaffold_entry(
            mod_name_or_path=args.mod,
            entry_type=args.type,
            entry_name=args.name,
            display_name=args.display_name,
            description=args.description,
            using=args.using,
            props=custom_props,
            dry_run=args.dry_run,
        )

        color = ConsoleColor(stream=sys.stdout)
        err_color = ConsoleColor(stream=sys.stderr)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            dry_str = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status_tag = color.green("[✓]")
            print(f"{status_tag} Successfully scaffolded '{args.name}' ({args.type}){dry_str}:")
            print(f"    Stat file: {result['stat_file']}")
            if result["display_name_handle"]:
                print(f"    DisplayName Handle: {result['display_name_handle']}")
            if result["description_handle"]:
                print(f"    Description Handle: {result['description_handle']}")
            print("\nGenerated Entry:")
            print(result["raw_entry"])
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
