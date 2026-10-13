#!/usr/bin/env python3
"""
validate_mod.py
---------------
Deterministic static linter and structural validator for Baldur's Gate 3 mods.

Checks performed:
1. Larian Directory Hierarchy (Projects/, Mods/, Public/, Localization/)
2. XML & LSX Syntax (well-formedness check across all XML/LSX files)
3. Metadata Integrity & Parity (UUID & Version64 match between Projects/ and Mods/ meta.lsx)
4. Localization Handle Consistency (referenced handles in stats exist in English/*.xml)
5. Spell List Cross-Reference (spells in SpellLists.lsx exist in stats or vanilla)
6. Asset Compliance (valid 512x512 PNG thumbnails and logos)
7. Global UUID Uniqueness across all workspace mods

Exits with 0 if valid, 1 if any errors are encountered.
"""

import argparse
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MY_MODS_DIR = WORKSPACE_ROOT / "my_mods"

# ANSI Colors
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


class ModValidator:
    def __init__(self, mod_dir: Path, strict: bool = False):
        self.mod_dir = mod_dir
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.meta_projects: dict = {}
        self.meta_mods: dict = {}
        self.defined_handles: set[str] = set()
        self.defined_spells: set[str] = set()

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def validate_directory_structure(self):
        proj_dir = self.mod_dir / "Projects"
        mods_dir = self.mod_dir / "Mods"
        pub_dir = self.mod_dir / "Public"
        loc_dir = self.mod_dir / "Localization"

        if not proj_dir.is_dir():
            self.add_error("Missing 'Projects/' directory.")
        if not mods_dir.is_dir():
            self.add_error("Missing 'Mods/' directory.")
        if not pub_dir.is_dir():
            self.add_error("Missing 'Public/' directory.")
        if not loc_dir.is_dir():
            self.add_warning("Missing 'Localization/' directory.")

    def validate_xml_syntax(self):
        for p in self.mod_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".xml", ".lsx"):
                try:
                    ET.parse(p)
                except ET.ParseError as e:
                    rel = p.relative_to(self.mod_dir)
                    self.add_error(f"Malformed XML in '{rel}': line {e.position[0]}, col {e.position[1]}: {e}")

    def parse_meta(self, meta_file: Path) -> dict:
        data = {
            "uuid": "",
            "version64": 0,
            "name": "",
            "author": "",
            "folder": "",
            "module": "",
            "type": "",
            "is_project": False,
        }
        if not meta_file.is_file():
            return data
        try:
            content = meta_file.read_text(encoding="utf-8")
            if '<region id="MetaData">' in content:
                data["is_project"] = True
                name = re.search(r'<attribute\s+id="Name"\s+type="LSString"\s+value="([^"]*)"', content)
                module = re.search(r'<attribute\s+id="Module"\s+type="LSString"\s+value="([^"]*)"', content)
                uuid_val = re.search(r'<attribute\s+id="UUID"\s+type="LSString"\s+value="([^"]*)"', content)
                mod_type = re.search(r'<attribute\s+id="Type"\s+type="LSString"\s+value="([^"]*)"', content)
                if name:
                    data["name"] = name.group(1)
                if module:
                    data["module"] = module.group(1)
                    data["uuid"] = module.group(1)
                if uuid_val:
                    data["project_uuid"] = uuid_val.group(1)
                if mod_type:
                    data["type"] = mod_type.group(1)
            else:
                mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
                target = mod_info.group(1) if mod_info else content

                name = re.search(r'<attribute\s+id="Name"\s+type="LSString"\s+value="([^"]*)"', target)
                author = re.search(r'<attribute\s+id="Author"\s+type="LSString"\s+value="([^"]*)"', target)
                uuid_val = re.search(r'<attribute\s+id="UUID"\s+type="(?:FixedString|guid|LSString)"\s+value="([^"]*)"', target)
                v64 = re.search(r'<attribute\s+id="Version64"\s+type="int64"\s+value="(\d+)"', target)
                folder = re.search(r'<attribute\s+id="Folder"\s+type="LSString"\s+value="([^"]*)"', target)

                if name:
                    data["name"] = name.group(1)
                if author:
                    data["author"] = author.group(1)
                if uuid_val:
                    data["uuid"] = uuid_val.group(1)
                if v64:
                    data["version64"] = int(v64.group(1))
                if folder:
                    data["folder"] = folder.group(1)
        except Exception as e:
            self.add_error(f"Failed to read metadata from {meta_file.name}: {e}")
        return data

    def validate_metadata_parity(self):
        proj_metas = list(self.mod_dir.glob("Projects/*/meta.lsx"))
        mods_metas = list(self.mod_dir.glob("Mods/*/meta.lsx"))

        if not proj_metas:
            self.add_error("No meta.lsx found under Projects/*/")
            return
        if not mods_metas:
            self.add_error("No meta.lsx found under Mods/*/")
            return

        self.meta_projects = self.parse_meta(proj_metas[0])
        self.meta_mods = self.parse_meta(mods_metas[0])

        if not self.meta_mods["uuid"]:
            self.add_error("Mods meta.lsx is missing UUID attribute.")

        if self.meta_projects["is_project"]:
            # Official Toolkit Project schema (<region id="MetaData">)
            if not self.meta_projects.get("module"):
                self.add_error("Projects meta.lsx is missing Module attribute.")
            elif self.meta_mods["uuid"] and self.meta_projects["module"] != self.meta_mods["uuid"]:
                self.add_error(
                    f"Module UUID mismatch between Projects ({self.meta_projects['module']}) and Mods ({self.meta_mods['uuid']})."
                )
            if not self.meta_projects["name"]:
                self.add_error("Mod Name in Projects meta.lsx is empty.")
            elif self.meta_mods["name"] and self.meta_projects["name"] != self.meta_mods["name"]:
                self.add_error(
                    f"Mod Name mismatch between Projects ({self.meta_projects['name']}) and Mods ({self.meta_mods['name']})."
                )

            # Check for <node id="Categories"/> required by Toolkit ls::DefaultObjectVisitor
            proj_content = proj_metas[0].read_text(encoding="utf-8", errors="ignore")
            if '<node id="Categories"' not in proj_content:
                self.add_error(
                    "Projects meta.lsx is missing '<node id=\"Categories\"/>', which causes Toolkit to fail loading the project."
                )
        else:
            # Legacy Config/ModuleInfo schema
            self.add_warning("Projects meta.lsx uses legacy Config schema instead of official Toolkit MetaData schema.")
            if not self.meta_projects["uuid"]:
                self.add_error("Projects meta.lsx is missing UUID attribute.")
            elif self.meta_mods["uuid"] and self.meta_projects["uuid"] != self.meta_mods["uuid"]:
                self.add_error(
                    f"UUID mismatch between Projects ({self.meta_projects['uuid']}) and Mods ({self.meta_mods['uuid']})."
                )
            if self.meta_projects["version64"] != self.meta_mods["version64"]:
                self.add_error(
                    f"Version64 mismatch between Projects ({self.meta_projects['version64']}) and Mods ({self.meta_mods['version64']})."
                )
            if not self.meta_projects["name"]:
                self.add_error("Mod Name in Projects meta.lsx is empty.")

    def validate_localization_handles(self):
        # 1. Collect all defined handles from Localization/English/*.xml
        loc_dir = self.mod_dir / "Localization" / "English"
        if loc_dir.is_dir():
            for xf in loc_dir.glob("*.xml"):
                try:
                    tree = ET.parse(xf)
                    for c in tree.findall(".//content"):
                        h = c.get("contentuid", "").strip()
                        if h:
                            self.defined_handles.add(h)
                except Exception:
                    pass

        # 2. Extract handles referenced in Stats/Generated/Data/*.txt
        stats_dirs = list(self.mod_dir.glob("Public/*/Stats/Generated/Data"))
        if not stats_dirs:
            return

        handle_pattern = re.compile(r'(h[0-9a-fA-F]{32}|h[a-zA-Z0-9_]{30,40})(?:;\d+)?')

        for txt_file in stats_dirs[0].glob("*.txt"):
            try:
                content = txt_file.read_text(encoding="utf-8", errors="replace")
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("//"):
                        continue
                    if 'data "DisplayName"' in line or 'data "Description"' in line or 'data "ExtraDescription"' in line:
                        for match in handle_pattern.finditer(line):
                            h = match.group(1)
                            if h not in self.defined_handles:
                                self.add_error(
                                    f"Missing localization handle '{h}' in {txt_file.name} (not found in English XML)."
                                )
            except Exception as e:
                self.add_warning(f"Could not read {txt_file.name}: {e}")

    def validate_spell_references(self):
        # 1. Collect spells defined in Stats/Generated/Data/Spell_*.txt
        stats_dirs = list(self.mod_dir.glob("Public/*/Stats/Generated/Data"))
        if stats_dirs:
            for s_file in stats_dirs[0].glob("Spell_*.txt"):
                try:
                    for line in s_file.read_text(encoding="utf-8", errors="replace").splitlines():
                        m = re.match(r'^new\s+entry\s+"([^"]+)"', line.strip())
                        if m:
                            self.defined_spells.add(m.group(1))
                except Exception:
                    pass

        # 2. Verify SpellLists.lsx
        spell_lists = list(self.mod_dir.glob("Public/*/Lists/SpellLists.lsx"))
        if spell_lists:
            try:
                tree = ET.parse(spell_lists[0])
                for attr in tree.findall(".//attribute[@id='Spells']"):
                    val = attr.get("value", "").strip()
                    if val:
                        spells = [s.strip() for s in val.split(";") if s.strip()]
                        for s in spells:
                            # If spell is custom (not standard vanilla prefix or known spell)
                            if s not in self.defined_spells:
                                # Provide warning if not found locally
                                self.add_warning(
                                    f"Spell '{s}' referenced in SpellLists.lsx is not defined locally in Spell_*.txt."
                                )
            except Exception as e:
                self.add_error(f"Error parsing SpellLists.lsx: {e}")

    def validate_image_asset(self, img_path: Path, label: str):
        if not img_path.is_file():
            self.add_warning(f"Missing {label} asset at {img_path.relative_to(self.mod_dir)}")
            return

        try:
            with open(img_path, "rb") as f:
                header = f.read(24)
                if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
                    self.add_error(f"{label} ({img_path.name}) is not a valid PNG file.")
                    return
                # IHDR width, height are bytes 16..24
                width, height = struct.unpack(">II", header[16:24])
                if width != height or width not in (512, 1024):
                    self.add_error(
                        f"{label} ({img_path.name}) must be square (512x512 or 1024x1024) pixels (found {width}x{height})."
                    )
        except Exception as e:
            self.add_error(f"Failed to validate PNG {img_path.name}: {e}")

    def validate_assets(self):
        # Larian standard:
        # Projects/<ModFolder>/thumbnail.png (512x512 or 1024x1024)
        # Mods/<ModFolder>/mod_publish_logo.png (512x512 or 1024x1024)
        for d in (self.mod_dir / "Projects").glob("*"):
            if d.is_dir():
                self.validate_image_asset(d / "thumbnail.png", "Projects thumbnail")

        for d in (self.mod_dir / "Mods").glob("*"):
            if d.is_dir():
                self.validate_image_asset(d / "mod_publish_logo.png", "Mods publish logo")

    def run(self) -> dict:
        self.validate_directory_structure()
        self.validate_xml_syntax()
        self.validate_metadata_parity()
        self.validate_localization_handles()
        self.validate_spell_references()
        self.validate_assets()

        status = "PASSED"
        if self.errors or (self.strict and self.warnings):
            status = "FAILED"

        return {
            "mod_name": self.mod_dir.name,
            "status": status,
            "uuid": self.meta_mods.get("uuid", "") or self.meta_projects.get("module", "") or self.meta_projects.get("uuid", ""),
            "version64": self.meta_mods.get("version64", 0) or self.meta_projects.get("version64", 0),
            "errors": self.errors,
            "warnings": self.warnings,
        }


