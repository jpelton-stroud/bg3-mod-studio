"""Core serialization, parsing, and management of Baldur's Gate 3 modsettings.lsx profiles."""

from __future__ import annotations

import datetime
import io
import os
import re
import shutil
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from typing import Any

from ..binary.larian_parsers import DEFAULT_VERSION64, find_mod_meta_files, parse_meta_lsx
from ..binary.lspk import BG3BinaryError, LspkArchive
from ..env_paths import (
    MODS_DIR,
    MY_MODS_DIR,
    detect_bg3_appdata_dirs,
    get_env_var,
    normalize_mod_key,
)
from ..exceptions import BG3Error

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
        "Version64": str(DEFAULT_VERSION64),
    },
    {
        "Folder": "DiceSet_02",
        "MD5": "9c98eaefccfb3f7cfd6870ff4e84a50d",
        "Name": "DiceSet_02",
        "PublishHandle": "0",
        "UUID": "b176a0ac-d79f-ed9d-5a87-5c2c80874e10",
        "Version64": str(DEFAULT_VERSION64),
    },
    {
        "Folder": "DiceSet_03",
        "MD5": "e800e59821eb3090e7e5f25cc478dbd3",
        "Name": "DiceSet_03",
        "PublishHandle": "0",
        "UUID": "e0a4d990-7b9b-8fa9-d7c6-04017c6cf5b1",
        "Version64": str(DEFAULT_VERSION64),
    },
    {
        "Folder": "DiceSet_06",
        "MD5": "4a53b4f61b1667007e21c661309b7435",
        "Name": "DiceSet_06",
        "PublishHandle": "0",
        "UUID": "ee4989eb-aab8-968f-8674-812ea2f4bfd7",
        "Version64": str(DEFAULT_VERSION64),
    },
    {
        "Folder": "MainUI",
        "MD5": "d41d8cd98f00b204e9800998ecf8427e",
        "Name": "MainUI",
        "PublishHandle": "0",
        "UUID": "630daa32-70f8-3da5-41b9-154fe8410236",
        "Version64": str(DEFAULT_VERSION64),
    },
    {
        "Folder": "ModBrowser",
        "MD5": "981922692a4f3bbfc4dd5941221fc4f3",
        "Name": "ModBrowser",
        "PublishHandle": "0",
        "UUID": "ee5a55ff-eb38-0b27-c5b0-f358dc306d34",
        "Version64": str(DEFAULT_VERSION64),
    },
    {
        "Folder": "PhotoMode",
        "MD5": "045fe21b32b1c766a0a09193aa9d1215",
        "Name": "PhotoMode",
        "PublishHandle": "0",
        "UUID": "55ef175c-59e3-b44b-3fb2-8f86acc5d550",
        "Version64": str(DEFAULT_VERSION64),
    },
    {
        "Folder": "CrossplayUI",
        "MD5": "d41d8cd98f00b204e9800998ecf8427e",
        "Name": "CrossplayUI",
        "PublishHandle": "0",
        "UUID": "e1ce736b-52e6-e713-e9e7-e6abbb15a198",
        "Version64": str(DEFAULT_VERSION64),
    },
]

CORE_SYSTEM_UUIDS = {m["UUID"].lower() for m in CORE_SYSTEM_MODULES} | {GUSTAV_DEV["UUID"].lower()}
CORE_SYSTEM_NAMES = {m["Name"].lower() for m in CORE_SYSTEM_MODULES} | CORE_GUSTAV_NAMES


def detect_modsettings_path() -> Path | None:
    """Detect modsettings.lsx path across WSL, native Linux, and Windows."""
    env_override = get_env_var("BG3_MODSETTINGS_PATH")
    if env_override:
        p = Path(env_override)
        if p.exists():
            return p

    for base in detect_bg3_appdata_dirs():
        candidate = base / "PlayerProfiles" / "Public" / "modsettings.lsx"
        if candidate.exists():
            return candidate

    return None


