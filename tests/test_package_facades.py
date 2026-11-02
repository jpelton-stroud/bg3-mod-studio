#!/usr/bin/env python3
"""
test_package_facades.py
------------------------
Contract unit tests verifying public API facades and __all__ exports for:
- bg3_core
- bg3_authoring
- bg3_theorycraft
"""

from __future__ import annotations

import unittest


class TestPackageFacades(unittest.TestCase):
    def test_bg3_core_public_exports(self) -> None:
        import bg3_core

        self.assertTrue(hasattr(bg3_core, "__all__"))
        self.assertGreater(len(bg3_core.__all__), 20)
        self.assertEqual(getattr(bg3_core, "__version__", None), "1.0.0")

        for symbol in bg3_core.__all__:
            self.assertTrue(
                hasattr(bg3_core, symbol),
                f"Exported symbol '{symbol}' not found on bg3_core",
            )

        # Core binary engines
        self.assertTrue(callable(bg3_core.build_lspk_archive))
        self.assertIsNotNone(bg3_core.LspkArchive)
        self.assertIsNotNone(bg3_core.LsfDocument)

        # Larian parsers
        self.assertTrue(callable(bg3_core.calculate_version64))
        self.assertTrue(callable(bg3_core.compile_xml_bytes_to_loca))
        self.assertEqual(bg3_core.DEFAULT_VERSION64, 36028797018963968)

        # Environment
        self.assertTrue(callable(bg3_core.get_workspace_root))
        self.assertTrue(callable(bg3_core.get_studio_dir))

    def test_bg3_core_subpackages(self) -> None:
        import bg3_core.binary
        import bg3_core.cli
        import bg3_core.modio
        import bg3_core.profile

        # Binary subpackage
        self.assertTrue(hasattr(bg3_core.binary, "__all__"))
        self.assertIsNotNone(bg3_core.binary.LspkArchive)
        self.assertIsNotNone(bg3_core.binary.LsfDocument)
        self.assertTrue(callable(bg3_core.binary.calculate_version64))
        self.assertEqual(bg3_core.binary.DEFAULT_VERSION64, 36028797018963968)

        # Modio subpackage
        self.assertTrue(hasattr(bg3_core.modio, "__all__"))
        self.assertIsNotNone(bg3_core.modio.ModioClient)

        # Profile subpackage
        self.assertTrue(hasattr(bg3_core.profile, "__all__"))
        self.assertTrue(callable(bg3_core.profile.auto_sort_load_order))

        # CLI subpackage
        self.assertTrue(hasattr(bg3_core.cli, "__all__"))
        self.assertTrue(callable(bg3_core.cli.main))
        self.assertTrue(callable(bg3_core.cli.build_parser))

    def test_bg3_authoring_public_exports(self) -> None:
        import bg3_authoring

        self.assertTrue(hasattr(bg3_authoring, "__all__"))
        self.assertGreater(len(bg3_authoring.__all__), 25)
        self.assertEqual(getattr(bg3_authoring, "__version__", None), "1.0.0")

        for symbol in bg3_authoring.__all__:
            self.assertTrue(
                hasattr(bg3_authoring, symbol),
                f"Exported symbol '{symbol}' not found on bg3_authoring",
            )

        # Scaffolding
        self.assertTrue(callable(bg3_authoring.scaffold_mod))
        self.assertTrue(callable(bg3_authoring.scaffold_class))
        self.assertTrue(callable(bg3_authoring.scaffold_asset))

        # Diagnostics & Packaging
        self.assertTrue(callable(bg3_authoring.collect_mod_files))
        self.assertTrue(callable(bg3_authoring.check_uuid_uniqueness))
        self.assertTrue(callable(bg3_authoring.sync_mod))

    def test_bg3_theorycraft_public_exports(self) -> None:
        import bg3_theorycraft

        self.assertTrue(hasattr(bg3_theorycraft, "__all__"))
        self.assertGreater(len(bg3_theorycraft.__all__), 15)

        for symbol in bg3_theorycraft.__all__:
            self.assertTrue(
                hasattr(bg3_theorycraft, symbol),
                f"Exported symbol '{symbol}' not found on bg3_theorycraft",
            )

        self.assertTrue(callable(bg3_theorycraft.simulate_build))
        self.assertTrue(callable(bg3_theorycraft.simulate_turn_1_dpr))


if __name__ == "__main__":
    unittest.main()
