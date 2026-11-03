"""Clean-room isolation, deduplication, and quarantine management for BG3 mods."""

from __future__ import annotations

import datetime
import json
import re
import shutil
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

from ..binary.lspk import BG3BinaryError, LspkArchive
from ..env_paths import detect_bg3_appdata_dirs, detect_data_dir
from .modsettings_io import (
    CORE_SYSTEM_NAMES,
    CORE_SYSTEM_UUIDS,
    _extract_meta_from_xml_text,
    save_modsettings,
)


def isolate_load_order(path: Path, keep_uuids: set[str], dry_run: bool = False) -> int:
    """Disables all mods in modsettings.lsx except Patch 8 core system modules and those in keep_uuids."""
    if not path.is_file():
        return 0

    tree = ET.parse(path)
    root = tree.getroot()

    root_children = root.find(".//node[@id='root']/children")
    if root_children is None:
        root_node = root.find(".//node[@id='root']")
        if root_node is None:
            root_node = ET.SubElement(root, "node", id="root")
        root_children = ET.SubElement(root_node, "children")

    mod_order_node = root.find(".//node[@id='ModOrder']")
    if mod_order_node is None:
        mod_order_node = ET.Element("node", id="ModOrder")
        root_children.insert(0, mod_order_node)
    mod_order_children = mod_order_node.find("children")
    if mod_order_children is None:
        mod_order_children = ET.SubElement(mod_order_node, "children")

    mods_children = root.find(".//node[@id='Mods']/children")
    if mods_children is None:
        mods_node = root.find(".//node[@id='Mods']")
        if mods_node is None:
            mods_node = ET.SubElement(root_children, "node", id="Mods")
        mods_children = ET.SubElement(mods_node, "children")

    norm_keep = {u.lower().strip() for u in keep_uuids if u}

    removed_count = 0
    # Clean Mods
    for desc in list(mods_children.findall("node[@id='ModuleShortDesc']")):
        u_attr = desc.find("attribute[@id='UUID']")
        n_attr = desc.find("attribute[@id='Name']")
        f_attr = desc.find("attribute[@id='Folder']")
        u_val = (u_attr.get("value", "") if u_attr is not None else "").lower().strip()
        n_val = (n_attr.get("value", "") if n_attr is not None else "").lower().strip()
        f_val = (f_attr.get("value", "") if f_attr is not None else "").lower().strip()

        if u_val in CORE_SYSTEM_UUIDS or n_val in CORE_SYSTEM_NAMES or f_val in CORE_SYSTEM_NAMES:
            continue
        if u_val not in norm_keep:
            mods_children.remove(desc)
            removed_count += 1

    # Clean ModOrder
    for m_node in list(mod_order_children.findall("node[@id='Module']")):
        u_attr = m_node.find("attribute[@id='UUID']")
        u_val = (u_attr.get("value", "") if u_attr is not None else "").lower().strip()
        if u_val in CORE_SYSTEM_UUIDS or u_val in norm_keep:
            continue
        mod_order_children.remove(m_node)

    if not dry_run:
        save_modsettings(path, tree)

    return removed_count


def get_pak_module_info(pak_path: Path) -> dict | None:
    """Extract UUID, Name, Folder, Version64 from meta.lsx inside a .pak archive."""
    try:
        with LspkArchive.open(pak_path, use_mmap=True) as archive:
            for entry in archive.files:
                if entry["name"].replace("\\", "/").lower().endswith("meta.lsx"):
                    xml_txt = archive.extract_file(entry).decode("utf-8", errors="ignore")
                    return _extract_meta_from_xml_text(xml_txt, pak_path.stem)
    except (OSError, struct.error, zlib.error, BG3BinaryError):
        pass
    return None


def clean_steam_data_paks(dry_run: bool = False) -> list[dict]:
    """
    Purge or archive stray .pak archives from Steam <Game>/Data/Mods/.
    Custom mods must reside in AppData/Mods; .pak files in Steam Data/Mods cause duplicate registration collisions.
    """
    data_dir = detect_data_dir()
    if not data_dir:
        return []
    steam_mods = data_dir / "Mods"
    if not steam_mods.is_dir():
        return []

    cleaned = []
    quarantine_steam = None
    for appdata in detect_bg3_appdata_dirs():
        quarantine_steam = appdata / "Mods_Disabled" / "steam_data_paks"
        break

    for pak_file in sorted(steam_mods.glob("*.pak")):
        if not pak_file.is_file():
            continue
        dest = (quarantine_steam / pak_file.name) if quarantine_steam else None
        record = {
            "file": pak_file.name,
            "path": str(pak_file),
            "destination": str(dest) if dest else "",
            "action": "removed_steam_data_pak",
        }
        cleaned.append(record)
        if not dry_run:
            if quarantine_steam:
                quarantine_steam.mkdir(parents=True, exist_ok=True)
                if dest and dest.exists():
                    dest.unlink()
                if dest:
                    shutil.move(str(pak_file), str(dest))
            else:
                pak_file.unlink()

    return cleaned


