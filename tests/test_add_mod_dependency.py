#!/usr/bin/env python3
"""
tests/test_add_mod_dependency.py
--------------------------------
Unit and integration tests for scripts/add_mod_dependency.py.
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

from scripts.add_mod_dependency import (
    add_permanent_dependencies,
    add_permanent_dependency,
    add_test_dependencies,
    add_test_dependency,
    parse_slug_list,
    resolve_cli_targets,
)


class TestAddModDependency(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="bg3_add_dep_test_")
        self.temp_path = Path(self.temp_dir)
        self.mod_dir = self.temp_path / "TestMod"
        self.mod_dir.mkdir(parents=True)

        # Create minimal Mods/TestMod/meta.lsx
        meta_dir = self.mod_dir / "Mods" / "TestMod"
        meta_dir.mkdir(parents=True)
        self.meta_file = meta_dir / "meta.lsx"
        self.meta_file.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="7" revision="1" build="3"/>
    <region id="Config">
        <node id="root">
            <children>
                <node id="Dependencies">
                    <children>
                    </children>
                </node>
                <node id="ModuleInfo">
                    <attribute id="Folder" type="LSString" value="TestMod"/>
                    <attribute id="Name" type="LSString" value="TestMod"/>
                    <attribute id="UUID" type="FixedString" value="11111111-2222-3333-4444-555555555555"/>
                    <attribute id="Version64" type="int64" value="36028797018963968"/>
                </node>
            </children>
        </node>
    </region>
</save>
""",
            encoding="utf-8",
        )

        # Create minimal README.md
        self.readme_file = self.mod_dir / "README.md"
        self.readme_file.write_text(
            """# TestMod

## Dependencies
- None.

## Features
- Test feature
""",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_slug_list(self):
        self.assertEqual(parse_slug_list(None), [])
        self.assertEqual(parse_slug_list([]), [])
        self.assertEqual(parse_slug_list("mod1"), ["mod1"])
        self.assertEqual(
            parse_slug_list(["mod1,mod2", "mod3", "mod2, mod4"]),
            ["mod1", "mod2", "mod3", "mod4"],
        )
        self.assertEqual(
            parse_slug_list(" unlocklevelcurve , unlocklevelcurve-instant-xp "),
            ["unlocklevelcurve", "unlocklevelcurve-instant-xp"],
        )

    def test_resolve_cli_targets(self):
        class MockArgs:
            def __init__(self, dep=None, test_dep=None, test_only=None):
                self.dep = dep or []
                self.test_dep = test_dep or []
                self.test_only = test_only or []

        # Case 1: only --dep
        perm, test = resolve_cli_targets(MockArgs(dep=["dep1,dep2"]))
        self.assertEqual(perm, ["dep1", "dep2"])
        self.assertEqual(test, [])

        # Case 2: only --test-only with slugs
        perm, test = resolve_cli_targets(MockArgs(test_only=["test1,test2"]))
        self.assertEqual(perm, [])
        self.assertEqual(test, ["test1", "test2"])

        # Case 3: backward compatible bare flag --dep ... --test-only
        perm, test = resolve_cli_targets(MockArgs(dep=["dep1,dep2"], test_only=[True]))
        self.assertEqual(perm, [])
        self.assertEqual(test, ["dep1", "dep2"])

        # Case 4: simultaneous --dep and --test-only with values
        perm, test = resolve_cli_targets(MockArgs(dep=["perm1,perm2"], test_only=["test1,test2"]))
        self.assertEqual(perm, ["perm1", "perm2"])
        self.assertEqual(test, ["test1", "test2"])

        # Case 5: simultaneous --dep and --test-dep
        perm, test = resolve_cli_targets(MockArgs(dep=["perm1", "perm2"], test_dep=["test1,test2"]))
        self.assertEqual(perm, ["perm1", "perm2"])
        self.assertEqual(test, ["test1", "test2"])

    def test_add_test_dependencies_batch(self):
        meta1 = {"Name": "TestDep1", "Folder": "TestDep1_Folder", "UUID": "aaaa-1111"}
        meta2 = {"Name": "TestDep2", "Folder": "TestDep2_Folder", "UUID": "bbbb-2222"}

        # Dry run test
        res_dry = add_test_dependencies(self.mod_dir, [meta1, meta2], dry_run=True)
        self.assertEqual(len(res_dry), 2)
        self.assertEqual(res_dry[0]["status"], "added_test_dependency")
        self.assertTrue(res_dry[0]["dry_run"])
        self.assertFalse((self.mod_dir / ".test_deps.json").is_file())

        # Real add
        res_real = add_test_dependencies(self.mod_dir, [meta1, meta2], dry_run=False)
        self.assertEqual(len(res_real), 2)
        self.assertEqual(res_real[0]["status"], "added_test_dependency")
        self.assertEqual(res_real[1]["status"], "added_test_dependency")

        cfg_file = self.mod_dir / ".test_deps.json"
        self.assertTrue(cfg_file.is_file())
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        self.assertEqual(data["test_dependencies"], ["TestDep1", "TestDep2"])

        # Add again: should report already_present
        res_again = add_test_dependencies(self.mod_dir, [meta1], dry_run=False)
        self.assertEqual(len(res_again), 1)
        self.assertEqual(res_again[0]["status"], "already_present")

    def test_add_permanent_dependencies_batch(self):
        meta1 = {
            "Name": "PermDep1",
            "Folder": "PermDep1_Folder",
            "UUID": "28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8",
            "MD5": "abcd1234",
            "PublishHandle": 12345,
            "Version64": 36028797018963968,
        }
        meta2 = {
            "Name": "PermDep2",
            "Folder": "PermDep2_Folder",
            "UUID": "cb555efe-2d9e-131f-8195-a89329d218ea",
            "MD5": "dcba4321",
            "PublishHandle": 54321,
            "Version64": 36028797018963968,
        }

        # Dry run test
        res_dry = add_permanent_dependencies(self.mod_dir, [meta1, meta2], dry_run=True)
        self.assertEqual(len(res_dry), 2)
        self.assertEqual(res_dry[0]["status"], "added_dependency")
        self.assertTrue(res_dry[0]["dry_run"])
        # Verify meta.lsx was NOT changed
        tree = ET.parse(self.meta_file)
        self.assertEqual(len(tree.getroot().findall(".//node[@id='ModuleShortDesc']")), 0)

        # Real add
        res_real = add_permanent_dependencies(self.mod_dir, [meta1, meta2], dry_run=False)
        self.assertEqual(len(res_real), 2)
        self.assertEqual(res_real[0]["status"], "added_dependency")
        self.assertEqual(res_real[1]["status"], "added_dependency")
        self.assertTrue(res_real[0]["readme_updated"])

        # Verify meta.lsx has both nodes
        tree = ET.parse(self.meta_file)
        descs = tree.getroot().findall(".//node[@id='ModuleShortDesc']")
        self.assertEqual(len(descs), 2)
        uuids = [d.find("attribute[@id='UUID']").get("value").lower() for d in descs]
        self.assertIn("28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8", uuids)
        self.assertIn("cb555efe-2d9e-131f-8195-a89329d218ea", uuids)

        # Verify README.md updated
        readme_content = self.readme_file.read_text(encoding="utf-8")
        self.assertNotIn("- None.", readme_content)
        self.assertIn("`PermDep1` (`28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8`)", readme_content)
        self.assertIn("`PermDep2` (`cb555efe-2d9e-131f-8195-a89329d218ea`)", readme_content)

        # Add again: should report already_present
        res_again = add_permanent_dependencies(self.mod_dir, [meta1], dry_run=False)
        self.assertEqual(len(res_again), 1)
        self.assertEqual(res_again[0]["status"], "already_present")

    def test_cli_integration_simultaneous_and_comma_separated(self):
        script_path = REPO_ROOT / "scripts" / "add_mod_dependency.py"

        # 1. Test comma-separated test-only invocation on mock mod
        cmd1 = [
            sys.executable,
            str(script_path),
            "--mod",
            str(self.mod_dir),
            "--test-only",
            "unlocklevelcurve,unlocklevelcurve-instant-xp",
            "--json",
        ]
        proc1 = subprocess.run(cmd1, capture_output=True, text=True)
        self.assertEqual(proc1.returncode, 0, f"Error: {proc1.stderr}")
        data1 = json.loads(proc1.stdout)
        self.assertEqual(data1["status"], "success")
        self.assertEqual(len(data1["test_dependencies"]), 2)
        self.assertEqual(len(data1["dependencies"]), 0)

        # 2. Test simultaneous permanent dep and test dep
        cmd2 = [
            sys.executable,
            str(script_path),
            "--mod",
            str(self.mod_dir),
            "--dep",
            "GustavDev",
            "--test-dep",
            "GustavX",
            "--json",
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True)
        self.assertEqual(proc2.returncode, 0, f"Error: {proc2.stderr}")
        data2 = json.loads(proc2.stdout)
        self.assertEqual(data2["status"], "success")
        self.assertEqual(len(data2["dependencies"]), 1)
        self.assertEqual(data2["dependencies"][0]["dependency"], "GustavDev")
        self.assertEqual(len(data2["test_dependencies"]), 1)
        self.assertEqual(data2["test_dependencies"][0]["dependency"], "GustavX")

        # 3. Test backward compatibility for single dep JSON format
        cmd3 = [
            sys.executable,
            str(script_path),
            "--mod",
            str(self.mod_dir),
            "--dep",
            "UnlockLevelCurve",
            "--dry-run",
            "--json",
        ]
        proc3 = subprocess.run(cmd3, capture_output=True, text=True)
        self.assertEqual(proc3.returncode, 0, f"Error: {proc3.stderr}")
        data3 = json.loads(proc3.stdout)
        self.assertEqual(data3["status"], "added_dependency")
        self.assertEqual(data3["uuid"], "a2ffd0e4-c407-8642-2611-c934ea0b0a77")


if __name__ == "__main__":
    unittest.main()
