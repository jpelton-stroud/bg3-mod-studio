"""Integration tests for bg3 unified CLI entrypoint."""

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from bg3_core.cli.router import main

REPO_ROOT = Path(__file__).resolve().parent.parent


class _ProcResult:
    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestBg3CliIntegration(unittest.TestCase):

    def run_cli(self, args, stdin=None):
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        stdin_stream = io.StringIO(stdin or "")
        test_argv = ["bg3"] + list(args)
        returncode = 0

        with patch("sys.argv", test_argv), \
             patch("sys.stdout", stdout_buf), \
             patch("sys.stderr", stderr_buf), \
             patch("sys.stdin", stdin_stream):
            try:
                main()
            except SystemExit as e:
                returncode = e.code if isinstance(e.code, int) else (1 if e.code else 0)

        return _ProcResult(returncode, stdout_buf.getvalue(), stderr_buf.getvalue())

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
        self.assertEqual(data["name"], "IntegrationTestBlade")
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
from bg3_core.cli.common import OutputEmitter

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
from bg3_core.cli.common import OutputEmitter

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

    def test_conflict_command_works_without_authoring_package(self):
        """Assert that 'bg3 mod conflict' and 'bg3 conflict' operate independently of bg3-authoring."""
        code = """
import sys
sys.modules['bg3_authoring'] = None
from bg3_core.cli import build_parser, dispatch_command
from bg3_core.cli.common import OutputEmitter

parser = build_parser()
args = parser.parse_args(['mod', 'conflict', '--all', '--json'])
emitter = OutputEmitter(json_mode=True)
ret = dispatch_command(args, emitter)
sys.exit(ret)
"""
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        # Should not be PACKAGE_NOT_INSTALLED (exit code 69)
        self.assertNotEqual(proc.returncode, 69)
        payload = json.loads(proc.stdout)
        self.assertIn("total_mods", payload)

    def test_bump_version_targets_authoring_package(self):
        """Assert that 'bg3 mod bump-version' points to bg3_authoring."""
        from bg3_core.cli.router import COMMAND_REGISTRY

        spec = COMMAND_REGISTRY.get(("mod", "bump-version"))
        self.assertIsNotNone(spec)
        self.assertEqual(spec.target_module, "bg3_authoring.bump_mod_version")
        self.assertEqual(spec.pkg_requirement, "bg3_authoring")

    def test_missing_authoring_package_gating_bump_version(self):
        """Assert that missing bg3_authoring cleanly gates bump-version with exit code 69."""
        code = """
import sys
sys.modules['bg3_authoring'] = None
from bg3_core.cli import build_parser, dispatch_command
from bg3_core.cli.common import OutputEmitter

parser = build_parser()
args = parser.parse_args(['mod', 'bump-version', '--patch', '--json'])
emitter = OutputEmitter(json_mode=True)
sys.exit(dispatch_command(args, emitter))
"""
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 69)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "PACKAGE_NOT_INSTALLED")
        self.assertIn("bg3-authoring", payload["error"]["message"])

    def test_entry_points_manifest_declarations(self):
        """Verify that bg3.commands entry points are properly configured in package pyproject.toml files."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        authoring_toml = REPO_ROOT / "packages" / "bg3-authoring" / "pyproject.toml"
        with open(authoring_toml, "rb") as f:
            auth_data = tomllib.load(f)

        auth_eps = auth_data.get("project", {}).get("entry-points", {}).get("bg3.commands", {})
        self.assertIn("mod.create", auth_eps)
        self.assertIn("mod.scaffold", auth_eps)
        self.assertIn("mod.bump-version", auth_eps)
        self.assertIn("mod.pack", auth_eps)
        self.assertEqual(auth_eps["mod.bump-version"], "bg3_authoring.bump_mod_version:main")

        theory_toml = REPO_ROOT / "packages" / "bg3-theorycraft" / "pyproject.toml"
        with open(theory_toml, "rb") as f:
            theory_data = tomllib.load(f)

        theory_eps = theory_data.get("project", {}).get("entry-points", {}).get("bg3.commands", {})
        self.assertIn("build.simulate", theory_eps)
        self.assertIn("build.sim", theory_eps)

    def test_mod_subparser_expanded_flag_schemas(self):
        """Assert that mod subparsers expose complete operational flags in --help output."""
        # diagnose-logs
        proc = self.run_cli(["mod", "diagnose-logs", "--help"])
        self.assertEqual(proc.returncode, 0)
        for flag in ["--toolkit-dir", "--type", "--severity", "--subsystem", "--mod", "--follow", "--list-logs"]:
            self.assertIn(flag, proc.stdout)

        # sync-game
        proc = self.run_cli(["mod", "sync-game", "--help"])
        self.assertEqual(proc.returncode, 0)
        for flag in ["--source-dir", "--data-dir", "--mods", "--clean-legacy", "--clean-custom", "--clean-mod", "--bump-build", "--watch"]:
            self.assertIn(flag, proc.stdout)

        # pack
        proc = self.run_cli(["mod", "pack", "--help"])
        self.assertEqual(proc.returncode, 0)
        for flag in ["--out", "--output-dir", "--publish-local", "--clean-local", "--include-projects", "--uncompressed"]:
            self.assertIn(flag, proc.stdout)

        # create
        proc = self.run_cli(["mod", "create", "--help"])
        self.assertEqual(proc.returncode, 0)
        for flag in ["--slug", "--uuid", "--unlock-level-curve", "--dependency", "--output-dir", "--type"]:
            self.assertIn(flag, proc.stdout)


if __name__ == "__main__":
    unittest.main()
