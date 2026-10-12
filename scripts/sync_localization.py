#!/usr/bin/env python3
"""
sync_localization.py - Audits, prunes orphaned string handles, and syncs multi-language XMLs.

Cross-references string handles across Stats/*.txt, RootTemplates/*.lsx, and
Progressions/*.lsx against Localization/English/*.xml to detect orphans, find
missing keys, and generate foreign language translation skeletons.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

HANDLE_PATTERN = re.compile(r'(h[0-9a-fA-F]{32}|h[a-zA-Z0-9_]{30,40})(?:;\d+)?')

LANGUAGE_DIR_MAP = {
    "de": "German",
    "german": "German",
    "es": "Spanish",
    "spanish": "Spanish",
    "fr": "French",
    "french": "French",
    "it": "Italian",
    "italian": "Italian",
    "ru": "Russian",
    "russian": "Russian",
    "pt": "BrazilianPortuguese",
    "brazilian": "BrazilianPortuguese",
    "zh": "Chinese",
    "chinese": "Chinese",
}


def resolve_mod_dir(mod_path_or_slug: str, workspace_root: Path) -> Path:
    candidate = Path(mod_path_or_slug)
    if candidate.is_dir():
        return candidate
    for parent in ["my_mods", "mods"]:
        c = workspace_root / parent / mod_path_or_slug
        if c.is_dir():
            return c
    raise FileNotFoundError(f"Mod directory not found: '{mod_path_or_slug}'")


def collect_referenced_handles(mod_dir: Path) -> dict[str, list[str]]:
    """Collects all handle occurrences across stats, LSX, and metadata."""
    referenced = {}

    for path in mod_dir.rglob("*"):
        if not path.is_file():
            continue

        # Skip localization files themselves
        if "localization" in [p.lower() for p in path.parts]:
            continue

        ext = path.suffix.lower()
        if ext not in [".txt", ".lsx", ".xml"]:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            for match in HANDLE_PATTERN.finditer(content):
                h = match.group(1).strip()
                if h:
                    referenced.setdefault(h, []).append(str(path.relative_to(mod_dir)))
        except Exception:
            continue

    return referenced


def load_english_xml(mod_dir: Path) -> tuple[Path, dict[str, str], ET.ElementTree]:
    """Loads Localization/English/<Mod>.xml, returns (file_path, handle_map, ElementTree)."""
    loc_dir = mod_dir / "Localization" / "English"
    if not loc_dir.is_dir():
        raise FileNotFoundError(f"Missing Localization/English directory in '{mod_dir}'.")

    xml_files = list(loc_dir.glob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(f"No XML localization files found in '{loc_dir}'.")

    target_file = xml_files[0]
    tree = ET.parse(target_file)

    handle_map = {}
    for node in tree.findall(".//content"):
        h = node.get("contentuid", "").strip()
        text = (node.text or "").strip()
        if h:
            handle_map[h] = text

    return target_file, handle_map, tree


def prune_orphan_handles(xml_file: Path, orphans: set[str], dry_run: bool = False) -> None:
    """Removes orphan content tags from the XML file and creates a backup."""
    if not orphans or dry_run:
        return

    # Backup
    backup_path = xml_file.with_suffix(f".xml.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.bak")
    shutil.copy2(xml_file, backup_path)

    tree = ET.parse(xml_file)
    root = tree.getroot()

    removed_count = 0
    for node in list(root.findall(".//content")):
        h = node.get("contentuid", "").strip()
        if h in orphans:
            root.remove(node)
            removed_count += 1

    rough = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    pretty = reparsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")
    lines = [line for line in pretty.splitlines() if line.strip()]

    xml_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_language_skeletons(
    mod_dir: Path,
    source_xml: Path,
    languages: list[str],
    dry_run: bool = False,
) -> list[str]:
    """Generates skeleton XMLs for target foreign languages."""
    tree = ET.parse(source_xml)
    created = []

    for lang_code in languages:
        folder_name = LANGUAGE_DIR_MAP.get(lang_code.lower(), lang_code.capitalize())
        target_dir = mod_dir / "Localization" / folder_name
        target_file = target_dir / source_xml.name

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            if not target_file.exists():
                shutil.copy2(source_xml, target_file)
                created.append(str(target_file.relative_to(mod_dir)))
        else:
            created.append(f"[dry-run] {target_file.relative_to(mod_dir)}")

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Audit, prune orphaned string handles, and sync multi-language localization XMLs."
    )
    parser.add_argument("--mod", required=True, help="Mod name/slug or directory path.")
    parser.add_argument("--check", action="store_true", help="Audit mode (exits with code 1 if missing handles found).")
    parser.add_argument("--prune", action="store_true", help="Remove orphan handles from English XML (creates .bak backup).")
    parser.add_argument(
        "--sync-languages",
        help="Comma-separated language codes to generate translation skeletons for (e.g. 'de,es,fr,it,ru').",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview modifications without writing.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON summary.")

    args = parser.parse_args()
    workspace_root = Path(__file__).resolve().parent.parent

    try:
        mod_dir = resolve_mod_dir(args.mod, workspace_root)
        xml_file, declared_handles, _ = load_english_xml(mod_dir)
        referenced_handles = collect_referenced_handles(mod_dir)

        declared_set = set(declared_handles.keys())
        referenced_set = set(referenced_handles.keys())

        orphans = declared_set - referenced_set
        missing = referenced_set - declared_set

        pruned_count = 0
        if args.prune and orphans:
            prune_orphan_handles(xml_file, orphans, dry_run=args.dry_run)
            pruned_count = len(orphans)

        synced_files = []
        if args.sync_languages:
            langs = [l.strip() for l in args.sync_languages.split(",") if l.strip()]
            synced_files = sync_language_skeletons(mod_dir, xml_file, langs, dry_run=args.dry_run)

        res = {
            "mod": mod_dir.name,
            "xml_file": str(xml_file),
            "declared_count": len(declared_set),
            "referenced_count": len(referenced_set),
            "orphans_count": len(orphans),
            "orphans": sorted(list(orphans)),
            "missing_count": len(missing),
            "missing": sorted(list(missing)),
            "pruned": pruned_count,
            "synced_languages": synced_files,
            "status": "clean" if (not missing and not orphans) else "issues_detected",
        }

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Localization Audit: {mod_dir.name} ({xml_file.name})")
            print("=" * 70)
            print(f"  Declared handles in XML:   {len(declared_set)}")
            print(f"  Referenced in stats/LSX:   {len(referenced_set)}")
            print(f"  Orphaned handles in XML:   {len(orphans)}")
            print(f"  Missing handles in XML:    {len(missing)}")

            if orphans:
                print(f"\n  Orphaned Handles ({len(orphans)}):")
                for h in sorted(list(orphans))[:10]:
                    print(f"    - {h} ('{declared_handles[h]}')")
                if len(orphans) > 10:
                    print(f"    ... and {len(orphans) - 10} more.")

            if missing:
                print(f"\n  Missing Handles ({len(missing)}):")
                for h in sorted(list(missing))[:10]:
                    sources = ", ".join(referenced_handles[h][:2])
                    print(f"    - {h} (referenced in {sources})")
                if len(missing) > 10:
                    print(f"    ... and {len(missing) - 10} more.")

            if args.prune:
                dry_str = " [DRY-RUN]" if args.dry_run else ""
                print(f"\n[✓] Pruned {pruned_count} orphan handle(s) from XML{dry_str}.")

            if synced_files:
                print(f"\n[✓] Synchronized language skeletons:")
                for sf in synced_files:
                    print(f"    - {sf}")

        if args.check and missing:
            return 1
        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
