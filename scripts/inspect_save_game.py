#!/usr/bin/env python3
"""
inspect_save_game.py - Inspects BG3 .lsv save files and audits them against active mod load orders.

Unpacks save metadata and mod lists from LSPK v18 save archives and compares them
against modsettings.lsx to warn of missing or mismatched mods before loading the game.
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Ensure workspace root and scripts are in sys.path
workspace_dir = Path(__file__).resolve().parent.parent
if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))
if str(workspace_dir / "scripts") not in sys.path:
    sys.path.insert(0, str(workspace_dir / "scripts"))

# Import LSPK unpacker
try:
    from scripts.modio_extract import LspkArchive
except ImportError:
    try:
        from modio_extract import LspkArchive
    except ImportError:
        LspkArchive = None

STANDARD_SAVE_SEARCH_PATHS = [
    # Linux native / Wine / Proton paths
    Path.home() / ".steam/steam/steamapps/compatdata/1086940/pfx/drive_c/users/steamuser/AppData/Local/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/Savegames/Story",
    Path.home() / ".local/share/Steam/steamapps/compatdata/1086940/pfx/drive_c/users/steamuser/AppData/Local/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/Savegames/Story",
    Path.home() / ".local/share/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/Savegames/Story",
    # Windows native
    Path(os.environ.get("LOCALAPPDATA", "")) / "Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/Savegames/Story",
]


def find_save_file(save_arg: str | None = None, save_dir_arg: str | None = None) -> Path:
    """Finds target save file or latest save in standard directories."""
    if save_arg and save_arg.lower() != "latest":
        p = Path(save_arg)
        if not p.is_file():
            raise FileNotFoundError(f"Save file not found: '{save_arg}'")
        return p

    search_dirs = []
    if save_dir_arg:
        search_dirs.append(Path(save_dir_arg))
    search_dirs.extend(STANDARD_SAVE_SEARCH_PATHS)

    candidates = []
    for d in search_dirs:
        if d.is_dir():
            for f in d.glob("*.lsv"):
                try:
                    candidates.append((f.stat().st_mtime, f))
                except Exception:
                    continue

    if not candidates:
        dirs_searched = [str(d) for d in search_dirs if str(d).strip()]
        raise FileNotFoundError(
            f"No .lsv save games found. Searched:\n" + "\n".join(f"  - {d}" for d in dirs_searched)
        )

    # Return latest
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def extract_save_metadata(save_path: Path) -> dict:
    """Extracts meta.lsx from the .lsv LSPK package."""
    if LspkArchive is None:
        raise ImportError("LspkArchive unpacker not available in environment.")

    data_bytes = save_path.read_bytes()
    archive = LspkArchive(data_bytes)

    meta_entry = None
    for entry in archive.files:
        norm = entry["name"].replace("\\", "/").lower()
        if norm.endswith("meta.lsx"):
            meta_entry = entry
            break

    if not meta_entry:
        raise ValueError(f"No meta.lsx found inside save archive: {save_path.name}")

    meta_bytes = archive.extract_file(meta_entry)
    tree = ET.fromstring(meta_bytes)

    # Extract save attributes
    save_info = {
        "save_file": str(save_path),
        "save_name": save_path.stem,
        "size_bytes": len(data_bytes),
        "level_name": "",
        "save_time": "",
        "version": "",
        "mods": [],
    }

    # Meta node search
    for attr in tree.findall(".//attribute"):
        attr_id = attr.get("id")
        val = attr.get("value", "")
        if attr_id == "LevelName":
            save_info["level_name"] = val
        elif attr_id == "Timestamp":
            save_info["save_time"] = val
        elif attr_id == "Version64":
            save_info["version"] = val

    # Extract mod list
    for mod_node in tree.findall(".//node[@id='Mod']"):
        uuid_attr = mod_node.find("attribute[@id='UUID']")
        name_attr = mod_node.find("attribute[@id='Name']")
        folder_attr = mod_node.find("attribute[@id='Folder']")
        ver_attr = mod_node.find("attribute[@id='Version']")

        if uuid_attr is not None:
            save_info["mods"].append({
                "uuid": uuid_attr.get("value", ""),
                "name": name_attr.get("value", "") if name_attr is not None else "",
                "folder": folder_attr.get("value", "") if folder_attr is not None else "",
                "version": ver_attr.get("value", "") if ver_attr is not None else "",
            })

    return save_info


def audit_against_modsettings(save_mods: list[dict], workspace_root: Path) -> dict:
    """Compares save mod list against active modsettings.lsx."""
    try:
        from scripts.manage_load_order import detect_modsettings_path, parse_modsettings
    except ImportError:
        from manage_load_order import detect_modsettings_path, parse_modsettings

    settings_file = detect_modsettings_path()
    if not settings_file or not settings_file.exists():
        return {
            "modsettings_path": str(settings_file) if settings_file else None,
            "status": "modsettings_not_found",
            "message": "Could not locate active modsettings.lsx profile to compare against.",
            "total_save_mods": len(save_mods),
            "missing_mods": [],
            "new_mods": [],
        }

    parsed = parse_modsettings(settings_file)
    active_mods = parsed.get("mods", {})

    active_by_uuid = {u.lower(): m for u, m in active_mods.items()}
    save_by_uuid = {m["uuid"].lower(): m for m in save_mods}

    # Exclude base game GustavDev
    gustav_uuid = "28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8".lower()
    save_by_uuid.pop(gustav_uuid, None)
    active_by_uuid.pop(gustav_uuid, None)

    missing_in_active = []
    for u, sm in save_by_uuid.items():
        if u not in active_by_uuid:
            missing_in_active.append(sm)

    new_in_active = []
    for u, am in active_by_uuid.items():
        if u not in save_by_uuid:
            new_in_active.append({
                "uuid": u,
                "name": am.get("Name", ""),
                "folder": am.get("Folder", ""),
            })

    return {
        "modsettings_path": str(settings_file),
        "total_save_mods": len(save_mods),
        "total_active_mods": len(active_mods),
        "missing_mods": missing_in_active,
        "new_mods": new_in_active,
        "status": "safe" if not missing_in_active else "missing_mods_warning",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Inspect BG3 .lsv save files and audit them against active mod load orders."
    )
    parser.add_argument("--save", help="Path to .lsv save file, or 'latest' to automatically discover.")
    parser.add_argument("--save-dir", help="Custom directory containing .lsv save files.")
    parser.add_argument("--audit", action="store_true", help="Compare save mod list against active modsettings.lsx.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")

    args = parser.parse_args()
    workspace_root = Path(__file__).resolve().parent.parent

    try:
        save_file = find_save_file(args.save, args.save_dir)
        meta = extract_save_metadata(save_file)

        audit_result = None
        if args.audit:
            audit_result = audit_against_modsettings(meta["mods"], workspace_root)
            meta["audit"] = audit_result

        if args.json:
            print(json.dumps(meta, indent=2))
        else:
            print(f"BG3 Save Game Inspection: {save_file.name}")
            print("=" * 70)
            print(f"  Path:        {save_file}")
            print(f"  Size:        {meta['size_bytes'] / (1024*1024):.2f} MB")
            if meta["level_name"]:
                print(f"  Level/Act:   {meta['level_name']}")
            print(f"  Active Mods: {len(meta['mods'])}")

            if meta["mods"]:
                print("\n  Recorded Mods:")
                for m in meta["mods"]:
                    print(f"    • {m['name']:<30} (UUID: {m['uuid']})")

            if audit_result:
                print("\n" + "=" * 70)
                print("Mod Load Order Audit:")
                if audit_result["missing_mods"]:
                    print("  [!] WARNING: Missing mods in current profile (Save may fail or crash):")
                    for m in audit_result["missing_mods"]:
                        print(f"      ✗ {m['name']} ({m['uuid']})")
                else:
                    print("  [✓] All required mods are present and active in current profile.")

                if audit_result["new_mods"]:
                    print("\n  [i] New mods enabled since save was created:")
                    for m in audit_result["new_mods"]:
                        print(f"      + {m['name']} ({m['uuid']})")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
