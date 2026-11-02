"""
bg3_core.exceptions
-------------------
Unified domain exception hierarchy for the Baldur's Gate 3 Mod Studio toolchain.
"""

from __future__ import annotations


class BG3Error(Exception):
    """Base domain exception for all Baldur's Gate 3 Mod Studio errors."""


class BG3BinaryError(BG3Error, ValueError):
    """Raised on binary format parsing, AST decoding, or serialization failures."""


class BG3PackagingError(BG3Error, RuntimeError):
    """Raised on mod package creation, extraction, or package integrity verification failures."""


class BG3ProfileError(BG3Error, RuntimeError):
    """Raised on modsettings, load order, or savegame profile manipulation errors."""


class BG3CatalogError(BG3Error, RuntimeError):
    """Raised on library catalog synchronization, parsing, or remote mod repository failures."""


class BG3EnvironmentError(BG3Error, OSError):
    """Raised on workspace path discovery, missing directory layout, or environment misconfiguration."""


__all__ = [
    "BG3BinaryError",
    "BG3CatalogError",
    "BG3EnvironmentError",
    "BG3Error",
    "BG3PackagingError",
    "BG3ProfileError",
]
