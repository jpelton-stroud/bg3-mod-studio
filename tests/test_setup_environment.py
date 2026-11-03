#!/usr/bin/env python3
"""
tests/test_setup_environment.py
-------------------------------
Unit and integration tests for environment wizard prompts, subscription sync,
custom mod purge, and non-interactive safety guards in bg3_core.setup_environment.
"""

import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bg3_core.cli.setup_environment import (
    handle_subscription_sync,
    prompt_subscription_sync,
    run_wizard,
)


class SetupEnvironmentQATests(unittest.TestCase):
    def setUp(self):
        self._stdout_patcher = patch("sys.stdout", new_callable=io.StringIO)
        self.mock_stdout = self._stdout_patcher.start()

    def tearDown(self):
        self._stdout_patcher.stop()
    def test_prompt_subscription_sync_non_interactive(self):
        # Non-interactive mode must return option "3" (continue without sync)
        choice = prompt_subscription_sync(non_interactive=True)
        self.assertEqual(choice, "3")

    @patch("builtins.input", side_effect=[""])
    def test_prompt_subscription_sync_default(self, _mock_input):
        # Pressing Enter defaults to option "1"
        choice = prompt_subscription_sync(non_interactive=False)
        self.assertEqual(choice, "1")

    @patch("builtins.input", side_effect=["2"])
    def test_prompt_subscription_sync_option_2(self, _mock_input):
        choice = prompt_subscription_sync(non_interactive=False)
        self.assertEqual(choice, "2")

    @patch("builtins.input", side_effect=["4"])
    def test_prompt_subscription_sync_option_4(self, _mock_input):
        choice = prompt_subscription_sync(non_interactive=False)
        self.assertEqual(choice, "4")

    @patch("builtins.input", side_effect=[EOFError])
    def test_prompt_subscription_sync_eof(self, _mock_input):
        # On EOF in interactive mode, default to 1; in non-interactive, default to 3
        self.assertEqual(prompt_subscription_sync(non_interactive=False), "1")
        self.assertEqual(prompt_subscription_sync(non_interactive=True), "3")

    def test_handle_subscription_sync_dry_run(self):
        # Must execute without raising exceptions in dry-run mode for all choices
        for choice in ("1", "2", "3", "4"):
            with self.subTest(choice=choice):
                handle_subscription_sync(choice, dry_run=True)

    def test_run_wizard_omits_legacy_custom_mods_purge(self):
        """Assert that run_wizard completes without prompting for or executing legacy custom mods purge."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            with patch("bg3_core.cli.setup_environment.WORKSPACE_ROOT", temp_root):
                # Run wizard in non-interactive dry-run mode
                run_wizard(dry_run=True, non_interactive=True)
                output = self.mock_stdout.getvalue()
                self.assertNotIn("Custom Mods Cleanup", output)
                self.assertNotIn("Would purge custom mods", output)

    def test_cli_env_integration(self):
        repo_root = Path(__file__).resolve().parent.parent

        # 1. bg3 env check (via bg3_core.cli)
        proc_check = subprocess.run(
            [sys.executable, "-m", "bg3_core.cli", "env", "check"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Environment Configuration Status", proc_check.stdout)

        # 2. bg3 env check --json (via bg3_core.cli)
        proc_json = subprocess.run(
            [sys.executable, "-m", "bg3_core.cli", "env", "check", "--json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn('"configured": true', proc_json.stdout)
        self.assertIn('"xdg"', proc_json.stdout)
        self.assertIn('"config_home"', proc_json.stdout)

        # 3. python3 -m bg3_core.cli.setup_environment --dry-run --non-interactive
        proc_dry = subprocess.run(
            [sys.executable, "-m", "bg3_core.cli.setup_environment", "--dry-run", "--non-interactive"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Continuing setup without subscription sync.", proc_dry.stdout)
        self.assertNotIn("purging custom mods", proc_dry.stdout)

    def test_legacy_env_is_not_auto_migrated(self):
        """Verify that a legacy repo-level .env is ignored and not unlinked."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            legacy_file = tmp_root / ".env"
            legacy_file.write_text("MODIO_API_KEY=legacy_key_999\n", encoding="utf-8")
            target_config = tmp_root / "xdg" / "bg3" / "env"

            from bg3_core.cli.setup_environment import check_environment_status

            with patch("bg3_core.cli.setup_environment.WORKSPACE_ROOT", tmp_root), \
                 patch("bg3_core.cli.setup_environment.ENV_PATH", target_config):
                check_environment_status(as_json=True)
                self.assertFalse(target_config.is_file())
                self.assertTrue(legacy_file.is_file())

    def test_setup_environment_studio_dir_option(self):
        """Verify that --studio-dir sets BG3_STUDIO_DIR and scaffolds directories."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target_env = tmp_root / "xdg" / "bg3" / "env"
            custom_studio = tmp_root / "My_Custom_Studio"

            from bg3_core.cli.setup_environment import run_wizard

            with patch("bg3_core.cli.setup_environment.WORKSPACE_ROOT", tmp_root), \
                 patch("bg3_core.cli.setup_environment.ENV_PATH", target_env):
                run_wizard(
                    dry_run=False,
                    non_interactive=True,
                    config_path=target_env,
                    studio_dir_override=str(custom_studio),
                )
                self.assertTrue(target_env.is_file())
                self.assertIn(f"BG3_STUDIO_DIR={custom_studio}", target_env.read_text(encoding="utf-8"))
                self.assertTrue((custom_studio / "Build_Guides").is_dir())
                self.assertTrue((custom_studio / "Mods" / "subscribed").is_dir())
                self.assertTrue((custom_studio / "Mods" / "authored").is_dir())


if __name__ == "__main__":
    unittest.main()
