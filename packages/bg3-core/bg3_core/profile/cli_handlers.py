"""CLI argument parsing and dispatch handlers for BG3 load order management."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from ..cli.common import ConsoleColor
from ..env_paths import resolve_mod_dir
from ..exceptions import BG3Error
from .mod_resolver import ensure_dependency_paks, resolve_dependency_metadata
from .modsettings_io import (
    create_default_modsettings,
    detect_modsettings_path,
    disable_mod,
    enable_mod,
    get_appdata_mods_dir,
    get_mod_metadata_from_workspace,
    parse_modsettings,
    resolve_all_dependencies,
    validate_load_order,
)
from .quarantine import (
    clean_steam_data_paks,
    deduplicate_installed_paks,
    isolate_load_order,
    quarantine_unrelated_paks,
    restore_quarantined_paks,
)
from .sorter import auto_sort_load_order

_color = ConsoleColor(stream=sys.stderr)
BOLD = "\033[1m" if _color.enabled else ""
GREEN = "\033[32m" if _color.enabled else ""
YELLOW = "\033[33m" if _color.enabled else ""
RED = "\033[31m" if _color.enabled else ""
CYAN = "\033[36m" if _color.enabled else ""
RESET = "\033[0m" if _color.enabled else ""


def build_load_order_parser() -> argparse.ArgumentParser:
    """Build the argument parser for manage_load_order."""
    parser = argparse.ArgumentParser(
        description="Inspect, activate, reorder, and validate Baldur's Gate 3 modsettings.lsx load order."
    )
    parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    parser.add_argument("--list", action="store_true", help="Display active mod load order")
    parser.add_argument(
        "--enable",
        "--activate",
        dest="enable",
        help="Enable a mod by name/slug from authored, subscribed, or AppData Mods",
    )
    parser.add_argument(
        "--order", type=int, help="Target load order index (>= 1) when enabling or reordering a mod"
    )
    parser.add_argument("--disable", help="Disable a mod by name/UUID from active load order")
    parser.add_argument(
        "--with-deps",
        dest="with_deps",
        action="store_true",
        default=True,
        help="Automatically enable declared dependencies from meta.lsx (default: True)",
    )
    parser.add_argument(
        "--no-deps",
        dest="with_deps",
        action="store_false",
        help="Do not automatically enable dependencies",
    )
    parser.add_argument(
        "--test-dep",
        action="append",
        default=[],
        dest="test_deps",
        help="Temporary test dependency name, slug, or UUID to activate ahead of the mod",
    )
    parser.add_argument(
        "--isolate",
        "--clean",
        dest="isolate",
        action="store_true",
        help="Clean-room isolation: disable all other mods except base game and dependencies in modsettings.lsx",
    )
    parser.add_argument(
        "--quarantine",
        action="store_true",
        help="Physically quarantine unrelated .pak files to Mods_Disabled/ (Warning: triggers mod.io auto-download for subscribed mods)",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore quarantined mods from Mods_Disabled/ back to active Mods directory",
    )
    parser.add_argument(
        "--dedup",
        "--deduplicate",
        dest="dedup",
        action="store_true",
        help="Deduplicate installed .pak files in AppData Mods",
    )
    parser.add_argument("--validate", action="store_true", help="Validate current load order rules")
    parser.add_argument(
        "--auto-sort",
        "--sort",
        dest="auto_sort",
        action="store_true",
        help="Topologically auto-sort active mods based on dependencies",
    )
    parser.add_argument(
        "--create-default", action="store_true", help="Create default modsettings.lsx if missing"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview modifications without writing to disk"
    )
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument(
        "subcommand",
        nargs="?",
        choices=[
            "list",
            "sync",
            "clean",
            "enable",
            "disable",
            "validate",
            "auto-sort",
            "sort",
            "isolate",
            "quarantine",
            "restore",
            "dedup",
            "create-default",
        ],
        help="Subcommand action for loadorder",
    )
    parser.add_argument("mod_name", nargs="?", help="Mod name or UUID for enable/disable/isolate")
    return parser


def _resolve_subcommand_aliases(args: argparse.Namespace) -> None:
    """Map positional subcommands to explicit flag combinations."""
    sc = args.subcommand
    if not sc:
        return
    if sc in ("list", "sync"):
        args.list = True
        return
    if sc in ("enable", "activate"):
        args.enable = args.mod_name or args.enable
        return
    if sc == "disable":
        args.disable = args.mod_name or args.disable
        return
    if sc in ("clean", "isolate"):
        args.isolate = True
        if args.mod_name:
            args.enable = args.mod_name
        return
    if sc in ("auto-sort", "sort"):
        args.auto_sort = True
        return
    if sc == "validate":
        args.validate = True
        return
    if sc == "quarantine":
        args.quarantine = True
        return
    if sc == "restore":
        args.restore = True
        return
    if sc == "dedup":
        args.dedup = True
        return
    if sc == "create-default":
        args.create_default = True
        return


def _resolve_modsettings_path(args: argparse.Namespace) -> Path:
    """Resolve and validate the modsettings.lsx file path."""
    modsettings_path = Path(args.path) if args.path else detect_modsettings_path()
    if not modsettings_path:
        msg = "Could not locate modsettings.lsx. Specify path with --path."
        if args.json:
            print(json.dumps({"error": msg, "success": False}, indent=2))
        else:
            print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)
        sys.exit(1)
    return modsettings_path


def _handle_create_default(modsettings_path: Path, args: argparse.Namespace) -> None:
    """Handle the --create-default action and exit."""
    created = False
    if not modsettings_path.is_file():
        create_default_modsettings(modsettings_path)
        created = True
    if args.json:
        print(
            json.dumps(
                {
                    "status": "created" if created else "already_exists",
                    "path": str(modsettings_path),
                },
                indent=2,
            )
        )
    else:
        if created:
            print(f"✓ Created default modsettings.lsx at: {modsettings_path}")
        else:
            print(f"modsettings.lsx already exists at: {modsettings_path}")
    sys.exit(0)


def _dispatch_auto_sort(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle topological load order sorting."""
    success, sorted_order, meta_sort = auto_sort_load_order(modsettings_path, dry_run=args.dry_run)
    action_result["auto_sort"] = {
        "success": success,
        "sorted_order": sorted_order,
        **meta_sort,
    }
    if not args.json:
        verb = "[DRY-RUN] Would reorder" if args.dry_run else "Reordered"
        print(f"✓ {verb} {len(sorted_order)} active mod(s) via topological dependency sorting.")


