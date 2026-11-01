#!/usr/bin/env python3
"""
scaffold_atlas.py
-----------------
Texture atlas UV coordinate computation and GUI/Icons.lsx scaffolding
for Baldur's Gate 3 modding.
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from typing import Any

from bg3_authoring.scaffold_common import (
    ScaffoldResult,
    create_empty_lsx,
    get_or_create_root_children,
    prettify_xml,
    resolve_mod_paths,
)


def _compute_icon_uvs(
    icons: list[str],
    icon_size: int,
    atlas_width: int,
    atlas_height: int,
) -> list[dict[str, Any]]:
    cols = atlas_width // icon_size
    rows = atlas_height // icon_size
    max_icons = cols * rows

    if len(icons) > max_icons:
        raise ValueError(
            f"Too many icons ({len(icons)}) for atlas size {atlas_width}x{atlas_height} (max {max_icons})."
        )

    mappings: list[dict[str, Any]] = []
    for idx, name in enumerate(icons):
        col = idx % cols
        row = idx // cols
        u1 = round((col * icon_size) / atlas_width, 6)
        u2 = round(((col + 1) * icon_size) / atlas_width, 6)
        v1 = round((row * icon_size) / atlas_height, 6)
        v2 = round(((row + 1) * icon_size) / atlas_height, 6)
        mappings.append({
            "name": name.strip(),
            "u1": u1,
            "u2": u2,
            "v1": v1,
            "v2": v2,
        })
    return mappings


def scaffold_icon_uvs(
    mod_name_or_path: str,
    atlas_name: str,
    icons: list[str],
    icon_size: int = 64,
    atlas_width: int = 2048,
    atlas_height: int = 2048,
    atlas_uuid: str | None = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """Calculates UV coordinates and scaffolds GUI/Icons.lsx for texture atlas grids."""
    _mod_root, mod_folder_dir, _loc_file, mod_slug = resolve_mod_paths(mod_name_or_path)

    gui_dir = mod_folder_dir / "GUI"
    icons_file = gui_dir / "Icons.lsx"

    allocated_atlas_uuid = atlas_uuid.strip() if atlas_uuid else str(uuid.uuid4())
    mappings = _compute_icon_uvs(icons, icon_size, atlas_width, atlas_height)

    if icons_file.exists():
        tree = ET.parse(icons_file)
        root = tree.getroot()
    else:
        root = create_empty_lsx("TextureAtlasInfo")

    children = get_or_create_root_children(root, "TextureAtlasInfo")

    for node in list(children.findall("./node[@id='TextureAtlasIconProperties']")):
        for attr in node.findall("./attribute"):
            if attr.get("id") == "Id" and attr.get("value") == atlas_name:
                children.remove(node)
                break

    atlas_props_node = ET.SubElement(children, "node", id="TextureAtlasIconProperties")
    ET.SubElement(atlas_props_node, "attribute", id="Id", type="FixedString", value=atlas_name)
    ET.SubElement(atlas_props_node, "attribute", id="UUID", type="guid", value=allocated_atlas_uuid)

    atlas_icons_node = ET.SubElement(atlas_props_node, "children")
    for m in mappings:
        inode = ET.SubElement(atlas_icons_node, "node", id="IconUV")
        ET.SubElement(inode, "attribute", id="Id", type="FixedString", value=m["name"])
        ET.SubElement(inode, "attribute", id="U1", type="float", value=str(m["u1"]))
        ET.SubElement(inode, "attribute", id="U2", type="float", value=str(m["u2"]))
        ET.SubElement(inode, "attribute", id="V1", type="float", value=str(m["v1"]))
        ET.SubElement(inode, "attribute", id="V2", type="float", value=str(m["v2"]))

    if not dry_run:
        gui_dir.mkdir(parents=True, exist_ok=True)
        icons_file.write_text(prettify_xml(root), encoding="utf-8")

    return ScaffoldResult(
        success=True,
        mod=mod_slug,
        name=atlas_name,
        asset_type="icon-uvs",
        uuid=allocated_atlas_uuid,
        file=str(icons_file),
        dry_run=dry_run,
        details={
            "icon_size": icon_size,
            "total_icons": len(mappings),
            "mappings": mappings,
        },
    )
