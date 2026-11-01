"""Automated regression gate: verifies complete absence of legacy references and deprecated code."""

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestLegacyReferencesRegressionGate(unittest.TestCase):
    """Enforces zero tolerance for legacy standalone script paths, registry.json, and deprecated shims."""

    def test_registry_json_and_builder_deleted(self):
        """Assert that registry.json and registry_builder.py no longer exist anywhere in the repository."""
        legacy_registry = REPO_ROOT / "packages" / "bg3-core" / "bg3_core" / "registry.json"
        legacy_builder = REPO_ROOT / "packages" / "bg3-core" / "bg3_core" / "registry_builder.py"
        self.assertFalse(legacy_registry.exists(), f"Found legacy file: {legacy_registry}")
        self.assertFalse(legacy_builder.exists(), f"Found legacy file: {legacy_builder}")

    def test_no_setup_shell_scripts(self):
        """Assert that setup.sh and setup.ps1 do not exist in the repository root."""
        setup_sh = REPO_ROOT / "setup.sh"
        setup_ps1 = REPO_ROOT / "setup.ps1"
        self.assertFalse(setup_sh.exists(), f"Found legacy shell script: {setup_sh}")
        self.assertFalse(setup_ps1.exists(), f"Found legacy PowerShell script: {setup_ps1}")

    def test_no_scripts_directory(self):
        """Assert that root scripts/ directory does not exist."""
        scripts_dir = REPO_ROOT / "scripts"
        self.assertFalse(scripts_dir.exists(), f"Found legacy scripts directory: {scripts_dir}")

    def test_no_scripts_slash_references_in_codebase(self):
        """Scan repository files for any lingering 'scripts/' references."""
        excluded_dirs = {
            ".git",
            ".venv",
            ".mypy_cache",
            ".ruff_cache",
            "dist",
            "__pycache__",
            ".agents",
        }
        allowed_extensions = {
            ".py",
            ".md",
            ".json",
            ".toml",
            ".yaml",
            ".yml",
        }

        violations = []
        pattern = re.compile(r"scripts/")

        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            rel_root = Path(root).relative_to(REPO_ROOT)

            for f in files:
                file_path = Path(root) / f
                if file_path.suffix not in allowed_extensions:
                    continue

                # Skip this regression test file itself
                if file_path.name == "test_legacy_references.py":
                    continue

                try:
                    text = file_path.read_text(encoding="utf-8")
                except Exception:
                    continue

                for line_no, line in enumerate(text.splitlines(), start=1):
                    # Exclude the validator check in tools.py that actively forbids legacy script paths
                    if file_path.name == "tools.py" and any(k in line for k in ("forbidden_refs", "flags any lingering", "script_refs =")):
                        continue
                    if file_path.name == "tools.py" and "startswith" in line and "scripts" in line:
                        continue

                    if pattern.search(line):
                        violations.append(f"{rel_root / f}:{line_no}: {line.strip()}")

        self.assertEqual(
            violations,
            [],
            f"Found {len(violations)} legacy 'scripts/' references:\n" + "\n".join(violations),
        )

    def test_no_registry_json_references_in_codebase(self):
        """Scan repository files for any lingering 'registry.json' references."""
        excluded_dirs = {
            ".git",
            ".venv",
            ".mypy_cache",
            ".ruff_cache",
            "dist",
            "__pycache__",
            ".agents",
        }
        allowed_extensions = {
            ".py",
            ".md",
            ".json",
            ".toml",
            ".yaml",
            ".yml",
        }

        violations = []
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            rel_root = Path(root).relative_to(REPO_ROOT)

            for f in files:
                file_path = Path(root) / f
                if file_path.suffix not in allowed_extensions:
                    continue

                if file_path.name == "test_legacy_references.py":
                    continue

                try:
                    text = file_path.read_text(encoding="utf-8")
                except Exception:
                    continue

                for line_no, line in enumerate(text.splitlines(), start=1):
                    if "registry.json" in line:
                        violations.append(f"{rel_root / f}:{line_no}: {line.strip()}")

        self.assertEqual(
            violations,
            [],
            f"Found {len(violations)} legacy 'registry.json' references:\n" + "\n".join(violations),
        )

    def test_bg3_run_subcommand_rejected(self):
        """Assert that 'bg3 run' is rejected as an invalid command."""
        proc = subprocess.run(
            [sys.executable, "-m", "bg3_core.cli", "run", "anything"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid choice: 'run'", proc.stderr)


if __name__ == "__main__":
    unittest.main()
