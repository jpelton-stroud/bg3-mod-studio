"""Unit tests for bg3_core.registry_builder and dynamic registry synchronization."""

import json
import unittest
from pathlib import Path

from bg3_core.cli import build_parser
from bg3_core.registry_builder import (
    LEGACY_SCRIPT_ALIASES,
    extract_registry_from_parser,
)
from bg3_core.tools import find_tool, load_registry, search_tools, verify_registry


class TestRegistryBuilder(unittest.TestCase):

    def setUp(self):
        self.parser = build_parser()
        self.registry = extract_registry_from_parser(self.parser)

    def test_extract_registry_metadata(self):
        self.assertIn("version", self.registry)
        self.assertEqual(self.registry["version"], "1.0.0")
        self.assertIn("tools", self.registry)
        self.assertIsInstance(self.registry["tools"], list)
        self.assertGreaterEqual(len(self.registry["tools"]), 50)

    def test_canonical_categories_present(self):
        tools = self.registry["tools"]
        categories = {t["category"] for t in tools}
        expected_categories = {
            "authoring",
            "packaging",
            "diagnostics",
            "management",
            "library",
            "theorycrafting",
        }
        for cat in expected_categories:
            self.assertIn(cat, categories)

    def test_tool_entry_fields(self):
        for tool in self.registry["tools"]:
            name = tool["name"]
            self.assertTrue(name)
            self.assertTrue(tool["summary"], f"Missing summary for {name}")
            self.assertTrue(tool["category"], f"Missing category for {name}")
            self.assertTrue(tool["command"], f"Missing command for {name}")
            self.assertIsInstance(tool["flags"], list)
            self.assertIsInstance(tool["aliases"], list)
            self.assertIsInstance(tool["intents"], list)

    def test_legacy_script_aliases_mapped(self):
        tools_by_name = {t["name"]: t for t in self.registry["tools"]}
        for legacy_script, canonical_name in LEGACY_SCRIPT_ALIASES.items():
            self.assertIn(
                canonical_name,
                tools_by_name,
                f"Canonical command '{canonical_name}' not found in registry",
            )
            self.assertIn(
                legacy_script,
                tools_by_name[canonical_name]["aliases"],
                f"Alias '{legacy_script}' not found in '{canonical_name}'",
            )

    def test_find_tool_by_canonical_and_alias(self):
        # By full canonical command
        t1 = find_tool(self.registry, "bg3 mod create")
        self.assertIsNotNone(t1)
        self.assertEqual(t1["name"], "mod create")

        # By short name
        t2 = find_tool(self.registry, "mod create")
        self.assertIsNotNone(t2)
        self.assertEqual(t2["name"], "mod create")

        # By legacy script alias
        t3 = find_tool(self.registry, "create_mod_scaffold.py")
        self.assertIsNotNone(t3)
        self.assertEqual(t3["name"], "mod create")

        t4 = find_tool(self.registry, "manage_load_order.py")
        self.assertIsNotNone(t4)
        self.assertEqual(t4["name"], "loadorder list")

    def test_search_tools(self):
        results = search_tools(self.registry, "scaffold class")
        self.assertTrue(len(results) > 0)
        top_names = [r["name"] for r in results[:3]]
        self.assertIn("scaffold class", top_names)

    def test_registry_json_file_in_sync(self):
        json_path = (
            Path(__file__).resolve().parent.parent
            / "packages"
            / "bg3-core"
            / "bg3_core"
            / "registry.json"
        )
        self.assertTrue(json_path.exists(), "registry.json should exist")
        with open(json_path, "r", encoding="utf-8") as f:
            disk_registry = json.load(f)

        disk_names = {t["name"] for t in disk_registry["tools"]}
        extracted_names = {t["name"] for t in self.registry["tools"]}
        self.assertEqual(
            disk_names,
            extracted_names,
            "registry.json tool names differ from build_parser() extraction",
        )

    def test_verify_registry_passes(self):
        res = verify_registry(self.registry)
        self.assertTrue(res["valid"], f"Registry verification failed: {res}")
        self.assertEqual(len(res["missing_docs"]), 0)
        self.assertEqual(len(res["help_errors"]), 0)
        self.assertGreaterEqual(res["total_registered"], 50)


if __name__ == "__main__":
    unittest.main()
