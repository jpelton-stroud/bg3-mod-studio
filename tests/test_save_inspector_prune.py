#!/usr/bin/env python3
"""tests/test_save_inspector_prune.py.

Unit tests for BG3 save game mod pruning, AST deserialization/reserialization,
and non-destructive .lsv package repair.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bg3_core.lsf import (
    TYPE_FIXED_STRING,
    TYPE_INT64,
    TYPE_LS_STRING,
    TYPE_UUID,
    LsfAttribute,
    LsfDocument,
    LsfNode,
)
from bg3_core.lspk import LspkArchive, build_lspk_archive
from bg3_core.save_inspector import (
    extract_save_metadata,
    prune_missing_mods_from_save,
)


class TestSaveInspectorPrune(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _create_synthetic_lsf_save(
        self,
        mods: list[dict[str, str]],
        save_name: str = "TestSave.lsv",
    ) -> Path:
        """Constructs a minimal valid .lsv save file containing binary LSF metadata."""
        doc = LsfDocument(version=7, engine_version=36028797018963968)
        root = LsfNode(name="save")
        region = LsfNode(name="region")
        root.children.append(region)

        for m in mods:
            mod_node = LsfNode(name="ModuleShortDesc")
            mod_node.attributes["UUID"] = LsfAttribute(name="UUID", type_id=TYPE_UUID, value=m["uuid"])
            mod_node.attributes["Name"] = LsfAttribute(name="Name", type_id=TYPE_LS_STRING, value=m["name"])
            mod_node.attributes["Folder"] = LsfAttribute(name="Folder", type_id=TYPE_FIXED_STRING, value=m["folder"])
            mod_node.attributes["Version64"] = LsfAttribute(name="Version64", type_id=TYPE_INT64, value=1000)
            region.children.append(mod_node)

        doc.root_nodes.append(root)
        meta_lsf_bytes = doc.to_bytes(compress=True)

        save_info = {
            "Current Level": "WLD_Main_A",
            "Game Version": "4.1.1.5022896",
        }
        save_info_bytes = json.dumps(save_info).encode("utf-8")
        dummy_story_bytes = b"DUMMY_GAME_STATE_PAYLOAD_1234567890"

        files = [
            ("meta.lsf", meta_lsf_bytes),
            ("SaveInfo.json", save_info_bytes),
            ("story.save", dummy_story_bytes),
        ]
        pak_bytes = build_lspk_archive(files, compress=True)

        save_path = self.dir_path / save_name
        save_path.write_bytes(pak_bytes)
        return save_path

    def _create_synthetic_lsx_save(
        self,
        mods: list[dict[str, str]],
        save_name: str = "TestXmlSave.lsv",
    ) -> Path:
        """Constructs a minimal valid .lsv save file containing XML meta.lsx metadata."""
        nodes_xml = []
        for m in mods:
            nodes_xml.append(
                f'<node id="ModuleShortDesc">'
                f'<attribute id="Folder" type="LSString" value="{m["folder"]}"/>'
                f'<attribute id="Name" type="LSString" value="{m["name"]}"/>'
                f'<attribute id="UUID" type="FixedString" value="{m["uuid"]}"/>'
                f'<attribute id="Version64" type="int64" value="1000"/>'
                f"</node>"
            )

        meta_lsx = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<save>\n'
            '  <version major="4" minor="0" revision="9" build="331"/>\n'
            '  <region id="SaveInfo">\n'
            '    <node id="root">\n'
            '      <children>\n'
            '        <node id="Mods">\n'
            '          <children>\n'
            + "\n".join(nodes_xml)
            + "\n          </children>\n"
            "        </node>\n"
            "      </children>\n"
            "    </node>\n"
            "  </region>\n"
            "</save>"
        )

        files = [
            ("meta.lsx", meta_lsx.encode("utf-8")),
            ("SaveInfo.json", b'{"Current Level": "Act1"}'),
        ]
        pak_bytes = build_lspk_archive(files, compress=True)
        save_path = self.dir_path / save_name
        save_path.write_bytes(pak_bytes)
        return save_path

    def test_prune_lsf_missing_mods_to_output_file(self) -> None:
        """Verify targeted mod UUID is pruned from binary LSF AST and cleanly repacked."""
        mod1 = {"uuid": "11111111-1111-1111-1111-111111111111", "name": "PreservedMod", "folder": "PreservedMod"}
        mod2 = {"uuid": "22222222-2222-2222-2222-222222222222", "name": "MissingOrphanMod", "folder": "MissingOrphanMod"}

        source_save = self._create_synthetic_lsf_save([mod1, mod2], "Campaign1.lsv")
        out_save = self.dir_path / "Campaign1_Rescued.lsv"

        # Verify initial metadata has 2 mods
        initial_meta = extract_save_metadata(source_save)
        self.assertEqual(len(initial_meta["mods"]), 2)

        # Prune mod2
        ok, pruned = prune_missing_mods_from_save(
            save_path=source_save,
            output_path=out_save,
            target_uuids=["22222222-2222-2222-2222-222222222222"],
            dry_run=False,
        )

        self.assertTrue(ok)
        self.assertEqual(len(pruned), 1)
        self.assertIn("MissingOrphanMod", pruned)
        self.assertTrue(out_save.exists())

        # Inspect rescued save
        rescued_meta = extract_save_metadata(out_save)
        self.assertEqual(len(rescued_meta["mods"]), 1)
        self.assertEqual(rescued_meta["mods"][0]["uuid"], mod1["uuid"])
        self.assertEqual(rescued_meta["mods"][0]["name"], "PreservedMod")
        self.assertEqual(rescued_meta["level_name"], "WLD_Main_A")

        # Verify other files preserved intact
        with LspkArchive.open(out_save) as arc:
            file_names = {f["name"] for f in arc.files}
            self.assertIn("meta.lsf", file_names)
            self.assertIn("SaveInfo.json", file_names)
            self.assertIn("story.save", file_names)

            for entry in arc.files:
                if entry["name"] == "story.save":
                    data = arc.extract_file(entry)
                    self.assertEqual(data, b"DUMMY_GAME_STATE_PAYLOAD_1234567890")

    def test_prune_lsf_dry_run_does_not_modify(self) -> None:
        """Verify dry-run returns planned pruned list without modifying files."""
        mod1 = {"uuid": "11111111-1111-1111-1111-111111111111", "name": "Mod1", "folder": "Mod1"}
        mod2 = {"uuid": "22222222-2222-2222-2222-222222222222", "name": "Mod2", "folder": "Mod2"}

        save = self._create_synthetic_lsf_save([mod1, mod2], "DryRunSave.lsv")
        initial_mtime = save.stat().st_mtime_ns

        ok, pruned = prune_missing_mods_from_save(
            save_path=save,
            target_uuids=["22222222-2222-2222-2222-222222222222"],
            dry_run=True,
        )

        self.assertTrue(ok)
        self.assertEqual(len(pruned), 1)
        self.assertIn("Mod2", pruned)
        self.assertEqual(save.stat().st_mtime_ns, initial_mtime)

        # Still has 2 mods
        meta = extract_save_metadata(save)
        self.assertEqual(len(meta["mods"]), 2)

    def test_prune_in_place_creates_backup(self) -> None:
        """Verify in-place pruning creates a .bak backup file."""
        mod1 = {"uuid": "11111111-1111-1111-1111-111111111111", "name": "Mod1", "folder": "Mod1"}
        mod2 = {"uuid": "22222222-2222-2222-2222-222222222222", "name": "Mod2", "folder": "Mod2"}

        save = self._create_synthetic_lsf_save([mod1, mod2], "InPlaceSave.lsv")
        backup = save.with_name("InPlaceSave.lsv.bak")

        ok, pruned = prune_missing_mods_from_save(
            save_path=save,
            output_path=None,
            target_uuids=["22222222-2222-2222-2222-222222222222"],
            dry_run=False,
        )

        self.assertTrue(ok)
        self.assertTrue(backup.exists())

        # Backup has original 2 mods
        backup_meta = extract_save_metadata(backup)
        self.assertEqual(len(backup_meta["mods"]), 2)

        # Repaired file has 1 mod
        repaired_meta = extract_save_metadata(save)
        self.assertEqual(len(repaired_meta["mods"]), 1)
        self.assertEqual(repaired_meta["mods"][0]["uuid"], mod1["uuid"])

    def test_prune_xml_save(self) -> None:
        """Verify pruning works for saves using XML meta.lsx."""
        mod1 = {"uuid": "33333333-3333-3333-3333-333333333333", "name": "XmlMod1", "folder": "XmlMod1"}
        mod2 = {"uuid": "44444444-4444-4444-4444-444444444444", "name": "XmlMod2", "folder": "XmlMod2"}

        save = self._create_synthetic_lsx_save([mod1, mod2], "XmlSave.lsv")
        out_save = self.dir_path / "XmlSave_Cleaned.lsv"

        ok, pruned = prune_missing_mods_from_save(
            save_path=save,
            output_path=out_save,
            target_uuids=["44444444-4444-4444-4444-444444444444"],
            dry_run=False,
        )

        self.assertTrue(ok)
        self.assertEqual(len(pruned), 1)
        self.assertIn("XmlMod2", pruned)

        meta = extract_save_metadata(out_save)
        self.assertEqual(len(meta["mods"]), 1)
        self.assertEqual(meta["mods"][0]["uuid"], mod1["uuid"])


if __name__ == "__main__":
    unittest.main()
