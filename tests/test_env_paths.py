#!/usr/bin/env python3
"""
tests/test_env_paths.py
-----------------------
Unit tests for XDG Base Directory Specification compliance, cross-platform fallbacks,
cache directory resolution, and cascading configuration precedence in bg3_core.env_paths.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bg3_core.env_paths import (
    get_authored_mods_dir,
    get_build_guides_dir,
    get_cache_dir,
    get_env_source,
    get_env_var,
    get_library_catalog_path,
    get_studio_dir,
    get_subscribed_mods_dir,
    get_workspace_root,
    get_xdg_cache_home,
    get_xdg_config_home,
    get_xdg_data_home,
    get_xdg_documents_home,
    get_xdg_state_home,
    load_env_file,
)


class TestXDGPaths(unittest.TestCase):
    def test_default_xdg_paths_posix(self):
        """Test default POSIX paths when XDG environment variables are unset."""
        env_clean = {
            "XDG_CONFIG_HOME": "",
            "XDG_CACHE_HOME": "",
            "XDG_DATA_HOME": "",
            "XDG_STATE_HOME": "",
            "BG3_CACHE_DIR": "",
        }
        with patch.dict(os.environ, env_clean), patch("os.name", "posix"):
            home = Path.home()
            self.assertEqual(get_xdg_config_home(), home / ".config" / "bg3")
            self.assertEqual(get_xdg_cache_home(), home / ".cache" / "bg3")
            self.assertEqual(get_xdg_data_home(), home / ".local" / "share" / "bg3")
            self.assertEqual(get_xdg_state_home(), home / ".local" / "state" / "bg3")
            self.assertEqual(get_cache_dir(), home / ".cache" / "bg3")

    def test_xdg_environment_overrides(self):
        """Test that explicit XDG environment variables take precedence."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            custom_env = {
                "XDG_CONFIG_HOME": str(tmp_path / "custom_config"),
                "XDG_CACHE_HOME": str(tmp_path / "custom_cache"),
                "XDG_DATA_HOME": str(tmp_path / "custom_data"),
                "XDG_STATE_HOME": str(tmp_path / "custom_state"),
                "BG3_CACHE_DIR": "",
            }
            with patch.dict(os.environ, custom_env):
                self.assertEqual(get_xdg_config_home(), tmp_path / "custom_config" / "bg3")
                self.assertEqual(get_xdg_cache_home(), tmp_path / "custom_cache" / "bg3")
                self.assertEqual(get_xdg_data_home(), tmp_path / "custom_data" / "bg3")
                self.assertEqual(get_xdg_state_home(), tmp_path / "custom_state" / "bg3")
                self.assertEqual(get_cache_dir(), tmp_path / "custom_cache" / "bg3")

    def test_bg3_cache_dir_override(self):
        """Test that BG3_CACHE_DIR explicitly overrides XDG cache directory."""
        with tempfile.TemporaryDirectory() as tmp:
            cache_override = Path(tmp) / "explicit_cache"
            with patch.dict(os.environ, {"BG3_CACHE_DIR": str(cache_override)}):
                self.assertEqual(get_cache_dir(), cache_override)

    @unittest.skipIf(os.name != "nt", "WindowsPath cannot be instantiated on POSIX systems")
    def test_windows_fallbacks(self):
        """Test Windows AppData and LocalAppData resolution when running on NT."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            roaming = tmp_path / "AppData" / "Roaming"
            local = tmp_path / "AppData" / "Local"
            nt_env = {
                "XDG_CONFIG_HOME": "",
                "XDG_CACHE_HOME": "",
                "XDG_DATA_HOME": "",
                "XDG_STATE_HOME": "",
                "BG3_CACHE_DIR": "",
                "APPDATA": str(roaming),
                "LOCALAPPDATA": str(local),
            }
            with patch.dict(os.environ, nt_env):
                self.assertEqual(get_xdg_config_home(), roaming / "bg3")
                self.assertEqual(get_xdg_cache_home(), local / "bg3" / "cache")
                self.assertEqual(get_xdg_data_home(), local / "bg3" / "data")
                self.assertEqual(get_xdg_state_home(), local / "bg3" / "state")

    def test_repo_env_is_strictly_ignored(self):
        """Verify that in-repo .env file is NEVER consulted by load_env_file."""
        with tempfile.TemporaryDirectory() as tmp:
            fake_repo = Path(tmp)
            fake_env = fake_repo / ".env"
            fake_env.write_text("IN_REPO_VAR=should_never_be_read\n", encoding="utf-8")

            # Point REPO_ROOT to fake repo
            with patch("bg3_core.env_paths.REPO_ROOT", fake_repo):
                # Empty out any existing XDG config directory
                empty_xdg = fake_repo / "xdg_config"
                with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(empty_xdg)}, clear=False):
                    env = load_env_file()
                    self.assertNotIn("IN_REPO_VAR", env)
                    self.assertIsNone(get_env_var("IN_REPO_VAR"))

    def test_xdg_config_file_loading(self):
        """Verify that load_env_file reads configuration from $XDG_CONFIG_HOME/bg3/env."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_xdg = Path(tmp) / "config"
            bg3_cfg_dir = tmp_xdg / "bg3"
            bg3_cfg_dir.mkdir(parents=True)
            env_file = bg3_cfg_dir / "env"
            env_file.write_text("MODIO_API_KEY=test_api_key_123\nMODIO_PAT=test_pat_456\n", encoding="utf-8")

            with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_xdg), "MODIO_API_KEY": "", "MODIO_PAT": ""}):
                env = load_env_file()
                self.assertEqual(env.get("MODIO_API_KEY"), "test_api_key_123")
                self.assertEqual(env.get("MODIO_PAT"), "test_pat_456")
                self.assertEqual(get_env_var("MODIO_API_KEY"), "test_api_key_123")

    def test_configuration_precedence_hierarchy(self):
        """Verify that process environment overrides XDG configuration file."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_xdg = Path(tmp) / "config"
            bg3_cfg_dir = tmp_xdg / "bg3"
            bg3_cfg_dir.mkdir(parents=True)
            (bg3_cfg_dir / "env").write_text("TEST_KEY=from_xdg\n", encoding="utf-8")

            # 1. When unset in os.environ, reads from XDG config
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_xdg), "TEST_KEY": ""}):
                self.assertEqual(get_env_var("TEST_KEY"), "from_xdg")
                val, source = get_env_source("TEST_KEY")
                self.assertEqual(val, "from_xdg")
                self.assertIn("env", source)

            # 2. When set in os.environ, os.environ wins
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_xdg), "TEST_KEY": "from_env"}):
                self.assertEqual(get_env_var("TEST_KEY"), "from_env")
                val, source = get_env_source("TEST_KEY")
                self.assertEqual(val, "from_env")
                self.assertEqual(source, "environment")

    def test_studio_paths_defaults_and_overrides(self):
        """Test default studio paths and environment variable overrides."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_docs = Path(tmp) / "Documents"
            with patch.dict(os.environ, {"XDG_DOCUMENTS_DIR": str(tmp_docs), "BG3_STUDIO_DIR": ""}):
                self.assertEqual(get_xdg_documents_home(), tmp_docs)
                self.assertEqual(get_studio_dir(), tmp_docs / "BG3_Mod_Studio")
                self.assertEqual(get_build_guides_dir(), tmp_docs / "BG3_Mod_Studio" / "Build_Guides")
                self.assertEqual(get_subscribed_mods_dir(), tmp_docs / "BG3_Mod_Studio" / "Mods" / "subscribed")
                self.assertEqual(get_authored_mods_dir(), tmp_docs / "BG3_Mod_Studio" / "Mods" / "authored")

            # Custom BG3_STUDIO_DIR override
            custom_studio = Path(tmp) / "custom_studio"
            with patch.dict(os.environ, {"BG3_STUDIO_DIR": str(custom_studio)}):
                self.assertEqual(get_studio_dir(), custom_studio)
                self.assertEqual(get_build_guides_dir(), custom_studio / "Build_Guides")
                self.assertEqual(get_subscribed_mods_dir(), custom_studio / "Mods" / "subscribed")
                self.assertEqual(get_authored_mods_dir(), custom_studio / "Mods" / "authored")

            # Individual subfolder overrides
            with patch.dict(os.environ, {
                "BG3_STUDIO_DIR": str(custom_studio),
                "BG3_BUILD_GUIDES_DIR": str(Path(tmp) / "guides"),
                "BG3_SUBSCRIBED_MODS_DIR": str(Path(tmp) / "sub"),
                "BG3_AUTHORED_MODS_DIR": str(Path(tmp) / "auth"),
            }):
                self.assertEqual(get_build_guides_dir(), Path(tmp) / "guides")
                self.assertEqual(get_subscribed_mods_dir(), Path(tmp) / "sub")
                self.assertEqual(get_authored_mods_dir(), Path(tmp) / "auth")

    def test_library_catalog_path_resolution(self):
        """Test library catalog path resolution and environment overrides."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_docs = Path(tmp) / "Documents"
            with patch.dict(os.environ, {"XDG_DOCUMENTS_DIR": str(tmp_docs), "BG3_STUDIO_DIR": "", "BG3_LIBRARY_CATALOG_PATH": "", "BG3_LIBRARY_PATH": ""}):
                expected_default = tmp_docs / "BG3_Mod_Studio" / "Mods" / "subscribed" / "library.md"
                self.assertEqual(get_library_catalog_path(), expected_default)

            # Override via BG3_LIBRARY_CATALOG_PATH
            custom_catalog = Path(tmp) / "custom_library.md"
            with patch.dict(os.environ, {"BG3_LIBRARY_CATALOG_PATH": str(custom_catalog)}):
                self.assertEqual(get_library_catalog_path(), custom_catalog)

            # Override via BG3_LIBRARY_PATH
            with patch.dict(os.environ, {"BG3_LIBRARY_CATALOG_PATH": "", "BG3_LIBRARY_PATH": str(custom_catalog)}):
                self.assertEqual(get_library_catalog_path(), custom_catalog)

    def test_zero_repo_root_fallbacks(self):
        """Verify get_subscribed_mods_dir and get_authored_mods_dir never fall back to REPO_ROOT."""
        with tempfile.TemporaryDirectory() as tmp:
            empty_studio = Path(tmp) / "empty_studio"
            with patch.dict(os.environ, {"BG3_STUDIO_DIR": str(empty_studio)}):
                sub = get_subscribed_mods_dir()
                auth = get_authored_mods_dir()
                self.assertEqual(sub, empty_studio / "Mods" / "subscribed")
                self.assertEqual(auth, empty_studio / "Mods" / "authored")

    def test_get_workspace_root(self):
        """Verify dynamic workspace root discovery."""
        root = get_workspace_root()
        self.assertTrue((root / "pyproject.toml").is_file() or (root / ".git").is_dir())

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"BG3_WORKSPACE_ROOT": tmp}):
                self.assertEqual(get_workspace_root(), Path(tmp).resolve())

    def test_zero_parents_traversal_in_packages(self):
        """Assert zero fragile parents traversal or _REPO_ROOT assignments exist across packages."""
        repo_root = Path(__file__).resolve().parent.parent
        packages_dir = repo_root / "packages"
        forbidden_patterns = [
            "_REPO_ROOT = Path(__file__).resolve().parents",
            "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))",
            "workspace_root = Path(__file__).resolve().parents[2]",
        ]
        leaks = []
        for py_file in packages_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="replace")
            for pattern in forbidden_patterns:
                if pattern in text:
                    leaks.append(f"{py_file.relative_to(repo_root)}: contains '{pattern}'")

        self.assertEqual(leaks, [], f"Found forbidden path traversal patterns: {leaks}")


if __name__ == "__main__":
    unittest.main()
