#!/usr/bin/env python3
"""tests/test_purge_logs.py
------------------------
Unit and CLI integration tests for BG3 Toolkit runtime log purging.
"""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bg3_authoring.diagnostics.diagnose_toolkit_logs import purge_toolkit_logs


class TestPurgeToolkitLogs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.toolkit_dir = Path(self.temp_dir.name)

        # Create mock log files with staggered mtimes
        now = time.time()
        self.log_files = []
        for i in range(7):
            f = self.toolkit_dir / f"log.{i}.txt"
            f.write_text(f"Session log {i}\n" * 10, encoding="utf-8")
            # Newer files have higher i
            mtime = now - (10 - i) * 3600
            import os
            os.utime(f, (mtime, mtime))
            self.log_files.append(f)

        # Create an osiris log and a non-log file
        self.osiris_log = self.toolkit_dir / "osirislog.1.txt"
        self.osiris_log.write_text("Osiris log\n", encoding="utf-8")
        self.non_log = self.toolkit_dir / "readme.txt"
        self.non_log.write_text("Do not purge me\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_purge_toolkit_logs_keep_count(self):
        # 7 engine logs, keep=3 -> purge 4 oldest engine logs
        res = purge_toolkit_logs(
            toolkit_dir=self.toolkit_dir,
            log_type="engine",
            keep=3,
            dry_run=False,
        )
        self.assertEqual(res["total_discovered"], 7)
        self.assertEqual(res["purged_count"], 4)
        self.assertEqual(res["preserved_count"], 3)
        self.assertEqual(res["failed_count"], 0)
        self.assertFalse(res["dry_run"])

        # Check that the 3 newest files still exist
        self.assertTrue((self.toolkit_dir / "log.6.txt").exists())
        self.assertTrue((self.toolkit_dir / "log.5.txt").exists())
        self.assertTrue((self.toolkit_dir / "log.4.txt").exists())
        # The 4 oldest should be deleted
        self.assertFalse((self.toolkit_dir / "log.0.txt").exists())
        self.assertFalse((self.toolkit_dir / "log.1.txt").exists())
        # Non-engine logs and non-logs must remain untouched
        self.assertTrue(self.osiris_log.exists())
        self.assertTrue(self.non_log.exists())

    def test_purge_toolkit_logs_dry_run(self):
        res = purge_toolkit_logs(
            toolkit_dir=self.toolkit_dir,
            log_type="engine",
            keep=2,
            dry_run=True,
        )
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["purged_count"], 5)
        self.assertEqual(res["preserved_count"], 2)

        # All files must still exist on disk
        for f in self.log_files:
            self.assertTrue(f.exists())

    def test_purge_toolkit_logs_all(self):
        res = purge_toolkit_logs(
            toolkit_dir=self.toolkit_dir,
            log_type="all",
            purge_all=True,
            dry_run=False,
        )
        # 7 engine logs + 1 osiris log = 8 total
        self.assertEqual(res["total_discovered"], 8)
        self.assertEqual(res["purged_count"], 8)
        self.assertEqual(res["preserved_count"], 0)
        self.assertTrue(self.non_log.exists())

    def test_purge_toolkit_logs_empty_dir(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            res = purge_toolkit_logs(Path(empty_dir), log_type="all", dry_run=False)
            self.assertEqual(res["total_discovered"], 0)
            self.assertEqual(res["purged_count"], 0)
            self.assertEqual(res["preserved_count"], 0)

    def test_cli_purge_confirmation_required(self):
        script = REPO_ROOT / "packages" / "bg3-authoring" / "bg3_authoring" / "diagnostics" / "diagnose_toolkit_logs.py"
        cmd = [
            sys.executable,
            str(script),
            "--toolkit-dir",
            str(self.toolkit_dir),
            "--purge",
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "CONFIRMATION_REQUIRED")

    def test_cli_purge_with_yes(self):
        script = REPO_ROOT / "packages" / "bg3-authoring" / "bg3_authoring" / "diagnostics" / "diagnose_toolkit_logs.py"
        cmd = [
            sys.executable,
            str(script),
            "--toolkit-dir",
            str(self.toolkit_dir),
            "--purge",
            "--keep",
            "2",
            "--yes",
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["purged_count"], 5)
        self.assertEqual(payload["data"]["preserved_count"], 2)


if __name__ == "__main__":
    unittest.main()
