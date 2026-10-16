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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib.env_paths import MODS_DIR, MY_MODS_DIR, REPO_ROOT as WORKSPACE_ROOT, normalize_mod_key, resolve_mod_dir

# ANSI Terminal Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"

BUILTIN_MODULES = {
    "gustav",
    "gustavdev",
    "gustavx",
    "shared",
    "shareddev",
    "engine",
    "photomode",
    "honour",
    "mainui",
    "modbrowser",
    "fw3",
}


def resolve_mod_path(query: str) -> Path:
    return resolve_mod_dir(query, prefer_my_mods=True)


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


def extract_root_templates(mod_dir: Path) -> dict[str, dict]:
    """
    Extracts GameObjects MapKey UUIDs from RootTemplates LSX files.
    """
    templates = {}
    lsx_files = [
        f for f in mod_dir.rglob("*.lsx")
        if "roottemplate" in str(f.relative_to(mod_dir)).lower() or f.name.lower() == "_merged.lsx"
    ]
    for f in lsx_files:
        try:
            tree = ET.parse(f)
            for node in tree.findall(".//node[@id='GameObjects']"):
                map_key = ""
                t_name = ""
                for attr in node.findall("attribute"):
                    aid = attr.get("id")
                    val = attr.get("value", "")
                    if aid == "MapKey":
                        map_key = val
                    elif aid == "Name":
                        t_name = val
                if map_key:
                    templates[map_key] = {
                        "map_key": map_key,
                        "name": t_name,
                        "file": f.name,
                    }
        except Exception:
            pass
    return templates


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
    for mf in meta_files:
        try:
            content = mf.read_text(encoding="utf-8")
            dep_block = re.search(r'<node\s+id="Dependencies">(.*?)</node>\s*(?:<node\s+id="ModuleInfo"|</children>)', content, re.DOTALL)
            target = dep_block.group(1) if dep_block else content
            for m in re.finditer(r'<node\s+id="ModuleShortDesc">.*?<attribute\s+id="Name"\s+type="[^"]*"\s+value="([^"]+)".*?</node>', target, re.DOTALL):
                dep_name = m.group(1).strip()
                if dep_name and dep_name.lower() not in BUILTIN_MODULES and not dep_name.lower().startswith("diceset"):
                    if dep_name not in deps:
                        deps.append(dep_name)
        except Exception:
            pass
    return deps


def find_missing_local_dependencies(mod_dir: Path) -> list[str]:
    """Checks whether declared dependencies in meta.lsx exist in my_mods/ or mods/."""
    deps = get_mod_dependencies(mod_dir)
    if not deps:
        return []

    known_keys: set[str] = set()
    for base in (MY_MODS_DIR, MODS_DIR):
        if base.is_dir():
            for d in base.iterdir():
                if d.is_dir():
                    known_keys.add(normalize_mod_key(d.name))
                    for mf in d.rglob("meta.lsx"):
                        try:
                            txt = mf.read_text(encoding="utf-8", errors="ignore")
                            for m in re.finditer(r'<attribute\s+id="(?:Name|Folder)"\s+type="[^"]*"\s+value="([^"]+)"', txt):
                                known_keys.add(normalize_mod_key(m.group(1)))
                        except Exception:
                            pass

    missing = []
    for dep in deps:
        dep_norm = normalize_mod_key(dep)
        if not any(dep_norm == k or dep_norm in k or k in dep_norm for k in known_keys if k):
            missing.append(dep)
    return missing


