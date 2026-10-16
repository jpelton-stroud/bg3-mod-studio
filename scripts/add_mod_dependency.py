#!/usr/bin/env python3
"""
scripts/add_mod_dependency.py
-----------------------------
Appends a community or core mod dependency to an existing custom mod in my_mods/.

Features:
- Resolves dependency metadata (UUID, Version64, MD5, Folder, Name, PublishHandle)
  via local mods/library.md before falling back to mod.io.
- Injects standard Larian v4.8 ModuleShortDesc nodes into Mods/*/meta.lsx.
- Updates mod README.md under ## Dependencies.
- Supports --test-only flag to manage test dependencies in .test_deps.json.
- Supports --dry-run and structured --json output.
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib.env_paths import MY_MODS_DIR, resolve_mod_dir
from scripts.lib.mod_resolver import resolve_dependency_metadata


def add_test_dependency(mod_dir: Path, dep_meta: dict, dry_run: bool = False) -> dict:
    """Adds a temporary test dependency to .test_deps.json in the mod workspace."""
    config_file = mod_dir / ".test_deps.json"
    data = {"test_dependencies": []}
    if config_file.is_file():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            if "test_dependencies" not in data or not isinstance(data["test_dependencies"], list):
                data["test_dependencies"] = []
        except Exception:
            data = {"test_dependencies": []}

    dep_name = dep_meta.get("Name") or dep_meta.get("Folder") or dep_meta.get("UUID")
    dep_identifier = dep_meta.get("Folder") or dep_name

    existing = [d.lower() for d in data["test_dependencies"]]
    if dep_name.lower() in existing or dep_identifier.lower() in existing:
        return {
            "status": "already_present",
            "mod": mod_dir.name,
            "type": "test_dependency",
            "dependency": dep_name,
            "config_file": str(config_file),
        }

    data["test_dependencies"].append(dep_name)

    if not dry_run:
        config_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return {
        "status": "added_test_dependency",
        "mod": mod_dir.name,
        "type": "test_dependency",
        "dependency": dep_name,
        "uuid": dep_meta.get("UUID"),
        "config_file": str(config_file),
        "dry_run": dry_run,
    }


def add_permanent_dependency(mod_dir: Path, dep_meta: dict, dry_run: bool = False) -> dict:
    """Injects dependency ModuleShortDesc into meta.lsx and updates README.md."""
    meta_files = list(mod_dir.glob("Mods/*/meta.lsx"))
    if not meta_files:
        raise FileNotFoundError(f"Could not locate Mods/*/meta.lsx in '{mod_dir}'.")

    target_meta = meta_files[0]
    tree = ET.parse(target_meta)
    root = tree.getroot()

    # Find or create Dependencies node
    deps_node = root.find(".//node[@id='Dependencies']")
    if deps_node is None:
        root_node = root.find(".//node[@id='root']/children")
        if root_node is None:
            raise ValueError(f"Malformed meta.lsx in '{target_meta}': missing root children.")
        deps_node = ET.SubElement(root_node, "node", id="Dependencies")

    children = deps_node.find("children")
    if children is None:
        children = ET.SubElement(deps_node, "children")

    dep_uuid = dep_meta["UUID"].lower()
    for short_desc in children.findall("node[@id='ModuleShortDesc']"):
        u_attr = short_desc.find("attribute[@id='UUID']")
        if u_attr is not None and u_attr.get("value", "").lower() == dep_uuid:
            return {
                "status": "already_present",
                "mod": mod_dir.name,
                "type": "permanent_dependency",
                "dependency": dep_meta.get("Name"),
                "uuid": dep_meta["UUID"],
                "file": str(target_meta),
            }

    # Construct new ModuleShortDesc node
    new_desc = ET.Element("node", id="ModuleShortDesc")
    ET.SubElement(new_desc, "attribute", id="Folder", type="LSString", value=dep_meta.get("Folder", dep_meta.get("Name")))
    ET.SubElement(new_desc, "attribute", id="MD5", type="LSString", value=dep_meta.get("MD5", ""))
    ET.SubElement(new_desc, "attribute", id="Name", type="LSString", value=dep_meta.get("Name", ""))
    ET.SubElement(new_desc, "attribute", id="PublishHandle", type="uint64", value=str(dep_meta.get("PublishHandle", 0)))
    ET.SubElement(new_desc, "attribute", id="UUID", type="guid", value=dep_meta["UUID"])
    ET.SubElement(new_desc, "attribute", id="Version64", type="int64", value=str(dep_meta.get("Version64", 36028797018963968)))

    children.append(new_desc)

    # Indent XML cleanly
    ET.indent(tree, space="    ")

    if not dry_run:
        tree.write(target_meta, encoding="utf-8", xml_declaration=True)

    # Update README.md if present
    readme_path = mod_dir / "README.md"
    readme_updated = False
    if readme_path.is_file():
        readme_txt = readme_path.read_text(encoding="utf-8")
        dep_entry = f"- `{dep_meta.get('Name')}` (`{dep_meta.get('UUID')}`)"
        if dep_meta["UUID"] not in readme_txt:
            if "## Dependencies" in readme_txt:
                # Replace "- None." if present or append to list
                if re.search(r"## Dependencies\s*\n\s*- None\.", readme_txt):
                    readme_txt = re.sub(r"(## Dependencies\s*\n)\s*- None\.", r"\1" + dep_entry, readme_txt)
                else:
                    readme_txt = re.sub(r"(## Dependencies\s*\n)", r"\1" + dep_entry + "\n", readme_txt)
                readme_updated = True
                if not dry_run:
                    readme_path.write_text(readme_txt, encoding="utf-8")

    return {
        "status": "added_dependency",
        "mod": mod_dir.name,
        "type": "permanent_dependency",
        "dependency": dep_meta.get("Name"),
        "uuid": dep_meta["UUID"],
        "folder": dep_meta.get("Folder"),
        "publish_handle": dep_meta.get("PublishHandle"),
        "meta_file": str(target_meta),
        "readme_updated": readme_updated,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Add a community or core mod dependency to an existing custom mod in my_mods/."
    )
    parser.add_argument("--mod", required=True, help="Custom mod name, slug, or folder in my_mods/")
    parser.add_argument("--dep", "--dependency", dest="dep", required=True, help="Dependency mod name, slug, or UUID")
    parser.add_argument("--test-only", action="store_true", help="Add as a temporary test dependency (.test_deps.json) instead of meta.lsx")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON result")

    args = parser.parse_args()

    try:
        mod_dir = resolve_mod_dir(args.mod, prefer_my_mods=True)
        if not mod_dir or not mod_dir.is_dir():
            raise FileNotFoundError(f"Could not locate mod directory for '{args.mod}'.")

        dep_meta = resolve_dependency_metadata(args.dep, auto_document=True, strict=not args.test_only)

        if args.test_only:
            result = add_test_dependency(mod_dir, dep_meta, dry_run=args.dry_run)
        else:
            result = add_permanent_dependency(mod_dir, dep_meta, dry_run=args.dry_run)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            verb = "[DRY-RUN] Would add" if args.dry_run else "Successfully added"
            dep_type = "test dependency" if args.test_only else "dependency"
            print(f"✓ {verb} {dep_type} '{result.get('dependency')}' to '{result.get('mod')}'.")
            if result.get("uuid"):
                print(f"  UUID: {result.get('uuid')}")
            if result.get("meta_file"):
                print(f"  Updated: {result.get('meta_file')}")
            elif result.get("config_file"):
                print(f"  Updated: {result.get('config_file')}")

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
