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
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MY_MODS_DIR = WORKSPACE_ROOT / "my_mods"
MODS_DIR = WORKSPACE_ROOT / "mods"

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"

# Default GustavDev module entry
GUSTAV_DEV = {
    "Folder": "GustavDev",
    "MD5": "33c1655f7ae3559b579ff3b9d2c45413",
    "Name": "GustavDev",
    "PublishHandle": "0",
    "UUID": "28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8",
    "Version64": "145100393449790344",
}


def detect_modsettings_path() -> Path | None:
    """Detect modsettings.lsx path across WSL, native Linux, and Windows."""
    env_override = os.environ.get("BG3_MODSETTINGS_PATH")
    if env_override:
        p = Path(env_override)
        if p.exists() or p.parent.exists():
            return p

    # WSL detection
    users_dir = Path("/mnt/c/Users")
    if users_dir.is_dir():
        for user_folder in users_dir.iterdir():
            if user_folder.is_dir() and user_folder.name not in ("All Users", "Default", "Default User", "Public"):
                target = user_folder / "AppData/Local/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/modsettings.lsx"
                if target.exists():
                    return target
                # Check if parent directory exists even if file doesn't exist yet
                if target.parent.is_dir():
                    return target

    # Native Windows detection
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        target = Path(local_app_data) / "Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/modsettings.lsx"
        if target.exists() or target.parent.is_dir():
            return target

    return None


def create_default_modsettings(path: Path):
    """Generate a clean skeleton modsettings.lsx with GustavDev."""
    path.parent.mkdir(parents=True, exist_ok=True)
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="500"/>
    <region id="ModuleSettings">
        <node id="root">
            <children>
                <node id="ModOrder">
                    <children>
                        <node id="Module">
                            <attribute id="UUID" type="FixedString" value="{GUSTAV_DEV['UUID']}"/>
                        </node>
                    </children>
                </node>
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

    return {"order": order, "mods": mods}


def get_mod_metadata_from_workspace(mod_name: str) -> dict | None:
    """Find mod in my_mods/ and extract its metadata for modsettings injection."""
    if not MY_MODS_DIR.exists():
        return None

    candidates = [d for d in MY_MODS_DIR.iterdir() if d.is_dir()]
    target_dir = None
    query_norm = mod_name.strip().lower().replace("-", "").replace("_", "")
    for d in candidates:
        if query_norm in d.name.lower().replace("-", "").replace("_", ""):
            target_dir = d
            break

    if not target_dir:
        return None

    meta_files = list(target_dir.glob("Mods/*/meta.lsx")) or list(target_dir.glob("Projects/*/meta.lsx"))
    if not meta_files:
        return None

    try:
        content = meta_files[0].read_text(encoding="utf-8")
        mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
        target = mod_info.group(1) if mod_info else content

        name = re.search(r'<attribute\s+id="Name"\s+type="LSString"\s+value="([^"]*)"', target)
        folder = re.search(r'<attribute\s+id="Folder"\s+type="LSString"\s+value="([^"]*)"', target)
        uuid_val = re.search(r'<attribute\s+id="UUID"\s+type="FixedString"\s+value="([^"]*)"', target)
        v64 = re.search(r'<attribute\s+id="Version64"\s+type="int64"\s+value="(\d+)"', target)
        md5 = re.search(r'<attribute\s+id="MD5"\s+type="LSString"\s+value="([^"]*)"', target)
        handle = re.search(r'<attribute\s+id="PublishHandle"\s+type="uint64"\s+value="([^"]*)"', target)

        if uuid_val:
            return {
                "Folder": folder.group(1) if folder else target_dir.name,
                "MD5": md5.group(1) if md5 else "",
                "Name": name.group(1) if name else target_dir.name,
                "PublishHandle": handle.group(1) if handle else "0",
                "UUID": uuid_val.group(1),
                "Version64": v64.group(1) if v64 else "36028797018963968",
            }
    except Exception:
        pass
    return None


