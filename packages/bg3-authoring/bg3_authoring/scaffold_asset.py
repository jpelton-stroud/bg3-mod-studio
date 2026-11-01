#!/usr/bin/env python3
"""
scaffold_asset.py - Unified Larian Patch 8 Asset Scaffolding Engine.
Facade and CLI router re-exporting modular asset scaffolding submodules.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from bg3_core.larian_parsers import split_larian_items
from bg3_core.cli_common import ConsoleColor, ExitCode

from bg3_authoring.scaffold_atlas import (
    scaffold_icon_uvs,
)
from bg3_authoring.scaffold_character import (
    VANILLA_PARENT_RACES,
    VANILLA_RACE_UUIDS,
    scaffold_origin,
    scaffold_race,
    scaffold_tag,
)
from bg3_authoring.scaffold_common import (
    PATCH_8_VERSION_ATTRIBUTES,
    ScaffoldResult,
    create_empty_lsx,
    generate_placeholder_png,
    get_or_create_root_children,
    prettify_xml,
    resolve_mod_paths,
)
from bg3_authoring.scaffold_mechanics import (
    CLASS_TABLE_UUIDS,
    STAT_TYPE_CONFIG,
    SUBCLASS_TABLE_UUIDS,
    VANILLA_CLASS_TABLES,
    VANILLA_PARENT_CLASSES,
    scaffold_action_resource,
    scaffold_class,
    scaffold_default_values,
    scaffold_feat,
    scaffold_level_map,
    scaffold_progression,
    scaffold_spell_list,
    scaffold_stat,
)
from bg3_authoring.scaffold_visuals import (
    VISUAL_PRESETS,
    scaffold_appearance_visual,
    scaffold_root_template,
)

ASSET_HANDLERS: dict[str, Any] = {
    "class": scaffold_class,
    "class-description": scaffold_class,
    "progression": scaffold_progression,
    "feat": scaffold_feat,
    "action-resource": scaffold_action_resource,
    "spell-list": scaffold_spell_list,
    "level-map": scaffold_level_map,
    "default-values": scaffold_default_values,
    "stat": scaffold_stat,
    "root-template": scaffold_root_template,
    "icon-uvs": scaffold_icon_uvs,
    "race": scaffold_race,
    "origin": scaffold_origin,
    "appearance": scaffold_appearance_visual,
    "appearance-visual": scaffold_appearance_visual,
    "tag": scaffold_tag,
}


def scaffold_asset(asset_type: str, **kwargs: Any) -> ScaffoldResult:
    """Unified entrypoint to scaffold any supported Baldur's Gate 3 asset type."""
    key = asset_type.strip().lower()
    handler = ASSET_HANDLERS.get(key)
    if not handler:
        valid_keys = ", ".join(sorted(ASSET_HANDLERS.keys()))
        raise ValueError(f"Unknown asset type '{asset_type}'. Valid types: {valid_keys}")
    return handler(**kwargs)


