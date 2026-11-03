"""
bg3_authoring.diagnostics - Static linting, log analysis, and localization sync.
"""

from __future__ import annotations

from bg3_authoring.diagnostics.diagnose_toolkit_logs import (
    classify_entry,
    correlate_message,
    get_available_log_files,
    index_mod_content,
    parse_log_file,
    purge_toolkit_logs,
    resolve_toolkit_dir,
    stream_log_file,
)
from bg3_authoring.diagnostics.sync_localization import (
    collect_referenced_handles,
    compile_mod_localization,
    load_english_xml,
    prune_orphan_handles,
    sync_language_skeletons,
)
from bg3_authoring.diagnostics.validate_mod import (
    ModValidator,
    check_uuid_uniqueness,
)

__all__ = [
    "ModValidator",
    "check_uuid_uniqueness",
    "classify_entry",
    "collect_referenced_handles",
    "compile_mod_localization",
    "correlate_message",
    "get_available_log_files",
    "index_mod_content",
    "load_english_xml",
    "parse_log_file",
    "prune_orphan_handles",
    "purge_toolkit_logs",
    "resolve_toolkit_dir",
    "stream_log_file",
    "sync_language_skeletons",
]
