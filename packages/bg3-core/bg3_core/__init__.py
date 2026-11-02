"""
bg3_core - Core runtime, binary engines, environment, and CLI tools for Baldur's Gate 3 Mod Studio.
"""

from __future__ import annotations

from bg3_core.binary.larian_parsers import (
    DEFAULT_VERSION64,
    PATCH_8_VERSION,
    calculate_version64,
    compile_xml_bytes_to_loca,
    decode_version64,
    generate_larian_handle,
    parse_meta_lsx,
    split_larian_items,
)
from bg3_core.binary.lsf import LsfAttribute, LsfDocument, LsfNode
from bg3_core.binary.lspk import LspkArchive, build_lspk_archive
from bg3_core.cli.common import ConsoleColor, ExitCode, OutputEmitter
from bg3_core.cli.skills_installer import discover_bundled_skills, install_agent_skills
from bg3_core.env_paths import (
    REPO_ROOT,
    get_authored_mods_dir,
    get_build_guides_dir,
    get_library_catalog_path,
    get_studio_dir,
    get_subscribed_mods_dir,
    get_workspace_root,
    load_env_file,
    normalize_mod_key,
)
from bg3_core.modio.modio_client import ModioClient, ModioError

__version__ = "1.0.0"

__all__ = [
    "ConsoleColor",
    "DEFAULT_VERSION64",
    "ExitCode",
    "LsfAttribute",
    "LsfDocument",
    "LsfNode",
    "LspkArchive",
    "ModioClient",
    "ModioError",
    "OutputEmitter",
    "PATCH_8_VERSION",
    "REPO_ROOT",
    "__version__",
    "build_lspk_archive",
    "calculate_version64",
    "compile_xml_bytes_to_loca",
    "decode_version64",
    "discover_bundled_skills",
    "generate_larian_handle",
    "get_authored_mods_dir",
    "get_build_guides_dir",
    "get_library_catalog_path",
    "get_studio_dir",
    "get_subscribed_mods_dir",
    "get_workspace_root",
    "install_agent_skills",
    "load_env_file",
    "normalize_mod_key",
    "parse_meta_lsx",
    "split_larian_items",
]
