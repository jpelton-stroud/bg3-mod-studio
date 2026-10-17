#!/usr/bin/env python3
"""
scaffold_icon_uvs.py - Calculates UV coordinates and scaffolds GUI/Icons.lsx for custom BG3 icons.

Computes normalized floating-point UV coordinates (U1, V1, U2, V2) on a
power-of-two texture atlas grid and emits engine-compliant Larian Icons.lsx.
"""

import argparse
import json
import math
import os
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.lib.cli_common import ConsoleColor, ExitCode
from scripts.lib.env_paths import MY_MODS_DIR, resolve_mod_dir


def resolve_mod_public_dir(mod_path_or_slug: str, workspace_root: Path) -> tuple[Path, str]:
    candidate = resolve_mod_dir(mod_path_or_slug, prefer_my_mods=True)
    if candidate is None or not candidate.is_dir():
        raise FileNotFoundError(f"Mod directory not found: '{mod_path_or_slug}'")

    public_dir = candidate / "Public"
    if not public_dir.is_dir():
        raise FileNotFoundError(f"Missing 'Public/' directory in mod: '{candidate}'")

    subdirs = [d for d in public_dir.iterdir() if d.is_dir() and d.name != "Shared"]
    if not subdirs:
        raise FileNotFoundError(f"No mod folder found under '{public_dir}'")

    return subdirs[0], candidate.name


def compute_uv_mappings(
    icon_names: list[str],
    icon_size: int = 64,
    atlas_width: int = 2048,
    atlas_height: int = 2048,
) -> list[dict]:
    """Calculates normalized float UV coordinates (0.0 to 1.0) for each icon on the grid."""
    cols = atlas_width // icon_size
    rows = atlas_height // icon_size
    max_icons = cols * rows

    if len(icon_names) > max_icons:
        raise ValueError(
            f"Too many icons ({len(icon_names)}) for atlas size {atlas_width}x{atlas_height} (max {max_icons})."
        )

    mappings = []
    for idx, name in enumerate(icon_names):
        col = idx % cols
        row = idx // cols

        u1 = (col * icon_size) / atlas_width
        u2 = ((col + 1) * icon_size) / atlas_width
        v1 = (row * icon_size) / atlas_height
        v2 = ((row + 1) * icon_size) / atlas_height

        mappings.append({
            "name": name,
            "col": col,
            "row": row,
            "u1": round(u1, 6),
            "u2": round(u2, 6),
            "v1": round(v1, 6),
            "v2": round(v2, 6),
        })

    return mappings


