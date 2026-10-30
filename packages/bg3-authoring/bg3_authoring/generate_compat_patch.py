#!/usr/bin/env python3
"""
generate_compat_patch.py - Automatically scaffolds compatibility patches for colliding BG3 mods.

Detects progression collisions between two mods, extracts metadata dependencies,
and generates either a standalone patch mod (with merged Progressions.lsx) or a
Compatibility Framework (CF) integration payload.
"""

import argparse
import json
import re
import struct
import sys
import uuid
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from typing import Any
from xml.dom import minidom

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bg3_core.env_paths import resolve_mod_dir as _resolve_mod_dir
from bg3_core.larian_parsers import find_mod_meta_files, find_mod_progression_files


def resolve_mod_dir(mod_name_or_path: str, workspace_root: Path | None = None) -> Path:
    res = _resolve_mod_dir(mod_name_or_path, prefer_my_mods=True)
    if res is None:
        raise FileNotFoundError(f"Mod directory not found: {mod_name_or_path}")
    return res


def extract_mod_meta(mod_dir: Path) -> dict:
    """Extracts UUID, Name, Folder, and Version64 from meta.lsx across my_mods/ and mods/."""
    meta_files = find_mod_meta_files(mod_dir)
    if not meta_files:
        raise FileNotFoundError(f"No meta.lsx found in {mod_dir}")

    tree = ET.parse(meta_files[0])
    desc = tree.find(".//node[@id='ModuleInfo']/attribute[@id='UUID']")
    name_attr = tree.find(".//node[@id='ModuleInfo']/attribute[@id='Name']")
    folder_attr = tree.find(".//node[@id='ModuleInfo']/attribute[@id='Folder']")
    ver_attr = tree.find(".//node[@id='ModuleInfo']/attribute[@id='Version64']")

    mod_uuid = desc.get("value") if desc is not None else str(uuid.uuid4())
    mod_name = name_attr.get("value") if name_attr is not None else mod_dir.name
    mod_folder = folder_attr.get("value") if folder_attr is not None else mod_dir.name
    mod_ver = ver_attr.get("value") if ver_attr is not None else "36028797018963968"

    return {
        "UUID": mod_uuid,
        "Name": mod_name,
        "Folder": mod_folder,
        "Version64": mod_ver,
        "path": mod_dir,
    }


def parse_progressions(mod_dir: Path) -> dict[tuple[str, str], ET.Element]:
    """Parses Progressions.lsx across my_mods/ and mods/data/ and returns map of (class_name.lower(), level) -> node."""
    nodes = {}
    for p_file in find_mod_progression_files(mod_dir):
        try:
            tree = ET.parse(p_file)
            for p_node in tree.findall(".//node[@id='Progression']"):
                name_attr = p_node.find("attribute[@id='Name']")
                lvl_attr = p_node.find("attribute[@id='Level']")
                if name_attr is not None and lvl_attr is not None:
                    key = (name_attr.get("value", "").strip().lower(), lvl_attr.get("value", "").strip())
                    nodes[key] = p_node
        except Exception:
            continue
    return nodes


def merge_progression_attributes(node1: ET.Element, node2: ET.Element) -> dict[str, str]:
    """Combines passives, boosts, and selectors from two colliding nodes."""
    res = {}
    for attr in ["PassivesAdded", "Boosts", "Selectors"]:
        v1 = node1.find(f"attribute[@id='{attr}']")
        v2 = node2.find(f"attribute[@id='{attr}']")
        parts = []
        val1 = v1.get("value") if v1 is not None else None
        if val1:
            parts.extend([x.strip() for x in val1.split(";") if x.strip()])
        val2 = v2.get("value") if v2 is not None else None
        if val2:
            parts.extend([x.strip() for x in val2.split(";") if x.strip()])

        # Deduplicate while preserving order
        unique_parts = list(dict.fromkeys(parts))
        if unique_parts:
            res[attr] = ";".join(unique_parts)

    imp1 = node1.find("attribute[@id='AllowImprovement']")
    imp2 = node2.find("attribute[@id='AllowImprovement']")
    if (imp1 is not None and imp1.get("value") == "true") or (imp2 is not None and imp2.get("value") == "true"):
        res["AllowImprovement"] = "true"

    return res


