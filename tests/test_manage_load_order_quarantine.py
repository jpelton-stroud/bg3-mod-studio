"""
Unit tests for load order Patch 8 system module preservation,
physical .pak deduplication, clean-room quarantine, and restore.
"""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from bg3_core.lspk import build_lspk_archive as build_pak_archive
from bg3_core.manage_load_order import (
    CORE_SYSTEM_MODULES,
    _ensure_base_module,
    create_default_modsettings,
    deduplicate_installed_paks,
    disable_mod,
    enable_mod,
    isolate_load_order,
    parse_modsettings,
    quarantine_unrelated_paks,
    restore_quarantined_paks,
    validate_load_order,
)


def create_dummy_pak(path: Path, mod_name: str, mod_uuid: str, version64: int = 36028797018963968):
    """Helper to generate a minimal valid .pak archive with an internal meta.lsx."""
    meta_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Config">
        <node id="root">
            <children>
                <node id="Dependencies"/>
                <node id="ModuleInfo">
                    <attribute id="Folder" type="LSString" value="{mod_name}"/>
                    <attribute id="MD5" type="LSString" value=""/>
                    <attribute id="Name" type="LSString" value="{mod_name}"/>
                    <attribute id="PublishHandle" type="uint64" value="0"/>
                    <attribute id="UUID" type="FixedString" value="{mod_uuid}"/>
                    <attribute id="Version64" type="int64" value="{version64}"/>
                </node>
            </children>
        </node>
    </region>
