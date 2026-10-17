"""Integration tests for scripts/bg3.py unified CLI entrypoint."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BG3_CLI = REPO_ROOT / "scripts" / "bg3.py"


class TestBg3CliIntegration(unittest.TestCase):

    def run_cli(self, args, stdin=None):
        return subprocess.run(
            [sys.executable, str(BG3_CLI)] + args,
            capture_output=True,
            text=True,
            input=stdin,
        )

    def test_help_screen(self):
        proc = self.run_cli(["--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Baldur's Gate 3 Mod Studio", proc.stdout)
        self.assertIn("mod", proc.stdout)
        self.assertIn("loadorder", proc.stdout)
        self.assertIn("modio", proc.stdout)
        self.assertIn("env", proc.stdout)

    def test_no_args_exits_usage(self):
        proc = self.run_cli([])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage: bg3", proc.stderr)

    def test_missing_subcommand_json_error(self):
        proc = self.run_cli(["mod", "--json"])
        self.assertEqual(proc.returncode, 2)
        # Should output valid JSON on stdout
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["status"], "error")
        self.assertEqual(parsed["error"]["code"], "MISSING_COMMAND")

    def test_non_interactive_mutation_requires_yes(self):
        # In headless/subprocess mode, stdin is not a TTY.
        # sync should fail with exit code 2 and mention --yes
        proc = self.run_cli(["loadorder", "sync", "--json"])
        self.assertEqual(proc.returncode, 2)
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["status"], "error")
        self.assertEqual(parsed["error"]["code"], "CONFIRMATION_REQUIRED")
    def test_mod_conflict_missing_args(self):
        proc = self.run_cli(["mod", "conflict", "--json"])
        self.assertEqual(proc.returncode, 2)
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["status"], "error")
        self.assertEqual(parsed["error"]["code"], "INVALID_ARGUMENTS")

    def test_env_check(self):
        proc = self.run_cli(["env", "check", "--json"])
        self.assertIn(proc.returncode, [0, 1])
        parsed = json.loads(proc.stdout)
        self.assertTrue("configured" in parsed or "status" in parsed)

    def test_modio_sync_prune_requires_yes(self):
        proc = self.run_cli(["modio", "sync", "--prune", "--json"])
        self.assertEqual(proc.returncode, 2)
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["status"], "error")
        self.assertEqual(parsed["error"]["code"], "CONFIRMATION_REQUIRED")
        self.assertIn("--yes", parsed["error"]["remediation"])

    def test_mod_add_dependency_help(self):
        proc = self.run_cli(["mod", "add-dependency", "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("add-dependency", proc.stdout)

    def test_mod_add_dependency_alias(self):
        proc = self.run_cli(["mod", "add_dependency", "--help"])
        self.assertEqual(proc.returncode, 0)

    def test_bg3_run_universal(self):
        proc = self.run_cli(["run", "query_mod_database", "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("query_mod_database", proc.stdout)


if __name__ == "__main__":
    unittest.main()
