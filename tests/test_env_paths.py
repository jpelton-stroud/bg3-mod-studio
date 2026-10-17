#!/usr/bin/env python3
"""
tests/test_env_paths.py
-----------------------
Unit tests for XDG Base Directory Specification compliance, cross-platform fallbacks,
cache directory resolution, and cascading configuration precedence in scripts/lib/env_paths.py.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.lib.env_paths import (
    REPO_ROOT,
    get_cache_dir,
    get_env_source,
    get_env_var,
    get_xdg_cache_home,
    get_xdg_config_home,
    get_xdg_data_home,
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
            with patch("scripts.lib.env_paths.REPO_ROOT", fake_repo):
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


if __name__ == "__main__":
    unittest.main()
