#!/usr/bin/env python3
"""
manage_load_order.py
--------------------
Inspects, activates, and validates Baldur's Gate 3 mods in the user's
`modsettings.lsx` load order profile without needing to open the in-game Mod Manager.

Features:
- Auto-detects Larian Studios PlayerProfiles directory in WSL and Windows environments
- Lists current active load order, UUIDs, and version information
- Enables custom mods from `my_mods/` by injecting them into ModOrder and Mods nodes
- Disables mods safely while protecting essential base game modules (GustavDev)
- Validates load order rules (GustavDev first, dependencies load before children)
- Creates timestamped backups before writing changes
"""

import argparse
import datetime
import io
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bg3_core.cli_common import ConsoleColor
from bg3_core.env_paths import (
    MODS_DIR,
    MY_MODS_DIR,
    detect_bg3_appdata_dirs,
    detect_data_dir,
    get_env_var,
    normalize_mod_key,
    resolve_mod_dir,
)
from bg3_core.larian_parsers import find_mod_meta_files
from bg3_core.lspk import LspkArchive
from bg3_core.mod_resolver import ensure_dependency_paks, resolve_dependency_metadata

# Zero-dependency ANSI Terminal Colors honoring NO_COLOR
_color = ConsoleColor(stream=sys.stderr)
BOLD = "\033[1m" if _color.enabled else ""
GREEN = "\033[32m" if _color.enabled else ""
YELLOW = "\033[33m" if _color.enabled else ""
RED = "\033[31m" if _color.enabled else ""
CYAN = "\033[36m" if _color.enabled else ""
RESET = "\033[0m" if _color.enabled else ""

# Default GustavDev module entry (for legacy Patch 7 modsettings)
GUSTAV_DEV = {
    "Folder": "GustavDev",
    "MD5": "33c1655f7ae3559b579ff3b9d2c45413",
    "Name": "GustavDev",
    "PublishHandle": "0",
    "UUID": "28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8",
    "Version64": "145100393449790344",
}

CORE_GUSTAV_NAMES = {"gustavdev", "gustavx", "gustav"}

# Full suite of core system modules required by Patch 8 (Build 700)
CORE_SYSTEM_MODULES = [
    {
        "Folder": "GustavX",
        "MD5": "ef3fcba3f3684b3088ad1f9874d4957c",
        "Name": "GustavX",
        "PublishHandle": "0",
        "UUID": "cb555efe-2d9e-131f-8195-a89329d218ea",
        "Version64": "145241946983300916",
    },
    {
        "Folder": "DiceSet_01",
        "MD5": "8edd9729dcdbcafdbba0770834bdd323",
        "Name": "DiceSet_01",
        "PublishHandle": "0",
        "UUID": "e842840a-2449-588c-b0c4-22122cfce31b",
        "Version64": "36028797018963968",
    },
    {
        "Folder": "DiceSet_02",
        "MD5": "9c98eaefccfb3f7cfd6870ff4e84a50d",
        "Name": "DiceSet_02",
        "PublishHandle": "0",
        "UUID": "b176a0ac-d79f-ed9d-5a87-5c2c80874e10",
        "Version64": "36028797018963968",
    },
    {
        "Folder": "DiceSet_03",
        "MD5": "e800e59821eb3090e7e5f25cc478dbd3",
        "Name": "DiceSet_03",
        "PublishHandle": "0",
        "UUID": "e0a4d990-7b9b-8fa9-d7c6-04017c6cf5b1",
        "Version64": "36028797018963968",
    },
    {
        "Folder": "DiceSet_06",
        "MD5": "4a53b4f61b1667007e21c661309b7435",
        "Name": "DiceSet_06",
        "PublishHandle": "0",
        "UUID": "ee4989eb-aab8-968f-8674-812ea2f4bfd7",
        "Version64": "36028797018963968",
    },
    {
        "Folder": "MainUI",
        "MD5": "d41d8cd98f00b204e9800998ecf8427e",
        "Name": "MainUI",
        "PublishHandle": "0",
        "UUID": "630daa32-70f8-3da5-41b9-154fe8410236",
        "Version64": "36028797018963968",
    },
    {
        "Folder": "ModBrowser",
        "MD5": "981922692a4f3bbfc4dd5941221fc4f3",
        "Name": "ModBrowser",
        "PublishHandle": "0",
        "UUID": "ee5a55ff-eb38-0b27-c5b0-f358dc306d34",
        "Version64": "36028797018963968",
    },
    {
        "Folder": "PhotoMode",
        "MD5": "045fe21b32b1c766a0a09193aa9d1215",
        "Name": "PhotoMode",
        "PublishHandle": "0",
        "UUID": "55ef175c-59e3-b44b-3fb2-8f86acc5d550",
        "Version64": "36028797018963968",
    },
    {
        "Folder": "CrossplayUI",
        "MD5": "d41d8cd98f00b204e9800998ecf8427e",
        "Name": "CrossplayUI",
        "PublishHandle": "0",
        "UUID": "e1ce736b-52e6-e713-e9e7-e6abbb15a198",
        "Version64": "36028797018963968",
    },
]

CORE_SYSTEM_UUIDS = {m["UUID"].lower() for m in CORE_SYSTEM_MODULES} | {GUSTAV_DEV["UUID"].lower()}
CORE_SYSTEM_NAMES = {m["Name"].lower() for m in CORE_SYSTEM_MODULES} | CORE_GUSTAV_NAMES


def detect_modsettings_path() -> Path | None:
    """Detect modsettings.lsx path across WSL, native Linux, and Windows."""
    env_override = get_env_var("BG3_MODSETTINGS_PATH")
    if env_override:
        p = Path(env_override)
        if p.exists() or p.parent.exists():
            return p

    for appdata in detect_bg3_appdata_dirs():
        target = appdata / "PlayerProfiles/Public/modsettings.lsx"
        if target.exists() or target.parent.is_dir():
            return target

    return None


def get_appdata_mods_dir(modsettings_path: Path | None = None) -> Path | None:
    """Detect AppData/Local/Larian Studios/Baldur's Gate 3/Mods directory."""
    if modsettings_path and (modsettings_path.is_file() or modsettings_path.parent.is_dir()):
        try:
            candidate = modsettings_path.resolve().parents[2] / "Mods"
            if candidate.is_dir() or candidate.parent.is_dir():
                return candidate
        except Exception:
            pass

    for appdata in detect_bg3_appdata_dirs():
        p = appdata / "Mods"
        if p.is_dir() or p.parent.is_dir():
            return p

    return None


