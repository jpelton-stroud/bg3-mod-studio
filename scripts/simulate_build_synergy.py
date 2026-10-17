#!/usr/bin/env python3
"""
simulate_build_synergy.py - Theorycrafting simulator for Level 20 character builds.

Computes Level 20 Hit Points, Spell Slots, Resource Pools, Armor Class,
effective Spell Save DC ceilings, and Turn 1 Damage Per Round (DPR) sequences
factoring in cataloged mod equipment and multi-class synergies.
"""

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib.cli_common import ConsoleColor, ExitCode
from scripts.lib.env_paths import get_cache_dir

# Caster classification for multiclass spell slot calculation
CASTER_WEIGHTS = {
    "bard": 1.0,
    "cleric": 1.0,
    "druid": 1.0,
    "sorcerer": 1.0,
    "wizard": 1.0,
    "paladin": 0.5,
    "ranger": 0.5,
    "fighter": 0.0,
    "barbarian": 0.0,
    "monk": 0.0,
    "rogue": 0.0,
    "warlock": 0.0,  # Handled separately as Pact Magic
}

PRIMARY_CASTING_STAT = {
    "wizard": "Int",
    "cleric": "Wis",
    "druid": "Wis",
    "bard": "Cha",
    "sorcerer": "Cha",
    "warlock": "Cha",
    "paladin": "Cha",
    "ranger": "Wis",
    "monk": "Wis",
    "barbarian": "Str",
    "fighter": "Str",
    "rogue": "Dex",
}

# 5e Multiclass spell slots table (levels 1-20, Level 13-20 extrapolated per UnlockLevelCurve)
MULTICLASS_SPELL_SLOTS = {
    1: [2, 0, 0, 0, 0, 0, 0, 0, 0],
    2: [3, 0, 0, 0, 0, 0, 0, 0, 0],
    3: [4, 2, 0, 0, 0, 0, 0, 0, 0],
    4: [4, 3, 0, 0, 0, 0, 0, 0, 0],
    5: [4, 3, 2, 0, 0, 0, 0, 0, 0],
    6: [4, 3, 3, 0, 0, 0, 0, 0, 0],
    7: [4, 3, 3, 1, 0, 0, 0, 0, 0],
    8: [4, 3, 3, 2, 0, 0, 0, 0, 0],
    9: [4, 3, 3, 3, 1, 0, 0, 0, 0],
    10: [4, 3, 3, 3, 2, 0, 0, 0, 0],
    11: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    12: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    13: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    14: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
    18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
    19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
    20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
}


def calculate_proficiency(total_level: int) -> int:
    if total_level >= 17:
        return 6
    elif total_level >= 13:
        return 5
    elif total_level >= 9:
        return 4
    elif total_level >= 5:
        return 3
    return 2


def parse_ability_modifier(score: int) -> int:
    return math.floor((score - 10) / 2)


def calculate_pact_slots(warlock_level: int) -> tuple[int, int]:
    """Returns (slot_count, slot_level)."""
    if warlock_level <= 0:
        return (0, 0)
    if warlock_level == 1:
        return (1, 1)
    if warlock_level == 2:
        return (2, 1)
    if warlock_level in (3, 4):
        return (2, 2)
    if warlock_level in (5, 6):
        return (2, 3)
    if warlock_level in (7, 8):
        return (2, 4)
    if warlock_level in (9, 10):
        return (2, 5)
    if warlock_level < 17:
        return (3, 5)
    return (4, 5)


