"""damage_types.py.

D&D 5e / Baldur's Gate 3 damage type enumerations, resistance multipliers,
and damage scaling primitives.
"""

from __future__ import annotations

from enum import Enum
from typing import Union


class DamageType(str, Enum):
    """Standard damage types in Baldur's Gate 3 / D&D 5e."""

    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    THUNDER = "thunder"
    ACID = "acid"
    POISON = "poison"
    RADIANT = "radiant"
    NECROTIC = "necrotic"
    FORCE = "force"
    PSYCHIC = "psychic"


class ResistanceMultiplier(float, Enum):
    """Multipliers applied to damage based on target resistance state."""

    IMMUNITY = 0.0
    RESISTANCE = 0.5
    NORMAL = 1.0
    VULNERABILITY = 2.0


RESISTANCE_LOOKUP: dict[str, float] = {
    "immunity": ResistanceMultiplier.IMMUNITY.value,
    "immune": ResistanceMultiplier.IMMUNITY.value,
    "resistance": ResistanceMultiplier.RESISTANCE.value,
    "resistant": ResistanceMultiplier.RESISTANCE.value,
    "normal": ResistanceMultiplier.NORMAL.value,
    "vulnerability": ResistanceMultiplier.VULNERABILITY.value,
    "vulnerable": ResistanceMultiplier.VULNERABILITY.value,
}


def normalize_damage_type(dt: str | DamageType) -> DamageType:
    """Normalize and validate damage type representation."""
    if isinstance(dt, DamageType):
        return dt
    key = str(dt).strip().lower()
    try:
        return DamageType(key)
    except ValueError as err:
        raise ValueError(f"Unknown damage type: '{dt}'") from err


def apply_resistance(
    damage: float,
    resistance: Union[float, ResistanceMultiplier, str] = ResistanceMultiplier.NORMAL,
) -> float:
    """Apply resistance multiplier (immunity: 0.0, resistance: 0.5, normal: 1.0, vulnerability: 2.0) to raw damage."""
    if isinstance(resistance, ResistanceMultiplier):
        mult = resistance.value
    elif isinstance(resistance, str):
        key = resistance.strip().lower()
        if key in RESISTANCE_LOOKUP:
            mult = RESISTANCE_LOOKUP[key]
        else:
            try:
                mult = float(key)
            except ValueError as err:
                raise ValueError(
                    f"Unknown resistance specification: '{resistance}'. "
                    f"Expected one of {list(RESISTANCE_LOOKUP.keys())} or a numeric multiplier."
                ) from err
    else:
        mult = float(resistance)

    return damage * mult


__all__ = [
    "RESISTANCE_LOOKUP",
    "DamageType",
    "ResistanceMultiplier",
    "apply_resistance",
    "normalize_damage_type",
]