def check_uuid_uniqueness(mod_dirs: list[Path]) -> list[str]:
    seen: dict[str, str] = {}
    dupes = []
    for md in mod_dirs:
        # Check Mods/*/meta.lsx first, fallback to Projects/*/meta.lsx
        target_metas = list(md.glob("Mods/*/meta.lsx")) or list(md.glob("Projects/*/meta.lsx"))
        for mf in target_metas:
            try:
                content = mf.read_text(encoding="utf-8")
                mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
                target = mod_info.group(1) if mod_info else content
                m = re.search(r'<attribute\s+id="(?:UUID|Module)"\s+type="(?:FixedString|guid|LSString)"\s+value="([^"]+)"', target)
                if m:
                    u = m.group(1)
                    if u in seen:
                        dupes.append(f"Duplicate UUID '{u}' shared by '{seen[u]}' and '{md.name}'.")
                    else:
                        seen[u] = md.name
            except Exception:
                pass
    return dupes


def main():
    parser = argparse.ArgumentParser(description="Deterministic static validator and linter for BG3 mods.")
    parser.add_argument("--mod", help="Specific mod name or folder in my_mods/ to validate")
    parser.add_argument("--all", action="store_true", help="Validate all custom mods in my_mods/")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    if not MY_MODS_DIR.exists():
        print(f"Error: {MY_MODS_DIR} does not exist.", file=sys.stderr)
        sys.exit(1)

    targets = []
    if args.mod:
        norm = args.mod.strip().lower().replace("-", "").replace("_", "")
        for d in MY_MODS_DIR.iterdir():
            if d.is_dir() and norm in d.name.lower().replace("-", "").replace("_", ""):
                targets.append(d)
        if not targets:
            print(f"Error: No mod found matching '{args.mod}'.", file=sys.stderr)
            sys.exit(1)
    else:
        targets = sorted([d for d in MY_MODS_DIR.iterdir() if d.is_dir()])

    results = []
    total_errors = 0
    total_warnings = 0

    # Cross-mod UUID collision check
    uuid_collisions = check_uuid_uniqueness(targets)

    for target in targets:
        validator = ModValidator(target, strict=args.strict)
        res = validator.run()
        if uuid_collisions:
            for c in uuid_collisions:
                if target.name in c:
                    res["errors"].append(c)
                    res["status"] = "FAILED"
        total_errors += len(res["errors"])
        total_warnings += len(res["warnings"])
        results.append(res)

    if args.json:
        output_payload = {
            "summary": {
                "mods_checked": len(targets),
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "all_passed": total_errors == 0 and (not args.strict or total_warnings == 0),
            },
            "results": results,
        }
        print(json.dumps(output_payload, indent=2))
    else:
        print(f"\n{BOLD}{CYAN}=== Baldur's Gate 3 Mod Validation Report ==={RESET}\n")
        for res in results:
            color = GREEN if res["status"] == "PASSED" else RED
            print(f"{BOLD}Mod:{RESET} {res['mod_name']} [{color}{res['status']}{RESET}]")
            if res["uuid"]:
                print(f"  UUID: {res['uuid']} | Version64: {res['version64']}")
            for err in res["errors"]:
                print(f"  {RED}✗ ERROR:{RESET} {err}")
            for warn in res["warnings"]:
                print(f"  {YELLOW}⚠ WARNING:{RESET} {warn}")
            if not res["errors"] and not res["warnings"]:
                print(f"  {GREEN}✓ All checks passed cleanly.{RESET}")
            print("")

        print(f"{BOLD}Summary:{RESET} {len(targets)} mods checked, {total_errors} errors, {total_warnings} warnings.")

    if total_errors > 0 or (args.strict and total_warnings > 0):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