def parse_boost_effects(boost_str: str) -> dict:
    effects = {
        "dc": 0,
        "ac": 0,
        "attack_bonus": 0,
        "damage_bonus": 0,
        "crit_threshold": 0,
        "stats": {},
    }
    for part in boost_str.split(";"):
        part = part.strip()
        m_dc = re.search(r'SpellSaveDC\((\d+)\)', part, re.IGNORECASE)
        if m_dc:
            effects["dc"] += int(m_dc.group(1))

        m_ac = re.search(r'AC\((\d+)\)', part, re.IGNORECASE)
        if m_ac:
            effects["ac"] += int(m_ac.group(1))

        m_att = re.search(r'RollBonus\(Attack,\s*(\d+)', part, re.IGNORECASE)
        if m_att:
            effects["attack_bonus"] += int(m_att.group(1))

        m_dmg = re.search(r'DamageBonus\((\d+)\)', part, re.IGNORECASE)
        if m_dmg:
            effects["damage_bonus"] += int(m_dmg.group(1))

        m_crit = re.search(r'ReduceCriticalThreshold\((\d+)\)', part, re.IGNORECASE)
        if m_crit:
            effects["crit_threshold"] += int(m_crit.group(1))

        m_ovr = re.search(r'AbilityOverrideMinimum\((\w+),\s*(\d+)', part, re.IGNORECASE)
        if m_ovr:
            stat_name = m_ovr.group(1)[:3].capitalize()
            effects["stats"][stat_name] = max(effects["stats"].get(stat_name, 0), int(m_ovr.group(2)))

    return effects


def load_gear_boosts(gear_items: list[str], _workspace_root: Path) -> tuple[dict, list[dict]]:
    cache_file = get_cache_dir() / "mod_database.json"
    gear_data = []
    combined_effects = {
        "dc": 0,
        "ac": 0,
        "attack_bonus": 0,
        "damage_bonus": 0,
        "crit_threshold": 0,
        "stats": {},
    }

    if not cache_file.is_file() or not gear_items:
        return combined_effects, gear_data

    try:
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
        entries_by_id = {e["id"].lower(): e for e in cache.get("entries", [])}
        entries_by_name = {e["display_name"].lower(): e for e in cache.get("entries", [])}

        for item in gear_items:
            item_clean = item.strip().lower()
            matched = entries_by_id.get(item_clean) or entries_by_name.get(item_clean)
            if matched:
                gear_data.append(matched)
                boosts = matched.get("boosts", "")
                eff = parse_boost_effects(boosts)
                combined_effects["dc"] += eff["dc"]
                combined_effects["ac"] += eff["ac"]
                combined_effects["attack_bonus"] += eff["attack_bonus"]
                combined_effects["damage_bonus"] += eff["damage_bonus"]
                combined_effects["crit_threshold"] += eff["crit_threshold"]
                for s, val in eff["stats"].items():
                    combined_effects["stats"][s] = max(combined_effects["stats"].get(s, 0), val)
    except Exception:
        pass

    return combined_effects, gear_data


