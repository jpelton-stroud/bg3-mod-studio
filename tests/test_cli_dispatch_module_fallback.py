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

    @patch("bg3_core.cli._invoke_in_process")
    def test_dispatch_in_process_execution(self, mock_invoke):
        mock_invoke.return_value = 0

        parser = build_parser()
        args = parser.parse_args(["tools", "list", "--json"])
        emitter = Mock(spec=OutputEmitter)
        emitter.log = Mock()
        emitter.error = Mock()

        ret = dispatch_command(args, emitter)

        self.assertEqual(ret, 0)
        self.assertTrue(mock_invoke.called)
        target_mod, target_args = mock_invoke.call_args[0]
        self.assertEqual(target_mod, "bg3_core.tools")
        self.assertIn("--list", target_args)
        self.assertIn("--json", target_args)

    def test_invoke_in_process_captures_system_exit(self):
        import contextlib
        import io
        from bg3_core.cli import _invoke_in_process
        from bg3_core.cli_common import ExitCode

        # Test in-process invocation with --help on a known core module
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            ret = _invoke_in_process("bg3_core.tools", ["--help"])
        self.assertEqual(ret, ExitCode.OK)


if __name__ == "__main__":
    unittest.main()