def deduplicate_installed_paks(
    mods_dir: Path,
    quarantine_base: Path | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    Find duplicate .pak archives sharing the same ModuleInfo UUID in mods_dir.
    Keeps canonical <Folder>_<UUID>.pak or newest archive, moving redundant copies to Mods_Disabled/duplicates/.
    Also cleans stray .pak.bak files.
    """
    if not mods_dir.is_dir():
        return []

    duplicates_dir = (quarantine_base or mods_dir.parent / "Mods_Disabled") / "duplicates"
    results = []

    # 1. Clean stray .pak.bak files
    for bak_file in sorted(mods_dir.glob("*.pak.bak")) + sorted(mods_dir.glob("*.bak")):
        if not bak_file.is_file():
            continue
        dest = duplicates_dir / bak_file.name
        results.append(
            {
                "action": "removed_bak",
                "file": bak_file.name,
                "path": str(bak_file),
                "destination": str(dest),
            }
        )
        if not dry_run:
            duplicates_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.unlink()
            shutil.move(str(bak_file), str(dest))

    # 2. Group .pak archives by internal module UUID
    paks_by_uuid: dict[str, list[tuple[Path, dict]]] = {}
    for pak_path in sorted(mods_dir.glob("*.pak")):
        info = get_pak_module_info(pak_path)
        if info and info.get("UUID"):
            uuid_key = info["UUID"].lower().strip()
            paks_by_uuid.setdefault(uuid_key, []).append((pak_path, info))

    for uuid_key, entries in paks_by_uuid.items():
        if len(entries) <= 1:
            continue

        def score_entry(
            item: tuple[Path, dict], current_uuid: str = uuid_key
        ) -> tuple[int, int, float]:
            path, meta = item
            stem = path.stem.lower()
            u_clean = current_uuid.replace("-", "")
            is_canonical = (
                f"_{current_uuid}" in stem
                or f"_{u_clean}" in stem
                or (meta.get("Folder", "").lower() in stem and current_uuid in stem)
            )
            is_modio_hash = bool(re.search(r"-[0-9a-z]{4}$", stem))
            try:
                v64 = int(meta.get("Version64", 0))
            except ValueError:
                v64 = 0
            mtime = path.stat().st_mtime
            score = (10 if is_canonical else 0) - (5 if is_modio_hash else 0)
            return (score, v64, mtime)

        sorted_entries = sorted(entries, key=score_entry, reverse=True)
        winner_path, winner_meta = sorted_entries[0]
        losers = sorted_entries[1:]

        for loser_path, _loser_meta in losers:
            dest = duplicates_dir / loser_path.name
            results.append(
                {
                    "action": "deduplicated",
                    "uuid": uuid_key,
                    "winner": winner_path.name,
                    "redundant": loser_path.name,
                    "destination": str(dest),
                }
            )
            if not dry_run:
                duplicates_dir.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    dest.unlink()
                shutil.move(str(loser_path), str(dest))

    return results


def quarantine_unrelated_paks(
    mods_dir: Path,
    keep_uuids: set[str],
    quarantine_base: Path | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    Move all .pak archives whose module UUID is NOT in keep_uuids into Mods_Disabled/.
    Saves quarantine_manifest.json so restore can reliably recover original state.
    """
    if not mods_dir.is_dir():
        return []

    quarantine_dir = quarantine_base or mods_dir.parent / "Mods_Disabled"
    manifest_path = quarantine_dir / "quarantine_manifest.json"
    norm_keep = {u.lower().strip() for u in keep_uuids if u}

    quarantined = []
    manifest_data = {}
    if manifest_path.is_file():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest_data = {}

    for pak_path in sorted(mods_dir.glob("*.pak")):
        info = get_pak_module_info(pak_path)
        u_val = info.get("UUID", "").lower().strip() if info else ""
        if not u_val:
            m = re.search(
                r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
                pak_path.name,
                re.IGNORECASE,
            )
            if m:
                u_val = m.group(1).lower()

        if u_val and u_val in norm_keep:
            continue

        dest = quarantine_dir / pak_path.name
        record = {
            "filename": pak_path.name,
            "uuid": u_val,
            "source": str(pak_path),
            "destination": str(dest),
            "timestamp": datetime.datetime.now().isoformat(),
        }
        quarantined.append(record)
        manifest_data[pak_path.name] = record

        if not dry_run:
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.unlink()
            shutil.move(str(pak_path), str(dest))

    if not dry_run and quarantined:
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    return quarantined


def restore_quarantined_paks(
    mods_dir: Path,
    quarantine_base: Path | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    Restores all quarantined .pak archives from Mods_Disabled/ back into their
    original source directories recorded in quarantine_manifest.json (defaulting to mods_dir).
    """
    quarantine_dir = quarantine_base or mods_dir.parent / "Mods_Disabled"
    if not quarantine_dir.is_dir():
        return []

    restored = []
    manifest_path = quarantine_dir / "quarantine_manifest.json"
    manifest_data: dict[str, dict] = {}
    if manifest_path.is_file():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest_data = {}

    for pak_path in sorted(quarantine_dir.glob("*.pak")):
        if not pak_path.is_file():
            continue
        dest = mods_dir / pak_path.name
        record_info = manifest_data.get(pak_path.name)
        if record_info and record_info.get("source"):
            src_candidate = Path(record_info["source"])
            if src_candidate.parent.exists() or not dry_run:
                dest = src_candidate

        record = {
            "filename": pak_path.name,
            "source": str(pak_path),
            "destination": str(dest),
        }
        restored.append(record)
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.unlink()
            shutil.move(str(pak_path), str(dest))

    if not dry_run and manifest_path.is_file():
        try:
            manifest_path.unlink()
        except OSError:
            pass

    return restored


__all__ = [
    "clean_steam_data_paks",
    "deduplicate_installed_paks",
    "get_pak_module_info",
    "isolate_load_order",
    "quarantine_unrelated_paks",
    "restore_quarantined_paks",
]