# -----------------------------------------------------------------------------
# Command Line Interface
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified Larian Patch 8 Asset Scaffolding Engine.")
    subparsers = parser.add_subparsers(dest="asset_type", required=True, help="Asset type to scaffold")

    # Class
    p_class = subparsers.add_parser("class", help="Scaffold class or subclass definition")
    p_class.add_argument("--mod", required=True, help="Target mod name or path in my_mods/")
    p_class.add_argument("--name", required=True, help="Internal class/subclass name")
    p_class.add_argument("--display-name", help="Display name in game UI")
    p_class.add_argument("--description", help="Description in character creation & level-up tree")
    p_class.add_argument("--parent-class", help="Vanilla parent class preset (e.g. rogue, wizard)")
    p_class.add_argument("--parent-guid", help="Explicit parent class GUID")
    p_class.add_argument("--class-uuid", help="Explicit UUID for this class/subclass")
    p_class.add_argument("--table-uuid", help="Explicit ProgressionTableUUID")
    p_class.add_argument("--base-hp", type=int, default=8, help="Base HP at level 1")
    p_class.add_argument("--hp-per-level", type=int, default=5, help="HP gain per level")
    p_class.add_argument("--primary-ability", type=int, default=1, help="Primary ability score enum")
    p_class.add_argument("--spell-ability", type=int, default=0, help="Spellcasting ability enum")
    p_class.add_argument("--register-in-parent", action="store_true", default=True, help="Inject into parent Progressions.lsx")
    p_class.add_argument("--no-register-in-parent", dest="register_in_parent", action="store_false")
    p_class.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    p_class.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # Progression
    p_prog = subparsers.add_parser("progression", help="Scaffold level progression node")
    p_prog.add_argument("--mod", required=True)
    p_prog.add_argument("--name", "--class", dest="name", required=True, help="Target class or progression name")
    p_prog.add_argument("--level", type=int, required=True)
    p_prog.add_argument("--table-uuid")
    p_prog.add_argument("--progression-type", type=int, default=0)
    p_prog.add_argument("--multiclass", action="store_true", help="Mark progression node as multiclass entry (sets ProgressionType=2)")
    p_prog.add_argument("--subclass", help="Optional subclass name (sets ProgressionType=1)")
    p_prog.add_argument("--passives")
    p_prog.add_argument("--spells")
    p_prog.add_argument("--selectors")
    p_prog.add_argument("--dry-run", action="store_true")
    p_prog.add_argument("--json", action="store_true")

    # Feat
    p_feat = subparsers.add_parser("feat", help="Scaffold feat definition")
    p_feat.add_argument("--mod", required=True)
    p_feat.add_argument("--name", required=True)
    p_feat.add_argument("--display-name")
    p_feat.add_argument("--description")
    p_feat.add_argument("--passives")
    p_feat.add_argument("--selectors")
    p_feat.add_argument("--requirements")
    p_feat.add_argument("--can-be-picked-multiple-times", action="store_true")
    p_feat.add_argument("--feat-uuid")
    p_feat.add_argument("--dry-run", action="store_true")
    p_feat.add_argument("--json", action="store_true")

    # Action Resource
    p_ar = subparsers.add_parser("action-resource", help="Scaffold action resource definition")
    p_ar.add_argument("--mod", required=True)
    p_ar.add_argument("--name", required=True)
    p_ar.add_argument("--display-name")
    p_ar.add_argument("--description")
    p_ar.add_argument("--replenish-type", default="ShortRest")
    p_ar.add_argument("--max-level", type=int, default=0)
    p_ar.add_argument("--dice-type", type=int, default=0)
    p_ar.add_argument("--party-action-resource", action="store_true")
    p_ar.add_argument("--uuid")
    p_ar.add_argument("--dry-run", action="store_true")
    p_ar.add_argument("--json", action="store_true")

    # Spell List
    p_sl = subparsers.add_parser("spell-list", help="Scaffold spell list or passive list")
    p_sl.add_argument("--mod", required=True)
    p_sl.add_argument("--comment")
    p_sl.add_argument("--spells", nargs="*")
    p_sl.add_argument("--passives", nargs="*")
    p_sl.add_argument("--uuid")
    p_sl.add_argument("--dry-run", action="store_true")
    p_sl.add_argument("--json", action="store_true")

    # Level Map
    p_lm = subparsers.add_parser("level-map", help="Scaffold level map scaling curve")
    p_lm.add_argument("--mod", required=True)
    p_lm.add_argument("--name", required=True)
    p_lm.add_argument("--levels", required=True)
    p_lm.add_argument("--dice-type", type=int)
    p_lm.add_argument("--uuid")
    p_lm.add_argument("--dry-run", action="store_true")
    p_lm.add_argument("--json", action="store_true")

    # Default Values
    p_dv = subparsers.add_parser("default-values", help="Scaffold default abilities/skills/spells for class")
    p_dv.add_argument("--mod", required=True)
    p_dv.add_argument("--class-name", "--class", dest="class_name", required=True)
    p_dv.add_argument("--abilities")
    p_dv.add_argument("--skills")
    p_dv.add_argument("--spells")
    p_dv.add_argument("--table-uuid")
    p_dv.add_argument("--level", type=int, default=1)
    p_dv.add_argument("--dry-run", action="store_true")
    p_dv.add_argument("--json", action="store_true")

    # Stat
    p_stat = subparsers.add_parser("stat", help="Scaffold stat entry in txt files")
    p_stat.add_argument("--mod", required=True)
    p_stat.add_argument("--type", required=True)
    p_stat.add_argument("--name", required=True)
    p_stat.add_argument("--using")
    p_stat.add_argument("--display-name")
    p_stat.add_argument("--description")
    p_stat.add_argument("--properties", "--props", dest="properties", nargs="*")
    p_stat.add_argument("--dry-run", action="store_true")
    p_stat.add_argument("--json", action="store_true")

    # Root Template
    p_rt = subparsers.add_parser("root-template", help="Scaffold 3D root template GameObject in _merged.lsx")
    p_rt.add_argument("--mod", required=True)
    p_rt.add_argument("--name", "--item", dest="name", required=True)
    p_rt.add_argument("--preset", "--visual-preset", dest="preset", default="greatsword")
    p_rt.add_argument("--template-type", default="item")
    p_rt.add_argument("--stats")
    p_rt.add_argument("--visual-resource")
    p_rt.add_argument("--parent-template-id")
    p_rt.add_argument("--display-name")
    p_rt.add_argument("--description")
    p_rt.add_argument("--icon")
    p_rt.add_argument("--uuid")
    p_rt.add_argument("--dry-run", action="store_true")
    p_rt.add_argument("--json", action="store_true")

    # Icon UVs
    p_icon = subparsers.add_parser("icon-uvs", help="Calculate icon UVs on texture atlas")
    p_icon.add_argument("--mod", required=True)
    p_icon.add_argument("--atlas-name", default="Icons")
    p_icon.add_argument("--icons", "--icon-names", dest="icons", nargs="*")
    p_icon.add_argument("--icon-size", type=int, default=64)
    p_icon.add_argument("--atlas-size", type=int)
    p_icon.add_argument("--atlas-width", type=int, default=2048)
    p_icon.add_argument("--atlas-height", type=int, default=2048)
    p_icon.add_argument("--uuid", "--atlas-uuid", dest="uuid")
    p_icon.add_argument("--dry-run", action="store_true")
    p_icon.add_argument("--json", action="store_true")

    # Race
    p_race = subparsers.add_parser("race", help="Scaffold race and subrace definitions")
    p_race.add_argument("--mod", required=True)
    p_race.add_argument("--name", required=True)
    p_race.add_argument("--display-name")
    p_race.add_argument("--description")
    p_race.add_argument("--parent-race")
    p_race.add_argument("--parent-guid")
    p_race.add_argument("--race-uuid")
    p_race.add_argument("--table-uuid")
    p_race.add_argument("--equipment")
    p_race.add_argument("--dry-run", action="store_true")
    p_race.add_argument("--json", action="store_true")

    # Origin
    p_orig = subparsers.add_parser("origin", help="Scaffold playable origin character")
    p_orig.add_argument("--mod", required=True)
    p_orig.add_argument("--name", required=True)
    p_orig.add_argument("--display-name")
    p_orig.add_argument("--description")
    p_orig.add_argument("--equipment")
    p_orig.add_argument("--class-uuid")
    p_orig.add_argument("--race-uuid")
    p_orig.add_argument("--body-type", type=int, choices=[0, 1], default=0)
    p_orig.add_argument("--body-shape", type=int, choices=[0, 1], default=0)
    p_orig.add_argument("--passives")
    p_orig.add_argument("--uuid")
    p_orig.add_argument("--dry-run", action="store_true")
    p_orig.add_argument("--json", action="store_true")

    # Appearance
    p_app = subparsers.add_parser("appearance", aliases=["appearance-visual"], help="Scaffold character creation appearance visuals")
    p_app.add_argument("--mod", required=True)
    p_app.add_argument("--name", required=True)
    p_app.add_argument("--visual-resource", required=True)
    p_app.add_argument("--slot", default="Hair")
    p_app.add_argument("--race")
    p_app.add_argument("--body-type", type=int, choices=[0, 1], default=0)
    p_app.add_argument("--body-shape", type=int, choices=[0, 1], default=0)
    p_app.add_argument("--display-name")
    p_app.add_argument("--uuid")
    p_app.add_argument("--dry-run", action="store_true")
    p_app.add_argument("--json", action="store_true")

    # Tag
    p_tag = subparsers.add_parser("tag", help="Scaffold dialogue and identity tag")
    p_tag.add_argument("--mod", required=True)
    p_tag.add_argument("--name", required=True)
    p_tag.add_argument("--display-name")
    p_tag.add_argument("--description")
    p_tag.add_argument("--category", action="append")
    p_tag.add_argument("--uuid")
    p_tag.add_argument("--dry-run", action="store_true")
    p_tag.add_argument("--json", action="store_true")

    return parser


