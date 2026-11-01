"""bg3_theorycraft - Combat modeling, multiclass build simulation, and theorycrafting engine.

Exposes public computational engines for D&D 5e / Baldur's Gate 3 rulesets:
action economy, resource pools, advantage/disadvantage hit distributions across
AC 10-25 curves, Savage Attacker dice mathematics, and mod gear synergy analysis.
"""

from __future__ import annotations

from bg3_theorycraft.simulate_build_synergy import (
    CASTER_WEIGHTS,
    MULTICLASS_SPELL_SLOTS,
    PRIMARY_CASTING_STAT,
    calculate_ac_curve,
    calculate_action_economy,
    calculate_hit_probability,
    calculate_pact_slots,
    calculate_proficiency,
    calculate_resource_pools,
    calculate_savage_attacker_average,
    calculate_spell_slots,
    load_gear_boosts,
    main,
    parse_ability_modifier,
    parse_boost_effects,
    simulate_build,
    simulate_turn_1_dpr,
)

__all__ = [
    "CASTER_WEIGHTS",
    "MULTICLASS_SPELL_SLOTS",
    "PRIMARY_CASTING_STAT",
    "calculate_ac_curve",
    "calculate_action_economy",
    "calculate_hit_probability",
    "calculate_pact_slots",
    "calculate_proficiency",
    "calculate_resource_pools",
    "calculate_savage_attacker_average",
    "calculate_spell_slots",
    "load_gear_boosts",
    "main",
    "parse_ability_modifier",
    "parse_boost_effects",
    "simulate_build",
    "simulate_turn_1_dpr",
]
