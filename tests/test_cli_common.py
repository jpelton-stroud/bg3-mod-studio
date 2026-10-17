"""Unit tests for scripts/lib/cli_common.py."""

import io
import json
import os
import unittest
from unittest.mock import patch

from scripts.lib.cli_common import (
    ConsoleColor,
    ExitCode,
    NonInteractiveConfirmationError,
    OutputEmitter,
    confirm_action,
    format_json_response,
)


class TestCliCommon(unittest.TestCase):

    def test_exit_codes(self):
        self.assertEqual(ExitCode.OK, 0)
        self.assertEqual(ExitCode.GENERAL, 1)
        self.assertEqual(ExitCode.USAGE, 2)
        self.assertEqual(ExitCode.DATAERR, 65)
        self.assertEqual(ExitCode.NOINPUT, 66)
        self.assertEqual(ExitCode.UNAVAILABLE, 69)

    def test_format_json_response(self):
        res = format_json_response(data={"foo": "bar"}, status="success")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"], {"foo": "bar"})
        self.assertNotIn("error", res)

        err_res = format_json_response(status="error", error={"code": "FAIL", "message": "msg"})
        self.assertEqual(err_res["status"], "error")
        self.assertEqual(err_res["error"]["code"], "FAIL")
        self.assertNotIn("data", err_res)

    def test_console_color_no_color(self):
        stream = io.StringIO()
        color = ConsoleColor(stream=stream)
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(color.enabled)
            self.assertEqual(color.red("test"), "test")
            self.assertEqual(color.bold("bold"), "bold")

    def test_console_color_forced(self):
        stream = io.StringIO()
        color = ConsoleColor(stream=stream, force_color=True)
        self.assertTrue(color.enabled)
        self.assertIn("\033[31m", color.red("test"))

    def test_output_emitter_stream_isolation(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        emitter = OutputEmitter(json_mode=False, stdout=stdout, stderr=stderr)

        emitter.log("diagnostic log", level="INFO")
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("diagnostic log", stderr.getvalue())

        stdout.truncate(0)
        stdout.seek(0)
        stderr.truncate(0)
        stderr.seek(0)

        emitter.data({"key": "val"})
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn('"key": "val"', stdout.getvalue())

    def test_output_emitter_json_mode(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        emitter = OutputEmitter(json_mode=True, stdout=stdout, stderr=stderr)

        # In json_mode, log messages are suppressed on stdout
        emitter.log("some internal info", level="INFO")
        self.assertEqual(stdout.getvalue(), "")

        emitter.data({"items": [1, 2, 3]})
        parsed = json.loads(stdout.getvalue())
        self.assertEqual(parsed["status"], "success")
        self.assertEqual(parsed["data"]["items"], [1, 2, 3])

    def test_output_emitter_error_json(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        emitter = OutputEmitter(json_mode=True, stdout=stdout, stderr=stderr)

        emitter.error(
            message="Resource not found",
            code="NOT_FOUND",
            remediation="Check resource ID",
            exit_code=ExitCode.NOINPUT,
            exit_process=False,
        )
        parsed = json.loads(stdout.getvalue())
        self.assertEqual(parsed["status"], "error")
        self.assertEqual(parsed["error"]["code"], "NOT_FOUND")
        self.assertEqual(parsed["error"]["remediation"], "Check resource ID")

    def test_confirm_action_non_interactive(self):
        stream = io.StringIO()
        # Mock sys.stdin.isatty to False
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(NonInteractiveConfirmationError):
                confirm_action("Delete all mods?", non_interactive_yes=False, stream=stream)

            # When non_interactive_yes is True, should return True
            res = confirm_action("Delete all mods?", non_interactive_yes=True, stream=stream)
            self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
