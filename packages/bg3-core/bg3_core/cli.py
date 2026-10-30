#!/usr/bin/env python3
"""Baldur's Gate 3 Mod Studio — Unified 2026 CLI Suite.

Unified entrypoint providing structured noun-verb command execution, stream
discipline, and standard exit codes across the entire automation toolchain.

Usage:
    bg3 [--json] [--no-color] [--verbose] <command> <subcommand> [options...]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, List, NoReturn, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import bg3_core
from bg3_core.cli_common import (
    ConsoleColor,
    ExitCode,
    NonInteractiveConfirmationError,
    OutputEmitter,
    confirm_action,
)

bg3_theorycraft: Any
try:
    import bg3_theorycraft
except ImportError:
    bg3_theorycraft = None

bg3_authoring: Any
try:
    import bg3_authoring
except ImportError:
    bg3_authoring = None

CORE_DIR = Path(bg3_core.__file__).resolve().parent
THEORYCRAFTING_DIR = Path(bg3_theorycraft.__file__).resolve().parent if bg3_theorycraft else CORE_DIR.parent.parent / "bg3-theorycraft" / "bg3_theorycraft"
AUTHORING_DIR = Path(bg3_authoring.__file__).resolve().parent if bg3_authoring else CORE_DIR.parent.parent / "bg3-authoring" / "bg3_authoring"
DIAGNOSTICS_DIR = AUTHORING_DIR / "diagnostics"
PACKAGING_DIR = AUTHORING_DIR / "packaging"


class JsonCompliantArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that emits JSON error envelopes when --json flag is present."""

    def error(self, message: str) -> NoReturn:
        if "--json" in sys.argv:
            emitter = OutputEmitter(json_mode=True)
            emitter.error(
                message=message,
                code="USAGE_ERROR",
                remediation="Run 'bg3 --help' or 'bg3 <command> --help' for syntax.",
                exit_code=ExitCode.USAGE,
                exit_process=True,
            )
        super().error(message)


def setup_scaffold_subparsers(subparsers_obj: Any, common_parser: JsonCompliantArgumentParser) -> None:
    """Configures the unified asset scaffolding subcommands across 'bg3 scaffold' and 'bg3 mod scaffold'."""
    # 1. class
    sc_class = subparsers_obj.add_parser("class", help="Scaffold Class/Subclass definition, ProgressionDescriptions, and parent progression wiring", parents=[common_parser])
    sc_class.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_class.add_argument("--name", required=True, help="Internal class or subclass name")
    sc_class.add_argument("--display-name", help="Display name in UI")
    sc_class.add_argument("--description", help="Description for level-up UI")
    sc_class.add_argument("--parent-class", help="Vanilla parent class preset (e.g. rogue, wizard, paladin)")
    sc_class.add_argument("--parent-guid", help="Explicit parent class GUID")
    sc_class.add_argument("--class-uuid", help="Explicit UUID for this class")
    sc_class.add_argument("--table-uuid", help="Explicit ProgressionTableUUID")
    sc_class.add_argument("--base-hp", type=int, default=8, help="Base HP at level 1")
    sc_class.add_argument("--hp-per-level", type=int, default=5, help="HP gain per level")
    sc_class.add_argument("--primary-ability", type=int, default=1, help="Primary ability score enum")
    sc_class.add_argument("--spell-ability", type=int, default=0, help="Spellcasting ability enum")
    sc_class.add_argument("--register-in-parent", action="store_true", default=True, help="Inject subclass into parent's Progressions.lsx")
    sc_class.add_argument("--no-register-in-parent", dest="register_in_parent", action="store_false", help="Do not inject subclass into parent's Progressions.lsx")
    sc_class.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 2. feat
    sc_feat = subparsers_obj.add_parser("feat", help="Scaffold Feats and FeatDescriptions with localization", parents=[common_parser])
    sc_feat.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_feat.add_argument("--name", required=True, help="Internal feat name")
    sc_feat.add_argument("--display-name", help="Display name in UI")
    sc_feat.add_argument("--description", help="Description for tooltip")
    sc_feat.add_argument("--passives", nargs="*", help="Passives granted by feat")
    sc_feat.add_argument("--selectors", nargs="*", help="Selectors expressions")
    sc_feat.add_argument("--requirements", help="Feat requirements")
    sc_feat.add_argument("--can-be-picked-multiple-times", action="store_true", help="Allow selecting feat multiple times")
    sc_feat.add_argument("--feat-uuid", help="Explicit UUID for this feat")
    sc_feat.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 3. action-resource
    sc_res = subparsers_obj.add_parser("action-resource", aliases=["resource"], help="Scaffold ActionResourceDefinitions with replenish type", parents=[common_parser])
    sc_res.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_res.add_argument("--name", required=True, help="Internal resource name")
    sc_res.add_argument("--display-name", help="Display name in UI")
    sc_res.add_argument("--description", help="Description for tooltip")
    sc_res.add_argument("--replenish-type", choices=["Rest", "ShortRest", "Never", "Combat"], default="ShortRest", help="Replenish condition")
    sc_res.add_argument("--max-level", type=int, default=0, help="Maximum resource tier")
    sc_res.add_argument("--dice-type", type=int, default=0, help="Die size (4, 6, 8, 10, 12)")
    sc_res.add_argument("--show-on-action-panel", action="store_true", default=True, help="Display on action bar")
    sc_res.add_argument("--hide-from-action-panel", dest="show_on_action_panel", action="store_false", help="Hide from action bar")
    sc_res.add_argument("--is-spell-resource", action="store_true", help="Mark as spell resource")
    sc_res.add_argument("--party-resource", action="store_true", help="Mark as party-wide resource")
    sc_res.add_argument("--resource-uuid", help="Explicit UUID for this resource")
    sc_res.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 4. spell-list
    sc_spl = subparsers_obj.add_parser("spell-list", aliases=["spell_list"], help="Scaffold standalone SpellLists and PassiveLists", parents=[common_parser])
    sc_spl.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_spl.add_argument("--comment", help="Documentation label/comment")
    sc_spl.add_argument("--spells", nargs="*", help="Spell names for SpellLists.lsx")
    sc_spl.add_argument("--passives", nargs="*", help="Passive names for PassiveLists.lsx")
    sc_spl.add_argument("--uuid", help="Explicit UUID for this list")
    sc_spl.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 5. level-map
    sc_lm = subparsers_obj.add_parser("level-map", aliases=["level_map"], help="Scaffold LevelMapValues scaling curves across levels 1-20", parents=[common_parser])
    sc_lm.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_lm.add_argument("--name", required=True, help="Internal curve name")
    sc_lm.add_argument("--levels", required=True, help="Level mappings (e.g. '1=1d6,3=2d6,5=3d6')")
    sc_lm.add_argument("--dice-type", type=int, help="Override preferred dice type")
    sc_lm.add_argument("--uuid", help="Explicit UUID for this level map")
    sc_lm.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 6. default-values
    sc_dv = subparsers_obj.add_parser("default-values", aliases=["default_values"], help="Scaffold Character Creation DefaultValues (Abilities, Skills, Spells)", parents=[common_parser])
    sc_dv.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_dv.add_argument("--class", dest="class_name", required=True, help="Target class name")
    sc_dv.add_argument("--abilities", nargs="*", help="Recommended abilities")
    sc_dv.add_argument("--skills", nargs="*", help="Default skill proficiencies")
    sc_dv.add_argument("--spells", nargs="*", help="Default spells/cantrips")
    sc_dv.add_argument("--table-uuid", help="Explicit TableUUID")
    sc_dv.add_argument("--level", type=int, default=1, help="Level for default values")
    sc_dv.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 7. tag
    sc_tag = subparsers_obj.add_parser("tag", help="Scaffold dialogue and identity tag definitions in Tags/<UUID>.lsx", parents=[common_parser])
    sc_tag.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_tag.add_argument("--name", required=True, help="Internal tag name (e.g. SHADOW_STALKER)")
    sc_tag.add_argument("--display-name", help="Display name in character sheet")
    sc_tag.add_argument("--description", help="Description for tag")
    sc_tag.add_argument("--category", action="append", help="Tag category (e.g. Class, Subclass, Dialog). Can specify multiple.")
    sc_tag.add_argument("--uuid", help="Explicit UUID for this tag")
    sc_tag.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 8. race
    sc_race = subparsers_obj.add_parser("race", help="Scaffold Races.lsx and RaceDescriptions.lsx custom races and subraces", parents=[common_parser])
    sc_race.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_race.add_argument("--name", required=True, help="Internal race/subrace name")
    sc_race.add_argument("--display-name", help="Display name in UI")
    sc_race.add_argument("--description", help="Description in character creation")
    sc_race.add_argument("--parent-race", help="Vanilla parent race preset (e.g. elf, drow, human)")
    sc_race.add_argument("--parent-guid", help="Explicit parent race GUID")
    sc_race.add_argument("--race-uuid", help="Explicit UUID for this race")
    sc_race.add_argument("--table-uuid", help="Explicit ProgressionTableUUID")
    sc_race.add_argument("--equipment", help="Starting CC equipment preset name")
    sc_race.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 9. origin
    sc_orig = subparsers_obj.add_parser("origin", help="Scaffold Origins.lsx playable origin characters", parents=[common_parser])
    sc_orig.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_orig.add_argument("--name", required=True, help="Internal origin name")
    sc_orig.add_argument("--display-name", help="Display name in UI")
    sc_orig.add_argument("--description", help="Description in character creation")
    sc_orig.add_argument("--equipment", help="ClassEquipmentOverride preset name")
    sc_orig.add_argument("--class-uuid", help="Default class GUID")
    sc_orig.add_argument("--race-uuid", help="Default race GUID")
    sc_orig.add_argument("--body-type", type=int, choices=[0, 1], default=0, help="0=Male, 1=Female")
    sc_orig.add_argument("--body-shape", type=int, choices=[0, 1], default=0, help="0=Standard, 1=Strong")
    sc_orig.add_argument("--passives", nargs="*", help="Starting passive names")
    sc_orig.add_argument("--uuid", help="Explicit UUID for this origin")
    sc_orig.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 10. appearance
    sc_app = subparsers_obj.add_parser("appearance", aliases=["appearance-visual", "appearance_visual"], help="Scaffold CharacterCreationAppearanceVisuals.lsx cosmetic assets", parents=[common_parser])
    sc_app.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_app.add_argument("--name", required=True, help="Internal cosmetic name")
    sc_app.add_argument("--visual-resource", required=True, help="VisualResource mesh/asset GUID")
    sc_app.add_argument("--slot", choices=["Hair", "Head", "Horns", "Body", "Tail", "Beard", "Piercing", "EyeColor", "Tattoo", "Makeup"], default="Hair", help="Cosmetic slot")
    sc_app.add_argument("--race", help="Target race name or UUID")
    sc_app.add_argument("--body-type", type=int, choices=[0, 1], default=0, help="0=Male, 1=Female")
    sc_app.add_argument("--body-shape", type=int, choices=[0, 1], default=0, help="0=Standard, 1=Strong")
    sc_app.add_argument("--display-name", help="Display name in character creator")
    sc_app.add_argument("--uuid", help="Explicit UUID for this visual entry")
    sc_app.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    # 11. stat
    sc_stat = subparsers_obj.add_parser("stat", help="Scaffold Larian stat entries with string handles", parents=[common_parser])
    sc_stat.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_stat.add_argument("--type", required=True, help="Stat type: weapon, armor, interrupt, equipment, character, status_*, etc.")
    sc_stat.add_argument("--name", required=True, help="Internal stat identifier")
    sc_stat.add_argument("--display-name", help="In-game display name")
    sc_stat.add_argument("--description", help="In-game description")
    sc_stat.add_argument("--using", help="Base stat entry to inherit from")
    sc_stat.add_argument("--props", nargs="*", help="Key-value property pairs")
    sc_stat.add_argument("--dry-run", action="store_true", help="Preview generated stat entry")

    # 12. progression
    sc_prog = subparsers_obj.add_parser("progression", help="Scaffold Class/Subclass progression node", parents=[common_parser])
    sc_prog.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_prog.add_argument("--class", dest="class_name", required=True, help="Target Class name")
    sc_prog.add_argument("--level", type=int, required=True, help="Progression level (1-20)")
    sc_prog.add_argument("--subclass", help="Subclass name if applicable")
    sc_prog.add_argument("--multiclass", action="store_true", help="Mark progression node as multiclass entry (ProgressionType=2)")
    sc_prog.add_argument("--table-uuid", help="Explicit ProgressionTableUUID")
    sc_prog.add_argument("--passives", nargs="*", help="Passives to award")
    sc_prog.add_argument("--boosts", nargs="*", help="Boosts to award")
    sc_prog.add_argument("--spells", nargs="*", help="Spells/selectors to award")
    sc_prog.add_argument("--spell-count", type=int, default=1, help="Spell selector count")
    sc_prog.add_argument("--feat", action="store_true", help="Award feat at this level")
    sc_prog.add_argument("--dry-run", action="store_true", help="Preview progression LSX node")

    # 13. root-template
    sc_root = subparsers_obj.add_parser("root-template", aliases=["root_template"], help="Scaffold physical item RootTemplate", parents=[common_parser])
    sc_root.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_root.add_argument("--item", required=True, help="Item root template name")
    sc_root.add_argument("--visual-preset", help="Visual preset archetype")
    sc_root.add_argument("--parent-template", help="Parent template UUID")
    sc_root.add_argument("--display-handle", help="Display name handle")
    sc_root.add_argument("--description-handle", help="Description handle")
    sc_root.add_argument("--icon", help="Icon name")
    sc_root.add_argument("--no-link-stat", action="store_true", help="Do not link Stats property")
    sc_root.add_argument("--list-presets", action="store_true", help="List available visual presets")
    sc_root.add_argument("--dry-run", action="store_true", help="Preview root template XML")

    # 14. icon-uvs
    sc_icons = subparsers_obj.add_parser("icon-uvs", aliases=["icon_uvs"], help="Generate atlas icon coordinates and LSX definitions", parents=[common_parser])
    sc_icons.add_argument("--mod", required=True, help="Mod directory name in my_mods/")
    sc_icons.add_argument("--icon-names", nargs="*", help="List of icon names")
    sc_icons.add_argument("--icons-dir", help="Directory containing source icons")
    sc_icons.add_argument("--atlas-name", help="Atlas texture name")
    sc_icons.add_argument("--atlas-uuid", help="Atlas resource UUID")
    sc_icons.add_argument("--icon-size", type=int, default=64, help="Icon dimension in pixels")
    sc_icons.add_argument("--atlas-size", type=int, default=2048, help="Atlas texture dimension")
    sc_icons.add_argument("--dry-run", action="store_true", help="Preview icon UV LSX definitions")


