"""
Unit tests for manage_load_order topological auto-sorting and dependency resolution.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bg3_core.profile.manage_load_order import (
    auto_sort_load_order,
    backup_file,
    create_default_modsettings,
    parse_modsettings,
    save_modsettings,
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
        from bg3_core.profile.manage_load_order import enable_mod
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

    def test_backup_file_microsecond_collision_deduplication(self) -> None:
        create_default_modsettings(self.modsettings_path)
        # Call backup_file in rapid succession
        b1 = backup_file(self.modsettings_path)
        b2 = backup_file(self.modsettings_path)
        b3 = backup_file(self.modsettings_path)
        self.assertTrue(b1.is_file())
        self.assertTrue(b2.is_file())
        self.assertTrue(b3.is_file())
        # All three must be distinct files
        self.assertEqual(len({b1, b2, b3}), 3)

    def test_save_modsettings_atomic_replace(self) -> None:
        create_default_modsettings(self.modsettings_path)
        import xml.etree.ElementTree as ET
        tree = ET.parse(self.modsettings_path)
        save_modsettings(self.modsettings_path, tree)
        self.assertTrue(self.modsettings_path.is_file())
        # Confirm no leftover temporary files in directory
        tmp_files = list(self.modsettings_path.parent.glob("*.tmp"))
        self.assertEqual(tmp_files, [])


class TestModResolverStrategies(unittest.TestCase):
    def test_resolve_dependency_metadata_with_custom_fetcher(self) -> None:
        from bg3_core.profile.mod_resolver import resolve_dependency_metadata

        mock_payload = {
            "Folder": "CustomMod",
            "MD5": "abc123",
            "Name": "Custom Mod Display",
            "PublishHandle": 9999,
            "UUID": "11111111-2222-3333-4444-555555555555",
            "Version64": 12345678,
        }

        def dummy_fetcher(clean_id: str, auto_doc: bool = True) -> dict:
            return mock_payload

        meta = resolve_dependency_metadata("unknown_query", remote_fetcher=dummy_fetcher)
        self.assertEqual(meta["UUID"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(meta["Name"], "Custom Mod Display")

    def test_ensure_dependency_paks_with_custom_downloader(self) -> None:
        from bg3_core.profile.mod_resolver import ensure_dependency_paks

        with tempfile.TemporaryDirectory() as tmp:
            t_dir = Path(tmp) / "target_mods"
            t_dir.mkdir()

            dep = {
                "Folder": "InjectedMod",
                "Name": "Injected Mod",
                "PublishHandle": 8888,
                "UUID": "22222222-3333-4444-5555-666666666666",
            }

            def dummy_downloader(d: dict) -> tuple[str, bytes]:
                return ("InjectedMod.pak", b"LSPK\x01\x00\x00\x00testpayload")

            results = ensure_dependency_paks([dep], target_dirs=[t_dir], remote_downloader=dummy_downloader)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["action"], "downloaded")
            self.assertTrue((t_dir / "InjectedMod.pak").is_file())
            self.assertEqual((t_dir / "InjectedMod.pak").read_bytes(), b"LSPK\x01\x00\x00\x00testpayload")


class TestCheckModDependenciesPreIndexed(unittest.TestCase):
    """Verifies pre-indexed dependency resolution in game data packaging."""

    def test_check_mod_dependencies_indexing(self) -> None:
        from bg3_authoring.packaging.sync_game_data import check_mod_dependencies

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            mod_path = tmp_root / "MyTestMod"
            meta_dir = mod_path / "Mods" / "MyTestMod"
            meta_dir.mkdir(parents=True)
            meta_file = meta_dir / "meta.lsx"
            meta_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<save>
    <region id="Config">
        <node id="root">
            <children>
                <node id="Dependencies">
                    <children>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="Gustav"/>
                            <attribute id="Name" type="LSString" value="Gustav"/>
                            <attribute id="UUID" type="FixedString" value="11111111-1111-1111-1111-111111111111"/>
                        </node>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="PresentPak"/>
                            <attribute id="Name" type="LSString" value="PresentPak"/>
                            <attribute id="UUID" type="FixedString" value="22222222-2222-2222-2222-222222222222"/>
                        </node>
                        <node id="ModuleShortDesc">
                            <attribute id="Folder" type="LSString" value="MissingDep"/>
                            <attribute id="Name" type="LSString" value="MissingDep"/>
                            <attribute id="UUID" type="FixedString" value="33333333-3333-3333-3333-333333333333"/>
                        </node>
                    </children>
                </node>
            </children>
        </node>
    </region>
</save>""", encoding="utf-8")

            data_dir = tmp_root / "Data"
            data_dir.mkdir()
            user_mods_dir = tmp_root / "UserMods"
            user_mods_dir.mkdir()
            (user_mods_dir / "PresentPak.pak").write_bytes(b"dummy pak")

            with patch.dict(os.environ, {"BG3_USER_MODS_DIR": str(user_mods_dir)}):
                missing = check_mod_dependencies(mod_path, data_dir)
                self.assertEqual(len(missing), 1)
                self.assertIn("MissingDep", missing[0])


if __name__ == "__main__":
    unittest.main()
