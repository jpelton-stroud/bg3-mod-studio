#!/usr/bin/env python3
"""
create_mod_scaffold.py
----------------------
Generates a standard Baldur's Gate 3 mod project scaffold under `my_mods/<ModSlug>` with internal Larian structures under `<ModName>_<UUID>`.

Features:
- Generates valid UUIDv4 for module identity and pre-allocated localization handles
- Calculates Larian Version64 integers (major.minor.revision.build)
- Emits standard Larian v4.8 engine metadata (meta.lsx) for Projects/ and Mods/
- Configures dependencies (GustavDev default, UnlockLevelCurve, etc.)
- Scaffolds complete directory structure: Projects, Mods, Public, Localization
- Generates clean 512x512 placeholder PNG thumbnail and logo assets (pure stdlib)
- Emits structured JSON summary for subagent consumption
"""

import argparse
import json
import os
import re
import struct
import sys
import uuid
import zlib
from pathlib import Path


# Known common dependencies for BG3 (Patch 8)
KNOWN_DEPENDENCIES = {
    "GustavX": {
        "Folder": "GustavX",
        "MD5": "ef3fcba3f3684b3088ad1f9874d4957c",
        "Name": "GustavX",
        "PublishHandle": 0,
        "UUID": "cb555efe-2d9e-131f-8195-a89329d218ea",
        "Version64": 145241946983300916,
    },
    "GustavDev": {
        "Folder": "GustavDev",
        "MD5": "33c1655f7ae3559b579ff3b9d2c45413",
        "Name": "GustavDev",
        "PublishHandle": 0,
        "UUID": "28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8",
        "Version64": 145100393449790344,
    },
    "UnlockLevelCurve": {
        "Folder": "UnlockLevelCurve_a2ffd0e4-c407-8642-2611-c934ea0b0a77",
        "MD5": "f94d034502139cf8b65a1597554e7236",
        "Name": "UnlockLevelCurve",
        "PublishHandle": 4166963,
        "UUID": "a2ffd0e4-c407-8642-2611-c934ea0b0a77",
        "Version64": 72057594037927960,
    },
}


def sanitize_mod_name(name: str) -> str:
    """Removes non-alphanumeric characters and converts to PascalCase/CamelCase."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", name.strip())
    if not cleaned:
        raise ValueError(f"Invalid mod name: '{name}'. Must contain alphanumeric characters.")
    return cleaned


def slugify_mod_name(name: str) -> str:
    """
    Converts PascalCase, CamelCase, or spaced/underscored names to a clean kebab-case slug.
    Example: 'EldritchApotheosis' -> 'eldritch-apotheosis'
             'PactOfTheBladeUnleashed' -> 'pact-of-the-blade-unleashed'
             'Paladins_Call' -> 'paladins-call'
    """
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name.strip())
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s)
    slug = s.lower().strip("-")
    if not slug:
        raise ValueError(f"Unable to generate valid slug from '{name}'.")
    return slug


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_handle() -> str:
    """Generates a standard Larian localization handle (h...g...g...g...g...)."""
    u_str = str(uuid.uuid4()).replace("-", "g")
    return f"h{u_str}"


def calculate_version64(major: int = 1, minor: int = 0, revision: int = 0, build: int = 0) -> int:
    """
    Encodes major.minor.revision.build into Larian's 64-bit version integer:
    - major: bits 55..63 (9 bits)
    - minor: bits 47..54 (8 bits)
    - revision: bits 31..46 (16 bits)
    - build: bits 0..30 (31 bits)
    """
    return (major << 55) | (minor << 47) | (revision << 31) | (build & 0x7FFFFFFF)


def generate_png_bytes(width: int = 512, height: int = 512, r: int = 45, g: int = 52, b: int = 64) -> bytes:
    """Generates a minimal valid uncompressed RGB PNG using standard library zlib."""
    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = make_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))

    # Raw scanlines: each line starts with filter byte 0 (None) followed by RGB bytes
    row = b"\x00" + bytes([r, g, b]) * width
    raw_data = row * height
    compressed = zlib.compress(raw_data, level=6)
    idat = make_chunk(b"IDAT", compressed)
    iend = make_chunk(b"IEND", b"")

    return header + ihdr + idat + iend


def build_project_meta_lsx_content(
    mod_name: str,
    mod_uuid: str,
    project_uuid: str,
    game_project: str = "Gustav",
    mod_type: str = "Add-on",
) -> str:
    """
    Builds the official Baldur's Gate 3 Toolkit project meta.lsx (<region id="MetaData">).
    This descriptor is scanned by the Toolkit Project Browser to discover editable projects.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="500"/>
    <region id="MetaData">
        <node id="root">
            <attribute id="GameProject" type="LSString" value="{game_project}"/>
            <attribute id="Module" type="LSString" value="{mod_uuid}"/>
            <attribute id="Name" type="LSString" value="{mod_name}"/>
            <attribute id="Type" type="LSString" value="{mod_type}"/>
            <attribute id="UUID" type="LSString" value="{project_uuid}"/>
            <children>
                <node id="Categories"/>
            </children>
        </node>
    </region>
