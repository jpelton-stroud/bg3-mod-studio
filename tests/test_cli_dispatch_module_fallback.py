#!/usr/bin/env python3
"""
tests/test_cli_dispatch_module_fallback.py
-----------------------------------------
Unit tests for CLI dispatch module resolution and fallback execution via `python -m <module>`.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from bg3_core.cli import build_parser, dispatch_command, resolve_module_fallback
from bg3_core.cli_common import OutputEmitter


class TestCliDispatchModuleFallback(unittest.TestCase):
    def test_resolve_module_fallback_core(self):
        p = Path("/app/packages/bg3-core/bg3_core/modio_search.py")
        mod = resolve_module_fallback(p)
        self.assertEqual(mod, "bg3_core.modio_search")

    def test_resolve_module_fallback_authoring_subpackage(self):
        p = Path("/app/packages/bg3-authoring/bg3_authoring/packaging/pack_mod_pak.py")
        mod = resolve_module_fallback(p)
        self.assertEqual(mod, "bg3_authoring.packaging.pack_mod_pak")

    def test_resolve_module_fallback_theorycraft(self):
        p = Path("/app/packages/bg3-theorycraft/bg3_theorycraft/simulate_build_synergy.py")
        mod = resolve_module_fallback(p)
        self.assertEqual(mod, "bg3_theorycraft.simulate_build_synergy")

    def test_resolve_module_fallback_unknown(self):
        p = Path("/some/random/script.py")
        mod = resolve_module_fallback(p)
        self.assertIsNone(mod)

    @patch("subprocess.run")
    def test_dispatch_fallback_when_forced(self, mock_run):
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        parser = build_parser()
        args = parser.parse_args(["tools", "list", "--json"])
        emitter = Mock(spec=OutputEmitter)
        emitter.log = Mock()
        emitter.error = Mock()

        with patch.dict(os.environ, {"_BG3_FORCE_MODULE_DISPATCH": "1"}):
            ret = dispatch_command(args, emitter)

        self.assertEqual(ret, 0)
        self.assertTrue(mock_run.called)
        cmd_called = mock_run.call_args[0][0]
        self.assertEqual(cmd_called[1], "-m")
        self.assertEqual(cmd_called[2], "bg3_core.tools")
        self.assertIn("--list", cmd_called)
        self.assertIn("--json", cmd_called)

    @patch("subprocess.run")
    def test_dispatch_normal_when_file_exists(self, mock_run):
        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        parser = build_parser()
        args = parser.parse_args(["tools", "list", "--json"])
        emitter = Mock(spec=OutputEmitter)
        emitter.log = Mock()
        emitter.error = Mock()

        with patch.dict(os.environ, {"_BG3_FORCE_MODULE_DISPATCH": "0"}):
            ret = dispatch_command(args, emitter)

        self.assertEqual(ret, 0)
        self.assertTrue(mock_run.called)
        cmd_called = mock_run.call_args[0][0]
        # In editable workspace, target exists on disk so directly invoked by path
        self.assertTrue(cmd_called[1].endswith("tools.py"))


if __name__ == "__main__":
    unittest.main()
