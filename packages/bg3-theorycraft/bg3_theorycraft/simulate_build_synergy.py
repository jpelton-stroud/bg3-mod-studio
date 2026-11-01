#!/usr/bin/env python3
"""simulate_build_synergy.py - Theorycrafting simulator for Level 20 character builds.

Computes Level 20 Hit Points, Spell Slots, Resource Pools (Ki, Sorcery Points,
Superiority Dice, Channel Oath, Rage), Action Economy, Armor Class, effective
Spell Save DC ceilings, Advantage/Disadvantage hit distributions across AC 10-25,
and Turn 1 Damage Per Round (DPR) sequences factoring in cataloged mod equipment
via direct programmatic integration with bg3_core.query_mod_database.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.query_mod_database import build_or_load_index

from bg3_theorycraft.models import (
    ActionBudget,
    CombatSequence,
    DamageBreakdown,
    ResourcePools,
    SimulationResult,
)

# Caster classification for multiclass spell slot calculation
CASTER_WEIGHTS: Dict[str, float] = {
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

PRIMARY_CASTING_STAT: Dict[str, str] = {
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

# 5e Multiclass spell slots table (levels 1-20)
MULTICLASS_SPELL_SLOTS: Dict[int, List[int]] = {
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
    """Calculate 5e proficiency bonus for character level 1-20."""
    if total_level >= 17:
        return 6
    if total_level >= 13:
        return 5
    if total_level >= 9:
        return 4
    if total_level >= 5:
        return 3
    return 2


def parse_ability_modifier(score: int) -> int:
    """Calculate ability score modifier floor((score - 10) / 2)."""
    return math.floor((score - 10) / 2)


def calculate_spell_slots(classes: Dict[str, int]) -> Tuple[int, List[int]]:
    """Calculates multiclass caster level and 9-level spell slot array."""
    caster_level = sum(classes.get(c, 0) * CASTER_WEIGHTS.get(c, 0.0) for c in classes)
    caster_level_rounded = math.floor(caster_level)
    if caster_level_rounded <= 0:
        return 0, [0] * 9
    clamped_level = min(20, max(1, caster_level_rounded))
    return caster_level_rounded, list(MULTICLASS_SPELL_SLOTS.get(clamped_level, [0] * 9))


def calculate_pact_slots(warlock_level: int) -> Tuple[int, int]:
    """Returns (slot_count, slot_level) for Warlock Pact Magic."""
    if warlock_level <= 0:
        return 0, 0
    if warlock_level == 1:
        return 1, 1
    if warlock_level == 2:
        return 2, 1
    if warlock_level in (3, 4):
        return 2, 2
    if warlock_level in (5, 6):
        return 2, 3
    if warlock_level in (7, 8):
        return 2, 4
    if warlock_level in (9, 10):
        return 2, 5
    if warlock_level < 17:
        return 3, 5
    return 4, 5


def calculate_action_economy(classes: Dict[str, int]) -> Dict[str, Any]:
    """Calculates action economy budget: Actions, Bonus Actions, Reactions,

    Action Surge, and Extra Attack scaling.
    """
    fighter_lvl = classes.get("fighter", 0)
    rogue_lvl = classes.get("rogue", 0)
    has_action_surge = fighter_lvl >= 2

    # Extra Attack scaling: Fighter 20 -> 4, Fighter 11 -> 3, Martial 5 -> 2, else 1
    martial_classes = ("fighter", "paladin", "barbarian", "ranger", "monk")
    attacks_per_action = 1
    if fighter_lvl >= 20:
        attacks_per_action = 4
    elif fighter_lvl >= 11:
        attacks_per_action = 3
    elif any(classes.get(c, 0) >= 5 for c in martial_classes):
        attacks_per_action = 2

    base_actions = 1
    turn_1_actions = 2 if has_action_surge else 1

    # Rogue level 3 Fast Hands grants an extra Bonus Action
    bonus_actions = 2 if rogue_lvl >= 3 else 1
    reactions = 1

    total_turn_1_attacks = attacks_per_action * turn_1_actions

    return ActionBudget(
        base_actions=base_actions,
        turn_1_actions=turn_1_actions,
        has_action_surge=has_action_surge,
        bonus_actions=bonus_actions,
        reactions=reactions,
        attacks_per_action=attacks_per_action,
        turn_1_weapon_attacks=total_turn_1_attacks,
    )


def calculate_resource_pools(classes: Dict[str, int]) -> ResourcePools:
    """Calculates specific class action resources:

    Ki (Monk), Sorcery Points (Sorcerer), Superiority Dice (Fighter),
    Channel Oath (Paladin), and Rage Charges (Barbarian).
    """
    monk_lvl = classes.get("monk", 0)
    sorcerer_lvl = classes.get("sorcerer", 0)
    fighter_lvl = classes.get("fighter", 0)
    paladin_lvl = classes.get("paladin", 0)
    barbarian_lvl = classes.get("barbarian", 0)

    # Ki points: Monk level starting at level 2
    ki_points = monk_lvl if monk_lvl >= 2 else 0

    # Sorcery points: Sorcerer level starting at level 2
    sorcery_points = sorcerer_lvl if sorcerer_lvl >= 2 else 0

    # Superiority dice: Fighter level 3+
    if fighter_lvl >= 15:
        superiority_count = 6
        superiority_die = "d10"
    elif fighter_lvl >= 7:
        superiority_count = 5
        superiority_die = "d8"
    elif fighter_lvl >= 3:
        superiority_count = 4
        superiority_die = "d8"
    else:
        superiority_count = 0
        superiority_die = "None"

    # Channel Oath: Paladin level 1+
    channel_oath = 1 if paladin_lvl >= 1 else 0

    # Rage charges: Barbarian progression
    if barbarian_lvl >= 20:
        rage_charges: Any = "Unlimited"
    elif barbarian_lvl >= 17:
        rage_charges = 6
    elif barbarian_lvl >= 12:
        rage_charges = 5
    elif barbarian_lvl >= 6:
        rage_charges = 4
    elif barbarian_lvl >= 3:
        rage_charges = 3
    elif barbarian_lvl >= 1:
        rage_charges = 2
    else:
        rage_charges = 0

    return ResourcePools(
        ki_points=ki_points,
        sorcery_points=sorcery_points,
        superiority_dice={
            "count": superiority_count,
            "die": superiority_die,
        },
        channel_oath_charges=channel_oath,
        rage_charges=rage_charges,
    )


def calculate_savage_attacker_average(dice_count: int, die_sides: int) -> float:
    """Calculates exact analytical expected value for rolling dice_count d(die_sides)

    twice and selecting the higher sum (Savage Attacker feat).
    """
    # Compute probability mass function for sum of dice_count uniform independent dice
    # Base distribution for 1 die:
    probs = [0.0] + [1.0 / die_sides] * die_sides
    for _ in range(dice_count - 1):
        next_probs = [0.0] * (len(probs) + die_sides)
        for i, p in enumerate(probs):
            if p == 0.0:
                continue
            for d in range(1, die_sides + 1):
                next_probs[i + d] += p * (1.0 / die_sides)
        probs = next_probs

    # Compute CDF: F(s) = P(Sum <= s)
    cdf = [0.0] * len(probs)
    running = 0.0
    for s, p in enumerate(probs):
        running += p
        cdf[s] = running

    # E[max(X1, X2)] = sum_s s * (F(s)^2 - F(s-1)^2)
    ev = 0.0
    for s in range(dice_count, len(probs)):
        p_max = (cdf[s] ** 2) - (cdf[s - 1] ** 2 if s > 0 else 0.0)
        ev += s * p_max

    return round(ev, 4)


def calculate_hit_probability(
    target_ac: int,
    attack_bonus: int,
    crit_threshold: int = 20,
    roll_mode: str = "normal",
) -> Dict[str, float]:
    """Calculates hit and critical hit probabilities given target AC, attack bonus,

    crit threshold, and roll mode ('normal', 'advantage', 'disadvantage').
    """
    needed_roll = target_ac - attack_bonus

    # Standard d20 bounding: nat 1 always misses (0.95 max), nat 20 always hits (0.05 min)
    base_hit = min(0.95, max(0.05, (21.0 - needed_roll) / 20.0))

    threshold = max(1, min(20, crit_threshold))
    base_crit = (21.0 - threshold) / 20.0

    mode = roll_mode.lower()
    if mode == "advantage":
        p_hit = 1.0 - ((1.0 - base_hit) ** 2)
        p_crit = 1.0 - ((1.0 - base_crit) ** 2)
    elif mode == "disadvantage":
        p_hit = base_hit**2
        p_crit = base_crit**2
    else:
        p_hit = base_hit
        p_crit = base_crit

    # Ensure crit is counted inside hit, calculate regular hit probability
    p_hit = max(p_crit, p_hit)
    p_regular = max(0.0, p_hit - p_crit)

    return {
        "hit_chance": round(p_hit, 4),
        "crit_chance": round(p_crit, 4),
        "regular_hit_chance": round(p_regular, 4),
        "needed_roll": needed_roll,
    }


def parse_boost_effects(boost_str: str) -> Dict[str, Any]:
    """Parses stat, DC, AC, roll, and damage boosts from item boosts string."""
    stats_dict: Dict[str, int] = {}
    effects: Dict[str, Any] = {
        "dc": 0,
        "ac": 0,
        "attack_bonus": 0,
        "damage_bonus": 0,
        "crit_threshold": 0,
        "stats": stats_dict,
    }
    for part in boost_str.split(";"):
        part = part.strip()
        m_dc = re.search(r"SpellSaveDC\((\d+)\)", part, re.IGNORECASE)
        if m_dc:
            effects["dc"] = int(effects["dc"]) + int(m_dc.group(1))

        m_ac = re.search(r"AC\((\d+)\)", part, re.IGNORECASE)
        if m_ac:
            effects["ac"] = int(effects["ac"]) + int(m_ac.group(1))

        m_att = re.search(r"RollBonus\(Attack,\s*(\d+)", part, re.IGNORECASE)
        if m_att:
            effects["attack_bonus"] = int(effects["attack_bonus"]) + int(m_att.group(1))

        m_dmg = re.search(r"DamageBonus\((\d+)\)", part, re.IGNORECASE)
        if m_dmg:
            effects["damage_bonus"] = int(effects["damage_bonus"]) + int(m_dmg.group(1))

        m_crit = re.search(r"ReduceCriticalThreshold\((\d+)\)", part, re.IGNORECASE)
        if m_crit:
            effects["crit_threshold"] = int(effects["crit_threshold"]) + int(m_crit.group(1))

        m_ovr = re.search(r"AbilityOverrideMinimum\((\w+),\s*(\d+)", part, re.IGNORECASE)
        if m_ovr:
            stat_name = m_ovr.group(1)[:3].capitalize()
            stats_dict[stat_name] = max(stats_dict.get(stat_name, 0), int(m_ovr.group(2)))

    return effects


def load_gear_boosts(
    gear_items: List[str], workspace_root: Optional[Path] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Programmatically queries cataloged mod equipment using bg3_core.query_mod_database."""
    gear_data: List[Dict[str, Any]] = []
    combined_stats: Dict[str, int] = {}
    combined_effects: Dict[str, Any] = {
        "dc": 0,
        "ac": 0,
        "attack_bonus": 0,
        "damage_bonus": 0,
        "crit_threshold": 0,
        "weapon_damage": "",
        "stats": combined_stats,
    }

    if not gear_items:
        return combined_effects, gear_data

    # Query mod entries via bg3_core.query_mod_database
    entries = build_or_load_index(workspace_root=workspace_root)
    if not entries:
        return combined_effects, gear_data

    entries_by_id = {e["id"].lower(): e for e in entries if "id" in e}
    entries_by_name = {e["display_name"].lower(): e for e in entries if "display_name" in e}

    for item in gear_items:
        item_clean = item.strip().lower()
        matched = entries_by_id.get(item_clean) or entries_by_name.get(item_clean)
        if matched:
            gear_data.append(matched)
            boosts = matched.get("boosts", "")
            eff = parse_boost_effects(boosts)
            combined_effects["dc"] = int(combined_effects["dc"]) + int(eff["dc"])
            combined_effects["ac"] = int(combined_effects["ac"]) + int(eff["ac"])
            combined_effects["attack_bonus"] = int(combined_effects["attack_bonus"]) + int(
                eff["attack_bonus"]
            )
            combined_effects["damage_bonus"] = int(combined_effects["damage_bonus"]) + int(
                eff["damage_bonus"]
            )
            combined_effects["crit_threshold"] = int(combined_effects["crit_threshold"]) + int(
                eff["crit_threshold"]
            )

            # Record weapon damage if present
            if matched.get("slot") == "Weapon" and matched.get("damage"):
                combined_effects["weapon_damage"] = matched["damage"]

            eff_stats: Dict[str, int] = eff.get("stats", {})
            for s, val in eff_stats.items():
                combined_stats[s] = max(combined_stats.get(s, 0), val)

    return combined_effects, gear_data


