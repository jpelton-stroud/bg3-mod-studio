#!/usr/bin/env python3
"""
inspect_save_game.py - Inspects BG3 .lsv save files and audits them against active mod load orders.

Unpacks save metadata and mod lists from LSPK v18 save archives and compares them
against modsettings.lsx to warn of missing or mismatched mods before loading the game.
"""

import argparse
import json
import os
import re
import struct
import sys
from typing import Any
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import detect_bg3_appdata_dirs
from bg3_core.lspk import LspkArchive


def get_save_search_paths() -> list[Path]:
    paths: list[Path] = []
    for appdata in detect_bg3_appdata_dirs():
        paths.append(appdata / "PlayerProfiles/Public/Savegames/Story")
    return paths


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
    search_dirs.extend(get_save_search_paths())

    candidates = []
    for d in search_dirs:
        if d.is_dir():
            for f in d.rglob("*.lsv"):
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


def _parse_lsf_save_mods(lsf_bytes: bytes) -> list[dict]:
    """Extracts ModuleShortDesc entries from binary LSOF v7 meta.lsf values chunk."""
    from bg3_core.lspk import lz4_frame_or_block_decompress

    payload = lsf_bytes
    if len(lsf_bytes) >= 64 and lsf_bytes[:4] == b"LSOF":
        try:
            vals = struct.unpack_from("<4sIqIIIIIIIIII", lsf_bytes, 0)
            hdr_sz = 64 if vals[1] >= 7 else 56
            val_off = hdr_sz + vals[4] + vals[6] + vals[8] + vals[10]
            val_uncomp_sz, val_comp_sz = vals[11], vals[12]
            if val_comp_sz > 0 and val_off + val_comp_sz <= len(lsf_bytes):
                payload = lz4_frame_or_block_decompress(
                    lsf_bytes[val_off : val_off + val_comp_sz], val_uncomp_sz
                )
        except Exception:
            payload = lsf_bytes

    mods = []
    # In LSOF values table, each ModuleShortDesc stores:
    # 16-byte Larian GUID (<IHHHHHH) + 8-byte Version64 + 32-char MD5 + \x00 + Folder + \x00 + Name + \x00
    pattern = re.compile(rb"([0-9a-f]{32})\x00([A-Za-z0-9_\-\. ]{2,128})\x00([A-Za-z0-9_\-\. ]{2,128})\x00")
    for m in pattern.finditer(payload):
        md5_pos = m.start()
        folder = m.group(2).decode("utf-8", errors="ignore")
        name = m.group(3).decode("utf-8", errors="ignore")
        mod_uuid = ""
        ver_str = ""
        # Check if Folder has trailing _<UUID>
        uuid_suffix = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$", folder)
        if uuid_suffix:
            mod_uuid = uuid_suffix.group(1)
        elif md5_pos >= 24:
            guid_bytes = payload[md5_pos - 24 : md5_pos - 8]
            d1, d2, d3, d4, d5, d6, d7 = struct.unpack("<IHHHHHH", guid_bytes)
            mod_uuid = f"{d1:08x}-{d2:04x}-{d3:04x}-{d4:04x}-{d5:04x}{d6:04x}{d7:04x}"
        if md5_pos >= 8:
            ver_int = struct.unpack("<q", payload[md5_pos - 8 : md5_pos])[0]
            ver_str = str(ver_int)
        if mod_uuid:
            mods.append({
                "uuid": mod_uuid,
                "name": name,
                "folder": folder,
                "version": ver_str,
            })
    return mods