def create_default_modsettings(path: Path) -> None:
    """Generate a clean Patch 8 (Build 700) skeleton modsettings.lsx with all core system modules and ModOrder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    module_nodes = []
    for mod in CORE_SYSTEM_MODULES:
        module_nodes.append(f"""                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="{mod['Folder']}"/>
                            <attribute id="MD5" type="LSString" value="{mod['MD5']}"/>
                            <attribute id="Name" type="LSString" value="{mod['Name']}"/>
                            <attribute id="PublishHandle" type="uint64" value="{mod['PublishHandle']}"/>
                            <attribute id="UUID" type="guid" value="{mod['UUID']}"/>
                            <attribute id="Version64" type="int64" value="{mod['Version64']}"/>
                        </node>""")
    mods_xml = "\n".join(module_nodes)
    base_uuid = CORE_SYSTEM_MODULES[0]["UUID"]
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="ModuleSettings">
        <node id="root">
            <children>
                <node id="ModOrder">
                    <children>
                        <node id="Module">
                            <attribute id="UUID" type="FixedString" value="{base_uuid}"/>
                        </node>
                    </children>
                </node>
                <node id="Mods">
                    <children>
{mods_xml}
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>
"""
    path.write_text(xml_content, encoding="utf-8")


def save_modsettings(path: Path, tree: Any) -> None:
    """Save modsettings.lsx with clean 4-space indentation and standard Larian XML declaration."""
    backup_file(path)
    if hasattr(ET, "indent"):
        ET.indent(tree, space="    ")
    out = io.BytesIO()
    tree.write(out, encoding="utf-8", xml_declaration=True)
    raw = out.getvalue()
    if raw.startswith(b"<?xml"):
        header_end = raw.find(b"?>")
        if header_end != -1:
            raw = b'<?xml version="1.0" encoding="UTF-8"?>' + raw[header_end + 2:]
    path.write_bytes(raw.rstrip() + b"\n")


def parse_modsettings(path: Path) -> dict:
    if not path.is_file():
        return {"order": [], "mods": {}}

    tree = ET.parse(path)
    root = tree.getroot()

    order = []
    for mod_node in root.findall(".//node[@id='ModOrder']/children/node[@id='Module']"):
        uuid_attr = mod_node.find("attribute[@id='UUID']")
        if uuid_attr is not None:
            val = uuid_attr.get("value", "").strip()
            if val:
                order.append(val)

    mods = {}
    for desc in root.findall(".//node[@id='Mods']/children/node[@id='ModuleShortDesc']"):
        m_info = {}
        for attr in desc.findall("attribute"):
            aid = attr.get("id")
            val = attr.get("value", "")
            m_info[aid] = val
        if "UUID" in m_info:
            mods[m_info["UUID"]] = m_info

    # If ModOrder is empty (modern BG3 Patch 7+ often relies solely on Mods/ModuleShortDesc order),
    # populate order from Mods node sequence.
    if not order and mods:
        order = list(mods.keys())

    return {"order": order, "mods": mods}


def _extract_dependencies_from_xml_text(content: str) -> list[dict]:
    """Extract list of dependency module metadata dicts from meta.lsx XML text."""
    deps = []
    try:
        root = ET.fromstring(content)
        for node in root.iter("node"):
            if node.get("id") == "Dependencies":
                for sub in node.iter("node"):
                    if sub.get("id") == "ModuleShortDesc":
                        attrs = {a.get("id"): a.get("value", "") for a in sub.findall("attribute")}
                        u_str = attrs.get("UUID", "")
                        n_str = attrs.get("Name", "")
                        f_str = attrs.get("Folder", "")
                        if not u_str:
                            continue
                        if u_str == GUSTAV_DEV["UUID"] or n_str.lower() in CORE_GUSTAV_NAMES or f_str.lower() in CORE_GUSTAV_NAMES:
                            continue
                        deps.append({
                            "Folder": f_str,
                            "MD5": attrs.get("MD5", ""),
                            "Name": n_str,
                            "PublishHandle": attrs.get("PublishHandle", "0"),
                            "UUID": u_str,
                            "Version64": attrs.get("Version64", "36028797018963968"),
                        })
    except Exception:
        pass
    return deps


def _extract_meta_from_xml_text(content: str, fallback_name: str) -> dict | None:
    mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
    target = mod_info.group(1) if mod_info else content

    name = re.search(r'<attribute\s+id="Name"\s+type="[^"]*"\s+value="([^"]*)"', target)
    folder = re.search(r'<attribute\s+id="Folder"\s+type="[^"]*"\s+value="([^"]*)"', target)
    uuid_val = re.search(r'<attribute\s+id="UUID"\s+type="(?:FixedString|guid|LSString)"\s+value="([^"]*)"', target)
    v64 = re.search(r'<attribute\s+id="Version64"\s+type="int64"\s+value="(\d+)"', target)
    md5 = re.search(r'<attribute\s+id="MD5"\s+type="[^"]*"\s+value="([^"]*)"', target)
    handle = re.search(r'<attribute\s+id="PublishHandle"\s+type="[^"]*"\s+value="([^"]*)"', target)

    if uuid_val:
        return {
            "Dependencies": _extract_dependencies_from_xml_text(content),
            "Folder": folder.group(1) if folder else fallback_name,
            "MD5": md5.group(1) if md5 else "",
            "Name": name.group(1) if name else fallback_name,
            "PublishHandle": handle.group(1) if handle else "0",
            "UUID": uuid_val.group(1),
            "Version64": v64.group(1) if v64 else "36028797018963968",
        }
    return None


