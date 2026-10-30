#!/usr/bin/env python3
"""
tests/test_purge_library.py
---------------------------
Unit tests for library purging utilities and CLI in bg3_core.library_catalog
and bg3_core.purge_library.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bg3_core.library_catalog import EMPTY_LIBRARY_HEADER, purge_library_mods


class PurgeLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.mods_dir = self.root / "mods"
        self.mods_dir.mkdir(parents=True)
        self.library_file = self.mods_dir / "library.md"

        # Populate fixture mod directories
        (self.mods_dir / "mod-alpha").mkdir()
        (self.mods_dir / "mod-alpha" / "README.md").write_text("# Alpha", encoding="utf-8")
        (self.mods_dir / "mod-beta").mkdir()
        (self.mods_dir / "mod-beta" / "README.md").write_text("# Beta", encoding="utf-8")
        (self.mods_dir / ".hidden-folder").mkdir()
        (self.mods_dir / "regular_file.txt").write_text("keep me", encoding="utf-8")

        initial_content = (
            "# Baldur's Gate 3 Mod Library\n\n"
            "## Gear\n\n"
            "| Mod Id | Mod Name | Mod Slug | Description | Features Documented | Spec Link |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| 100 | Mod Alpha | `mod-alpha` | Alpha mod | 1 implemented | [View Spec](mod-alpha/README.md) |\n"
            "| 200 | Mod Beta | `mod-beta` | Beta mod | 2 implemented | [View Spec](mod-beta/README.md) |\n"
        )
        self.library_file.write_text(initial_content, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_purge_library_dry_run(self):
        result = purge_library_mods(
            mods_dir=self.mods_dir,
            library_path=self.library_file,
            dry_run=True,
        )

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["purged_count"], 2)
        # Folders must still exist on disk
        self.assertTrue((self.mods_dir / "mod-alpha").is_dir())
        self.assertTrue((self.mods_dir / "mod-beta").is_dir())
        # Library file must remain unmodified
        self.assertIn("Mod Alpha", self.library_file.read_text(encoding="utf-8"))

    def test_purge_library_live(self):
        result = purge_library_mods(
            mods_dir=self.mods_dir,
            library_path=self.library_file,
            dry_run=False,
        )

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["purged_count"], 2)
        # Folders must be removed
        self.assertFalse((self.mods_dir / "mod-alpha").exists())
        self.assertFalse((self.mods_dir / "mod-beta").exists())
        # Hidden folder and non-directory files should be preserved
        self.assertTrue((self.mods_dir / ".hidden-folder").is_dir())
        self.assertTrue((self.mods_dir / "regular_file.txt").is_file())
        # Library file must be reset to the empty catalog template
        self.assertTrue(self.library_file.is_file())
        self.assertEqual(self.library_file.read_text(encoding="utf-8"), EMPTY_LIBRARY_HEADER)

    def test_purge_library_cli(self):
        script_path = Path(__file__).resolve().parent.parent / "packages" / "bg3-core" / "bg3_core" / "purge_library.py"
        cmd = [
            sys.executable,
            str(script_path),
            "--dry-run",
            "--json",
            "--mods-dir",
            str(self.mods_dir),
            "--library-path",
            str(self.library_file),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)
        self.assertEqual(data["purged_count"], 2)
        self.assertTrue(data["dry_run"])


if __name__ == "__main__":
    unittest.main()