def build_parser() -> JsonCompliantArgumentParser:
    """Build the unified CLI argument parser with noun-verb subcommand tree."""
    common_parser = JsonCompliantArgumentParser(add_help=False)
    common_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON payloads on stdout exclusively.",
    )
    common_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI terminal colors and text formatting.",
    )
    common_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed diagnostic messages on stderr.",
    )
    common_parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to custom environment configuration file.",
    )

    parser = JsonCompliantArgumentParser(
        prog="bg3",
        description="Baldur's Gate 3 Mod Studio — Unified 2026 CLI Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="Commands",
        metavar="<command>",
        parser_class=JsonCompliantArgumentParser,
    )

    # -------------------------------------------------------------------------
    # 'mod' command group
    # -------------------------------------------------------------------------
    mod_parser = subparsers.add_parser(
        "mod",
        help="Mod authoring, validation, and collision detection",
        parents=[common_parser],
    )
    mod_subparsers = mod_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    # bg3 mod conflict
    conflict_parser = mod_subparsers.add_parser(
        "conflict",
        help="Detect stat, progression, or root template collisions between mods",
        parents=[common_parser],
    )
    conflict_parser.add_argument(
        "candidate",
        nargs="?",
        help="Candidate mod name, directory, or path to inspect.",
    )
    conflict_parser.add_argument(
        "--against-library",
        action="store_true",
        help="Compare candidate against all cataloged mods in mods/.",
    )
    conflict_parser.add_argument(
        "--mod2",
        help="Second mod path or identifier to compare against directly.",
    )
    conflict_parser.add_argument(
        "--all",
        action="store_true",
        help="Cross-check all active mods across my_mods/ and mods/.",
    )

    # bg3 mod validate
    validate_parser = mod_subparsers.add_parser(
        "validate",
        help="Validate mod folder structure, meta.lsx, and localization entries",
        parents=[common_parser],
    )
    validate_parser.add_argument(
        "mod_identifier",
        help="Target mod slug, folder name, or directory path to validate.",
    )
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on non-critical warnings.",
    )
    validate_parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt automated remediation for missing UUIDs or sync issues.",
    )

    # bg3 mod create (Option A)
    create_parser = mod_subparsers.add_parser(
        "create",
        help="Create a new mod workspace in my_mods/",
        parents=[common_parser],
    )
    create_parser.add_argument(
        "name",
        help="Display name or slug for the new mod.",
    )
    create_parser.add_argument(
        "--slug",
        help="Custom folder slug (default: derived from name).",
    )
    create_parser.add_argument(
        "--uuid",
        help="Explicit ModuleUUID GUID.",
    )
    create_parser.add_argument(
        "--author",
        help="Author name (defaults to configured environment author).",
    )
    create_parser.add_argument(
        "--description",
        help="In-game and mod.io description.",
    )
    create_parser.add_argument(
        "--version",
        default="1.0.0.0",
        help="Initial semantic Version64 (default: 1.0.0.0).",
    )
    create_parser.add_argument(
        "--unlock-level-curve",
        action="store_true",
        help="Add UnlockLevelCurve compatibility and progression boost table.",
    )
    create_parser.add_argument(
        "--dependency",
        action="append",
        default=[],
        help="Dependency mod slug or UUID to register in meta.lsx.",
    )
    create_parser.add_argument(
        "--output-dir",
        help="Custom output directory (defaults to my_mods/<slug>).",
    )
    create_parser.add_argument(
        "--type",
        default="Standard",
        choices=["Standard", "Class", "Subclass", "Item", "Spell", "Cosmetic"],
        help="Mod template archetype (default: Standard).",
    )
    create_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview generated files without writing to disk.",
    )

    # bg3 mod scaffold (forwarding to asset scaffolders)
    mod_scaffold_parser = mod_subparsers.add_parser(
        "scaffold",
        help="Scaffold mod assets, stat entries, progressions, and schemas (alias for bg3 scaffold)",
        parents=[common_parser],
    )
    mod_scaffold_subparsers = mod_scaffold_parser.add_subparsers(
        dest="mod_scaffold_subcommand",
        metavar="<asset>",
        parser_class=JsonCompliantArgumentParser,
    )
    setup_scaffold_subparsers(mod_scaffold_subparsers, common_parser)

    # bg3 mod add-dependency
    add_dep_parser = mod_subparsers.add_parser(
        "add-dependency",
        help="Append dependencies or test dependencies to a custom mod",
        parents=[common_parser],
    )
    add_dep_parser.add_argument("mod", help="Target mod name or slug")
    add_dep_parser.add_argument("dependencies", nargs="*", help="Dependency mod slugs or names")
    add_dep_parser.add_argument("--dep", action="append", default=[], help="Explicit dependency slug")
    add_dep_parser.add_argument("--test-dep", action="append", default=[], help="Explicit test dependency slug")
    add_dep_parser.add_argument("--test-only", action="store_true", help="Mark dependencies as test-only")
    add_dep_parser.add_argument("--dry-run", action="store_true", help="Preview metadata changes without saving")

    # bg3 mod bump-version
    bump_parser = mod_subparsers.add_parser(
        "bump-version",
        aliases=["bump_version"],
        help="Increment semantic Version64 across meta.lsx and README.md",
        parents=[common_parser],
    )
    bump_parser.add_argument("mod", nargs="?", help="Mod slug or directory")
    bump_group = bump_parser.add_mutually_exclusive_group()
    bump_group.add_argument("--patch", "-p", action="store_true", help="Increment patch version")
    bump_group.add_argument("--minor", "-m", action="store_true", help="Increment minor version")
    bump_group.add_argument("--major", action="store_true", help="Increment major version")
    bump_group.add_argument("--build", "-b", action="store_true", help="Increment build integer")
    bump_group.add_argument("--show", action="store_true", help="Display current version without modifying")
    bump_group.add_argument("--set", help="Explicit version string (e.g. 1.2.0.0)")
    bump_parser.add_argument("--dry-run", action="store_true", help="Preview version changes without writing to disk")

    # bg3 mod pack
    pack_parser = mod_subparsers.add_parser(
        "pack",
        help="Build a game-ready LSPK .pak archive from my_mods/<slug>",
        parents=[common_parser],
    )
    pack_parser.add_argument("mod", help="Mod slug or directory")
    pack_parser.add_argument("--out", "--output", dest="output", help="Output .pak file path")
    pack_parser.add_argument("--output-dir", help="Output directory for generated .pak file")
    pack_parser.add_argument("--publish-local", action="store_true", help="Publish .pak directly to local BG3 Mods directory")
    pack_parser.add_argument("--clean-local", action="store_true", help="Purge local test .pak file(s) for this mod")
    pack_parser.add_argument("--include-projects", action="store_true", help="Include Projects/ directory")
    pack_parser.add_argument("--uncompressed", action="store_true", help="Store files uncompressed")
    pack_parser.add_argument("--dry-run", action="store_true", help="Preview operations without modifying files")

    # bg3 mod sync-loca
    loca_parser = mod_subparsers.add_parser(
        "sync-loca",
        aliases=["sync_loca"],
        help="Audit, prune, or compile Localization XML handles",
        parents=[common_parser],
    )
    loca_parser.add_argument("mod", help="Mod slug or directory")
    loca_parser.add_argument("--check", action="store_true", help="Check for orphaned or missing handles")
    loca_parser.add_argument("--prune", action="store_true", help="Prune orphaned localization handles")
    loca_parser.add_argument("--backup", action="store_true", help="Backup localization files before modifying")
    loca_parser.add_argument("--compile", action="store_true", help="Compile localization XML to binary .loca")
    loca_parser.add_argument("--sync-languages", action="store_true", help="Synchronize handles across language files")
    loca_parser.add_argument("--dry-run", action="store_true", help="Preview localization actions")

    # bg3 mod sync-game
    sync_game_parser = mod_subparsers.add_parser(
        "sync-game",
        aliases=["sync_game"],
        help="Synchronize unpacked mod assets and compiled .loca to BG3 Data directory",
        parents=[common_parser],
    )
    sync_game_parser.add_argument("--mods", nargs="*", help="Specific mod slugs to synchronize")
    sync_game_parser.add_argument("--source-dir", help="Source directory containing mods (default: my_mods)")
    sync_game_parser.add_argument("--data-dir", help="Baldur's Gate 3 Data directory path")
    sync_game_parser.add_argument("--clean-legacy", action="store_true", help="Clean up legacy mod folders/files in Steam Data")
    sync_game_parser.add_argument("--no-clean-legacy", action="store_true", help="Disable automatic cleaning of legacy mod folders")
    sync_game_parser.add_argument("--clean-custom", action="store_true", help="Purge custom studio mods from Steam Data")
    sync_game_parser.add_argument("--clean-mod", help="Purge a specific custom mod's loose files from Steam Data")
    sync_game_parser.add_argument("--bump-build", action="store_true", help="Increment build number (+1) in meta.lsx")
    sync_game_parser.add_argument("--watch", action="store_true", help="Watch source directory and sync continuously")
    sync_game_parser.add_argument("--interval", type=float, default=2.0, help="Watch interval in seconds")
    sync_game_parser.add_argument("--dry-run", action="store_true", help="Preview file sync operations")

    # bg3 mod patch
    patch_parser = mod_subparsers.add_parser(
        "patch",
        help="Generate compatibility override patch or Compatibility Framework config",
        parents=[common_parser],
    )
    patch_parser.add_argument("--mod1", required=True, help="First mod slug or directory")
    patch_parser.add_argument("--mod2", required=True, help="Second mod slug or directory")
    patch_parser.add_argument("--name", help="Patch mod name")
    patch_parser.add_argument("--mode", choices=["standalone", "cf"], default="standalone", help="Patch format")
    patch_parser.add_argument("--dry-run", action="store_true", help="Preview generated patch files")

    # bg3 mod diagnose-logs
    diag_parser = mod_subparsers.add_parser(
        "diagnose-logs",
        aliases=["diagnose_logs"],
        help="Diagnose BG3 Toolkit runtime logs and triage errors",
        parents=[common_parser],
    )
    diag_parser.add_argument("--mod", help="Target mod name or slug")
    diag_parser.add_argument("--toolkit-dir", help="Path to BG3 Toolkit directory")
    diag_parser.add_argument("--type", choices=["engine", "osiris", "thoth", "personal", "network", "all", "general", "crash", "assert"], default="engine")
    diag_parser.add_argument("--severity", choices=["critical", "error", "warning", "info", "debug", "all"], default="warning")
    diag_parser.add_argument("--subsystem", help="Filter by engine subsystem")
    diag_parser.add_argument("--limit", type=int, default=50, help="Max entries to report")
    diag_parser.add_argument("-f", "--follow", action="store_true", help="Follow logs live")
    diag_parser.add_argument("--list-logs", action="store_true", help="List available log files")
    diag_parser.add_argument("--info", action="store_true", help="Show log metadata")
    diag_parser.add_argument("--purge", action="store_true", help="Purge session log files from the toolkit directory based on retention rules")
    diag_parser.add_argument("--keep", type=int, default=5, help="Number of most recent log files to preserve during purge (default: 5)")
    diag_parser.add_argument("--days", type=float, help="Purge log files older than specified days")
    diag_parser.add_argument("--all", action="store_true", help="Purge all matching log files without preserving any recent logs")
    diag_parser.add_argument("-n", "--dry-run", action="store_true", help="Simulate purge without modifying files")
    diag_parser.add_argument("-y", "--yes", action="store_true", help="Confirm deletion non-interactively")

    # bg3 mod inspect-save
    inspect_save_parser = mod_subparsers.add_parser(
        "inspect-save",
        aliases=["inspect_save"],
        help="Inspect Baldur's Gate 3 save games and audit mod dependencies",
        parents=[common_parser],
    )
    inspect_save_parser.add_argument("save", nargs="?", help="Path to .lsv save game file")
    inspect_save_parser.add_argument("--save-dir", help="Custom save directory")
    inspect_save_parser.add_argument("--audit", action="store_true", help="Audit active mods against save requirements")

    # bg3 mod inject-treasure
    inject_parser = mod_subparsers.add_parser(
        "inject-treasure",
        aliases=["inject_treasure"],
        help="Inject mod item into world container treasure tables",
        parents=[common_parser],
    )
    inject_parser.add_argument("--mod", required=True, help="Target mod name or slug")
    inject_parser.add_argument("--item", required=True, help="Stat entry name or root template map key")
    inject_parser.add_argument("--container", help="Container or table name (e.g. TUT_Chest_Potions)")
    inject_parser.add_argument("--count", type=int, default=1, help="Drop count")
    inject_parser.add_argument("--ratio", type=int, default=1, help="Drop ratio frequency")
    inject_parser.add_argument("--start-level", type=int, default=1, help="Min character level")
    inject_parser.add_argument("--raw-item-name", action="store_true", help="Treat item name as raw stat entry")
    inject_parser.add_argument("--list-containers", action="store_true", help="List common container tables")
    inject_parser.add_argument("--dry-run", action="store_true", help="Preview table modifications")

    # bg3 mod render-desc
    render_desc_parser = mod_subparsers.add_parser(
        "render-desc",
        aliases=["render_desc"],
        help="Render mod.io HTML description from README.md",
        parents=[common_parser],
    )
    render_desc_parser.add_argument("mod", help="Target mod name or slug")
    render_desc_parser.add_argument("--write", action="store_true", help="Write modio_description.html to mod dir")

    # -------------------------------------------------------------------------
    # 'loadorder' command group
    # -------------------------------------------------------------------------
    lo_parser = subparsers.add_parser(
        "loadorder",
        help="Player profile modsettings.lsx load order management",
        parents=[common_parser],
    )
    lo_subparsers = lo_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    lo_list_parser = lo_subparsers.add_parser(
        "list",
        help="List active mods in the current modsettings.lsx profile",
        parents=[common_parser],
    )
    lo_list_parser.add_argument(
        "--profile",
        help="Specify custom profile name or directory.",
    )

    lo_sync_parser = lo_subparsers.add_parser(
        "sync",
        help="Synchronize my_mods into the active load order profile",
        parents=[common_parser],
    )
    lo_sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing modsettings.lsx.",
    )
    lo_sync_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Bypass interactive confirmation in non-interactive sessions.",
    )

    lo_clean_parser = lo_subparsers.add_parser(
        "clean",
        help="Remove missing or invalid mod entries from load order",
        parents=[common_parser],
    )
    lo_clean_parser.add_argument(
        "--path",
        help="Explicit path to modsettings.lsx.",
    )
    lo_clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleaned load order without saving.",
    )
    lo_clean_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Bypass interactive confirmation in non-interactive sessions.",
    )

    # bg3 loadorder enable
    lo_enable_parser = lo_subparsers.add_parser(
        "enable",
        aliases=["activate"],
        help="Enable a mod in active load order",
        parents=[common_parser],
    )
    lo_enable_parser.add_argument("mod", help="Mod name, slug, or UUID to enable")
    lo_enable_parser.add_argument("--order", type=int, help="Target 1-indexed load order position")
    lo_enable_parser.add_argument("--with-deps", action="store_true", default=True, help="Automatically enable declared dependencies")
    lo_enable_parser.add_argument("--no-deps", action="store_false", dest="with_deps", help="Do not automatically enable dependencies")
    lo_enable_parser.add_argument("--test-dep", action="append", default=[], help="Activate test dependency ahead of mod")
    lo_enable_parser.add_argument("--isolate", "--clean", dest="isolate", action="store_true", help="Clean-room isolation: disable unrelated mods in modsettings.lsx and deduplicate .pak collisions")
    lo_enable_parser.add_argument("--quarantine", action="store_true", help="Physically quarantine unrelated .pak files to Mods_Disabled/ (Warning: triggers mod.io auto-download for subscribed mods)")
    lo_enable_parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    lo_enable_parser.add_argument("--dry-run", action="store_true", help="Preview modifications without saving")

    # bg3 loadorder disable
    lo_disable_parser = lo_subparsers.add_parser(
        "disable",
        help="Disable a mod in active load order",
        parents=[common_parser],
    )
    lo_disable_parser.add_argument("mod", help="Mod name, slug, or UUID to disable")
    lo_disable_parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    lo_disable_parser.add_argument("--dry-run", action="store_true", help="Preview modifications without saving")

    # bg3 loadorder validate
    lo_val_parser = lo_subparsers.add_parser(
        "validate",
        help="Validate active load order against dependency and ordering rules",
        parents=[common_parser],
    )
    lo_val_parser.add_argument("--path", help="Explicit path to modsettings.lsx")

    # bg3 loadorder isolate
    lo_iso_parser = lo_subparsers.add_parser(
        "isolate",
        help="Clean-room isolation: disable unrelated mods in modsettings.lsx and deduplicate .pak collisions",
        description="Clean-room isolation: disable unrelated mods in modsettings.lsx and deduplicate .pak collisions",
        parents=[common_parser],
    )
    lo_iso_parser.add_argument("mod", help="Target mod name or slug to isolate")
    lo_iso_parser.add_argument("--test-dep", action="append", default=[], help="Activate test dependency ahead of mod")
    lo_iso_parser.add_argument("--with-deps", action="store_true", default=True, help="Automatically enable declared dependencies")
    lo_iso_parser.add_argument("--no-deps", action="store_false", dest="with_deps", help="Do not automatically enable dependencies")
    lo_iso_parser.add_argument("--quarantine", action="store_true", help="Physically quarantine unrelated .pak files (Warning: triggers mod.io auto-download for subscribed mods)")
    lo_iso_parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    lo_iso_parser.add_argument("--dry-run", action="store_true", help="Preview modifications without saving")
    lo_iso_parser.add_argument("-y", "--yes", action="store_true", help="Confirm non-interactively")

    # bg3 loadorder restore
    lo_restore_parser = lo_subparsers.add_parser(
        "restore",
        help="Restore quarantined mods from Mods_Disabled/ back to active Mods directory",
        description="Restore quarantined mods from Mods_Disabled/ back to active Mods directory",
        parents=[common_parser],
    )
    lo_restore_parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    lo_restore_parser.add_argument("--dry-run", action="store_true", help="Preview restoration without moving files")
    lo_restore_parser.add_argument("-y", "--yes", action="store_true", help="Confirm non-interactively")

    # bg3 loadorder dedup
    lo_dedup_parser = lo_subparsers.add_parser(
        "dedup",
        aliases=["deduplicate"],
        help="Deduplicate installed .pak files in AppData Mods",
        description="Deduplicate installed .pak files in AppData Mods",
        parents=[common_parser],
    )
    lo_dedup_parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    lo_dedup_parser.add_argument("--dry-run", action="store_true", help="Preview deduplication without moving files")
    lo_dedup_parser.add_argument("-y", "--yes", action="store_true", help="Confirm non-interactively")

    # -------------------------------------------------------------------------
    # 'modio' command group
    # -------------------------------------------------------------------------
    modio_parser = subparsers.add_parser(
        "modio",
        help="Mod.io integration (search, sync, extract, update)",
        parents=[common_parser],
    )
    modio_subparsers = modio_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    modio_search_parser = modio_subparsers.add_parser(
        "search",
        help="Search Baldur's Gate 3 community mods on mod.io",
        parents=[common_parser],
    )
    modio_search_parser.add_argument(
        "query",
        help="Search keywords or intent.",
    )
    modio_search_parser.add_argument(
        "-p", "--platform",
        choices=["pc", "mac", "ps5", "xbox", "all"],
        default="all",
        help="Target platform filter (default: all).",
    )
    modio_search_parser.add_argument(
        "--include-tracked",
        action="store_true",
        help="Include already tracked mods in search results.",
    )
    modio_search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum results to return (default: 10).",
    )

    modio_sync_parser = modio_subparsers.add_parser(
        "sync",
        help="Synchronize tracked mods from mod.io",
        parents=[common_parser],
    )
    modio_sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview updates without downloading or extracting.",
    )
    modio_sync_parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove unsubscribed mods from library.md and delete applicable mod folders.",
    )
    modio_sync_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of new subscribed mods to extract and document.",
    )
    modio_sync_parser.add_argument(
        "--filter",
        help="Filter subscribed mods by name or slug substring.",
    )
    modio_sync_parser.add_argument(
        "--skip-updates",
        action="store_true",
        help="Skip checking/updating existing documented mods.",
    )
    modio_sync_parser.add_argument(
        "--token", "-t",
        help="mod.io OAuth 2.0 Personal Access Token.",
    )
    modio_sync_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Bypass interactive confirmation in non-interactive sessions.",
    )

    # bg3 modio extract
    modio_extract_parser = modio_subparsers.add_parser(
        "extract",
        help="Download and extract mod.io .pak archive and document in library",
        parents=[common_parser],
    )
    modio_extract_parser.add_argument("query", nargs="?", help="Mod slug, name, or URL")
    modio_extract_parser.add_argument("--pak", help="Local .pak file path to extract")
    modio_extract_parser.add_argument("-o", "--output-dir", help="Output directory")
    modio_extract_parser.add_argument("--write-spec", action="store_true", help="Generate README specification")
    modio_extract_parser.add_argument("--update-library", action="store_true", help="Update mods/library.md entry")

    # bg3 modio update
    modio_update_parser = modio_subparsers.add_parser(
        "update",
        help="Check and update tracked mods from mod.io",
        parents=[common_parser],
    )
    modio_update_parser.add_argument("query", nargs="?", help="Specific mod slug or directory")
    modio_update_parser.add_argument("--all", action="store_true", help="Check all tracked mods")
    modio_update_parser.add_argument("--check-only", action="store_true", help="Report updates without downloading")
    modio_update_parser.add_argument("--force", action="store_true", help="Force redownload even if up-to-date")
    modio_update_parser.add_argument("--list-tracked", action="store_true", help="List all tracked mods")

    # bg3 modio update-metadata
    modio_meta_parser = modio_subparsers.add_parser(
        "update-metadata",
        aliases=["update_metadata"],
        help="Update mod.io tags, metadata, and visibility",
        parents=[common_parser],
    )
    modio_meta_parser.add_argument("--mod", required=True, help="Target mod name or slug")
    modio_meta_parser.add_argument("--tags", nargs="*", help="Tags to assign on mod.io")
    modio_meta_parser.add_argument("--confirm", action="store_true", help="Apply updates without prompting")

    # bg3 modio create-collection
    modio_coll_parser = modio_subparsers.add_parser(
        "create-collection",
        aliases=["create_collection"],
        help="Generate or update public mod.io collection from library.md",
        parents=[common_parser],
    )
    modio_coll_parser.add_argument("--library", default="mods/library.md", help="Path to library.md")
    modio_coll_parser.add_argument("--dry-run", action="store_true", help="Preview collection payload")

    # bg3 modio purge
    modio_purge_parser = modio_subparsers.add_parser(
        "purge",
        help="Purge local mod folders and reset library.md",
        parents=[common_parser],
    )
    modio_purge_parser.add_argument("-n", "--dry-run", action="store_true", help="Preview purge operations")
    modio_purge_parser.add_argument("-f", "--force", action="store_true", help="Force deletion without prompt")
    modio_purge_parser.add_argument("-y", "--yes", action="store_true", help="Confirm non-interactively")
    modio_purge_parser.add_argument("--mods-dir", help="Custom mods directory")
    modio_purge_parser.add_argument("--library-path", help="Custom library.md path")

    # bg3 modio update-catalog
    modio_cat_parser = modio_subparsers.add_parser(
        "update-catalog",
        aliases=["update_catalog"],
        help="Regenerate mods/library.md catalog from mods/ README files",
        parents=[common_parser],
    )
    modio_cat_parser.add_argument("--write", action="store_true", help="Write regenerated catalog to library.md")
    modio_cat_parser.add_argument("--check", action="store_true", help="Check for drift without writing")
    modio_cat_parser.add_argument("--stdout", action="store_true", help="Output catalog to stdout")

    # -------------------------------------------------------------------------
    # 'scaffold' command group
    # -------------------------------------------------------------------------
    scaffold_grp_parser = subparsers.add_parser(
        "scaffold",
        help="Scaffold mod assets, stat entries, progressions, and templates",
        parents=[common_parser],
    )
    scaffold_grp_subparsers = scaffold_grp_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )
    setup_scaffold_subparsers(scaffold_grp_subparsers, common_parser)

    # -------------------------------------------------------------------------
    # 'query' command group
    # -------------------------------------------------------------------------
    query_parser = subparsers.add_parser(
        "query",
        help="Query high-speed BiS gear, spell, and mechanics database",
        parents=[common_parser],
    )
    query_parser.add_argument("search", nargs="?", help="General search term across name, description, boosts, and passives")
    query_parser.add_argument("--slot", help="Filter by equipment slot (Amulet, Ring, Boots, Weapon, Cloak)")
    query_parser.add_argument("--boost", help="Filter by boost effect (SpellSaveDC, AC, CriticalHit)")
    query_parser.add_argument("--passive", help="Filter by passive effect (ExtraAttack, Lifedrinker)")
    query_parser.add_argument("--rarity", help="Filter by item rarity (Rare, VeryRare, Legendary)")
    query_parser.add_argument("--mod", help="Filter by mod slug/name")
    query_parser.add_argument("--limit", type=int, default=10, help="Maximum results to display")
    query_parser.add_argument("--compact", action="store_true", help="Output compact records")
    query_parser.add_argument("--reindex", action="store_true", help="Force rebuild of index")

    # -------------------------------------------------------------------------
    # 'build' command group
    # -------------------------------------------------------------------------
    build_parser = subparsers.add_parser(
        "build",
        aliases=["sim"],
        help="Character build theorycrafting and combat simulation",
        parents=[common_parser],
    )
    build_subparsers = build_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )
    sim_parser = build_subparsers.add_parser(
        "simulate",
        aliases=["sim"],
        help="Simulate Level 20 character build stats, spell slots, AC, and Turn 1 DPR",
        parents=[common_parser],
    )
    sim_parser.add_argument("--classes", help="Class distribution (e.g. 'Paladin 12, Warlock 8')")
    sim_parser.add_argument("--stats", help="Base ability scores (e.g. 'STR 16, CHA 16')")
    sim_parser.add_argument("--gear", nargs="*", help="Equipped cataloged items")
    sim_parser.add_argument("--dpr-sequence", help="Turn 1 attack sequence")
    sim_parser.add_argument("--target-ac", type=int, default=18, help="Target enemy Armor Class")
    sim_parser.add_argument("--haste", action="store_true", help="Include Haste additional action")
    sim_parser.add_argument("--advantage", action="store_true", help="Roll attacks with Advantage")

    # -------------------------------------------------------------------------
    # 'tools' command group
    # -------------------------------------------------------------------------
    tools_parser = subparsers.add_parser(
        "tools",
        help="Tool registry discovery, verification, and inspection",
        parents=[common_parser],
    )
    tools_subparsers = tools_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )
    tools_list_parser = tools_subparsers.add_parser("list", help="List studio automation tools", parents=[common_parser])
    tools_list_parser.add_argument("--category", help="Filter by category")
    tools_list_parser.add_argument("--categories", action="store_true", help="List all tool categories and descriptions")
    tools_list_parser.add_argument("--full", action="store_true", help="Include full schemas, flags, and examples")

    tools_search_parser = tools_subparsers.add_parser("search", help="Search studio tools by intent or keyword", parents=[common_parser])
    tools_search_parser.add_argument("query", help="Keyword or intent")

    tools_info_parser = tools_subparsers.add_parser("info", help="Inspect tool documentation and flags", parents=[common_parser])
    tools_info_parser.add_argument("tool_name", help="Tool name or command")

    tools_verify_parser = tools_subparsers.add_parser("verify", help="Verify tool syntax and registry integrity", parents=[common_parser])
    tools_verify_parser.add_argument("--audit-skills", action="store_true", help="Audit skill references")

    # -------------------------------------------------------------------------
    # 'env' command group
    # -------------------------------------------------------------------------
    env_parser = subparsers.add_parser(
        "env",
        help="Studio environment configuration and path diagnostics",
        parents=[common_parser],
    )
    env_subparsers = env_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    env_subparsers.add_parser(
        "check",
        help="Perform non-interactive path, tool, and environment health check",
        parents=[common_parser],
    )

    env_subparsers.add_parser(
        "paths",
        help="Display canonical XDG Base Directory specification paths and status",
        parents=[common_parser],
    )

    env_setup_parser = env_subparsers.add_parser(
        "setup",
        help="Run environment setup wizard",
        parents=[common_parser],
    )
    env_setup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview configuration changes without writing to disk.",
    )

    # -------------------------------------------------------------------------
    # 'save' command group (manage_saves.py)
    # -------------------------------------------------------------------------
    save_parser = subparsers.add_parser(
        "save",
        aliases=["saves"],
        help="Inspect, list, backup, and purge Baldur's Gate 3 save games",
        parents=[common_parser],
    )
    save_subparsers = save_parser.add_subparsers(
        dest="subcommand",
        metavar="<action>",
        parser_class=JsonCompliantArgumentParser,
    )

    # bg3 save list
    save_list_p = save_subparsers.add_parser(
        "list",
        help="List discovered BG3 save games across standard and custom search paths",
        parents=[common_parser],
    )
    save_list_p.add_argument("--save-dir", help="Custom directory containing .lsv save files")

    # bg3 save inspect
    save_inspect_p = save_subparsers.add_parser(
        "inspect",
        help="Inspect and audit a specific or latest save game",
        parents=[common_parser],
    )
    save_inspect_p.add_argument("save", nargs="?", help="Path or name of .lsv save file, or 'latest'")
    save_inspect_p.add_argument("--save-dir", help="Custom directory containing .lsv save files")
    save_inspect_p.add_argument("--audit", action="store_true", help="Audit save mods against active modsettings.lsx")

    # bg3 save backup
    save_backup_p = save_subparsers.add_parser(
        "backup",
        help="Archive save games into a ZIP backup",
        parents=[common_parser],
    )
    save_backup_p.add_argument("--save", help="Specific save game name to back up")
    save_backup_p.add_argument("--dest", help="Destination directory or ZIP archive path")
    save_backup_p.add_argument("--save-dir", help="Custom directory containing .lsv save files")

    # bg3 save purge
    save_purge_p = save_subparsers.add_parser(
        "purge",
        help="Prune old or unneeded save games",
        parents=[common_parser],
    )
    save_purge_p.add_argument("--keep", type=int, default=5, help="Number of newest saves to preserve (default: 5)")
    save_purge_p.add_argument("--days", type=float, help="Purge saves older than specified days")
    save_purge_p.add_argument("--save", help="Specific save name to purge")
    save_purge_p.add_argument("--all", action="store_true", help="Purge all matching saves (preserves latest unless --force-all)")
    save_purge_p.add_argument("--force-all", action="store_true", help="Purge ALL saves including the latest save")
    save_purge_p.add_argument("--no-keep-latest", action="store_true", help="Disable latest save protection")
    save_purge_p.add_argument("--backup", action="store_true", help="Create a ZIP backup before purging")
    save_purge_p.add_argument("--backup-dir", help="Custom directory for pre-purge backup")
    save_purge_p.add_argument("--save-dir", help="Custom directory containing .lsv save files")
    save_purge_p.add_argument("-n", "--dry-run", action="store_true", help="Simulate purge without modifying files")
    save_purge_p.add_argument("-y", "--yes", action="store_true", help="Confirm deletion non-interactively")

    return parser


