"""Mod.io community platform integration, library management, and catalog indexing."""

from __future__ import annotations

from bg3_core.modio.library_catalog import purge_library_mods
from bg3_core.modio.modio_client import (
    BG3_GAME_ID,
    MODIO_API_HOST,
    USER_AGENT,
    ModioClient,
    ModioError,
)
from bg3_core.modio.query_mod_database import build_or_load_index
from bg3_core.modio.render_modio_description import render_mod_description
from bg3_core.modio.update_library_catalog import write_library_catalog

__all__ = [
    "BG3_GAME_ID",
    "MODIO_API_HOST",
    "USER_AGENT",
    "ModioClient",
    "ModioError",
    "build_or_load_index",
    "purge_library_mods",
    "render_mod_description",
    "write_library_catalog",
]
