#!/usr/bin/env python3
"""
inspect_save_game.py - Backward-compatible shim redirecting to bg3_core.save_inspector.
"""

from __future__ import annotations

import sys

from bg3_core.save_inspector import (
    _parse_lsf_save_mods,
    audit_against_modsettings,
    extract_save_metadata,
    find_save_file,
    get_save_search_paths,
    main,
)

__all__ = [
    "_parse_lsf_save_mods",
    "audit_against_modsettings",
    "extract_save_metadata",
    "find_save_file",
    "get_save_search_paths",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