def build_icons_lsx(
    atlas_name: str,
    atlas_uuid: str,
    icon_size: int,
    atlas_width: int,
    atlas_height: int,
    uv_mappings: list[dict],
) -> str:
    """Generates Larian Icons.lsx XML document."""
    root = ET.Element("save")
    ET.SubElement(root, "version", major="4", minor="0", revision="9", build="328")

    # Region 1: TextureAtlasInfo
    reg_info = ET.SubElement(root, "region", id="TextureAtlasInfo")
    node_info_root = ET.SubElement(reg_info, "node", id="root")
    children_info = ET.SubElement(node_info_root, "children")

    node_icon_size = ET.SubElement(children_info, "node", id="TextureAtlasIconSize")
    ET.SubElement(node_icon_size, "attribute", id="Height", type="int64", value=str(icon_size))
    ET.SubElement(node_icon_size, "attribute", id="Width", type="int64", value=str(icon_size))

    node_path = ET.SubElement(children_info, "node", id="TextureAtlasPath")
    ET.SubElement(node_path, "attribute", id="Path", type="LSString", value=f"Assets/Textures/Icons/{atlas_name}.dds")
    ET.SubElement(node_path, "attribute", id="UUID", type="FixedString", value=atlas_uuid)

    node_tex_size = ET.SubElement(children_info, "node", id="TextureAtlasTextureSize")
    ET.SubElement(node_tex_size, "attribute", id="Height", type="int64", value=str(atlas_height))
    ET.SubElement(node_tex_size, "attribute", id="Width", type="int64", value=str(atlas_width))

    # Region 2: IconUVList
    reg_uv = ET.SubElement(root, "region", id="IconUVList")
    node_uv_root = ET.SubElement(reg_uv, "node", id="root")
    children_uv = ET.SubElement(node_uv_root, "children")

    for m in uv_mappings:
        node_uv = ET.SubElement(children_uv, "node", id="IconUV")
        ET.SubElement(node_uv, "attribute", id="MapKey", type="FixedString", value=m["name"])
        ET.SubElement(node_uv, "attribute", id="U1", type="float", value=str(m["u1"]))
        ET.SubElement(node_uv, "attribute", id="U2", type="float", value=str(m["u2"]))
        ET.SubElement(node_uv, "attribute", id="V1", type="float", value=str(m["v1"]))
        ET.SubElement(node_uv, "attribute", id="V2", type="float", value=str(m["v2"]))

    rough_string = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty = reparsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")
    lines = [line for line in pretty.splitlines() if line.strip()]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Calculate UV coordinates and generate GUI/Icons.lsx for custom BG3 icons."
    )
    parser.add_argument("--mod", required=True, help="Mod name/slug in my_mods/ or directory path.")
    parser.add_argument(
        "--icon-names",
        help="Comma-separated icon names (e.g. 'Spell_NethereseBlast,Item_ShadowBlade,Passive_DarkAffinity').",
    )
    parser.add_argument(
        "--icons-dir",
        help="Directory containing individual PNG icon files (names will be derived from filenames).",
    )
    parser.add_argument("--atlas-name", help="Name of the atlas texture file without extension (e.g. MyMod_Icons).")
    parser.add_argument("--atlas-uuid", help="Atlas UUID (defaults to generating a new random UUID).")
    parser.add_argument("--icon-size", type=int, default=64, help="Square pixel dimensions per icon (default: 64).")
    parser.add_argument("--atlas-size", type=int, default=2048, help="Atlas texture dimension in pixels (default: 2048).")
    parser.add_argument("--dry-run", action="store_true", help="Preview generated LSX without modifying files.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON summary.")

    args = parser.parse_args()
    workspace_root = Path(__file__).resolve().parents[2]

    try:
        mod_public_dir, mod_slug = resolve_mod_public_dir(args.mod, workspace_root)
        gui_dir = mod_public_dir / "GUI"
        icons_lsx_file = gui_dir / "Icons.lsx"

        # Determine icon names
        names = []
        if args.icons_dir:
            dir_path = Path(args.icons_dir)
            if not dir_path.is_dir():
                raise FileNotFoundError(f"Icons directory not found: '{args.icons_dir}'")
            for p in sorted(dir_path.glob("*.png")):
                names.append(p.stem)

        if args.icon_names:
            for item in args.icon_names.split(","):
                item_clean = item.strip()
                if item_clean and item_clean not in names:
                    names.append(item_clean)

        if not names:
            raise ValueError("No icons provided. Specify --icon-names or --icons-dir.")

        atlas_name = args.atlas_name or f"{mod_slug.replace('-', '_')}_Icons"
        atlas_uuid = args.atlas_uuid or str(uuid.uuid4())

        uv_mappings = compute_uv_mappings(
            icon_names=names,
            icon_size=args.icon_size,
            atlas_width=args.atlas_size,
            atlas_height=args.atlas_size,
        )

        lsx_content = build_icons_lsx(
            atlas_name=atlas_name,
            atlas_uuid=atlas_uuid,
            icon_size=args.icon_size,
            atlas_width=args.atlas_size,
            atlas_height=args.atlas_size,
            uv_mappings=uv_mappings,
        )

        if not args.dry_run:
            gui_dir.mkdir(parents=True, exist_ok=True)
            icons_lsx_file.write_text(lsx_content, encoding="utf-8")

        res = {
            "status": "success",
            "mod": mod_slug,
            "icons_file": str(icons_lsx_file),
            "atlas_name": atlas_name,
            "atlas_uuid": atlas_uuid,
            "atlas_size": f"{args.atlas_size}x{args.atlas_size}",
            "icon_size": f"{args.icon_size}x{args.icon_size}",
            "total_icons": len(uv_mappings),
            "dry_run": args.dry_run,
            "icons": uv_mappings,
        }

        color = ConsoleColor(stream=sys.stdout)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            dry_str = color.yellow(" [DRY-RUN]") if args.dry_run else ""
            status_tag = color.green("[✓]")
            print(f"{status_tag} Successfully generated icon atlas mapping for '{mod_slug}'{dry_str}:")
            print(f"    Target File: {icons_lsx_file}")
            print(f"    Atlas Path: Assets/Textures/Icons/{atlas_name}.dds ({args.atlas_size}x{args.atlas_size})")
            print(f"    Mapped Icons: {len(uv_mappings)}")
            for m in uv_mappings[:10]:
                print(f"      • {m['name']:<30} -> U:[{m['u1']}, {m['u2']}] V:[{m['v1']}, {m['v2']}]")
            if len(uv_mappings) > 10:
                print(f"      ... and {len(uv_mappings) - 10} more.")

        return ExitCode.SUCCESS

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            err_color = ConsoleColor(stream=sys.stderr)
            print(f"{err_color.red('[ERROR]')} {e}", file=sys.stderr)
        return ExitCode.GENERAL


if __name__ == "__main__":
    sys.exit(main())
