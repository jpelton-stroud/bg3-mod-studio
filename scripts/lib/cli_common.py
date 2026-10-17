"""Shared CLI utilities, stream discipline, exit codes, and envelope formatting.

Pure Python 3.10+ standard library implementation adhering to 2026 CLI standards.
"""

from __future__ import annotations

import enum
import json
import os
import sys
from typing import Any, Dict, Optional, TextIO


class ExitCode(enum.IntEnum):
    """Standardized POSIX / BSD sysexits exit codes."""
    OK = 0
    SUCCESS = 0
    GENERAL = 1
    USAGE = 2            # Command syntax or flag misuse
    DATAERR = 65          # Input data error or validation collision
    NOINPUT = 66          # File, mod, or resource not found
    UNAVAILABLE = 69      # Upstream service / network / tool unavailable
    TEMPFAIL = 75         # Temporary transient failure
    NOPERM = 77           # Permission or authentication denied


class ConsoleColor:
    """Zero-dependency terminal styling supporting NO_COLOR and TTY detection."""

    def __init__(self, stream: Optional[TextIO] = None, force_color: bool = False):
        self.stream = stream or sys.stderr
        self.force_color = force_color

    @property
    def enabled(self) -> bool:
        if self.force_color:
            return True
        if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
            return False
        return hasattr(self.stream, "isatty") and self.stream.isatty()

    def _style(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return self._style("1", text)

    def dim(self, text: str) -> str:
        return self._style("2", text)

    def red(self, text: str) -> str:
        return self._style("31", text)

    def green(self, text: str) -> str:
        return self._style("32", text)

    def yellow(self, text: str) -> str:
        return self._style("33", text)

    def cyan(self, text: str) -> str:
        return self._style("36", text)

    def blue(self, text: str) -> str:
        return self._style("34", text)

    def magenta(self, text: str) -> str:
        return self._style("35", text)


class NonInteractiveConfirmationError(Exception):
    """Raised when a destructive operation is invoked without --yes non-interactively."""
    pass


def confirm_action(
    prompt: str,
    default: bool = False,
    non_interactive_yes: bool = False,
    stream: Optional[TextIO] = None,
    force_non_interactive: bool = False,
) -> bool:
    """Prompt for confirmation in interactive TTYs, or validate --yes in non-interactive runs.

    Raises:
        NonInteractiveConfirmationError: If running non-interactively and non_interactive_yes is False.
    """
    out_stream = stream or sys.stderr
    is_tty = (
        hasattr(sys.stdin, "isatty")
        and sys.stdin.isatty()
        and not force_non_interactive
        and os.environ.get("CI") != "true"
        and os.environ.get("DEBIAN_FRONTEND") != "noninteractive"
    )

    if not is_tty:
        if non_interactive_yes:
            return True
        raise NonInteractiveConfirmationError(
            f"Operation requires confirmation: '{prompt}'. In non-interactive mode, pass --yes / -y to proceed."
        )

    suffix = " [Y/n]: " if default else " [y/N]: "
    out_stream.write(f"{prompt}{suffix}")
    out_stream.flush()
    try:
        response = sys.stdin.readline().strip().lower()
    except (EOFError, KeyboardInterrupt):
        out_stream.write("\n")
        return False

    if not response:
        return default
    return response in ("y", "yes")


def format_json_response(
    data: Any = None,
    status: str = "success",
    error: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a standard machine-readable JSON envelope."""
    payload: Dict[str, Any] = {"status": status}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    return payload


class OutputEmitter:
    """Enforces stream discipline: stdout for primary data, stderr for diagnostics."""

    def __init__(
        self,
        json_mode: bool = False,
        stdout: Optional[TextIO] = None,
        stderr: Optional[TextIO] = None,
        color: Optional[ConsoleColor] = None,
    ):
        self.json_mode = json_mode
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.color = color or ConsoleColor(stream=self.stderr)

    def data(self, payload: Any, indent: int = 2) -> None:
        """Write primary data to stdout."""
        if self.json_mode:
            envelope = format_json_response(data=payload, status="success")
            self.stdout.write(json.dumps(envelope, indent=indent, default=str) + "\n")
        else:
            if isinstance(payload, (dict, list)):
                self.stdout.write(json.dumps(payload, indent=indent, default=str) + "\n")
            else:
                self.stdout.write(str(payload) + "\n")
        self.stdout.flush()

    def log(self, message: str, level: str = "INFO") -> None:
        """Write diagnostic logs to stderr."""
        if self.json_mode:
            return
        tag = level.upper()
        if tag == "INFO":
            prefix = self.color.cyan("[INFO]")
        elif tag == "WARN" or tag == "WARNING":
            prefix = self.color.yellow("[WARN]")
        elif tag == "ERROR":
            prefix = self.color.red("[ERROR]")
        elif tag == "SUCCESS":
            prefix = self.color.green("[OK]")
        else:
            prefix = f"[{tag}]"
        self.stderr.write(f"{prefix} {message}\n")
        self.stderr.flush()

    def error(
        self,
        message: str,
        code: str = "GENERAL_ERROR",
        remediation: Optional[str] = None,
        exit_code: int = ExitCode.GENERAL,
        exit_process: bool = True,
    ) -> None:
        """Write structured error to stdout (in JSON mode) or colored diagnostic to stderr."""
        if self.json_mode:
            err_obj = {
                "code": code,
                "message": message,
            }
            if remediation:
                err_obj["remediation"] = remediation
            envelope = format_json_response(status="error", error=err_obj)
            self.stdout.write(json.dumps(envelope, indent=2) + "\n")
            self.stdout.flush()
        else:
            self.stderr.write(f"{self.color.bold(self.color.red('Error:'))} {message}\n")
            if remediation:
                self.stderr.write(f"{self.color.cyan('Hint:')} {remediation}\n")
            self.stderr.flush()

        if exit_process:
            sys.exit(exit_code)
