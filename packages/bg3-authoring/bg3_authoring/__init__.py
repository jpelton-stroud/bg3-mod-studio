"""
bg3_authoring - Authoring, scaffolding, and asset generation toolkit for Baldur's Gate 3.
"""

from __future__ import annotations

from bg3_authoring.add_mod_dependency import add_permanent_dependency, add_test_dependency
from bg3_authoring.bump_mod_version import bump_version
from bg3_authoring.create_mod_scaffold import scaffold_mod
from bg3_authoring.diagnostics.diagnose_toolkit_logs import parse_log_file, purge_toolkit_logs
from bg3_authoring.diagnostics.sync_localization import (
    compile_mod_localization,
    sync_language_skeletons,
)
from bg3_authoring.diagnostics.validate_mod import check_uuid_uniqueness
from bg3_authoring.exceptions import (
    BG3AuthoringError,
    BG3ConflictError,
    BG3ScaffoldError,
)
from bg3_authoring.generate_compat_patch import merge_progression_attributes
from bg3_authoring.inject_treasure_table import inject_into_treasure_table
from bg3_authoring.packaging.pack_mod_pak import clean_local_pak, collect_mod_files
from bg3_authoring.packaging.sync_game_data import run_sync, sync_mod
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

__version__ = "1.0.0"

__all__ = [
    "ASSET_HANDLERS",
    "BG3AuthoringError",
    "BG3ConflictError",
    "BG3ScaffoldError",
    "ScaffoldResult",
    "__version__",
    "add_permanent_dependency",
    "add_test_dependency",
    "bump_version",
    "check_uuid_uniqueness",
    "clean_local_pak",
    "collect_mod_files",
    "compile_mod_localization",
    "inject_into_treasure_table",
    "merge_progression_attributes",
    "parse_log_file",
    "purge_toolkit_logs",
    "run_sync",
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
    "sync_language_skeletons",
    "sync_mod",
]
