"""Integration tests for bg3 unified CLI entrypoint."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BG3_CLI = REPO_ROOT / "packages" / "bg3-core" / "bg3_core" / "cli.py"


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

    def test_mod_add_dependency_rejects_underscore(self):
        proc = self.run_cli(["mod", "add_dependency", "--help"])
        self.assertEqual(proc.returncode, 2)

    def test_bg3_run_deprecated_rejected(self):
        proc = self.run_cli(["run", "query_mod_database", "--help"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("invalid choice: 'run'", proc.stderr)

    def test_bg3_query_canonical(self):
        proc = self.run_cli(["query", "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("General search term across name", proc.stdout)

    def test_scaffold_stat_dry_run_json(self):
        proc = self.run_cli([
            "scaffold", "stat",
            "--mod", "paladins-call",
            "--type", "weapon",
            "--name", "IntegrationTestBlade",
            "--dry-run",
            "--json",
        ])
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "created")
        self.assertEqual(data["entry_name"], "IntegrationTestBlade")
        self.assertTrue(data["dry_run"])

    def test_scaffold_progression_help(self):
        proc = self.run_cli(["scaffold", "progression", "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--class", proc.stdout)
        self.assertIn("--level", proc.stdout)

    def test_modio_purge_requires_confirmation(self):
        proc = self.run_cli(["modio", "purge", "--json"])
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertEqual(data["error"]["code"], "CONFIRMATION_REQUIRED")

    def test_query_database_json(self):
        proc = self.run_cli(["query", "--limit", "2", "--json"])
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIn("results", data)
        self.assertIn("count", data)

    def test_build_simulate_json(self):
        proc = self.run_cli(["build", "simulate", "--classes", "Wizard=20", "--json"])
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["total_level"], 20)
        self.assertIn("spell_slots", data)

    def test_tools_list_json(self):
        proc = self.run_cli(["tools", "list", "--json"])
        self.assertEqual(proc.returncode, 0)
        tools = json.loads(proc.stdout)
        self.assertIsInstance(tools, list)
        self.assertTrue(len(tools) >= 20)

    def test_bg3_save_list_json(self):
        proc = self.run_cli(["save", "list", "--json"])
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "success")
        self.assertIn("saves", payload["data"])

    def test_bg3_save_purge_dry_run_json(self):
        proc = self.run_cli(["save", "purge", "--dry-run", "--json"])
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "success")

    def test_bg3_save_purge_confirmation_required(self):
        proc = self.run_cli(["save", "purge", "--json"])
        # If there are saves discovered, it must require confirmation
        # If 0 saves, it returns OK with 0 purged
        self.assertIn(proc.returncode, (0, 2))
        payload = json.loads(proc.stdout)
        if proc.returncode == 2:
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["error"]["code"], "CONFIRMATION_REQUIRED")

    def test_bg3_mod_diagnose_logs_purge_dry_run_json(self):
        proc = self.run_cli(["mod", "diagnose-logs", "--purge", "--dry-run", "--json"])
        self.assertIn(proc.returncode, (0, 1))
        payload = json.loads(proc.stdout)
        self.assertIn(payload["status"], ("success", "error"))

    def test_missing_authoring_package_gating(self):
        code = """
import sys
sys.modules['bg3_authoring'] = None
from bg3_core.cli import build_parser, dispatch_command
from bg3_core.cli_common import OutputEmitter

parser = build_parser()
args = parser.parse_args(['mod', 'validate', 'fake-mod', '--json'])
emitter = OutputEmitter(json_mode=True)
sys.exit(dispatch_command(args, emitter))
"""
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 69)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "PACKAGE_NOT_INSTALLED")
        self.assertIn("bg3-authoring", payload["error"]["message"])

    def test_missing_theorycraft_package_gating(self):
        code = """
import sys
sys.modules['bg3_theorycraft'] = None
from bg3_core.cli import build_parser, dispatch_command
from bg3_core.cli_common import OutputEmitter

parser = build_parser()
args = parser.parse_args(['build', 'sim', '--classes', 'Fighter=1', '--json'])
emitter = OutputEmitter(json_mode=True)
sys.exit(dispatch_command(args, emitter))
"""
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 69)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "PACKAGE_NOT_INSTALLED")
        self.assertIn("bg3-theorycraft", payload["error"]["message"])


if __name__ == "__main__":
    unittest.main()
