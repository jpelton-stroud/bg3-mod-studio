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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib.env_paths import (
    MODS_DIR,
    MY_MODS_DIR,
    REPO_ROOT as WORKSPACE_ROOT,
    detect_bg3_appdata_dirs,
    detect_data_dir,
    get_env_var,
    normalize_mod_key,
    resolve_mod_dir,
)
from scripts.lib.larian_parsers import find_mod_meta_files
from scripts.lib.lspk import LspkArchive
from scripts.lib.mod_resolver import ensure_dependency_paks, resolve_dependency_metadata

from scripts.lib.cli_common import ConsoleColor, ExitCode

# Zero-dependency ANSI Terminal Colors honoring NO_COLOR
_color = ConsoleColor(stream=sys.stderr)
BOLD = "\033[1m" if _color.enabled else ""
GREEN = "\033[32m" if _color.enabled else ""
YELLOW = "\033[33m" if _color.enabled else ""
RED = "\033[31m" if _color.enabled else ""
CYAN = "\033[36m" if _color.enabled else ""
RESET = "\033[0m" if _color.enabled else ""

# Default GustavDev module entry
GUSTAV_DEV = {
    "Folder": "GustavDev",
    "MD5": "33c1655f7ae3559b579ff3b9d2c45413",
    "Name": "GustavDev",
    "PublishHandle": "0",
    "UUID": "28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8",
    "Version64": "145100393449790344",
}

CORE_GUSTAV_NAMES = {"gustavdev", "gustavx", "gustav"}


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