</save>
"""


def build_meta_lsx_content(
    mod_name: str,
    mod_uuid: str,
    folder_name: str,
    author: str,
    description: str,
    version64: int,
    dependencies: list,
) -> str:
    dep_nodes = []
    for dep in dependencies:
        dep_node = f"""                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="{dep.get('Folder', dep.get('Name'))}"/>
                            <attribute id="MD5" type="LSString" value="{dep.get('MD5', '')}"/>
                            <attribute id="Name" type="LSString" value="{dep.get('Name')}"/>
                            <attribute id="PublishHandle" type="uint64" value="{dep.get('PublishHandle', 0)}"/>
                            <attribute id="UUID" type="guid" value="{dep.get('UUID')}"/>
                            <attribute id="Version64" type="int64" value="{dep.get('Version64', 0)}"/>
                        </node>"""
        dep_nodes.append(dep_node)

    dep_xml = "\n".join(dep_nodes)

    # Escape description for XML
    desc_escaped = (
        description.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="500"/>
    <region id="Config">
        <node id="root">
            <children>
                <node id="Conflicts"/>
                <node id="Dependencies">
                    <children>
{dep_xml}
                    </children>
                </node>
                <node id="ModuleInfo">
                    <attribute id="Author" type="LSString" value="{author}"/>
                    <attribute id="CharacterCreationLevelName" type="FixedString" value=""/>
                    <attribute id="Description" type="LSString" value="{desc_escaped}"/>
                    <attribute id="FileSize" type="uint64" value="0"/>
                    <attribute id="Folder" type="LSString" value="{folder_name}"/>
                    <attribute id="LobbyLevelName" type="FixedString" value=""/>
                    <attribute id="MD5" type="LSString" value=""/>
                    <attribute id="MenuLevelName" type="FixedString" value=""/>
                    <attribute id="Name" type="LSString" value="{mod_name}"/>
                    <attribute id="NumPlayers" type="uint8" value="4"/>
                    <attribute id="PhotoBooth" type="FixedString" value=""/>
                    <attribute id="PublishHandle" type="uint64" value="0"/>
                    <attribute id="StartupLevelName" type="FixedString" value=""/>
                    <attribute id="UUID" type="FixedString" value="{mod_uuid}"/>
                    <attribute id="Version64" type="int64" value="{version64}"/>
                    <children>
                        <node id="PublishVersion">
                            <attribute id="Version64" type="int64" value="144255927717549775"/>
                        </node>
                        <node id="Scripts"/>
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>
"""


def build_localization_xml(mod_name: str, placeholder_handles: list) -> str:
    entries = []
    for h in placeholder_handles:
        entries.append(f'  <content contentuid="{h}" version="1">{mod_name} Display Name</content>')
    entries_str = "\n".join(entries) if entries else ""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<contentList xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
{entries_str}
</contentList>
"""


def build_readme_content(
    mod_name: str,
    mod_uuid: str,
    folder_name: str,
    mod_slug: str,
    author: str,
    description: str,
    dependencies: list,
) -> str:
    dep_list_str = "\n".join(f"- `{d.get('Name')}` ({d.get('UUID')})" for d in dependencies)
    return f"""# {mod_name}
**Module UUID**: `{mod_uuid}`  
**Mod Slug**: `{mod_slug}`  
**Larian Folder**: `{folder_name}`  
**Author**: `{author}`  
**Toolkit Target**: Patch 7 / Patch 8 Native Toolkit Drag-and-Drop Structure

