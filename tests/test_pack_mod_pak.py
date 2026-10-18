#!/usr/bin/env python3
"""Unit tests for LSPK v18 package creation, header validation, and LZ4 compression."""

import struct
import unittest
from pathlib import Path

from scripts.lib.lspk import LspkArchive, lz4_block_compress, lz4_block_decompress
from scripts.packaging.pack_mod_pak import build_pak_archive, verify_pak_archive


class TestLspkPackaging(unittest.TestCase):
    def test_lz4_block_roundtrip(self):
        """Test LZ4 compression and decompression across various payload sizes and patterns."""
        payloads = [
            b"",
            b"a",
            b"Hello world!",
            b"Repeatable pattern " * 50,
            bytes(range(256)) * 4,
        ]
        for data in payloads:
            comp = lz4_block_compress(data)
            decomp = lz4_block_decompress(comp, len(data))
            self.assertEqual(decomp, data, f"Mismatch for payload of length {len(data)}")

    def test_build_pak_archive_lspk_v18_header(self):
        """Test that the 40-byte header adheres strictly to LSPK v18 specification."""
        files = [
            ("Mods/Sample/meta.lsx", b"<save><version>1</version></save>"),
            ("Public/Sample/Stats/Generated/Data/Armor.txt", b"new entry Sample_Armor\ntype Armor\n"),
        ]
        pak = build_pak_archive(files, compress=True)
        self.assertGreaterEqual(len(pak), 40)

        magic, ver, fl_offset, fl_size, flags, priority, md5, num_parts = struct.unpack_from(
            "<4sIQIBB16sH", pak, 0
        )
        self.assertEqual(magic, b"LSPK")
        self.assertEqual(ver, 18)
        self.assertEqual(flags, 2)  # PackageFlags.AllowMemoryMapping
        self.assertEqual(priority, 0)
        self.assertEqual(num_parts, 1)  # Critical for BG3 engine recognition
        self.assertEqual(len(md5), 16)

        # File list offset and size checks
        self.assertLess(fl_offset, len(pak))
        self.assertEqual(fl_offset + fl_size, len(pak))

        # Check file list block prefix (<II -> num_files, comp_size)
        fl_header = pak[fl_offset : fl_offset + 8]
        num_files, comp_size = struct.unpack("<II", fl_header)
        self.assertEqual(num_files, 2)
        self.assertEqual(fl_size, 8 + comp_size)

        # Verify compressed file list decompresses to 2 * 272 bytes
        fl_comp_payload = pak[fl_offset + 8 : fl_offset + 8 + comp_size]
        fl_decomp = lz4_block_decompress(fl_comp_payload, num_files * 272)
        self.assertEqual(len(fl_decomp), 2 * 272)

    def test_lspk_archive_parsing_and_extraction(self):
        """Test that LspkArchive successfully parses and extracts files from generated packages."""
        files = [
            ("Mods/ModA/meta.lsx", b"meta-content-here"),
            ("Public/ModA/Data.txt", b"data-content-line-1\ndata-content-line-2\n" * 10),
        ]
        pak = build_pak_archive(files, compress=True)
        arc = LspkArchive(pak)

        self.assertEqual(arc.version, 18)
        self.assertEqual(arc.flags, 2)
        self.assertEqual(arc.num_parts, 1)
        self.assertEqual(len(arc.files), 2)

        file_names = {f["name"] for f in arc.files}
        self.assertIn("Mods/ModA/meta.lsx", file_names)
        self.assertIn("Public/ModA/Data.txt", file_names)

        self.assertTrue(verify_pak_archive(pak, files))

    def test_uncompressed_packaging(self):
        """Test packaging with compress=False sets appropriate flags and uncomp_size=0."""
        files = [
            ("Mods/ModB/meta.lsx", b"uncompressed-data"),
        ]
        pak = build_pak_archive(files, compress=False)
        arc = LspkArchive(pak)

        self.assertEqual(len(arc.files), 1)
        entry = arc.files[0]
        self.assertEqual(entry["flags"], 0)
        self.assertEqual(entry["disk_size"], len(b"uncompressed-data"))
        self.assertEqual(arc.extract_file(entry), b"uncompressed-data")
        self.assertTrue(verify_pak_archive(pak, files))

    def test_collect_mod_files_posix_paths_and_dotfile_filtering(self):
        """Test that collect_mod_files outputs POSIX forward slashes and filters dotfiles."""
        import tempfile
        from scripts.packaging.pack_mod_pak import collect_mod_files

        with tempfile.TemporaryDirectory() as tmp_dir:
            mod_dir = Path(tmp_dir)
            (mod_dir / ".test_deps.json").write_text('{"test": true}')
            (mod_dir / "README.md").write_text("# Doc")
            mod_sub = mod_dir / "Mods" / "TestMod"
            mod_sub.mkdir(parents=True)
            (mod_sub / "meta.lsx").write_text("<meta/>")
            loca_sub = mod_dir / "Localization" / "English"
            loca_sub.mkdir(parents=True)
            (loca_sub / "strings.xml").write_text(
                '<?xml version="1.0" encoding="utf-8"?><contentList><content contentuid="h1">Hello</content></contentList>'
            )

            entries = collect_mod_files(mod_dir)
            entry_names = [name for name, _ in entries]

            # Verify no backslashes
            for name in entry_names:
                self.assertNotIn("\\", name, f"Path contains backslash: {name}")

            # Verify forward slash entries
            self.assertIn("Mods/TestMod/meta.lsx", entry_names)
            self.assertIn("Localization/English/strings.loca", entry_names)

            # Verify dotfiles and excluded documentation are filtered out
            self.assertFalse(any(".test_deps.json" in name for name in entry_names))
            self.assertFalse(any("README.md" in name for name in entry_names))


if __name__ == "__main__":
    unittest.main()
