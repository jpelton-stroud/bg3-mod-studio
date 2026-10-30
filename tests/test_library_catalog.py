#!/usr/bin/env python3
"""
tests/test_library_catalog.py
-----------------------------
Unit tests for centralized library catalog queries, tracked mod discovery,
row pruning, orphan detection, and safe folder deletion in bg3_core.library_catalog.
"""

import tempfile
import unittest
from pathlib import Path

from bg3_core.library_catalog import (
    find_mod_folder,
    find_orphaned_folders,
    get_tracked_mod_identifiers,
    get_tracked_mods,
    parse_library_rows,
    prune_mod_from_library,
    safe_batch_delete_folders,
)


class LibraryCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.mods_dir = self.root / "mods"
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

    def test_get_tracked_mods_and_identifiers(self):
        self.make_library([
            {"mod_id": "101", "name": "Alpha Blade", "slug": "alpha-blade", "desc": "A sharp blade", "features": "3 implemented"},
            {"mod_id": "202", "name": "Beta Shield", "slug": "beta-shield", "desc": "A sturdy shield", "features": "5 implemented"},
        ])

        tracked = get_tracked_mods(self.library_file, workspace_root=self.root)
        self.assertEqual(len(tracked), 2)
        self.assertEqual(tracked["alpha-blade"]["mod_id"], "101")
        self.assertEqual(tracked["alpha-blade"]["name"], "Alpha Blade")
        self.assertEqual(tracked["alpha-blade"]["features_count"], 3)
        self.assertEqual(tracked["beta-shield"]["features_count"], 5)

        slugs, names = get_tracked_mod_identifiers(self.library_file, workspace_root=self.root)
        self.assertEqual(slugs, {"alpha-blade", "beta-shield"})
        self.assertEqual(names, {"alpha blade", "beta shield"})

    def test_get_tracked_mods_with_filesystem_discovery(self):
        self.make_library([
            {"mod_id": "101", "name": "Tracked Mod", "slug": "tracked-mod"},
        ])
        # Add undocumented mod directory with README.md
        undoc_dir = self.mods_dir / "undocumented-mod"
        undoc_dir.mkdir()
        (undoc_dir / "README.md").write_text("# Undocumented Mod", encoding="utf-8")

        tracked_without_fs = get_tracked_mods(self.library_file, include_filesystem=False, workspace_root=self.root)
        self.assertNotIn("undocumented-mod", tracked_without_fs)

        tracked_with_fs = get_tracked_mods(self.library_file, include_filesystem=True, workspace_root=self.root)
        self.assertIn("undocumented-mod", tracked_with_fs)
        self.assertEqual(tracked_with_fs["undocumented-mod"]["features_count"], 0)

    def test_prune_mod_from_library(self):
        self.make_library([
            {"mod_id": "101", "name": "Keep Mod", "slug": "keep-mod"},
            {"mod_id": "102", "name": "Remove Mod", "slug": "remove-mod"},
        ])

        self.assertTrue(prune_mod_from_library(self.library_file, "remove-mod"))
        content = self.library_file.read_text(encoding="utf-8")
        self.assertNotIn("remove-mod", content)
        self.assertIn("keep-mod", content)

        # Attempt to prune already removed mod
        self.assertFalse(prune_mod_from_library(self.library_file, "remove-mod"))

    def test_find_mod_folder_and_orphans(self):
        active_dir = self.mods_dir / "active-gear"
        active_dir.mkdir()
        orphan_dir = self.mods_dir / "orphaned-gear"
        orphan_dir.mkdir()
        hidden_dir = self.mods_dir / ".git_test"
        hidden_dir.mkdir()

        # Find mod folder
        self.assertEqual(find_mod_folder("active-gear", self.mods_dir), active_dir)
        self.assertEqual(find_mod_folder("ActiveGear", self.mods_dir), active_dir)
        self.assertIsNone(find_mod_folder("unknown-gear", self.mods_dir))

        # Orphans
        orphans = find_orphaned_folders(self.mods_dir, active_slugs=["active-gear"])
        self.assertEqual([o.name for o in orphans], ["orphaned-gear"])

    def test_safe_batch_delete_folders(self):
        target = self.mods_dir / "target"
        target.mkdir()

        dry_res = safe_batch_delete_folders([target], mods_dir=self.mods_dir, dry_run=True)
        self.assertEqual(dry_res[0]["status"], "dry_run_deleted")
        self.assertTrue(target.exists())

        del_res = safe_batch_delete_folders([target], mods_dir=self.mods_dir, dry_run=False)
        self.assertEqual(del_res[0]["status"], "deleted")
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