def build_mods_meta_lsx(patch_name: str, patch_uuid: str, folder_name: str, deps: list[dict]) -> str:
    dep_nodes = []
    for d in deps:
        dep_nodes.append(f"""                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="{d['Folder']}"/>
                            <attribute id="MD5" type="LSString" value=""/>
                            <attribute id="Name" type="LSString" value="{d['Name']}"/>
                            <attribute id="PublishHandle" type="uint64" value="0"/>
                            <attribute id="UUID" type="guid" value="{d['UUID']}"/>
                            <attribute id="Version64" type="int64" value="{d['Version64']}"/>
                        </node>""")

    dep_xml = "\n".join(dep_nodes)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="500"/>
    <region id="Config">
        <node id="root">
            <children>
                <node id="Dependencies">
                    <children>
{dep_xml}
                    </children>
                </node>
                <node id="ModuleInfo">
                    <attribute id="Author" type="LSString" value="MTGHillGiant"/>
                    <attribute id="CharacterCreationLevelName" type="FixedString" value=""/>
                    <attribute id="Description" type="LSString" value="Compatibility Patch for {deps[0]['Name']} and {deps[1]['Name']}"/>
                    <attribute id="Folder" type="LSString" value="{folder_name}"/>
                    <attribute id="GMTemplate" type="FixedString" value=""/>
                    <attribute id="LobbyLevelName" type="FixedString" value=""/>
                    <attribute id="MD5" type="LSString" value=""/>
                    <attribute id="MainMenuBackgroundVideo" type="FixedString" value=""/>
                    <attribute id="MenuLevelName" type="FixedString" value=""/>
                    <attribute id="Name" type="LSString" value="{patch_name}"/>
                    <attribute id="NumPlayers" type="uint8" value="4"/>
                    <attribute id="PhotoBooth" type="FixedString" value=""/>
                    <attribute id="PublishHandle" type="uint64" value="0"/>
                    <attribute id="StartupLevelName" type="FixedString" value=""/>
                    <attribute id="UUID" type="FixedString" value="{patch_uuid}"/>
                    <attribute id="Version64" type="int64" value="36028797018963968"/>
                    <children>
                        <node id="PublishVersion">
                            <attribute id="Version64" type="int64" value="36028797018963968"/>
                        </node>
                        <node id="Scripts"/>
                        <node id="TargetModes">
                            <children>
                                <node id="Target">
                                    <attribute id="Object" type="FixedString" value="Story"/>
                                </node>
                            </children>
                        </node>
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>
"""


def build_projects_meta_lsx(patch_name: str, patch_uuid: str, project_uuid: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="500"/>
    <region id="MetaData">
        <node id="root">
            <attribute id="GameProject" type="LSString" value=""/>
            <attribute id="Module" type="LSString" value="{patch_uuid}"/>
            <attribute id="Name" type="LSString" value="{patch_name}"/>
            <attribute id="UUID" type="LSString" value="{project_uuid}"/>
            <attribute id="UpdatedDependencies" type="bool" value="true"/>
            <children>
                <node id="Categories"/>
            </children>
        </node>
    </region>
</save>
"""


def generate_512_png(r: int = 35, g: int = 25, b: int = 55) -> bytes:
    width, height = 512, 512
    raw_row = b"\x00" + bytes([r, g, b, 255]) * width
    raw_image = raw_row * height
    compressed = zlib.compress(raw_image, 9)

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = zlib.crc32(chunk) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", compressed)
        + make_chunk(b"IEND", b"")
    )


