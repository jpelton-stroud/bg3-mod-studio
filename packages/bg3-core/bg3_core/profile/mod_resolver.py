"""
packages/bg3-core/bg3_core/mod_resolver.py
-------------------------------------------
Centralized dependency metadata resolution and .pak provisioning for Baldur's Gate 3 mods.

Resolution Priority:
1. Hardcoded known engine dependencies (GustavDev, GustavX, UnlockLevelCurve)
2. Local catalog lookup via library catalog (Mods/subscribed/library.md) and meta.lsx
3. Studio workspace search in Mods/authored/ and Mods/subscribed/
4. Remote fallback to mod.io REST API (with automatic cataloging into Mods/subscribed/<slug>/)
"""

import io
import re
import shutil
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from bg3_core.binary.larian_parsers import DEFAULT_VERSION64, find_mod_meta_files, parse_meta_lsx
from bg3_core.binary.lspk import LspkArchive
from bg3_core.env_paths import (
    detect_bg3_appdata_dirs,
    detect_data_dir,
    get_authored_mods_dir,
    get_library_catalog_path,
    get_subscribed_mods_dir,
    normalize_mod_key,
)
from bg3_core.exceptions import BG3BinaryError, BG3Error
from bg3_core.modio.library_catalog import parse_library_rows

# Known common core dependencies
KNOWN_DEPENDENCIES: Dict[str, Dict[str, Any]] = {
    "GustavDev": {
        "Folder": "GustavDev",
        "MD5": "33c1655f7ae3559b579ff3b9d2c45413",
        "Name": "GustavDev",
        "PublishHandle": 0,
        "UUID": "28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8",
        "Version64": 145100393449790344,
    },
    "GustavX": {
        "Folder": "GustavX",
        "MD5": "ef3fcba3f3684b3088ad1f9874d4957c",
        "Name": "GustavX",
        "PublishHandle": 0,
        "UUID": "cb555efe-2d9e-131f-8195-a89329d218ea",
        "Version64": 145241946983300916,
    },
    "UnlockLevelCurve": {
        "Folder": "UnlockLevelCurve_a2ffd0e4-c407-8642-2611-c934ea0b0a77",
        "MD5": "87dfb0212784985b157a4209e1ab9357",
        "Name": "UnlockLevelCurve - Level 13-20 | Patch 8",
        "PublishHandle": 4166963,
        "UUID": "a2ffd0e4-c407-8642-2611-c934ea0b0a77",
        "Version64": 72057594037927963,
    },
}

CORE_GAME_UUIDS = {
    KNOWN_DEPENDENCIES["GustavDev"]["UUID"],
    KNOWN_DEPENDENCIES["GustavX"]["UUID"],
}


def parse_library_catalog() -> Dict[str, Dict[str, Any]]:
    """
    Parses library.md for documented mod slugs, display titles, and mod.io IDs.
    Returns mapping keyed by normalized mod key -> {name, slug, modio_id, path}.
    """
    catalog: Dict[str, Dict[str, Any]] = {}
    library_md = get_library_catalog_path()
    if not library_md.is_file():
        return catalog

    content = library_md.read_text(encoding="utf-8", errors="ignore")
    rows = parse_library_rows(content)
    for r in rows:
        slug = r["slug"]
        name = r["name"]
        try:
            mid = int(r["mod_id"])
        except ValueError:
            mid = 0
        entry = {
            "Name": name,
            "Slug": slug,
            "ModioID": mid,
            "Path": library_md.parent / slug,
        }
        catalog[normalize_mod_key(slug)] = entry
        catalog[normalize_mod_key(name)] = entry

    return catalog


def extract_metadata_from_meta_lsx(path: Path, fallback_name: str = "") -> Optional[Dict[str, Any]]:
    """Extract standard Larian mod metadata from a meta.lsx file."""
    if not path.is_file():
        return None
    try:
        raw_bytes = path.read_bytes()
        parsed = parse_meta_lsx(raw_bytes)
        if not parsed or "UUID" not in parsed:
            return None

        folder = parsed.get("Folder") or fallback_name
        name = parsed.get("Name") or fallback_name
        v64_raw = parsed.get("Version64", str(DEFAULT_VERSION64))
        try:
            v64 = int(v64_raw)
        except ValueError:
            v64 = DEFAULT_VERSION64

        handle_raw = parsed.get("PublishHandle", "0")
        try:
            handle = int(handle_raw)
        except ValueError:
            handle = 0

        return {
            "Folder": folder,
            "MD5": parsed.get("MD5", ""),
            "Name": name,
            "PublishHandle": handle,
            "UUID": parsed["UUID"],
            "Version64": v64,
        }
    except (ET.ParseError, OSError, KeyError, ValueError):
        return None


