"""Baldur's Gate 3 Mod Studio — Unified Command-Line Interface and Routing Subsystem."""

from __future__ import annotations

from bg3_core.cli.common import (
    ConsoleColor,
    ExitCode,
    NonInteractiveConfirmationError,
    OutputEmitter,
    confirm_action,
    format_json_response,
)
from bg3_core.cli.router import (
    COMMAND_REGISTRY,
    DIRECT_COMMANDS,
    CommandSpec,
    _invoke_in_process,
    build_parser,
    dispatch_command,
    main,
    resolve_module_fallback,
)

__all__ = [
    "COMMAND_REGISTRY",
    "DIRECT_COMMANDS",
    "CommandSpec",
    "ConsoleColor",
    "ExitCode",
    "NonInteractiveConfirmationError",
    "OutputEmitter",
    "_invoke_in_process",
    "build_parser",
    "confirm_action",
    "dispatch_command",
    "format_json_response",
    "main",
    "resolve_module_fallback",
]
