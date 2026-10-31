#!/usr/bin/env python3
"""Baldur's Gate 3 Mod Studio — Unified Tooling Registry & CLI Discovery Hub.

Provides machine-readable discovery, search, schema inspection, and verification
for all studio CLI commands dynamically generated from the unified command parser.

Usage:
    bg3 tools --list [--category <cat>] [--json]
    bg3 tools --search "<intent or keyword>" [--json]
    bg3 tools --info <tool_name> [--json]
    bg3 tools --verify [--json]
    bg3 tools --audit-skills [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from bg3_core.env_paths import REPO_ROOT, get_studio_dir

CATEGORIES: Dict[str, str] = {
    "authoring": "Mod authoring, stat generation, progression curves, and asset scaffolding",
    "packaging": "Pure Python LSPK .pak archive building and game data deployment",
    "diagnostics": "Static validation, conflict detection, handle auditing, and save file inspection",
    "management": "Load order management, version bumping, metadata generation, and setup",
    "library": "Mod.io API search, archive synchronization, and community mod database queries",
    "theorycrafting": "Combat DPR simulation, multiclass spell slots, and build mechanics",
}

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


def determine_category(group: str, subcmd: Optional[str] = None) -> str:
    """Resolve category for a command group or subcmd pair."""
    key = f"{group} {subcmd}" if subcmd else group
    if key in COMMAND_CATEGORY_OVERRIDES:
        return COMMAND_CATEGORY_OVERRIDES[key]
    if group in ("scaffold", "mod"):
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
        if action.default not in (None, argparse.SUPPRESS):
            flag_entry["default"] = action.default

        flags.append(flag_entry)

    return flags


def generate_intents(group: str, subcmd: str, summary: str, aliases: List[str]) -> List[str]:
    """Generate search intent keywords for discovery matching."""
    intents = set()
    intents.add(group)
    if subcmd:
        intents.add(subcmd)
        intents.add(f"{group} {subcmd}")
        intents.add(f"{group}-{subcmd}")

    for alias in aliases:
        intents.add(alias)
        intents.add(f"bg3 {alias}")

    if summary:
        for word in summary.replace(",", " ").replace(".", " ").replace("-", " ").split():
            clean_word = word.lower().strip()
            if len(clean_word) >= 3 and clean_word not in ("and", "the", "for", "with", "from"):
                intents.add(clean_word)

    return sorted(list(intents))


def extract_registry_from_parser(parser: Optional[argparse.ArgumentParser] = None) -> Dict[str, Any]:
    """
    Introspect the build_parser() CLI hierarchy dynamically to produce a comprehensive,
    canonical tool registry without any legacy script aliases.
    """
    if parser is None:
        from bg3_core.cli import build_parser
        parser = build_parser()

    tools: List[Dict[str, Any]] = []

    for action in parser._actions:
        if not (action.choices and isinstance(action.choices, dict)):
            continue

        for ca in getattr(action, "_choices_actions", []):
            group_name = ca.dest
            group_subp = action.choices[group_name]
            group_summary = ca.help or ""

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

                    all_aliases: List[str] = []
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

                all_aliases = []
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
        "description": "Baldur's Gate 3 Mod Studio & Mod.io Automation Workspace — Canonical Tool Registry",
        "categories": CATEGORIES,
        "tools": tools,
    }


_CACHED_REGISTRY: Optional[Dict[str, Any]] = None


def load_registry(force_refresh: bool = False) -> Dict[str, Any]:
    """Load and dynamically cache the machine-readable registry in memory."""
    global _CACHED_REGISTRY
    if _CACHED_REGISTRY is None or force_refresh:
        _CACHED_REGISTRY = extract_registry_from_parser()
    return _CACHED_REGISTRY


def find_tool(registry: Dict[str, Any], query: str) -> Optional[Dict[str, Any]]:
    """Find a tool by canonical command name or alias."""
    q_norm = query.strip().lower()
    if q_norm.startswith("bg3 "):
        q_norm = q_norm[4:].strip()

    for tool in registry.get("tools", []):
        t_name = tool.get("name", "").lower()
        t_cmd = tool.get("command", "").lower()
        t_cmd_short = t_cmd[4:].strip() if t_cmd.startswith("bg3 ") else t_cmd
        aliases = [a.lower() for a in tool.get("aliases", [])]

        match_targets = {t_name, t_cmd, t_cmd_short} | set(aliases)
        if q_norm in match_targets:
            return tool
    return None


def search_tools(registry: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Score and rank tools based on intent, keyword, name, and summary."""
    tokens = [t.lower() for t in query.strip().split() if t.strip()]
    if not tokens:
        return []

    scored_results = []
    for tool in registry.get("tools", []):
        score = 0
        name = tool.get("name", "").lower()
        cmd = tool.get("command", "").lower()
        category = tool.get("category", "").lower()
        summary = tool.get("summary", "").lower()
        desc = tool.get("description", "").lower()
        intents = [i.lower() for i in tool.get("intents", [])]

        full_query = query.strip().lower()

        if full_query in name or full_query in cmd:
            score += 100
        for intent in intents:
            if full_query in intent:
                score += 80
            elif intent in full_query:
                score += 60

        if full_query in summary:
            score += 40
        if full_query in desc:
            score += 20

        for t in tokens:
            if t in name or t in cmd:
                score += 30
            for intent in intents:
                if t in intent:
                    score += 25
            if t in category:
                score += 15
            if t in summary:
                score += 10
            if t in desc:
                score += 5

        if score > 0:
            tool_copy = dict(tool)
            tool_copy["relevance_score"] = score
            scored_results.append(tool_copy)

    scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored_results


