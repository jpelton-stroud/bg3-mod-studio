#!/usr/bin/env python3
"""
scripts/add_mod_dependency.py
-----------------------------
Appends community or core mod dependencies and test dependencies to an existing custom mod in my_mods/.

Features:
- Resolves dependency metadata (UUID, Version64, MD5, Folder, Name, PublishHandle)
  via local mods/library.md before falling back to mod.io.
- Injects standard Larian v4.8 ModuleShortDesc nodes into Mods/*/meta.lsx.
- Updates mod README.md under ## Dependencies.
- Supports adding both permanent dependencies and test dependencies in a single invocation.
- Supports multiple comma-separated mod slugs or repeated CLI flags.
- Supports --test-only (with values or as a flag) and --test-dep flags to manage test dependencies in .test_deps.json.
- Supports target mod detection via --mod, positional argument, or current working directory.
- Supports --dry-run and structured --json output.
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bg3_core.env_paths import MY_MODS_DIR, resolve_mod_dir
from bg3_core.mod_resolver import resolve_dependency_metadata


def detect_mod_from_cwd() -> Optional[str]:
    """Detects mod name if the current working directory is inside a mod in MY_MODS_DIR."""
    try:
        cwd = Path.cwd().resolve()
        my_mods = MY_MODS_DIR.resolve()
        rel = cwd.relative_to(my_mods)
        if rel.parts:
            return rel.parts[0]
    except Exception:
        pass
    return None


def parse_slug_list(values: Any) -> List[str]:
    """Parses a list of CLI values which may contain comma-separated mod slugs."""
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    slugs: List[str] = []
    for val in values:
        if isinstance(val, str):
            for part in val.split(","):
                cleaned = part.strip()
                if cleaned and cleaned not in slugs:
                    slugs.append(cleaned)
    return slugs


def add_test_dependencies(mod_dir: Path, dep_metas: List[Dict[str, Any]], dry_run: bool = False) -> List[Dict[str, Any]]:
    """Adds temporary test dependencies to .test_deps.json in the mod workspace."""
    config_file = mod_dir / ".test_deps.json"
    data: Dict[str, Any] = {"test_dependencies": []}
    if config_file.is_file():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            if "test_dependencies" not in data or not isinstance(data["test_dependencies"], list):
                data["test_dependencies"] = []
        except Exception:
            data = {"test_dependencies": []}

    existing = [str(d).lower() for d in data["test_dependencies"]]
    results: List[Dict[str, Any]] = []
    modified = False

    for dep_meta in dep_metas:
        dep_name = dep_meta.get("Name") or dep_meta.get("Folder") or dep_meta.get("UUID") or "Unknown"
        dep_identifier = dep_meta.get("Folder") or dep_name

        if dep_name.lower() in existing or dep_identifier.lower() in existing:
            results.append({
                "status": "already_present",
                "mod": mod_dir.name,
                "type": "test_dependency",
                "dependency": dep_name,
                "config_file": str(config_file),
            })
            continue

        data["test_dependencies"].append(dep_name)
        existing.append(dep_name.lower())
        existing.append(dep_identifier.lower())
        modified = True

        results.append({
            "status": "added_test_dependency",
            "mod": mod_dir.name,
            "type": "test_dependency",
            "dependency": dep_name,
            "uuid": dep_meta.get("UUID"),
            "config_file": str(config_file),
            "dry_run": dry_run,
        })

    if modified and not dry_run:
        config_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return results


def add_test_dependency(mod_dir: Path, dep_meta: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Single-dependency wrapper for add_test_dependencies."""
    res = add_test_dependencies(mod_dir, [dep_meta], dry_run=dry_run)
    return res[0] if res else {}