def resolve_module_fallback(script_target: Path) -> Optional[str]:
    """Derives a fully-qualified Python module name from a target script path."""
    for base_pkg in ("bg3_authoring", "bg3_core", "bg3_theorycraft"):
        parts = script_target.parts
        if base_pkg in parts:
            idx = parts.index(base_pkg)
            rel_parts = list(parts[idx:])
            if rel_parts[-1].endswith(".py"):
                rel_parts[-1] = rel_parts[-1][:-3]
            return ".".join(rel_parts)
    return None


def dispatch_command(args: argparse.Namespace, emitter: OutputEmitter) -> int:
    """Route parsed CLI arguments to the target implementation script."""
    cmd = args.command
    sub = getattr(args, "subcommand", None)

    if not cmd or (cmd != "query" and not sub):
        emitter.error(
            message="Missing required command and action. Run 'bg3 --help' for available commands.",
            code="MISSING_COMMAND",
            exit_code=ExitCode.USAGE,
            exit_process=False,
        )
        return ExitCode.USAGE

    # Build underlying invocation
    script_target: Optional[Path] = None
    target_args: List[str] = []

    if cmd == "scaffold" or (cmd == "mod" and sub == "scaffold"):
        actual_sub = getattr(args, "mod_scaffold_subcommand", None) or getattr(args, "subcommand", None)
        if actual_sub == "class":
            script_target = AUTHORING_DIR / "scaffold_class_description.py"
            target_args.extend(["--mod", args.mod, "--name", args.name])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "parent_class", None):
                target_args.extend(["--parent-class", args.parent_class])
            if getattr(args, "parent_guid", None):
                target_args.extend(["--parent-guid", args.parent_guid])
            if getattr(args, "class_uuid", None):
                target_args.extend(["--class-uuid", args.class_uuid])
            if getattr(args, "table_uuid", None):
                target_args.extend(["--table-uuid", args.table_uuid])
            if getattr(args, "base_hp", None) is not None:
                target_args.extend(["--base-hp", str(args.base_hp)])
            if getattr(args, "hp_per_level", None) is not None:
                target_args.extend(["--hp-per-level", str(args.hp_per_level)])
            if getattr(args, "primary_ability", None) is not None:
                target_args.extend(["--primary-ability", str(args.primary_ability)])
            if getattr(args, "spell_ability", None) is not None:
                target_args.extend(["--spell-ability", str(args.spell_ability)])
            if getattr(args, "register_in_parent", True) is False:
                target_args.append("--no-register-in-parent")
            elif getattr(args, "register_in_parent", False):
                target_args.append("--register-in-parent")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub == "feat":
            script_target = AUTHORING_DIR / "scaffold_feat.py"
            target_args.extend(["--mod", args.mod, "--name", args.name])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "passives", None):
                target_args.extend(["--passives", ",".join(args.passives) if isinstance(args.passives, list) else args.passives])
            if getattr(args, "selectors", None):
                target_args.extend(["--selectors", ",".join(args.selectors) if isinstance(args.selectors, list) else args.selectors])
            if getattr(args, "requirements", None):
                target_args.extend(["--requirements", args.requirements])
            if getattr(args, "can_be_picked_multiple_times", False):
                target_args.append("--can-be-picked-multiple-times")
            if getattr(args, "feat_uuid", None):
                target_args.extend(["--feat-uuid", args.feat_uuid])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub in ("action-resource", "resource"):
            script_target = AUTHORING_DIR / "scaffold_action_resource.py"
            target_args.extend(["--mod", args.mod, "--name", args.name])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "replenish_type", None):
                target_args.extend(["--replenish-type", args.replenish_type])
            if getattr(args, "max_level", None) is not None:
                target_args.extend(["--max-level", str(args.max_level)])
            if getattr(args, "dice_type", None) is not None:
                target_args.extend(["--dice-type", str(args.dice_type)])
            if getattr(args, "show_on_action_panel", True) is False:
                target_args.append("--hide-from-action-panel")
            elif getattr(args, "show_on_action_panel", False):
                target_args.append("--show-on-action-panel")
            if getattr(args, "is_spell_resource", False):
                target_args.append("--is-spell-resource")
            if getattr(args, "party_resource", False):
                target_args.append("--party-resource")
            if getattr(args, "resource_uuid", None):
                target_args.extend(["--resource-uuid", args.resource_uuid])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub in ("spell-list", "spell_list"):
            script_target = AUTHORING_DIR / "scaffold_spell_list.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "comment", None):
                target_args.extend(["--comment", args.comment])
            if getattr(args, "spells", None):
                target_args.extend(["--spells", ",".join(args.spells) if isinstance(args.spells, list) else args.spells])
            if getattr(args, "passives", None):
                target_args.extend(["--passives", ",".join(args.passives) if isinstance(args.passives, list) else args.passives])
            if getattr(args, "uuid", None):
                target_args.extend(["--uuid", args.uuid])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub in ("level-map", "level_map"):
            script_target = AUTHORING_DIR / "scaffold_level_map.py"
            target_args.extend(["--mod", args.mod, "--name", args.name, "--levels", args.levels])
            if getattr(args, "dice_type", None) is not None:
                target_args.extend(["--dice-type", str(args.dice_type)])
            if getattr(args, "uuid", None):
                target_args.extend(["--uuid", args.uuid])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub in ("default-values", "default_values"):
            script_target = AUTHORING_DIR / "scaffold_default_values.py"
            target_args.extend(["--mod", args.mod, "--class", args.class_name])
            if getattr(args, "abilities", None):
                target_args.extend(["--abilities", ",".join(args.abilities) if isinstance(args.abilities, list) else args.abilities])
            if getattr(args, "skills", None):
                target_args.extend(["--skills", ",".join(args.skills) if isinstance(args.skills, list) else args.skills])
            if getattr(args, "spells", None):
                target_args.extend(["--spells", ",".join(args.spells) if isinstance(args.spells, list) else args.spells])
            if getattr(args, "table_uuid", None):
                target_args.extend(["--table-uuid", args.table_uuid])
            if getattr(args, "level", None) is not None:
                target_args.extend(["--level", str(args.level)])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub == "tag":
            script_target = AUTHORING_DIR / "scaffold_tag.py"
            target_args.extend(["--mod", args.mod, "--name", args.name])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            for cat in getattr(args, "category", []):
                target_args.extend(["--category", cat])
            if getattr(args, "uuid", None):
                target_args.extend(["--uuid", args.uuid])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub == "race":
            script_target = AUTHORING_DIR / "scaffold_race.py"
            target_args.extend(["--mod", args.mod, "--name", args.name])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "parent_race", None):
                target_args.extend(["--parent-race", args.parent_race])
            if getattr(args, "parent_guid", None):
                target_args.extend(["--parent-guid", args.parent_guid])
            if getattr(args, "race_uuid", None):
                target_args.extend(["--race-uuid", args.race_uuid])
            if getattr(args, "table_uuid", None):
                target_args.extend(["--table-uuid", args.table_uuid])
            if getattr(args, "equipment", None):
                target_args.extend(["--equipment", args.equipment])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub == "origin":
            script_target = AUTHORING_DIR / "scaffold_origin.py"
            target_args.extend(["--mod", args.mod, "--name", args.name])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "equipment", None):
                target_args.extend(["--equipment", args.equipment])
            if getattr(args, "class_uuid", None):
                target_args.extend(["--class-uuid", args.class_uuid])
            if getattr(args, "race_uuid", None):
                target_args.extend(["--race-uuid", args.race_uuid])
            if getattr(args, "body_type", None) is not None:
                target_args.extend(["--body-type", str(args.body_type)])
            if getattr(args, "body_shape", None) is not None:
                target_args.extend(["--body-shape", str(args.body_shape)])
            if getattr(args, "passives", None):
                target_args.extend(["--passives", ",".join(args.passives) if isinstance(args.passives, list) else args.passives])
            if getattr(args, "uuid", None):
                target_args.extend(["--uuid", args.uuid])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub in ("appearance", "appearance-visual", "appearance_visual"):
            script_target = AUTHORING_DIR / "scaffold_appearance_visual.py"
            target_args.extend(["--mod", args.mod, "--name", args.name, "--visual-resource", args.visual_resource])
            if getattr(args, "slot", None):
                target_args.extend(["--slot", args.slot])
            if getattr(args, "race", None):
                target_args.extend(["--race", args.race])
            if getattr(args, "body_type", None) is not None:
                target_args.extend(["--body-type", str(args.body_type)])
            if getattr(args, "body_shape", None) is not None:
                target_args.extend(["--body-shape", str(args.body_shape)])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "uuid", None):
                target_args.extend(["--uuid", args.uuid])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub == "stat":
            script_target = AUTHORING_DIR / "scaffold_stat_entry.py"
            target_args.extend(["--mod", args.mod, "--type", args.type, "--name", args.name])
            if getattr(args, "display_name", None):
                target_args.extend(["--display-name", args.display_name])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "using", None):
                target_args.extend(["--using", args.using])
            if getattr(args, "props", None):
                target_args.extend(["--props", ",".join(args.props) if isinstance(args.props, list) else args.props])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub == "progression":
            script_target = AUTHORING_DIR / "scaffold_progression_node.py"
            target_args.extend(["--mod", args.mod, "--class", args.class_name, "--level", str(args.level)])
            if getattr(args, "subclass", None):
                target_args.extend(["--subclass", args.subclass])
            if getattr(args, "multiclass", False):
                target_args.append("--multiclass")
            if getattr(args, "table_uuid", None):
                target_args.extend(["--table-uuid", args.table_uuid])
            if getattr(args, "passives", None):
                target_args.extend(["--passives", ",".join(args.passives) if isinstance(args.passives, list) else args.passives])
            if getattr(args, "boosts", None):
                target_args.extend(["--boosts", ",".join(args.boosts) if isinstance(args.boosts, list) else args.boosts])
            if getattr(args, "spells", None):
                target_args.extend(["--spells", ",".join(args.spells) if isinstance(args.spells, list) else args.spells])
            if getattr(args, "spell_count", None) is not None:
                target_args.extend(["--spell-count", str(args.spell_count)])
            if getattr(args, "feat", False):
                target_args.append("--feat")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub in ("root-template", "root_template"):
            script_target = AUTHORING_DIR / "scaffold_root_template.py"
            target_args.extend(["--mod", args.mod, "--item", args.item])
            if getattr(args, "visual_preset", None):
                target_args.extend(["--visual-preset", args.visual_preset])
            if getattr(args, "parent_template", None):
                target_args.extend(["--parent-template", args.parent_template])
            if getattr(args, "display_handle", None):
                target_args.extend(["--display-handle", args.display_handle])
            if getattr(args, "description_handle", None):
                target_args.extend(["--description-handle", args.description_handle])
            if getattr(args, "icon", None):
                target_args.extend(["--icon", args.icon])
            if getattr(args, "no_link_stat", False):
                target_args.append("--no-link-stat")
            if getattr(args, "list_presets", False):
                target_args.append("--list-presets")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif actual_sub in ("icon-uvs", "icon_uvs"):
            script_target = AUTHORING_DIR / "scaffold_icon_uvs.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "icon_names", None):
                target_args.extend(["--icon-names", ",".join(args.icon_names) if isinstance(args.icon_names, list) else args.icon_names])
            if getattr(args, "icons_dir", None):
                target_args.extend(["--icons-dir", args.icons_dir])
            if getattr(args, "atlas_name", None):
                target_args.extend(["--atlas-name", args.atlas_name])
            if getattr(args, "atlas_uuid", None):
                target_args.extend(["--atlas-uuid", args.atlas_uuid])
            if getattr(args, "icon_size", None) is not None:
                target_args.extend(["--icon-size", str(args.icon_size)])
            if getattr(args, "atlas_size", None) is not None:
                target_args.extend(["--atlas-size", str(args.atlas_size)])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

    elif cmd == "mod":
        if sub == "conflict":
            script_target = DIAGNOSTICS_DIR / "check_mod_conflicts.py"
            if args.all:
                target_args.append("--all")
            elif args.mod2 and args.candidate:
                target_args.extend(["--mod1", args.candidate, "--mod2", args.mod2])
            elif args.candidate:
                target_args.extend(["--candidate", args.candidate])
                if args.against_library:
                    target_args.append("--against-library")
            else:
                emitter.error(
                    message="bg3 mod conflict requires a candidate mod or --all.",
                    code="INVALID_ARGUMENTS",
                    exit_code=ExitCode.USAGE,
                    exit_process=False,
                )
                return ExitCode.USAGE

        elif sub == "validate":
            script_target = DIAGNOSTICS_DIR / "validate_mod.py"
            if getattr(args, "mod_identifier", None):
                target_args.append(args.mod_identifier)
            if getattr(args, "all", False):
                target_args.append("--all")
            if getattr(args, "strict", False):
                target_args.append("--strict")
            if getattr(args, "fix", False):
                target_args.append("--fix")

        elif sub == "create":
            script_target = AUTHORING_DIR / "create_mod_scaffold.py"
            target_args.extend(["--name", args.name])
            if getattr(args, "slug", None):
                target_args.extend(["--slug", args.slug])
            if getattr(args, "uuid", None):
                target_args.extend(["--uuid", args.uuid])
            if getattr(args, "author", None):
                target_args.extend(["--author", args.author])
            if getattr(args, "description", None):
                target_args.extend(["--description", args.description])
            if getattr(args, "version", None):
                target_args.extend(["--version", args.version])
            if getattr(args, "unlock_level_curve", False):
                target_args.append("--unlock-level-curve")
            for dep in getattr(args, "dependency", []):
                target_args.extend(["--dependency", dep])
            if getattr(args, "output_dir", None):
                target_args.extend(["--output-dir", args.output_dir])
            if getattr(args, "type", None):
                target_args.extend(["--type", args.type])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub == "add-dependency":
            script_target = AUTHORING_DIR / "add_mod_dependency.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "dependencies", None):
                target_args.extend(args.dependencies)
            for d in getattr(args, "dep", []):
                target_args.extend(["--dep", d])
            for td in getattr(args, "test_dep", []):
                target_args.extend(["--test-dep", td])
            if getattr(args, "test_only", False):
                target_args.append("--test-only")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("bump-version", "bump_version"):
            script_target = CORE_DIR / "bump_mod_version.py"
            if getattr(args, "mod", None):
                target_args.extend(["--mod", args.mod])
            if getattr(args, "patch", False):
                target_args.append("--patch")
            elif getattr(args, "minor", False):
                target_args.append("--minor")
            elif getattr(args, "major", False):
                target_args.append("--major")
            elif getattr(args, "build", False):
                target_args.append("--build")
            elif getattr(args, "show", False):
                target_args.append("--show")
            elif getattr(args, "set", None):
                target_args.extend(["--set", args.set])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub == "pack":
            script_target = PACKAGING_DIR / "pack_mod_pak.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "output", None):
                target_args.extend(["--out", args.output])
            if getattr(args, "output_dir", None):
                target_args.extend(["--output-dir", args.output_dir])
            if getattr(args, "publish_local", False):
                target_args.append("--publish-local")
            if getattr(args, "clean_local", False):
                target_args.append("--clean-local")
            if getattr(args, "include_projects", False):
                target_args.append("--include-projects")
            if getattr(args, "uncompressed", False):
                target_args.append("--uncompressed")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("sync-loca", "sync_loca"):
            script_target = DIAGNOSTICS_DIR / "sync_localization.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "check", False):
                target_args.append("--check")
            if getattr(args, "prune", False):
                target_args.append("--prune")
            if getattr(args, "backup", False):
                target_args.append("--backup")
            if getattr(args, "compile", False):
                target_args.append("--compile")
            if getattr(args, "sync_languages", False):
                target_args.append("--sync-languages")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("sync-game", "sync_game"):
            script_target = PACKAGING_DIR / "sync_game_data.py"
            if getattr(args, "mods", None):
                target_args.extend(["--mods"] + args.mods)
            if getattr(args, "source_dir", None):
                target_args.extend(["--source-dir", args.source_dir])
            if getattr(args, "data_dir", None):
                target_args.extend(["--data-dir", args.data_dir])
            if getattr(args, "clean_legacy", False):
                target_args.append("--clean-legacy")
            if getattr(args, "no_clean_legacy", False):
                target_args.append("--no-clean-legacy")
            if getattr(args, "clean_custom", False):
                target_args.append("--clean-custom")
            if getattr(args, "clean_mod", None):
                target_args.extend(["--clean-mod", args.clean_mod])
            if getattr(args, "bump_build", False):
                target_args.append("--bump-build")
            if getattr(args, "watch", False):
                target_args.append("--watch")
            if getattr(args, "interval", None) is not None:
                target_args.extend(["--interval", str(args.interval)])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub == "patch":
            script_target = AUTHORING_DIR / "generate_compat_patch.py"
            target_args.extend(["--mod1", args.mod1, "--mod2", args.mod2])
            if getattr(args, "name", None):
                target_args.extend(["--name", args.name])
            if getattr(args, "mode", None):
                target_args.extend(["--mode", args.mode])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("diagnose-logs", "diagnose_logs"):
            script_target = DIAGNOSTICS_DIR / "diagnose_toolkit_logs.py"
            if getattr(args, "mod", None):
                target_args.extend(["--mod", args.mod])
            if getattr(args, "toolkit_dir", None):
                target_args.extend(["--toolkit-dir", args.toolkit_dir])
            if getattr(args, "type", None):
                target_args.extend(["--type", args.type])
            if getattr(args, "severity", None):
                target_args.extend(["--severity", args.severity])
            if getattr(args, "subsystem", None):
                target_args.extend(["--subsystem", args.subsystem])
            if getattr(args, "limit", None) is not None:
                target_args.extend(["--limit", str(args.limit)])
            if getattr(args, "follow", False):
                target_args.append("--follow")
            if getattr(args, "list_logs", False):
                target_args.append("--list-logs")
            if getattr(args, "info", False):
                target_args.append("--info")
            if getattr(args, "purge", False):
                target_args.append("--purge")
            if getattr(args, "keep", None) is not None:
                target_args.extend(["--keep", str(args.keep)])
            if getattr(args, "days", None) is not None:
                target_args.extend(["--days", str(args.days)])
            if getattr(args, "all", False):
                target_args.append("--all")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
            if getattr(args, "yes", False):
                target_args.append("--yes")

        elif sub in ("inspect-save", "inspect_save"):
            script_target = DIAGNOSTICS_DIR / "inspect_save_game.py"
            if getattr(args, "save", None):
                target_args.extend(["--save", args.save])
            if getattr(args, "save_dir", None):
                target_args.extend(["--save-dir", args.save_dir])
            if getattr(args, "audit", False):
                target_args.append("--audit")

        elif sub in ("inject-treasure", "inject_treasure"):
            script_target = AUTHORING_DIR / "inject_treasure_table.py"
            target_args.extend(["--mod", args.mod, "--item", args.item])
            if getattr(args, "container", None):
                target_args.extend(["--container", args.container])
            if getattr(args, "count", None) is not None:
                target_args.extend(["--count", str(args.count)])
            if getattr(args, "ratio", None) is not None:
                target_args.extend(["--ratio", str(args.ratio)])
            if getattr(args, "start_level", None) is not None:
                target_args.extend(["--start-level", str(args.start_level)])
            if getattr(args, "raw_item_name", False):
                target_args.append("--raw-item-name")
            if getattr(args, "list_containers", False):
                target_args.append("--list-containers")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

        elif sub in ("render-desc", "render_desc"):
            script_target = CORE_DIR / "render_modio_description.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "write", False):
                target_args.append("--write")

    elif cmd == "loadorder":
        script_target = CORE_DIR / "manage_load_order.py"
        if sub == "list":
            target_args.append("--list")
            if getattr(args, "profile", None):
                target_args.extend(["--profile", args.profile])
        elif sub == "sync":
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Sync my_mods into active load order profile?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            target_args.append("--sync")
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "clean":
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Clean invalid mods from load order profile?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            target_args.append("--clean")
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub in ("enable", "activate"):
            target_args.extend(["--enable", args.mod])
            if getattr(args, "order", None) is not None:
                target_args.extend(["--order", str(args.order)])
            if not getattr(args, "with_deps", True):
                target_args.append("--no-deps")
            for td in getattr(args, "test_dep", []):
                target_args.extend(["--test-dep", td])
            if getattr(args, "isolate", False):
                target_args.append("--isolate")
            if getattr(args, "quarantine", False):
                target_args.append("--quarantine")
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "disable":
            target_args.extend(["--disable", args.mod])
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "validate":
            target_args.append("--validate")
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
        elif sub == "isolate":
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Isolate mod in load order (all unrelated mods will be disabled in modsettings.lsx)?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            target_args.extend(["--enable", args.mod, "--isolate"])
            if getattr(args, "quarantine", False):
                target_args.append("--quarantine")
            if not getattr(args, "with_deps", True):
                target_args.append("--no-deps")
            for td in getattr(args, "test_dep", []):
                target_args.extend(["--test-dep", td])
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "restore":
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Restore quarantined mods back to active Mods directory?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            target_args.append("--restore")
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub in ("dedup", "deduplicate"):
            target_args.append("--dedup")
            if getattr(args, "path", None):
                target_args.extend(["--path", args.path])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

    elif cmd == "modio":
        if sub == "search":
            script_target = CORE_DIR / "modio_search.py"
            target_args.extend(["--query", args.query, "--limit", str(args.limit)])
            if getattr(args, "platform", None):
                target_args.extend(["--platform", args.platform])
            if getattr(args, "include_tracked", False):
                target_args.append("--include-tracked")
        elif sub == "sync":
            script_target = CORE_DIR / "modio_sync.py"
            if getattr(args, "prune", False) and not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Prune unsubscribed mods from library and disk?",
                        non_interactive_yes=getattr(args, "yes", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y or --yes when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE

            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
            if getattr(args, "prune", False):
                target_args.append("--prune")
            if getattr(args, "limit", None) is not None:
                target_args.extend(["--limit", str(args.limit)])
            if getattr(args, "filter", None):
                target_args.extend(["--filter", args.filter])
            if getattr(args, "skip_updates", False):
                target_args.append("--skip-updates")
            if getattr(args, "token", None):
                target_args.extend(["--token", args.token])
        elif sub == "extract":
            script_target = CORE_DIR / "modio_extract.py"
            if getattr(args, "query", None):
                target_args.extend(["--query", args.query])
            if getattr(args, "pak", None):
                target_args.extend(["--pak", args.pak])
            if getattr(args, "output_dir", None):
                target_args.extend(["--output-dir", args.output_dir])
            if getattr(args, "write_spec", False):
                target_args.append("--write-spec")
            if getattr(args, "update_library", False):
                target_args.append("--update-library")
        elif sub == "update":
            script_target = CORE_DIR / "modio_update.py"
            if getattr(args, "query", None):
                target_args.extend(["--query", args.query])
            if getattr(args, "all", False):
                target_args.append("--all")
            if getattr(args, "check_only", False):
                target_args.append("--check-only")
            if getattr(args, "force", False):
                target_args.append("--force")
            if getattr(args, "list_tracked", False):
                target_args.append("--list-tracked")
        elif sub in ("update-metadata", "update_metadata"):
            script_target = CORE_DIR / "modio_update_metadata.py"
            target_args.extend(["--mod", args.mod])
            if getattr(args, "tags", None):
                target_args.extend(["--tags", ",".join(args.tags) if isinstance(args.tags, list) else args.tags])
            if getattr(args, "confirm", False):
                target_args.append("--confirm")
        elif sub in ("create-collection", "create_collection"):
            script_target = CORE_DIR / "modio_create_collection.py"
            if getattr(args, "library", None):
                target_args.extend(["--library", args.library])
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
        elif sub == "purge":
            script_target = CORE_DIR / "purge_library.py"
            if not getattr(args, "dry_run", False):
                try:
                    confirm_action(
                        "Purge all cataloged mods from mods/ and reset mods/library.md?",
                        non_interactive_yes=getattr(args, "yes", False) or getattr(args, "force", False),
                        force_non_interactive=args.json,
                    )
                except NonInteractiveConfirmationError as exc:
                    emitter.error(
                        message=str(exc),
                        code="CONFIRMATION_REQUIRED",
                        remediation="Pass -y, --yes, or -f when running in automated scripts or agent skills.",
                        exit_code=ExitCode.USAGE,
                        exit_process=False,
                    )
                    return ExitCode.USAGE
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")
            if getattr(args, "force", False):
                target_args.append("--force")
            if getattr(args, "mods_dir", None):
                target_args.extend(["--mods-dir", args.mods_dir])
            if getattr(args, "library_path", None):
                target_args.extend(["--library-path", args.library_path])
        elif sub in ("update-catalog", "update_catalog"):
            script_target = CORE_DIR / "update_library_catalog.py"
            if getattr(args, "write", False):
                target_args.append("--write")
            if getattr(args, "check", False):
                target_args.append("--check")
            if getattr(args, "stdout", False):
                target_args.append("--stdout")

    elif cmd == "query":
        script_target = CORE_DIR / "query_mod_database.py"
        if getattr(args, "search", None):
            target_args.extend(["--search", args.search])
        if getattr(args, "slot", None):
            target_args.extend(["--slot", args.slot])
        if getattr(args, "boost", None):
            target_args.extend(["--boost", args.boost])
        if getattr(args, "passive", None):
            target_args.extend(["--passive", args.passive])
        if getattr(args, "rarity", None):
            target_args.extend(["--rarity", args.rarity])
        if getattr(args, "mod", None):
            target_args.extend(["--mod", args.mod])
        if getattr(args, "limit", None) is not None:
            target_args.extend(["--limit", str(args.limit)])
        if getattr(args, "compact", False):
            target_args.append("--compact")
        if getattr(args, "reindex", False):
            target_args.append("--reindex")

    elif cmd in ("build", "sim"):
        script_target = THEORYCRAFTING_DIR / "simulate_build_synergy.py"
        if getattr(args, "classes", None):
            target_args.extend(["--classes", args.classes])
        if getattr(args, "stats", None):
            target_args.extend(["--stats", args.stats])
        if getattr(args, "gear", None):
            target_args.extend(["--gear", ",".join(args.gear) if isinstance(args.gear, list) else args.gear])
        if getattr(args, "dpr_sequence", None):
            target_args.extend(["--dpr-sequence", args.dpr_sequence])
        if getattr(args, "target_ac", None) is not None:
            target_args.extend(["--target-ac", str(args.target_ac)])

    elif cmd == "tools":
        script_target = CORE_DIR / "tools.py"
        if sub == "list":
            target_args.append("--list")
            if getattr(args, "category", None):
                target_args.extend(["--category", args.category])
            if getattr(args, "categories", False):
                target_args.append("--categories")
            if getattr(args, "full", False):
                target_args.append("--full")
        elif sub == "search":
            target_args.extend(["--search", args.query])
        elif sub == "info":
            target_args.extend(["--info", args.tool_name])
        elif sub == "verify":
            target_args.append("--verify")
            if getattr(args, "audit_skills", False):
                target_args.append("--audit-skills")

    elif cmd == "env":
        if sub == "paths":
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
            if args.json:
                print(json.dumps(paths_data, indent=2))
            else:
                color = emitter.color
                print(f"\n{color.bold('=== XDG Base Directory Paths ===')}")
                for var, info in paths_data.items():
                    status = color.green("[exists]") if info["exists"] else color.yellow("[not created]")
                    print(f"{color.bold(f'{var:17}')}: {info['path']} {status}")
                print("")
            return ExitCode.OK

        script_target = CORE_DIR / "setup_environment.py"
        if sub == "check":
            target_args.append("--check")
        elif sub == "setup":
            if getattr(args, "dry_run", False):
                target_args.append("--dry-run")

    elif cmd in ("save", "saves"):
        script_target = CORE_DIR / "manage_saves.py"
        if sub:
            target_args.append(str(sub))
        if getattr(args, "save", None):
            if sub == "inspect":
                target_args.append(args.save)
            else:
                target_args.extend(["--save", args.save])
        if getattr(args, "save_dir", None):
            target_args.extend(["--save-dir", args.save_dir])
        if getattr(args, "audit", False):
            target_args.append("--audit")
        if getattr(args, "dest", None):
            target_args.extend(["--dest", args.dest])
        if getattr(args, "keep", None) is not None:
            target_args.extend(["--keep", str(args.keep)])
        if getattr(args, "days", None) is not None:
            target_args.extend(["--days", str(args.days)])
        if getattr(args, "all", False):
            target_args.append("--all")
        if getattr(args, "force_all", False):
            target_args.append("--force-all")
        if getattr(args, "no_keep_latest", False):
            target_args.append("--no-keep-latest")
        if getattr(args, "backup", False):
            target_args.append("--backup")
        if getattr(args, "backup_dir", None):
            target_args.extend(["--backup-dir", args.backup_dir])
        if getattr(args, "dry_run", False):
            target_args.append("--dry-run")
        if getattr(args, "yes", False):
            target_args.append("--yes")

    if not script_target:
        emitter.error(
            message=f"Handler script not found for command '{cmd} {sub}'.",
            code="COMMAND_NOT_FOUND",
            exit_code=ExitCode.UNAVAILABLE,
            exit_process=False,
        )
        return ExitCode.UNAVAILABLE

    # Propagate global --config flag if specified
    if getattr(args, "config", None):
        target_args.extend(["--config", str(args.config)])

    # Propagate global --json flag if requested
    if args.json:
        target_args.append("--json")

    force_module = os.environ.get("_BG3_FORCE_MODULE_DISPATCH") == "1"
    if script_target.is_file() and not force_module:
        cmd_line = [sys.executable, str(script_target)] + target_args
    else:
        module_name = resolve_module_fallback(script_target)
        if not module_name:
            emitter.error(
                message=f"Handler script not found on disk or as module for command '{cmd} {sub}'.",
                code="COMMAND_NOT_FOUND",
                exit_code=ExitCode.UNAVAILABLE,
                exit_process=False,
            )
            return ExitCode.UNAVAILABLE
        cmd_line = [sys.executable, "-m", module_name] + target_args
    emitter.log(f"Executing: {' '.join(cmd_line)}", level="INFO")

    proc = subprocess.run(cmd_line)
    return proc.returncode


def main() -> None:
    """CLI execution entrypoint."""
    if "--no-color" in sys.argv:
        os.environ["NO_COLOR"] = "1"

    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(ExitCode.USAGE)

    args = parser.parse_args()

    color = ConsoleColor(stream=sys.stderr, force_color=False)
    emitter = OutputEmitter(json_mode=args.json, color=color)

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
    except Exception as exc:
        emitter.error(
            message=f"Unhandled internal error: {exc}",
            code="INTERNAL_ERROR",
            exit_code=ExitCode.GENERAL,
            exit_process=True,
        )


if __name__ == "__main__":
    main()
