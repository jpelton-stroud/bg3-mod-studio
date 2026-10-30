"""Unit tests for bg3_core.tools dynamic in-memory registry and discovery."""

import unittest

from bg3_core.cli import build_parser
from bg3_core.tools import (
    extract_registry_from_parser,
    find_tool,
    load_registry,
    search_tools,
    verify_registry,
)


class TestToolsRegistry(unittest.TestCase):

    def setUp(self):
        self.parser = build_parser()
        self.registry = load_registry(force_refresh=True)

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

    def test_zero_legacy_script_aliases_in_registry(self):
        """Assert that no tool has a .py script alias in the dynamic registry."""
        for tool in self.registry["tools"]:
            name = tool["name"]
            for alias in tool.get("aliases", []):
                self.assertFalse(
                    alias.endswith(".py"),
                    f"Legacy .py script alias '{alias}' found in tool '{name}'",
                )
            for intent in tool.get("intents", []):
                self.assertFalse(
                    intent.endswith(".py"),
                    f"Legacy .py intent '{intent}' found in tool '{name}'",
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

        # By alias (scaffold class vs mod class)
        t3 = find_tool(self.registry, "scaffold class")
        self.assertIsNotNone(t3)

    def test_search_tools(self):
        results = search_tools(self.registry, "scaffold class")
        self.assertTrue(len(results) > 0)
        top_names = [r["name"] for r in results[:3]]
        self.assertTrue(any("class" in n for n in top_names))

    def test_verify_registry_passes(self):
        res = verify_registry(self.registry)
        self.assertTrue(res["valid"], f"Registry verification failed: {res}")
        self.assertEqual(len(res["missing_docs"]), 0)
        self.assertEqual(len(res["help_errors"]), 0)
        self.assertGreaterEqual(res["total_registered"], 50)


if __name__ == "__main__":
    unittest.main()
