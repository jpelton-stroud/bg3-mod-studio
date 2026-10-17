#!/usr/bin/env python3
"""
tests/test_setup_environment.py
-------------------------------
Unit and integration tests for environment wizard prompts, subscription sync,
custom mod purge, and non-interactive safety guards in scripts/setup_environment.py.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.setup_environment import (
    handle_custom_mods_purge,
    handle_subscription_sync,
    prompt_custom_mods_purge,
    prompt_subscription_sync,
)


class SetupEnvironmentQATests(unittest.TestCase):
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

    def test_prompt_custom_mods_purge_non_interactive(self):
        # Non-interactive mode must return "n" to avoid data destruction
        choice = prompt_custom_mods_purge(non_interactive=True)
        self.assertEqual(choice, "n")

    @patch("builtins.input", side_effect=[""])
    def test_prompt_custom_mods_purge_default(self, _mock_input):
        # Pressing Enter defaults to "y"
        choice = prompt_custom_mods_purge(non_interactive=False)
        self.assertEqual(choice, "y")

    @patch("builtins.input", side_effect=["n"])
    def test_prompt_custom_mods_purge_no(self, _mock_input):
        choice = prompt_custom_mods_purge(non_interactive=False)
        self.assertEqual(choice, "n")

    @patch("builtins.input", side_effect=[EOFError])
    def test_prompt_custom_mods_purge_eof(self, _mock_input):
        self.assertEqual(prompt_custom_mods_purge(non_interactive=False), "y")
        self.assertEqual(prompt_custom_mods_purge(non_interactive=True), "n")

    def test_handle_subscription_sync_dry_run(self):
        # Must execute without raising exceptions in dry-run mode for all choices
        for choice in ("1", "2", "3", "4"):
            with self.subTest(choice=choice):
                handle_subscription_sync(choice, dry_run=True)

    def test_handle_custom_mods_purge_live(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            mock_my_mods = temp_root / "my_mods"
            mock_my_mods.mkdir()
            (mock_my_mods / "sample-mod").mkdir()
            (mock_my_mods / "sample-mod" / "meta.lsx").write_text("<save/>", encoding="utf-8")
            (mock_my_mods / "notes.txt").write_text("notes", encoding="utf-8")

            with patch("scripts.setup_environment.WORKSPACE_ROOT", temp_root):
                # When choice is 'n', nothing is removed
                handle_custom_mods_purge("n", dry_run=False)
                self.assertTrue((mock_my_mods / "sample-mod").is_dir())
                self.assertTrue((mock_my_mods / "notes.txt").is_file())

                # When choice is 'y', all contents inside my_mods are removed
                handle_custom_mods_purge("y", dry_run=False)
                self.assertTrue(mock_my_mods.is_dir())
                self.assertEqual(list(mock_my_mods.iterdir()), [])

    def test_setup_sh_cli_integration(self):
        repo_root = Path(__file__).resolve().parent.parent

        # 1. ./setup.sh --check
        proc_check = subprocess.run(
            ["./setup.sh", "--check"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Environment Configuration Status", proc_check.stdout)

        # 2. ./setup.sh --check --json
        proc_json = subprocess.run(
            ["./setup.sh", "--check", "--json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn('"configured": true', proc_json.stdout)

        # 3. python3 scripts/setup_environment.py --dry-run --non-interactive
        proc_dry = subprocess.run(
            [sys.executable, "scripts/setup_environment.py", "--dry-run", "--non-interactive"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Continuing setup without subscription sync.", proc_dry.stdout)
        self.assertIn("Continuing without purging custom mods.", proc_dry.stdout)


if __name__ == "__main__":
    unittest.main()
