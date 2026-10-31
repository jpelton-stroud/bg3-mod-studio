#!/usr/bin/env python3
"""
save_inspector.py - Inspects BG3 .lsv save files and audits them against active mod load orders.

Unpacks save metadata and mod lists from LSPK v18 save archives and compares them
against modsettings.lsx to warn of missing or mismatched mods before loading the game.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import detect_bg3_appdata_dirs
from bg3_core.lspk import LspkArchive, build_lspk_archive


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

    search_dirs: list[Path] = []
    if save_dir_arg:
        search_dirs.append(Path(save_dir_arg))
    search_dirs.extend(get_save_search_paths())

    candidates: list[tuple[float, Path]] = []
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
            "No .lsv save games found. Searched:\n" + "\n".join(f"  - {d}" for d in dirs_searched)
        )

    # Return latest
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _parse_lsf_save_mods(lsf_bytes: bytes) -> list[dict[str, str]]:
    """Extracts ModuleShortDesc entries from binary LSOF meta.lsf via AST traversal with regex fallback."""
    # 1. Primary path: Pure-Python LSF AST decompiler
    try:
        from bg3_core.lsf import LsfDocument

        doc = LsfDocument.from_bytes(lsf_bytes)
        mod_nodes = doc.find_all("ModuleShortDesc")
        if mod_nodes:
            ast_mods: list[dict[str, str]] = []
            for node in mod_nodes:
                uuid_val = str(node.get_attr_value("UUID") or "")
                name_val = str(node.get_attr_value("Name") or "")
                folder_val = str(node.get_attr_value("Folder") or "")
                ver_val = str(node.get_attr_value("Version64") or "")
                if uuid_val or name_val:
                    ast_mods.append({
                        "uuid": uuid_val,
                        "name": name_val,
                        "folder": folder_val,
                        "version": ver_val,
                    })
            if ast_mods:
                return ast_mods
    except Exception:
        pass

    # 2. Fallback path: Raw binary payload scanning
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

    mods: list[dict[str, str]] = []
    pattern = re.compile(rb"([0-9a-f]{32})\x00([A-Za-z0-9_\-\. ]{2,128})\x00([A-Za-z0-9_\-\. ]{2,128})\x00")
    for m in pattern.finditer(payload):
        md5_pos = m.start()
        folder = m.group(2).decode("utf-8", errors="ignore")
        name = m.group(3).decode("utf-8", errors="ignore")
        mod_uuid = ""
        ver_str = ""
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


def extract_save_metadata(save_path: Path) -> dict[str, Any]:
    """Extracts meta.lsx or meta.lsf + SaveInfo.json from the .lsv LSPK package using mmap."""
    if LspkArchive is None:
        raise ImportError("LspkArchive unpacker not available in environment.")

    file_size = save_path.stat().st_size

    with LspkArchive.open(save_path, use_mmap=True) as archive:
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
            "size_bytes": file_size,
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


def audit_against_modsettings(save_mods: list[dict[str, Any]], workspace_root: Path | None = None) -> dict[str, Any]:
    """Compares save mod list against active modsettings.lsx."""
    from bg3_core.manage_load_order import (
        CORE_GUSTAV_NAMES,
        detect_modsettings_path,
        parse_modsettings,
    )

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


def prune_missing_mods_from_save(
    save_path: Path,
    output_path: Path | None = None,
    target_uuids: list[str] | None = None,
    dry_run: bool = False,
) -> tuple[bool, list[str]]:
    """Prunes missing or uninstalled mod records from a .lsv save file.

    Extracts meta.lsf / meta.lsx, removes ModuleShortDesc / Mod entries matching
    missing mods (or explicit target_uuids), re-serializes the binary LSF AST,
    and repacks the .lsv archive without corrupting the savegame.

    Returns:
        (success, list_of_pruned_mod_names_or_uuids)
    """
    save_path = Path(save_path).resolve()
    if not save_path.is_file():
        raise FileNotFoundError(f"Save file not found: '{save_path}'")

    if LspkArchive is None:
        raise ImportError("LspkArchive unpacker not available in environment.")

    meta = extract_save_metadata(save_path)
    save_mods = meta.get("mods", [])

    if target_uuids is not None:
        uuids_to_remove = {u.strip().lower() for u in target_uuids if u.strip()}
    else:
        audit_result = audit_against_modsettings(save_mods)
        uuids_to_remove = {m["uuid"].strip().lower() for m in audit_result.get("missing_mods", []) if m.get("uuid")}

    if not uuids_to_remove:
        return True, []

    # Map matched mods for informative return
    pruned_mods: list[str] = []
    for m in save_mods:
        m_uuid = m.get("uuid", "").strip().lower()
        if m_uuid in uuids_to_remove:
            label = m.get("name") or m.get("folder") or m_uuid
            pruned_mods.append(label)

    for u in uuids_to_remove:
        if not any(m.get("uuid", "").strip().lower() == u for m in save_mods):
            pruned_mods.append(u)

    if dry_run:
        return True, pruned_mods

    dest_path = Path(output_path).resolve() if output_path else save_path
    if dest_path == save_path:
        backup_path = save_path.with_name(save_path.name + ".bak")
        if not backup_path.exists():
            shutil.copy2(save_path, backup_path)

    archive_files: list[tuple[str, bytes]] = []
    with LspkArchive.open(save_path, use_mmap=False) as archive:
        for entry in archive.files:
            name = entry["name"]
            norm = name.replace("\\", "/").lower()
            raw = archive.extract_file(entry)

            if norm.endswith("meta.lsf"):
                from bg3_core.lsf import LsfDocument, LsfNode

                doc = LsfDocument.from_bytes(raw)

                def _prune_lsf_node(node: LsfNode) -> None:
                    kept_children: list[LsfNode] = []
                    for child in node.children:
                        if child.name in ("ModuleShortDesc", "Mod"):
                            c_uuid = str(child.get_attr_value("UUID") or "").strip().lower()
                            if c_uuid and c_uuid in uuids_to_remove:
                                continue
                        _prune_lsf_node(child)
                        kept_children.append(child)
                    node.children = kept_children

                new_roots: list[LsfNode] = []
                for r in doc.root_nodes:
                    if r.name in ("ModuleShortDesc", "Mod"):
                        r_uuid = str(r.get_attr_value("UUID") or "").strip().lower()
                        if r_uuid and r_uuid in uuids_to_remove:
                            continue
                    _prune_lsf_node(r)
                    new_roots.append(r)
                doc.root_nodes = new_roots
                archive_files.append((name, doc.to_bytes(compress=True)))

            elif norm.endswith("meta.lsx"):
                tree = ET.fromstring(raw)
                for parent in tree.iter():
                    to_remove = []
                    for child in list(parent):
                        if child.tag == "node" and child.get("id") in ("Mod", "ModuleShortDesc"):
                            u_attr = child.find("attribute[@id='UUID']")
                            if u_attr is not None:
                                val = (u_attr.get("value") or "").strip().lower()
                                if val in uuids_to_remove:
                                    to_remove.append(child)
                    for child in to_remove:
                        parent.remove(child)
                archive_files.append((name, ET.tostring(tree, encoding="utf-8")))

            else:
                archive_files.append((name, raw))

    repacked_bytes = build_lspk_archive(archive_files, compress=True)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(repacked_bytes)

    return True, pruned_mods


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect BG3 .lsv save files and audit them against active mod load orders."
    )
    parser.add_argument("save_pos", nargs="?", help="Path to .lsv save file, or 'latest' (positional).")
    parser.add_argument("--save", dest="save_flag", help="Path to .lsv save file, or 'latest' to automatically discover.")
    parser.add_argument("--save-dir", help="Custom directory containing .lsv save files.")
    parser.add_argument("--audit", action="store_true", help="Compare save mod list against active modsettings.lsx.")
    parser.add_argument("--clean-missing", action="store_true", help="Prune missing mods from save game.")
    parser.add_argument("--out", help="Output path for cleaned save file.")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Simulate pruning without modifying files.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")

    args = parser.parse_args(argv)

    color = ConsoleColor(stream=sys.stdout)
    err_color = ConsoleColor(stream=sys.stderr)
    save_arg = args.save_flag or args.save_pos

    try:
        save_file = find_save_file(save_arg, args.save_dir)
        meta = extract_save_metadata(save_file)

        audit_result = None
        if args.audit or args.clean_missing:
            audit_result = audit_against_modsettings(meta["mods"])
            meta["audit"] = audit_result

        if args.clean_missing:
            out_p = Path(args.out) if args.out else None
            ok, pruned = prune_missing_mods_from_save(save_file, output_path=out_p, dry_run=args.dry_run)
            if args.json:
                print(json.dumps({
                    "save_file": str(save_file),
                    "output_file": str(out_p or save_file),
                    "dry_run": args.dry_run,
                    "pruned_mods": pruned,
                    "success": ok,
                }, indent=2))
            else:
                action = "Previewed pruning" if args.dry_run else "Successfully pruned"
                print(f"{color.green('[✓]')} {action} {len(pruned)} missing mod(s).")
                for p in pruned:
                    print(f"    - {p}")
                if not args.dry_run:
                    print(f"    Target output: {out_p or save_file}")
            return ExitCode.OK

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
