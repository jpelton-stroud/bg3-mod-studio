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
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import (
    get_authored_mods_dir,
    resolve_mod_dir,
)
from bg3_core.larian_parsers import HANDLE_PATTERN, has_balanced_parens

# Zero-dependency ANSI Terminal Colors honoring NO_COLOR
_color = ConsoleColor(stream=sys.stderr)
GREEN = "\033[32m" if _color.enabled else ""
YELLOW = "\033[33m" if _color.enabled else ""
RED = "\033[31m" if _color.enabled else ""
CYAN = "\033[36m" if _color.enabled else ""
BOLD = "\033[1m" if _color.enabled else ""
RESET = "\033[0m" if _color.enabled else ""


class ModValidator:
    def __init__(self, mod_dir: Path, strict: bool = False) -> None:
        self.mod_dir = mod_dir
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.meta_projects: dict[str, Any] = {}
        self.meta_mods: dict[str, Any] = {}
        self.defined_handles: set[str] = set()
        self.referenced_handles: set[str] = set()
        self.defined_spells: set[str] = set()
        self.defined_root_templates: set[str] = set()

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def validate_directory_structure(self) -> None:
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

    def validate_xml_syntax(self) -> None:
        for p in self.mod_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".xml", ".lsx"):
                try:
                    ET.parse(p)
                except ET.ParseError as e:
                    rel = p.relative_to(self.mod_dir)
                    self.add_error(f"Malformed XML in '{rel}': line {e.position[0]}, col {e.position[1]}: {e}")

    def parse_meta(self, meta_file: Path) -> dict[str, Any]:
        data: dict[str, Any] = {
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

    def validate_metadata_parity(self) -> None:
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

    def validate_localization_handles(self) -> None:
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

        # 2. Extract handles referenced across Stats/*.txt, RootTemplates/*.lsx, and Progressions/*.lsx
        stats_dirs = list(self.mod_dir.glob("Public/*/Stats/Generated/Data"))
        for sdir in stats_dirs:
            for txt_file in sdir.glob("*.txt"):
                try:
                    content = txt_file.read_text(encoding="utf-8", errors="replace")
                    for line in content.splitlines():
                        line = line.strip()
                        if not line or line.startswith("//"):
                            continue
                        if line.startswith("data "):
                            for match in HANDLE_PATTERN.finditer(line):
                                h = match.group(1)
                                self.referenced_handles.add(h)
                                if h not in self.defined_handles:
                                    self.add_error(
                                        f"Missing localization handle '{h}' in {txt_file.name} (not found in English XML)."
                                    )
                except Exception as e:
                    self.add_warning(f"Could not read {txt_file.name}: {e}")

        # Scan all LSX files under Public/ for TranslatedString handles
        lsx_targets = list(self.mod_dir.glob("Public/**/*.lsx"))
        for lsx_file in lsx_targets:
            try:
                content = lsx_file.read_text(encoding="utf-8", errors="replace")
                for match in HANDLE_PATTERN.finditer(content):
                    h = match.group(1)
                    self.referenced_handles.add(h)
                    if h not in self.defined_handles:
                        self.add_error(
                            f"Missing localization handle '{h}' in {lsx_file.name} (not found in English XML)."
                        )
            except Exception as e:
                self.add_warning(f"Could not read {lsx_file.name}: {e}")

        # Also collect any handles referenced in Mods/*/meta.lsx or Projects/*/meta.lsx
        for meta_file in list(self.mod_dir.glob("Mods/*/meta.lsx")) + list(self.mod_dir.glob("Projects/*/meta.lsx")):
            try:
                content = meta_file.read_text(encoding="utf-8", errors="replace")
                for match in HANDLE_PATTERN.finditer(content):
                    self.referenced_handles.add(match.group(1))
            except Exception:
                pass

        # 3. Warn on orphan handles in Localization/English/*.xml
        orphans = self.defined_handles - self.referenced_handles
        if orphans:
            self.add_warning(
                f"{len(orphans)} orphaned localization handle(s) in English XML not referenced in Stats/LSX "
                f"(run 'sync_localization.py --mod {self.mod_dir.name} --prune' to clean)."
            )

    def validate_stats_and_templates(self) -> None:
        # 1. Collect defined RootTemplate MapKey UUIDs in Public/*/RootTemplates/*.lsx
        for rt_file in self.mod_dir.glob("Public/*/RootTemplates/*.lsx"):
            try:
                tree = ET.parse(rt_file)
                for node in tree.findall(".//node[@id='GameObjects']"):
                    for attr in node.findall("attribute[@id='MapKey']"):
                        val = attr.get("value", "").strip()
                        if val:
                            self.defined_root_templates.add(val)
            except Exception:
                pass

        # 2. Validate RootTemplate references & balanced functor parentheses in Stats/*.txt
        guid_re = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        paren_keys = {"Boosts", "DefaultBoosts", "PassivesOnEquip", "SpellProperties", "StatsFunctors", "OnEquipFunctors"}
        data_re = re.compile(r'^data\s+"([^"]+)"\s+"(.*)"$')

        for sdir in self.mod_dir.glob("Public/*/Stats/Generated/Data"):
            for txt_file in sdir.glob("*.txt"):
                try:
                    lines = txt_file.read_text(encoding="utf-8", errors="replace").splitlines()
                    for idx, raw_line in enumerate(lines, 1):
                        line = raw_line.strip()
                        if not line or line.startswith("//"):
                            continue
                        m = data_re.match(line)
                        if not m:
                            continue
                        key, val = m.group(1), m.group(2)
                        if key in paren_keys and val and not has_balanced_parens(val):
                            self.add_error(
                                f"Unbalanced parentheses in {txt_file.name}:{idx} data \"{key}\": '{val}'"
                            )
                        if key == "RootTemplate" and val:
                            if not guid_re.match(val):
                                self.add_error(
                                    f"Invalid RootTemplate UUID format in {txt_file.name}:{idx}: '{val}'"
                                )
                            elif self.defined_root_templates and val not in self.defined_root_templates:
                                self.add_warning(
                                    f"RootTemplate '{val}' in {txt_file.name}:{idx} is not defined in local RootTemplates/*.lsx (ensure it is a valid vanilla template)."
                                )
                except Exception:
                    pass

    def validate_spell_references(self) -> None:
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

    def validate_image_asset(self, img_path: Path, label: str) -> None:
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

    def validate_assets(self) -> None:
        # Larian standard:
        # Projects/<ModFolder>/thumbnail.png (512x512 or 1024x1024)
        # Mods/<ModFolder>/mod_publish_logo.png (512x512 or 1024x1024)
        for d in (self.mod_dir / "Projects").glob("*"):
            if d.is_dir():
                self.validate_image_asset(d / "thumbnail.png", "Projects thumbnail")

        for d in (self.mod_dir / "Mods").glob("*"):
            if d.is_dir():
                self.validate_image_asset(d / "mod_publish_logo.png", "Mods publish logo")

    def validate_companion_schemas(self) -> None:
        # 1. Feats.lsx vs Feats/FeatDescriptions.lsx
        feat_files = list(self.mod_dir.glob("Public/*/Feats/Feats.lsx"))
        feat_desc_files = list(self.mod_dir.glob("Public/*/Feats/FeatDescriptions.lsx"))
        if feat_files:
            feat_uuids = set()
            for ff in feat_files:
                try:
                    tree = ET.parse(ff)
                    for node in tree.findall(".//node[@id='Feat']"):
                        for attr in node.findall("attribute[@id='UUID']"):
                            val = attr.get("value", "").strip()
                            if val:
                                feat_uuids.add(val)
                except Exception as e:
                    self.add_error(f"Error parsing Feats.lsx: {e}")

            if feat_uuids and not feat_desc_files:
                self.add_warning("Feats.lsx defines feats but companion FeatDescriptions.lsx is missing.")
            elif feat_desc_files:
                desc_feat_ids = set()
                for fdf in feat_desc_files:
                    try:
                        tree = ET.parse(fdf)
                        for node in tree.findall(".//node[@id='FeatDescription']"):
                            for attr in node.findall("attribute[@id='FeatId']"):
                                val = attr.get("value", "").strip()
                                if val:
                                    desc_feat_ids.add(val)
                    except Exception as e:
                        self.add_error(f"Error parsing FeatDescriptions.lsx: {e}")
                missing_descs = feat_uuids - desc_feat_ids
                if missing_descs:
                    self.add_warning(
                        f"{len(missing_descs)} feat(s) defined in Feats.lsx lack companion FeatDescriptions."
                    )

        # 2. Races.lsx vs Races/RaceDescriptions.lsx
        race_files = list(self.mod_dir.glob("Public/*/Races/Races.lsx"))
        race_desc_files = list(self.mod_dir.glob("Public/*/Races/RaceDescriptions.lsx"))
        if race_files:
            race_uuids = set()
            for rf in race_files:
                try:
                    tree = ET.parse(rf)
                    for node in tree.findall(".//node[@id='Race']"):
                        for attr in node.findall("attribute[@id='UUID']"):
                            val = attr.get("value", "").strip()
                            if val:
                                race_uuids.add(val)
                except Exception as e:
                    self.add_error(f"Error parsing Races.lsx: {e}")

            if race_uuids and not race_desc_files:
                self.add_warning("Races.lsx defines races but companion RaceDescriptions.lsx is missing.")
            elif race_desc_files:
                desc_race_ids = set()
                for rdf in race_desc_files:
                    try:
                        tree = ET.parse(rdf)
                        for node in tree.findall(".//node[@id='RaceDescription']"):
                            for attr in node.findall("attribute[@id='RaceId']"):
                                val = attr.get("value", "").strip()
                                if val:
                                    desc_race_ids.add(val)
                    except Exception as e:
                        self.add_error(f"Error parsing RaceDescriptions.lsx: {e}")
                missing_descs = race_uuids - desc_race_ids
                if missing_descs:
                    self.add_warning(
                        f"{len(missing_descs)} race(s) defined in Races.lsx lack companion RaceDescriptions."
                    )

    def run(self) -> dict:
        self.validate_directory_structure()
        self.validate_xml_syntax()
        self.validate_metadata_parity()
        self.validate_localization_handles()
        self.validate_stats_and_templates()
        self.validate_spell_references()
        self.validate_companion_schemas()
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic static validator and linter for BG3 mods.")
    parser.add_argument("mod_pos", nargs="?", help="Specific mod name, slug, or directory path to validate (positional)")
    parser.add_argument("--mod", help="Specific mod name, slug, or directory path to validate")
    parser.add_argument("--all", action="store_true", help="Validate all custom mods in my_mods/")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    targets: list[Path] = []
    selected_mod = args.mod or args.mod_pos
    if selected_mod and not args.all:
        try:
            resolved = resolve_mod_dir(selected_mod, prefer_my_mods=True)
            if resolved is None:
                print(f"Error: No mod found matching '{selected_mod}'.", file=sys.stderr)
                sys.exit(ExitCode.NOINPUT)
            targets.append(resolved)
        except FileNotFoundError:
            print(f"Error: No mod found matching '{selected_mod}'.", file=sys.stderr)
            sys.exit(ExitCode.NOINPUT)
    else:
        authored_dir = get_authored_mods_dir()
        if not authored_dir.exists():
            print(f"Error: {authored_dir} does not exist.", file=sys.stderr)
            sys.exit(1)
        targets = sorted([d for d in authored_dir.iterdir() if d.is_dir()])

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
        sys.exit(ExitCode.DATAERR)
    sys.exit(ExitCode.OK)


if __name__ == "__main__":
    main()
