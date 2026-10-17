#!/usr/bin/env python3
"""Baldur's Gate 3 Mod Studio — Unified Tooling Registry & CLI Discovery Hub.

Provides machine-readable discovery, search, schema inspection, and execution
dispatching for all studio automation scripts.

Usage:
    python3 scripts/tools.py --list [--category <cat>] [--json]
    python3 scripts/tools.py --search "<intent or keyword>" [--json]
    python3 scripts/tools.py --info <tool_name> [--json]
    python3 scripts/tools.py --verify [--json]
    python3 scripts/tools.py run <tool_name> [args...]
"""

import argparse
import json
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = SCRIPTS_DIR / "registry.json"
_REPO_ROOT = SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def load_registry() -> Dict[str, Any]:
    """Load the machine-readable registry JSON."""
    if not REGISTRY_PATH.is_file():
        print(f"Error: Registry file not found at {REGISTRY_PATH}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Failed to parse {REGISTRY_PATH}: {e}", file=sys.stderr)
        sys.exit(1)


def find_tool(registry: Dict[str, Any], query: str) -> Optional[Dict[str, Any]]:
    """Find a tool by script name, command name, or stem."""
    q_norm = query.strip().lower()
    if q_norm.endswith(".py"):
        stem = q_norm[:-3]
    else:
        stem = q_norm

    for tool in registry.get("tools", []):
        t_name = tool.get("name", "").lower()
        t_cmd = tool.get("command", "").lower()
        t_stem = t_name[:-3] if t_name.endswith(".py") else t_name

        if q_norm in (t_name, t_cmd, t_stem) or stem in (t_name, t_cmd, t_stem):
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

        # Exact phrase bonus
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

        # Token matches
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


def find_script_path(tool_entry: Dict[str, Any]) -> Optional[Path]:
    """Find script path for a tool entry across domain subfolders or scripts root."""
    rel_path = tool_entry.get("path")
    if rel_path and (SCRIPTS_DIR / rel_path).is_file():
        return SCRIPTS_DIR / rel_path
    name = tool_entry.get("name", "")
    if (SCRIPTS_DIR / name).is_file():
        return SCRIPTS_DIR / name
    category = tool_entry.get("category", "")
    if category and (SCRIPTS_DIR / category / name).is_file():
        return SCRIPTS_DIR / category / name
    for p in SCRIPTS_DIR.rglob(name):
        if "/lib/" not in p.as_posix() and "__pycache__" not in p.as_posix():
            return p
    return None