def _default_modio_fetcher(clean_id: str, auto_document: bool = True) -> Optional[Dict[str, Any]]:
    """Strategy handler for fetching remote dependency metadata from mod.io."""
    try:
        from bg3_core.modio.modio_client import get_api_key, query_modio

        api_key = get_api_key()
        if not api_key:
            return None

        mod_meta = query_modio(clean_id, api_key)
        if not mod_meta:
            return None

        slug = mod_meta.get("name_id", "")
        m_name = mod_meta.get("name", clean_id)
        m_id = mod_meta.get("id", 0)

        if auto_document:
            try:
                from bg3_core.modio.modio_extract import process_mod

                res = process_mod(
                    query=slug or clean_id,
                    write_spec=True,
                    update_library=True,
                )
                target_dir = Path(res["output_dir"])
                for meta_path in find_mod_meta_files(target_dir):
                    extracted = extract_metadata_from_meta_lsx(meta_path, m_name)
                    if extracted:
                        if not extracted.get("PublishHandle"):
                            extracted["PublishHandle"] = m_id
                        return extracted
            except (OSError, KeyError, ValueError, ET.ParseError, BG3Error):
                pass

        # Return synthesized metadata if auto-documentation did not complete
        return {
            "Folder": slug or clean_id,
            "MD5": "",
            "Name": m_name,
            "PublishHandle": m_id,
            "UUID": str(mod_meta.get("id", "")),
            "Version64": DEFAULT_VERSION64,
        }
    except (OSError, KeyError, ValueError, BG3Error):
        return None