---

## Overview
{description}

---

## Dependencies
{dep_list_str}

---

## Installation & Toolkit Import

### Method 1: Automatic Sync (Recommended)
Sync mod files directly into your Baldur's Gate 3 `Data/` folder using:
```bash
python3 scripts/sync_to_game_data.py --mods {mod_slug}
```

### Method 2: Manual Toolkit Workspace Import
1. Locate your game's **Data** directory (typically `.../Baldurs Gate 3/Data/`).
2. Copy the folders from this mod directory directly into `Data/`:
   - `Projects/`
   - `Mods/`
   - `Public/`
   - `Localization/`
3. Launch the **Baldur's Gate 3 Toolkit**.
4. Click **File -> Open Project...** and select **{mod_name}**.
5. Save and Publish!

---

## Features & Implementation
*(To be detailed by mod authors and subagents)*
"""


def scaffold_mod(
    name: str,
    mod_uuid: str = None,
    mod_slug: str = None,
    author: str = None,
    description: str = "",
    version_str: str = "1.0.0.0",
    dependencies: list = None,
    output_dir: Path = Path("my_mods"),
    dry_run: bool = False,
) -> dict:
    clean_name = sanitize_mod_name(name)
    if not mod_uuid:
        mod_uuid = generate_uuid()

    if not mod_slug:
        mod_slug = slugify_mod_name(name)

    env_vars = load_env_defaults()
    if not author:
        author = os.environ.get("BG3_MOD_AUTHOR") or env_vars.get("BG3_MOD_AUTHOR") or "MTGHillGiant"

    larian_folder = f"{clean_name}_{mod_uuid}"
    mod_root = output_dir / mod_slug

    # Parse version
    v_parts = [int(p) for p in (version_str.split(".") + [0, 0, 0, 0])[:4]]
    version64 = calculate_version64(*v_parts)

    # Dependencies: default to GustavX (Patch 8 base game module) unless GustavDev requested
    base_dep = "GustavDev" if (dependencies and "GustavDev" in dependencies) else "GustavX"
    resolved_deps = [KNOWN_DEPENDENCIES[base_dep]]
    if dependencies:
        for dep in dependencies:
            if dep in ("GustavX", "GustavDev"):
                continue
            if dep in KNOWN_DEPENDENCIES:
                resolved_deps.append(KNOWN_DEPENDENCIES[dep])
            elif isinstance(dep, dict) and "UUID" in dep:
                resolved_deps.append(dep)
            else:
                # Custom named dependency fallback
                resolved_deps.append({
                    "Folder": str(dep),
                    "MD5": "",
                    "Name": str(dep),
                    "PublishHandle": 0,
                    "UUID": generate_uuid(),
                    "Version64": 36028797018963968,
                })

    if not description:
        description = f"{clean_name}: Custom mod for Baldur's Gate 3."

    # Directories
    projects_dir = mod_root / "Projects" / larian_folder
    mods_dir = mod_root / "Mods" / larian_folder
    public_dir = mod_root / "Public" / larian_folder
    editor_dir = mod_root / "Editor" / "Mods" / larian_folder / "Assets"
    stats_dir = public_dir / "Stats" / "Generated" / "Data"
    progressions_dir = public_dir / "Progressions"
    lists_dir = public_dir / "Lists"
    loc_dir = mod_root / "Localization" / "English"

    created_dirs = [
        projects_dir,
        mods_dir,
        public_dir,
        editor_dir,
        stats_dir,
        progressions_dir,
        lists_dir,
        loc_dir,
    ]

    # Pre-allocate 10 standard handles for subagents
    allocated_handles = [generate_handle() for _ in range(10)]

    # File contents
    project_uuid = generate_uuid()
    project_meta_xml = build_project_meta_lsx_content(
        mod_name=clean_name,
        mod_uuid=mod_uuid,
        project_uuid=project_uuid,
    )
    meta_xml = build_meta_lsx_content(
        mod_name=clean_name,
        mod_uuid=mod_uuid,
        folder_name=larian_folder,
        author=author,
        description=description,
        version64=version64,
        dependencies=resolved_deps,
    )
    loc_xml = build_localization_xml(clean_name, allocated_handles[:2])
    readme_md = build_readme_content(clean_name, mod_uuid, larian_folder, mod_slug, author, description, resolved_deps)
    png_data = generate_png_bytes(512, 512, 45, 52, 64)

    files_to_write = {
        projects_dir / "meta.lsx": project_meta_xml.encode("utf-8"),
        projects_dir / "thumbnail.png": png_data,
        mods_dir / "meta.lsx": meta_xml.encode("utf-8"),
        mods_dir / "mod_publish_logo.png": png_data,
        editor_dir / ".gitkeep": b"",
        loc_dir / f"{clean_name}.xml": loc_xml.encode("utf-8"),
        mod_root / "README.md": readme_md.encode("utf-8"),
        mod_root / "thumbnail.png": png_data,
    }

    if not dry_run:
        for d in created_dirs:
            d.mkdir(parents=True, exist_ok=True)
        for filepath, content in files_to_write.items():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(content)

    return {
        "name": clean_name,
        "uuid": mod_uuid,
        "project_uuid": project_uuid,
        "mod_slug": mod_slug,
        "folder_name": larian_folder,
        "larian_folder": larian_folder,
        "root_dir": str(mod_root),
        "projects_dir": str(projects_dir),
        "mods_dir": str(mods_dir),
        "public_dir": str(public_dir),
        "stats_dir": str(stats_dir),
        "progressions_dir": str(progressions_dir),
        "lists_dir": str(lists_dir),
        "localization_file": str(loc_dir / f"{clean_name}.xml"),
        "readme_file": str(mod_root / "README.md"),
        "allocated_handles": allocated_handles,
        "dependencies": [d["Name"] for d in resolved_deps],
    }


def load_env_defaults() -> dict:
    """Load key-value pairs from .env if present."""
    env = {}
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass
    return env


def main():
    env_vars = load_env_defaults()
    default_author = os.environ.get("BG3_MOD_AUTHOR") or env_vars.get("BG3_MOD_AUTHOR") or "MTGHillGiant"

    parser = argparse.ArgumentParser(description="Scaffold a new Baldur's Gate 3 mod directory under my_mods/")
    parser.add_argument("--name", required=True, help="Mod name (PascalCase/CamelCase, e.g. ArcaneProgression)")
    parser.add_argument("--slug", default=None, help="Main folder slug under my_mods/ (e.g. arcane-progression; auto-generated if omitted)")
    parser.add_argument("--uuid", default=None, help="Specific UUIDv4 (auto-generated if omitted)")
    parser.add_argument("--author", default=default_author, help=f"Mod author name (default: {default_author})")
    parser.add_argument("--description", default="", help="Mod description")
    parser.add_argument("--version", default="1.0.0.0", help="Mod version string (default: 1.0.0.0)")
    parser.add_argument(
        "--unlock-level-curve",
        action="store_true",
        help="Include UnlockLevelCurve as a parent dependency",
    )
    parser.add_argument(
        "--dependency",
        action="append",
        dest="dependencies",
        default=[],
        help="Additional dependency name(s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("my_mods"),
        help="Base directory for mods (default: my_mods)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files to disk")
    parser.add_argument("--json", action="store_true", help="Output JSON result to stdout")

    args = parser.parse_args()

    deps = list(args.dependencies)
    if args.unlock_level_curve and "UnlockLevelCurve" not in deps:
        deps.append("UnlockLevelCurve")

    result = scaffold_mod(
        name=args.name,
        mod_uuid=args.uuid,
        mod_slug=args.slug,
        author=args.author,
        description=args.description,
        version_str=args.version,
        dependencies=deps,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n Mod scaffold successfully created for '{result['name']}':")
        print(f"  UUID:           {result['uuid']}")
        print(f"  Mod Slug:       {result['mod_slug']}")
        print(f"  Larian Folder:  {result['larian_folder']}")
        print(f"  Author:         {args.author}")
        print(f"  Root Dir:       {result['root_dir']}")
        print(f"  Dependencies:   {', '.join(result['dependencies'])}")
        print(f"  Allocated Handles: {len(result['allocated_handles'])} handles ready for localization")
        print(f"\nReady to build assets in: {result['public_dir']}")


if __name__ == "__main__":
    main()
