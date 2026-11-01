#!/usr/bin/env python3
"""
common.py
---------
Shared packaging exclusions, constants, and archive filtering predicates
for Baldur's Gate 3 mod distribution (.pak) and game Data synchronization.
"""

from __future__ import annotations

from pathlib import Path

EXCLUDED_FILENAMES: set[str] = {
    ".gitignore",
    ".gitkeep",
    "desktop.ini",
    ".ds_store",
    "thumbs.db",
    "readme.md",
    "task.md",
    "modio_description.md",
    "modio_description.html",
}

EXCLUDED_EXTENSIONS: set[str] = {
    ".tmp",
    ".bak",
    ".py",
    ".pyc",
}

EXCLUDED_DIRECTORIES: set[str] = {
    "projects",
    "editor",
    "metadata",
    "__pycache__",
    ".git",
    "dist",
}


def should_include_file(rel_path: Path, include_projects: bool = False) -> bool:
    """Filters files for inclusion in release pak archive or synchronization."""
    parts = [p.lower() for p in rel_path.parts]

    # Exclude root-level thumbnail.png (only Mods/*/mod_publish_logo.png or Projects/*/thumbnail.png belong in subfolders)
    if len(parts) == 1 and parts[0] == "thumbnail.png":
        return False

    # Exclude dotfiles and dotdirs (e.g. .test_deps.json, .gitignore)
    if any(p.startswith(".") for p in parts):
        return False

    for part in parts[:-1]:
        if part in EXCLUDED_DIRECTORIES:
            if part == "projects" and include_projects:
                continue
            return False

    name_lower = rel_path.name.lower()
    if name_lower in EXCLUDED_FILENAMES:
        return False

    if any(name_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
        return False

    return True