def get_appdata_mods_dir(modsettings_path: Path | None = None) -> Path | None:
    """Detect AppData/Local/Larian Studios/Baldur's Gate 3/Mods directory."""
    if modsettings_path and (modsettings_path.is_file() or modsettings_path.parent.is_dir()):
        try:
            candidate = modsettings_path.resolve().parents[2] / "Mods"
            if candidate.is_dir() or candidate.parent.is_dir():
                return candidate
        except (OSError, ValueError):
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
                            <attribute id="Folder" type="LSString" value="{mod["Folder"]}"/>
                            <attribute id="MD5" type="LSString" value="{mod["MD5"]}"/>
                            <attribute id="Name" type="LSString" value="{mod["Name"]}"/>
                            <attribute id="PublishHandle" type="uint64" value="{mod["PublishHandle"]}"/>
                            <attribute id="UUID" type="guid" value="{mod["UUID"]}"/>
                            <attribute id="Version64" type="int64" value="{mod["Version64"]}"/>
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
            raw = b'<?xml version="1.0" encoding="UTF-8"?>' + raw[header_end + 2 :]
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
    meta = parse_meta_lsx(content.encode("utf-8") if isinstance(content, str) else content)
    for attrs in meta.get("dependencies", []):
        u_str = attrs.get("UUID", "")
        n_str = attrs.get("Name", "")
        f_str = attrs.get("Folder", "")
        if not u_str:
            continue
        if (
            u_str == GUSTAV_DEV["UUID"]
            or n_str.lower() in CORE_GUSTAV_NAMES
            or f_str.lower() in CORE_GUSTAV_NAMES
        ):
            continue
        deps.append(
            {
                "Folder": f_str,
                "MD5": attrs.get("MD5", ""),
                "Name": n_str,
                "PublishHandle": attrs.get("PublishHandle", "0"),
                "UUID": u_str,
                "Version64": attrs.get("Version64", str(DEFAULT_VERSION64)),
            }
        )
    return deps


def _extract_meta_from_xml_text(content: str, fallback_name: str) -> dict | None:
    mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
    target = mod_info.group(1) if mod_info else content

    name = re.search(r'<attribute\s+id="Name"\s+type="[^"]*"\s+value="([^"]*)"', target)
    folder = re.search(r'<attribute\s+id="Folder"\s+type="[^"]*"\s+value="([^"]*)"', target)
    uuid_val = re.search(
        r'<attribute\s+id="UUID"\s+type="(?:FixedString|guid|LSString)"\s+value="([^"]*)"', target
    )
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
            "Version64": v64.group(1) if v64 else str(DEFAULT_VERSION64),
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
                        parsed = _extract_meta_from_xml_text(
                            mf.read_text(encoding="utf-8", errors="ignore"), d.name
                        )
                        if parsed and parsed.get("UUID", "").lower() == query_raw:
                            return parsed
                    except (OSError, UnicodeDecodeError, ValueError):
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
                        parsed = _extract_meta_from_xml_text(
                            mf.read_text(encoding="utf-8", errors="ignore"), d.name
                        )
                        if parsed:
                            return parsed
                    except (OSError, UnicodeDecodeError, ValueError):
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
                        parsed = _extract_meta_from_xml_text(
                            mf.read_text(encoding="utf-8", errors="ignore"), d.name
                        )
                        if parsed:
                            return parsed
                    except (OSError, UnicodeDecodeError, ValueError):
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
                except (OSError, struct.error, zlib.error, BG3BinaryError):
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
                except (OSError, struct.error, zlib.error, BG3BinaryError):
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

                resolved_info = resolve_dependency_metadata(
                    dep_uuid or dep.get("Name", ""), auto_document=False
                )
                if resolved_info and resolved_info.get("UUID"):
                    installed = resolved_info
            except (BG3Error, OSError, ValueError):
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


