#!/usr/bin/env python3
"""
tests/test_modio_sync.py
------------------------
Unit tests for mod.io library sync pruning, folder resolution, orphan detection,
and safe batch folder deletion.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.modio_sync import (
    find_mod_folder,
    find_orphaned_folders,
    safe_batch_delete_folders,
    sync_library,
)


class ModioSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name)
        self.mods_dir = self.test_root / "mods"
        self.mods_dir.mkdir(parents=True)
        self.library_file = self.mods_dir / "library.md"

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_library(self, rows):
        content = (
            "# Baldur's Gate 3 Mod Library\n\n"
            "## Gear\n\n"
            "| Mod Id | Mod Name | Mod Slug | Description | Features Documented | Spec Link |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        )
        for r in rows:
            content += (
                f"| {r['mod_id']} | {r['name']} | `{r['slug']}` | {r.get('desc', 'Description')} | "
                f"{r.get('features', '1 implemented')} | [View Spec]({r['slug']}/README.md) |\n"
            )
        self.library_file.write_text(content, encoding="utf-8")
        return self.library_file

    def test_find_mod_folder(self):
        alpha_dir = self.mods_dir / "alpha-mod"
        alpha_dir.mkdir()

        # Exact match
        self.assertEqual(find_mod_folder("alpha-mod", self.mods_dir), alpha_dir)
        # Case-insensitive / normalized match
        self.assertEqual(find_mod_folder("AlphaMod", self.mods_dir), alpha_dir)
        # Not found
        self.assertIsNone(find_mod_folder("nonexistent", self.mods_dir))

    def test_find_orphaned_folders(self):
        (self.mods_dir / "active-mod").mkdir()
        (self.mods_dir / "orphan-mod").mkdir()
        (self.mods_dir / ".hidden-folder").mkdir()
        (self.mods_dir / "some-file.txt").write_text("hello", encoding="utf-8")

        active_slugs = ["active-mod"]
        orphans = find_orphaned_folders(self.mods_dir, active_slugs)

        orphan_names = [o.name for o in orphans]
        self.assertIn("orphan-mod", orphan_names)
        self.assertNotIn("active-mod", orphan_names)
        self.assertNotIn(".hidden-folder", orphan_names)

    def test_safe_batch_delete_folders_dry_run(self):
        target = self.mods_dir / "to-delete"
        target.mkdir()

        res = safe_batch_delete_folders([target], mods_dir=self.mods_dir, dry_run=True)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["status"], "dry_run_deleted")
        self.assertTrue(target.is_dir(), "Folder should not be deleted in dry-run")

    def test_safe_batch_delete_folders_execution(self):
        target1 = self.mods_dir / "target1"
        target1.mkdir()
        target2 = self.mods_dir / "target2"
        target2.mkdir()

        res = safe_batch_delete_folders([target1, target2], mods_dir=self.mods_dir, dry_run=False)
        self.assertEqual(len(res), 2)
        self.assertTrue(all(r["status"] == "deleted" for r in res))
        self.assertFalse(target1.exists())
        self.assertFalse(target2.exists())

    def test_safe_batch_delete_folders_prevents_directory_traversal(self):
        outside_dir = self.test_root / "outside"
        outside_dir.mkdir()

        res = safe_batch_delete_folders([outside_dir, self.mods_dir], mods_dir=self.mods_dir, dry_run=False)
        self.assertTrue(outside_dir.exists())
        self.assertTrue(self.mods_dir.exists())
        self.assertTrue(all(r["status"] == "error" for r in res))

    @patch("scripts.modio_sync.fetch_subscribed_mods")
    def test_sync_library_prune_deletes_folder_and_row(self, mock_fetch):
        # Only alpha is subscribed remotely
        mock_fetch.return_value = [
            {"name_id": "alpha", "name": "Alpha Mod"},
        ]

        # Both alpha and beta are in library.md and have folders
        self.make_library([
            {"mod_id": "101", "name": "Alpha Mod", "slug": "alpha"},
            {"mod_id": "102", "name": "Beta Mod", "slug": "beta"},
        ])
        alpha_folder = self.mods_dir / "alpha"
        alpha_folder.mkdir()
        beta_folder = self.mods_dir / "beta"
        beta_folder.mkdir()

        results = sync_library(
            oauth_token="fake_token",
            api_key="fake_key",
            dry_run=False,
            prune=True,
            skip_updates=True,
            library_path=str(self.library_file),
            mods_dir=self.mods_dir,
        )

        lib_text = self.library_file.read_text(encoding="utf-8")
        self.assertIn("`alpha`", lib_text)
        self.assertNotIn("`beta`", lib_text)

        self.assertTrue(alpha_folder.exists(), "Subscribed mod folder should remain")
        self.assertFalse(beta_folder.exists(), "Unsubscribed pruned mod folder should be deleted")

        deleted_names = [d["name"] for d in results["actions"]["deleted_folders"]]
        self.assertIn("beta", deleted_names)

    @patch("scripts.modio_sync.fetch_subscribed_mods")
    def test_sync_library_prune_dry_run_retains_folder_and_row(self, mock_fetch):
        mock_fetch.return_value = [
            {"name_id": "alpha", "name": "Alpha Mod"},
        ]

        self.make_library([
            {"mod_id": "101", "name": "Alpha Mod", "slug": "alpha"},
            {"mod_id": "102", "name": "Beta Mod", "slug": "beta"},
        ])
        beta_folder = self.mods_dir / "beta"
        beta_folder.mkdir()

        results = sync_library(
            oauth_token="fake_token",
            api_key="fake_key",
            dry_run=True,
            prune=True,
            skip_updates=True,
            library_path=str(self.library_file),
            mods_dir=self.mods_dir,
        )

        lib_text = self.library_file.read_text(encoding="utf-8")
        self.assertIn("`beta`", lib_text, "Library row should not be removed in dry-run")
        self.assertTrue(beta_folder.exists(), "Folder should not be deleted in dry-run")

        deleted_statuses = [d["status"] for d in results["actions"]["deleted_folders"]]
        self.assertIn("dry_run_deleted", deleted_statuses)

    @patch("scripts.modio_sync.fetch_subscribed_mods")
    def test_sync_library_prune_deletes_orphaned_folders(self, mock_fetch):
        mock_fetch.return_value = [
            {"name_id": "alpha", "name": "Alpha Mod"},
        ]

        self.make_library([
            {"mod_id": "101", "name": "Alpha Mod", "slug": "alpha"},
        ])
        alpha_folder = self.mods_dir / "alpha"
        alpha_folder.mkdir()
        orphan_folder = self.mods_dir / "abandoned-orphan"
        orphan_folder.mkdir()

        # Run with prune=True
        results = sync_library(
            oauth_token="fake_token",
            api_key="fake_key",
            dry_run=False,
            prune=True,
            skip_updates=True,
            library_path=str(self.library_file),
            mods_dir=self.mods_dir,
        )

        self.assertTrue(alpha_folder.exists())
        self.assertFalse(orphan_folder.exists(), "Orphaned folder should be deleted when prune=True")

        deleted_names = [d["name"] for d in results["actions"]["deleted_folders"]]
        self.assertIn("abandoned-orphan", deleted_names)

    @patch("scripts.modio_sync.fetch_subscribed_mods")
    def test_sync_library_without_prune_retains_unsubscribed_and_orphaned(self, mock_fetch):
        mock_fetch.return_value = [
            {"name_id": "alpha", "name": "Alpha Mod"},
        ]

        self.make_library([
            {"mod_id": "101", "name": "Alpha Mod", "slug": "alpha"},
            {"mod_id": "102", "name": "Beta Mod", "slug": "beta"},
        ])
        beta_folder = self.mods_dir / "beta"
        beta_folder.mkdir()
        orphan_folder = self.mods_dir / "orphan-folder"
        orphan_folder.mkdir()

        results = sync_library(
            oauth_token="fake_token",
            api_key="fake_key",
            dry_run=False,
            prune=False,
            skip_updates=True,
            library_path=str(self.library_file),
            mods_dir=self.mods_dir,
        )

        self.assertTrue(beta_folder.exists())
        self.assertTrue(orphan_folder.exists())
        lib_text = self.library_file.read_text(encoding="utf-8")
        self.assertIn("`beta`", lib_text)


if __name__ == "__main__":
    unittest.main()