def resolve_dependency_metadata(
    identifier: str,
    auto_document: bool = True,
    strict: bool = False,
    remote_fetcher: Optional[Callable[..., Optional[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Resolves dependency metadata with fallback chain:
    1. Check KNOWN_DEPENDENCIES
    2. Lookup via mods/library.md & local mods/<slug>/data/meta.lsx
    3. Search workspace mods/ & my_mods/
    4. Remote fallback via mod.io REST API (or custom remote_fetcher strategy)
    """
    clean_id = identifier.strip()
    norm_id = normalize_mod_key(clean_id)

    # 1. Check KNOWN_DEPENDENCIES
    for k, v in KNOWN_DEPENDENCIES.items():
        if (
            norm_id == normalize_mod_key(k)
            or norm_id == normalize_mod_key(v["Name"])
            or norm_id == normalize_mod_key(v["Folder"])
            or clean_id.lower() == v["UUID"].lower()
        ):
            return dict(v)

    # 2. Check local mods/library.md catalog
    catalog = parse_library_catalog()
    if norm_id in catalog:
        cat_entry = catalog[norm_id]
        mod_dir = cat_entry["Path"]
        if mod_dir.is_dir():
            for meta_path in find_mod_meta_files(mod_dir):
                meta = extract_metadata_from_meta_lsx(meta_path, cat_entry["Name"])
                if meta:
                    if not meta.get("PublishHandle") and cat_entry.get("ModioID"):
                        meta["PublishHandle"] = cat_entry["ModioID"]
                    return meta

    # Check by UUID if identifier looks like a UUID
    search_bases = (get_subscribed_mods_dir(), get_authored_mods_dir())
    if "-" in clean_id and len(clean_id) >= 32:
        for base in search_bases:
            if not base.is_dir():
                continue
            for child in sorted(base.iterdir()):
                if not child.is_dir():
                    continue
                for meta_path in find_mod_meta_files(child):
                    meta = extract_metadata_from_meta_lsx(meta_path, child.name)
                    if meta and meta["UUID"].lower() == clean_id.lower():
                        return meta

    # 3. Search local directories in mods/ and my_mods/ (exact match first)
    for base in search_bases:
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            c_norm = normalize_mod_key(child.name)
            if c_norm == norm_id:
                for meta_path in find_mod_meta_files(child):
                    meta = extract_metadata_from_meta_lsx(meta_path, child.name)
                    if meta:
                        return meta

    # 3b. Search local directories (substring match fallback)
    for base in search_bases:
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            c_norm = normalize_mod_key(child.name)
            if norm_id in c_norm:
                for meta_path in find_mod_meta_files(child):
                    meta = extract_metadata_from_meta_lsx(meta_path, child.name)
                    if meta:
                        return meta

    # 4. Remote fallback via strategy handler
    fetcher = remote_fetcher if remote_fetcher is not None else _default_modio_fetcher
    try:
        import inspect

        sig = inspect.signature(fetcher)
        if len(sig.parameters) >= 2:
            remote_meta = fetcher(clean_id, auto_document)
        else:
            remote_meta = fetcher(clean_id)

        if remote_meta:
            return remote_meta
    except (OSError, KeyError, ValueError, BG3Error):
        pass

    if strict:
        raise ValueError(f"Could not resolve mod dependency for '{identifier}'.")

    # Fallback placeholder
    return {
        "Folder": clean_id,
        "MD5": "",
        "Name": clean_id,
        "PublishHandle": 0,
        "UUID": "",
        "Version64": DEFAULT_VERSION64,
    }


def find_installed_pak(dep: Dict[str, Any], search_dirs: Sequence[Path]) -> Optional[Path]:
    """Search target directories for a pak matching a mod by Folder, Name, or UUID."""
    folder = dep.get("Folder", "")
    name = dep.get("Name", "")
    dep_uuid = dep.get("UUID", "").lower()

    norm_folder = normalize_mod_key(folder)
    norm_name = normalize_mod_key(name)

    # 1. Fast filename stem matching (prefer canonical names without mod.io hashed suffixes)
    canonical_candidates = []
    fallback_candidates = []
    for s_dir in search_dirs:
        if not s_dir.is_dir():
            continue
        for pak_file in sorted(s_dir.glob("*.pak")):
            p_stem = pak_file.stem
            p_norm = normalize_mod_key(p_stem)
            # Require exact UUID match or exact normalized folder/name equality to avoid falsely matching sub-patches
            if (
                (dep_uuid and dep_uuid in p_stem.lower())
                or p_norm == norm_folder
                or p_norm == norm_name
            ):
                if re.search(r"-[0-9a-z]{4}$", p_stem.lower()):
                    fallback_candidates.append(pak_file)
                else:
                    canonical_candidates.append(pak_file)

    if canonical_candidates:
        return canonical_candidates[0]
    if fallback_candidates:
        return fallback_candidates[0]

    # 2. Deep fallback: Inspect internal meta.lsx in .pak archives for hashed/truncated filenames (e.g. mod.io *-xxxx.pak)
    if dep_uuid:
        for s_dir in search_dirs:
            if not s_dir.is_dir():
                continue
            for pak_file in sorted(s_dir.glob("*.pak")):
                try:
                    with LspkArchive.open(pak_file, use_mmap=True) as archive:
                        for entry in archive.files:
                            if entry["name"].replace("\\", "/").lower().endswith("meta.lsx"):
                                xml_bytes = archive.extract_file(entry)
                                parsed_meta = parse_meta_lsx(xml_bytes)
                                if parsed_meta.get("UUID", "").lower() == dep_uuid:
                                    if not re.search(r"-[0-9a-z]{4}$", pak_file.stem.lower()):
                                        return pak_file
                                    fallback_candidates.append(pak_file)
                                break
                except (OSError, struct.error, zlib.error, BG3BinaryError):
                    pass

    if fallback_candidates:
        return fallback_candidates[0]

    return None


def _default_modio_downloader(dep: Dict[str, Any]) -> Optional[Tuple[str, bytes]]:
    """Strategy handler downloading a mod archive from mod.io."""
    pub_handle = dep.get("PublishHandle")
    mod_name = dep.get("Name", dep.get("Folder", ""))
    try:
        from bg3_core.modio.modio_client import download_mod_file, get_api_key, query_modio

        api_key = get_api_key()
        if not api_key:
            return None

        lookup_query = str(pub_handle) if pub_handle and pub_handle != 0 else mod_name
        mod_meta = query_modio(lookup_query, api_key)
        if not mod_meta:
            return None

        archive_bytes = download_mod_file(mod_meta, api_key)
        pak_name = f"{dep.get('Folder', mod_meta.get('name_id', 'mod'))}.pak"
        pak_payload: Optional[bytes] = None

        if archive_bytes[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
                for item in z.namelist():
                    if item.lower().endswith(".pak"):
                        pak_name = Path(item).name
                        pak_payload = z.read(item)
                        break
        elif archive_bytes[:4] == b"LSPK":
            pak_payload = archive_bytes

        if pak_payload is not None:
            return (pak_name, pak_payload)
        return None
    except (BG3Error, OSError, ValueError, zipfile.BadZipFile):
        return None


def ensure_dependency_paks(
    dependencies: Sequence[Dict[str, Any]],
    target_dirs: Optional[Sequence[Path]] = None,
    remote_downloader: Optional[Callable[[Dict[str, Any]], Optional[Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Ensures .pak files for dependencies exist in AppData Mods.
    Synchronizes between directories if found in one, or downloads via remote_downloader if missing.
    Custom .pak files must reside in AppData/Mods (never copied to Steam Data/Mods).
    """
    dirs: List[Path] = []
    if target_dirs is None:
        for appdata in detect_bg3_appdata_dirs():
            app_mods = appdata / "Mods"
            if app_mods not in dirs:
                dirs.append(app_mods)
        if not dirs:
            data_mods = detect_data_dir() / "Mods"
            dirs.append(data_mods)
    else:
        dirs = list(target_dirs)

    results: List[Dict[str, Any]] = []

    for dep in dependencies:
        dep_uuid = dep.get("UUID", "")
        if dep_uuid in CORE_GAME_UUIDS or dep.get("Name") in ("GustavDev", "GustavX"):
            continue

        existing_pak = find_installed_pak(dep, dirs)

        if existing_pak and existing_pak.is_file():
            # Synchronize to any target directories missing it
            for t_dir in dirs:
                if find_installed_pak(dep, [t_dir]):
                    continue
                dest = t_dir / existing_pak.name
                if not dest.is_file():
                    t_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(existing_pak, dest)
                        results.append(
                            {
                                "mod": dep.get("Name", dep_uuid),
                                "action": "copied",
                                "source": str(existing_pak),
                                "destination": str(dest),
                                "status": "synchronized",
                            }
                        )
                    except (OSError, shutil.Error) as err:
                        results.append(
                            {
                                "mod": dep.get("Name", dep_uuid),
                                "action": "copy_failed",
                                "error": str(err),
                                "status": "error",
                            }
                        )
            continue

        # Missing from all target directories: attempt to fetch via remote downloader strategy
        mod_name = dep.get("Name", dep.get("Folder", ""))
        downloaded = False
        downloader = remote_downloader if remote_downloader is not None else _default_modio_downloader

        try:
            res = downloader(dep)
            pak_name = f"{dep.get('Folder', 'mod')}.pak"
            pak_payload: Optional[bytes] = None
            if isinstance(res, tuple) and len(res) == 2:
                pak_name, pak_payload = res
            elif isinstance(res, (bytes, bytearray)):
                pak_payload = bytes(res)

            if pak_payload:
                for t_dir in dirs:
                    t_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = t_dir / pak_name
                    dest_file.write_bytes(pak_payload)
                downloaded = True
                results.append(
                    {
                        "mod": mod_name,
                        "action": "downloaded",
                        "filename": pak_name,
                        "size_bytes": len(pak_payload),
                        "status": "downloaded_from_modio",
                    }
                )
        except (BG3Error, OSError, ValueError, zipfile.BadZipFile) as exc:
            results.append(
                {
                    "mod": mod_name,
                    "action": "download_failed",
                    "error": str(exc),
                    "status": "missing",
                }
            )
            continue

        if not downloaded:
            results.append(
                {
                    "mod": mod_name,
                    "action": "not_found",
                    "status": "missing",
                }
            )

    return results
