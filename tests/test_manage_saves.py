#!/usr/bin/env python3
"""tests/test_manage_saves.py
--------------------------
Unit and CLI integration tests for BG3 savegame management, discovery, backup, and cleanup.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bg3_core.manage_saves import (
    backup_save_games,
    discover_save_games,
    filter_saves_for_purge,
    purge_save_games,
)


class TestManageSaves(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_dir = Path(self.temp_dir.name) / "PlayerProfiles" / "Public" / "Savegames" / "Story"
        self.save_dir.mkdir(parents=True)

        now = time.time()
        self.saves = []

        # Create 4 directory-based saves (typical BG3 structure)
        for i in range(4):
            save_name = f"Campaign_Save_{i}"
            pkg_dir = self.save_dir / save_name
            pkg_dir.mkdir()
            lsv = pkg_dir / f"{save_name}.lsv"
            lsv.write_text(f"Mock LSV save data {i}\n", encoding="utf-8")
            webp = pkg_dir / f"{save_name}.WebP"
            webp.write_text("Mock thumbnail\n", encoding="utf-8")

            mtime = now - (10 - i) * 3600
            os.utime(lsv, (mtime, mtime))
            self.saves.append({
                "name": save_name,
                "dir": pkg_dir,
                "lsv": lsv,
                "webp": webp,
                "mtime": mtime,
            })

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_discover_save_games(self):
        discovered = discover_save_games([self.save_dir])
        self.assertEqual(len(discovered), 4)
        # Newest save should be Campaign_Save_3
        self.assertEqual(discovered[0]["name"], "Campaign_Save_3")
        self.assertTrue(discovered[0]["is_latest"])
        self.assertTrue(discovered[0]["is_dir_package"])
        self.assertEqual(len(discovered[0]["associated_files"]), 2)

    def test_filter_saves_keep_count(self):
        discovered = discover_save_games([self.save_dir])
        to_purge, to_preserve = filter_saves_for_purge(
            all_saves=discovered,
            keep=2,
            keep_latest=True,
        )
        self.assertEqual(len(to_preserve), 2)
        self.assertEqual(len(to_purge), 2)
        preserved_names = {s["name"] for s in to_preserve}
        self.assertIn("Campaign_Save_3", preserved_names)
        self.assertIn("Campaign_Save_2", preserved_names)

    def test_latest_save_protection(self):
        discovered = discover_save_games([self.save_dir])
        # Even with purge_all=True, keep_latest=True must protect the latest save
        to_purge, to_preserve = filter_saves_for_purge(
            all_saves=discovered,
            purge_all=True,
            keep_latest=True,
        )
        self.assertEqual(len(to_preserve), 1)
        self.assertEqual(to_preserve[0]["name"], "Campaign_Save_3")
        self.assertEqual(len(to_purge), 3)

    def test_force_all_purges_latest(self):
        discovered = discover_save_games([self.save_dir])
        # When keep_latest=False, all saves are purged
        to_purge, to_preserve = filter_saves_for_purge(
            all_saves=discovered,
            purge_all=True,
            keep_latest=False,
        )
        self.assertEqual(len(to_preserve), 0)
        self.assertEqual(len(to_purge), 4)

    def test_purge_save_games_live(self):
        discovered = discover_save_games([self.save_dir])
        to_purge, _ = filter_saves_for_purge(discovered, keep=2)
        result = purge_save_games(to_purge, dry_run=False)

        self.assertEqual(result["purged_count"], 2)
        self.assertEqual(result["failed_count"], 0)
        self.assertFalse(result["dry_run"])

        # Check that the purged directories were deleted entirely
        self.assertFalse((self.save_dir / "Campaign_Save_0").exists())
        self.assertFalse((self.save_dir / "Campaign_Save_1").exists())
        # Preserved directories must still exist
        self.assertTrue((self.save_dir / "Campaign_Save_2").is_dir())
        self.assertTrue((self.save_dir / "Campaign_Save_3").is_dir())

    def test_purge_save_games_dry_run(self):
        discovered = discover_save_games([self.save_dir])
        to_purge, _ = filter_saves_for_purge(discovered, keep=1)
        result = purge_save_games(to_purge, dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["purged_count"], 3)
        # All directories must still exist
        for s in self.saves:
            self.assertTrue(s["dir"].is_dir())

    def test_backup_save_games(self):
        discovered = discover_save_games([self.save_dir])
        backup_zip = self.save_dir.parent / "test_backup.zip"
        result = backup_save_games(discovered, dest_path=backup_zip)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["archived_count"], 4)
        self.assertTrue(backup_zip.is_file())

        with zipfile.ZipFile(backup_zip, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("Campaign_Save_0/Campaign_Save_0.lsv", namelist)
            self.assertIn("Campaign_Save_0/Campaign_Save_0.WebP", namelist)
            self.assertIn("Campaign_Save_3/Campaign_Save_3.lsv", namelist)

    def test_cli_list_json(self):
        script = REPO_ROOT / "packages" / "bg3-core" / "bg3_core" / "manage_saves.py"
        cmd = [
            sys.executable,
            str(script),
            "list",
            "--save-dir",
            str(self.save_dir),
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["total_count"], 4)

    def test_cli_purge_confirmation_required(self):
        script = REPO_ROOT / "packages" / "bg3-core" / "bg3_core" / "manage_saves.py"
        cmd = [
            sys.executable,
            str(script),
            "purge",
            "--save-dir",
            str(self.save_dir),
            "--keep",
            "1",
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "CONFIRMATION_REQUIRED")

    def test_cli_purge_with_yes(self):
        script = REPO_ROOT / "packages" / "bg3-core" / "bg3_core" / "manage_saves.py"
        cmd = [
            sys.executable,
            str(script),
            "purge",
            "--save-dir",
            str(self.save_dir),
            "--keep",
            "1",
            "--yes",
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["purged_count"], 3)
        self.assertEqual(payload["data"]["preserved_count"], 1)


if __name__ == "__main__":
    unittest.main()