def create_default_modsettings(path: Path):
    """Generate a clean Patch 7+ skeleton modsettings.lsx with GustavDev."""
    path.parent.mkdir(parents=True, exist_ok=True)
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="ModuleSettings">
        <node id="root">
            <children>
                <node id="Mods">
                    <children>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="{GUSTAV_DEV['Folder']}"/>
                            <attribute id="MD5" type="LSString" value="{GUSTAV_DEV['MD5']}"/>
                            <attribute id="Name" type="LSString" value="{GUSTAV_DEV['Name']}"/>
                            <attribute id="PublishHandle" type="uint64" value="{GUSTAV_DEV['PublishHandle']}"/>
                            <attribute id="UUID" type="guid" value="{GUSTAV_DEV['UUID']}"/>
                            <attribute id="Version64" type="int64" value="{GUSTAV_DEV['Version64']}"/>
                        </node>
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>
"""
    path.write_text(xml_content, encoding="utf-8")


def save_modsettings(path: Path, tree: ET.ElementTree):
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
    """Disables all mods in modsettings.lsx except GustavDev/GustavX and those in keep_uuids."""
    if not path.is_file():
        return 0

    tree = ET.parse(path)
    root = tree.getroot()

    mod_order_children = root.find(".//node[@id='ModOrder']/children")
    mods_children = root.find(".//node[@id='Mods']/children")

    if mods_children is None:
        return 0

    removed_count = 0
    # Clean Mods
    for desc in list(mods_children.findall("node[@id='ModuleShortDesc']")):
        u_attr = desc.find("attribute[@id='UUID']")
        n_attr = desc.find("attribute[@id='Name']")
        f_attr = desc.find("attribute[@id='Folder']")
        u_val = u_attr.get("value", "") if u_attr is not None else ""
        n_val = (n_attr.get("value", "") if n_attr is not None else "").lower()
        f_val = (f_attr.get("value", "") if f_attr is not None else "").lower()

        if u_val == GUSTAV_DEV["UUID"] or n_val in CORE_GUSTAV_NAMES or f_val in CORE_GUSTAV_NAMES:
            continue
        if u_val not in keep_uuids:
            mods_children.remove(desc)
            removed_count += 1

    # Clean ModOrder
    if mod_order_children is not None:
        for m_node in list(mod_order_children.findall("node[@id='Module']")):
            u_attr = m_node.find("attribute[@id='UUID']")
            u_val = u_attr.get("value", "") if u_attr is not None else ""
            if u_val == GUSTAV_DEV["UUID"] or u_val in keep_uuids:
                continue
            mod_order_children.remove(m_node)

    if removed_count > 0 and not dry_run:
        save_modsettings(path, tree)

    return removed_count


def backup_file(path: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".lsx.{ts}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def _ensure_base_module(root: ET.Element, mods_children: ET.Element, mod_order_children: ET.Element | None = None) -> bool:
    """Ensure base game module (GustavDev / GustavX) is present at index 0 in Mods (and ModOrder if present)."""
    modified = False
    base_module_uuid = None
    for desc_node in mods_children.findall("node[@id='ModuleShortDesc']"):
        u_attr = desc_node.find("attribute[@id='UUID']")
        n_attr = desc_node.find("attribute[@id='Name']")
        f_attr = desc_node.find("attribute[@id='Folder']")
        u_val = u_attr.get("value", "") if u_attr is not None else ""
        n_val = (n_attr.get("value", "") if n_attr is not None else "").lower()
        f_val = (f_attr.get("value", "") if f_attr is not None else "").lower()
        if u_val == GUSTAV_DEV["UUID"] or n_val in CORE_GUSTAV_NAMES or f_val in CORE_GUSTAV_NAMES:
            base_module_uuid = u_val
            break

    if not base_module_uuid:
        base_module_uuid = GUSTAV_DEV["UUID"]
        gustav_desc = ET.Element("node", id="ModuleShortDesc")
        ET.SubElement(gustav_desc, "attribute", id="Folder", type="LSString", value=GUSTAV_DEV["Folder"])
        ET.SubElement(gustav_desc, "attribute", id="MD5", type="LSString", value=GUSTAV_DEV["MD5"])
        ET.SubElement(gustav_desc, "attribute", id="Name", type="LSString", value=GUSTAV_DEV["Name"])
        ET.SubElement(gustav_desc, "attribute", id="PublishHandle", type="uint64", value=str(GUSTAV_DEV["PublishHandle"]))
        ET.SubElement(gustav_desc, "attribute", id="UUID", type="guid", value=GUSTAV_DEV["UUID"])
        ET.SubElement(gustav_desc, "attribute", id="Version64", type="int64", value=str(GUSTAV_DEV["Version64"]))
        mods_children.insert(0, gustav_desc)
        modified = True

    # Check mod_order_children only if ModOrder exists in file (legacy compatibility)
    if mod_order_children is not None:
        order_modules = mod_order_children.findall("node[@id='Module']")
        base_order_node = None
        for m in order_modules:
            u_attr = m.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value") == base_module_uuid:
                base_order_node = m
                break

        if base_order_node is None:
            base_order_node = ET.Element("node", id="Module")
            ET.SubElement(base_order_node, "attribute", id="UUID", type="FixedString", value=base_module_uuid)
            mod_order_children.insert(0, base_order_node)
            modified = True
        else:
            if order_modules and order_modules[0] != base_order_node:
                mod_order_children.remove(base_order_node)
                mod_order_children.insert(0, base_order_node)
                modified = True

    return modified


def enable_mod(path: Path, mod_meta: dict, order_index: int | None = None, dry_run: bool = False) -> tuple[bool, str]:
    """
    Enables or reorders a mod in modsettings.lsx.
    Returns (changed, action_status) where action_status is 'enabled', 'reordered', or 'already_active'.
    """
    if not path.is_file():
        if not dry_run:
            create_default_modsettings(path)
        else:
            return True, "enabled"

    tree = ET.parse(path)
    root = tree.getroot()

    mod_order_children = root.find(".//node[@id='ModOrder']/children")
    mods_children = root.find(".//node[@id='Mods']/children")

    if mods_children is None:
        raise ValueError("Invalid modsettings.lsx: missing Mods children node.")

    base_modified = _ensure_base_module(root, mods_children, mod_order_children)

    target_uuid = mod_meta["UUID"]

    # Check if already present in ModOrder (if present)
    existing_order_node = None
    if mod_order_children is not None:
        for mod_node in mod_order_children.findall("node[@id='Module']"):
            u_attr = mod_node.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value") == target_uuid:
                existing_order_node = mod_node
                break

    existing_desc_node = None
    for desc_node in mods_children.findall("node[@id='ModuleShortDesc']"):
        u_attr = desc_node.find("attribute[@id='UUID']")
        if u_attr is not None and u_attr.get("value") == target_uuid:
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
            # Never insert at index 0 ahead of GustavDev/GustavX
            safe_idx = max(1, order_index)
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

    if target_uuid == GUSTAV_DEV["UUID"] or target_name.lower() in CORE_GUSTAV_NAMES:
        raise ValueError(f"Cannot disable core game module {target_name or 'GustavDev'}.")

    if not dry_run:
        if mod_order_children is not None:
            for m_node in list(mod_order_children.findall("node[@id='Module']")):
                u_attr = m_node.find("attribute[@id='UUID']")
                if u_attr is not None and u_attr.get("value") == target_uuid:
                    mod_order_children.remove(m_node)

        for desc in list(mods_children.findall("node[@id='ModuleShortDesc']")):
            u_attr = desc.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value") == target_uuid:
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
    if first_uuid != GUSTAV_DEV["UUID"] and first_name not in CORE_GUSTAV_NAMES:
        issues.append(
            f"Base game module (GustavDev / GustavX) must be at load order index 0 (found '{first_mod.get('Name', first_uuid)}')."
        )

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
            if idx < ulc_idx and u != GUSTAV_DEV["UUID"] and m_name not in CORE_GUSTAV_NAMES:
                issues.append(f"Warning: Mod '{mod_entry.get('Name', u)}' is loaded before UnlockLevelCurve.")

    return issues


def main():
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
    parser.add_argument("--isolate", "--clean", dest="isolate", action="store_true", help="Clean-room isolation: disable all other mods except base game and dependencies")
    parser.add_argument("--validate", action="store_true", help="Validate current load order rules")
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
    if args.json and not (args.list or args.enable or args.disable or args.validate):
        args.list = True

    action_result = {}

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
            isolated_count = isolate_load_order(modsettings_path, keep_uuids, dry_run=args.dry_run)
            action_result["isolated_count"] = isolated_count
            if not args.json and isolated_count > 0:
                verb = "[DRY-RUN] Would isolate" if args.dry_run else "Isolated"
                print(f"✓ {verb} load order (disabled {isolated_count} unrelated mod{'s' if isolated_count != 1 else ''}).")

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

    if args.list or args.enable or args.disable or args.validate:
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
