"""
Unit tests for manage_load_order topological auto-sorting and dependency resolution.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bg3_core.manage_load_order import (
    auto_sort_load_order,
    create_default_modsettings,
    parse_modsettings,
    topological_sort_mods,
)


class TestManageLoadOrderAutoSort(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name)
        self.modsettings_path = self.test_root / "modsettings.lsx"
        self.workspace_mods = self.test_root / "my_mods"
        self.workspace_mods.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _create_mod_with_meta(self, folder_name: str, name: str, uuid: str, dep_uuids: list[str] | None = None, version64: str = "36028797018963968") -> Path:
        mod_dir = self.workspace_mods / folder_name
        meta_dir = mod_dir / "Mods" / folder_name
        meta_dir.mkdir(parents=True, exist_ok=True)

        dep_xml = ""
        if dep_uuids:
            dep_nodes = []
            for du in dep_uuids:
                dep_nodes.append(f"""
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="Dep_{du[:8]}"/>
                            <attribute id="MD5" type="LSString" value=""/>
                            <attribute id="Name" type="LSString" value="Dep_{du[:8]}"/>
                            <attribute id="PublishHandle" type="uint64" value="0"/>
                            <attribute id="UUID" type="FixedString" value="{du}"/>
                            <attribute id="Version64" type="int64" value="36028797018963968"/>
                        </node>""")
            dep_xml = f"""
                <node id="Dependencies">
                    <children>
                        {''.join(dep_nodes)}
                    </children>
                </node>"""
        else:
            dep_xml = """
                <node id="Dependencies"/>"""

        meta_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<save>
    <version major="4" minor="8" revision="0" build="700"/>
    <region id="Config">
        <node id="root">
            <children>
                {dep_xml}
                <node id="ModuleInfo">
                    <attribute id="Folder" type="LSString" value="{folder_name}"/>
                    <attribute id="MD5" type="LSString" value=""/>
                    <attribute id="Name" type="LSString" value="{name}"/>
                    <attribute id="PublishHandle" type="uint64" value="0"/>
                    <attribute id="UUID" type="FixedString" value="{uuid}"/>
                    <attribute id="Version64" type="int64" value="{version64}"/>
                </node>
            </children>
        </node>
    </region>
</save>"""
        meta_file = meta_dir / "meta.lsx"
        meta_file.write_text(meta_content, encoding="utf-8")
        return mod_dir

    def test_topological_sort_mods_framework_priority(self) -> None:
        active_mods = {
            "33333333-3333-3333-3333-333333333333": {"Name": "ZedMod", "UUID": "33333333-3333-3333-3333-333333333333"},
            "22222222-2222-2222-2222-222222222222": {"Name": "CommunityLibrary", "UUID": "22222222-2222-2222-2222-222222222222"},
            "11111111-1111-1111-1111-111111111111": {"Name": "CompatibilityFramework", "UUID": "11111111-1111-1111-1111-111111111111"},
        }
        dep_graph: dict[str, list[str]] = {u: [] for u in active_mods}
        sorted_uuids = topological_sort_mods(active_mods, dep_graph)

        self.assertEqual(sorted_uuids[0], "22222222-2222-2222-2222-222222222222")  # CommunityLibrary first
        self.assertEqual(sorted_uuids[1], "11111111-1111-1111-1111-111111111111")  # CompatibilityFramework second
        self.assertEqual(sorted_uuids[2], "33333333-3333-3333-3333-333333333333")  # ZedMod third

    def test_auto_sort_load_order_resolves_workspace_dependencies(self) -> None:
        create_default_modsettings(self.modsettings_path)

        # Mod B is prerequisite, Mod A depends on Mod B
        uuid_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        uuid_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

        self._create_mod_with_meta("ModB", "ModB", uuid_b)
        self._create_mod_with_meta("ModA", "ModA", uuid_a, dep_uuids=[uuid_b])

        # Inject ModA first, then ModB into modsettings.lsx (reverse order)
        from bg3_core.manage_load_order import enable_mod
        with patch.dict(os.environ, {"BG3_MODS_DIR": str(self.workspace_mods)}):
            enable_mod(self.modsettings_path, "ModA")
            enable_mod(self.modsettings_path, "ModB")

            # Check that ModA was enabled before ModB initially
            parsed_initial = parse_modsettings(self.modsettings_path)
            custom_mods = [u for u in parsed_initial["order"] if u in (uuid_a, uuid_b)]
            self.assertEqual(custom_mods, [uuid_a, uuid_b])

            # Run auto-sort
            success, sorted_uuids, meta = auto_sort_load_order(self.modsettings_path, dry_run=False)
            self.assertTrue(success)

            # Check new order in file: ModB MUST appear before ModA
            parsed_sorted = parse_modsettings(self.modsettings_path)
            idx_b = parsed_sorted["order"].index(uuid_b)
            idx_a = parsed_sorted["order"].index(uuid_a)
            self.assertLess(idx_b, idx_a, "Prerequisite ModB must be ordered before dependent ModA")


if __name__ == "__main__":
    unittest.main()