</save>
"""
    files = [("Mods/" + mod_name + "/meta.lsx", meta_xml.encode("utf-8"))]
    pak_bytes = build_pak_archive(files)
    path.write_bytes(pak_bytes)


class TestManageLoadOrderQuarantine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name)
        self.modsettings_path = self.test_root / "PlayerProfiles" / "Public" / "modsettings.lsx"
        self.mods_dir = self.test_root / "Mods"
        self.mods_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_default_modsettings_contains_all_core_system_modules(self):
        create_default_modsettings(self.modsettings_path)
        self.assertTrue(self.modsettings_path.is_file())

        parsed = parse_modsettings(self.modsettings_path)
        for core_mod in CORE_SYSTEM_MODULES:
            uuid = core_mod["UUID"]
            self.assertIn(uuid, parsed["mods"], f"Missing core module {core_mod['Name']} ({uuid})")
            self.assertEqual(parsed["mods"][uuid]["Name"], core_mod["Name"])

        # Validation must pass without any missing core module issues
        issues = validate_load_order(parsed)
        self.assertEqual(issues, [])

    def test_ensure_base_module_injects_patch8_modules(self):
        # Create an incomplete modsettings with only GustavX and a custom mod
        custom_uuid = "11111111-2222-3333-4444-555555555555"
        incomplete_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="ModuleSettings">
        <node id="root">
            <children>
                <node id="Mods">
                    <children>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="GustavX"/>
                            <attribute id="MD5" type="LSString" value="ef3fcba3f3684b3088ad1f9874d4957c"/>
                            <attribute id="Name" type="LSString" value="GustavX"/>
                            <attribute id="PublishHandle" type="uint64" value="0"/>
                            <attribute id="UUID" type="guid" value="cb555efe-2d9e-131f-8195-a89329d218ea"/>
                            <attribute id="Version64" type="int64" value="145241946983300916"/>
                        </node>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="MyCustomMod"/>
                            <attribute id="MD5" type="LSString" value=""/>
                            <attribute id="Name" type="LSString" value="MyCustomMod"/>
                            <attribute id="PublishHandle" type="uint64" value="0"/>
                            <attribute id="UUID" type="guid" value="{custom_uuid}"/>
                            <attribute id="Version64" type="int64" value="36028797018963968"/>
                        </node>
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>
"""
        self.modsettings_path.parent.mkdir(parents=True, exist_ok=True)
        self.modsettings_path.write_text(incomplete_xml, encoding="utf-8")

        tree = ET.parse(self.modsettings_path)
        root = tree.getroot()
        mods_children = root.find(".//node[@id='Mods']/children")

        modified = _ensure_base_module(root, mods_children)
        self.assertTrue(modified)

        # Verify all core modules were inserted ahead of MyCustomMod
        descs = mods_children.findall("node[@id='ModuleShortDesc']")
        uuids_in_order = [d.find("attribute[@id='UUID']").get("value").lower() for d in descs]

        # First 9 must be the core system modules
        for idx, core in enumerate(CORE_SYSTEM_MODULES):
            self.assertEqual(uuids_in_order[idx], core["UUID"].lower())

        # The custom mod must remain at the end (index 9)
        self.assertEqual(uuids_in_order[len(CORE_SYSTEM_MODULES)], custom_uuid.lower())

    def test_isolate_load_order_preserves_core_system_modules(self):
        create_default_modsettings(self.modsettings_path)

        # Add two custom mods
        keep_mod = {
            "Folder": "TargetMod",
            "Name": "TargetMod",
            "UUID": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "Version64": "36028797018963968",
        }
        unrelated_mod = {
            "Folder": "UnrelatedMod",
            "Name": "UnrelatedMod",
            "UUID": "99999999-8888-7777-6666-555555555555",
            "Version64": "36028797018963968",
        }
        enable_mod(self.modsettings_path, keep_mod)
        enable_mod(self.modsettings_path, unrelated_mod)

        parsed_before = parse_modsettings(self.modsettings_path)
        self.assertIn(keep_mod["UUID"], parsed_before["mods"])
        self.assertIn(unrelated_mod["UUID"], parsed_before["mods"])

        # Run isolation keeping only TargetMod
        isolated_count = isolate_load_order(self.modsettings_path, {keep_mod["UUID"]})
        self.assertEqual(isolated_count, 1)

        parsed_after = parse_modsettings(self.modsettings_path)
        # Unrelated mod must be gone
        self.assertNotIn(unrelated_mod["UUID"], parsed_after["mods"])
        # Target mod must be present
        self.assertIn(keep_mod["UUID"], parsed_after["mods"])
        # ALL core system modules must still be present!
        for core in CORE_SYSTEM_MODULES:
            self.assertIn(core["UUID"], parsed_after["mods"])

    def test_disable_mod_forbids_disabling_core_modules(self):
        create_default_modsettings(self.modsettings_path)
        with self.assertRaises(ValueError) as ctx:
            disable_mod(self.modsettings_path, "ModBrowser")
        self.assertIn("Cannot disable", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            disable_mod(self.modsettings_path, "GustavX")
        self.assertIn("Cannot disable", str(ctx.exception))

    def test_deduplicate_installed_paks(self):
        # Create canonical pak and hashed mod.io duplicate with same UUID
        test_uuid = "059e2688-ba86-61f1-89d7-73755df32aea"
        canonical_pak = self.mods_dir / "UnlockLevelCurve_Patch_XP_Instant_059e2688-ba86-61f1-89d7-73755df32aea.pak"
        hashed_pak = self.mods_dir / "unlocklevelcurve_patch_xp_inst-4uq9.pak"
        bak_file = self.mods_dir / "stray_backup.pak.bak"

        create_dummy_pak(canonical_pak, "UnlockLevelCurve_Patch_XP_Instant", test_uuid)
        create_dummy_pak(hashed_pak, "UnlockLevelCurve_Patch_XP_Instant", test_uuid)
        bak_file.write_text("dummy backup")

        _ = deduplicate_installed_paks(self.mods_dir)

        # Winner must still exist in Mods/
        self.assertTrue(canonical_pak.is_file())
        # Hashed loser and .bak file must be removed from Mods/
        self.assertFalse(hashed_pak.is_file())
        self.assertFalse(bak_file.is_file())

        # Redundant files must be archived under Mods_Disabled/duplicates/
        dup_dir = self.mods_dir.parent / "Mods_Disabled" / "duplicates"
        self.assertTrue((dup_dir / hashed_pak.name).is_file())
        self.assertTrue((dup_dir / bak_file.name).is_file())

    def test_quarantine_and_restore_unrelated_paks(self):
        target_uuid = "cfef8d1a-128b-4b02-b518-4177f162e61a"
        unrelated_uuid = "8671399a-affb-bc52-2bme-000000000000"

        target_pak = self.mods_dir / "ArcaneProgression_cfef8d1a-128b-4b02-b518-4177f162e61a.pak"
        unrelated_pak = self.mods_dir / "abilityring_8671399a-affb-bc52-2bme.pak"

        create_dummy_pak(target_pak, "ArcaneProgression", target_uuid)
        create_dummy_pak(unrelated_pak, "AbilityRing", unrelated_uuid)

        # Quarantine unrelated paks
        quarantined = quarantine_unrelated_paks(self.mods_dir, keep_uuids={target_uuid})
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0]["filename"], unrelated_pak.name)

        # target_pak must remain in Mods/
        self.assertTrue(target_pak.is_file())
        # unrelated_pak must be moved to Mods_Disabled/
        self.assertFalse(unrelated_pak.is_file())
        disabled_dir = self.mods_dir.parent / "Mods_Disabled"
        self.assertTrue((disabled_dir / unrelated_pak.name).is_file())
        self.assertTrue((disabled_dir / "quarantine_manifest.json").is_file())

        # Restore quarantined paks
        restored = restore_quarantined_paks(self.mods_dir)
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0]["filename"], unrelated_pak.name)

        # Both paks must now be back in Mods/
        self.assertTrue(target_pak.is_file())
        self.assertTrue(unrelated_pak.is_file())
        self.assertFalse((disabled_dir / unrelated_pak.name).is_file())

    def test_cli_loadorder_commands(self):
        import subprocess
        import sys
        bg3_cli = Path(__file__).resolve().parent.parent / "packages" / "bg3-core" / "bg3_core" / "cli.py"

        # 1. Test bg3 loadorder enable --help shows --isolate and --quarantine
        proc = subprocess.run([sys.executable, str(bg3_cli), "loadorder", "enable", "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--isolate", proc.stdout)
        self.assertIn("--quarantine", proc.stdout)

        # 2. Test bg3 loadorder isolate --help shows Clean-room isolation and --quarantine
        proc = subprocess.run([sys.executable, str(bg3_cli), "loadorder", "isolate", "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Clean-room isolation", proc.stdout)
        self.assertIn("--quarantine", proc.stdout)

        # 3. Test bg3 loadorder restore --help
        proc = subprocess.run([sys.executable, str(bg3_cli), "loadorder", "restore", "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Restore quarantined mods", proc.stdout)

        # 4. Test bg3 loadorder dedup --help
        proc = subprocess.run([sys.executable, str(bg3_cli), "loadorder", "dedup", "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Deduplicate installed .pak files", proc.stdout)

    def test_modsettings_maintains_mod_order_node(self):
        """Verify that create_default_modsettings, enable_mod, and isolate_load_order maintain ModOrder."""
        target_path = Path(self.temp_dir.name) / "test_modsettings.lsx"
        create_default_modsettings(target_path)

        # 1. Verify ModOrder exists in newly created modsettings.lsx
        tree = ET.parse(target_path)
        mod_order = tree.find(".//node[@id='ModOrder']")
        self.assertIsNotNone(mod_order, "ModOrder node missing in default modsettings.lsx")
        modules = mod_order.findall("./children/node[@id='Module']")
        self.assertGreaterEqual(len(modules), 1)
        self.assertEqual(modules[0].find("attribute[@id='UUID']").get("value"), CORE_SYSTEM_MODULES[0]["UUID"])

        # 2. Verify enable_mod adds to ModOrder
        sample_mod = {
            "Folder": "SampleMod",
            "Name": "Sample Mod",
            "UUID": "11111111-2222-3333-4444-555555555555",
            "Version64": 36028797018963968,
        }
        enable_mod(target_path, sample_mod)
        tree = ET.parse(target_path)
        order_uuids = [m.find("attribute[@id='UUID']").get("value") for m in tree.findall(".//node[@id='ModOrder']/children/node[@id='Module']")]
        self.assertIn("11111111-2222-3333-4444-555555555555", order_uuids)

        # 3. Verify isolate_load_order preserves ModOrder for kept mod
        isolate_load_order(target_path, {"11111111-2222-3333-4444-555555555555"})
        tree = ET.parse(target_path)
        order_uuids_post = [m.find("attribute[@id='UUID']").get("value") for m in tree.findall(".//node[@id='ModOrder']/children/node[@id='Module']")]
        self.assertIn(CORE_SYSTEM_MODULES[0]["UUID"], order_uuids_post)
        self.assertIn("11111111-2222-3333-4444-555555555555", order_uuids_post)


if __name__ == "__main__":
    unittest.main()
