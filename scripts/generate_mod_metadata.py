#!/usr/bin/env python3
"""
generate_mod_metadata.py
------------------------
Analyzes custom Baldur's Gate 3 mod files (stats, localizations, and meta.lsx)
to generate rich publication-ready descriptions, changelogs, feature tables,
and recommended tags for the official Baldur's Gate 3 Toolkit and mod.io.

Features:
- Resolves localization handles (h...;1) from Localization/English/*.xml to in-game text
- Parses Larian stats syntax for Spells, Passives, Statuses, Weapons, and Armor
- Formats rich Markdown and BBCode mod descriptions ready to copy-paste into the Toolkit
- Recommends categorized tags (Classes, Spells, Equipment, Tweaks) for the publishing window
- Emits structured JSON summary for subagent consumption
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MY_MODS_DIR = WORKSPACE_ROOT / "my_mods"


def find_mod_dir(mod_query: str) -> Path:
    if not MY_MODS_DIR.exists():
        raise FileNotFoundError(f"my_mods directory does not exist at {MY_MODS_DIR}")

    candidates = [d for d in MY_MODS_DIR.iterdir() if d.is_dir()]
    query_norm = mod_query.strip().lower().replace("-", "").replace("_", "")
    for d in candidates:
        if query_norm in d.name.lower().replace("-", "").replace("_", ""):
            return d
    raise ValueError(f"No mod found in my_mods/ matching query '{mod_query}'.")


def load_localization_strings(mod_dir: Path) -> dict[str, str]:
    """Parse Localization/English/*.xml to map contentuid -> text."""
    strings = {}
    loc_dir = mod_dir / "Localization" / "English"
    if not loc_dir.exists():
        return strings

    for xml_file in loc_dir.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            for content in root.findall(".//content"):
                uid = content.get("contentuid", "").strip()
                text = (content.text or "").strip()
                if uid:
                    strings[uid] = text
        except Exception:
            pass
    return strings


def parse_meta_lsx(mod_dir: Path) -> dict:
    """Extract metadata (name, author, description, uuid, version, dependencies) from meta.lsx."""
    meta_files = list(mod_dir.glob("Mods/*/meta.lsx")) or list(mod_dir.glob("Projects/*/meta.lsx"))
    if not meta_files:
        return {}

    content = meta_files[0].read_text(encoding="utf-8")
    meta = {
        "name": "",
        "author": "",
        "description": "",
        "uuid": "",
        "version64": 0,
        "dependencies": [],
    }

    # ModuleInfo
    mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
    if mod_info:
        info_block = mod_info.group(1)
        name_m = re.search(r'<attribute\s+id="Name"\s+type="LSString"\s+value="([^"]*)"', info_block)
        auth_m = re.search(r'<attribute\s+id="Author"\s+type="LSString"\s+value="([^"]*)"', info_block)
        desc_m = re.search(r'<attribute\s+id="Description"\s+type="LSString"\s+value="([^"]*)"', info_block)
        uuid_m = re.search(r'<attribute\s+id="UUID"\s+type="FixedString"\s+value="([^"]*)"', info_block)
        ver_m = re.search(r'<attribute\s+id="Version64"\s+type="int64"\s+value="(\d+)"', info_block)

        if name_m:
            meta["name"] = name_m.group(1)
        if auth_m:
            meta["author"] = auth_m.group(1)
        if desc_m:
            meta["description"] = desc_m.group(1)
        if uuid_m:
            meta["uuid"] = uuid_m.group(1)
        if ver_m:
            meta["version64"] = int(ver_m.group(1))

    # Dependencies
    deps_block = re.search(r'<node\s+id="Dependencies">(.*?)</node>\s*<node\s+id="ModuleInfo">', content, re.DOTALL)
    if deps_block:
        for dep in re.finditer(r'<node\s+id="ModuleShortDesc">(.*?)</node>', deps_block.group(1), re.DOTALL):
            dep_text = dep.group(1)
            dname = re.search(r'<attribute\s+id="Name"\s+type="LSString"\s+value="([^"]*)"', dep_text)
            duuid = re.search(r'<attribute\s+id="UUID"\s+type="guid"\s+value="([^"]*)"', dep_text)
            if dname:
                meta["dependencies"].append({
                    "name": dname.group(1),
                    "uuid": duuid.group(1) if duuid else "",
                })

    return meta


def parse_stats_file(file_path: Path) -> list[dict]:
    """Parse standard Larian stats text files into structured entries."""
    if not file_path.exists():
        return []

    entries = []
    current_entry = None

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            entry_match = re.match(r'^new\s+entry\s+"([^"]+)"', line)
            if entry_match:
                if current_entry:
                    entries.append(current_entry)
                current_entry = {
                    "name": entry_match.group(1),
                    "file": file_path.name,
                    "type": "",
                    "data": {},
                }
                continue

            type_match = re.match(r'^type\s+"([^"]+)"', line)
            if type_match and current_entry:
                current_entry["type"] = type_match.group(1)
                continue

            using_match = re.match(r'^using\s+"([^"]+)"', line)
            if using_match and current_entry:
                current_entry["using"] = using_match.group(1)
                continue

            data_match = re.match(r'^data\s+"([^"]+)"\s+"([^"]*)"', line)
            if data_match and current_entry:
                key, val = data_match.group(1), data_match.group(2)
                current_entry["data"][key] = val

    if current_entry:
        entries.append(current_entry)

    return entries


def resolve_handle(handle_str: str, strings_map: dict[str, str]) -> str:
    """Extract uuid portion of handle (h<UUID>;<ver>) and resolve to string."""
    if not handle_str:
        return ""
    clean = handle_str.split(";")[0].strip()
    return strings_map.get(clean, "")


def collect_mod_features(mod_dir: Path, strings_map: dict[str, str]) -> dict:
    """Scan all stats files in Public/*/Stats/Generated/Data/."""
    features = {
        "spells": [],
        "passives": [],
        "statuses": [],
        "items": [],
        "other": [],
    }

    stats_dirs = list(mod_dir.glob("Public/*/Stats/Generated/Data"))
    if not stats_dirs:
        return features

    stats_dir = stats_dirs[0]
    for txt_file in stats_dir.glob("*.txt"):
        entries = parse_stats_file(txt_file)
        for e in entries:
            name = e["name"]
            data = e["data"]
            disp_h = data.get("DisplayName", "")
            desc_h = data.get("Description", "")
            disp_name = resolve_handle(disp_h, strings_map) or name
            desc_text = resolve_handle(desc_h, strings_map)

            item_info = {
                "id": name,
                "display_name": disp_name,
                "description": desc_text,
                "file": e["file"],
                "type": e.get("type", ""),
                "data": data,
            }

            fname = txt_file.name.lower()
            if "spell" in fname:
                features["spells"].append(item_info)
            elif "passive" in fname:
                features["passives"].append(item_info)
            elif "status" in fname:
                features["statuses"].append(item_info)
            elif any(k in fname for k in ["weapon", "armor", "object"]):
                features["items"].append(item_info)
            else:
                features["other"].append(item_info)

    return features


def suggest_tags(meta: dict, features: dict) -> list[str]:
    """Recommend BG3 Toolkit tags based on mod contents."""
    tags = set()
    if features["classes"] if "classes" in features else False:
        tags.add("Classes")
    if features["spells"]:
        tags.add("Spells")
    if features["items"]:
        tags.add("Equipment")
    if features["passives"]:
        tags.add("Combat")

    for dep in meta.get("dependencies", []):
        if "unlocklevelcurve" in dep["name"].lower():
            tags.add("Progression")

    if not tags:
        tags.add("Tweaks")
    return sorted(list(tags))


def generate_markdown_description(meta: dict, features: dict, tags: list[str]) -> str:
    lines = []
    name = meta.get("name") or "Baldur's Gate 3 Mod"
    desc = meta.get("description") or "A custom modification for Baldur's Gate 3."
    author = meta.get("author") or "Unknown"

    lines.append(f"# {name}")
    lines.append(f"**Author:** {author}")
    lines.append("")
    lines.append("## Overview")
    lines.append(desc)
    lines.append("")

    # Features Overview
    lines.append("## Features Included")
    if features["spells"]:
        lines.append("### Spells & Actions")
        lines.append("| Spell Name | Type | Level | Description |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for s in features["spells"]:
            s_type = s["data"].get("SpellType", s["type"])
            s_level = s["data"].get("Level", "Cantrip" if s_type == "Target" else "-")
            lines.append(f"| **{s['display_name']}** | {s_type} | {s_level} | {s['description'] or s['id']} |")
        lines.append("")

    if features["passives"]:
        lines.append("### Passives & Traits")
        lines.append("| Passive Name | Boosts / Properties | Description |")
        lines.append("| :--- | :--- | :--- |")
        for p in features["passives"]:
            boosts = p["data"].get("Boosts", "-")
            lines.append(f"| **{p['display_name']}** | `{boosts}` | {p['description'] or p['id']} |")
        lines.append("")

    if features["items"]:
        lines.append("### Items & Equipment")
        lines.append("| Item Name | Rarity | Default Boosts | Description |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for it in features["items"]:
            rarity = it["data"].get("Rarity", "Common")
            boosts = it["data"].get("DefaultBoosts", "-")
            lines.append(f"| **{it['display_name']}** | {rarity} | `{boosts}` | {it['description'] or it['id']} |")
        lines.append("")

    # Dependencies & Load Order
    lines.append("## Dependencies & Load Order")
    deps = meta.get("dependencies", [])
    if deps:
        lines.append("This mod requires the following parent dependencies to be loaded before it:")
        for d in deps:
            lines.append(f"- **{d['name']}** (`{d['uuid']}`)")
    else:
        lines.append("No external mod dependencies required (native compatibility).")
    lines.append("")

    # Recommended Tags
    lines.append("## Recommended Toolkit Tags")
    lines.append(f"`{', '.join(tags)}`")
    lines.append("")

    return "\n".join(lines)


def generate_bbcode_description(meta: dict, features: dict, tags: list[str]) -> str:
    lines = []
    name = meta.get("name") or "Baldur's Gate 3 Mod"
    desc = meta.get("description") or "A custom modification for Baldur's Gate 3."
    author = meta.get("author") or "Unknown"

    lines.append(f"[b][size=5]{name}[/size][/b]")
    lines.append(f"[i]Created by {author}[/i]\n")
    lines.append("[b][size=4]Overview[/size][/b]")
    lines.append(f"{desc}\n")

    if features["spells"]:
        lines.append("[b][size=4]Spells & Actions[/size][/b]")
        lines.append("[list]")
        for s in features["spells"]:
            lines.append(f"[*] [b]{s['display_name']}[/b] - {s['description'] or s['id']}")
        lines.append("[/list]\n")

    if features["passives"]:
        lines.append("[b][size=4]Passives & Traits[/size][/b]")
        lines.append("[list]")
        for p in features["passives"]:
            lines.append(f"[*] [b]{p['display_name']}[/b] - {p['description'] or p['id']}")
        lines.append("[/list]\n")

    if features["items"]:
        lines.append("[b][size=4]Equipment[/size][/b]")
        lines.append("[list]")
        for it in features["items"]:
            rarity = it["data"].get("Rarity", "Common")
            lines.append(f"[*] [b]{it['display_name']}[/b] ({rarity}) - {it['description'] or it['id']}")
        lines.append("[/list]\n")

    lines.append("[b][size=4]Dependencies[/size][/b]")
    deps = meta.get("dependencies", [])
    if deps:
        lines.append("[list]")
        for d in deps:
            lines.append(f"[*] [b]{d['name']}[/b]")
        lines.append("[/list]\n")
    else:
        lines.append("None required.\n")

    lines.append(f"[b]Tags:[/b] {', '.join(tags)}")
    return "\n".join(lines)


def process_mod_metadata(mod_query: str, output_format: str = "all", write_files: bool = False, as_json: bool = False):
    mod_dir = find_mod_dir(mod_query)
    strings_map = load_localization_strings(mod_dir)
    meta = parse_meta_lsx(mod_dir)
    features = collect_mod_features(mod_dir, strings_map)
    tags = suggest_tags(meta, features)

    md_content = generate_markdown_description(meta, features, tags)
    bbcode_content = generate_bbcode_description(meta, features, tags)

    result = {
        "mod_name": meta.get("name") or mod_dir.name,
        "mod_dir": str(mod_dir.relative_to(WORKSPACE_ROOT)),
        "author": meta.get("author", ""),
        "uuid": meta.get("uuid", ""),
        "version64": meta.get("version64", 0),
        "dependencies": meta.get("dependencies", []),
        "counts": {
            "spells": len(features["spells"]),
            "passives": len(features["passives"]),
            "statuses": len(features["statuses"]),
            "items": len(features["items"]),
        },
        "suggested_tags": tags,
    }

    if write_files:
        md_file = mod_dir / "modio_description.md"
        bb_file = mod_dir / "modio_description.bbcode"
        md_file.write_text(md_content, encoding="utf-8")
        bb_file.write_text(bbcode_content, encoding="utf-8")
        result["written_files"] = [str(md_file.relative_to(WORKSPACE_ROOT)), str(bb_file.relative_to(WORKSPACE_ROOT))]
        print(f"✓ Generated {md_file.relative_to(WORKSPACE_ROOT)}")
        print(f"✓ Generated {bb_file.relative_to(WORKSPACE_ROOT)}")

    if as_json:
        print(json.dumps(result, indent=2))
    elif not write_files:
        if output_format in ("md", "all"):
            print(md_content)
        if output_format == "bbcode":
            print(bbcode_content)


def main():
    parser = argparse.ArgumentParser(
        description="Extract and format publication metadata for BG3 mods for the Toolkit & mod.io."
    )
    parser.add_argument("--mod", required=True, help="Mod name or directory in my_mods/ (e.g. arcane-progression)")
    parser.add_argument("--format", choices=["md", "bbcode", "all"], default="all", help="Output format (default: all)")
    parser.add_argument("--write", action="store_true", help="Write description files directly to mod folder")
    parser.add_argument("--json", action="store_true", help="Output metadata and summary counts as JSON")

    args = parser.parse_args()

    try:
        process_mod_metadata(
            mod_query=args.mod,
            output_format=args.format,
            write_files=args.write,
            as_json=args.json,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
