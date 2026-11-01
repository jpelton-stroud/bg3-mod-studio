"""tests/test_lsf_parser.py.

Unit tests for pure-Python LSF binary decompiler, AST data structures, and save game auditing.
"""

import unittest

from bg3_core.save_inspector import _parse_lsf_save_mods
from bg3_core.lsf import (
    TYPE_BOOL,
    TYPE_FIXED_STRING,
    TYPE_INT32,
    TYPE_INT64,
    TYPE_LS_STRING,
    TYPE_UUID,
    LsfAttribute,
    LsfDocument,
    LsfNode,
)


class TestLsfParser(unittest.TestCase):
    def test_lsf_roundtrip_compressed(self) -> None:
        """Verify building an AST, serializing to compressed LSOF bytes, and parsing back."""
        doc = LsfDocument(version=7, engine_version=36028797018963968)

        root = LsfNode(name="save")
        region = LsfNode(name="region")
        root.children.append(region)

        mod_node = LsfNode(name="ModuleShortDesc")
        mod_node.attributes["Name"] = LsfAttribute(name="Name", type_id=TYPE_LS_STRING, value="CustomSpells")
        mod_node.attributes["Folder"] = LsfAttribute(
            name="Folder", type_id=TYPE_LS_STRING, value="CustomSpells_11111111-2222-3333-4444-555555555555"
        )
        mod_node.attributes["UUID"] = LsfAttribute(
            name="UUID", type_id=TYPE_UUID, value="11111111-2222-3333-4444-555555555555"
        )
        mod_node.attributes["Version64"] = LsfAttribute(name="Version64", type_id=TYPE_INT64, value=36028797018963968)
        mod_node.attributes["Active"] = LsfAttribute(name="Active", type_id=TYPE_BOOL, value=True)

        region.children.append(mod_node)
        doc.root_nodes.append(root)

        # Serialize
        raw_bytes = doc.to_bytes(compress=True)
        self.assertTrue(raw_bytes.startswith(b"LSOF"))

        # Deserialize
        parsed_doc = LsfDocument.from_bytes(raw_bytes)
        self.assertEqual(parsed_doc.version, 7)
        self.assertEqual(len(parsed_doc.root_nodes), 1)
        self.assertEqual(parsed_doc.root_nodes[0].name, "save")

        # Query AST
        found_mod = parsed_doc.find_first("ModuleShortDesc")
        self.assertIsNotNone(found_mod)
        assert found_mod is not None
        self.assertEqual(found_mod.get_attr_value("Name"), "CustomSpells")
        self.assertEqual(found_mod.get_attr_value("UUID"), "11111111-2222-3333-4444-555555555555")
        self.assertEqual(found_mod.get_attr_value("Version64"), 36028797018963968)
        self.assertEqual(found_mod.get_attr_value("Active"), True)

    def test_lsf_roundtrip_uncompressed(self) -> None:
        """Verify uncompressed chunk roundtrip."""
        doc = LsfDocument(version=7, engine_version=100)
        root = LsfNode(name="root")
        child = LsfNode(name="Config")
        child.attributes["MaxFPS"] = LsfAttribute(name="MaxFPS", type_id=TYPE_INT32, value=144)
        root.children.append(child)
        doc.root_nodes.append(root)

        raw_bytes = doc.to_bytes(compress=False)
        parsed_doc = LsfDocument.from_bytes(raw_bytes)
        cfg_node = parsed_doc.find_first("Config")
        self.assertIsNotNone(cfg_node)
        assert cfg_node is not None
        self.assertEqual(cfg_node.get_attr_value("MaxFPS"), 144)

    def test_lsf_find_all(self) -> None:
        """Verify find_all returns multiple descendant nodes."""
        doc = LsfDocument(version=7)
        root = LsfNode(name="save")
        for i in range(3):
            item = LsfNode(name="Item")
            item.attributes["Id"] = LsfAttribute(name="Id", type_id=TYPE_INT32, value=i)
            root.children.append(item)
        doc.root_nodes.append(root)

        raw = doc.to_bytes(compress=True)
        parsed = LsfDocument.from_bytes(raw)
        items = parsed.find_all("Item")
        self.assertEqual(len(items), 3)
        self.assertEqual([it.get_attr_value("Id") for it in items], [0, 1, 2])

    def test_invalid_lsf_bytes(self) -> None:
        """Verify proper exceptions on invalid magic or truncated bytes."""
        with self.assertRaises(ValueError):
            LsfDocument.from_bytes(b"INVALID_HEADER_DATA")

        with self.assertRaises(ValueError):
            LsfDocument.from_bytes(b"LSOF\x01\x00\x00\x00")  # too short

    def test_inspect_save_game_lsf_ast_integration(self) -> None:
        """Verify _parse_lsf_save_mods extracts metadata using LSF AST parser."""
        doc = LsfDocument(version=7)
        save_root = LsfNode(name="save")
        mod1 = LsfNode(name="ModuleShortDesc")
        mod1.attributes["UUID"] = LsfAttribute(name="UUID", type_id=TYPE_UUID, value="22222222-3333-4444-5555-666666666666")
        mod1.attributes["Name"] = LsfAttribute(name="Name", type_id=TYPE_FIXED_STRING, value="EpicFeats")
        mod1.attributes["Folder"] = LsfAttribute(name="Folder", type_id=TYPE_FIXED_STRING, value="EpicFeats")
        mod1.attributes["Version64"] = LsfAttribute(name="Version64", type_id=TYPE_INT64, value=1000)

        save_root.children.append(mod1)
        doc.root_nodes.append(save_root)

        lsf_bytes = doc.to_bytes(compress=True)
        extracted_mods = _parse_lsf_save_mods(lsf_bytes)

        self.assertEqual(len(extracted_mods), 1)
        self.assertEqual(extracted_mods[0]["name"], "EpicFeats")
        self.assertEqual(extracted_mods[0]["uuid"], "22222222-3333-4444-5555-666666666666")
        self.assertEqual(extracted_mods[0]["folder"], "EpicFeats")
        self.assertEqual(extracted_mods[0]["version"], "1000")


if __name__ == "__main__":
    unittest.main()
