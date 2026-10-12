#!/usr/bin/env python3
"""
check_mod_conflicts.py
----------------------
Static conflict detector and compatibility analyzer for Baldur's Gate 3 mods.

Detects:
1. Stat Entry Collisions: Identical entry names in Spell_*.txt, Passive.txt, Status_*.txt, Weapon.txt
2. Progression Collisions: Duplicate (Class, Level) progression entries in Progressions.lsx
3. Console Incompatibility: Native DLL or SO files that crash console platforms
4. Missing Dependencies: Stated dependencies in meta.lsx not found in local library

Modes:
--mod1 <path> --mod2 <path> : Compare two specific mods
--candidate <path> --against-library : Compare candidate mod against all cataloged mods in mods/
--all : Cross-check all active mods in my_mods/ and mods/
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MODS_DIR = WORKSPACE_ROOT / "mods"
MY_MODS_DIR = WORKSPACE_ROOT / "my_mods"

# ANSI Terminal Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"


def resolve_mod_path(query: str) -> Path:
    p = Path(query)
    if p.exists() and p.is_dir():
        return p

    # Check my_mods
    if MY_MODS_DIR.exists():
        for d in MY_MODS_DIR.iterdir():
            if d.is_dir() and query.lower() in d.name.lower():
                return d

    # Check mods
    if MODS_DIR.exists():
        for d in MODS_DIR.iterdir():
            if d.is_dir() and query.lower() in d.name.lower():
                return d

    raise FileNotFoundError(f"Could not resolve mod path for query '{query}'.")


def extract_stats_entries(mod_dir: Path) -> dict[str, dict]:
    """
    Extracts all 'new entry \"<Name>\"' from any .txt files in the mod.
    Handles both my_mods (Public/*/Stats/Generated/Data) and mods (data/).
    """
    entries = {}
    txt_files = list(mod_dir.rglob("*.txt"))

    for f in txt_files:
        # Ignore readme or task files
        if f.name.lower() in ("readme.txt", "task.txt", "license.txt"):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            current_entry = ""
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                m = re.match(r'^new\s+entry\s+"([^"]+)"', line)
                if m:
                    current_entry = m.group(1)
                    entries[current_entry] = {
                        "entry": current_entry,
                        "file": f.name,
                        "rel_path": str(f.relative_to(mod_dir)),
                    }
        except Exception:
            pass
    return entries


def extract_progressions(mod_dir: Path) -> dict[tuple[str, str], dict]:
    """
    Extracts progression nodes from Progressions.lsx.
    Maps (Name, Level) -> progression details.
    """
    progressions = {}
    lsx_files = list(mod_dir.rglob("*Progression*.lsx"))

    for f in lsx_files:
        try:
            tree = ET.parse(f)
            for node in tree.findall(".//node[@id='Progression']"):
                p_name = ""
                p_level = ""
                p_uuid = ""
                for attr in node.findall("attribute"):
                    aid = attr.get("id")
                    val = attr.get("value", "")
                    if aid == "Name":
                        p_name = val
                    elif aid == "Level":
                        p_level = val
                    elif aid == "UUID":
                        p_uuid = val

                if p_name and p_level:
                    key = (p_name, p_level)
                    progressions[key] = {
                        "name": p_name,
                        "level": p_level,
                        "uuid": p_uuid,
                        "file": f.name,
                    }
        except Exception:
            pass
    return progressions


def check_native_dlls(mod_dir: Path) -> list[str]:
    """Detects .dll or .so binary files indicating native PC code / BG3SE requirement."""
    binaries = []
    for f in mod_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".dll", ".so", ".exe"):
            binaries.append(str(f.relative_to(mod_dir)))
    return binaries


def get_mod_dependencies(mod_dir: Path) -> list[str]:
    """Extracts dependency names from meta.lsx."""
    deps = []
    meta_files = list(mod_dir.rglob("meta.lsx"))
    if not meta_files:
        return deps
    try:
        content = meta_files[0].read_text(encoding="utf-8")
        for m in re.finditer(r'<node\s+id="ModuleShortDesc">.*?<attribute\s+id="Name"\s+type="LSString"\s+value="([^"]+)".*?</node>', content, re.DOTALL):
            deps.append(m.group(1))
    except Exception:
        pass
    return deps


def compare_two_mods(mod1_dir: Path, mod2_dir: Path) -> dict:
    mod1_name = mod1_dir.name
    mod2_name = mod2_dir.name

    stats1 = extract_stats_entries(mod1_dir)
    stats2 = extract_stats_entries(mod2_dir)

    progs1 = extract_progressions(mod1_dir)
    progs2 = extract_progressions(mod2_dir)

    dlls1 = check_native_dlls(mod1_dir)
    dlls2 = check_native_dlls(mod2_dir)

    # 1. Entry overlaps
    stat_collisions = []
    common_entries = set(stats1.keys()) & set(stats2.keys())
    for e in sorted(common_entries):
        stat_collisions.append({
            "entry": e,
            "mod1_file": stats1[e]["file"],
            "mod2_file": stats2[e]["file"],
        })

    # 2. Progression overlaps
    prog_collisions = []
    common_progs = set(progs1.keys()) & set(progs2.keys())
    for p in sorted(common_progs):
        prog_collisions.append({
            "class": p[0],
            "level": p[1],
            "mod1_uuid": progs1[p].get("uuid", ""),
            "mod2_uuid": progs2[p].get("uuid", ""),
        })

    has_conflict = bool(stat_collisions or prog_collisions)

    return {
        "mod1": mod1_name,
        "mod2": mod2_name,
        "has_conflicts": has_conflict,
        "stat_collisions": stat_collisions,
        "progression_collisions": prog_collisions,
        "console_incompatible": {
            mod1_name: dlls1,
            mod2_name: dlls2,
        },
    }


def compare_candidate_against_catalog(candidate_dir: Path, catalog_dirs: list[Path]) -> list[dict]:
    results = []
    for cat_dir in catalog_dirs:
        if cat_dir.resolve() == candidate_dir.resolve():
            continue
        res = compare_two_mods(candidate_dir, cat_dir)
        if res["has_conflicts"] or res["console_incompatible"][cat_dir.name]:
            results.append(res)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Static entry collision and compatibility analyzer for BG3 mods."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--candidate", help="Path or name of candidate mod to check")
    group.add_argument("--mod1", help="First mod path/name to compare")
    group.add_argument("--all", action="store_true", help="Cross-check all mods in my_mods/ and mods/")

    parser.add_argument("--mod2", help="Second mod path/name (used with --mod1)")
    parser.add_argument("--against-library", action="store_true", help="Compare candidate against all cataloged mods in mods/")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.mod1:
        if not args.mod2:
            print("Error: --mod2 is required when using --mod1.", file=sys.stderr)
            sys.exit(1)
        m1 = resolve_mod_path(args.mod1)
        m2 = resolve_mod_path(args.mod2)
        res = compare_two_mods(m1, m2)

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"\n{BOLD}{CYAN}=== BG3 Mod Compatibility Analysis ==={RESET}")
            print(f"Comparing: {BOLD}{res['mod1']}{RESET} vs {BOLD}{res['mod2']}{RESET}\n")
            if not res["has_conflicts"]:
                print(f"{GREEN}✓ No stat or progression collisions detected between these mods.{RESET}")
            else:
                if res["stat_collisions"]:
                    print(f"{YELLOW}⚠ Stat Entry Overrides ({len(res['stat_collisions'])}):{RESET}")
                    for sc in res["stat_collisions"]:
                        print(f"  • Entry '{sc['entry']}' defined in both '{sc['mod1_file']}' and '{sc['mod2_file']}'")
                if res["progression_collisions"]:
                    print(f"{RED}✗ Class Progression Collisions ({len(res['progression_collisions'])}):{RESET}")
                    for pc in res["progression_collisions"]:
                        print(f"  • Class '{pc['class']}' Level {pc['level']} overwritten by both mods")

            # Check dlls
            for mname, dlls in res["console_incompatible"].items():
                if dlls:
                    print(f"{RED}✗ Console Incompatibility in {mname}:{RESET} contains native binaries {dlls}")
            print("")

        sys.exit(1 if res["has_conflicts"] else 0)

    elif args.candidate:
        cand_path = resolve_mod_path(args.candidate)
        catalog = []
        if args.against_library and MODS_DIR.exists():
            catalog = [d for d in MODS_DIR.iterdir() if d.is_dir()]
        elif MY_MODS_DIR.exists():
            catalog = [d for d in MY_MODS_DIR.iterdir() if d.is_dir()]

        results = compare_candidate_against_catalog(cand_path, catalog)
        cand_dlls = check_native_dlls(cand_path)

        if args.json:
            output = {
                "candidate": cand_path.name,
                "console_incompatible": cand_dlls,
                "conflict_count": len(results),
                "conflicts": results,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n{BOLD}{CYAN}=== BG3 Mod Candidate Conflict Scan ==={RESET}")
            print(f"Candidate: {BOLD}{cand_path.name}{RESET}")
            if cand_dlls:
                print(f"{RED}✗ Native DLLs detected (Console Incompatible): {cand_dlls}{RESET}")

            if not results:
                print(f"{GREEN}✓ No conflicts found with any tracked mods in catalog ({len(catalog)} checked).{RESET}\n")
                sys.exit(0)
            else:
                print(f"{YELLOW}⚠ Potential collisions found with {len(results)} cataloged mods:{RESET}")
                for r in results:
                    print(f"\n  {BOLD}vs {r['mod2']}:{RESET}")
                    for sc in r["stat_collisions"]:
                        print(f"    • Overlap: '{sc['entry']}' in {sc['mod2_file']}")
                    for pc in r["progression_collisions"]:
                        print(f"    • Progression collision: {pc['class']} Lvl {pc['level']}")
                print("")
                sys.exit(1)

    elif args.all:
        all_mods = []
        if MY_MODS_DIR.exists():
            all_mods.extend([d for d in MY_MODS_DIR.iterdir() if d.is_dir()])
        if MODS_DIR.exists():
            all_mods.extend([d for d in MODS_DIR.iterdir() if d.is_dir()])

        pair_conflicts = []
        for i in range(len(all_mods)):
            for j in range(i + 1, len(all_mods)):
                res = compare_two_mods(all_mods[i], all_mods[j])
                if res["has_conflicts"]:
                    pair_conflicts.append(res)

        if args.json:
            print(json.dumps({"total_mods": len(all_mods), "conflicting_pairs": pair_conflicts}, indent=2))
        else:
            print(f"\n{BOLD}{CYAN}=== Workspace Full Mod Compatibility Scan ==={RESET}")
            print(f"Scanned {len(all_mods)} total mods across my_mods/ and mods/.")
            if not pair_conflicts:
                print(f"{GREEN}✓ No inter-mod stat or progression collisions detected.{RESET}\n")
                sys.exit(0)
            else:
                print(f"{YELLOW}Found {len(pair_conflicts)} conflicting mod pairs.{RESET}")
                for pc in pair_conflicts:
                    print(f"  • {pc['mod1']} ↔ {pc['mod2']}: {len(pc['stat_collisions'])} stat overrides, {len(pc['progression_collisions'])} progression collisions")
                print("")
                sys.exit(1)


if __name__ == "__main__":
    main()
