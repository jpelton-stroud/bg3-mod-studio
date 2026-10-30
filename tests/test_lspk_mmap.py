#!/usr/bin/env python3
"""
tests/test_lspk_mmap.py
-----------------------
Unit tests for zero-copy memory-mapped file access (mmap) in LspkArchive.
"""

import tempfile
import unittest
from pathlib import Path

from bg3_authoring.packaging.pack_mod_pak import build_pak_archive
from bg3_core.lspk import LspkArchive


class TestLspkMmap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pak_path = Path(self.temp_dir.name) / "test_mod.pak"

        self.sample_files = [
            ("Mods/TestMod/meta.lsx", b"<save><version>1</version></save>"),
            ("Public/TestMod/Stats/Armor.txt", b"new entry TestArmor\ntype Armor\n" * 20),
        ]
        pak_data = build_pak_archive(self.sample_files, compress=True)
        self.pak_path.write_bytes(pak_data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_open_with_mmap_extracts_entries(self):
        arc = LspkArchive.open(self.pak_path, use_mmap=True)
        try:
            self.assertEqual(arc.version, 18)
            self.assertEqual(len(arc.files), 2)
            self.assertIsNotNone(arc._mmap_obj)

            entry_map = {f["name"]: f for f in arc.files}
            meta_entry = entry_map["Mods/TestMod/meta.lsx"]
            extracted_meta = arc.extract_file(meta_entry)
            self.assertEqual(extracted_meta, b"<save><version>1</version></save>")

            armor_entry = entry_map["Public/TestMod/Stats/Armor.txt"]
            extracted_armor = arc.extract_file(armor_entry)
            self.assertEqual(extracted_armor, b"new entry TestArmor\ntype Armor\n" * 20)
        finally:
            arc.close()

    def test_open_context_manager_cleans_up(self):
        with LspkArchive.open(self.pak_path) as arc:
            self.assertIsNotNone(arc._mmap_obj)
            extracted = arc.extract_file(arc.files[0])
            self.assertTrue(len(extracted) > 0)

        # Context manager exit should close mmap and file
        self.assertIsNone(arc._mmap_obj)
        self.assertIsNone(arc._file_obj)

    def test_open_fallback_bytes_mode(self):
        with LspkArchive.open(self.pak_path, use_mmap=False) as arc:
            self.assertIsNone(arc._mmap_obj)
            self.assertEqual(len(arc.files), 2)
            extracted = arc.extract_file(arc.files[0])
            self.assertTrue(len(extracted) > 0)

    def test_invalid_magic_raises_value_error(self):
        corrupt_path = Path(self.temp_dir.name) / "corrupt.pak"
        corrupt_path.write_bytes(b"CORRUPTDATA123456789012345678901234567890")
        with self.assertRaises(ValueError):
            LspkArchive.open(corrupt_path)


if __name__ == "__main__":
    unittest.main()
