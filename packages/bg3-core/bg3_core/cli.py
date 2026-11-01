"""
Baldur's Gate 3 Mod Studio & Mod.io Automation Workspace — Lightweight In-Process CLI Dispatcher.

Transparently routes noun-verb CLI commands to self-contained module entrypoints in-process.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, NoReturn, Optional, Tuple

from bg3_core.cli_common import (
    ConsoleColor,
    ExitCode,
    NonInteractiveConfirmationError,
    OutputEmitter,
    confirm_action,
)


class CommandSpec(NamedTuple):
    target_module: str
    help: str
    category: str
    pkg_requirement: Optional[str] = None


class JsonCompliantArgumentParser(argparse.ArgumentParser):
    """Intercept parser errors to emit formatted JSON when --json flag is present, and collect remainder args."""

    def error(self, message: str) -> NoReturn:
        if "--json" in sys.argv:
            err_payload = {
                "status": "error",
                "error": {
                    "code": "USAGE_ERROR",
                    "message": message,
                    "remediation": "Review 'bg3 --help' or 'bg3 <cmd> --help' for correct argument syntax.",
                },
            }
            print(json.dumps(err_payload, indent=2))
            sys.exit(ExitCode.USAGE)
        super().error(message)

    def parse_args(self, args: Optional[List[str]] = None, namespace: Optional[argparse.Namespace] = None) -> argparse.Namespace:  # type: ignore[override]
        res, argv = self.parse_known_args(args, namespace)
        raw_tokens = sys.argv[1:] if args is None else list(args)
        cmd = str(getattr(res, "command", "") or "")
        sub = str(getattr(res, "subcommand", "") or "")
        if cmd == "mod" and sub == "scaffold" and "scaffold" in raw_tokens:
            sc_idx = raw_tokens.index("scaffold")
            if sc_idx + 1 < len(raw_tokens) and not raw_tokens[sc_idx + 1].startswith("-"):
                sub = f"scaffold {raw_tokens[sc_idx + 1]}"
                res.subcommand = sub
        res._raw_tokens = raw_tokens
        res.remainder_args = argv
        return res


# Canonical registry mapping (group, subcmd) -> CommandSpec
COMMAND_REGISTRY: Dict[Tuple[str, str], CommandSpec] = {
    # mod group
    ("mod", "create"): CommandSpec("bg3_authoring.create_mod_scaffold", "Create a new mod project scaffold with meta.lsx, localization, and folder structure", "authoring", "bg3_authoring"),
    ("mod", "scaffold"): CommandSpec("bg3_authoring.scaffold_asset", "Scaffold mod asset definitions (class, feat, spell-list, etc.)", "authoring", "bg3_authoring"),
    ("mod", "validate"): CommandSpec("bg3_authoring.diagnostics.validate_mod", "Run static validation audits on mod assets, XML syntax, and directory layout", "diagnostics", "bg3_authoring"),
    ("mod", "conflict"): CommandSpec("bg3_core.check_mod_conflicts", "Detect potential stat, progression, or root template collisions across mods", "diagnostics"),
    ("mod", "add-dependency"): CommandSpec("bg3_authoring.add_mod_dependency", "Add a dependency module UUID and metadata to a target mod's meta.lsx", "authoring", "bg3_authoring"),
    ("mod", "bump-version"): CommandSpec("bg3_core.bump_mod_version", "Bump or set the 64-bit integer Version64 in a mod's meta.lsx", "management"),
    ("mod", "pack"): CommandSpec("bg3_authoring.packaging.pack_mod_pak", "Build a distributable LSPK package (.pak) from raw mod files", "packaging", "bg3_authoring"),
    ("mod", "sync-loca"): CommandSpec("bg3_authoring.diagnostics.sync_localization", "Synchronize string handles across XML files and compile .loca binaries", "diagnostics", "bg3_authoring"),
    ("mod", "sync-game"): CommandSpec("bg3_authoring.packaging.sync_game_data", "Synchronize custom mod files into the Baldur's Gate 3 Data directory", "packaging", "bg3_authoring"),
    ("mod", "patch"): CommandSpec("bg3_authoring.generate_compat_patch", "Generate compatibility patches between conflicting mods", "authoring", "bg3_authoring"),
    ("mod", "diagnose-logs"): CommandSpec("bg3_authoring.diagnostics.diagnose_toolkit_logs", "Inspect and triage Baldur's Gate 3 Toolkit messages.log runtime errors", "diagnostics", "bg3_authoring"),
    ("mod", "inspect-save"): CommandSpec("bg3_core.save_inspector", "Inspect mod dependencies in a save game (.lsv)", "diagnostics"),
    ("mod", "inject-treasure"): CommandSpec("bg3_authoring.inject_treasure_table", "Inject modded items into standard world containers and vendor inventories", "authoring", "bg3_authoring"),
    ("mod", "render-desc"): CommandSpec("bg3_core.render_modio_description", "Render mod README.md to HTML for mod.io description", "management"),
    # loadorder group
    ("loadorder", "list"): CommandSpec("bg3_core.manage_load_order", "Display active mod load order from modsettings.lsx", "management"),
    ("loadorder", "sync"): CommandSpec("bg3_core.manage_load_order", "Synchronize local mods into active load order profile", "management"),
    ("loadorder", "clean"): CommandSpec("bg3_core.manage_load_order", "Clean invalid or missing mods from load order profile", "management"),
    ("loadorder", "enable"): CommandSpec("bg3_core.manage_load_order", "Enable a mod in the active load order profile", "management"),
    ("loadorder", "disable"): CommandSpec("bg3_core.manage_load_order", "Disable a mod from active load order profile", "management"),
    ("loadorder", "validate"): CommandSpec("bg3_core.manage_load_order", "Validate current load order rules and core module positions", "management"),
    ("loadorder", "auto-sort"): CommandSpec("bg3_core.manage_load_order", "Topologically auto-sort active mods based on dependencies", "management"),
    ("loadorder", "isolate"): CommandSpec("bg3_core.manage_load_order", "Clean-room isolation: disable all other mods except dependencies", "management"),
    ("loadorder", "restore"): CommandSpec("bg3_core.manage_load_order", "Restore quarantined mods from Mods_Disabled/ back to active Mods", "management"),
    ("loadorder", "dedup"): CommandSpec("bg3_core.manage_load_order", "Deduplicate installed .pak files in AppData Mods", "management"),
    # modio group
    ("modio", "search"): CommandSpec("bg3_core.modio_search", "Search mod.io community catalog with platform and tag filters", "library"),
    ("modio", "sync"): CommandSpec("bg3_core.modio_sync", "Sync subscribed mods from mod.io into local library", "library"),
    ("modio", "extract"): CommandSpec("bg3_core.modio_extract", "Unpack mod.io .pak archive and generate documentation spec", "library"),
    ("modio", "update"): CommandSpec("bg3_core.modio_update", "Check for upstream updates to cataloged community mods", "library"),
    ("modio", "update-metadata"): CommandSpec("bg3_core.modio_update_metadata", "Update mod.io storefront profile metadata and tags", "library"),
    ("modio", "create-collection"): CommandSpec("bg3_core.modio_create_collection", "Create or update a public mod.io collection from library.md", "library"),
    ("modio", "purge"): CommandSpec("bg3_core.purge_library", "Safely purge downloaded mods and catalog documentation", "library"),
    ("modio", "catalog"): CommandSpec("bg3_core.update_library_catalog", "Update master community mod catalog markdown documentation", "library"),
    ("modio", "update-catalog"): CommandSpec("bg3_core.update_library_catalog", "Update master community mod catalog markdown documentation", "library"),
    # save group
    ("save", "list"): CommandSpec("bg3_core.manage_saves", "Discover and list BG3 save games across Proton/WSL/Windows", "diagnostics"),
    ("save", "inspect"): CommandSpec("bg3_core.manage_saves", "Audit save game dependencies against active modsettings.lsx", "diagnostics"),
    ("save", "backup"): CommandSpec("bg3_core.manage_saves", "Create timestamped zip backup of save game folders", "management"),
    ("save", "purge"): CommandSpec("bg3_core.manage_saves", "Safely purge old save games with configurable retention", "management"),
    ("save", "clean-missing"): CommandSpec("bg3_core.manage_saves", "Prune missing mod UUIDs from save game meta.lsf to rescue save", "diagnostics"),
    # build group
    ("build", "simulate"): CommandSpec("bg3_theorycraft.simulate_build_synergy", "Calculate Level 20 multiclass spell slots and Turn 1 DPR burst sequence", "theorycrafting", "bg3_theorycraft"),
    ("build", "sim"): CommandSpec("bg3_theorycraft.simulate_build_synergy", "Calculate Level 20 multiclass spell slots and Turn 1 DPR burst sequence", "theorycrafting", "bg3_theorycraft"),
    # tools group
    ("tools", "list"): CommandSpec("bg3_core.tools", "List all registered tools in the studio discovery catalog", "management"),
    ("tools", "search"): CommandSpec("bg3_core.tools", "Search registered tools by intent keywords or category", "management"),
    ("tools", "info"): CommandSpec("bg3_core.tools", "Display detailed help and argument schemas for a specific tool", "management"),
    ("tools", "verify"): CommandSpec("bg3_core.tools", "Validate tool availability and verify command health across studio", "management"),
    # env group
    ("env", "check"): CommandSpec("bg3_core.setup_environment", "Check environment configuration and XDG directories", "management"),
    ("env", "paths"): CommandSpec("bg3_core.cli", "Display standard XDG base directory paths", "management"),
    ("env", "setup"): CommandSpec("bg3_core.setup_environment", "Run interactive setup wizard for BG3 Mod Studio environment", "management"),
}

# Scaffold asset types forwarded to bg3_authoring.scaffold_asset
SCAFFOLD_ASSETS = [
    "class",
    "progression",
    "feat",
    "action-resource",
    "spell-list",
    "level-map",
    "default-values",
    "stat",
    "root-template",
    "icon-uvs",
    "race",
    "origin",
    "appearance",
    "appearance-visual",
    "tag",
]

for asset in SCAFFOLD_ASSETS:
    spec = CommandSpec(
        "bg3_authoring.scaffold_asset",
        f"Scaffold {asset} definition LSX/XML assets",
        "authoring",
        "bg3_authoring",
    )
    COMMAND_REGISTRY[("scaffold", asset)] = spec
    COMMAND_REGISTRY[("mod", f"scaffold {asset}")] = spec

# Direct top-level command specifications
DIRECT_COMMANDS: Dict[str, CommandSpec] = {
    "query": CommandSpec("bg3_core.query_mod_database", "Query indexed catalog equipment, passives, spells, and boosts", "theorycrafting"),
    "conflict": CommandSpec("bg3_core.check_mod_conflicts", "Detect potential stat, progression, or root template collisions across mods", "diagnostics"),
    "sim": CommandSpec("bg3_theorycraft.simulate_build_synergy", "Simulate Level 20 character progression and DPR burst sequence", "theorycrafting", "bg3_theorycraft"),
}

DESTRUCTIVE_CONFIRMATIONS = {
    ("loadorder", "sync"): "Sync mod state into active load order profile?",
    ("loadorder", "clean"): "Clean invalid mods from load order profile?",
    ("loadorder", "isolate"): "Isolate mod in load order (all unrelated mods will be disabled in modsettings.lsx)?",
    ("loadorder", "restore"): "Restore quarantined mods back to active Mods directory?",
    ("modio", "purge"): "Purge local mod.io library cache and downloads?",
    ("save", "purge"): "Purge old save games?",
}


def resolve_module_fallback(script_target: Path) -> Optional[str]:
    """Derive fully qualified python module name from a target file path."""
    parts = list(script_target.parts)
    for pkg in ("bg3_authoring", "bg3_core", "bg3_theorycraft"):
        if pkg in parts:
            idx = parts.index(pkg)
            mod_parts = list(parts[idx:])
            if mod_parts[-1].endswith(".py"):
                mod_parts[-1] = mod_parts[-1][:-3]
            return ".".join(mod_parts)
    return None


def _find_module_file(mod_name: str) -> Optional[Path]:
    """Find absolute file path for a given module name."""
    try:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, "__file__") and mod.__file__:
            return Path(mod.__file__).resolve()
    except Exception:
        pass
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    pkg_dir = mod_name.split(".")[0].replace("_", "-")
    rel_path = Path("packages") / pkg_dir / Path(*mod_name.split(".")).with_suffix(".py")
    candidate = repo_root / rel_path
    if candidate.is_file():
        return candidate
    return None


def _add_scaffold_subparsers(sub_sp: Any) -> None:
    """Add structured subparsers for asset scaffolding types."""
    # Attempt to load rich schema definitions from scaffold_asset if available
    target_parser = None
    try:
        from bg3_authoring.scaffold_asset import build_parser as build_scaffold_p
        target_parser = build_scaffold_p()
    except Exception:
        pass

    target_actions: Dict[str, Any] = {}
    if target_parser is not None:
        for act in target_parser._actions:
            if isinstance(act, argparse._SubParsersAction) and act.choices:
                target_actions = act.choices
                break

    for asset in SCAFFOLD_ASSETS:
        spec = COMMAND_REGISTRY.get(("scaffold", asset))
        help_text = spec.help if spec else f"Scaffold {asset} definition"
        if asset in target_actions:
            # Mount subparser and duplicate argument definitions for transparent help trees
            src_p = target_actions[asset]
            sub_p = sub_sp.add_parser(asset, help=help_text, description=src_p.description)
            for action in src_p._actions:
                if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
                    continue
                opts = list(action.option_strings)
                kwargs: Dict[str, Any] = {
                    "help": action.help,
                    "default": action.default,
                }
                if action.type is not None:
                    kwargs["type"] = action.type
                if action.choices:
                    kwargs["choices"] = action.choices
                if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
                    kwargs["action"] = "store_true" if isinstance(action, argparse._StoreTrueAction) else "store_false"
                elif action.nargs is not None:
                    kwargs["nargs"] = action.nargs

                if opts:
                    sub_p.add_argument(*opts, **kwargs)
                elif action.dest:
                    kwargs["nargs"] = action.nargs if action.nargs is not None else "?"
                    sub_p.add_argument(action.dest, **kwargs)
        else:
            sub_p = sub_sp.add_parser(asset, help=help_text)
            sub_p.add_argument("--mod", help="Target mod name or path in my_mods/")
            sub_p.add_argument("--name", help="Internal asset name")
            sub_p.add_argument("--dry-run", action="store_true", help="Preview without writing files")
            sub_p.add_argument("--json", action="store_true", help="Format output as JSON")


def build_parser() -> JsonCompliantArgumentParser:
    """Build structured command tree for in-process execution, CLI help, and introspection."""
    parser = JsonCompliantArgumentParser(
        prog="bg3",
        description="Baldur's Gate 3 Mod Studio & Mod.io Automation Workspace",
    )
    parser.add_argument("--json", action="store_true", help="Format all output as machine-readable JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose diagnostics on stderr")
    parser.add_argument("--config", help="Custom environment configuration file path")

    subparsers = parser.add_subparsers(dest="command", parser_class=JsonCompliantArgumentParser)

    # 1. Direct top-level commands
    # query
    p_query = subparsers.add_parser("query", help=DIRECT_COMMANDS["query"].help)
    p_query.add_argument("query", nargs="?", default=None, help="General search term across name, desc, and boosts")
    p_query.add_argument("--name", help="Exact or substring match for item/spell/passive name")
    p_query.add_argument("--type", help="Filter by data type (Armor, Weapon, Spell, Passive, StatusData)")
    p_query.add_argument("--limit", type=int, default=25, help="Maximum number of results to display")
    p_query.add_argument("--format", default="table", choices=["table", "json", "compact"], help="Output presentation format")
    p_query.add_argument("--exact", action="store_true", help="Require exact case-insensitive match")

    # conflict
    p_conflict = subparsers.add_parser("conflict", help=DIRECT_COMMANDS["conflict"].help)
    p_conflict.add_argument("candidate", nargs="?", default=None, help="Candidate mod directory or .pak file")
    p_conflict.add_argument("--candidate", dest="candidate_flag", help="Candidate mod directory or .pak file")
    p_conflict.add_argument("--mod1", help="First mod directory or .pak file to compare")
    p_conflict.add_argument("--mod2", help="Second mod directory or .pak file to compare")
    p_conflict.add_argument("--all", action="store_true", help="Check for conflicts across all installed mods")

    # sim
    p_sim = subparsers.add_parser("sim", help=DIRECT_COMMANDS["sim"].help)
    p_sim.add_argument("--classes", help="Multiclass specification (e.g. 'Paladin=5,Warlock=5')")
    p_sim.add_argument("--level", type=int, default=20, help="Total character level cap")
    p_sim.add_argument("--dry-run", action="store_true", help="Simulate progression without saving")

    # 2. Group commands
    # mod group
    p_mod = subparsers.add_parser("mod", help="Mod creation, diagnostics, packaging, and asset authoring")
    mod_sp = p_mod.add_subparsers(dest="subcommand", parser_class=JsonCompliantArgumentParser)

    p_mod_create = mod_sp.add_parser("create", help=COMMAND_REGISTRY[("mod", "create")].help)
    p_mod_create.add_argument("name", nargs="?", default=None, help="Target mod project name")
    p_mod_create.add_argument("--name", dest="name_flag", help="Target mod project name")
    p_mod_create.add_argument("--author", default="Developer", help="Mod author name")
    p_mod_create.add_argument("--description", default="", help="Mod description")
    p_mod_create.add_argument("--version", default="1.0.0.0", help="Initial version string")
    p_mod_create.add_argument("--dest", help="Destination workspace directory")
    p_mod_create.add_argument("--dry-run", action="store_true", help="Preview scaffold layout without creating files")

    p_mod_scaffold = mod_sp.add_parser("scaffold", help=COMMAND_REGISTRY[("mod", "scaffold")].help)
    mod_scaffold_sp = p_mod_scaffold.add_subparsers(dest="asset_type", parser_class=JsonCompliantArgumentParser)
    _add_scaffold_subparsers(mod_scaffold_sp)

    p_mod_val = mod_sp.add_parser("validate", help=COMMAND_REGISTRY[("mod", "validate")].help)
    p_mod_val.add_argument("mod", nargs="?", default=None, help="Target mod directory or .pak")
    p_mod_val.add_argument("--mod", dest="mod_flag", help="Target mod directory or .pak")
    p_mod_val.add_argument("--all", action="store_true", help="Validate all mods in workspace")
    p_mod_val.add_argument("--fix", action="store_true", help="Automatically correct safe repairable issues")
    p_mod_val.add_argument("--dry-run", action="store_true", help="Preview fixes without modifying files")

    p_mod_conf = mod_sp.add_parser("conflict", help=COMMAND_REGISTRY[("mod", "conflict")].help)
    p_mod_conf.add_argument("candidate", nargs="?", default=None, help="Candidate mod directory or .pak file")
    p_mod_conf.add_argument("--candidate", dest="candidate_flag", help="Candidate mod directory or .pak file")
    p_mod_conf.add_argument("--mod1", help="First mod directory or .pak file to compare")
    p_mod_conf.add_argument("--mod2", help="Second mod directory or .pak file to compare")
    p_mod_conf.add_argument("--all", action="store_true", help="Check for conflicts across all installed mods")

    p_mod_dep = mod_sp.add_parser("add-dependency", help=COMMAND_REGISTRY[("mod", "add-dependency")].help)
    p_mod_dep.add_argument("mod", nargs="?", default=None, help="Target mod directory")
    p_mod_dep.add_argument("--mod", dest="mod_flag", help="Target mod directory")
    p_mod_dep.add_argument("--dep-uuid", help="Explicit UUID of the dependency module")
    p_mod_dep.add_argument("--dep-name", help="Human-readable name of dependency")
    p_mod_dep.add_argument("--dep-version", help="Minimum required Version64 string")
    p_mod_dep.add_argument("--dep-folder", help="Folder attribute for dependency")
    p_mod_dep.add_argument("--md5", help="MD5 hash string of dependency package")
    p_mod_dep.add_argument("--dry-run", action="store_true", help="Preview meta.lsx modification")

    p_mod_bump = mod_sp.add_parser("bump-version", help=COMMAND_REGISTRY[("mod", "bump-version")].help)
    p_mod_bump.add_argument("mod", nargs="?", default=None, help="Target mod directory or meta.lsx path")
    p_mod_bump.add_argument("--mod", dest="mod_flag", help="Target mod directory or meta.lsx path")
    p_mod_bump.add_argument("--type", choices=["major", "minor", "patch", "build"], default="patch", help="Version component to increment")
    p_mod_bump.add_argument("--version", help="Explicit 4-part version string to set")
    p_mod_bump.add_argument("--dry-run", action="store_true", help="Preview version change without writing")

    p_mod_pack = mod_sp.add_parser("pack", help=COMMAND_REGISTRY[("mod", "pack")].help)
    p_mod_pack.add_argument("mod", nargs="?", default=None, help="Target mod directory in my_mods/")
    p_mod_pack.add_argument("--mod", dest="mod_flag", help="Target mod directory in my_mods/")
    p_mod_pack.add_argument("--dest", help="Destination path for built .pak file")
    p_mod_pack.add_argument("--compress", action="store_true", default=True, help="Compress archive blocks with LZ4")
    p_mod_pack.add_argument("--dry-run", action="store_true", help="Calculate manifest without packing")

    p_mod_loca = mod_sp.add_parser("sync-loca", help=COMMAND_REGISTRY[("mod", "sync-loca")].help)
    p_mod_loca.add_argument("mod", nargs="?", default=None, help="Target mod directory")
    p_mod_loca.add_argument("--mod", dest="mod_flag", help="Target mod directory")
    p_mod_loca.add_argument("--dry-run", action="store_true", help="Preview handle generation")

    p_mod_sync_game = mod_sp.add_parser("sync-game", help=COMMAND_REGISTRY[("mod", "sync-game")].help)
    p_mod_sync_game.add_argument("--mod", help="Specific mod to synchronize")
    p_mod_sync_game.add_argument("--clean", action="store_true", help="Clean legacy mod files before syncing")
    p_mod_sync_game.add_argument("--dry-run", action="store_true", help="Preview sync file operations")

    p_mod_patch = mod_sp.add_parser("patch", help=COMMAND_REGISTRY[("mod", "patch")].help)
    p_mod_patch.add_argument("mod1", nargs="?", default=None, help="Base mod directory or .pak")
    p_mod_patch.add_argument("mod2", nargs="?", default=None, help="Overriding mod directory or .pak")
    p_mod_patch.add_argument("--output", help="Target directory for generated patch mod")
    p_mod_patch.add_argument("--dry-run", action="store_true", help="Preview patch changes")

    p_mod_logs = mod_sp.add_parser("diagnose-logs", help=COMMAND_REGISTRY[("mod", "diagnose-logs")].help)
    p_mod_logs.add_argument("--path", help="Explicit path to messages.log")
    p_mod_logs.add_argument("--purge", action="store_true", help="Truncate or clear messages.log")
    p_mod_logs.add_argument("--dry-run", action="store_true", help="Preview log diagnostics")

    p_mod_ins_save = mod_sp.add_parser("inspect-save", help=COMMAND_REGISTRY[("mod", "inspect-save")].help)
    p_mod_ins_save.add_argument("save", nargs="?", default=None, help="Path to save file (.lsv)")
    p_mod_ins_save.add_argument("--save", dest="save_flag", help="Path to save file (.lsv)")

    p_mod_treasure = mod_sp.add_parser("inject-treasure", help=COMMAND_REGISTRY[("mod", "inject-treasure")].help)
    p_mod_treasure.add_argument("mod", nargs="?", default=None, help="Target mod directory")
    p_mod_treasure.add_argument("--mod", dest="mod_flag", help="Target mod directory")
    p_mod_treasure.add_argument("--table", help="Target vanilla treasure table name")
    p_mod_treasure.add_argument("--item", help="Mod item stat identifier to inject")
    p_mod_treasure.add_argument("--drop-chance", type=float, default=1.0, help="Drop probability")
    p_mod_treasure.add_argument("--dry-run", action="store_true", help="Preview injection")

    p_mod_desc = mod_sp.add_parser("render-desc", help=COMMAND_REGISTRY[("mod", "render-desc")].help)
    p_mod_desc.add_argument("mod", nargs="?", default=None, help="Target mod directory containing README.md")
    p_mod_desc.add_argument("--mod", dest="mod_flag", help="Target mod directory containing README.md")
    p_mod_desc.add_argument("--output", help="Output file path for rendered HTML")

    # scaffold group (top-level alias for mod scaffold)
    p_scaffold = subparsers.add_parser("scaffold", help="Scaffold mod asset definitions (class, feat, spell-list, etc.)")
    scaffold_sp = p_scaffold.add_subparsers(dest="asset_type", parser_class=JsonCompliantArgumentParser)
    _add_scaffold_subparsers(scaffold_sp)

    # loadorder group
    p_lo = subparsers.add_parser("loadorder", help="Mod load order profile inspection, synchronization, and sorting")
    lo_sp = p_lo.add_subparsers(dest="subcommand", parser_class=JsonCompliantArgumentParser)

    p_lo_list = lo_sp.add_parser("list", help=COMMAND_REGISTRY[("loadorder", "list")].help)
    p_lo_list.add_argument("--path", help="Explicit path to modsettings.lsx")

    p_lo_sync = lo_sp.add_parser("sync", help=COMMAND_REGISTRY[("loadorder", "sync")].help)
    p_lo_sync.add_argument("--path", help="Explicit path to modsettings.lsx")
    p_lo_sync.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation prompt")
    p_lo_sync.add_argument("--dry-run", action="store_true", help="Preview changes without modifying modsettings.lsx")

    p_lo_clean = lo_sp.add_parser("clean", help=COMMAND_REGISTRY[("loadorder", "clean")].help)
    p_lo_clean.add_argument("--path", help="Explicit path to modsettings.lsx")
    p_lo_clean.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation prompt")
    p_lo_clean.add_argument("--dry-run", action="store_true", help="Preview cleaning without writing")

    p_lo_en = lo_sp.add_parser("enable", help=COMMAND_REGISTRY[("loadorder", "enable")].help)
    p_lo_en.add_argument("mod", nargs="?", default=None, help="Mod name, slug, or UUID to enable")
    p_lo_en.add_argument("--enable", dest="enable_flag", help="Mod name, slug, or UUID to enable")
    p_lo_en.add_argument("--order", type=int, help="Target load order position (1-based index)")
    p_lo_en.add_argument("--with-deps", action="store_true", default=True, help="Enable declared dependencies automatically")
    p_lo_en.add_argument("--no-deps", dest="with_deps", action="store_false", help="Do not automatically enable dependencies")
    p_lo_en.add_argument("--test-dep", action="append", default=[], help="Temporary test dependency to activate ahead of mod")
    p_lo_en.add_argument("--isolate", action="store_true", help="Clean-room isolation: disable all other mods except base game and dependencies")
    p_lo_en.add_argument("--quarantine", action="store_true", help="Physically quarantine unrelated .pak files to Mods_Disabled/")
    p_lo_en.add_argument("--dry-run", action="store_true", help="Preview enabling without writing")

    p_lo_dis = lo_sp.add_parser("disable", help=COMMAND_REGISTRY[("loadorder", "disable")].help)
    p_lo_dis.add_argument("mod", nargs="?", default=None, help="Mod name, slug, or UUID to disable")
    p_lo_dis.add_argument("--disable", dest="disable_flag", help="Mod name, slug, or UUID to disable")
    p_lo_dis.add_argument("--dry-run", action="store_true", help="Preview disabling without writing")

    p_lo_val = lo_sp.add_parser("validate", help=COMMAND_REGISTRY[("loadorder", "validate")].help)
    p_lo_val.add_argument("--path", help="Explicit path to modsettings.lsx")

    p_lo_sort = lo_sp.add_parser("auto-sort", help=COMMAND_REGISTRY[("loadorder", "auto-sort")].help)
    p_lo_sort.add_argument("--path", help="Explicit path to modsettings.lsx")
    p_lo_sort.add_argument("--dry-run", action="store_true", help="Preview topological sort")

    p_lo_iso = lo_sp.add_parser("isolate", help=COMMAND_REGISTRY[("loadorder", "isolate")].help, description="Clean-room isolation: disable all other mods except dependencies in modsettings.lsx")
    p_lo_iso.add_argument("mod", nargs="?", default=None, help="Mod name, slug, or UUID to isolate")
    p_lo_iso.add_argument("--quarantine", action="store_true", help="Physically quarantine unrelated .pak files to Mods_Disabled/")
    p_lo_iso.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation prompt")
    p_lo_iso.add_argument("--dry-run", action="store_true", help="Preview isolation without modifying modsettings.lsx")

    p_lo_rest = lo_sp.add_parser("restore", help=COMMAND_REGISTRY[("loadorder", "restore")].help, description="Restore quarantined mods from Mods_Disabled/ back to active Mods directory")
    p_lo_rest.add_argument("--path", help="Explicit path to modsettings.lsx")
    p_lo_rest.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation prompt")
    p_lo_rest.add_argument("--dry-run", action="store_true", help="Preview restore operations")

    p_lo_dedup = lo_sp.add_parser("dedup", help=COMMAND_REGISTRY[("loadorder", "dedup")].help, description="Deduplicate installed .pak files in AppData Mods")
    p_lo_dedup.add_argument("--path", help="Explicit path to modsettings.lsx")
    p_lo_dedup.add_argument("--dry-run", action="store_true", help="Preview deduplication")

    # modio group
    p_modio = subparsers.add_parser("modio", help="Mod.io community library integration and catalog updates")
    modio_sp = p_modio.add_subparsers(dest="subcommand", parser_class=JsonCompliantArgumentParser)

    p_modio_search = modio_sp.add_parser("search", help=COMMAND_REGISTRY[("modio", "search")].help)
    p_modio_search.add_argument("query", nargs="?", default=None, help="Search query string")
    p_modio_search.add_argument("--query", dest="query_flag", help="Search query string")
    p_modio_search.add_argument("--tag", action="append", default=[], help="Filter by tag")
    p_modio_search.add_argument("--limit", type=int, default=20, help="Maximum search results")
    p_modio_search.add_argument("--sort", default="popular", help="Sorting criteria")

    p_modio_sync = modio_sp.add_parser("sync", help=COMMAND_REGISTRY[("modio", "sync")].help)
    p_modio_sync.add_argument("--prune", action="store_true", help="Prune untracked mods from local library")
    p_modio_sync.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation prompt")
    p_modio_sync.add_argument("--dry-run", action="store_true", help="Preview sync operations")

    p_modio_ext = modio_sp.add_parser("extract", help=COMMAND_REGISTRY[("modio", "extract")].help)
    p_modio_ext.add_argument("pak", nargs="?", default=None, help="Path to .pak file to extract")
    p_modio_ext.add_argument("--pak", dest="pak_flag", help="Path to .pak file to extract")
    p_modio_ext.add_argument("--output", help="Target destination directory for extracted mod")

    p_modio_up = modio_sp.add_parser("update", help=COMMAND_REGISTRY[("modio", "update")].help)
    p_modio_up.add_argument("--all", action="store_true", help="Check updates for all subscribed mods")
    p_modio_up.add_argument("--dry-run", action="store_true", help="Preview updates")

    p_modio_meta = modio_sp.add_parser("update-metadata", help=COMMAND_REGISTRY[("modio", "update-metadata")].help)
    p_modio_meta.add_argument("mod", nargs="?", default=None, help="Target mod directory or profile")
    p_modio_meta.add_argument("--mod", dest="mod_flag", help="Target mod directory or profile")
    p_modio_meta.add_argument("--tags", help="Comma-separated tag list")
    p_modio_meta.add_argument("--name", help="Updated mod title")
    p_modio_meta.add_argument("--summary", help="Updated short summary")
    p_modio_meta.add_argument("--dry-run", action="store_true", help="Preview metadata changes")

    p_modio_col = modio_sp.add_parser("create-collection", help=COMMAND_REGISTRY[("modio", "create-collection")].help)
    p_modio_col.add_argument("--title", help="Collection title")
    p_modio_col.add_argument("--summary", help="Collection summary")
    p_modio_col.add_argument("--visibility", default="public", choices=["public", "unlisted", "private"], help="Collection visibility")
    p_modio_col.add_argument("--dry-run", action="store_true", help="Preview collection payload")

    p_modio_purge = modio_sp.add_parser("purge", help=COMMAND_REGISTRY[("modio", "purge")].help)
    p_modio_purge.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation prompt")
    p_modio_purge.add_argument("--dry-run", action="store_true", help="Preview library purge")

    p_modio_cat = modio_sp.add_parser("catalog", help=COMMAND_REGISTRY[("modio", "catalog")].help)
    p_modio_cat.add_argument("--output", help="Output path for updated catalog markdown")

    p_modio_up_cat = modio_sp.add_parser("update-catalog", help=COMMAND_REGISTRY[("modio", "update-catalog")].help)
    p_modio_up_cat.add_argument("--output", help="Output path for updated catalog markdown")

    # save group
    p_save = subparsers.add_parser("save", help="Save game dependency inspection, backup, and recovery")
    save_sp = p_save.add_subparsers(dest="subcommand", parser_class=JsonCompliantArgumentParser)

    save_sp.add_parser("list", help=COMMAND_REGISTRY[("save", "list")].help)

    p_save_ins = save_sp.add_parser("inspect", help=COMMAND_REGISTRY[("save", "inspect")].help)
    p_save_ins.add_argument("save", nargs="?", default=None, help="Save game file or folder to inspect")
    p_save_ins.add_argument("--save", dest="save_flag", help="Save game file or folder to inspect")

    p_save_bak = save_sp.add_parser("backup", help=COMMAND_REGISTRY[("save", "backup")].help)
    p_save_bak.add_argument("--dest", help="Destination folder for timestamped zip backup")

    p_save_purge = save_sp.add_parser("purge", help=COMMAND_REGISTRY[("save", "purge")].help)
    p_save_purge.add_argument("--retention", type=int, default=10, help="Number of newest saves to retain")
    p_save_purge.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation prompt")
    p_save_purge.add_argument("--dry-run", action="store_true", help="Preview purge operations")

    p_save_clean = save_sp.add_parser("clean-missing", help=COMMAND_REGISTRY[("save", "clean-missing")].help)
    p_save_clean.add_argument("save", nargs="?", default=None, help="Save game file (.lsv) to rescue")
    p_save_clean.add_argument("--save", dest="save_flag", help="Save game file (.lsv) to rescue")
    p_save_clean.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation prompt")
    p_save_clean.add_argument("--dry-run", action="store_true", help="Preview rescue operations")

    # build group
    p_build = subparsers.add_parser("build", help="Character theorycrafting and Level 20 DPR burst simulation")
    build_sp = p_build.add_subparsers(dest="subcommand", parser_class=JsonCompliantArgumentParser)

    p_build_sim = build_sp.add_parser("simulate", help=COMMAND_REGISTRY[("build", "simulate")].help)
    p_build_sim.add_argument("--classes", help="Multiclass distribution specification (e.g. 'Fighter=12,Rogue=4')")
    p_build_sim.add_argument("--level", type=int, default=20, help="Total character level cap")
    p_build_sim.add_argument("--dry-run", action="store_true", help="Simulate progression without writing")

    p_build_sim2 = build_sp.add_parser("sim", help=COMMAND_REGISTRY[("build", "sim")].help)
    p_build_sim2.add_argument("--classes", help="Multiclass distribution specification (e.g. 'Fighter=12,Rogue=4')")
    p_build_sim2.add_argument("--level", type=int, default=20, help="Total character level cap")
    p_build_sim2.add_argument("--dry-run", action="store_true", help="Simulate progression without writing")

    # tools group
    p_tools = subparsers.add_parser("tools", help="Studio CLI command registry and discovery catalog")
    tools_sp = p_tools.add_subparsers(dest="subcommand", parser_class=JsonCompliantArgumentParser)

    tools_sp.add_parser("list", help=COMMAND_REGISTRY[("tools", "list")].help)

    p_tools_search = tools_sp.add_parser("search", help=COMMAND_REGISTRY[("tools", "search")].help)
    p_tools_search.add_argument("query", nargs="?", default=None, help="Search intent keyword or phrase")
    p_tools_search.add_argument("--category", help="Filter by tool category")

    p_tools_info = tools_sp.add_parser("info", help=COMMAND_REGISTRY[("tools", "info")].help)
    p_tools_info.add_argument("tool", nargs="?", default=None, help="Target command name or alias")
    p_tools_info.add_argument("--tool", dest="tool_flag", help="Target command name or alias")

    p_tools_verify = tools_sp.add_parser("verify", help=COMMAND_REGISTRY[("tools", "verify")].help)
    p_tools_verify.add_argument("--audit-skills", action="store_true", help="Audit agent skills in .agents/skills/")

    # env group
    p_env = subparsers.add_parser("env", help="Environment setup, path diagnostics, and XDG directory status")
    env_sp = p_env.add_subparsers(dest="subcommand", parser_class=JsonCompliantArgumentParser)

    env_sp.add_parser("check", help=COMMAND_REGISTRY[("env", "check")].help)
    env_sp.add_parser("paths", help=COMMAND_REGISTRY[("env", "paths")].help)
    env_sp.add_parser("setup", help=COMMAND_REGISTRY[("env", "setup")].help)

    return parser


def _execute_env_paths(json_mode: bool, emitter: OutputEmitter) -> int:
    """In-process handler for bg3 env paths."""
    from bg3_core.env_paths import (
        get_xdg_cache_home,
        get_xdg_config_home,
        get_xdg_data_home,
        get_xdg_state_home,
    )
    cfg = get_xdg_config_home()
    cache = get_xdg_cache_home()
    data = get_xdg_data_home()
    state = get_xdg_state_home()
    paths_data = {
        "XDG_CONFIG_HOME": {"path": str(cfg), "exists": cfg.exists()},
        "XDG_CACHE_HOME": {"path": str(cache), "exists": cache.exists()},
        "XDG_DATA_HOME": {"path": str(data), "exists": data.exists()},
        "XDG_STATE_HOME": {"path": str(state), "exists": state.exists()},
    }
    if json_mode:
        print(json.dumps(paths_data, indent=2))
    else:
        color = emitter.color
        print(f"\n{color.bold('=== XDG Base Directory Paths ===')}")
        for var, info in paths_data.items():
            status = color.green("[exists]") if info["exists"] else color.yellow("[not created]")
            print(f"{color.bold(f'{var:17}')}: {info['path']} {status}")
        print("")
    return ExitCode.OK


def _invoke_in_process(target_module_name: str, target_args: List[str]) -> int:
    """Invoke target module main entrypoint directly in-process, capturing return codes cleanly."""
    mod = importlib.import_module(target_module_name)
    main_func = getattr(mod, "main", None)
    if main_func is None or not callable(main_func):
        raise AttributeError(f"Module '{target_module_name}' does not expose a callable main() entrypoint.")

    sig = inspect.signature(main_func)
    old_argv = list(sys.argv)
    try:
        sys.argv = [target_module_name] + target_args
        if len(sig.parameters) > 0:
            ret = main_func(target_args)
        else:
            ret = main_func()

        if isinstance(ret, int):
            return ret
        return ExitCode.OK
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return ExitCode.OK
        if isinstance(code, int):
            return code
        return ExitCode.GENERAL_ERROR if code else ExitCode.OK
    finally:
        sys.argv = old_argv


def dispatch_command(args: Any, emitter: OutputEmitter) -> int:
    """Dispatch command to target module entrypoint via in-process execution."""
    cmd: str = str(getattr(args, "command", "") or "")
    sub: str = str(getattr(args, "subcommand", "") or "")
    asset_type: str = str(getattr(args, "asset_type", "") or "")

    if not cmd:
        raw_tokens = [a for a in sys.argv[1:] if not a.startswith("-")]
        if raw_tokens:
            cmd = raw_tokens[0]
            if len(raw_tokens) > 1:
                sub = raw_tokens[1]

    json_mode = getattr(args, "json", False) or "--json" in sys.argv
    verbose = getattr(args, "verbose", False) or "-v" in sys.argv or "--verbose" in sys.argv

    # Handle missing subcommand for multi-command groups
    if cmd in ("mod", "loadorder", "modio", "save", "scaffold", "tools", "env") and not sub and not asset_type:
        emitter.error(
            message=f"Missing required subcommand for command '{cmd}'.",
            code="MISSING_COMMAND",
            remediation=f"Run 'bg3 {cmd} --help' to inspect available subcommands.",
            exit_code=ExitCode.USAGE,
            exit_process=False,
        )
        return ExitCode.USAGE

    # Resolve target CommandSpec
    spec: Optional[CommandSpec] = None

    if cmd in DIRECT_COMMANDS:
        spec = DIRECT_COMMANDS[cmd]
    elif cmd == "scaffold" and asset_type:
        spec = COMMAND_REGISTRY.get(("scaffold", asset_type)) or CommandSpec("bg3_authoring.scaffold_asset", f"Scaffold {asset_type}", "authoring", "bg3_authoring")
    elif cmd == "mod" and sub == "scaffold" and asset_type:
        spec = COMMAND_REGISTRY.get(("scaffold", asset_type)) or CommandSpec("bg3_authoring.scaffold_asset", f"Scaffold {asset_type}", "authoring", "bg3_authoring")
    elif (cmd, sub) in COMMAND_REGISTRY:
        spec = COMMAND_REGISTRY[(cmd, sub)]
    elif cmd == "build" and sub in ("sim", "simulate"):
        spec = COMMAND_REGISTRY[("build", "simulate")]

    if not spec:
        full_cmd = f"{cmd} {sub}".strip()
        emitter.error(
            message=f"Handler script not found for command '{full_cmd}'.",
            code="COMMAND_NOT_FOUND",
            exit_code=ExitCode.UNAVAILABLE,
            exit_process=False,
        )
        return ExitCode.UNAVAILABLE

    # Package requirement check (gating)
    if spec.pkg_requirement:
        pkg = spec.pkg_requirement
        is_missing = False
        if pkg in sys.modules and sys.modules[pkg] is None:
            is_missing = True
        else:
            try:
                importlib.import_module(pkg)
            except ImportError:
                is_missing = True

        if is_missing:
            full_cmd = f"bg3 {cmd} {sub or ''}".strip()
            emitter.error(
                message=f"Command '{full_cmd}' requires the '{pkg.replace('_', '-')}' package (install via 'uv pip install {pkg.replace('_', '-')}' or 'pip install \"bg3[all]\"').",
                code="PACKAGE_NOT_INSTALLED",
                exit_code=ExitCode.UNAVAILABLE,
                exit_process=False,
            )
            return ExitCode.UNAVAILABLE

    # In-process execution for env paths
    if cmd == "env" and sub == "paths":
        return _execute_env_paths(json_mode, emitter)

    # Collect raw tokens from args or sys.argv for transparent downstream flag forwarding
    raw_tokens = getattr(args, "_raw_tokens", None) if getattr(args, "_raw_tokens", None) is not None else sys.argv[1:]
    # Find start of subcommand tokens
    target_args: List[str] = []
    if cmd in DIRECT_COMMANDS:
        if cmd in raw_tokens:
            c_idx = raw_tokens.index(cmd)
            target_args = raw_tokens[c_idx + 1:]
    elif cmd == "scaffold":
        if asset_type and asset_type in raw_tokens:
            s_idx = raw_tokens.index(asset_type)
            target_args = [asset_type] + raw_tokens[s_idx + 1:]
        elif "scaffold" in raw_tokens:
            s_idx = raw_tokens.index("scaffold")
            target_args = raw_tokens[s_idx + 1:]
    elif cmd == "mod" and sub.startswith("scaffold"):
        if asset_type and asset_type in raw_tokens:
            s_idx = raw_tokens.index(asset_type)
            target_args = [asset_type] + raw_tokens[s_idx + 1:]
        elif "scaffold" in raw_tokens:
            s_idx = raw_tokens.index("scaffold")
            target_args = raw_tokens[s_idx + 1:]
    elif sub and sub in raw_tokens:
        s_idx = raw_tokens.index(sub)
        target_args = raw_tokens[s_idx + 1:]
    elif cmd in raw_tokens:
        c_idx = raw_tokens.index(cmd)
        target_args = raw_tokens[c_idx + 1:]

    is_help = any(a in target_args for a in ("-h", "--help"))

    # Argument translation for scaffold_asset
    if spec.target_module == "bg3_authoring.scaffold_asset":
        asset_name = asset_type or (sub.split()[1] if sub.startswith("scaffold ") else None)
        if asset_name and (not target_args or target_args[0] != asset_name):
            target_args = [asset_name] + target_args

    # Argument translation for save noun-verb syntax
    if cmd == "save" and sub:
        target_args = [sub] + target_args

    # Argument translation for tools noun-verb syntax
    if cmd == "tools" and sub in ("list", "search", "info", "verify"):
        if not is_help:
            target_args = [f"--{sub}"] + target_args

    # Argument translation for env check
    if cmd == "env" and sub == "check":
        target_args = ["--check"] + target_args

    # Normalize positional name parameter to --name for mod create
    if (cmd, sub) == ("mod", "create"):
        if target_args and not target_args[0].startswith("-"):
            target_args = ["--name", target_args[0]] + target_args[1:]

    # Normalize positional mod parameter to --mod for specific mod tools
    if (cmd, sub) in (("mod", "pack"), ("mod", "sync-loca"), ("mod", "bump-version"), ("mod", "render-desc")):
        if target_args and not target_args[0].startswith("-"):
            target_args = ["--mod", target_args[0]] + target_args[1:]

    # Argument translation for loadorder noun-verb syntax
    if cmd == "loadorder":
        loadorder_map = {
            "list": ["--list"],
            "sync": ["--sync"],
            "clean": ["--clean"],
            "validate": ["--validate"],
            "auto-sort": ["--auto-sort"],
            "sort": ["--auto-sort"],
            "restore": ["--restore"],
            "dedup": ["--dedup"],
        }
        if is_help:
            target_args = ["--help"]
        elif sub in loadorder_map:
            target_args = loadorder_map[sub] + target_args
        elif sub in ("enable", "activate"):
            mod = target_args[0] if target_args and not target_args[0].startswith("-") else getattr(args, "mod", None)
            rest = target_args[1:] if mod and target_args and target_args[0] == mod else target_args
            target_args = (["--enable", mod] if mod else ["--enable"]) + rest
        elif sub == "disable":
            mod = target_args[0] if target_args and not target_args[0].startswith("-") else getattr(args, "mod", None)
            rest = target_args[1:] if mod and target_args and target_args[0] == mod else target_args
            target_args = (["--disable", mod] if mod else ["--disable"]) + rest
        elif sub == "isolate":
            mod = target_args[0] if target_args and not target_args[0].startswith("-") else getattr(args, "mod", None)
            rest = target_args[1:] if mod and target_args and target_args[0] == mod else target_args
            target_args = (["--enable", mod, "--isolate"] if mod else ["--isolate"]) + rest

    # Argument translation for mod conflict / conflict
    if (cmd == "conflict" or (cmd == "mod" and sub == "conflict")) and not is_help:
        has_pos = target_args and not target_args[0].startswith("-")
        has_flag = any(a in target_args for a in ("--candidate", "--mod1", "--all"))
        cand_attr = getattr(args, "candidate", None) or getattr(args, "candidate_flag", None)
        all_attr = getattr(args, "all", False)
        if not (has_pos or has_flag or cand_attr or all_attr):
            emitter.error(
                message="bg3 conflict requires a candidate mod or --all.",
                code="INVALID_ARGUMENTS",
                exit_code=ExitCode.USAGE,
                exit_process=False,
            )
            return ExitCode.USAGE
        if has_pos:
            target_args = ["--candidate", target_args[0]] + target_args[1:]
        elif cand_attr and not has_flag:
            target_args = ["--candidate", str(cand_attr)] + target_args

    # Destructive action confirmation check
    if (cmd, sub) in DESTRUCTIVE_CONFIRMATIONS and not is_help:
        prompt_msg = DESTRUCTIVE_CONFIRMATIONS[(cmd, sub)]
        if not any(a in target_args for a in ("--dry-run", "-n", "-y", "--yes")):
            try:
                confirm_action(prompt_msg, non_interactive_yes=False, force_non_interactive=json_mode)
            except NonInteractiveConfirmationError as exc:
                emitter.error(
                    message=str(exc),
                    code="CONFIRMATION_REQUIRED",
                    remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                    exit_code=ExitCode.USAGE,
                    exit_process=False,
                )
                return ExitCode.USAGE

    if (cmd, sub) == ("modio", "sync") and "--prune" in target_args and not is_help:
        if not any(a in target_args for a in ("--dry-run", "-n", "-y", "--yes")):
            try:
                confirm_action("Prune untracked mods from local library?", non_interactive_yes=False, force_non_interactive=json_mode)
            except NonInteractiveConfirmationError as exc:
                emitter.error(
                    message=str(exc),
                    code="CONFIRMATION_REQUIRED",
                    remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                    exit_code=ExitCode.USAGE,
                    exit_process=False,
                )
                return ExitCode.USAGE

    # Propagate global flags
    if getattr(args, "config", None) and "--config" not in target_args:
        target_args.extend(["--config", str(args.config)])
    if json_mode and "--json" not in target_args:
        target_args.append("--json")

    if verbose:
        emitter.log(f"Invoking in-process: {spec.target_module} with {target_args}", level="INFO")

    return _invoke_in_process(spec.target_module, target_args)


def main() -> None:
    """CLI execution entrypoint."""
    if "--no-color" in sys.argv:
        os.environ["NO_COLOR"] = "1"

    color = ConsoleColor(stream=sys.stderr, force_color=False)
    json_mode = "--json" in sys.argv
    emitter = OutputEmitter(json_mode=json_mode, color=color)

    if len(sys.argv) == 1:
        parser = build_parser()
        parser.print_help(sys.stderr)
        sys.exit(ExitCode.USAGE)

    parser = build_parser()
    args = parser.parse_args()

    try:
        ret = dispatch_command(args, emitter)
        sys.exit(ret)
    except KeyboardInterrupt:
        emitter.error(
            message="Operation aborted by user.",
            code="SIGINT",
            exit_code=130,
            exit_process=True,
        )


if __name__ == "__main__":
    main()
