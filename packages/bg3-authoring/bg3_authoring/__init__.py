"""
bg3_authoring - Authoring, scaffolding, and asset generation toolkit for Baldur's Gate 3.
"""

from __future__ import annotations

from bg3_authoring.create_mod_scaffold import scaffold_mod
from bg3_authoring.scaffold_asset import (
    ASSET_HANDLERS,
    ScaffoldResult,
    scaffold_action_resource,
    scaffold_appearance_visual,
    scaffold_asset,
    scaffold_class,
    scaffold_default_values,
    scaffold_feat,
    scaffold_icon_uvs,
    scaffold_level_map,
    scaffold_origin,
    scaffold_progression,
    scaffold_race,
    scaffold_root_template,
    scaffold_spell_list,
    scaffold_stat,
    scaffold_tag,
)

__all__ = [
    "ASSET_HANDLERS",
    "ScaffoldResult",
    "scaffold_action_resource",
    "scaffold_appearance_visual",
    "scaffold_asset",
    "scaffold_class",
    "scaffold_default_values",
    "scaffold_feat",
    "scaffold_icon_uvs",
    "scaffold_level_map",
    "scaffold_mod",
    "scaffold_origin",
    "scaffold_progression",
    "scaffold_race",
    "scaffold_root_template",
    "scaffold_spell_list",
    "scaffold_stat",
    "scaffold_tag",
]