def extract_save_metadata(save_path: Path) -> dict:
    """Extracts meta.lsx or meta.lsf + SaveInfo.json from the .lsv LSPK package."""
    if LspkArchive is None:
        raise ImportError("LspkArchive unpacker not available in environment.")

    data_bytes = save_path.read_bytes()
    archive = LspkArchive(data_bytes)

    meta_lsx_entry = None
    meta_lsf_entry = None
    save_info_entry = None
    for entry in archive.files:
        norm = entry["name"].replace("\\", "/").lower()
        if norm.endswith("meta.lsx"):
            meta_lsx_entry = entry
        elif norm.endswith("meta.lsf"):
            meta_lsf_entry = entry
        elif norm.endswith("saveinfo.json"):
            save_info_entry = entry

    if not meta_lsx_entry and not meta_lsf_entry:
        raise ValueError(f"No meta.lsx or meta.lsf found inside save archive: {save_path.name}")

    save_info: dict[str, Any] = {
        "save_file": str(save_path),
        "save_name": save_path.stem,
        "size_bytes": len(data_bytes),
        "level_name": "",
        "save_time": "",
        "version": "",
        "mods": [],
    }

    if save_info_entry is not None:
        try:
            info_json = json.loads(archive.extract_file(save_info_entry).decode("utf-8", errors="ignore"))
            save_info["level_name"] = info_json.get("Current Level", "")
            save_info["version"] = info_json.get("Game Version", "")
        except Exception:
            pass

    if meta_lsx_entry is not None:
        meta_bytes = archive.extract_file(meta_lsx_entry)
        tree = ET.fromstring(meta_bytes)

        for attr in tree.findall(".//attribute"):
            attr_id = attr.get("id")
            val = attr.get("value", "")
            if attr_id == "LevelName" and not save_info["level_name"]:
                save_info["level_name"] = val
            elif attr_id == "Timestamp":
                save_info["save_time"] = val
            elif attr_id == "Version64" and not save_info["version"]:
                save_info["version"] = val

        mod_nodes = tree.findall(".//node[@id='Mod']") or tree.findall(".//node[@id='Mods']//node[@id='ModuleShortDesc']")
        for mod_node in mod_nodes:
            uuid_attr = mod_node.find("attribute[@id='UUID']")
            name_attr = mod_node.find("attribute[@id='Name']")
            folder_attr = mod_node.find("attribute[@id='Folder']")
            ver_attr = mod_node.find("attribute[@id='Version']") or mod_node.find("attribute[@id='Version64']")

            if uuid_attr is not None:
                save_info["mods"].append({
                    "uuid": uuid_attr.get("value", ""),
                    "name": name_attr.get("value", "") if name_attr is not None else "",
                    "folder": folder_attr.get("value", "") if folder_attr is not None else "",
                    "version": ver_attr.get("value", "") if ver_attr is not None else "",
                })
    elif meta_lsf_entry is not None:
        lsf_bytes = archive.extract_file(meta_lsf_entry)
        save_info["mods"] = _parse_lsf_save_mods(lsf_bytes)

    return save_info


def audit_against_modsettings(save_mods: list[dict], workspace_root: Path) -> dict:
    """Compares save mod list against active modsettings.lsx."""
    try:
        from bg3_core.manage_load_order import CORE_GUSTAV_NAMES, detect_modsettings_path, parse_modsettings
    except ImportError:
        from manage_load_order import CORE_GUSTAV_NAMES, detect_modsettings_path, parse_modsettings  # type: ignore[no-redef]

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

    active_by_uuid = {
        u.lower(): m for u, m in active_mods.items()
        if (m.get("Name") or m.get("Folder") or "").lower() not in CORE_GUSTAV_NAMES
    }
    save_by_uuid = {
        m["uuid"].lower(): m for m in save_mods
        if (m.get("name") or m.get("folder") or "").lower() not in CORE_GUSTAV_NAMES
    }

    # Exclude base game GustavDev UUID explicitly as well
    gustav_uuid = "28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8"
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
    parser.add_argument("save_pos", nargs="?", help="Path to .lsv save file, or 'latest' (positional).")
    parser.add_argument("--save", dest="save_flag", help="Path to .lsv save file, or 'latest' to automatically discover.")
    parser.add_argument("--save-dir", help="Custom directory containing .lsv save files.")
    parser.add_argument("--audit", action="store_true", help="Compare save mod list against active modsettings.lsx.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")

    args = parser.parse_args()
    workspace_root = Path(__file__).resolve().parents[2]

    color = ConsoleColor(stream=sys.stdout)
    err_color = ConsoleColor(stream=sys.stderr)
    save_arg = args.save_flag or args.save_pos

    try:
        save_file = find_save_file(save_arg, args.save_dir)
        meta = extract_save_metadata(save_file)

        audit_result = None
        if args.audit:
            audit_result = audit_against_modsettings(meta["mods"], workspace_root)
            meta["audit"] = audit_result

        if args.json:
            print(json.dumps(meta, indent=2))
        else:
            print(f"{color.bold('BG3 Save Game Inspection:')} {save_file.name}")
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
                    print(f"  {err_color.red('[!] WARNING:')} Missing mods in current profile (Save may fail or crash):")
                    for m in audit_result["missing_mods"]:
                        print(f"      {err_color.red('✗')} {m['name']} ({m['uuid']})")
                else:
                    print(f"  {color.green('[✓]')} All required mods are present and active in current profile.")

                if audit_result["new_mods"]:
                    print("\n  [i] New mods enabled since save was created:")
                    for m in audit_result["new_mods"]:
                        print(f"      + {m['name']} ({m['uuid']})")

        return ExitCode.OK

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"{err_color.red('[ERROR]')} {e}", file=sys.stderr)
        return ExitCode.GENERAL


if __name__ == "__main__":
    sys.exit(main())
