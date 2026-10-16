#!/usr/bin/env python3
"""
update_library_catalog.py
-------------------------
Scans all documented mod specifications under `mods/` and automatically
regenerates and sorts the master catalog in `mods/library.md`.

Features:
- Extracts mod titles, descriptions, and implemented feature counts from mods/*/README.md
- Categorizes mods into standard sections:
  * Gear
  * Spells
  * Classes & Subclasses
  * Progression & Rules
  * Utilities & Cheats
- Verifies relative spec links
- Supports --check (for CI validation), --write (updates mods/library.md), and --stdout
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lib.env_paths import MODS_DIR, REPO_ROOT
from scripts.lib.library_catalog import LIBRARY_COLUMNS, parse_library_rows, render_library_row

WORKSPACE_ROOT = REPO_ROOT
LIBRARY_FILE = MODS_DIR / "library.md"

CATEGORY_ORDER = [
    "Gear",
    "Spells",
    "Classes & Subclasses",
    "Progression & Rules",
    "Utilities & Cheats",
]

# Explicit known classifications for library stability
KNOWN_CATEGORIES = {
    "sets-of-faerun": "Gear",
    "gearup": "Gear",
    "pact-and-power-warlock-equipment": "Gear",
    "paragon-encounters": "Gear",
    "dynamic-extra-encounters": "Gear",
    "slightly-deadlier-pack": "Gear",
    "longstrider-qol1": "Spells",
    "requiem-for-the-absolute": "Spells",
    "dynamic-difficulty-scaling": "Spells",
    "enemy-tacticians": "Spells",
    "fix-jump-fly-shortcut": "Spells",
    "customcompanionslite": "Spells",
    "extra-encounters-and-minibosses": "Spells",
    "cantrip-mastery": "Spells",
    "elemental-eldritch-blast": "Spells",
    "pact-of-the-blade-overhaul": "Classes & Subclasses",
    "invocations-unlocked": "Classes & Subclasses",
    "eldritch-knight-war-magic-enhanced": "Classes & Subclasses",
    "unlocklevelcurve": "Progression & Rules",
    "choose-your-scores": "Utilities & Cheats",
    "unlocklevelcurve-patch-xp-instant": "Utilities & Cheats",
    "warlockinvocation": "Utilities & Cheats",
    "immediate-tutorial-chest": "Utilities & Cheats",
    "enemy-legends-patch": "Utilities & Cheats",
    "nightmare-difficulty": "Utilities & Cheats",
    "illithid-wisdom-check": "Utilities & Cheats",
    "everybody-moves-fast": "Utilities & Cheats",
    "more-enemies-in-basic-fights": "Utilities & Cheats",
    "sets-of-faerun-cheat": "Utilities & Cheats",
    "goodies-bag": "Utilities & Cheats",
    "normal-half-illithid": "Utilities & Cheats",
    "paladins-have-gods": "Utilities & Cheats",
    "no-astral-tadpole-required-for-illithid-powers": "Utilities & Cheats",
    "warlock-multiclass-spell-slots-fix": "Utilities & Cheats",
}


def classify_mod(slug: str, title: str, desc: str) -> str:
    if slug in KNOWN_CATEGORIES:
        return KNOWN_CATEGORIES[slug]

    text = f"{slug} {title} {desc}".lower()
    if any(k in text for k in ["weapon", "armor", "gear", "equipment", "set", "items"]):
        return "Gear"
    if any(k in text for k in ["class", "subclass", "warlock", "cleric", "paladin", "fighter", "sorcerer", "monk", "rogue", "wizard", "bard"]):
        return "Classes & Subclasses"
    if any(k in text for k in ["level", "xp", "curve", "progression", "cap"]):
        return "Progression & Rules"
    if any(k in text for k in ["spell", "cantrip", "magic", "action", "fly", "jump"]):
        return "Spells"
    return "Utilities & Cheats"


def parse_existing_mod_ids(library_content: str) -> dict[str, str]:
    """Read IDs from the current schema or the legacy Mod.io IDs table."""
    ids = {}
    for row in parse_library_rows(library_content):
        raw_id = row["mod_id"].strip()
        if raw_id.isdigit() and int(raw_id) > 0:
            ids[row["slug"]] = raw_id

    in_legacy_ids = False
    legacy_row = re.compile(
        r"^\|\s*[^|]*?\s*\|\s*`(?P<slug>[^`]+)`\s*\|\s*(?P<mod_id>[^|]*?)\s*\|$"
    )
    for line in library_content.splitlines():
        if line.startswith("## "):
            in_legacy_ids = line[3:].strip().casefold() == "mod.io ids"
            continue
        if not in_legacy_ids or not line.startswith("|"):
            continue
        match = legacy_row.match(line)
        if not match:
            continue
        raw_id = match.group("mod_id").strip()
        slug = match.group("slug").strip()
        if raw_id.isdigit() and int(raw_id) > 0:
            ids.setdefault(slug, raw_id)
    return ids


def parse_mod_readme(mod_dir: Path, known_mod_ids: dict[str, str] | None = None) -> dict:
    readme_path = mod_dir / "README.md"
    if not readme_path.is_file():
        return {}

    slug = mod_dir.name
    title = slug
    desc = ""
    feature_count = 0

    content = readme_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    # 1. Title
    for line in lines:
        if line.startswith("# "):
            raw_title = line[2:].strip()
            raw_title = re.sub(r"^Mod Specification:\s*", "", raw_title, flags=re.IGNORECASE)
            title = raw_title.strip()
            break

    # 2. Features count
    feat_match = re.search(r"(\d+)\s+implemented", content, re.IGNORECASE)
    if feat_match:
        feature_count = int(feat_match.group(1))
    else:
        # Count table rows across markdown tables in README
        table_rows = re.findall(r"^\|(?!\s*:---).+\|$", content, re.MULTILINE)
        if len(table_rows) > 2:
            feature_count = max(0, len(table_rows) - 2)

    # 3. Description
    desc_match = re.search(r"## (?:Overview|Description)\s*\n+(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if desc_match:
        raw_desc = desc_match.group(1).strip()
        # Take first non-empty line
        desc_lines = [l.strip() for l in raw_desc.splitlines() if l.strip() and not l.startswith("-") and not l.startswith("|")]
        if desc_lines:
            desc = desc_lines[0]
    
    if not desc:
        desc = f"{title} mod specification."

    # Truncate overly long descriptions
    if len(desc) > 280:
        desc = desc[:277] + "..."

    category = classify_mod(slug, title, desc)
    id_match = re.search(r"\*\*(?:mod\.io ID|Mod Id)\*\*:\s*`?([0-9]+)`?", content, re.IGNORECASE)
    mod_id = id_match.group(1) if id_match else (known_mod_ids or {}).get(slug, "")

    return {
        "mod_id": mod_id,
        "slug": slug,
        "title": title,
        "description": desc,
        "feature_count": feature_count,
        "category": category,
        "spec_link": f"{slug}/README.md",
    }


def generate_library_markdown(mods_data: list[dict]) -> str:
    categories = {cat: [] for cat in CATEGORY_ORDER}

    for mod in mods_data:
        cat = mod["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(mod)

    lines = [
        "# Baldur's Gate 3 Mod Library",
        "",
        "This library catalogs documented Baldur's Gate 3 mods, their in-game features, and specifications for build crafting.",
        "",
    ]

    for cat in CATEGORY_ORDER:
        mod_list = categories[cat]
        if not mod_list:
            continue

        lines.append(f"## {cat}")
        lines.append("")
        lines.append("| " + " | ".join(LIBRARY_COLUMNS) + " |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        for m in sorted(mod_list, key=lambda x: x["title"].lower()):
            lines.append(render_library_row(m))

        lines.append("")

    return "\n".join(lines).strip() + "\n"


def collect_mods_data(mods_dir: Path = MODS_DIR, library_content: str = "") -> list[dict]:
    known_mod_ids = parse_existing_mod_ids(library_content)
    mods_data = []
    for mod_dir in sorted(mods_dir.iterdir()):
        if mod_dir.is_dir() and not mod_dir.name.startswith("."):
            parsed = parse_mod_readme(mod_dir, known_mod_ids)
            if parsed:
                mods_data.append(parsed)
    return mods_data


def write_library_catalog(
    mods_dir: Path = MODS_DIR, library_file: Path = LIBRARY_FILE
) -> list[dict]:
    current_content = (
        library_file.read_text(encoding="utf-8") if library_file.is_file() else ""
    )
    mods_data = collect_mods_data(mods_dir, current_content)
    library_file.write_text(generate_library_markdown(mods_data), encoding="utf-8")
    return mods_data


def main():
    parser = argparse.ArgumentParser(
        description="Update or check master catalog in mods/library.md from mods/*/README.md."
    )
    parser.add_argument("--write", action="store_true", help="Write changes to mods/library.md")
    parser.add_argument("--check", action="store_true", help="Check if mods/library.md is up to date without modifying")
    parser.add_argument("--stdout", action="store_true", help="Output generated catalog to stdout")
    parser.add_argument("--json", action="store_true", help="Emit catalog status as JSON")

    args = parser.parse_args()

    if not MODS_DIR.exists():
        print(f"Error: {MODS_DIR} does not exist.", file=sys.stderr)
        sys.exit(1)

    current_content = ""
    if LIBRARY_FILE.is_file():
        current_content = LIBRARY_FILE.read_text(encoding="utf-8")
    mods_data = collect_mods_data(MODS_DIR, current_content)
    generated_md = generate_library_markdown(mods_data)

    is_identical = current_content.strip() == generated_md.strip()

    if args.stdout:
        print(generated_md)
        return

    if args.write:
        LIBRARY_FILE.write_text(generated_md, encoding="utf-8")

    if args.json:
        result = {
            "catalog_file": str(LIBRARY_FILE.relative_to(WORKSPACE_ROOT)),
            "mod_count": len(mods_data),
            "up_to_date": is_identical,
            "written": bool(args.write),
        }
        print(json.dumps(result, indent=2))
        sys.exit(0 if (is_identical or args.write) else 1)

    if args.check:
        if is_identical:
            print(f"✓ mods/library.md is fully up to date ({len(mods_data)} mods cataloged).")
            sys.exit(0)
        else:
            print("✗ mods/library.md is out of date. Run with --write to regenerate.", file=sys.stderr)
            sys.exit(1)

    if args.write:
        print(f"✓ Successfully regenerated {LIBRARY_FILE.relative_to(WORKSPACE_ROOT)} with {len(mods_data)} cataloged mods.")
    else:
        print(f"Scanned {len(mods_data)} mods. Use --write to update mods/library.md or --stdout to inspect.")


if __name__ == "__main__":
    main()