def compare_two_mods(mod1_dir: Path, mod2_dir: Path) -> dict:
    mod1_name = mod1_dir.name
    mod2_name = mod2_dir.name

    stats1 = extract_stats_entries(mod1_dir)
    stats2 = extract_stats_entries(mod2_dir)

    progs1 = extract_progressions(mod1_dir)
    progs2 = extract_progressions(mod2_dir)

    rt1 = extract_root_templates(mod1_dir)
    rt2 = extract_root_templates(mod2_dir)

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

    # 3. RootTemplate MapKey overlaps
    rt_collisions = []
    common_rts = set(rt1.keys()) & set(rt2.keys())
    for rk in sorted(common_rts):
        rt_collisions.append({
            "map_key": rk,
            "name": rt1[rk].get("name") or rt2[rk].get("name", ""),
            "mod1_file": rt1[rk]["file"],
            "mod2_file": rt2[rk]["file"],
        })

    has_conflict = bool(stat_collisions or prog_collisions or rt_collisions)

    return {
        "mod1": mod1_name,
        "mod2": mod2_name,
        "has_conflicts": has_conflict,
        "stat_collisions": stat_collisions,
        "progression_collisions": prog_collisions,
        "root_template_collisions": rt_collisions,
        "missing_dependencies": {
            mod1_name: find_missing_local_dependencies(mod1_dir),
            mod2_name: find_missing_local_dependencies(mod2_dir),
        },
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
    parser.add_argument("--summary", action="store_true", help="Output high-level collision counts and mod pairs without dumping full raw entries")
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
            if args.summary:
                res_out = {
                    "mod1": res["mod1"],
                    "mod2": res["mod2"],
                    "has_conflicts": res["has_conflicts"],
                    "stat_collision_count": len(res.get("stat_collisions", [])),
                    "progression_collision_count": len(res.get("progression_collisions", [])),
                    "root_template_collision_count": len(res.get("root_template_collisions", [])),
                    "missing_dependencies": res.get("missing_dependencies", {}),
                }
                print(json.dumps(res_out, indent=2))
            else:
                print(json.dumps(res, indent=2))
        else:
            print(f"\n{BOLD}{CYAN}=== BG3 Mod Compatibility Analysis ==={RESET}")
            print(f"Comparing: {BOLD}{res['mod1']}{RESET} vs {BOLD}{res['mod2']}{RESET}\n")
            if not res["has_conflicts"]:
                print(f"{GREEN}✓ No stat, progression, or template collisions detected between these mods.{RESET}")
            else:
                if res["stat_collisions"]:
                    print(f"{YELLOW}⚠ Stat Entry Overrides ({len(res['stat_collisions'])}):{RESET}")
                    for sc in res["stat_collisions"]:
                        print(f"  • Entry '{sc['entry']}' defined in both '{sc['mod1_file']}' and '{sc['mod2_file']}'")
                if res["progression_collisions"]:
                    print(f"{RED}✗ Class Progression Collisions ({len(res['progression_collisions'])}):{RESET}")
                    for pc in res["progression_collisions"]:
                        print(f"  • Class '{pc['class']}' Level {pc['level']} overwritten by both mods")
                if res.get("root_template_collisions"):
                    print(f"{RED}✗ RootTemplate MapKey Collisions ({len(res['root_template_collisions'])}):{RESET}")
                    for rc in res["root_template_collisions"]:
                        print(f"  • MapKey '{rc['map_key']}' ({rc['name']}) defined in both mods")

            for mname, mdeps in res.get("missing_dependencies", {}).items():
                if mdeps:
                    print(f"{YELLOW}⚠ Missing Local Dependencies for {mname}:{RESET} {', '.join(mdeps)}")

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
        cand_missing_deps = find_missing_local_dependencies(cand_path)

        if args.json:
            if args.summary:
                summary_conflicts = [
                    {
                        "mod2": r["mod2"],
                        "stat_collision_count": len(r.get("stat_collisions", [])),
                        "progression_collision_count": len(r.get("progression_collisions", [])),
                        "root_template_collision_count": len(r.get("root_template_collisions", [])),
                    }
                    for r in results
                ]
                output = {
                    "candidate": cand_path.name,
                    "console_incompatible": cand_dlls,
                    "missing_dependencies": cand_missing_deps,
                    "conflict_count": len(results),
                    "conflicts": summary_conflicts,
                }
            else:
                output = {
                    "candidate": cand_path.name,
                    "console_incompatible": cand_dlls,
                    "missing_dependencies": cand_missing_deps,
                    "conflict_count": len(results),
                    "conflicts": results,
                }
            print(json.dumps(output, indent=2))

        else:
            print(f"\n{BOLD}{CYAN}=== BG3 Mod Candidate Conflict Scan ==={RESET}")
            print(f"Candidate: {BOLD}{cand_path.name}{RESET}")
            if cand_dlls:
                print(f"{RED}✗ Native DLLs detected (Console Incompatible): {cand_dlls}{RESET}")
            if cand_missing_deps:
                print(f"{YELLOW}⚠ Missing Local Dependencies: {', '.join(cand_missing_deps)}{RESET}")

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
                    for rc in r.get("root_template_collisions", []):
                        print(f"    • RootTemplate MapKey collision: {rc['map_key']} ({rc['name']})")
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