def _parse_weapon_dice(
    weapon_str: str | None, default: tuple[int, int] = (2, 6)
) -> tuple[int, int]:
    if not weapon_str:
        return default
    m = re.match(r"^(\d+)[dD](\d+)$", str(weapon_str).strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return default


def simulate_turn_1_dpr(
    sequence_type: str,
    classes: Dict[str, int],
    stats: Dict[str, int],
    gear_effects: Dict[str, Any],
    prof: int,
    target_ac: int = 18,
    roll_mode: str = "normal",
    savage_attacker: bool = False,
    weapon_damage: str | None = None,
) -> CombatSequence:
    """Calculates Turn 1 Damage Per Round factoring in class abilities, resources,

    roll state (Advantage/Disadvantage), and Savage Attacker dice math.
    """
    crit_threshold = 20 - int(gear_effects.get("crit_threshold", 0))
    action_econ = calculate_action_economy(classes)
    resources = calculate_resource_pools(classes)

    if sequence_type == "eldritch_blast":
        total_lvl = sum(classes.values())
        base_beams = (
            4 if total_lvl >= 17 else (3 if total_lvl >= 11 else (2 if total_lvl >= 5 else 1))
        )
        cha_mod = parse_ability_modifier(stats.get("Cha", 10))
        attack_mod = prof + cha_mod + gear_effects.get("attack_bonus", 0)

        hit_info = calculate_hit_probability(target_ac, attack_mod, crit_threshold, roll_mode)
        p_hit = hit_info["hit_chance"]
        p_crit = hit_info["crit_chance"]

        # Metamagic Quicken Spell: Sorcerer level >= 3 with >= 3 Sorcery Points casts a second EB
        has_quicken = classes.get("sorcerer", 0) >= 3 and resources["sorcery_points"] >= 3
        # Fighter Action Surge: Fighter level >= 2 casts EB with surged Action
        has_surge = action_econ["has_action_surge"]

        multiplier = 1
        actions_desc = ["1 Action"]
        if has_surge:
            multiplier += 1
            actions_desc.append("Action Surge")
        if has_quicken:
            multiplier += 1
            actions_desc.append("Quickened (3 SP)")

        total_beams = base_beams * multiplier

        # Beam: 1d10 (5.5) + cha_mod (Agonizing Blast) + gear_damage
        dmg_bonus = gear_effects.get("damage_bonus", 0)
        beam_avg = 5.5 + cha_mod + dmg_bonus
        beam_crit_extra = 5.5  # Extra 1d10 on critical hit

        per_beam_expected = (p_hit * beam_avg) + (p_crit * beam_crit_extra)
        total_dpr = total_beams * per_beam_expected
        max_crit_burst = total_beams * ((5.5 * 2) + cha_mod + dmg_bonus)

        return CombatSequence(
            sequence=f"Eldritch Blast ({total_beams} Beams, Agonizing Blast)",
            actions_used=" + ".join(actions_desc),
            beams_or_attacks=total_beams,
            hit_chance_pct=round(p_hit * 100, 1),
            crit_chance_pct=round(p_crit * 100, 1),
            expected_dpr=round(total_dpr, 1),
            max_crit_burst=round(max_crit_burst, 1),
            roll_mode=roll_mode,
            savage_attacker=savage_attacker,
            sequence_type=sequence_type,
            damage_breakdown=DamageBreakdown(
                weapon_base_avg=5.5,
                ability_mod=cha_mod,
                gear_damage_bonus=dmg_bonus,
                hit_damage_per_attack=beam_avg,
                crit_damage_per_attack=beam_crit_extra,
            ),
        )

    if sequence_type == "ranged_burst":
        total_attacks = action_econ["turn_1_weapon_attacks"]
        dex_mod = parse_ability_modifier(stats.get("Dex", 10))
        attack_roll_bonus = prof + dex_mod + gear_effects.get("attack_bonus", 0)

        hit_info = calculate_hit_probability(target_ac, attack_roll_bonus, crit_threshold, roll_mode)
        p_hit = hit_info["hit_chance"]
        p_crit = hit_info["crit_chance"]

        w_spec = weapon_damage or gear_effects.get("weapon_damage", "1d10")
        w_count, w_sides = _parse_weapon_dice(w_spec, default=(1, 10))
        if savage_attacker:
            weapon_base_die = calculate_savage_attacker_average(w_count, w_sides)
        else:
            weapon_base_die = w_count * (w_sides + 1) / 2.0

        dmg_bonus = gear_effects.get("damage_bonus", 0)
        rogue_lvl = classes.get("rogue", 0)
        sneak_attack_avg = math.ceil(rogue_lvl / 2) * 3.5 if rogue_lvl >= 1 else 0.0

        superiority_avg = 0.0
        if resources["superiority_dice"]["count"] > 0:
            superiority_avg = 5.5 if resources["superiority_dice"]["die"] == "d10" else 4.5

        action_notes = [f"{action_econ['turn_1_actions']} Action(s)"]
        if action_econ["has_action_surge"]:
            action_notes.append("Action Surge")
        if rogue_lvl >= 1:
            action_notes.append("Sneak Attack")

        attack_flat = dex_mod + dmg_bonus
        per_attack_base = weapon_base_die + attack_flat
        per_attack_crit_extra = (
            weapon_base_die * 2 if savage_attacker else (w_count * (w_sides + 1) / 2.0)
        )

        total_dpr = (
            total_attacks * ((p_hit * per_attack_base) + (p_crit * per_attack_crit_extra))
            + (p_hit * sneak_attack_avg)
            + (p_crit * sneak_attack_avg)
            + (p_hit * superiority_avg)
        )

        max_crit_burst = (
            total_attacks * (((weapon_base_die) * 2) + attack_flat)
            + (sneak_attack_avg * 2)
            + (superiority_avg * 2)
        )

        return CombatSequence(
            sequence=f"Ranged Burst ({total_attacks} Attacks)",
            actions_used=" + ".join(action_notes),
            beams_or_attacks=total_attacks,
            hit_chance_pct=round(p_hit * 100, 1),
            crit_chance_pct=round(p_crit * 100, 1),
            expected_dpr=round(total_dpr, 1),
            max_crit_burst=round(max_crit_burst, 1),
            roll_mode=roll_mode,
            savage_attacker=savage_attacker,
            sequence_type=sequence_type,
            damage_breakdown=DamageBreakdown(
                weapon_base_avg=weapon_base_die,
                ability_mod=dex_mod,
                smite_avg=0.0,
                sneak_attack_avg=sneak_attack_avg,
                rage_bonus=0,
                gear_damage_bonus=dmg_bonus,
                superiority_avg=superiority_avg,
                hit_damage_per_attack=per_attack_base,
                crit_damage_per_attack=per_attack_crit_extra,
            ),
        )

    # Default Melee Burst
    total_attacks = action_econ["turn_1_weapon_attacks"]
    main_mod = max(
        parse_ability_modifier(stats.get("Str", 10)), parse_ability_modifier(stats.get("Dex", 10))
    )
    attack_roll_bonus = prof + main_mod + gear_effects.get("attack_bonus", 0)

    hit_info = calculate_hit_probability(target_ac, attack_roll_bonus, crit_threshold, roll_mode)
    p_hit = hit_info["hit_chance"]
    p_crit = hit_info["crit_chance"]

    # Base Weapon: parameterized weapon_damage or gear weapon or Greatsword (2d6)
    w_spec = weapon_damage or gear_effects.get("weapon_damage", "2d6")
    weapon_dice_count, weapon_die_sides = _parse_weapon_dice(w_spec, default=(2, 6))
    if savage_attacker:
        weapon_base_die = calculate_savage_attacker_average(weapon_dice_count, weapon_die_sides)
    else:
        weapon_base_die = weapon_dice_count * (weapon_die_sides + 1) / 2.0

    dmg_bonus = gear_effects.get("damage_bonus", 0)

    # Barbarian Rage bonus damage
    barbarian_lvl = classes.get("barbarian", 0)
    rage_bonus = 0
    if barbarian_lvl >= 16:
        rage_bonus = 4
    elif barbarian_lvl >= 9:
        rage_bonus = 3
    elif barbarian_lvl >= 1:
        rage_bonus = 2

    # Paladin Divine Smite: uses highest available multiclass or pact spell slot
    paladin_lvl = classes.get("paladin", 0)
    smite_dice_avg = 0.0
    if paladin_lvl >= 2:
        _, slots = calculate_spell_slots(classes)
        pact_count, pact_level = calculate_pact_slots(classes.get("warlock", 0))
        highest_slot = 0
        for i in range(len(slots) - 1, -1, -1):
            if slots[i] > 0:
                highest_slot = i + 1
                break
        highest_slot = max(highest_slot, pact_level if pact_count > 0 else 0)
        # Divine Smite: 2d8 for 1st level slot, +1d8 per slot level above 1st, max 5d8
        smite_slot_effective = min(4, max(1, highest_slot if highest_slot > 0 else 1))
        smite_dice_count = 1 + smite_slot_effective
        smite_dice_avg = smite_dice_count * 4.5

    # Rogue Sneak Attack: ceil(rogue_lvl / 2) d6 once per turn
    rogue_lvl = classes.get("rogue", 0)
    sneak_attack_avg = math.ceil(rogue_lvl / 2) * 3.5 if rogue_lvl >= 1 else 0.0

    # Superiority Die rider: Fighter level >= 3 adds 1 die on first attack
    superiority_avg = 0.0
    if resources["superiority_dice"]["count"] > 0:
        superiority_avg = 5.5 if resources["superiority_dice"]["die"] == "d10" else 4.5

    # Turn 1 actions description
    action_notes: List[str] = [f"{action_econ['turn_1_actions']} Action(s)"]
    if action_econ["has_action_surge"]:
        action_notes.append("Action Surge")
    if paladin_lvl >= 2:
        action_notes.append("Divine Smite")
    if barbarian_lvl >= 1:
        action_notes.append(f"Rage (+{rage_bonus})")
    if rogue_lvl >= 1:
        action_notes.append("Sneak Attack")

    attack_flat = main_mod + dmg_bonus + rage_bonus
    per_attack_base = weapon_base_die + attack_flat + smite_dice_avg
    per_attack_crit_extra = (
        (weapon_base_die * 2 if savage_attacker else (weapon_dice_count * (weapon_die_sides + 1) / 2.0))
        + smite_dice_avg
    )  # Extra dice on crit

    total_dpr = (
        total_attacks * ((p_hit * per_attack_base) + (p_crit * per_attack_crit_extra))
        + (p_hit * sneak_attack_avg)
        + (p_crit * sneak_attack_avg)
        + (p_hit * superiority_avg)
    )

    max_crit_burst = (
        total_attacks * (((weapon_base_die + smite_dice_avg) * 2) + attack_flat)
        + (sneak_attack_avg * 2)
        + (superiority_avg * 2)
    )

    return CombatSequence(
        sequence=f"Melee Burst ({total_attacks} Attacks)",
        actions_used=" + ".join(action_notes),
        beams_or_attacks=total_attacks,
        hit_chance_pct=round(p_hit * 100, 1),
        crit_chance_pct=round(p_crit * 100, 1),
        expected_dpr=round(total_dpr, 1),
        max_crit_burst=round(max_crit_burst, 1),
        roll_mode=roll_mode,
        savage_attacker=savage_attacker,
        sequence_type=sequence_type,
        damage_breakdown=DamageBreakdown(
            weapon_base_avg=weapon_base_die,
            ability_mod=main_mod,
            smite_avg=smite_dice_avg,
            sneak_attack_avg=sneak_attack_avg,
            rage_bonus=rage_bonus,
            gear_damage_bonus=dmg_bonus,
            superiority_avg=superiority_avg,
            hit_damage_per_attack=per_attack_base,
            crit_damage_per_attack=per_attack_crit_extra,
        ),
    )


def calculate_ac_curve(
    sequence_type: str,
    classes: Dict[str, int],
    stats: Dict[str, int],
    gear_effects: Dict[str, Any],
    prof: int,
    roll_mode: str = "normal",
    savage_attacker: bool = False,
    min_ac: int = 10,
    max_ac: int = 25,
) -> List[Dict[str, Any]]:
    """Calculates Damage Per Round and Hit Chances across an AC curve (10-25)."""
    curve: List[Dict[str, Any]] = []
    for ac in range(min_ac, max_ac + 1):
        sim = simulate_turn_1_dpr(
            sequence_type=sequence_type,
            classes=classes,
            stats=stats,
            gear_effects=gear_effects,
            prof=prof,
            target_ac=ac,
            roll_mode=roll_mode,
            savage_attacker=savage_attacker,
        )
        curve.append(
            {
                "target_ac": ac,
                "hit_chance_pct": sim["hit_chance_pct"],
                "crit_chance_pct": sim["crit_chance_pct"],
                "expected_dpr": sim["expected_dpr"],
            }
        )
    return curve


def simulate_build(
    classes: Dict[str, int],
    stats: Dict[str, int],
    gear_items: Optional[List[str]] = None,
    dpr_sequence: str = "melee_burst",
    target_ac: int = 18,
    roll_mode: str = "normal",
    savage_attacker: bool = False,
    include_ac_curve: bool = False,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Top-level simulation function for character progression, resource pools,

    action economy, and combat DPR.
    """
    total_level = sum(classes.values())
    if total_level > 20:
        raise ValueError(f"Total character level cannot exceed 20 (got {total_level}).")

    gear_effects, loaded_gear = load_gear_boosts(gear_items or [], workspace_root=workspace_root)

    # Apply gear stat overrides (e.g. Amulet of Greater Health -> Con 23)
    final_stats = dict(stats)
    for stat_name, min_val in gear_effects.get("stats", {}).items():
        if min_val > final_stats.get(stat_name, 0):
            final_stats[stat_name] = min_val

    prof = calculate_proficiency(total_level)
    caster_lvl, spell_slots = calculate_spell_slots(classes)
    pact_count, pact_level = calculate_pact_slots(classes.get("warlock", 0))

    primary_class = max(classes.items(), key=lambda x: x[1])[0]
    cast_stat_name = PRIMARY_CASTING_STAT.get(primary_class, "Cha")
    cast_mod = parse_ability_modifier(final_stats.get(cast_stat_name, 10))

    spell_dc = 8 + prof + cast_mod + gear_effects.get("dc", 0)
    dex_mod = parse_ability_modifier(final_stats.get("Dex", 10))
    base_ac = 10 + dex_mod + gear_effects.get("ac", 0)

    action_econ = calculate_action_economy(classes)
    resources = calculate_resource_pools(classes)

    dpr_sim = simulate_turn_1_dpr(
        sequence_type=dpr_sequence,
        classes=classes,
        stats=final_stats,
        gear_effects=gear_effects,
        prof=prof,
        target_ac=target_ac,
        roll_mode=roll_mode,
        savage_attacker=savage_attacker,
    )

    ac_curve_data: list[dict[str, Any]] = []
    if include_ac_curve:
        ac_curve_data = calculate_ac_curve(
            sequence_type=dpr_sequence,
            classes=classes,
            stats=final_stats,
            gear_effects=gear_effects,
            prof=prof,
            roll_mode=roll_mode,
            savage_attacker=savage_attacker,
        )

    return SimulationResult(
        total_level=total_level,
        classes=classes,
        proficiency_bonus=prof,
        final_stats=final_stats,
        primary_casting_stat=cast_stat_name,
        effective_spell_save_dc=spell_dc,
        armor_class=base_ac,
        spell_slots={f"Level {i+1}": spell_slots[i] for i in range(9) if spell_slots[i] > 0},
        pact_magic={
            "slots": pact_count,
            "slot_level": pact_level,
        }
        if pact_count > 0
        else None,
        action_economy=action_econ,
        resource_pools=resources,
        gear_applied=[g.get("display_name", g.get("id")) for g in loaded_gear],
        gear_bonuses={
            "dc_bonus": gear_effects.get("dc", 0),
            "ac_bonus": gear_effects.get("ac", 0),
            "attack_bonus": gear_effects.get("attack_bonus", 0),
            "damage_bonus": gear_effects.get("damage_bonus", 0),
        },
        turn_1_dpr=dpr_sim,
        ac_curve=ac_curve_data,
    )


def main() -> int:
    """CLI entrypoint for bg3 build simulate."""
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
        choices=["melee_burst", "eldritch_blast", "ranged_burst"],
        default="melee_burst",
        help="Turn 1 combat sequence to simulate (default: melee_burst).",
    )
    parser.add_argument(
        "--target-ac",
        type=int,
        default=18,
        help="Enemy Armor Class for DPR simulation (default: 18).",
    )
    parser.add_argument(
        "--roll-mode",
        choices=["normal", "advantage", "disadvantage"],
        default="normal",
        help="Roll mode distribution (default: normal).",
    )
    parser.add_argument(
        "--advantage",
        action="store_const",
        dest="roll_mode",
        const="advantage",
        help="Shorthand for --roll-mode advantage.",
    )
    parser.add_argument(
        "--disadvantage",
        action="store_const",
        dest="roll_mode",
        const="disadvantage",
        help="Shorthand for --roll-mode disadvantage.",
    )
    parser.add_argument(
        "--savage-attacker",
        action="store_true",
        help="Apply Savage Attacker feat weapon damage rerolls.",
    )
    parser.add_argument(
        "--ac-curve",
        action="store_true",
        help="Output full Damage Per Round distribution across AC 10-25.",
    )
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")

    args = parser.parse_args()

    try:
        # Parse classes
        classes = {}
        for c in args.classes.split(","):
            if "=" in c:
                k, v = c.split("=", 1)
                classes[k.strip().lower()] = int(v.strip())

        # Parse stats
        stats = {"Str": 10, "Dex": 10, "Con": 10, "Int": 10, "Wis": 10, "Cha": 10}
        for s in args.stats.split(","):
            if "=" in s:
                k, v = s.split("=", 1)
                stats[k.strip().capitalize()] = int(v.strip())

        gear_list = (
            [g.strip() for g in args.gear.split(",") if g.strip()] if args.gear else []
        )

        res = simulate_build(
            classes=classes,
            stats=stats,
            gear_items=gear_list,
            dpr_sequence=args.dpr_sequence,
            target_ac=args.target_ac,
            roll_mode=args.roll_mode,
            savage_attacker=args.savage_attacker,
            include_ac_curve=args.ac_curve,
        )

        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            color = ConsoleColor(stream=sys.stdout)
            class_str = " / ".join(f"{c.capitalize()} {lvl}" for c, lvl in classes.items())
            print(f"{color.bold('Build Synergy Simulation:')} {class_str} (Level {res['total_level']})")
            print("=" * 75)
            print(f"  Proficiency Bonus:   +{res['proficiency_bonus']}")
            st = res["final_stats"]
            print(f"  Ability Scores:      STR {st['Str']} | DEX {st['Dex']} | CON {st['Con']} | INT {st['Int']} | WIS {st['Wis']} | CHA {st['Cha']}")
            print(f"  Effective Spell DC:  {res['effective_spell_save_dc']}")
            print(f"  Base Armor Class:    {res['armor_class']}")

            # Action Economy
            ae = res["action_economy"]
            surge_str = " (Action Surge)" if ae["has_action_surge"] else ""
            print(f"  Action Economy:      {ae['turn_1_actions']} Action(s){surge_str} | {ae['bonus_actions']} Bonus Action(s) | {ae['reactions']} Reaction(s)")
            print(f"  Attacks per Action:  {ae['attacks_per_action']} ({ae['turn_1_weapon_attacks']} total turn-1 attacks)")

            # Resource Pools
            rp = res["resource_pools"]
            pools: List[str] = []
            if rp["ki_points"] > 0:
                pools.append(f"Ki: {rp['ki_points']}")
            if rp["sorcery_points"] > 0:
                pools.append(f"Sorcery Points: {rp['sorcery_points']}")
            if rp["superiority_dice"]["count"] > 0:
                pools.append(f"Superiority: {rp['superiority_dice']['count']}{rp['superiority_dice']['die']}")
            if rp["channel_oath_charges"] > 0:
                pools.append(f"Channel Oath: {rp['channel_oath_charges']}")
            if rp["rage_charges"] != 0:
                pools.append(f"Rage: {rp['rage_charges']}")
            if pools:
                print(f"  Resource Pools:      {' | '.join(pools)}")

            if res["spell_slots"]:
                slots_repr = ", ".join(f"L{k[-1]}:{v}" for k, v in res["spell_slots"].items())
                print(f"  Spell Slots:         {slots_repr}")
            if res["pact_magic"]:
                print(f"  Pact Magic:          {res['pact_magic']['slots']}x Level {res['pact_magic']['slot_level']} slots")
            if res["gear_applied"]:
                print(f"\n  Active Gear ({len(res['gear_applied'])} items):")
                for gi in res["gear_applied"]:
                    print(f"    • {gi}")

            print("\n" + "-" * 75)
            dpr = res["turn_1_dpr"]
            print(f"Turn 1 Combat Simulation: {dpr['sequence']}")
            print(f"  Actions Expended:    {dpr['actions_used']}")
            print(f"  Roll Mode:           {dpr['roll_mode'].capitalize()}" + (" (Savage Attacker)" if dpr["savage_attacker"] else ""))
            print(f"  Target AC:           {args.target_ac}")
            print(f"  Hit Probability:     {dpr['hit_chance_pct']}% (Crit: {dpr['crit_chance_pct']}%)")
            print(f"  Expected DPR:        {dpr['expected_dpr']} damage")
            print(f"  Max Crit Potential:  {dpr['max_crit_burst']} damage")

            if "ac_curve" in res:
                print("\n" + "-" * 75)
                print("Target AC Distribution Curve (AC 10-25):")
                print("  AC | Hit % | Crit % | Expected DPR")
                print("  ---+-------+--------+-------------")
                for row in res["ac_curve"]:
                    print(f"  {row['target_ac']:2d} | {row['hit_chance_pct']:4.1f}% |  {row['crit_chance_pct']:4.1f}% | {row['expected_dpr']:6.1f} dmg")

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
