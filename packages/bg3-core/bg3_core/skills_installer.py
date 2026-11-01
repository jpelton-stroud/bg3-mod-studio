#!/usr/bin/env python3
"""
skills_installer.py
-------------------
Discovers and deploys agent skills bundled in BG3 Mod Studio domain packages
(bg3-core, bg3-authoring, bg3-theorycraft) into the target studio directory
(${BG3_STUDIO_DIR}/.agents/skills by default).
"""

import argparse
import importlib.resources as pkg_resources
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from bg3_core.env_paths import REPO_ROOT, get_studio_dir

# Domain package definitions: (import_module_name, display_package_name)
PACKAGED_SKILL_SOURCES = [
    ("bg3_core", "bg3"),
    ("bg3_authoring", "bg3-authoring"),
    ("bg3_theorycraft", "bg3-theorycraft"),
]

# ANSI Terminal Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"


def get_default_skills_target(studio_dir: Optional[Path] = None) -> Path:
    """Return default target skills directory in the user's BG3 Mod Studio workspace."""
    base_dir = studio_dir if studio_dir is not None else get_studio_dir()
    return base_dir / ".agents" / "skills"


def discover_bundled_skills() -> Dict[str, Dict[str, Any]]:
    """
    Discover all bundled skills from installed bg3_* packages or workspace paths.
    Returns a dictionary mapping skill_name -> metadata dict.
    """
    discovered: Dict[str, Dict[str, Any]] = {}

    for module_name, pkg_name in PACKAGED_SKILL_SOURCES:
        source_dir: Optional[Path] = None

        # 1. Try resolving via importlib.resources (wheels, installed packages, and editable installs)
        try:
            ref = pkg_resources.files(module_name) / "skills"
            cand = Path(str(ref))
            if cand.is_dir():
                source_dir = cand
        except Exception:
            pass

        # 2. Try resolving via module spec location
        if source_dir is None or not source_dir.is_dir():
            try:
                spec = importlib.util.find_spec(module_name)
                if spec and spec.submodule_search_locations:
                    for loc in spec.submodule_search_locations:
                        cand = Path(loc) / "skills"
                        if cand.is_dir():
                            source_dir = cand
                            break
            except Exception:
                pass

        if source_dir is None or not source_dir.is_dir():
            continue

        for item in sorted(source_dir.iterdir()):
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.is_file():
                    skill_name = item.name
                    # Read description if available
                    desc = ""
                    try:
                        header = skill_md.read_text(encoding="utf-8")
                        for line in header.splitlines():
                            if line.startswith("description:"):
                                desc = line.split("description:", 1)[1].strip()
                                break
                    except Exception:
                        pass

                    discovered[skill_name] = {
                        "name": skill_name,
                        "package": pkg_name,
                        "module": module_name,
                        "source_path": item.resolve(),
                        "skill_md": skill_md.resolve(),
                        "description": desc,
                    }

    return discovered


def install_agent_skills(
    target_dir: Optional[Path] = None,
    symlink: bool = False,
    force: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Install discovered domain skills into the destination skills directory.
    Default destination is ${BG3_STUDIO_DIR}/.agents/skills.
    """
    destination = target_dir or get_default_skills_target()
    discovered = discover_bundled_skills()

    installed: List[str] = []
    updated: List[str] = []
    skipped: List[str] = []
    errors: List[Dict[str, str]] = []

    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)

    for skill_name, meta in discovered.items():
        src = meta["source_path"]
        dest = destination / skill_name

        try:
            if dest.exists() or dest.is_symlink():
                if not force:
                    skipped.append(skill_name)
                    continue
                if not dry_run:
                    if dest.is_symlink() or dest.is_file():
                        dest.unlink()
                    elif dest.is_dir():
                        shutil.rmtree(dest)
                updated.append(skill_name)
            else:
                installed.append(skill_name)

            if not dry_run:
                if symlink:
                    # Create relative or absolute symlink
                    dest.symlink_to(src.resolve(), target_is_directory=True)
                else:
                    shutil.copytree(src.resolve(), dest, dirs_exist_ok=True)
        except Exception as e:
            errors.append({"skill": skill_name, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "target_dir": str(destination),
        "total_discovered": len(discovered),
        "installed": installed,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install BG3 Mod Studio domain agent skills into the user studio workspace."
    )
    parser.add_argument(
        "--target-dir",
        "-t",
        type=Path,
        default=None,
        help="Target skills directory (default: ${BG3_STUDIO_DIR}/.agents/skills)",
    )
    parser.add_argument(
        "--symlink",
        "-s",
        action="store_true",
        help="Symlink skills instead of copying them (useful for active development)",
    )
    parser.add_argument(
        "--check",
        "-c",
        action="store_true",
        help="Check and list available packaged skills without installing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview installation actions without making disk changes",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )

    args = parser.parse_args()

    discovered = discover_bundled_skills()
    target_dir = args.target_dir or get_default_skills_target()

    if args.check:
        if args.json:
            out = {
                "target_dir": str(target_dir),
                "total": len(discovered),
                "skills": [
                    {
                        "name": s["name"],
                        "package": s["package"],
                        "installed": (target_dir / s["name"]).is_dir(),
                        "description": s["description"],
                    }
                    for s in discovered.values()
                ],
            }
            print(json.dumps(out, indent=2))
        else:
            print(f"\n{BOLD}Discovered Packaged Agent Skills ({len(discovered)} total):{RESET}")
            print(f"Target Directory: {CYAN}{target_dir}{RESET}\n")
            print(f"{'Skill Name':<30} | {'Package':<16} | {'Installed in Target':<20}")
            print("-" * 72)
            for s in discovered.values():
                is_inst = (target_dir / s["name"]).is_dir()
                status_str = f"{GREEN}[✓] Installed{RESET}" if is_inst else f"{YELLOW}[ ] Missing{RESET}"
                print(f"{s['name']:<30} | {s['package']:<16} | {status_str}")
            print()
        sys.exit(0)

    result = install_agent_skills(
        target_dir=args.target_dir,
        symlink=args.symlink,
        force=True,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        prefix = "[DRY-RUN] " if args.dry_run else ""
        if result["success"]:
            count = len(result["installed"]) + len(result["updated"])
            print(f"{GREEN}✓ {prefix}Successfully installed {count} agent skills to {target_dir}{RESET}")
        else:
            print(f"{RED}✗ {prefix}Errors occurred during skill installation:{RESET}")
            for err in result["errors"]:
                print(f"  - {err['skill']}: {err['error']}")
            sys.exit(1)


if __name__ == "__main__":
    main()
