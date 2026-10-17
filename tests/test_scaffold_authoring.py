#!/usr/bin/env python3
"""
tests/test_scaffold_authoring.py
--------------------------------
Comprehensive unit and integration test suite for Baldur's Gate 3
Patch 8 authoring tools, Option A CLI suite (bg3 mod create, bg3 scaffold <asset>),
diagnostics validation, and conflict detection.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.larian_parsers import (
    PATCH_8_VERSION,
    format_patch8_lsx_header,
    generate_larian_handle,
    update_localization_xml,
)
from scripts.diagnostics.validate_mod import ModValidator
from scripts.diagnostics.check_mod_conflicts import compare_two_mods

BG3_CLI = REPO_ROOT / "scripts" / "bg3.py"


class TestPatch8Primitives(unittest.TestCase):
    """Test Larian Patch 8 handle generation, XML updating, and LSX headers."""

    def test_generate_larian_handle(self):
        h1 = generate_larian_handle()
        h2 = generate_larian_handle()
        self.assertTrue(h1.startswith("h"))
        self.assertTrue(h2.startswith("h"))
        self.assertEqual(len(h1), 37)  # 'h' + 36 char UUID (or 32 hex + 4 dashes)
        self.assertNotEqual(h1, h2)

    def test_format_patch8_lsx_header(self):
        header = format_patch8_lsx_header()
        self.assertEqual(
            header,
            f'<version major="{PATCH_8_VERSION["major"]}" minor="{PATCH_8_VERSION["minor"]}" revision="{PATCH_8_VERSION["revision"]}" build="{PATCH_8_VERSION["build"]}"/>',
        )

    def test_update_localization_xml(self):
        with tempfile.TemporaryDirectory() as td:
            loc_xml = Path(td) / "Test.xml"
            handle = generate_larian_handle()
            update_localization_xml(loc_xml, [(handle, "Test Value & Special <Chars>")])
            self.assertTrue(loc_xml.exists())

            # Parse to ensure valid XML
            tree = ET.parse(loc_xml)
            content_node = tree.find(".//content")
            self.assertIsNotNone(content_node)
            self.assertEqual(content_node.get("contentuid"), handle)
            self.assertEqual(content_node.text, "Test Value & Special <Chars>")


class TestScaffoldAuthoringIntegration(unittest.TestCase):
    """End-to-end authoring and Option A CLI tests."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="bg3_authoring_test_")
        self.test_path = Path(self.test_dir)
        self.mod_name = "TestAuthoringMod"
        self.mod_dir = self.test_path / "test-authoring-mod"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def run_cli(self, args: list[str]) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["BG3_MODS_DIR"] = str(self.test_path)
        return subprocess.run(
            [sys.executable, str(BG3_CLI)] + args,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_option_a_cli_and_scaffolding_pipeline(self):
        # 1. Test bg3 mod create
        res = self.run_cli([
            "mod", "create", self.mod_name,
            "--author", "Tester",
            "--description", "Test desc",
            "--output-dir", str(self.test_path),
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"mod create failed: {res.stderr}\n{res.stdout}")
        create_payload = json.loads(res.stdout)
        self.assertIn("uuid", create_payload)
        self.assertTrue(self.mod_dir.is_dir())
        folder = create_payload["folder_name"]
        pub_folder = self.mod_dir / "Public" / folder

        # Check Patch 8 header in meta.lsx
        meta_file = self.mod_dir / "Mods" / folder / "meta.lsx"
        self.assertTrue(meta_file.exists())
        meta_content = meta_file.read_text(encoding="utf-8")
        self.assertIn('version major="4" minor="8" revision="0" build="700"', meta_content)

        # 2. Test bg3 scaffold class
        res = self.run_cli([
            "scaffold", "class",
            "--mod", str(self.mod_dir),
            "--name", "BladeDancer",
            "--display-name", "Blade Dancer",
            "--parent-class", "rogue",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold class failed: {res.stderr}\n{res.stdout}")
        class_desc_file = pub_folder / "ClassDescriptions" / "ClassDescriptions.lsx"
        self.assertTrue(class_desc_file.exists())
        cd_tree = ET.parse(class_desc_file)
        self.assertIsNotNone(cd_tree.find(".//attribute[@id='Name'][@value='BladeDancer']"))

        # 3. Test bg3 scaffold feat
        res = self.run_cli([
            "scaffold", "feat",
            "--mod", str(self.mod_dir),
            "--name", "ArcanePrecision",
            "--display-name", "Arcane Precision",
            "--passives", "Arcane_Precision_Passive",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold feat failed: {res.stderr}")
        feat_file = pub_folder / "Feats" / "Feats.lsx"
        feat_desc_file = pub_folder / "Feats" / "FeatDescriptions.lsx"
        self.assertTrue(feat_file.exists())
        self.assertTrue(feat_desc_file.exists())

        # 4. Test bg3 scaffold action-resource
        res = self.run_cli([
            "scaffold", "action-resource",
            "--mod", str(self.mod_dir),
            "--name", "DanceCharges",
            "--display-name", "Dance Charges",
            "--replenish-type", "ShortRest",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold action-resource failed: {res.stderr}")
        res_file = pub_folder / "ActionResourceDefinitions" / "ActionResourceDefinitions.lsx"
        self.assertTrue(res_file.exists())

        # 5. Test bg3 scaffold spell-list
        res = self.run_cli([
            "scaffold", "spell-list",
            "--mod", str(self.mod_dir),
            "--spells", "Target_DanceStrike", "Target_ShadowStep",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold spell-list failed: {res.stderr}")
        sl_file = pub_folder / "Lists" / "SpellLists.lsx"
        self.assertTrue(sl_file.exists())

        # 6. Test bg3 scaffold level-map
        res = self.run_cli([
            "scaffold", "level-map",
            "--mod", str(self.mod_dir),
            "--name", "DanceDamage",
            "--levels", "1=1d4,5=1d6,11=1d8",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold level-map failed: {res.stderr}")
        lm_file = pub_folder / "LevelMapValues" / "LevelMapValues.lsx"
        self.assertTrue(lm_file.exists())

        # 7. Test bg3 scaffold default-values
        res = self.run_cli([
            "scaffold", "default-values",
            "--mod", str(self.mod_dir),
            "--class", "Rogue",
            "--abilities", "15,14,13,12,10,8",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold default-values failed: {res.stderr}")
        dv_file = pub_folder / "DefaultValues" / "Abilities.lsx"
        self.assertTrue(dv_file.exists())

        # 8. Test bg3 scaffold tag
        res = self.run_cli([
            "scaffold", "tag",
            "--mod", str(self.mod_dir),
            "--name", "BLADE_DANCER",
            "--display-name", "Blade Dancer",
            "--category", "Dialog",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold tag failed: {res.stderr}")
        tag_files = list((pub_folder / "Tags").glob("*.lsx"))
        self.assertTrue(len(tag_files) > 0)

        # 9. Test bg3 scaffold race
        res = self.run_cli([
            "scaffold", "race",
            "--mod", str(self.mod_dir),
            "--name", "MoonElf",
            "--display-name", "Moon Elf",
            "--parent-race", "elf",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold race failed: {res.stderr}")
        race_file = pub_folder / "Races" / "Races.lsx"
        race_desc_file = pub_folder / "Races" / "RaceDescriptions.lsx"
        self.assertTrue(race_file.exists())
        self.assertTrue(race_desc_file.exists())

        # 10. Test bg3 scaffold origin
        res = self.run_cli([
            "scaffold", "origin",
            "--mod", str(self.mod_dir),
            "--name", "Lyra",
            "--display-name", "Lyra",
            "--class-uuid", "rogue",
            "--race-uuid", "elf",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold origin failed: {res.stderr}")
        origin_file = pub_folder / "Origins" / "Origins.lsx"
        self.assertTrue(origin_file.exists())

        # 11. Test bg3 scaffold appearance-visual
        res = self.run_cli([
            "scaffold", "appearance-visual",
            "--mod", str(self.mod_dir),
            "--name", "CCAV_MoonElf_Hair",
            "--visual-resource", "22222222-3333-4444-5555-666666666666",
            "--race", "elf",
            "--slot", "Hair",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold appearance-visual failed: {res.stderr}")
        ccav_file = pub_folder / "CharacterCreation" / "CharacterCreationAppearanceVisuals.lsx"
        self.assertTrue(ccav_file.exists())

        # 12. Test expanded stat scaffolding (interrupt, equipment, character, spell_teleport)
        for stat_type, stat_name in [
            ("interrupt", "Interrupt_BladeParry"),
            ("equipment", "EQP_BladeDancer_Starter"),
            ("character", "CHR_BladeDancer_NPC"),
            ("spell_teleport", "Target_BladeStep"),
        ]:
            res = self.run_cli([
                "scaffold", "stat",
                "--mod", str(self.mod_dir),
                "--type", stat_type,
                "--name", stat_name,
                "--json",
            ])
            self.assertEqual(res.returncode, 0, f"scaffold stat {stat_type} failed: {res.stderr}")

        # 13. Test progression multiclass
        res = self.run_cli([
            "scaffold", "progression",
            "--mod", str(self.mod_dir),
            "--class", "Rogue",
            "--level", "1",
            "--multiclass",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"scaffold progression multiclass failed: {res.stderr}")
        prog_file = pub_folder / "Progressions" / "Progressions.lsx"
        self.assertTrue(prog_file.exists())
        prog_tree = ET.parse(prog_file)
        self.assertIsNotNone(prog_tree.find(".//node[@id='Progression']/attribute[@id='ProgressionType'][@value='2']"))

        # 14. Test bg3 mod scaffold forwarding alias
        res = self.run_cli([
            "mod", "scaffold", "spell-list",
            "--mod", str(self.mod_dir),
            "--passives", "Passive_A", "Passive_B",
            "--json",
        ])
        self.assertEqual(res.returncode, 0, f"mod scaffold forwarding failed: {res.stderr}")
        pass_file = pub_folder / "Lists" / "PassiveLists.lsx"
        self.assertTrue(pass_file.exists())

        # 15. Run deterministic static validator on the generated mod
        validator = ModValidator(self.mod_dir)
        val_result = validator.run()
        self.assertEqual(val_result["status"], "PASSED", f"Validator errors: {val_result['errors']}")


class TestDiagnosticsConflictDetection(unittest.TestCase):
    """Test diagnostics conflict detector across new Patch 8 schemas."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="bg3_conflict_test_")
        self.test_path = Path(self.test_dir)
        self.mod1 = self.test_path / "Mod1"
        self.mod2 = self.test_path / "Mod2"

        for m in (self.mod1, self.mod2):
            (m / "Mods" / m.name).mkdir(parents=True)
            (m / "Projects" / m.name).mkdir(parents=True)
            (m / "Public" / m.name).mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_detect_patch8_schema_collisions(self):
        # Create colliding ClassDescriptions
        for m in (self.mod1, self.mod2):
            cd_dir = m / "Public" / m.name / "ClassDescriptions"
            cd_dir.mkdir(parents=True)
            (cd_dir / "ClassDescriptions.lsx").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="ClassDescriptions">
        <node id="root">
            <children>
                <node id="ClassDescription">
                    <attribute id="Name" type="FixedString" value="CollidingClass"/>
                    <attribute id="UUID" type="guid" value="aaaa1111-2222-3333-4444-555555555555"/>
                </node>
            </children>
        </node>
    </region>
</save>""", encoding="utf-8")

            # Create colliding Feats
            f_dir = m / "Public" / m.name / "Feats"
            f_dir.mkdir(parents=True)
            (f_dir / "Feats.lsx").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Feats">
        <node id="root">
            <children>
                <node id="Feat">
                    <attribute id="Name" type="FixedString" value="CollidingFeat"/>
                    <attribute id="UUID" type="guid" value="bbbb1111-2222-3333-4444-555555555555"/>
                </node>
            </children>
        </node>
    </region>
</save>""", encoding="utf-8")

        res = compare_two_mods(self.mod1, self.mod2)
        self.assertTrue(res["has_conflicts"])
        self.assertEqual(len(res["class_collisions"]), 1)
        self.assertEqual(res["class_collisions"][0]["name"], "CollidingClass")
        self.assertEqual(len(res["feat_collisions"]), 1)
        self.assertEqual(res["feat_collisions"][0]["name"], "CollidingFeat")


if __name__ == "__main__":
    unittest.main()