def _dispatch_restore(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle restoring quarantined mod pak archives."""
    mods_dir = get_appdata_mods_dir(modsettings_path)
    if not mods_dir:
        msg = "Could not locate AppData Mods directory for restore."
        if args.json:
            print(json.dumps({"error": msg, "success": False}, indent=2))
        else:
            print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)
        sys.exit(1)
    restored = restore_quarantined_paks(mods_dir, dry_run=args.dry_run)
    action_result["restore"] = {
        "count": len(restored),
        "files": restored,
        "dry_run": args.dry_run,
    }
    if not args.json:
        verb = "[DRY-RUN] Would restore" if args.dry_run else "Restored"
        print(f"✓ {verb} {len(restored)} mod archive(s) from Mods_Disabled/ to Mods/.")
        for r in restored:
            print(f"  ↳ {r['filename']}")
    if not (args.enable or args.list or args.validate or args.disable):
        sys.exit(0)


def _dispatch_dedup(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle deduplicating installed paks and cleaning redundant archives."""
    mods_dir = get_appdata_mods_dir(modsettings_path)
    if not mods_dir:
        msg = "Could not locate AppData Mods directory for deduplication."
        if args.json:
            print(json.dumps({"error": msg, "success": False}, indent=2))
        else:
            print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)
        sys.exit(1)
    deduped = deduplicate_installed_paks(mods_dir, dry_run=args.dry_run)
    steam_cleaned = clean_steam_data_paks(dry_run=args.dry_run)
    action_result["deduplicate"] = {
        "count": len(deduped),
        "actions": deduped,
        "steam_cleaned": steam_cleaned,
        "dry_run": args.dry_run,
    }
    if not args.json:
        verb = "[DRY-RUN] Would deduplicate" if args.dry_run else "Deduplicated"
        print(f"✓ {verb} {len(deduped)} duplicate/backup file(s).")
        for d in deduped:
            if d.get("action") == "deduplicated":
                print(f"  ↳ Kept '{d['winner']}', archived '{d['redundant']}'")
            elif d.get("action") == "removed_bak":
                print(f"  ↳ Archived backup file '{d['file']}'")
        if steam_cleaned:
            print(f"✓ Cleaned {len(steam_cleaned)} duplicate .pak archive(s) from Steam Data/Mods.")
    if not (args.enable or args.list or args.validate or args.disable):
        sys.exit(0)