def add_permanent_dependencies(mod_dir: Path, dep_metas: List[Dict[str, Any]], dry_run: bool = False) -> List[Dict[str, Any]]:
    """Injects dependency ModuleShortDesc nodes into meta.lsx and updates README.md."""
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

    existing_uuids = set()
    for short_desc in children.findall("node[@id='ModuleShortDesc']"):
        u_attr = short_desc.find("attribute[@id='UUID']")
        if u_attr is not None and u_attr.get("value"):
            existing_uuids.add(u_attr.get("value", "").lower())

    results: List[Dict[str, Any]] = []
    meta_modified = False
    new_readme_entries: List[Tuple[Dict[str, Any], str]] = []

    for dep_meta in dep_metas:
        dep_uuid = (dep_meta.get("UUID") or "").lower()
        if dep_uuid and dep_uuid in existing_uuids:
            results.append({
                "status": "already_present",
                "mod": mod_dir.name,
                "type": "permanent_dependency",
                "dependency": dep_meta.get("Name"),
                "uuid": dep_meta.get("UUID"),
                "file": str(target_meta),
            })
            continue

        # Construct new ModuleShortDesc node
        new_desc = ET.Element("node", id="ModuleShortDesc")
        ET.SubElement(new_desc, "attribute", id="Folder", type="LSString", value=dep_meta.get("Folder", dep_meta.get("Name", "")))
        ET.SubElement(new_desc, "attribute", id="MD5", type="LSString", value=dep_meta.get("MD5", ""))
        ET.SubElement(new_desc, "attribute", id="Name", type="LSString", value=dep_meta.get("Name", ""))
        ET.SubElement(new_desc, "attribute", id="PublishHandle", type="uint64", value=str(dep_meta.get("PublishHandle", 0)))
        ET.SubElement(new_desc, "attribute", id="UUID", type="guid", value=dep_meta.get("UUID", ""))
        ET.SubElement(new_desc, "attribute", id="Version64", type="int64", value=str(dep_meta.get("Version64", 36028797018963968)))

        children.append(new_desc)
        if dep_uuid:
            existing_uuids.add(dep_uuid)
        meta_modified = True

        dep_entry = f"- `{dep_meta.get('Name')}` (`{dep_meta.get('UUID')}`)"
        new_readme_entries.append((dep_meta, dep_entry))

        results.append({
            "status": "added_dependency",
            "mod": mod_dir.name,
            "type": "permanent_dependency",
            "dependency": dep_meta.get("Name"),
            "uuid": dep_meta.get("UUID"),
            "folder": dep_meta.get("Folder"),
            "publish_handle": dep_meta.get("PublishHandle"),
            "meta_file": str(target_meta),
            "readme_updated": False,
            "dry_run": dry_run,
        })

    if meta_modified and not dry_run:
        ET.indent(tree, space="    ")
        tree.write(target_meta, encoding="utf-8", xml_declaration=True)

    # Update README.md if present
    readme_path = mod_dir / "README.md"
    readme_updated = False
    if readme_path.is_file() and new_readme_entries:
        readme_txt = readme_path.read_text(encoding="utf-8")
        unlisted = [e for e in new_readme_entries if e[0].get("UUID") and e[0]["UUID"] not in readme_txt]
        if unlisted and "## Dependencies" in readme_txt:
            entries_block = "\n".join(e[1] for e in unlisted)
            if re.search(r"## Dependencies\s*\n\s*- None\.", readme_txt):
                readme_txt = re.sub(r"(## Dependencies\s*\n)\s*- None\.", r"\1" + entries_block, readme_txt)
            else:
                readme_txt = re.sub(r"(## Dependencies\s*\n)", r"\1" + entries_block + "\n", readme_txt)
            readme_updated = True
            if not dry_run:
                readme_path.write_text(readme_txt, encoding="utf-8")

        for r in results:
            if r.get("status") == "added_dependency":
                r["readme_updated"] = readme_updated

    return results