def simulate_turn_1_dpr(
    sequence_type: str,
    classes: dict[str, int],
    stats: dict[str, int],
    gear_effects: dict,
    prof: int,
    target_ac: int = 18,
) -> dict:
    """Calculates Turn 1 Damage Per Round against AC 18."""
    crit_threshold = 20 - gear_effects["crit_threshold"]
    crit_chance = (21 - crit_threshold) / 20.0

    if sequence_type == "eldritch_blast":
        total_lvl = sum(classes.values())
        beams = 4 if total_lvl >= 17 else (3 if total_lvl >= 11 else (2 if total_lvl >= 5 else 1))
        cha_mod = parse_ability_modifier(stats["Cha"])
        attack_mod = prof + cha_mod + gear_effects["attack_bonus"]

        # Hit chance against target_ac (bounded 0.05 to 0.95)
        needed_roll = target_ac - attack_mod
        hit_chance = min(0.95, max(0.05, (21 - needed_roll) / 20.0))

        # Agonizing Blast beam: 1d10 (5.5) + cha_mod + damage_bonus
        beam_avg = 5.5 + cha_mod + gear_effects["damage_bonus"]
        beam_crit_avg = (5.5 * 2) + cha_mod + gear_effects["damage_bonus"]
        per_beam_expected = (hit_chance * beam_avg) + (crit_chance * 5.5)
        total_dpr = beams * per_beam_expected

        return {
            "sequence": f"Eldritch Blast ({beams} Beams, Agonizing Blast)",
            "actions_used": "1 Action",
            "beams_or_attacks": beams,
            "hit_chance_pct": round(hit_chance * 100, 1),
            "expected_dpr": round(total_dpr, 1),
            "max_crit_burst": round(beams * beam_crit_avg, 1),
        }

    # Default Melee Burst (Extra Attack + Action Surge + Smite if Paladin)
    attacks = 2
    if classes.get("fighter", 0) >= 11:
        attacks = 3

    has_action_surge = classes.get("fighter", 0) >= 2
    total_attacks = attacks * 2 if has_action_surge else attacks

    # Ability modifier (Str or Dex)
    main_mod = max(parse_ability_modifier(stats["Str"]), parse_ability_modifier(stats["Dex"]))
    attack_roll_bonus = prof + main_mod + gear_effects["attack_bonus"]
    needed_roll = target_ac - attack_roll_bonus
    hit_chance = min(0.95, max(0.05, (21 - needed_roll) / 20.0))

    # Base Weapon: Greatsword (2d6 = 7.0 avg) + main_mod + riders
    weapon_base = 7.0 + main_mod + gear_effects["damage_bonus"]

    # Smite rider if Paladin level >= 2
    paladin_lvl = classes.get("paladin", 0)
    smite_dice = 4.5 * min(5, 2 + (paladin_lvl // 3)) if paladin_lvl >= 2 else 0.0

    attack_avg = weapon_base + smite_dice
    per_attack_expected = (hit_chance * attack_avg) + (crit_chance * (7.0 + smite_dice))
    total_dpr = total_attacks * per_attack_expected

    return {
        "sequence": f"Melee Burst ({total_attacks} Attacks" + (", Action Surge" if has_action_surge else "") + (", Divine Smite" if paladin_lvl >= 2 else "") + ")",
        "actions_used": "2 Actions (Action Surge)" if has_action_surge else "1 Action",
        "beams_or_attacks": total_attacks,
        "hit_chance_pct": round(hit_chance * 100, 1),
        "expected_dpr": round(total_dpr, 1),
        "max_crit_burst": round(total_attacks * ((weapon_base + smite_dice) * 2), 1),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Theorycrafting simulator for Level 20 BG3 character builds and mod gear synergies."
    )
    parser.add_argument(
        "--classes",
        required=True,
        help="Class level breakdown (e.g. 'Paladin=7,Warlock=5,Sorcerer=8' or 'Wizard=20').",
    )
    parser.add_argument(
        "--stats",
        default="Str=16,Dex=14,Con=14,Int=10,Wis=10,Cha=20",
        help="Ability scores (Str=N,Dex=N,Con=N,Int=N,Wis=N,Cha=N).",
    )
    parser.add_argument(
        "--gear",
        help="Comma-separated gear names or item IDs to factor into stat and DC boosts.",
    )
    parser.add_argument(
        "--dpr-sequence",
        choices=["melee_burst", "eldritch_blast"],
        default="melee_burst",
        help="Turn 1 combat sequence to simulate (default: melee_burst).",
    )
    parser.add_argument("--target-ac", type=int, default=18, help="Enemy Armor Class for DPR simulation (default: 18).")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")

    args = parser.parse_args()
    workspace_root = Path(__file__).resolve().parent.parent

    try:
        # Parse classes
        classes = {}
        for c in args.classes.split(","):
            if "=" in c:
                k, v = c.split("=", 1)
                classes[k.strip().lower()] = int(v.strip())

        total_level = sum(classes.values())
        if total_level > 20:
            raise ValueError(f"Total character level cannot exceed 20 (got {total_level}).")

        # Parse stats
        stats = {"Str": 10, "Dex": 10, "Con": 10, "Int": 10, "Wis": 10, "Cha": 10}
        for s in args.stats.split(","):
            if "=" in s:
                k, v = s.split("=", 1)
                stats[k.strip().capitalize()] = int(v.strip())

        gear_list = [g.strip() for g in args.gear.split(",") if g.strip()] if args.gear else []
        gear_effects, gear_items = load_gear_boosts(gear_list, workspace_root)

        # Apply stat overrides from gear (e.g. Amulet of Greater Health -> Con 23)
        for stat_name, min_val in gear_effects["stats"].items():
            if min_val > stats.get(stat_name, 0):
                stats[stat_name] = min_val

        prof = calculate_proficiency(total_level)

        # Calculate Spell Slots
        caster_level = sum(classes[c] * CASTER_WEIGHTS.get(c, 0.0) for c in classes)
        caster_level_rounded = math.floor(caster_level)
        spell_slots = MULTICLASS_SPELL_SLOTS.get(min(20, max(1, caster_level_rounded)), [0]*9) if caster_level_rounded > 0 else [0]*9
        pact_count, pact_level = calculate_pact_slots(classes.get("warlock", 0))

        # Determine Primary Casting Stat
        primary_class = max(classes.items(), key=lambda x: x[1])[0]
        cast_stat_name = PRIMARY_CASTING_STAT.get(primary_class, "Cha")
        cast_mod = parse_ability_modifier(stats[cast_stat_name])

        spell_dc = 8 + prof + cast_mod + gear_effects["dc"]
        dex_mod = parse_ability_modifier(stats["Dex"])
        base_ac = 10 + dex_mod + gear_effects["ac"]

        # DPR Simulation
        dpr_sim = simulate_turn_1_dpr(
            sequence_type=args.dpr_sequence,
            classes=classes,
            stats=stats,
            gear_effects=gear_effects,
            prof=prof,
            target_ac=args.target_ac,
        )

        res = {
            "total_level": total_level,
            "classes": classes,
            "proficiency_bonus": prof,
            "final_stats": stats,
            "primary_casting_stat": cast_stat_name,
            "effective_spell_save_dc": spell_dc,
            "armor_class": base_ac,
            "spell_slots": {f"Level {i+1}": spell_slots[i] for i in range(9) if spell_slots[i] > 0},
            "pact_magic": {
                "slots": pact_count,
                "slot_level": pact_level,
            } if pact_count > 0 else None,
            "gear_applied": [g["display_name"] for g in gear_items],
            "gear_bonuses": {
                "dc_bonus": gear_effects["dc"],
                "ac_bonus": gear_effects["ac"],
                "attack_bonus": gear_effects["attack_bonus"],
            },
            "turn_1_dpr": dpr_sim,
        }

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            color = ConsoleColor(stream=sys.stdout)
            class_str = " / ".join(f"{c.capitalize()} {lvl}" for c, lvl in classes.items())
            print(f"{color.bold('Build Synergy Simulation:')} {class_str} (Level {total_level})")
            print("=" * 75)
            print(f"  Proficiency Bonus:   +{prof}")
            print(f"  Ability Scores:      STR {stats['Str']} | DEX {stats['Dex']} | CON {stats['Con']} | INT {stats['Int']} | WIS {stats['Wis']} | CHA {stats['Cha']}")
            print(f"  Effective Spell DC:  {spell_dc} (8 + {prof} Prof + {cast_mod} {cast_stat_name} + {gear_effects['dc']} Gear)")
            print(f"  Base Armor Class:    {base_ac}")
            if res["spell_slots"]:
                slots_repr = ", ".join(f"L{k[-1]}:{v}" for k, v in res["spell_slots"].items())
                print(f"  Spell Slots:         {slots_repr}")
            if res["pact_magic"]:
                print(f"  Pact Magic:          {pact_count}x Level {pact_level} slots")
            if gear_items:
                print(f"\n  Active Gear ({len(gear_items)} items):")
                for gi in gear_items:
                    print(f"    • {gi['display_name']} ({gi['mod']})")

            print("\n" + "-" * 75)
            print(f"Turn 1 Combat Simulation: {dpr_sim['sequence']}")
            print(f"  Target AC:           {args.target_ac}")
            print(f"  Hit Probability:     {dpr_sim['hit_chance_pct']}%")
            print(f"  Expected DPR:        {dpr_sim['expected_dpr']} damage")
            print(f"  Max Crit Potential:  {dpr_sim['max_crit_burst']} damage")

        return ExitCode.OK

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            err_color = ConsoleColor(stream=sys.stderr)
            print(f"{err_color.red('[ERROR]')} {e}", file=sys.stderr)
        return ExitCode.GENERAL


if __name__ == "__main__":
    sys.exit(main())