def _collect_test_dependencies(mod_name: str, cli_test_deps: Sequence[str]) -> list[dict]:
    """Collect and resolve metadata for declared and CLI-specified test dependencies."""
    mod_dir = resolve_mod_dir(mod_name, prefer_my_mods=True)
    test_dep_queries = list(cli_test_deps)
    if mod_dir and (mod_dir / ".test_deps.json").is_file():
        try:
            cfg = json.loads((mod_dir / ".test_deps.json").read_text(encoding="utf-8"))
            for td in cfg.get("test_dependencies", []):
                if td not in test_dep_queries:
                    test_dep_queries.append(td)
        except (json.JSONDecodeError, OSError):
            pass

    resolved_test_deps: list[dict] = []
    for t_query in test_dep_queries:
        t_meta = get_mod_metadata_from_workspace(t_query)
        if not t_meta:
            try:
                t_meta = resolve_dependency_metadata(t_query, auto_document=True)
            except (BG3Error, OSError, ValueError):
                pass
        if t_meta and t_meta.get("UUID"):
            resolved_test_deps.append(t_meta)
    return resolved_test_deps


def _dispatch_enable(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle enabling a mod, its declared dependencies, and test dependencies."""
    mod_meta = get_mod_metadata_from_workspace(args.enable)
    if not mod_meta:
        msg = f"Mod '{args.enable}' not found in authored, subscribed, or AppData Mods."
        if args.json:
            print(json.dumps({"error": msg, "success": False}, indent=2))
        else:
            print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)
        sys.exit(1)

    resolved_deps: list[dict] = []
    missing_deps: list[dict] = []
    if args.with_deps:
        resolved_deps, missing_deps = resolve_all_dependencies(mod_meta)

    resolved_test_deps = _collect_test_dependencies(args.enable, args.test_deps)

    pak_sync_results = []
    if args.with_deps and not args.dry_run:
        all_deps = list(resolved_deps) + list(resolved_test_deps)
        pak_sync_results = ensure_dependency_paks(all_deps)

    if args.isolate:
        keep_uuids = {
            mod_meta["UUID"],
            *(d["UUID"] for d in resolved_deps),
            *(d["UUID"] for d in resolved_test_deps),
        }
        mods_dir = get_appdata_mods_dir(modsettings_path)
        clean_steam_results = clean_steam_data_paks(dry_run=args.dry_run)
        dedup_results = []
        quarantined_paks = []
        if mods_dir and mods_dir.is_dir():
            dedup_results = deduplicate_installed_paks(mods_dir, dry_run=args.dry_run)
            if getattr(args, "quarantine", False):
                quarantined_paks = quarantine_unrelated_paks(
                    mods_dir, keep_uuids, dry_run=args.dry_run
                )

        action_result["clean_steam_data"] = clean_steam_results
        action_result["deduplicate"] = dedup_results
        action_result["quarantined_paks"] = quarantined_paks

        isolated_count = isolate_load_order(modsettings_path, keep_uuids, dry_run=args.dry_run)
        action_result["isolated_count"] = isolated_count
        if not args.json:
            verb = "[DRY-RUN] Would isolate" if args.dry_run else "Isolated"
            print(
                f"✓ {verb} load order (disabled {isolated_count} mod entries in modsettings.lsx)."
            )
            if clean_steam_results:
                print(
                    f"  ↳ Cleaned {len(clean_steam_results)} duplicate .pak archive(s) from Steam Data/Mods."
                )
            if dedup_results:
                print(
                    f"  ↳ Deduplicated {len(dedup_results)} conflicting/redundant .pak archive(s)."
                )
            if quarantined_paks:
                print(
                    f"  ↳ Quarantined {len(quarantined_paks)} unrelated .pak archive(s) to Mods_Disabled/."
                )

    current_order_idx = 1
    dep_results = []
    for dep in resolved_deps:
        req_idx = current_order_idx if args.isolate else None
        dep_changed, dep_status = enable_mod(
            modsettings_path, dep, order_index=req_idx, dry_run=args.dry_run
        )
        current_order_idx += 1
        dep_results.append(
            {
                "mod": dep.get("Name", dep["UUID"]),
                "uuid": dep["UUID"],
                "changed": dep_changed,
                "status": dep_status,
            }
        )
        if not args.json and dep_changed:
            verb = "[DRY-RUN] Would enable dependency" if args.dry_run else "Enabled dependency"
            print(f"  ↳ {verb} '{dep.get('Name', dep['UUID'])}' ({dep['UUID']})")

    test_dep_results = []
    for tdep in resolved_test_deps:
        req_idx = current_order_idx if args.isolate else None
        tdep_changed, tdep_status = enable_mod(
            modsettings_path, tdep, order_index=req_idx, dry_run=args.dry_run
        )
        current_order_idx += 1
        test_dep_results.append(
            {
                "mod": tdep.get("Name", tdep["UUID"]),
                "uuid": tdep["UUID"],
                "changed": tdep_changed,
                "status": tdep_status,
            }
        )
        if not args.json and tdep_changed:
            verb = (
                "[DRY-RUN] Would enable test dependency"
                if args.dry_run
                else "Enabled test dependency"
            )
            print(f"  🧪 {verb} '{tdep.get('Name', tdep['UUID'])}' ({tdep['UUID']})")

    target_order = (
        args.order if args.order is not None else (current_order_idx if args.isolate else None)
    )
    changed, status_str = enable_mod(
        modsettings_path, mod_meta, order_index=target_order, dry_run=args.dry_run
    )
    action_result["enable"] = {
        "mod": mod_meta["Name"],
        "uuid": mod_meta["UUID"],
        "changed": changed,
        "status": status_str,
        "order_index": args.order,
        "dry_run": args.dry_run,
        "dependencies": dep_results,
        "test_dependencies": test_dep_results,
        "pak_sync": pak_sync_results,
        "missing_dependencies": missing_deps,
    }
    if not args.json:
        if changed:
            verb = (
                "[DRY-RUN] Would enable/reorder" if args.dry_run else f"Successfully {status_str}"
            )
            print(
                f"✓ {verb} '{mod_meta['Name']}' ({mod_meta['UUID']}) in load order at {modsettings_path}!"
            )
        else:
            print(f"Mod '{mod_meta['Name']}' is already active in load order.")

        if missing_deps:
            print(
                f"{YELLOW}⚠ Warning: {len(missing_deps)} declared dependenc{'y' if len(missing_deps) == 1 else 'ies'} not found in workspace or AppData Mods:{RESET}"
            )
            for md in missing_deps:
                print(f"  • {md.get('Name', 'Unknown')} ({md.get('UUID', 'No UUID')})")


def _dispatch_disable(
    modsettings_path: Path,
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Handle disabling a mod from active load order."""
    try:
        changed = disable_mod(modsettings_path, args.disable, dry_run=args.dry_run)
        action_result["disable"] = {
            "mod": args.disable,
            "changed": changed,
            "dry_run": args.dry_run,
        }
        if not args.json:
            if changed:
                action_desc = "[DRY-RUN] Would disable" if args.dry_run else "Successfully disabled"
                print(f"✓ {action_desc} '{args.disable}' from load order at {modsettings_path}!")
            else:
                print(f"Mod '{args.disable}' was not found in active load order.")
    except (BG3Error, OSError, ValueError) as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"{RED}Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)


def _dispatch_validate(
    parsed: dict[str, Any],
    args: argparse.Namespace,
    action_result: dict[str, Any],
) -> None:
    """Validate current load order rules and display issues."""
    issues = validate_load_order(parsed)
    action_result["validation"] = {
        "valid": len(issues) == 0,
        "active_count": len(parsed["order"]),
        "issues": issues,
    }
    if not args.json:
        if not issues:
            print(f"{GREEN}✓ Load order is valid ({len(parsed['order'])} mods active).{RESET}")
        else:
            print(f"{YELLOW}Load order issues detected:{RESET}")
            for issue in issues:
                print(f"  • {issue}")


def _dispatch_list(parsed: dict[str, Any], modsettings_path: Path) -> None:
    """Display active load order table to stdout."""
    print(f"\n{BOLD}{CYAN}=== Active Baldur's Gate 3 Load Order ==={RESET}")
    print(f"Location: {modsettings_path}\n")
    print(f"{'Idx':<4} | {'Mod Name':<28} | {'UUID':<38} | {'Version'}")
    print("-" * 85)
    for idx, u in enumerate(parsed["order"]):
        m = parsed["mods"].get(u, {})
        name = m.get("Name", "Unknown")
        v64 = m.get("Version64", "-")
        print(f"{idx:<4} | {name:<28} | {u:<38} | {v64}")
    print(f"\nTotal active mods: {len(parsed['order'])}\n")


def main() -> None:
    parser = build_load_order_parser()
    args = parser.parse_args()
    _resolve_subcommand_aliases(args)

    modsettings_path = _resolve_modsettings_path(args)
    if args.create_default:
        _handle_create_default(modsettings_path, args)

    if not modsettings_path.is_file() and not args.enable:
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "missing_modsettings",
                        "path": str(modsettings_path),
                        "order": [],
                        "mods": {},
                    },
                    indent=2,
                )
            )
        else:
            print(
                f"{YELLOW}Notice: modsettings.lsx does not exist yet at {modsettings_path}.{RESET}"
            )
            print(
                "Run with --create-default to initialize, or --enable <Mod> to generate with mod."
            )
        sys.exit(0)

    if args.json and not (
        args.list or args.enable or args.disable or args.validate or args.auto_sort
    ):
        args.list = True

    action_result: dict[str, Any] = {}

    if args.auto_sort:
        _dispatch_auto_sort(modsettings_path, args, action_result)
    if args.restore:
        _dispatch_restore(modsettings_path, args, action_result)
    if args.dedup:
        _dispatch_dedup(modsettings_path, args, action_result)
    if args.enable:
        _dispatch_enable(modsettings_path, args, action_result)
    if args.disable:
        _dispatch_disable(modsettings_path, args, action_result)

    parsed = parse_modsettings(modsettings_path)

    if args.validate:
        _dispatch_validate(parsed, args, action_result)

    if args.list and not args.json:
        _dispatch_list(parsed, modsettings_path)

    if args.json:
        payload = {
            "path": str(modsettings_path),
            "order": parsed["order"],
            "mods": parsed["mods"],
            **action_result,
        }
        print(json.dumps(payload, indent=2))
        if args.validate and action_result.get("validation", {}).get("issues"):
            sys.exit(1)
        sys.exit(0)

    if args.validate and action_result.get("validation", {}).get("issues"):
        sys.exit(1)

    if args.list or args.enable or args.disable or args.validate or args.auto_sort:
        sys.exit(0)

    parser.print_help()


__all__ = [
    "build_load_order_parser",
    "main",
]
