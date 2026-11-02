"""
bg3_authoring.exceptions
------------------------
Domain exception hierarchy for Baldur's Gate 3 mod authoring, scaffolding, and diagnostics.
"""

from __future__ import annotations

from bg3_core.exceptions import BG3Error


class BG3AuthoringError(BG3Error, RuntimeError):
    """Base domain exception for authoring, scaffolding, and packaging diagnostics."""


class BG3ScaffoldError(BG3AuthoringError):
    """Raised when mod or asset template scaffolding fails."""


class BG3ConflictError(BG3AuthoringError):
    """Raised when progression, asset, or metadata collisions are detected between mods."""


__all__ = [
    "BG3AuthoringError",
    "BG3ConflictError",
    "BG3ScaffoldError",
]