def list_tools(registry: Dict[str, Any], category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Filter tools by category or return all."""
    tools = registry.get("tools", [])
    if category:
        cat_lower = category.strip().lower()
        tools = [t for t in tools if t.get("category", "").lower() == cat_lower]
    return tools


def verify_registry(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Verify that all registered CLI commands are valid, documented, and executable."""
    tools = registry.get("tools", [])
    missing_docs = []
    help_errors = []

    for tool in tools:
        cmd_name = tool.get("command", "")
        if not tool.get("summary"):
            missing_docs.append(f"{cmd_name}: Missing summary")

        parts = cmd_name.split()
        if parts and parts[0] == "bg3":
            cmd_args = parts[1:] + ["--help"]
            try:
                res = subprocess.run(
                    [sys.executable, "-m", "bg3_core.cli"] + cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res.returncode != 0:
                    help_errors.append({
                        "command": cmd_name,
                        "returncode": res.returncode,
                        "stderr": res.stderr.strip()[:200],
                    })
            except Exception as e:
                help_errors.append({"command": cmd_name, "error": str(e)})

    is_valid = not (missing_docs or help_errors)
    return {
        "valid": is_valid,
        "total_registered": len(tools),
        "missing_docs": missing_docs,
        "help_errors": help_errors,
    }


def audit_skills(registry: Dict[str, Any], skills_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Audit agent skills in .agents/skills/ for registry compliance, portability, and best practices."""
    if skills_dir is None:
        studio_skills = get_studio_dir() / ".agents" / "skills"
        if studio_skills.is_dir():
            skills_dir = studio_skills
        elif REPO_ROOT.is_dir():
            skills_dir = REPO_ROOT / ".agents" / "skills"
        else:
            skills_dir = studio_skills

    if not skills_dir.is_dir():
        return {
            "valid": False,
            "error": f"Skills directory not found at {skills_dir}",
            "skills": []
        }

    registered_names = set()
    for t in registry.get("tools", []):
        registered_names.add(t.get("name"))
        registered_names.add(t.get("command"))
        for a in t.get("aliases", []):
            registered_names.add(a)

    results: list[dict[str, Any]] = []
    total_refs = 0
    skills_with_discovery = 0
    all_unregistered = set()
    all_user_paths = []
    all_broken_links = []
    all_invalid_models = []
    non_kebab_skills = []
    kebab_pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"

    for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_path.parent.name
        try:
            content = skill_path.read_text(encoding="utf-8")
        except Exception as e:
            results.append({"skill": skill_name, "error": str(e), "status": "read_error"})
            continue

        # 1. Script references (flags any lingering loose .py or scripts/ paths)
        script_refs = sorted(list(set(re.findall(r"(?:scripts/|[a-zA-Z0-9_\-]+\.py)", content))))
        # Filter out self-mentions or legitimate docs
        forbidden_refs = [s for s in script_refs if s.startswith("scripts/") or (s not in registered_names and s.endswith(".py"))]
        total_refs += len(forbidden_refs)

        has_discovery_tip = (
            "bg3 tools" in content
            or "tools.py" in content
            or "registry" in content.lower()
        )
        if has_discovery_tip:
            skills_with_discovery += 1

        all_unregistered.update(forbidden_refs)

        # 2. Kebab-case naming check
        is_kebab = bool(re.match(kebab_pattern, skill_name))
        if not is_kebab:
            non_kebab_skills.append(skill_name)

        # 3. Path portability check (no /home/ or C:\Users\)
        user_paths = sorted(list(set(re.findall(r"(?:/home/|C:[/\\]Users[/\\])[a-zA-Z0-9_\-\.]+", content))))
        if user_paths:
            all_user_paths.extend([f"{skill_name}: {p}" for p in user_paths])

        # 4. Link integrity check
        broken_links = []
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
        for text, target in links:
            if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
                continue
            if target in ("profile_url", "..."):
                broken_links.append(f"[{text}]({target}) [placeholder]")
                continue
            clean = target[7:] if target.startswith("file://") else target
            clean_path = clean.split("#")[0]
            if not clean_path:
                continue
            target_file = (skill_path.parent / clean_path).resolve()
            via_agents_symlink = Path(os.path.normpath(os.path.join(str(skills_dir), skill_name, clean_path)))
            if not target_file.exists() and not via_agents_symlink.exists():
                broken_links.append(f"[{text}]({target}) [file not found: {clean_path}]")

        if broken_links:
            all_broken_links.extend([f"{skill_name}: {item}" for item in broken_links])

        # 5. Model inheritance check
        invalid_models = []
        for match in re.finditer(r"invoke_subagent\([^)]*Model=['\"]([^'\"]+)['\"]", content):
            model_val = match.group(1)
            if model_val != "inherit":
                invalid_models.append(model_val)
        for match in re.finditer(r"Model:\s*['\"]?([a-zA-Z0-9_-]+)['\"]?", content):
            model_val = match.group(1)
            if model_val != "inherit" and model_val not in ("None", "null"):
                invalid_models.append(model_val)
        if invalid_models:
            all_invalid_models.extend([f"{skill_name}: Model '{m}'" for m in invalid_models])

        results.append({
            "skill": skill_name,
            "has_discovery_tip": has_discovery_tip,
            "script_references": forbidden_refs,
            "broken_links": broken_links,
            "invalid_models": invalid_models,
            "is_kebab": is_kebab,
            "status": "fully_integrated" if has_discovery_tip and not forbidden_refs else "needs_alignment"
        })

    is_valid = (
        len(all_unregistered) == 0
        and len(all_user_paths) == 0
        and len(all_broken_links) == 0
        and len(all_invalid_models) == 0
        and len(non_kebab_skills) == 0
        and (skills_with_discovery == len(results) if results else True)
    )

    return {
        "valid": is_valid,
        "total_skills": len(results),
        "skills_with_discovery": skills_with_discovery,
        "discovery_percentage": round((skills_with_discovery / len(results) * 100), 1) if results else 100.0,
        "unregistered_scripts": sorted(list(all_unregistered)),
        "portability_violations": all_user_paths,
        "non_kebab_names": non_kebab_skills,
        "broken_link_violations": all_broken_links,
        "invalid_subagent_models": all_invalid_models,
        "skills": results
    }


def format_table(rows: List[List[str]], headers: List[str]) -> str:
    """Format tabular string output."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(val)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    row_lines = [
        " | ".join(str(r[i]).ljust(col_widths[i]) for i in range(len(headers)))
        for r in rows
    ]
    return f"{header_line}\n{sep_line}\n" + "\n".join(row_lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baldur's Gate 3 Mod Studio — Tooling Registry & CLI Discovery Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bg3 tools list
  bg3 tools list --category authoring
  bg3 tools search "stat handles"
  bg3 tools info scaffold stat
  bg3 tools verify
  bg3 tools verify --audit-skills
        """
    )
    parser.add_argument("--list", action="store_true", help="List all registered tools in the studio")
    parser.add_argument("--category", type=str, help="Filter listing by category (authoring, packaging, diagnostics, management, library, theorycrafting)")
    parser.add_argument("--categories", action="store_true", help="List all tool categories and descriptions")
    parser.add_argument("--search", type=str, help="Search tools by intent, keyword, or name")
    parser.add_argument("--info", type=str, help="Display detailed flags, examples, and schema for a specific tool")
    parser.add_argument("--verify", action="store_true", help="Run automated registry integrity verification test")
    parser.add_argument("--audit-skills", action="store_true", help="Audit agent skills in .agents/skills/ for registry compliance and tool discovery")
    parser.add_argument("--full", action="store_true", help="Include full schemas, flags, and examples when listing tools (default: compact manifest)")
    parser.add_argument("--json", action="store_true", help="Emit output formatted as JSON")

    # Positional subcommand dispatch
    parser.add_argument("subcommand", nargs="?", choices=["list", "search", "info", "verify", "audit"], help="Subcommand action")
    parser.add_argument("tool_name", nargs="?", help="Tool name or query for subcommand")

    args = parser.parse_args()
    registry = load_registry()

    if args.subcommand == "list":
        args.list = True
    elif args.subcommand == "search":
        args.search = args.tool_name
    elif args.subcommand == "info":
        args.info = args.tool_name
    elif args.subcommand == "verify":
        args.verify = True
    elif args.subcommand == "audit":
        args.audit_skills = True

    # 1. Categories
    if args.categories:
        categories = registry.get("categories", {})
        if args.json:
            print(json.dumps(categories, indent=2))
        else:
            rows = [[k, v] for k, v in categories.items()]
            print(f"\n📂 Tool Categories ({len(rows)}):\n")
            print(format_table(rows, ["Category", "Description"]))
            print()
        return

    # 1b. Audit Skills
    if args.audit_skills:
        report = audit_skills(registry)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            status_symbol = "[PASSED]" if report["valid"] else "[FAILED]"
            print(f"\nSkills Audit Report: {status_symbol}")
            print(f"  Total Skills:             {report['total_skills']}")
            print(f"  With Discovery Guidance:  {report['skills_with_discovery']} / {report['total_skills']} ({report['discovery_percentage']}%)")
            print(f"  Unregistered Scripts:     {len(report['unregistered_scripts'])}\n")

            rows = []
            for s in report.get("skills", []):
                disc_mark = "[✓]" if s["has_discovery_tip"] else "[✗]"
                ref_summary = ", ".join(s["script_references"]) if s["script_references"] else "(none)"
                rows.append([s["skill"], disc_mark, s["status"], ref_summary])

            print(format_table(rows, ["Skill Name", "Discovery", "Status", "Referenced Scripts"]))
            print()

            if report.get("portability_violations"):
                print("⚠️ Portability Violations (absolute user paths detected):")
                for v in report["portability_violations"]:
                    print(f"  - {v}")
                print()

            if report.get("broken_link_violations"):
                print("⚠️ Broken Link Violations (invalid relative markdown links):")
                for bl in report["broken_link_violations"]:
                    print(f"  - {bl}")
                print()

            if report.get("invalid_subagent_models"):
                print("⚠️ Subagent Model Violations (must use Model='inherit'):")
                for im in report["invalid_subagent_models"]:
                    print(f"  - {im}")
                print()

            if report.get("non_kebab_names"):
                print("⚠️ Naming Violations (skill directory names must be kebab-case):")
                for nk in report["non_kebab_names"]:
                    print(f"  - {nk}")
                print()

        sys.exit(0 if report["valid"] else 1)

    # 2. Verify
    if args.verify:
        verify_res = verify_registry(registry)
        if args.json:
            print(json.dumps(verify_res, indent=2))
        else:
            status = "PASSED" if verify_res["valid"] else "FAILED"
            print(f"\nRegistry Verification: [{status}]")
            print(f"  Total Registered: {verify_res['total_registered']}")
            print(f"  Missing Docs:     {len(verify_res['missing_docs'])}")
            print(f"  Help Failures:    {len(verify_res['help_errors'])}\n")
            if verify_res["missing_docs"]:
                print("Missing Documentation:")
                for d in verify_res["missing_docs"]:
                    print(f"  - {d}")
            if verify_res["help_errors"]:
                print("Help Invocation Errors:")
                for h in verify_res["help_errors"]:
                    print(f"  - {h['command']}: exit {h['returncode']}")
                    if h.get("stderr"):
                        print(f"    {h['stderr']}")
        sys.exit(0 if verify_res["valid"] else 1)

    # 3. Info
    if args.info:
        tool = find_tool(registry, args.info)
        if not tool:
            print(f"Error: Tool '{args.info}' not found in registry.", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(tool, indent=2))
        else:
            print(f"\n🛠️  Tool: {tool['name']}")
            print(f"Command:     {tool['command']}")
            print(f"Category:    {tool['category']}")
            print(f"Usage:       {tool['cli_usage']}")
            print(f"Summary:     {tool['summary']}")
            if tool.get("aliases"):
                print(f"Aliases:     {', '.join(tool['aliases'])}")
            print("\nOptions / Flags:")
            if tool.get("flags"):
                flag_rows = []
                for f in tool["flags"]:
                    req = "YES" if f.get("required") else "NO"
                    flag_rows.append([f["name"], f.get("type", "str"), req, f.get("description", "")])
                print(format_table(flag_rows, ["Flag", "Type", "Required", "Description"]))
            else:
                print("  (None or positional only)")
            print()
        return

    # 4. Search
    if args.search:
        results = search_tools(registry, args.search)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n🔍 Search Results for '{args.search}' ({len(results)} matches):\n")
            if not results:
                print("  No matching tools found. Try broader keywords or run 'bg3 tools list'.")
            else:
                rows = []
                for t in results[:10]:
                    rows.append([t["name"], t["category"], t["command"], t["summary"][:60]])
                print(format_table(rows, ["Tool Name", "Category", "Command", "Summary"]))
            print()
        return

    # 5. List
    if args.list or not any([args.search, args.info, args.verify, args.categories, args.audit_skills]):
        tools = list_tools(registry, args.category)
        if args.json:
            print(json.dumps(tools if args.full else [{"name": t["name"], "command": t["command"], "category": t["category"], "summary": t["summary"]} for t in tools], indent=2))
        else:
            filter_msg = f" (Category: {args.category})" if args.category else ""
            print(f"\n📦 Registered Studio Tools ({len(tools)}){filter_msg}:\n")
            rows = [[t["name"], t["category"], t["command"], t["summary"][:55]] for t in tools]
            print(format_table(rows, ["Tool Name", "Category", "Command", "Summary"]))
            print("\nRun 'bg3 tools info <tool_name>' for full parameter schemas.")
            print()
        return


if __name__ == "__main__":
    main()