def backup_file(path: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".lsx.{ts}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def _ensure_base_module(
    root: ET.Element, mods_children: ET.Element, mod_order_children: ET.Element | None = None
) -> bool:
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

    # Ensure each core system module is present in canonical order (Patch 8)
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
            ET.SubElement(
                node,
                "attribute",
                id="PublishHandle",
                type="uint64",
                value=str(mod["PublishHandle"]),
            )
            ET.SubElement(node, "attribute", id="UUID", type="guid", value=mod["UUID"])
            ET.SubElement(
                node, "attribute", id="Version64", type="int64", value=str(mod["Version64"])
            )
            mods_children.insert(idx, node)
            existing_by_uuid[u_key] = node
            modified = True

    # Check mod_order_children only if ModOrder exists in file (legacy compatibility)
    if mod_order_children is not None:
        order_modules = mod_order_children.findall("node[@id='Module']")
        base_uuid = CORE_SYSTEM_MODULES[0]["UUID"]
        base_order_node = None
        for m in order_modules:
            u_attr = m.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value", "").lower() == base_uuid.lower():
                base_order_node = m
                break

        if base_order_node is None:
            base_order_node = ET.Element("node", id="Module")
            ET.SubElement(
                base_order_node, "attribute", id="UUID", type="FixedString", value=base_uuid
            )
            mod_order_children.insert(0, base_order_node)
            modified = True
        else:
            if order_modules and order_modules[0] != base_order_node:
                mod_order_children.remove(base_order_node)
                mod_order_children.insert(0, base_order_node)
                modified = True

    return modified


def enable_mod(
    path: Path, mod_meta: dict | str, order_index: int | None = None, dry_run: bool = False
) -> tuple[bool, str]:
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
            ET.SubElement(
                new_order_node, "attribute", id="UUID", type="FixedString", value=target_uuid
            )
            if order_index is not None:
                safe_idx = max(1, order_index)
                order_len = len(mod_order_children.findall("node[@id='Module']"))
                mod_order_children.insert(min(safe_idx, order_len), new_order_node)
            else:
                mod_order_children.append(new_order_node)

        new_desc_node = ET.Element("node", id="ModuleShortDesc")
        ET.SubElement(
            new_desc_node, "attribute", id="Folder", type="LSString", value=mod_meta["Folder"]
        )
        ET.SubElement(
            new_desc_node, "attribute", id="MD5", type="LSString", value=mod_meta.get("MD5", "")
        )
        ET.SubElement(
            new_desc_node, "attribute", id="Name", type="LSString", value=mod_meta["Name"]
        )
        ET.SubElement(
            new_desc_node,
            "attribute",
            id="PublishHandle",
            type="uint64",
            value=str(mod_meta.get("PublishHandle", "0")),
        )
        ET.SubElement(new_desc_node, "attribute", id="UUID", type="guid", value=target_uuid)
        ET.SubElement(
            new_desc_node,
            "attribute",
            id="Version64",
            type="int64",
            value=str(mod_meta.get("Version64", str(DEFAULT_VERSION64))),
        )

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
        m.get("Name", "").lower() == "gustavx"
        or u.lower() == CORE_SYSTEM_MODULES[0]["UUID"].lower()
        for u, m in mods.items()
    )
    if has_gustav_x:
        missing_core = [
            m["Name"]
            for m in CORE_SYSTEM_MODULES
            if m["UUID"].lower() not in {u.lower() for u in mods.keys()}
        ]
        if missing_core:
            issues.append(
                f"Missing core system modules required by Patch 8: {', '.join(missing_core)}"
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
            if (
                idx < ulc_idx
                and u != GUSTAV_DEV["UUID"]
                and m_name not in CORE_GUSTAV_NAMES
                and u.lower() not in CORE_SYSTEM_UUIDS
            ):
                issues.append(
                    f"Warning: Mod '{mod_entry.get('Name', u)}' is loaded before UnlockLevelCurve."
                )

    return issues


__all__ = [
    "CORE_GUSTAV_NAMES",
    "CORE_SYSTEM_MODULES",
    "CORE_SYSTEM_NAMES",
    "CORE_SYSTEM_UUIDS",
    "GUSTAV_DEV",
    "_ensure_base_module",
    "_extract_dependencies_from_xml_text",
    "_extract_meta_from_xml_text",
    "backup_file",
    "create_default_modsettings",
    "detect_modsettings_path",
    "disable_mod",
    "enable_mod",
    "get_appdata_mods_dir",
    "get_mod_metadata_from_workspace",
    "parse_modsettings",
    "resolve_all_dependencies",
    "save_modsettings",
    "validate_load_order",
]
