#!/usr/bin/env python3
"""End-to-end unit and integration tests for the 5-Stage BG3 Mod Lifecycle.

Tests the sequential handoffs across all 5 stages:
  Stage 1: Scaffolding, stat authoring, progression, root template, treasure injection, icon UVs.
  Stage 2A: Static pre-flight validation, localization check, conflict detection.
  Stage 2B: Game Data synchronization with automatic binary .loca compilation.
  Stage 3: LSPK .pak packaging with embedded .loca and load order activation in modsettings.lsx.
  Stage 4: Atomic version bumping (meta.lsx + README), HTML description rendering, strict validation.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(PACKAGES_DIR / "bg3-core"))
sys.path.insert(0, str(PACKAGES_DIR / "bg3-authoring"))
sys.path.insert(0, str(PACKAGES_DIR / "bg3-theorycraft"))

from bg3_core.lspk import LspkArchive
from bg3_core.larian_parsers import parse_loca_bytes, decode_version64


class ModLifecycleTests(unittest.TestCase):
    """End-to-end integration tests for the 5-stage mod development lifecycle."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="bg3_lifecycle_test_")
        self.temp_path = Path(self.temp_dir)
        self.my_mods_dir = self.temp_path / "my_mods"
        self.my_mods_dir.mkdir(parents=True)
        self.game_data_dir = self.temp_path / "GameData"
        self.game_data_dir.mkdir(parents=True)
        self.profile_dir = self.temp_path / "Profile"
        self.profile_dir.mkdir(parents=True)
        self.dist_dir = self.temp_path / "dist"
        self.dist_dir.mkdir(parents=True)

        # Set up a minimal valid modsettings.lsx with GustavDev
        initial_modsettings = """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="7" revision="1" build="3"/>
    <region id="ModuleSettings">
        <node id="root">
            <children>
                <node id="ModOrder">
                    <children>
                        <node id="Module">
                            <attribute id="UUID" type="FixedString" value="28ac9e5a-3ded-4247-aa72-46603a11b8fd"/>
                        </node>
                    </children>
                </node>
                <node id="Mods">
                    <children>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="GustavDev"/>
                            <attribute id="MD5" type="LSString" value=""/>
                            <attribute id="Name" type="LSString" value="GustavDev"/>
                            <attribute id="UUID" type="FixedString" value="28ac9e5a-3ded-4247-aa72-46603a11b8fd"/>
                            <attribute id="Version64" type="int64" value="36028797018963968"/>
                        </node>
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>
"""
        (self.profile_dir / "modsettings.lsx").write_text(initial_modsettings, encoding="utf-8")

        # Set up custom environment pointing to our temp directories
        self.appdata_mods_dir = self.temp_path / "AppData" / "Mods"
        self.appdata_mods_dir.mkdir(parents=True)
        self.env = os.environ.copy()
        self.env["BG3_MODS_DIR"] = str(self.my_mods_dir)
        self.env["BG3_DATA_DIR"] = str(self.game_data_dir)
        self.env["BG3_LOCALAPPDATA"] = str(self.temp_path / "AppData")
        self.env["BG3_USER_MODS_DIR"] = str(self.appdata_mods_dir)
        self.env["PYTHONPATH"] = f"{REPO_ROOT}:{PACKAGES_DIR}/bg3-core:{PACKAGES_DIR}/bg3-authoring:{PACKAGES_DIR}/bg3-theorycraft"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_script(self, script_name: str, *args) -> tuple[int, str, dict | None]:
        """Helper to run a tool module from packages/ and return code, stdout, and parsed JSON."""
        target = None
        for cand in PACKAGES_DIR.rglob(script_name):
            if "__pycache__" not in cand.as_posix():
                target = cand
                break
        if not target.is_file():
            pass
        cmd = [sys.executable, str(target)] + list(args)
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=self.env,
            capture_output=True,
            text=True,
        )
        data = None
        if "--json" in args and proc.stdout:
            try:
                data = json.loads(proc.stdout)
            except Exception:
                pass
        output = proc.stdout + (f"\nSTDERR: {proc.stderr}" if proc.stderr else "")
        return proc.returncode, output, data

    def test_end_to_end_lifecycle(self):
        """Execute and verify complete Stage 1 through Stage 4 lifecycle pipeline."""
        mod_name = "LifecycleTestMod"
        mod_slug = "lifecycletestmod"

        # ---------------------------------------------------------
        # STAGE 1: CREATION (Scaffolding & Component Authoring)
        # ---------------------------------------------------------
        # 1.1 Scaffold mod
        code, out, data = self.run_script(
            "create_mod_scaffold.py",
            "--name", mod_name,
            "--slug", mod_slug,
            "--author", "TestAuthor",
            "--description", "Automated test mod for lifecycle pipeline",
            "--json",
        )
        self.assertEqual(code, 0, f"Scaffold failed: {out}")
        self.assertIsNotNone(data)
        mod_dir = Path(data.get("root_dir") or data.get("mod_dir"))
        self.assertTrue(mod_dir.is_dir())
        larian_folder = data.get("larian_folder") or data.get("folder_name")
        self.assertTrue(larian_folder.startswith(f"{mod_name}_"))

        # 1.2 Scaffold stat entry (Weapon)
        code, out, data = self.run_script(
            "scaffold_stat_entry.py",
            "--mod", mod_slug,
            "--type", "Weapon",
            "--name", "LIFECYCLE_Sword",
            "--display-name", "Blade of Lifecycle",
            "--description", "A legendary blade tested across all lifecycle gates.",
            "--props", "using _Shortsword,Damage 1d8 Piercing,Rarity VeryRare",
        )
        self.assertEqual(code, 0, f"Scaffold stat failed: {out}")
        weapon_txt = mod_dir / "Public" / larian_folder / "Stats" / "Generated" / "Data" / "Weapon.txt"
        self.assertTrue(weapon_txt.exists())
        self.assertIn("LIFECYCLE_Sword", weapon_txt.read_text(encoding="utf-8"))

        # 1.3 Scaffold RootTemplate
        code, out, data = self.run_script(
            "scaffold_root_template.py",
            "--mod", mod_slug,
            "--item", "LIFECYCLE_Sword",
            "--visual-preset", "longsword",
        )
        self.assertEqual(code, 0, f"Scaffold template failed: {out}")
        merged_lsx = mod_dir / "Public" / larian_folder / "RootTemplates" / "_merged.lsx"
        self.assertTrue(merged_lsx.exists())
        self.assertIn("LIFECYCLE_Sword", merged_lsx.read_text(encoding="utf-8"))

        # 1.4 Scaffold progression node
        code, out, data = self.run_script(
            "scaffold_progression_node.py",
            "--mod", mod_slug,
            "--class", "Rogue",
            "--level", "3",
            "--subclass", "LifecycleSubclass",
            "--table-uuid", "11111111-2222-3333-4444-555555555555",
        )
        self.assertEqual(code, 0, f"Scaffold progression failed: {out}")
        progressions_lsx = mod_dir / "Public" / larian_folder / "Progressions" / "Progressions.lsx"
        self.assertTrue(progressions_lsx.exists())
        self.assertIn("LifecycleSubclass", progressions_lsx.read_text(encoding="utf-8"))

        # 1.5 Inject treasure table drop
        code, out, data = self.run_script(
            "inject_treasure_table.py",
            "--mod", mod_slug,
            "--item", "LIFECYCLE_Sword",
            "--container", "tutorial_chest",
        )
        self.assertEqual(code, 0, f"Inject treasure failed: {out}")
        treasure_txt = mod_dir / "Public" / larian_folder / "Stats" / "Generated" / "Data" / "TreasureTable.txt"
        self.assertTrue(treasure_txt.exists())
        self.assertIn("LIFECYCLE_Sword", treasure_txt.read_text(encoding="utf-8"))

        # 1.6 Scaffold Icon UVs
        code, out, data = self.run_script(
            "scaffold_icon_uvs.py",
            "--mod", mod_slug,
            "--atlas-size", "1024",
            "--icon-size", "64",
            "--icon-names", "Item_LIFECYCLE_Sword,Spell_LIFECYCLE_Strike",
        )
        self.assertEqual(code, 0, f"Scaffold icon UVs failed: {out}")
        icons_lsx = mod_dir / "Public" / larian_folder / "GUI" / "Icons.lsx"
        self.assertTrue(icons_lsx.exists())
        self.assertIn("Item_LIFECYCLE_Sword", icons_lsx.read_text(encoding="utf-8"))

        # ---------------------------------------------------------
        # STAGE 2A: DIAGNOSTICS (Static Pre-Flight on my_mods/)
        # ---------------------------------------------------------
        # 2.1 Validate mod syntax and handles
        code, out, data = self.run_script(
            "validate_mod.py",
            "--mod", mod_slug,
            "--json",
        )
        self.assertEqual(code, 0, f"Validate mod failed: {out}")
        self.assertTrue(data["summary"]["all_passed"], f"Validation report errors: {data}")

        # 2.2 Localization audit
        code, out, data = self.run_script(
            "sync_localization.py",
            "--mod", mod_slug,
            "--check",
            "--json",
        )
        self.assertEqual(code, 0, f"Localization check failed: {out}")
        self.assertIsNotNone(data)
        self.assertEqual(len(data.get("missing_handles", [])), 0)

        # ---------------------------------------------------------
        # STAGE 2B: TOOLKIT SYNC & RUNTIME PREPARATION
        # ---------------------------------------------------------
        # Sync to game Data with automatic binary .loca compilation
        code, out, data = self.run_script(
            "sync_game_data.py",
            "--mods", mod_slug,
            "--json",
        )
        self.assertEqual(code, 0, f"Game data sync failed: {out}")
        self.assertIsNotNone(data)

        # Verify synced files in game Data
        synced_mod_dir = self.game_data_dir / "Mods" / larian_folder
        self.assertTrue(synced_mod_dir.is_dir())
        synced_public_dir = self.game_data_dir / "Public" / larian_folder
        self.assertTrue(synced_public_dir.is_dir())

        # Verify binary .loca compilation in synced game Data
        compiled_loca = synced_mod_dir / "Localization" / "English" / f"{mod_name}.loca"
        self.assertTrue(compiled_loca.is_file(), f"Compiled .loca missing at {compiled_loca}")
        loca_bytes = compiled_loca.read_bytes()
        entries = parse_loca_bytes(loca_bytes)
        self.assertGreater(len(entries), 0)
        self.assertTrue(any("Blade of Lifecycle" in text for text in entries.values()))

        # ---------------------------------------------------------
        # STAGE 3: IN-GAME TESTING (Clean Data, Packaging & Load Order)
        # ---------------------------------------------------------
        # 3.0 Clean loose Data files before packaging to ensure clean-room isolation
        code, out, data = self.run_script(
            "sync_game_data.py",
            "--clean-mod", mod_slug,
            "--json",
        )
        self.assertEqual(code, 0, f"Clean mod data failed: {out}")
        self.assertIsNotNone(data)
        self.assertGreater(data.get("removed_count", 0), 0)
        self.assertFalse(synced_mod_dir.exists(), "Loose Mods/<folder> lingered after --clean-mod")
        self.assertFalse(synced_public_dir.exists(), "Loose Public/<folder> lingered after --clean-mod")

        # 3.1 Pack mod into standalone .pak archive and publish local
        target_pak = self.dist_dir / f"{mod_slug}.pak"
        code, out, data = self.run_script(
            "pack_mod_pak.py",
            "--mod", mod_slug,
            "--out", str(target_pak),
            "--json",
        )
        self.assertEqual(code, 0, f"Pack mod failed: {out}")
        self.assertTrue(target_pak.is_file())
        self.assertGreater(target_pak.stat().st_size, 0)

        # 3.2 Publish local test .pak to AppData Mods directory
        code, out, data = self.run_script(
            "pack_mod_pak.py",
            "--mod", mod_slug,
            "--publish-local",
            "--json",
        )
        self.assertEqual(code, 0, f"Publish local failed: {out}")
        local_pak = self.appdata_mods_dir / f"{larian_folder}.pak"
        self.assertTrue(local_pak.is_file(), f"Local test pak missing at {local_pak}")

        # Verify LSPK archive contents (verify compiled .loca is present and README is excluded)
        archive = LspkArchive.open(str(target_pak))
        file_list = [f["name"] for f in archive.files]
        self.assertTrue(any(name.endswith(".loca") for name in file_list), f"No .loca in pak: {file_list}")
        self.assertFalse(any("README.md" in name for name in file_list), f"README leaked into pak: {file_list}")

        # 3.2 Enable in active profile modsettings.lsx
        code, out, data = self.run_script(
            "manage_load_order.py",
            "--enable", mod_slug,
            "--path", str(self.profile_dir / "modsettings.lsx"),
            "--validate",
            "--json",
        )
        self.assertEqual(code, 0, f"Manage load order failed: {out}")
        self.assertIsNotNone(data)
        self.assertTrue(data.get("validation", {}).get("valid"), f"Load order validation failed: {data}")
        # Verify the mod was appended
        modsettings_content = (self.profile_dir / "modsettings.lsx").read_text(encoding="utf-8")
        self.assertIn(larian_folder, modsettings_content)

        # ---------------------------------------------------------
        # STAGE 4: RELEASE PREPARATION
        # ---------------------------------------------------------
        # 4.1 Atomic semantic version bump
        code, out, data = self.run_script(
            "bump_mod_version.py",
            "--mod", mod_slug,
            "--patch",
            "--json",
        )
        self.assertEqual(code, 0, f"Version bump failed: {out}")
        self.assertIsNotNone(data)
        new_version_str = data.get("new_version")
        self.assertEqual(new_version_str, "1.0.1.0")
        # Verify README was updated
        readme_text = (mod_dir / "README.md").read_text(encoding="utf-8")
        self.assertIn("1.0.1.0", readme_text)

        # 4.2 Render mod.io description HTML (GFM table support)
        table_md = "\n\n### Mechanics\n\n| Item | Type | Damage |\n| :--- | :--- | :--- |\n| Blade of Lifecycle | Weapon | 1d8 Piercing |\n"
        with open(mod_dir / "README.md", "a", encoding="utf-8") as f:
            f.write(table_md)

        code, out, data = self.run_script(
            "render_modio_description.py",
            "--mod", mod_slug,
            "--write",
            "--json",
        )
        self.assertEqual(code, 0, f"Render description failed: {out}")
        desc_html = mod_dir / "modio_description.html"
        self.assertTrue(desc_html.exists())
        html_content = desc_html.read_text(encoding="utf-8")
        self.assertIn("<table>", html_content)

        # 4.3 Strict validation gate
        code, out, data = self.run_script(
            "validate_mod.py",
            "--mod", mod_slug,
            "--strict",
            "--json",
        )
        self.assertEqual(code, 0, f"Strict validation failed: {out}")
        self.assertTrue(data["summary"]["all_passed"], f"Strict validation errors: {data}")

        # ---------------------------------------------------------
        # STAGE 5: POST-RELEASE TEARDOWN (Clean-Room Subscriber Reset)
        # ---------------------------------------------------------
        # 5.1 Clean local test .pak from AppData Mods/
        code, out, data = self.run_script(
            "pack_mod_pak.py",
            "--mod", mod_slug,
            "--clean-local",
            "--json",
        )
        self.assertEqual(code, 0, f"Clean local pak failed: {out}")
        self.assertIsNotNone(data)
        self.assertGreater(data.get("removed_count", 0), 0)
        self.assertFalse(local_pak.exists(), f"Local test pak lingered at {local_pak}")

        # 5.2 Remove test entry from modsettings.lsx
        code, out, data = self.run_script(
            "manage_load_order.py",
            "--disable", mod_slug,
            "--path", str(self.profile_dir / "modsettings.lsx"),
        )
        self.assertEqual(code, 0, f"Disable mod failed: {out}")
        modsettings_after = (self.profile_dir / "modsettings.lsx").read_text(encoding="utf-8")
        self.assertNotIn(larian_folder, modsettings_after, "Mod lingered in modsettings.lsx after disable")


if __name__ == "__main__":
    unittest.main()
