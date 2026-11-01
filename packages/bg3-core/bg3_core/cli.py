"""
Baldur's Gate 3 Mod Studio & Mod.io Automation Workspace — Lightweight CLI Dispatcher.

Transparently routes noun-verb CLI commands to self-contained module entrypoints.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
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


def _extract_target_args(raw_tokens: List[str], cmd: str, sub: str) -> List[str]:
    """Extract raw positional and keyword arguments following the command and subcommand."""
    if not cmd or cmd not in raw_tokens:
        return []
    idx = raw_tokens.index(cmd)
    if sub and sub in raw_tokens[idx + 1:]:
        sub_idx = idx + 1 + raw_tokens[idx + 1:].index(sub)
        if cmd == "mod" and sub == "scaffold" and sub_idx + 1 < len(raw_tokens) and not raw_tokens[sub_idx + 1].startswith("-"):
            return raw_tokens[sub_idx + 2:]
        return raw_tokens[sub_idx + 1:]
    return raw_tokens[idx + 1:]


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
        target_tokens = _extract_target_args(raw_tokens, cmd, sub.split()[0] if " " in sub else sub)
        res.args = target_tokens
        return res


# Canonical registry mapping (group, subcmd) -> CommandSpec
COMMAND_REGISTRY: Dict[Tuple[str, str], CommandSpec] = {
    # mod group
    ("mod", "create"): CommandSpec("bg3_authoring.create_mod_scaffold", "Create a new mod project scaffold with meta.lsx, localization, and folder structure", "authoring", "bg3_authoring"),
    ("mod", "scaffold"): CommandSpec("bg3_authoring", "Scaffold mod asset definitions (class, feat, spell-list, etc.)", "authoring", "bg3_authoring"),
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

# Scaffold asset types forwarded from scaffold <asset> and mod scaffold <asset>
SCAFFOLD_ASSETS = {
    "class": "scaffold_class_description",
    "progression": "scaffold_progression_node",
    "feat": "scaffold_feat",
    "action-resource": "scaffold_action_resource",
    "spell-list": "scaffold_spell_list",
    "level-map": "scaffold_level_map",
    "default-values": "scaffold_default_values",
    "stat": "scaffold_stat_entry",
    "root-template": "scaffold_root_template",
    "icon-uvs": "scaffold_icon_uvs",
    "race": "scaffold_race",
    "origin": "scaffold_origin",
    "appearance": "scaffold_appearance_visual",
    "appearance-visual": "scaffold_appearance_visual",
    "tag": "scaffold_tag",
}

for asset, mod_suffix in SCAFFOLD_ASSETS.items():
    spec = CommandSpec(
        f"bg3_authoring.{mod_suffix}",
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


def build_parser() -> JsonCompliantArgumentParser:
    """Build lightweight command tree for introspection by tools.py and test suites."""
    parser = JsonCompliantArgumentParser(
        prog="bg3",
        description="Baldur's Gate 3 Mod Studio & Mod.io Automation Workspace",
    )
    parser.add_argument("--json", action="store_true", help="Format all output as machine-readable JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose diagnostics on stderr")
    parser.add_argument("--config", help="Custom environment configuration file path")

    subparsers = parser.add_subparsers(dest="command", parser_class=JsonCompliantArgumentParser)

    # Add direct top-level commands
    for name, spec in DIRECT_COMMANDS.items():
        cmd_p = subparsers.add_parser(name, help=spec.help, add_help=False)
        cmd_p.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    # Group commands into subparsers
    groups: Dict[str, Dict[str, CommandSpec]] = {}
    for (group, subcmd), spec in COMMAND_REGISTRY.items():
        groups.setdefault(group, {})[subcmd] = spec

    for group, subcmds in groups.items():
        group_p = subparsers.add_parser(group, help=f"{group.capitalize()} operations")
        sub_sp = group_p.add_subparsers(dest="subcommand", parser_class=JsonCompliantArgumentParser)
        for subcmd, spec in subcmds.items():
            if " " in subcmd:
                continue  # Skip composite alias keys in parser reflection
            sub_p = sub_sp.add_parser(subcmd, help=spec.help, add_help=False)
            sub_p.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

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


def dispatch_command(args: Any, emitter: OutputEmitter) -> int:
    """Dispatch command to target module entrypoint."""
    # Normalize command and subcommand from args or sys.argv
    cmd: str = str(getattr(args, "command", "") or "")
    sub: str = str(getattr(args, "subcommand", "") or "")

    if not cmd:
        raw_tokens = [a for a in sys.argv[1:] if not a.startswith("-")]
        if raw_tokens:
            cmd = raw_tokens[0]
            if len(raw_tokens) > 1:
                sub = raw_tokens[1]

    json_mode = getattr(args, "json", False) or "--json" in sys.argv
    verbose = getattr(args, "verbose", False) or "-v" in sys.argv or "--verbose" in sys.argv

    # Handle missing subcommand for multi-command groups
    if cmd in ("mod", "loadorder", "modio", "save", "scaffold", "tools", "env") and not sub:
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
    target_args: List[str] = []

    if cmd in DIRECT_COMMANDS:
        spec = DIRECT_COMMANDS[cmd]
        target_args = list(getattr(args, "args", []))
    elif (cmd, sub) in COMMAND_REGISTRY:
        spec = COMMAND_REGISTRY[(cmd, sub)]
        target_args = list(getattr(args, "args", []))
    elif cmd == "mod" and sub == "scaffold":
        raw_rest = list(getattr(args, "args", []))
        if raw_rest and ("scaffold", raw_rest[0]) in COMMAND_REGISTRY:
            spec = COMMAND_REGISTRY[("scaffold", raw_rest[0])]
            target_args = raw_rest[1:]
    elif cmd == "build" and sub in ("sim", "simulate"):
        spec = COMMAND_REGISTRY[("build", "simulate")]
        target_args = list(getattr(args, "args", []))

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
                message=f"Command '{full_cmd}' requires the '{pkg.replace('_', '-')}' package (install via 'pip install {pkg.replace('_', '-')}' or 'pip install bg3-mod-studio').",
                code="PACKAGE_NOT_INSTALLED",
                exit_code=ExitCode.UNAVAILABLE,
                exit_process=False,
            )
            return ExitCode.UNAVAILABLE

    # In-process execution for env paths
    if cmd == "env" and sub == "paths":
        return _execute_env_paths(json_mode, emitter)

    is_help = any(a in target_args for a in ("-h", "--help"))

    # Argument translation for save noun-verb syntax (manage_saves expects subcommand as first positional)
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
        cand_attr = getattr(args, "candidate", None)
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

    force_module = os.environ.get("_BG3_FORCE_MODULE_DISPATCH") == "1"
    script_path = _find_module_file(spec.target_module)

    if script_path and script_path.is_file() and not force_module:
        cmd_line = [sys.executable, str(script_path)] + target_args
    else:
        cmd_line = [sys.executable, "-m", spec.target_module] + target_args

    if verbose:
        emitter.log(f"Executing: {' '.join(cmd_line)}", level="INFO")

    proc = subprocess.run(cmd_line)
    return proc.returncode


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