def add_permanent_dependency(mod_dir: Path, dep_meta: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """Single-dependency wrapper for add_permanent_dependencies."""
    res = add_permanent_dependencies(mod_dir, [dep_meta], dry_run=dry_run)
    return res[0] if res else {}


def resolve_cli_targets(args: argparse.Namespace) -> Tuple[List[str], List[str]]:
    """
    Categorizes CLI input into permanent dependencies and test dependencies.
    Supports comma-separated slugs, repeated flags, --test-dep, and --test-only as flag or value.
    """
    perm_slugs: List[str] = []
    test_slugs: List[str] = []

    # 1. Parse explicit --test-dep / --test-deps values
    if getattr(args, "test_dep", None):
        test_slugs.extend(parse_slug_list(args.test_dep))

    # 2. Parse --test-only
    raw_test_only = getattr(args, "test_only", [])
    has_test_only_flag = any(v is True for v in raw_test_only)
    test_only_values = parse_slug_list([v for v in raw_test_only if isinstance(v, str)])
    if test_only_values:
        test_slugs.extend(test_only_values)

    # 3. Parse --dep / --dependency
    raw_dep = getattr(args, "dep", [])
    dep_slugs = parse_slug_list(raw_dep)

    # If --test-only was passed as a bare flag without slug values:
    # route --dep values to test dependencies (preserves backward compatibility)
    if has_test_only_flag and not test_only_values:
        test_slugs.extend(dep_slugs)
    else:
        perm_slugs.extend(dep_slugs)

    # Remove duplicates preserving order
    dedup_perm: List[str] = []
    for s in perm_slugs:
        if s not in dedup_perm:
            dedup_perm.append(s)

    dedup_test: List[str] = []
    for s in test_slugs:
        if s not in dedup_test:
            dedup_test.append(s)

    return dedup_perm, dedup_test


def main():
    parser = argparse.ArgumentParser(
        description="Add community or core mod dependencies and test dependencies to an existing custom mod in my_mods/."
    )
    parser.add_argument("pos_mod", nargs="?", default=None, help="Target mod name or slug (optional if --mod is specified)")
    parser.add_argument("--mod", default=None, help="Custom mod name, slug, or folder in my_mods/")
    parser.add_argument("--dep", "--dependency", dest="dep", action="append", default=[], help="Dependency mod name(s), slug(s), or UUID(s) (comma-separated or repeated)")
    parser.add_argument("--test-dep", "--test-deps", dest="test_dep", action="append", default=[], help="Test dependency mod name(s), slug(s), or UUID(s) (comma-separated or repeated)")
    parser.add_argument(
        "--test-only",
        dest="test_only",
        nargs="?",
        const=True,
        action="append",
        default=[],
        help="Add as test dependency in .test_deps.json. Can be a bare flag or take comma-separated mod slug(s)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON result")

    args = parser.parse_args()

    try:
        target_mod = args.mod or args.pos_mod or detect_mod_from_cwd()
        if not target_mod:
            raise ValueError("Target mod must be specified via --mod <name>, positional argument, or by running inside a mod folder in my_mods/.")

        mod_dir = resolve_mod_dir(target_mod, prefer_my_mods=True)
        if not mod_dir or not mod_dir.is_dir():
            raise FileNotFoundError(f"Could not locate mod directory for '{target_mod}'.")

        perm_slugs, test_slugs = resolve_cli_targets(args)
        if not perm_slugs and not test_slugs:
            raise ValueError("No dependencies specified. Provide dependency mod slugs via --dep, --test-dep, or --test-only.")

        perm_results: List[Dict[str, Any]] = []
        if perm_slugs:
            perm_metas = [
                resolve_dependency_metadata(slug, auto_document=True, strict=True)
                for slug in perm_slugs
            ]
            perm_results = add_permanent_dependencies(mod_dir, perm_metas, dry_run=args.dry_run)

        test_results: List[Dict[str, Any]] = []
        if test_slugs:
            test_metas = [
                resolve_dependency_metadata(slug, auto_document=True, strict=False)
                for slug in test_slugs
            ]
            test_results = add_test_dependencies(mod_dir, test_metas, dry_run=args.dry_run)

        all_results = perm_results + test_results
        success = True

        if args.json:
            response: Dict[str, Any] = {
                "mod": mod_dir.name,
                "status": "success",
                "dependencies": perm_results,
                "test_dependencies": test_results,
                "results": all_results,
                "success": success,
                "dry_run": args.dry_run,
            }
            if len(all_results) == 1:
                single = all_results[0]
                for k, v in single.items():
                    if k not in response:
                        response[k] = v
                response["status"] = single.get("status", "success")
            print(json.dumps(response, indent=2))
        else:
            verb = "[DRY-RUN] Would add" if args.dry_run else "Successfully added"
            for r in all_results:
                dep_name = r.get("dependency") or r.get("uuid") or "Unknown"
                status = r.get("status")
                dep_kind = "test dependency" if r.get("type") == "test_dependency" else "dependency"
                if status == "already_present":
                    print(f"• {dep_kind.capitalize()} '{dep_name}' is already present in '{r.get('mod')}'.")
                else:
                    print(f"✓ {verb} {dep_kind} '{dep_name}' to '{r.get('mod')}'.")
                if r.get("uuid"):
                    print(f"  UUID: {r.get('uuid')}")
                if r.get("meta_file"):
                    print(f"  Updated: {r.get('meta_file')}")
                elif r.get("config_file") and status != "already_present":
                    print(f"  Updated: {r.get('config_file')}")

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