def backup_file(path: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f".lsx.{ts}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def enable_mod(path: Path, mod_meta: dict, dry_run: bool = False) -> bool:
    if not path.is_file():
        create_default_modsettings(path)

    tree = ET.parse(path)
    root = tree.getroot()

    mod_order_children = root.find(".//node[@id='ModOrder']/children")
    mods_children = root.find(".//node[@id='Mods']/children")

    if mod_order_children is None or mods_children is None:
        raise ValueError("Invalid modsettings.lsx: missing ModOrder or Mods children nodes.")

    target_uuid = mod_meta["UUID"]

    # Check if already enabled
    for mod_node in mod_order_children.findall("node[@id='Module']"):
        u_attr = mod_node.find("attribute[@id='UUID']")
        if u_attr is not None and u_attr.get("value") == target_uuid:
            return False  # Already enabled

    if not dry_run:
        backup_file(path)

        # 1. Append to ModOrder
        new_order_node = ET.SubElement(mod_order_children, "node", id="Module")
        ET.SubElement(new_order_node, "attribute", id="UUID", type="FixedString", value=target_uuid)

        # 2. Append to Mods
        new_desc_node = ET.SubElement(mods_children, "node", id="ModuleShortDesc")
        ET.SubElement(new_desc_node, "attribute", id="Folder", type="LSString", value=mod_meta["Folder"])
        ET.SubElement(new_desc_node, "attribute", id="MD5", type="LSString", value=mod_meta["MD5"])
        ET.SubElement(new_desc_node, "attribute", id="Name", type="LSString", value=mod_meta["Name"])
        ET.SubElement(new_desc_node, "attribute", id="PublishHandle", type="uint64", value=str(mod_meta["PublishHandle"]))
        ET.SubElement(new_desc_node, "attribute", id="UUID", type="guid", value=target_uuid)
        ET.SubElement(new_desc_node, "attribute", id="Version64", type="int64", value=str(mod_meta["Version64"]))

        tree.write(path, encoding="utf-8", xml_declaration=True)

    return True


def disable_mod(path: Path, mod_name: str, dry_run: bool = False) -> bool:
    if not path.is_file():
        return False

    tree = ET.parse(path)
    root = tree.getroot()

    mod_order_children = root.find(".//node[@id='ModOrder']/children")
    mods_children = root.find(".//node[@id='Mods']/children")

    if mod_order_children is None or mods_children is None:
        return False

    # Find target UUID by matching name or folder or UUID directly
    target_uuid = None
    for desc in mods_children.findall("node[@id='ModuleShortDesc']"):
        name_attr = desc.find("attribute[@id='Name']")
        uuid_attr = desc.find("attribute[@id='UUID']")
        if name_attr is not None and uuid_attr is not None:
            n_val = name_attr.get("value", "")
            u_val = uuid_attr.get("value", "")
            if mod_name.lower() in n_val.lower() or mod_name.lower() == u_val.lower():
                target_uuid = u_val
                break

    if not target_uuid:
        return False

    if target_uuid == GUSTAV_DEV["UUID"]:
        raise ValueError("Cannot disable core game module GustavDev.")

    if not dry_run:
        backup_file(path)

        # Remove from ModOrder
        for m_node in list(mod_order_children.findall("node[@id='Module']")):
            u_attr = m_node.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value") == target_uuid:
                mod_order_children.remove(m_node)

        # Remove from Mods
        for desc in list(mods_children.findall("node[@id='ModuleShortDesc']")):
            u_attr = desc.find("attribute[@id='UUID']")
            if u_attr is not None and u_attr.get("value") == target_uuid:
                mods_children.remove(desc)

        tree.write(path, encoding="utf-8", xml_declaration=True)

    return True


def validate_load_order(parsed: dict) -> list[str]:
    issues = []
    order = parsed["order"]
    mods = parsed["mods"]

    if not order:
        issues.append("Load order is empty.")
        return issues

    if order[0] != GUSTAV_DEV["UUID"]:
        issues.append(f"GustavDev must be at load order index 0 (found {order[0]}).")

    for u in order:
        if u not in mods:
            issues.append(f"UUID '{u}' is in ModOrder but missing from Mods description list.")

    # Check UnlockLevelCurve ordering if present
    ulc_uuid = "a2ffd0e4-c407-8642-2611-c934ea0b0a77"
    if ulc_uuid in order:
        ulc_idx = order.index(ulc_uuid)
        # Check any custom mods that depend on ULC
        for idx, u in enumerate(order):
            if idx < ulc_idx and u != GUSTAV_DEV["UUID"]:
                issues.append(f"Warning: Mod '{mods.get(u, {}).get('Name', u)}' is loaded before UnlockLevelCurve.")

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Inspect, activate, and validate Baldur's Gate 3 modsettings.lsx load order."
    )
    parser.add_argument("--path", help="Explicit path to modsettings.lsx")
    parser.add_argument("--list", action="store_true", help="Display active mod load order")
    parser.add_argument("--enable", help="Enable a mod by name from my_mods/ in load order")
    parser.add_argument("--disable", help="Disable a mod by name/UUID from active load order")
    parser.add_argument("--validate", action="store_true", help="Validate current load order rules")
    parser.add_argument("--create-default", action="store_true", help="Create default modsettings.lsx if missing")
    parser.add_argument("--dry-run", action="store_true", help="Preview modifications without writing to disk")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    modsettings_path = Path(args.path) if args.path else detect_modsettings_path()

    if not modsettings_path:
        print(f"{RED}Error: Could not locate modsettings.lsx. Specify path with --path.{RESET}", file=sys.stderr)
        sys.exit(1)

    if args.create_default:
        if modsettings_path.is_file():
            print(f"modsettings.lsx already exists at: {modsettings_path}")
        else:
            create_default_modsettings(modsettings_path)
            print(f"✓ Created default modsettings.lsx at: {modsettings_path}")
        sys.exit(0)

    if not modsettings_path.is_file() and not args.enable:
        print(f"{YELLOW}Notice: modsettings.lsx does not exist yet at {modsettings_path}.{RESET}")
        print("Run with --create-default to initialize, or --enable <Mod> to generate with mod.")
        sys.exit(0)

    parsed = parse_modsettings(modsettings_path)

    if args.list:
        if args.json:
            print(json.dumps(parsed, indent=2))
        else:
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
        sys.exit(0)

    if args.enable:
        mod_meta = get_mod_metadata_from_workspace(args.enable)
        if not mod_meta:
            print(f"{RED}Error: Mod '{args.enable}' not found in my_mods/ or missing meta.lsx.{RESET}", file=sys.stderr)
            sys.exit(1)

        success = enable_mod(modsettings_path, mod_meta, dry_run=args.dry_run)
        if success:
            action_desc = "[DRY-RUN] Would enable" if args.dry_run else "Successfully enabled"
            print(f"✓ {action_desc} '{mod_meta['Name']}' ({mod_meta['UUID']}) in load order at {modsettings_path}!")
        else:
            print(f"Mod '{mod_meta['Name']}' is already active in load order.")
        sys.exit(0)

    if args.disable:
        try:
            success = disable_mod(modsettings_path, args.disable, dry_run=args.dry_run)
            if success:
                action_desc = "[DRY-RUN] Would disable" if args.dry_run else "Successfully disabled"
                print(f"✓ {action_desc} '{args.disable}' from load order at {modsettings_path}!")
            else:
                print(f"Mod '{args.disable}' was not found in active load order.")
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    if args.validate:
        issues = validate_load_order(parsed)
        if not issues:
            print(f"{GREEN}✓ Load order is valid ({len(parsed['order'])} mods active).{RESET}")
            sys.exit(0)
        else:
            print(f"{YELLOW}Load order issues detected:{RESET}")
            for issue in issues:
                print(f"  • {issue}")
            sys.exit(1)

    # Default action if no flags
    parser.print_help()


if __name__ == "__main__":
    main()
