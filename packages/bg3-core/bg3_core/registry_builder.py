#!/usr/bin/env python3
"""
registry_builder.py
-------------------
Dynamically inspects the unified bg3 CLI parser (bg3_core.cli) to extract
tool definitions, schemas, arguments, and categories into a standardized
tool registry. Provides single-source-of-truth tool discovery for agent skills
and human operators without manual JSON maintenance.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from bg3_core.env_paths import REPO_ROOT

CATEGORIES: Dict[str, str] = {
    "authoring": "Mod authoring, stat generation, progression curves, and asset scaffolding",
    "packaging": "Pure Python LSPK .pak archive building and game data deployment",
    "diagnostics": "Static validation, conflict detection, handle auditing, and save file inspection",
    "management": "Load order management, version bumping, metadata generation, and setup",
    "library": "Mod.io API search, archive synchronization, and community mod database queries",
    "theorycrafting": "Combat DPR simulation, multiclass spell slots, and build mechanics",
}

# Explicit category overrides for specific commands
COMMAND_CATEGORY_OVERRIDES: Dict[str, str] = {
    "mod conflict": "diagnostics",
    "mod validate": "diagnostics",
    "mod diagnose-logs": "diagnostics",
    "mod inspect-save": "diagnostics",
    "mod pack": "packaging",
    "mod sync-game": "packaging",
    "mod sync-loca": "diagnostics",
    "mod bump-version": "management",
    "mod render-desc": "management",
    "modio purge": "library",
    "modio catalog": "library",
    "modio update-catalog": "library",
    "modio update-metadata": "library",
    "modio create-collection": "library",
    "save": "diagnostics",
    "save list": "diagnostics",
    "save inspect": "diagnostics",
    "save backup": "management",
    "save purge": "management",
    "build": "theorycrafting",
    "sim": "theorycrafting",
    "query": "theorycrafting",
    "tools": "management",
    "env": "management",
}

# Legacy script name aliases mapped to modern canonical CLI commands
LEGACY_SCRIPT_ALIASES: Dict[str, str] = {
    "create_mod_scaffold.py": "mod create",
    "validate_mod.py": "mod validate",
    "check_mod_conflicts.py": "mod conflict",
    "add_mod_dependency.py": "mod add-dependency",
    "bump_mod_version.py": "mod bump-version",
    "pack_mod_pak.py": "mod pack",
    "sync_localization.py": "mod sync-loca",
    "sync_game_data.py": "mod sync-game",
    "generate_compat_patch.py": "mod patch",
    "diagnose_toolkit_logs.py": "mod diagnose-logs",
    "inspect_save_game.py": "mod inspect-save",
    "inject_treasure_table.py": "mod inject-treasure",
    "render_modio_description.py": "mod render-desc",
    "manage_load_order.py": "loadorder list",
    "modio_search.py": "modio search",
    "modio_sync.py": "modio sync",
    "modio_update.py": "modio update",
    "modio_extract.py": "modio extract",
    "modio_update_metadata.py": "modio update-metadata",
    "modio_create_collection.py": "modio create-collection",
    "purge_library.py": "modio purge",
    "update_library_catalog.py": "modio update-catalog",
    "setup_environment.py": "env setup",
    "simulate_build_synergy.py": "build simulate",
    "query_mod_database.py": "query",
    "tools.py": "tools list",
    "manage_saves.py": "save list",
    "scaffold_stat_entry.py": "scaffold stat",
    "scaffold_progression_node.py": "scaffold progression",
    "scaffold_root_template.py": "scaffold root-template",
    "scaffold_icon_uvs.py": "scaffold icon-uvs",
    "scaffold_class_description.py": "scaffold class",
    "scaffold_feat.py": "scaffold feat",
    "scaffold_action_resource.py": "scaffold action-resource",
    "scaffold_spell_list.py": "scaffold spell-list",
    "scaffold_level_map.py": "scaffold level-map",
    "scaffold_default_values.py": "scaffold default-values",
    "scaffold_tag.py": "scaffold tag",
    "scaffold_race.py": "scaffold race",
    "scaffold_origin.py": "scaffold origin",
    "scaffold_appearance_visual.py": "scaffold appearance",
}

# Reverse lookup: command -> list of legacy script names
CMD_TO_LEGACY_SCRIPTS: Dict[str, List[str]] = {}
for script, cmd in LEGACY_SCRIPT_ALIASES.items():
    CMD_TO_LEGACY_SCRIPTS.setdefault(cmd, []).append(script)


def determine_category(group: str, subcmd: Optional[str] = None) -> str:
    """Resolve category for a command group or subcmd pair."""
    key = f"{group} {subcmd}" if subcmd else group
    if key in COMMAND_CATEGORY_OVERRIDES:
        return COMMAND_CATEGORY_OVERRIDES[key]
    if group == "scaffold":
        return "authoring"
    if group == "mod":
        return "authoring"
    if group == "modio":
        return "library"
    if group == "loadorder":
        return "management"
    if group in ("build", "sim", "query"):
        return "theorycrafting"
    return "management"


def extract_flags_from_subparser(subp: argparse.ArgumentParser) -> List[Dict[str, Any]]:
    """Extract argument flag metadata from an argparse subparser."""
    flags: List[Dict[str, Any]] = []
    seen = set()

    for action in subp._actions:
        if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
            continue
        dest = action.dest
        if dest in ("help", "version") or dest in seen:
            continue
        seen.add(dest)

        flag_name = action.option_strings[0] if action.option_strings else f"<{dest}>"
        # Determine flag type string
        if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
            type_str = "bool"
        elif action.type is not None:
            type_str = getattr(action.type, "__name__", str(action.type))
        else:
            type_str = "str"

        flag_entry: Dict[str, Any] = {
            "name": flag_name,
            "type": type_str,
            "required": bool(action.required),
            "description": action.help or "",
        }
        if action.choices:
            flag_entry["choices"] = list(action.choices)
        if action.default not in (None, argparse.SUPPRESS, "==SUPPRESS=="):
            flag_entry["default"] = action.default

        flags.append(flag_entry)

    return flags


def generate_intents(group: str, subcmd: str, summary: str, aliases: List[str]) -> List[str]:
    """Generate search intents and keywords for tool ranking."""
    intents = {
        group,
        subcmd,
        f"{group} {subcmd}",
        f"bg3 {group} {subcmd}",
    }
    for alias in aliases:
        intents.add(alias)
        if alias.endswith(".py"):
            intents.add(alias[:-3])
        intents.add(f"bg3 {alias}")

    # Add keywords from summary
    if summary:
        for word in summary.replace(",", " ").replace(".", " ").replace("-", " ").split():
            clean_word = word.lower().strip()
            if len(clean_word) >= 3 and clean_word not in ("and", "the", "for", "with", "from"):
                intents.add(clean_word)

    return sorted(list(intents))


def extract_registry_from_parser(parser: Optional[argparse.ArgumentParser] = None) -> Dict[str, Any]:
    """
    Introspect the build_parser() CLI hierarchy to produce a comprehensive,
    unified tool registry dictionary.
    """
    if parser is None:
        from bg3_core.cli import build_parser
        parser = build_parser()

    tools: List[Dict[str, Any]] = []

    # Map top-level command groups from canonical _choices_actions
    for action in parser._actions:
        if not (action.choices and isinstance(action.choices, dict)):
            continue

        for ca in getattr(action, "_choices_actions", []):
            group_name = ca.dest
            group_subp = action.choices[group_name]
            group_summary = ca.help or ""

            # Check if group has nested subcommands
            sub_actions = [a for a in group_subp._actions if a.choices and isinstance(a.choices, dict)]
            if sub_actions:
                sub_a = sub_actions[0]
                for nca in getattr(sub_a, "_choices_actions", []):
                    subcmd_name = nca.dest
                    leaf_subp = sub_a.choices[subcmd_name]
                    summary = nca.help or leaf_subp.description or ""
                    description = leaf_subp.description or summary or f"bg3 {group_name} {subcmd_name} command"
                    category = determine_category(group_name, subcmd_name)
                    cmd_line = f"bg3 {group_name} {subcmd_name}"
                    flags = extract_flags_from_subparser(leaf_subp)

                    # Gather aliases
                    all_aliases = list(CMD_TO_LEGACY_SCRIPTS.get(f"{group_name} {subcmd_name}", []))
                    for alias_name, alias_subp in sub_a.choices.items():
                        if alias_subp is leaf_subp and alias_name != subcmd_name:
                            all_aliases.append(alias_name)
                            all_aliases.append(f"{group_name} {alias_name}")

                    intents = generate_intents(group_name, subcmd_name, summary, all_aliases)
                    cli_usage = f"bg3 {group_name} {subcmd_name} [options]"

                    tools.append({
                        "name": f"{group_name} {subcmd_name}",
                        "command": cmd_line,
                        "category": category,
                        "summary": summary,
                        "description": description,
                        "intents": intents,
                        "cli_usage": cli_usage,
                        "flags": flags,
                        "aliases": all_aliases,
                    })
            else:
                category = determine_category(group_name)
                cmd_line = f"bg3 {group_name}"
                summary = group_summary or group_subp.description or ""
                description = group_subp.description or summary or f"{cmd_line} command"
                flags = extract_flags_from_subparser(group_subp)

                all_aliases = list(CMD_TO_LEGACY_SCRIPTS.get(group_name, []))
                for alias_name, alias_subp in action.choices.items():
                    if alias_subp is group_subp and alias_name != group_name:
                        all_aliases.append(alias_name)

                intents = generate_intents(group_name, "", summary, all_aliases)
                cli_usage = f"bg3 {group_name} [options]"

                tools.append({
                    "name": group_name,
                    "command": cmd_line,
                    "category": category,
                    "summary": summary,
                    "description": description,
                    "intents": intents,
                    "cli_usage": cli_usage,
                    "flags": flags,
                    "aliases": all_aliases,
                })

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "version": "1.0.0",
        "description": "Baldur's Gate 3 Mod Studio Tooling Registry (Auto-Derived from CLI)",
        "categories": CATEGORIES,
        "tools": sorted(tools, key=lambda t: (t["category"], t["command"])),
    }


def export_registry_json(out_path: Optional[Path] = None) -> Path:
    """Generate and export the registry JSON snapshot."""
    dest = out_path or (Path(__file__).resolve().parent / "registry.json")
    registry_data = extract_registry_from_parser()
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)
    return dest


if __name__ == "__main__":
    out = export_registry_json()
    print(f"Exported registry JSON to {out}")