def _cli_dispatch_class(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_class(
        mod_name_or_path=args.mod,
        name=args.name,
        display_name=args.display_name,
        description=args.description,
        parent_class=args.parent_class,
        parent_guid=args.parent_guid,
        class_uuid=args.class_uuid,
        progression_table_uuid=args.table_uuid,
        base_hp=args.base_hp,
        hp_per_level=args.hp_per_level,
        primary_ability=args.primary_ability,
        spell_casting_ability=args.spell_ability,
        register_in_parent=args.register_in_parent,
        dry_run=args.dry_run,
    )


def _cli_dispatch_progression(args: argparse.Namespace) -> ScaffoldResult:
    prog_type = 2 if getattr(args, "multiclass", False) else (
        1 if getattr(args, "subclass", None) else args.progression_type
    )
    prog_name = args.subclass if getattr(args, "subclass", None) else args.name
    return scaffold_progression(
        mod_name_or_path=args.mod,
        name=prog_name,
        level=args.level,
        table_uuid=args.table_uuid,
        progression_type=prog_type,
        passives=args.passives,
        spells=args.spells,
        selectors=args.selectors,
        dry_run=args.dry_run,
    )


def _cli_dispatch_feat(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_feat(
        mod_name_or_path=args.mod,
        name=args.name,
        display_name=args.display_name,
        description=args.description,
        passives=args.passives,
        selectors=args.selectors,
        requirements=args.requirements,
        can_be_picked_multiple_times=args.can_be_picked_multiple_times,
        feat_uuid=args.feat_uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_action_resource(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_action_resource(
        mod_name_or_path=args.mod,
        name=args.name,
        display_name=args.display_name,
        description=args.description,
        replenish_type=args.replenish_type,
        max_level=args.max_level,
        dice_type=args.dice_type,
        resource_uuid=args.uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_spell_list(args: argparse.Namespace) -> ScaffoldResult:
    spells = ",".join(args.spells) if isinstance(args.spells, list) else args.spells
    passives = ",".join(args.passives) if isinstance(args.passives, list) else args.passives
    return scaffold_spell_list(
        mod_name_or_path=args.mod,
        spells=spells,
        passives=passives,
        comment=args.comment,
        list_uuid=args.uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_level_map(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_level_map(
        mod_name_or_path=args.mod,
        name=args.name,
        levels=args.levels,
        dice_type=args.dice_type or 0,
        map_uuid=args.uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_default_values(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_default_values(
        mod_name_or_path=args.mod,
        class_name=args.class_name,
        abilities=args.abilities,
        skills=args.skills,
        spells=args.spells,
        table_uuid=args.table_uuid,
        level=args.level,
        dry_run=args.dry_run,
    )


def _cli_dispatch_stat(args: argparse.Namespace) -> ScaffoldResult:
    prop_dict: dict[str, str] = {}
    if args.properties:
        for raw_prop in args.properties:
            for item in split_larian_items(raw_prop, separators=(",",)):
                if "=" in item:
                    k, v = item.split("=", 1)
                    prop_dict[k.strip()] = v.strip()
                elif " " in item:
                    k, v = item.split(" ", 1)
                    prop_dict[k.strip()] = v.strip()
    return scaffold_stat(
        mod_name_or_path=args.mod,
        entry_type=args.type,
        name=args.name,
        using=args.using,
        display_name=args.display_name,
        description=args.description,
        properties=prop_dict,
        dry_run=args.dry_run,
    )


def _cli_dispatch_root_template(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_root_template(
        mod_name_or_path=args.mod,
        name=args.name,
        preset=args.preset,
        template_type=args.template_type,
        stats=args.stats,
        visual_resource=args.visual_resource,
        parent_template_id=args.parent_template_id,
        display_name=args.display_name,
        description=args.description,
        icon=args.icon,
        template_uuid=args.uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_icon_uvs(args: argparse.Namespace) -> ScaffoldResult:
    icons_list: list[str] = []
    if args.icons:
        for item in args.icons:
            icons_list.extend(split_larian_items(item, separators=(",",)))
    w = args.atlas_size if getattr(args, "atlas_size", None) else args.atlas_width
    h = args.atlas_size if getattr(args, "atlas_size", None) else args.atlas_height
    return scaffold_icon_uvs(
        mod_name_or_path=args.mod,
        atlas_name=args.atlas_name,
        icons=icons_list,
        icon_size=args.icon_size,
        atlas_width=w,
        atlas_height=h,
        atlas_uuid=args.uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_race(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_race(
        mod_name_or_path=args.mod,
        name=args.name,
        display_name=args.display_name,
        description=args.description,
        parent_race=args.parent_race,
        parent_guid=args.parent_guid,
        race_uuid=args.race_uuid,
        progression_table_uuid=args.table_uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_origin(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_origin(
        mod_name_or_path=args.mod,
        name=args.name,
        display_name=args.display_name,
        description=args.description,
        class_uuid=args.class_uuid,
        race_uuid=args.race_uuid,
        origin_uuid=args.uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_appearance(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_appearance_visual(
        mod_name_or_path=args.mod,
        name=args.name,
        visual_resource=args.visual_resource,
        slot=args.slot,
        race=args.race or "human",
        body_type=args.body_type,
        body_shape=args.body_shape,
        display_name=args.display_name,
        visual_uuid=args.uuid,
        dry_run=args.dry_run,
    )


def _cli_dispatch_tag(args: argparse.Namespace) -> ScaffoldResult:
    return scaffold_tag(
        mod_name_or_path=args.mod,
        name=args.name,
        description=args.description,
        display_name=args.display_name,
        categories=args.category,
        tag_uuid=args.uuid,
        dry_run=args.dry_run,
    )


CLI_DISPATCHERS = {
    "class": _cli_dispatch_class,
    "class-description": _cli_dispatch_class,
    "progression": _cli_dispatch_progression,
    "feat": _cli_dispatch_feat,
    "action-resource": _cli_dispatch_action_resource,
    "spell-list": _cli_dispatch_spell_list,
    "level-map": _cli_dispatch_level_map,
    "default-values": _cli_dispatch_default_values,
    "stat": _cli_dispatch_stat,
    "root-template": _cli_dispatch_root_template,
    "icon-uvs": _cli_dispatch_icon_uvs,
    "race": _cli_dispatch_race,
    "origin": _cli_dispatch_origin,
    "appearance": _cli_dispatch_appearance,
    "appearance-visual": _cli_dispatch_appearance,
    "tag": _cli_dispatch_tag,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        atype = args.asset_type
        dispatcher = CLI_DISPATCHERS.get(atype)
        if not dispatcher:
            raise ValueError(f"Unsupported asset type: '{atype}'")

        res = dispatcher(args)

        color = ConsoleColor(stream=sys.stdout)
        if getattr(args, "json", False):
            print(json.dumps(res.to_dict(), indent=2))
        else:
            tag_str = color.yellow(" [DRY-RUN]") if res.dry_run else ""
            status = color.green("[✓]")
            print(f"{status} Successfully scaffolded {atype} '{res.name}'{tag_str}:")
            for k, v in res.to_dict().items():
                if k not in ("success", "mod", "dry_run"):
                    print(f"    {k}: {v}")
        return ExitCode.SUCCESS

    except Exception as e:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            err_color = ConsoleColor(stream=sys.stderr)
            print(f"{err_color.red('[ERROR]')} {e}", file=sys.stderr)
        return ExitCode.GENERAL


if __name__ == "__main__":
    sys.exit(main())
