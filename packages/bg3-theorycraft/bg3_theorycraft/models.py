#!/usr/bin/env python3
"""
models.py
---------
Strongly-typed domain dataclasses for Baldur's Gate 3 theorycrafting:
action economy budgets, resource pools, damage breakdowns, combat sequences,
and complete build simulation results.
"""

from __future__ import annotations

import collections.abc
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator


class _MappingDataclass(collections.abc.Mapping[str, Any]):
    """Base mixin providing transparent dict access and mapping semantics to dataclasses."""

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass and nested dataclasses to primitive dictionaries."""
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        d = self.to_dict()
        if key in d:
            return d[key]
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass
class ActionBudget(_MappingDataclass):
    """Action economy budget for Turn 1 burst combat."""

    base_actions: int = 1
    turn_1_actions: int = 1
    bonus_actions: int = 1
    reactions: int = 1
    attacks_per_action: int = 1
    turn_1_weapon_attacks: int = 1
    has_action_surge: bool = False


@dataclass
class ResourcePools(_MappingDataclass):
    """Resource pools available to a character build."""

    ki_points: int = 0
    sorcery_points: int = 0
    superiority_dice: dict[str, Any] = field(default_factory=lambda: {"count": 0, "die": "None"})
    channel_oath_charges: int = 0
    rage_charges: int | str = 0


@dataclass
class DamageBreakdown(_MappingDataclass):
    """Mathematical damage decomposition per attack hit and crit."""

    weapon_base_avg: float = 0.0
    ability_mod: int = 0
    smite_avg: float = 0.0
    sneak_attack_avg: float = 0.0
    rage_bonus: int = 0
    gear_damage_bonus: int = 0
    superiority_avg: float = 0.0
    hit_damage_per_attack: float = 0.0
    crit_damage_per_attack: float = 0.0


@dataclass
class CombatSequence(_MappingDataclass):
    """Simulated Turn 1 combat sequence results."""

    sequence: str
    actions_used: str
    beams_or_attacks: int
    hit_chance_pct: float
    crit_chance_pct: float
    expected_dpr: float
    max_crit_burst: float
    roll_mode: str = "normal"
    savage_attacker: bool = False
    sequence_type: str = "melee_burst"
    damage_breakdown: DamageBreakdown | dict[str, Any] | None = None


@dataclass
class SimulationResult(_MappingDataclass):
    """Complete character build simulation output."""

    total_level: int
    classes: dict[str, int]
    proficiency_bonus: int
    final_stats: dict[str, int]
    primary_casting_stat: str
    effective_spell_save_dc: int
    armor_class: int
    spell_slots: dict[str, int]
    pact_magic: dict[str, int] | None
    action_economy: ActionBudget
    resource_pools: ResourcePools
    turn_1_dpr: CombatSequence
    gear_applied: list[str] = field(default_factory=list)
    gear_bonuses: dict[str, int] = field(default_factory=dict)
    ac_curve: list[dict[str, Any]] = field(default_factory=list)