def get_mod_metadata_from_workspace(mod_name_or_uuid: str) -> dict | None:
    """Find mod in my_mods/, mods/, or AppData/.../Mods/*.pak and extract metadata for modsettings injection."""
    query_norm = normalize_mod_key(mod_name_or_uuid)
    query_raw = mod_name_or_uuid.strip().lower()

    my_mods_dir = Path(os.environ.get("BG3_MODS_DIR", MY_MODS_DIR))
    mods_dir = Path(os.environ.get("BG3_LIBRARY_DIR", MODS_DIR))

    # 1. Direct UUID lookup across all meta files if query looks like a UUID
    if "-" in query_raw and len(query_raw) >= 32:
        for base_dir in (my_mods_dir, mods_dir):
            if not base_dir.is_dir():
                continue
            for d in sorted(base_dir.iterdir()):
                if not d.is_dir():
                    continue
                for mf in find_mod_meta_files(d):
                    try:
                        parsed = _extract_meta_from_xml_text(mf.read_text(encoding="utf-8", errors="ignore"), d.name)
                        if parsed and parsed.get("UUID", "").lower() == query_raw:
                            return parsed
                    except Exception:
                        pass

    # 2. Pass 1: Exact directory name match
    for base_dir in (my_mods_dir, mods_dir):
        if not base_dir.is_dir():
            continue
        for d in sorted(base_dir.iterdir()):
            if not d.is_dir():
                continue
            d_norm = normalize_mod_key(d.name)
            if query_norm == d_norm:
                meta_files = find_mod_meta_files(d)
                for mf in meta_files:
                    try:
                        parsed = _extract_meta_from_xml_text(mf.read_text(encoding="utf-8", errors="ignore"), d.name)
                        if parsed:
                            return parsed
                    except Exception:
                        pass

    # 3. Pass 2: Substring directory name match
    for base_dir in (my_mods_dir, mods_dir):
        if not base_dir.is_dir():
            continue
        for d in sorted(base_dir.iterdir()):
            if not d.is_dir():
                continue
            d_norm = normalize_mod_key(d.name)
            if query_norm in d_norm or query_raw in d.name.lower():
                meta_files = find_mod_meta_files(d)
                for mf in meta_files:
                    try:
                        parsed = _extract_meta_from_xml_text(mf.read_text(encoding="utf-8", errors="ignore"), d.name)
                        if parsed:
                            return parsed
                    except Exception:
                        pass

    # 4. Search AppData/.../Mods/*.pak (exact stem first, then substring)
    for appdata in detect_bg3_appdata_dirs():
        pak_dir = appdata / "Mods"
        if not pak_dir.is_dir():
            continue
        for pak_file in sorted(pak_dir.glob("*.pak")):
            p_norm = normalize_mod_key(pak_file.stem)
            if query_norm == p_norm or query_raw == pak_file.stem.lower():
                try:
                    archive = LspkArchive(pak_file.read_bytes())
                    for entry in archive.files:
                        if entry["name"].replace("\\", "/").lower().endswith("meta.lsx"):
                            xml_txt = archive.extract_file(entry).decode("utf-8", errors="ignore")
                            parsed = _extract_meta_from_xml_text(xml_txt, pak_file.stem)
                            if parsed:
                                return parsed
                except Exception:
                    pass
        for pak_file in sorted(pak_dir.glob("*.pak")):
            if query_norm in normalize_mod_key(pak_file.stem) or query_raw in pak_file.stem.lower():
                try:
                    archive = LspkArchive(pak_file.read_bytes())
                    for entry in archive.files:
                        if entry["name"].replace("\\", "/").lower().endswith("meta.lsx"):
                            xml_txt = archive.extract_file(entry).decode("utf-8", errors="ignore")
                            parsed = _extract_meta_from_xml_text(xml_txt, pak_file.stem)
                            if parsed:
                                return parsed
                except Exception:
                    pass

    return None


def resolve_all_dependencies(
    mod_meta: dict, visited: set[str] | None = None
) -> tuple[list[dict], list[dict]]:
    """Recursively resolve declared dependencies for a mod.

    Returns:
        (resolved_dependencies_in_topological_order, missing_dependencies)
    """
    if visited is None:
        visited = set()
    resolved: list[dict] = []
    missing: list[dict] = []

    cand_uuid = mod_meta.get("UUID")
    if cand_uuid:
        visited.add(cand_uuid)

    for dep in mod_meta.get("Dependencies", []):
        dep_uuid = dep.get("UUID")
        if not dep_uuid or dep_uuid in visited:
            continue
        visited.add(dep_uuid)

        # Lookup in workspace or AppData Mods (UUID first, then Name, then Folder)
        installed = (
            get_mod_metadata_from_workspace(dep_uuid)
            or get_mod_metadata_from_workspace(dep.get("Name", ""))
            or get_mod_metadata_from_workspace(dep.get("Folder", ""))
        )
        if not installed:
            try:
                from .mod_resolver import resolve_dependency_metadata
                resolved_info = resolve_dependency_metadata(dep_uuid or dep.get("Name", ""), auto_document=False)
                if resolved_info and resolved_info.get("UUID"):
                    installed = resolved_info
            except Exception:
                pass
        if installed:
            actual_meta = installed
            sub_resolved, sub_missing = resolve_all_dependencies(actual_meta, visited)
            resolved.extend(sub_resolved)
            missing.extend(sub_missing)
            resolved.append(actual_meta)
        else:
            missing.append(dep)
            resolved.append(dep)

    return resolved, missing


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