def verify_registry(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Verify that all scripts on disk are registered, compile, and run --help."""
    tools_by_name = {t.get("name"): t for t in registry.get("tools", [])}
    registered_names = set(tools_by_name.keys())
    disk_scripts = {
        p.name for p in SCRIPTS_DIR.rglob("*.py")
        if p.name != "__init__.py" and "/lib/" not in p.as_posix() and "__pycache__" not in p.as_posix()
    }

    missing_from_disk = sorted(list(registered_names - disk_scripts))
    unregistered_on_disk = sorted(list(disk_scripts - registered_names))

    compile_errors = []
    help_errors = []

    for script_name in sorted(list(registered_names.intersection(disk_scripts))):
        tool = tools_by_name[script_name]
        script_path = find_script_path(tool)
        if not script_path or not script_path.is_file():
            missing_from_disk.append(script_name)
            continue

        # Test compilation
        try:
            py_compile.compile(str(script_path), doraise=True)
        except Exception as e:
            compile_errors.append({"script": script_name, "error": str(e)})

        # Test --help invocation
        try:
            res = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode != 0:
                help_errors.append({
                    "script": script_name,
                    "returncode": res.returncode,
                    "stderr": res.stderr.strip()[:200]
                })
        except Exception as e:
            help_errors.append({"script": script_name, "error": str(e)})

    is_valid = not (missing_from_disk or unregistered_on_disk or compile_errors or help_errors)

    return {
        "valid": is_valid,
        "total_registered": len(registered_names),
        "total_on_disk": len(disk_scripts),
        "missing_from_disk": sorted(list(set(missing_from_disk))),
        "unregistered_on_disk": unregistered_on_disk,
        "compile_errors": compile_errors,
        "help_errors": help_errors,
    }


def audit_skills(registry: Dict[str, Any], skills_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Audit agent skills in .agents/skills/ for registry compliance and tool discovery."""
    if skills_dir is None:
        workspace_dir = SCRIPTS_DIR.parent
        skills_dir = workspace_dir / ".agents" / "skills"

    if not skills_dir.is_dir():
        return {
            "valid": False,
            "error": f"Skills directory not found at {skills_dir}",
            "skills": []
        }

    registered_tools = {t["name"]: t for t in registry.get("tools", [])}
    registered_names = set(registered_tools.keys())

    results = []
    total_refs = 0
    skills_with_discovery = 0
    all_unregistered = set()

    for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_path.parent.name
        try:
            content = skill_path.read_text(encoding="utf-8")
        except Exception as e:
            results.append({"skill": skill_name, "error": str(e), "status": "read_error"})
            continue

        script_refs = sorted(list(set(re.findall(r"scripts/(?:[a-zA-Z0-9_\-]+/)?([a-zA-Z0-9_\-]+\.py)", content))))
        total_refs += len(script_refs)

        has_discovery_tip = "bg3 tools" in content or "tools.py" in content or "registry" in content.lower()
        if has_discovery_tip:
            skills_with_discovery += 1

        unregistered = [s for s in script_refs if s not in registered_names and s != "tools.py"]
        all_unregistered.update(unregistered)

        if unregistered:
            status = "unregistered_references"
        elif has_discovery_tip:
            status = "fully_integrated"
        else:
            status = "missing_discovery"

        results.append({
            "skill": skill_name,
            "script_references": script_refs,
            "has_discovery_guidance": has_discovery_tip,
            "unregistered_references": unregistered,
            "status": status
        })

    is_valid = len(all_unregistered) == 0

    return {
        "valid": is_valid,
        "total_skills": len(results),
        "skills_with_discovery": skills_with_discovery,
        "discovery_coverage_pct": round(skills_with_discovery / len(results) * 100, 1) if results else 0,
        "unregistered_scripts": sorted(list(all_unregistered)),
        "skills": results
    }



def dispatch_run(registry: Dict[str, Any], tool_query: str, extra_args: List[str]) -> int:
    """Dispatch and execute the targeted tool script."""
    tool = find_tool(registry, tool_query)
    if not tool:
        print(f"Error: Unknown tool '{tool_query}'. Run 'bg3 tools list' to see available tools.", file=sys.stderr)
        return 1

    script_path = find_script_path(tool)
    if not script_path or not script_path.is_file():
        print(f"Error: Script file not found for: {tool['name']}", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(script_path)] + extra_args
    proc = subprocess.run(cmd)
    return proc.returncode


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


def main():
    parser = argparse.ArgumentParser(
        description="Baldur's Gate 3 Mod Studio — Tooling Registry & CLI Discovery Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/tools.py --list
  python3 scripts/tools.py --list --category authoring
  python3 scripts/tools.py --search "stat handles"
  python3 scripts/tools.py --info scaffold_stat_entry
  python3 scripts/tools.py --verify
  python3 scripts/tools.py run scaffold-stat --mod arcane --type weapon --name Blade --json
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

    # Dispatch subcommand
    parser.add_argument("subcommand", nargs="?", choices=["run", "list", "search", "info", "verify", "audit"], help="Subcommand action")
    parser.add_argument("tool_name", nargs="?", help="Tool name or query for subcommand")
    parser.add_argument("extra_args", nargs=argparse.REMAINDER, help="Arguments passed to tool when using 'run'")

    args = parser.parse_args()
    registry = load_registry()

    # Route positional subcommand if provided
    if args.subcommand == "run":
        if not args.tool_name:
            print("Error: Missing tool name to run. E.g. 'python3 scripts/tools.py run scaffold-stat [args...]'", file=sys.stderr)
            sys.exit(1)
        sys.exit(dispatch_run(registry, args.tool_name, args.extra_args))
    elif args.subcommand == "list":
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
            status = "PASSED" if report["valid"] else "FAILED"
            print(f"\nSkills Audit Report: [{status}]")
            print(f"  Total Skills:             {report['total_skills']}")
            print(f"  With Discovery Guidance:  {report['skills_with_discovery']} / {report['total_skills']} ({report['discovery_coverage_pct']}%)")
            print(f"  Unregistered Scripts:     {len(report['unregistered_scripts'])}\n")

            rows = []
            for s in report["skills"]:
                scripts_str = ", ".join(s["script_references"]) if s["script_references"] else "(none)"
                discovery_icon = "[✓]" if s["has_discovery_guidance"] else "[ ]"
                rows.append([s["skill"], discovery_icon, s["status"], scripts_str])
            print(format_table(rows, ["Skill Name", "Discovery", "Status", "Referenced Scripts"]))
            print()
        sys.exit(0 if report["valid"] else 1)

    # 2. Verify
    if args.verify:
        report = verify_registry(registry)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            status = "PASSED" if report["valid"] else "FAILED"
            print(f"\nRegistry Verification: [{status}]")
            print(f"  Total on disk:     {report['total_on_disk']}")
            print(f"  Total registered:  {report['total_registered']}")
            if report["missing_from_disk"]:
                print(f"  Missing on disk:   {', '.join(report['missing_from_disk'])}")
            if report["unregistered_on_disk"]:
                print(f"  Unregistered:      {', '.join(report['unregistered_on_disk'])}")
            if report["compile_errors"]:
                print("  Compilation Errors:")
                for err in report["compile_errors"]:
                    print(f"    - {err['script']}: {err['error']}")
            if report["help_errors"]:
                print("  CLI Help Invocation Errors:")
                for err in report["help_errors"]:
                    print(f"    - {err['script']}: {err.get('stderr') or err.get('error')}")
            print()
        sys.exit(0 if report["valid"] else 1)

    # 3. Info
    if args.info:
        tool = find_tool(registry, args.info)
        if not tool:
            print(f"Error: Tool '{args.info}' not found in registry.", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(tool, indent=2))
        else:
            print(f"\n🛠️  Tool: {tool['name']} (alias: {tool.get('command')})")
            print(f"Category:    {tool.get('category')}")
            print(f"Summary:     {tool.get('summary')}")
            print(f"Description: {tool.get('description')}\n")
            print(f"CLI Usage:   {tool.get('cli_usage')}\n")
            print("Intents / Capabilities:")
            for intent in tool.get("intents", []):
                print(f"  • {intent}")
            print("\nOptions & Flags:")
            flag_rows = [
                [f.get("name"), f.get("type"), "Yes" if f.get("required") else "No", f.get("description")]
                for f in tool.get("flags", [])
            ]
            if flag_rows:
                print(format_table(flag_rows, ["Flag", "Type", "Required", "Description"]))
            print("\nExamples:")
            for ex in tool.get("examples", []):
                print(f"  $ {ex}")
            print()
        return

    # 4. Search
    if args.search:
        results = search_tools(registry, args.search)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"\nNo tools found matching query: '{args.search}'\n")
                return
            print(f"\n🔍 Search Results for '{args.search}' ({len(results)} matches):\n")
            rows = [
                [r["command"], r["category"], r["summary"], str(r["relevance_score"])]
                for r in results
            ]
            print(format_table(rows, ["Command", "Category", "Summary", "Score"]))
            print(f"\nTip: Run 'python3 scripts/tools.py --info <command>' for full flag specifications.\n")
        return

    # 5. List
    if args.list or not any([args.search, args.info, args.verify, args.audit_skills, args.categories]):
        tools = list_tools(registry, args.category)
        if args.json:
            if args.full:
                print(json.dumps(tools, indent=2))
            else:
                compact_manifest = [
                    {
                        "name": t.get("name"),
                        "command": t.get("command"),
                        "category": t.get("category"),
                        "summary": t.get("summary"),
                        "cli_usage": t.get("cli_usage"),
                    }
                    for t in tools
                ]
                print(json.dumps(compact_manifest, indent=2))
        else:
            cat_label = f" [{args.category}]" if args.category else ""
            print(f"\n🧰 BG3 Mod Studio Tools{cat_label} ({len(tools)} available):\n")
            rows = [
                [t.get("command", ""), t.get("name", ""), t.get("category", ""), t.get("summary", "")]
                for t in tools
            ]
            print(format_table(rows, ["Command", "Script Name", "Category", "Summary"]))
            print(f"\nTip: Run 'python3 scripts/tools.py --search \"<intent>\"' or '--info <command>' for flags.\n")
        return


if __name__ == "__main__":
    main()
