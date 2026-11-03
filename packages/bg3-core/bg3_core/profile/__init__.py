"""Profile, save game, and load order management."""

from __future__ import annotations

from bg3_core.profile.check_mod_conflicts import (
    compare_candidate_against_catalog,
    compare_two_mods,
)
from bg3_core.profile.manage_load_order import (
    auto_sort_load_order,
    clean_steam_data_paks,
    deduplicate_installed_paks,
    disable_mod,
    enable_mod,
    isolate_load_order,
    parse_modsettings,
    quarantine_unrelated_paks,
    restore_quarantined_paks,
    topological_sort_mods,
    validate_load_order,
)
from bg3_core.profile.manage_saves import (
    backup_save_games,
    discover_save_games,
    filter_saves_for_purge,
    purge_save_games,
)
from bg3_core.profile.mod_resolver import (
    KNOWN_DEPENDENCIES,
    ensure_dependency_paks,
    resolve_dependency_metadata,
)
from bg3_core.profile.save_inspector import (
    audit_against_modsettings,
    extract_save_metadata,
    find_save_file,
    get_save_search_paths,
    prune_missing_mods_from_save,
)

__all__ = [
    "KNOWN_DEPENDENCIES",
    "audit_against_modsettings",
    "auto_sort_load_order",
    "backup_save_games",
    "clean_steam_data_paks",
    "compare_candidate_against_catalog",
    "compare_two_mods",
    "deduplicate_installed_paks",
    "disable_mod",
    "discover_save_games",
    "enable_mod",
    "ensure_dependency_paks",
    "extract_save_metadata",
    "filter_saves_for_purge",
    "find_save_file",
    "get_save_search_paths",
    "isolate_load_order",
    "parse_modsettings",
    "prune_missing_mods_from_save",
    "purge_save_games",
    "quarantine_unrelated_paks",
    "resolve_dependency_metadata",
    "restore_quarantined_paks",
    "topological_sort_mods",
    "validate_load_order",
]