def backup_file(path: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".lsx.{ts}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def _ensure_base_module(root: ET.Element, mods_children: ET.Element, mod_order_children: ET.Element | None = None) -> bool:
    """Ensure base game and Patch 8 core system modules are present at the beginning of Mods."""
    modified = False

    # Map existing ModuleShortDesc nodes by UUID
    existing_by_uuid: dict[str, ET.Element] = {}
    for desc_node in list(mods_children.findall("node[@id='ModuleShortDesc']")):
        u_attr = desc_node.find("attribute[@id='UUID']")
        if u_attr is not None:
            val = u_attr.get("value", "").lower().strip()
            if val:
                existing_by_uuid[val] = desc_node

    # If file is legacy Patch 7 (GustavDev present without GustavX), keep GustavDev at index 0
    is_legacy_p7 = (
        GUSTAV_DEV["UUID"].lower() in existing_by_uuid
        and CORE_SYSTEM_MODULES[0]["UUID"].lower() not in existing_by_uuid
    )

    if is_legacy_p7:
        gustav_node = existing_by_uuid[GUSTAV_DEV["UUID"].lower()]
        all_descs = mods_children.findall("node[@id='ModuleShortDesc']")
        if all_descs and all_descs[0] != gustav_node:
            mods_children.remove(gustav_node)
            mods_children.insert(0, gustav_node)
            modified = True
    else:
        # Patch 8: ensure each core system module is present in canonical order
        for idx, mod in enumerate(CORE_SYSTEM_MODULES):
            u_key = mod["UUID"].lower()
            if u_key in existing_by_uuid:
                node = existing_by_uuid[u_key]
                all_descs = mods_children.findall("node[@id='ModuleShortDesc']")
                curr_idx = all_descs.index(node) if node in all_descs else -1
                if curr_idx != idx and curr_idx > idx:
                    mods_children.remove(node)
                    mods_children.insert(idx, node)
                    modified = True
            else:
                node = ET.Element("node", id="ModuleShortDesc")
                ET.SubElement(node, "attribute", id="Folder", type="LSString", value=mod["Folder"])
                ET.SubElement(node, "attribute", id="MD5", type="LSString", value=mod["MD5"])
                ET.SubElement(node, "attribute", id="Name", type="LSString", value=mod["Name"])
                ET.SubElement(node, "attribute", id="PublishHandle", type="uint64", value=str(mod["PublishHandle"]))
                ET.SubElement(node, "attribute", id="UUID", type="guid", value=mod["UUID"])
                ET.SubElement(node, "attribute", id="Version64", type="int64", value=str(mod["Version64"]))
                mods_children.insert(idx, node)
                existing_by_uuid[u_key] = node
                modified = True

    # Check mod_order_children only if ModOrder exists in file (legacy compatibility)
    if mod_order_children is not None:
        order_modules = mod_order_children.findall("node[@id='Module']")
        base_uuid = GUSTAV_DEV["UUID"] if is_legacy_p7 else CORE_SYSTEM_MODULES[0]["UUID"]
        base_order_node = None
        for m in order_modules:
            u_attr = m.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value", "").lower() == base_uuid.lower():
                base_order_node = m
                break

        if base_order_node is None:
            base_order_node = ET.Element("node", id="Module")
            ET.SubElement(base_order_node, "attribute", id="UUID", type="FixedString", value=base_uuid)
            mod_order_children.insert(0, base_order_node)
            modified = True
        else:
            if order_modules and order_modules[0] != base_order_node:
                mod_order_children.remove(base_order_node)
                mod_order_children.insert(0, base_order_node)
                modified = True

    return modified


def enable_mod(path: Path, mod_meta: dict | str, order_index: int | None = None, dry_run: bool = False) -> tuple[bool, str]:
    """
    Enables or reorders a mod in modsettings.lsx.
    Returns (changed, action_status) where action_status is 'enabled', 'reordered', or 'already_active'.
    """
    if isinstance(mod_meta, str):
        meta_lookup = get_mod_metadata_from_workspace(mod_meta)
        if not meta_lookup:
            return False, f"Mod metadata not found for {mod_meta}"
        mod_meta = meta_lookup

    if not path.is_file():
        if not dry_run:
            create_default_modsettings(path)
        else:
            return True, "enabled"

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

    base_modified = _ensure_base_module(root, mods_children, mod_order_children)

    target_uuid = mod_meta["UUID"]

    # Check if already present in ModOrder (if present)
    existing_order_node = None
    if mod_order_children is not None:
        for mod_node in mod_order_children.findall("node[@id='Module']"):
            u_attr = mod_node.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value", "").lower() == target_uuid.lower():
                existing_order_node = mod_node
                break

    existing_desc_node = None
    for desc_node in mods_children.findall("node[@id='ModuleShortDesc']"):
        u_attr = desc_node.find("attribute[@id='UUID']")
        if u_attr is not None and u_attr.get("value", "").lower() == target_uuid.lower():
            existing_desc_node = desc_node
            break

    if existing_desc_node is not None and order_index is None:
        if base_modified and not dry_run:
            save_modsettings(path, tree)
            return True, "enabled"
        return False, "already_active"

    action_status = "reordered" if existing_desc_node is not None else "enabled"

    if not dry_run:
        if existing_order_node is not None and mod_order_children is not None:
            mod_order_children.remove(existing_order_node)
        if existing_desc_node is not None:
            mods_children.remove(existing_desc_node)

        if mod_order_children is not None:
            new_order_node = ET.Element("node", id="Module")
            ET.SubElement(new_order_node, "attribute", id="UUID", type="FixedString", value=target_uuid)
            if order_index is not None:
                safe_idx = max(1, order_index)
                order_len = len(mod_order_children.findall("node[@id='Module']"))
                mod_order_children.insert(min(safe_idx, order_len), new_order_node)
            else:
                mod_order_children.append(new_order_node)

        new_desc_node = ET.Element("node", id="ModuleShortDesc")
        ET.SubElement(new_desc_node, "attribute", id="Folder", type="LSString", value=mod_meta["Folder"])
        ET.SubElement(new_desc_node, "attribute", id="MD5", type="LSString", value=mod_meta.get("MD5", ""))
        ET.SubElement(new_desc_node, "attribute", id="Name", type="LSString", value=mod_meta["Name"])
        ET.SubElement(new_desc_node, "attribute", id="PublishHandle", type="uint64", value=str(mod_meta.get("PublishHandle", "0")))
        ET.SubElement(new_desc_node, "attribute", id="UUID", type="guid", value=target_uuid)
        ET.SubElement(new_desc_node, "attribute", id="Version64", type="int64", value=str(mod_meta.get("Version64", "36028797018963968")))

        if order_index is not None:
            # Never insert ahead of core system modules
            core_count = 0
            for d in mods_children.findall("node[@id='ModuleShortDesc']"):
                u_node = d.find("attribute[@id='UUID']")
                if u_node is not None and (u_node.get("value") or "").lower() in CORE_SYSTEM_UUIDS:
                    core_count += 1
            if order_index < core_count:
                safe_idx = core_count + max(0, order_index - 1)
            else:
                safe_idx = order_index
            desc_len = len(mods_children.findall("node[@id='ModuleShortDesc']"))
            mods_children.insert(min(safe_idx, desc_len), new_desc_node)
        else:
            mods_children.append(new_desc_node)

        save_modsettings(path, tree)

    return True, action_status


def disable_mod(path: Path, mod_name: str, dry_run: bool = False) -> bool:
    if not path.is_file():
        return False

    tree = ET.parse(path)
    root = tree.getroot()

    mod_order_children = root.find(".//node[@id='ModOrder']/children")
    mods_children = root.find(".//node[@id='Mods']/children")

    if mods_children is None:
        return False

    query_norm = normalize_mod_key(mod_name)
    target_uuid = None
    target_name = ""
    for desc in mods_children.findall("node[@id='ModuleShortDesc']"):
        name_attr = desc.find("attribute[@id='Name']")
        folder_attr = desc.find("attribute[@id='Folder']")
        uuid_attr = desc.find("attribute[@id='UUID']")
        if uuid_attr is not None:
            n_val = name_attr.get("value", "") if name_attr is not None else ""
            f_val = folder_attr.get("value", "") if folder_attr is not None else ""
            u_val = uuid_attr.get("value", "")
            if (
                mod_name.lower() in n_val.lower()
                or query_norm in normalize_mod_key(n_val)
                or query_norm in normalize_mod_key(f_val)
                or mod_name.lower() == u_val.lower()
            ):
                target_uuid = u_val
                target_name = n_val or f_val
                break

    if not target_uuid:
        return False

    if target_uuid.lower() in CORE_SYSTEM_UUIDS or target_name.lower() in CORE_SYSTEM_NAMES:
        raise ValueError(f"Cannot disable core game or system module {target_name or target_uuid}.")

    if not dry_run:
        if mod_order_children is not None:
            for m_node in list(mod_order_children.findall("node[@id='Module']")):
                u_attr = m_node.find("attribute[@id='UUID']")
                if u_attr is not None and u_attr.get("value", "").lower() == target_uuid.lower():
                    mod_order_children.remove(m_node)

        for desc in list(mods_children.findall("node[@id='ModuleShortDesc']")):
            u_attr = desc.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value", "").lower() == target_uuid.lower():
                mods_children.remove(desc)

        save_modsettings(path, tree)

    return True


def validate_load_order(parsed: dict) -> list[str]:
    issues = []
    order = parsed["order"]
    mods = parsed["mods"]

    if not order:
        issues.append("Load order is empty.")
        return issues

    first_uuid = order[0]
    first_mod = mods.get(first_uuid, {})
    first_name = (first_mod.get("Name") or first_mod.get("Folder") or "").lower()
    if (
        first_uuid != GUSTAV_DEV["UUID"]
        and first_name not in CORE_GUSTAV_NAMES
        and first_uuid.lower() != CORE_SYSTEM_MODULES[0]["UUID"].lower()
    ):
        issues.append(
            f"Base game module (GustavDev / GustavX) must be at load order index 0 (found '{first_mod.get('Name', first_uuid)}')."
        )

    # In Patch 8 (GustavX present), verify all core system modules exist
    has_gustav_x = any(
        m.get("Name", "").lower() == "gustavx" or u.lower() == CORE_SYSTEM_MODULES[0]["UUID"].lower()
        for u, m in mods.items()
    )
    if has_gustav_x:
        missing_core = [
            m["Name"] for m in CORE_SYSTEM_MODULES
            if m["UUID"].lower() not in {u.lower() for u in mods.keys()}
        ]
        if missing_core:
            issues.append(f"Missing core system modules required by Patch 8: {', '.join(missing_core)}")

    for u in order:
        if u not in mods:
            issues.append(f"UUID '{u}' is in ModOrder but missing from Mods description list.")

    # Check UnlockLevelCurve ordering if present
    ulc_uuid = "a2ffd0e4-c407-8642-2611-c934ea0b0a77"
    if ulc_uuid in order:
        ulc_idx = order.index(ulc_uuid)
        for idx, u in enumerate(order):
            mod_entry = mods.get(u, {})
            m_name = (mod_entry.get("Name") or mod_entry.get("Folder") or "").lower()
            if idx < ulc_idx and u != GUSTAV_DEV["UUID"] and m_name not in CORE_GUSTAV_NAMES and u.lower() not in CORE_SYSTEM_UUIDS:
                issues.append(f"Warning: Mod '{mod_entry.get('Name', u)}' is loaded before UnlockLevelCurve.")

    return issues


def get_pak_module_info(pak_path: Path) -> dict | None:
    """Extract UUID, Name, Folder, Version64 from meta.lsx inside a .pak archive."""
    try:
        archive = LspkArchive(pak_path.read_bytes())
        for entry in archive.files:
            if entry["name"].replace("\\", "/").lower().endswith("meta.lsx"):
                xml_txt = archive.extract_file(entry).decode("utf-8", errors="ignore")
                return _extract_meta_from_xml_text(xml_txt, pak_path.stem)
    except Exception:
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
        results.append({
            "action": "removed_bak",
            "file": bak_file.name,
            "path": str(bak_file),
            "destination": str(dest),
        })
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

        def score_entry(item: tuple[Path, dict]) -> tuple[int, int, float]:
            path, meta = item
            stem = path.stem.lower()
            u_clean = uuid_key.replace("-", "")
            is_canonical = (
                f"_{uuid_key}" in stem
                or f"_{u_clean}" in stem
                or (meta.get("Folder", "").lower() in stem and uuid_key in stem)
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

        for loser_path, loser_meta in losers:
            dest = duplicates_dir / loser_path.name
            results.append({
                "action": "deduplicated",
                "uuid": uuid_key,
                "winner": winner_path.name,
                "redundant": loser_path.name,
                "destination": str(dest),
            })
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
        except Exception:
            manifest_data = {}

    for pak_path in sorted(mods_dir.glob("*.pak")):
        info = get_pak_module_info(pak_path)
        u_val = info.get("UUID", "").lower().strip() if info else ""
        if not u_val:
            m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", pak_path.name, re.IGNORECASE)
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
    Restores all quarantined .pak archives from Mods_Disabled/ back into mods_dir.
    """
    quarantine_dir = quarantine_base or mods_dir.parent / "Mods_Disabled"
    if not quarantine_dir.is_dir():
        return []

    restored = []
    manifest_path = quarantine_dir / "quarantine_manifest.json"

    for pak_path in sorted(quarantine_dir.glob("*.pak")):
        if not pak_path.is_file():
            continue
        dest = mods_dir / pak_path.name
        record = {
            "filename": pak_path.name,
            "source": str(pak_path),
            "destination": str(dest),
        }
        restored.append(record)
        if not dry_run:
            mods_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.unlink()
            shutil.move(str(pak_path), str(dest))

    if not dry_run and manifest_path.is_file():
        try:
            manifest_path.unlink()
        except Exception:
            pass

    return restored


def topological_sort_mods(
    active_mods: dict[str, dict[str, Any]],
    dependency_graph: dict[str, list[str]],
) -> list[str]:
    """
    Kahn's algorithm for topological sorting of active mods by dependency constraints.
    Returns ordered list of UUIDs, with core system modules pinned first.
    """
    core_uuids: list[str] = []
    custom_uuids: list[str] = []

    for u in active_mods:
        u_norm = u.lower()
        if u_norm in CORE_SYSTEM_UUIDS:
            core_uuids.append(u)
        else:
            custom_uuids.append(u)

    in_degree: dict[str, int] = {u: 0 for u in custom_uuids}
    adj: dict[str, list[str]] = {u: [] for u in custom_uuids}
    uuid_map = {u.lower(): u for u in custom_uuids}

    for u in custom_uuids:
        deps = dependency_graph.get(u, []) or dependency_graph.get(u.lower(), [])
        for dep in deps:
            dep_norm = dep.lower()
            if dep_norm in uuid_map:
                dep_actual = uuid_map[dep_norm]
                adj[dep_actual].append(u)
                in_degree[u] += 1

    def priority_key(u: str) -> tuple[int, str]:
        name = (active_mods.get(u, {}).get("Name") or "").lower()
        if "communitylibrary" in name:
            return (0, name)
        if "compatibilityframework" in name:
            return (1, name)
        return (2, name)

    queue = [u for u, deg in in_degree.items() if deg == 0]
    queue.sort(key=priority_key)

    sorted_custom: list[str] = []
    while queue:
        curr = queue.pop(0)
        sorted_custom.append(curr)
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                queue.sort(key=priority_key)

    if len(sorted_custom) < len(custom_uuids):
        remaining = [u for u in custom_uuids if u not in sorted_custom]
        sorted_custom.extend(remaining)

    return core_uuids + sorted_custom


def auto_sort_load_order(path: Path, dry_run: bool = False) -> tuple[bool, list[str], dict[str, Any]]:
    """Sorts active mods in modsettings.lsx according to dependencies using topological sort."""
    if not path.is_file():
        return False, [], {"error": "modsettings.lsx not found"}

    parsed = parse_modsettings(path)
    active_mods = parsed.get("mods", {})
    if not active_mods:
        return False, [], {"error": "No active mods in modsettings.lsx"}

    dep_graph: dict[str, list[str]] = {}
    for u, m in active_mods.items():
        dep_graph[u] = []
        meta = (
            get_mod_metadata_from_workspace(u)
            or get_mod_metadata_from_workspace(m.get("Name", ""))
            or get_mod_metadata_from_workspace(m.get("Folder", ""))
            or {}
        )
        if not m.get("Name") and meta.get("Name"):
            m["Name"] = meta["Name"]
        raw_deps = meta.get("Dependencies") or m.get("Dependencies") or []
        for d in raw_deps:
            if isinstance(d, dict) and "UUID" in d:
                dep_uuid = str(d["UUID"]).strip()
                if dep_uuid and dep_uuid.lower() != u.lower():
                    dep_graph[u].append(dep_uuid)

    sorted_order = topological_sort_mods(active_mods, dep_graph)

    if not dry_run:
        tree = ET.parse(path)
        root = tree.getroot()
        mods_children = root.find(".//node[@id='Mods']/children")
        if mods_children is not None:
            descs_by_uuid: dict[str, ET.Element] = {}
            for d in list(mods_children.findall("node[@id='ModuleShortDesc']")):
                u_attr = d.find("attribute[@id='UUID']")
                if u_attr is not None:
                    descs_by_uuid[u_attr.get("value", "").lower()] = d
                    mods_children.remove(d)

            for u in sorted_order:
                node = descs_by_uuid.get(u.lower())
                if node is not None:
                    mods_children.append(node)

        mod_order_children = root.find(".//node[@id='ModOrder']/children")
        if mod_order_children is not None:
            modules_by_uuid: dict[str, ET.Element] = {}
            for m_node in list(mod_order_children.findall("node[@id='Module']")):
                u_attr = m_node.find("attribute[@id='UUID']")
                if u_attr is not None:
                    modules_by_uuid[u_attr.get("value", "").lower()] = m_node
                    mod_order_children.remove(m_node)

            for u in sorted_order:
                matched_node = modules_by_uuid.get(u.lower())
                if matched_node is not None:
                    mod_order_children.append(matched_node)

        save_modsettings(path, tree)

    return True, sorted_order, {"total_sorted": len(sorted_order), "dry_run": dry_run}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect, activate, reorder, and validate Baldur's Gate 3 modsettings.lsx load order."
    )
    parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    parser.add_argument("--list", action="store_true", help="Display active mod load order")
    parser.add_argument("--enable", "--activate", dest="enable", help="Enable a mod by name/slug from my_mods/, mods/, or AppData Mods")
    parser.add_argument("--order", type=int, help="Target load order index (>= 1) when enabling or reordering a mod")
    parser.add_argument("--disable", help="Disable a mod by name/UUID from active load order")
    parser.add_argument("--with-deps", dest="with_deps", action="store_true", default=True, help="Automatically enable declared dependencies from meta.lsx (default: True)")
    parser.add_argument("--no-deps", dest="with_deps", action="store_false", help="Do not automatically enable dependencies")
    parser.add_argument("--test-dep", action="append", default=[], dest="test_deps", help="Temporary test dependency name, slug, or UUID to activate ahead of the mod")
    parser.add_argument("--isolate", "--clean", dest="isolate", action="store_true", help="Clean-room isolation: disable all other mods except base game and dependencies in modsettings.lsx")
    parser.add_argument("--quarantine", action="store_true", help="Physically quarantine unrelated .pak files to Mods_Disabled/ (Warning: triggers mod.io auto-download for subscribed mods)")
    parser.add_argument("--restore", action="store_true", help="Restore quarantined mods from Mods_Disabled/ back to active Mods directory")
    parser.add_argument("--dedup", "--deduplicate", dest="dedup", action="store_true", help="Deduplicate installed .pak files in AppData Mods")
    parser.add_argument("--validate", action="store_true", help="Validate current load order rules")
    parser.add_argument("--auto-sort", "--sort", dest="auto_sort", action="store_true", help="Topologically auto-sort active mods based on dependencies")
    parser.add_argument("--create-default", action="store_true", help="Create default modsettings.lsx if missing")
    parser.add_argument("--dry-run", action="store_true", help="Preview modifications without writing to disk")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    modsettings_path = Path(args.path) if args.path else detect_modsettings_path()

    if not modsettings_path:
        msg = "Could not locate modsettings.lsx. Specify path with --path."
        if args.json:
            print(json.dumps({"error": msg, "success": False}, indent=2))
        else:
            print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)
        sys.exit(1)

    if args.create_default:
        created = False
        if not modsettings_path.is_file():
            create_default_modsettings(modsettings_path)
            created = True
        if args.json:
            print(json.dumps({"status": "created" if created else "already_exists", "path": str(modsettings_path)}, indent=2))
        else:
            if created:
                print(f"✓ Created default modsettings.lsx at: {modsettings_path}")
            else:
                print(f"modsettings.lsx already exists at: {modsettings_path}")
        sys.exit(0)

    if not modsettings_path.is_file() and not args.enable:
        if args.json:
            print(json.dumps({"status": "missing_modsettings", "path": str(modsettings_path), "order": [], "mods": {}}, indent=2))
        else:
            print(f"{YELLOW}Notice: modsettings.lsx does not exist yet at {modsettings_path}.{RESET}")
            print("Run with --create-default to initialize, or --enable <Mod> to generate with mod.")
        sys.exit(0)

    # Default to --list when --json is passed without an explicit action
    if args.json and not (args.list or args.enable or args.disable or args.validate or args.auto_sort):
        args.list = True

    action_result: dict[str, Any] = {}

    if args.auto_sort:
        success, sorted_order, meta_sort = auto_sort_load_order(modsettings_path, dry_run=args.dry_run)
        action_result["auto_sort"] = {
            "success": success,
            "sorted_order": sorted_order,
            **meta_sort,
        }
        if not args.json:
            verb = "[DRY-RUN] Would reorder" if args.dry_run else "Reordered"
            print(f"✓ {verb} {len(sorted_order)} active mod(s) via topological dependency sorting.")

    if args.restore:
        mods_dir = get_appdata_mods_dir(modsettings_path)
        if not mods_dir:
            msg = "Could not locate AppData Mods directory for restore."
            if args.json:
                print(json.dumps({"error": msg, "success": False}, indent=2))
            else:
                print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)
            sys.exit(1)
        restored = restore_quarantined_paks(mods_dir, dry_run=args.dry_run)
        action_result["restore"] = {
            "count": len(restored),
            "files": restored,
            "dry_run": args.dry_run,
        }
        if not args.json:
            verb = "[DRY-RUN] Would restore" if args.dry_run else "Restored"
            print(f"✓ {verb} {len(restored)} mod archive(s) from Mods_Disabled/ to Mods/.")
            for r in restored:
                print(f"  ↳ {r['filename']}")
        if not (args.enable or args.list or args.validate or args.disable):
            sys.exit(0)

    if args.dedup:
        mods_dir = get_appdata_mods_dir(modsettings_path)
        if not mods_dir:
            msg = "Could not locate AppData Mods directory for deduplication."
            if args.json:
                print(json.dumps({"error": msg, "success": False}, indent=2))
            else:
                print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)
            sys.exit(1)
        deduped = deduplicate_installed_paks(mods_dir, dry_run=args.dry_run)
        steam_cleaned = clean_steam_data_paks(dry_run=args.dry_run)
        action_result["deduplicate"] = {
            "count": len(deduped),
            "actions": deduped,
            "steam_cleaned": steam_cleaned,
            "dry_run": args.dry_run,
        }
        if not args.json:
            verb = "[DRY-RUN] Would deduplicate" if args.dry_run else "Deduplicated"
            print(f"✓ {verb} {len(deduped)} duplicate/backup file(s).")
            for d in deduped:
                if d.get("action") == "deduplicated":
                    print(f"  ↳ Kept '{d['winner']}', archived '{d['redundant']}'")
                elif d.get("action") == "removed_bak":
                    print(f"  ↳ Archived backup file '{d['file']}'")
            if steam_cleaned:
                print(f"✓ Cleaned {len(steam_cleaned)} duplicate .pak archive(s) from Steam Data/Mods.")
        if not (args.enable or args.list or args.validate or args.disable):
            sys.exit(0)

    if args.enable:
        mod_meta = get_mod_metadata_from_workspace(args.enable)
        if not mod_meta:
            msg = f"Mod '{args.enable}' not found in my_mods/, mods/, or AppData Mods."
            if args.json:
                print(json.dumps({"error": msg, "success": False}, indent=2))
            else:
                print(f"{RED}Error: {msg}{RESET}", file=sys.stderr)
            sys.exit(1)

        resolved_deps: list[dict] = []
        missing_deps: list[dict] = []
        if args.with_deps:
            resolved_deps, missing_deps = resolve_all_dependencies(mod_meta)

        # Collect test dependencies from CLI and .test_deps.json if mod is in my_mods/
        mod_dir = resolve_mod_dir(args.enable, prefer_my_mods=True)
        test_dep_queries = list(args.test_deps)
        if mod_dir and (mod_dir / ".test_deps.json").is_file():
            try:
                cfg = json.loads((mod_dir / ".test_deps.json").read_text(encoding="utf-8"))
                for td in cfg.get("test_dependencies", []):
                    if td not in test_dep_queries:
                        test_dep_queries.append(td)
            except Exception:
                pass

        resolved_test_deps: list[dict] = []
        for t_query in test_dep_queries:
            t_meta = get_mod_metadata_from_workspace(t_query)
            if not t_meta:
                try:
                    t_meta = resolve_dependency_metadata(t_query, auto_document=True)
                except Exception:
                    pass
            if t_meta and t_meta.get("UUID"):
                resolved_test_deps.append(t_meta)

        # Ensure .pak files exist in Steam Data/Mods and AppData Mods
        pak_sync_results = []
        if args.with_deps and not args.dry_run:
            all_deps = list(resolved_deps) + list(resolved_test_deps)
            pak_sync_results = ensure_dependency_paks(all_deps)

        isolated_count = 0
        if args.isolate:
            keep_uuids = {
                mod_meta["UUID"],
                *(d["UUID"] for d in resolved_deps),
                *(d["UUID"] for d in resolved_test_deps),
            }
            mods_dir = get_appdata_mods_dir(modsettings_path)
            clean_steam_results = clean_steam_data_paks(dry_run=args.dry_run)
            dedup_results = []
            quarantined_paks = []
            if mods_dir and mods_dir.is_dir():
                dedup_results = deduplicate_installed_paks(mods_dir, dry_run=args.dry_run)
                if getattr(args, "quarantine", False):
                    quarantined_paks = quarantine_unrelated_paks(mods_dir, keep_uuids, dry_run=args.dry_run)

            action_result["clean_steam_data"] = clean_steam_results
            action_result["deduplicate"] = dedup_results
            action_result["quarantined_paks"] = quarantined_paks

            isolated_count = isolate_load_order(modsettings_path, keep_uuids, dry_run=args.dry_run)
            action_result["isolated_count"] = isolated_count
            if not args.json:
                verb = "[DRY-RUN] Would isolate" if args.dry_run else "Isolated"
                print(f"✓ {verb} load order (disabled {isolated_count} mod entries in modsettings.lsx).")
                if clean_steam_results:
                    print(f"  ↳ Cleaned {len(clean_steam_results)} duplicate .pak archive(s) from Steam Data/Mods.")
                if dedup_results:
                    print(f"  ↳ Deduplicated {len(dedup_results)} conflicting/redundant .pak archive(s).")
                if quarantined_paks:
                    print(f"  ↳ Quarantined {len(quarantined_paks)} unrelated .pak archive(s) to Mods_Disabled/.")

        current_order_idx = 1
        dep_results = []
        for dep in resolved_deps:
            req_idx = current_order_idx if args.isolate else None
            dep_changed, dep_status = enable_mod(modsettings_path, dep, order_index=req_idx, dry_run=args.dry_run)
            current_order_idx += 1
            dep_results.append({
                "mod": dep.get("Name", dep["UUID"]),
                "uuid": dep["UUID"],
                "changed": dep_changed,
                "status": dep_status,
            })
            if not args.json and dep_changed:
                verb = "[DRY-RUN] Would enable dependency" if args.dry_run else "Enabled dependency"
                print(f"  ↳ {verb} '{dep.get('Name', dep['UUID'])}' ({dep['UUID']})")

        test_dep_results = []
        for tdep in resolved_test_deps:
            req_idx = current_order_idx if args.isolate else None
            tdep_changed, tdep_status = enable_mod(modsettings_path, tdep, order_index=req_idx, dry_run=args.dry_run)
            current_order_idx += 1
            test_dep_results.append({
                "mod": tdep.get("Name", tdep["UUID"]),
                "uuid": tdep["UUID"],
                "changed": tdep_changed,
                "status": tdep_status,
            })
            if not args.json and tdep_changed:
                verb = "[DRY-RUN] Would enable test dependency" if args.dry_run else "Enabled test dependency"
                print(f"  🧪 {verb} '{tdep.get('Name', tdep['UUID'])}' ({tdep['UUID']})")

        target_order = args.order if args.order is not None else (current_order_idx if args.isolate else None)
        changed, status_str = enable_mod(modsettings_path, mod_meta, order_index=target_order, dry_run=args.dry_run)
        action_result["enable"] = {
            "mod": mod_meta["Name"],
            "uuid": mod_meta["UUID"],
            "changed": changed,
            "status": status_str,
            "order_index": args.order,
            "dry_run": args.dry_run,
            "dependencies": dep_results,
            "test_dependencies": test_dep_results,
            "pak_sync": pak_sync_results,
            "missing_dependencies": missing_deps,
        }
        if not args.json:
            if changed:
                verb = "[DRY-RUN] Would enable/reorder" if args.dry_run else f"Successfully {status_str}"
                print(f"✓ {verb} '{mod_meta['Name']}' ({mod_meta['UUID']}) in load order at {modsettings_path}!")
            else:
                print(f"Mod '{mod_meta['Name']}' is already active in load order.")

            if missing_deps:
                print(f"{YELLOW}⚠ Warning: {len(missing_deps)} declared dependenc{'y' if len(missing_deps) == 1 else 'ies'} not found in workspace or AppData Mods:{RESET}")
                for md in missing_deps:
                    print(f"  • {md.get('Name', 'Unknown')} ({md.get('UUID', 'No UUID')})")

    if args.disable:
        try:
            changed = disable_mod(modsettings_path, args.disable, dry_run=args.dry_run)
            action_result["disable"] = {
                "mod": args.disable,
                "changed": changed,
                "dry_run": args.dry_run,
            }
            if not args.json:
                if changed:
                    action_desc = "[DRY-RUN] Would disable" if args.dry_run else "Successfully disabled"
                    print(f"✓ {action_desc} '{args.disable}' from load order at {modsettings_path}!")
                else:
                    print(f"Mod '{args.disable}' was not found in active load order.")
        except Exception as e:
            if args.json:
                print(json.dumps({"error": str(e), "success": False}, indent=2))
            else:
                print(f"{RED}Error: {e}{RESET}", file=sys.stderr)
            sys.exit(1)

    parsed = parse_modsettings(modsettings_path)

    if args.validate:
        issues = validate_load_order(parsed)
        action_result["validation"] = {
            "valid": len(issues) == 0,
            "active_count": len(parsed["order"]),
            "issues": issues,
        }
        if not args.json:
            if not issues:
                print(f"{GREEN}✓ Load order is valid ({len(parsed['order'])} mods active).{RESET}")
            else:
                print(f"{YELLOW}Load order issues detected:{RESET}")
                for issue in issues:
                    print(f"  • {issue}")

    if args.list and not args.json:
        print(f"\n{BOLD}{CYAN}=== Active Baldur's Gate 3 Load Order ==={RESET}")
        print(f"Location: {modsettings_path}\n")
        print(f"{'Idx':<4} | {'Mod Name':<28} | {'UUID':<38} | {'Version'}")
        print("-" * 85)
        for idx, u in enumerate(parsed["order"]):
            m = parsed["mods"].get(u, {})
            name = m.get("Name", "Unknown")
            v64 = m.get("Version64", "-")
            print(f"{idx:<4} | {name:<28} | {u:<38} | {v64}")
        print(f"\nTotal active mods: {len(parsed['order'])}\n")

    if args.json:
        payload = {
            "path": str(modsettings_path),
            "order": parsed["order"],
            "mods": parsed["mods"],
            **action_result,
        }
        print(json.dumps(payload, indent=2))
        if args.validate and action_result.get("validation", {}).get("issues"):
            sys.exit(1)
        sys.exit(0)

    if args.validate and action_result.get("validation", {}).get("issues"):
        sys.exit(1)

    if args.list or args.enable or args.disable or args.validate or args.auto_sort:
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
