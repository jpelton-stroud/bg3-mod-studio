#!/usr/bin/env python3
"""
tests/test_cli_dispatch_module_fallback.py
-----------------------------------------
Unit tests for CLI dispatch module resolution and fallback execution via `python -m <module>`.
"""

import unittest
from unittest.mock import Mock, patch

from bg3_core.cli import build_parser, dispatch_command
from bg3_core.cli.common import OutputEmitter


class TestCliDispatchModuleFallback(unittest.TestCase):
    @patch("bg3_core.cli.router._invoke_in_process")
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
        self.assertEqual(target_mod, "bg3_core.cli.tools")
        self.assertIn("list", target_args)
        self.assertIn("--json", target_args)

    def test_invoke_in_process_captures_system_exit(self):
        import contextlib
        import io

        from bg3_core.cli import _invoke_in_process
        from bg3_core.cli.common import ExitCode

        # Test in-process invocation with --help on a known core module
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            ret = _invoke_in_process("bg3_core.cli.tools", ["--help"])
        self.assertEqual(ret, ExitCode.OK)


if __name__ == "__main__":
    unittest.main()