def prettify_xml_element(elem: ET.Element) -> str:
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty = reparsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")
    lines = [line for line in pretty.splitlines() if line.strip()]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold compatibility patches or Compatibility Framework configs for colliding BG3 mods."
    )
    parser.add_argument("--mod1", required=True, help="First mod name or directory path.")
    parser.add_argument("--mod2", required=True, help="Second mod name or directory path.")
    parser.add_argument("--name", help="Custom patch mod name (default: <Mod1><Mod2>Patch).")
    parser.add_argument("--mode", choices=["standalone", "cf"], default="standalone", help="Patch mode: 'standalone' or 'cf' (Compatibility Framework).")
    parser.add_argument("--dry-run", action="store_true", help="Preview patch generation without writing.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON summary.")

    args = parser.parse_args()
    workspace_root = Path(__file__).resolve().parents[2]

    try:
        mod1_dir = resolve_mod_dir(args.mod1, workspace_root)
        mod2_dir = resolve_mod_dir(args.mod2, workspace_root)

        meta1 = extract_mod_meta(mod1_dir)
        meta2 = extract_mod_meta(mod2_dir)

        # Detect colliding progressions
        p1 = parse_progressions(mod1_dir)
        p2 = parse_progressions(mod2_dir)

        collisions = {}
        for key in p1.keys():
            if key in p2:
                collisions[key] = (p1[key], p2[key])

        clean1 = re.sub(r"[^a-zA-Z0-9]", "", meta1["Name"])
        clean2 = re.sub(r"[^a-zA-Z0-9]", "", meta2["Name"])
        patch_name = args.name or f"{clean1}{clean2}Patch"
        patch_slug = f"{mod1_dir.name}-{mod2_dir.name}-patch".lower()

        patch_uuid = str(uuid.uuid4())
        project_uuid = str(uuid.uuid4())
        folder_name = f"{patch_name}_{patch_uuid}"
        patch_dir = workspace_root / "my_mods" / patch_slug

        merged_nodes: list[dict[str, Any]] = []
        for (c_name, lvl), (node1, node2) in collisions.items():
            merged_attrs = merge_progression_attributes(node1, node2)
            t1 = node1.find("attribute[@id='TableUUID']")
            t2 = node2.find("attribute[@id='TableUUID']")
            table_uuid_attr = t1 if t1 is not None else t2
            table_uuid = table_uuid_attr.get("value") if table_uuid_attr is not None else str(uuid.uuid4())

            pt1 = node1.find("attribute[@id='ProgressionType']")
            pt2 = node2.find("attribute[@id='ProgressionType']")
            prog_type_attr = pt1 if pt1 is not None else pt2
            prog_type = prog_type_attr.get("value") if prog_type_attr is not None else "0"

            merged_nodes.append({
                "class": c_name.capitalize(),
                "level": lvl,
                "table_uuid": table_uuid,
                "progression_type": prog_type,
                "node_uuid": str(uuid.uuid4()),
                "attrs": merged_attrs,
            })

        cf_config = None
        if args.mode == "cf":
            # Generate CF JSON payload
            cf_config = {
                "Author": "MTGHillGiant",
                "Mod": patch_name,
                "UUID": patch_uuid,
                "Injections": [
                    {
                        "Class": n["class"],
                        "Level": int(n["level"]),
                        "TableUUID": n["table_uuid"],
                        "Passives": n["attrs"].get("PassivesAdded", "").split(";"),
                        "Boosts": n["attrs"].get("Boosts", "").split(";"),
                    }
                    for n in merged_nodes
                ],
            }

        if not args.dry_run:
            # 1. Projects & Mods meta.lsx + PNG assets
            mods_meta_content = build_mods_meta_lsx(patch_name, patch_uuid, folder_name, [meta1, meta2])
            proj_meta_content = build_projects_meta_lsx(patch_name, patch_uuid, project_uuid)
            png_bytes = generate_512_png()

            proj_folder = patch_dir / "Projects" / folder_name
            mods_folder = patch_dir / "Mods" / folder_name
            pub_folder = patch_dir / "Public" / folder_name
            loc_folder = patch_dir / "Localization" / "English"

            proj_folder.mkdir(parents=True, exist_ok=True)
            mods_folder.mkdir(parents=True, exist_ok=True)
            pub_folder.mkdir(parents=True, exist_ok=True)
            loc_folder.mkdir(parents=True, exist_ok=True)

            (proj_folder / "meta.lsx").write_text(proj_meta_content, encoding="utf-8")
            (mods_folder / "meta.lsx").write_text(mods_meta_content, encoding="utf-8")
            (proj_folder / "thumbnail.png").write_bytes(png_bytes)
            (mods_folder / "mod_publish_logo.png").write_bytes(png_bytes)
            (loc_folder / f"{patch_name}.xml").write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n<contentList date="15/10/2026 00:00">\n</contentList>\n',
                encoding="utf-8",
            )

            # 2. Progressions.lsx
            if merged_nodes:
                root_tree = ET.fromstring("""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="500"/>
    <region id="Progressions">
        <node id="root">
            <children>
            </children>
        </node>
    </region>
</save>""")
                children = root_tree.find(".//children")
                if children is None:
                    children = ET.SubElement(root_tree, "children")
                for mn in merged_nodes:
                    node = ET.SubElement(children, "node", id="Progression")
                    ET.SubElement(node, "attribute", id="Level", type="uint8", value=str(mn["level"]))
                    ET.SubElement(node, "attribute", id="Name", type="LSString", value=mn["class"])
                    ET.SubElement(node, "attribute", id="ProgressionType", type="uint8", value=str(mn["progression_type"]))
                    ET.SubElement(node, "attribute", id="TableUUID", type="guid", value=mn["table_uuid"])
                    ET.SubElement(node, "attribute", id="UUID", type="guid", value=mn["node_uuid"])
                    for k, v in mn["attrs"].items():
                        ET.SubElement(node, "attribute", id=k, type="LSString" if k != "AllowImprovement" else "bool", value=v)

                prog_file = pub_folder / "Progressions" / "Progressions.lsx"
                prog_file.parent.mkdir(parents=True, exist_ok=True)
                prog_file.write_text(prettify_xml_element(root_tree), encoding="utf-8")

            # 3. CF Config if mode == cf
            if cf_config:
                cf_file = pub_folder / "CompatibilityFramework" / "Config.json"
                cf_file.parent.mkdir(parents=True, exist_ok=True)
                cf_file.write_text(json.dumps(cf_config, indent=2), encoding="utf-8")

            # 4. README
            readme_content = f"""# {patch_name}

Compatibility patch reconciling [{meta1['Name']}] and [{meta2['Name']}].

## Reconciled Progression Levels:
{chr(10).join(f"- **{n['class']} Level {n['level']}**: Merged passives: `{n['attrs'].get('PassivesAdded', 'none')}`" for n in merged_nodes) if merged_nodes else "- No direct progression collisions detected."}
"""
            (patch_dir / "README.md").write_text(readme_content, encoding="utf-8")

        res = {
            "status": "success",
            "patch_name": patch_name,
            "patch_slug": patch_slug,
            "patch_uuid": patch_uuid,
            "patch_dir": str(patch_dir),
            "mode": args.mode,
            "dependencies": [meta1["Name"], meta2["Name"]],
            "resolved_collisions": len(merged_nodes),
            "collisions": [f"{n['class']} Lvl {n['level']}" for n in merged_nodes],
            "dry_run": args.dry_run,
        }

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            dry_str = " [DRY-RUN]" if args.dry_run else ""
            print(f"[✓] Successfully generated compatibility patch '{patch_name}'{dry_str}:")
            print(f"    Target directory: {patch_dir}")
            print(f"    Resolved Collisions: {len(merged_nodes)}")
            for n in merged_nodes:
                print(f"      • {n['class']} Level {n['level']}: {n['attrs'].get('PassivesAdded', '')}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
