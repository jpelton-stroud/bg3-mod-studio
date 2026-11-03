"""bg3_core.data subpackage.

Contains static base-game and community-mod reference tables for feature extraction,
metadata resolution, and spec generation.
"""

from bg3_core.data.mod_overrides import (
    BASE_GAME_LOCA_HANDLES,
    BASE_GAME_PASSIVES,
    BASE_GAME_SPELLS,
    GEARUP_CHEST_NAMES,
    MOD_SPECIFIC_OVERRIDES,
    PP_ACT1_ITEMS,
    PP_ACT2_ITEMS,
    PP_ACT3_ITEMS,
)

__all__ = [
    "BASE_GAME_LOCA_HANDLES",
    "BASE_GAME_PASSIVES",
    "BASE_GAME_SPELLS",
    "GEARUP_CHEST_NAMES",
    "MOD_SPECIFIC_OVERRIDES",
    "PP_ACT1_ITEMS",
    "PP_ACT2_ITEMS",
    "PP_ACT3_ITEMS",
]
