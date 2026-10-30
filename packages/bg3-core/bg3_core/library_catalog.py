"""Shared parsing, catalog queries, pruning, and directory utilities for community mod libraries."""

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .env_paths import REPO_ROOT, get_subscribed_mods_dir, normalize_mod_key

LIBRARY_COLUMNS = (
    "Mod Id",
    "Mod Name",
    "Mod Slug",
    "Description",
    "Features Documented",
    "Spec Link",
)


def split_table_row(line: str) -> Optional[List[str]]:
    """Split a Markdown table row without treating escaped pipes as separators."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    fields = re.split(r"(?<!\\)\|", stripped[1:-1])
    return [field.replace(r"\|", "|").strip() for field in fields]


def parse_library_rows(content: str) -> List[Dict[str, str]]:
    """Return categorized rows from the six-column library schema."""
    rows = []
    category = ""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("## "):
            category = line[3:].strip()
            continue
        if not line.startswith("|"):
            continue
        fields = split_table_row(line)
        if fields is None or len(fields) != len(LIBRARY_COLUMNS):
            continue
        if tuple(field.casefold() for field in fields) == tuple(
            column.casefold() for column in LIBRARY_COLUMNS
        ):
            continue
        if fields[0].startswith(":") or (
            fields[0] and set(fields[0]) <= {":", "-"}
        ):
            continue

        slug = fields[2].strip("`")
        spec_match = re.fullmatch(r"\[[^\]]*\]\(([^)]+)\)", fields[5])
        rows.append(
            {
                "mod_id": fields[0],
                "name": fields[1],
                "slug": slug,
                "description": fields[3],
                "features_documented": fields[4],
                "spec_link": spec_match.group(1) if spec_match else fields[5],
                "category": category,
            }
        )
    return rows


def render_library_row(mod: Dict[str, Any]) -> str:
    """Render one row using the canonical six-column schema."""
    values = (
        str(mod.get("mod_id") or ""),
        mod["title"],
        f"`{mod['slug']}`",
        mod["description"],
        f"{mod['feature_count']} implemented",
        f"[View Spec]({mod['slug']}/README.md)",
    )
    escaped = [value.replace("|", r"\|").replace("\n", " ").strip() for value in values]
    return "| " + " | ".join(escaped) + " |"


def get_tracked_mods(
    library_path: Optional[Any] = None,
    include_filesystem: bool = False,
    workspace_root: Optional[Any] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Parses mods/library.md directly to identify mods currently tracked in the catalog.
    If include_filesystem is True, also discovers undocumented directories in mods/ containing a README.md.
    Returns a dict mapping lowercase slug to mod details dictionary.
    """
    root_path = Path(workspace_root) if workspace_root else REPO_ROOT
    if library_path is None:
        lib_file = root_path / "mods" / "library.md"
    else:
        lib_file = Path(library_path)

    tracked: Dict[str, Dict[str, Any]] = {}
    if lib_file.is_file():
        content = lib_file.read_text(encoding="utf-8")
        rows = parse_library_rows(content)
        for row in rows:
            slug = row["slug"]
            feature_match = re.match(
                r"(\d+)\s+implemented\b", row["features_documented"], re.IGNORECASE
            )
            if feature_match is None:
                raise ValueError(
                    f"Invalid Features Documented value for library entry '{slug}'."
                )
            tracked[slug.lower()] = {
                "mod_id": row["mod_id"],
                "name": row["name"],
                "slug": slug,
                "category": row["category"],
                "description": row["description"],
                "features_count": int(feature_match.group(1)),
                "spec_path": str(root_path / "mods" / slug / "README.md"),
            }

    if include_filesystem:
        mods_dir = root_path / "mods"
        if mods_dir.is_dir():
            for entry in sorted(mods_dir.iterdir()):
                if entry.is_dir() and not entry.name.startswith(".") and entry.name.lower() not in tracked:
                    readme_path = entry / "README.md"
                    if readme_path.is_file():
                        tracked[entry.name.lower()] = {
                            "name": entry.name,
                            "slug": entry.name,
                            "category": "General",
                            "description": "",
                            "features_count": 0,
                            "spec_path": str(readme_path),
                        }

    return tracked


def get_tracked_mod_identifiers(
    library_path: Optional[Any] = None,
    workspace_root: Optional[Any] = None,
) -> Tuple[Set[str], Set[str]]:
    """
    Parse mods/library.md to collect sets of already tracked mod slugs and lowercase names.
    Returns (tracked_slugs, tracked_names).
    """
    tracked_slugs: Set[str] = set()
    tracked_names: Set[str] = set()
    root_path = Path(workspace_root) if workspace_root else REPO_ROOT
    if library_path is None:
        lib_file = root_path / "mods" / "library.md"
    else:
        lib_file = Path(library_path)

    if lib_file.is_file():
        rows = parse_library_rows(lib_file.read_text(encoding="utf-8"))
        for row in rows:
            tracked_names.add(row["name"].lower())
            tracked_slugs.add(row["slug"].lower())

    return tracked_slugs, tracked_names


def prune_mod_from_library(library_path: Any, slug: str) -> bool:
    """Remove a mod's row from mods/library.md by slug."""
    lib_file = Path(library_path)
    if not lib_file.is_file():
        return False

    content = lib_file.read_text(encoding="utf-8")
    pattern = rf"^\|[^|\n]*\|[^|\n]*\|\s*`?{re.escape(slug)}`?\s*\|[^\n]*\n?"
    new_content, count = re.subn(pattern, "", content, flags=re.IGNORECASE | re.MULTILINE)
    if count == 0:
        legacy_pattern = rf"^\|[^\n]*\({re.escape(slug)}/README\.md\)[^\n]*\n?"
        new_content, count = re.subn(
            legacy_pattern, "", content, flags=re.IGNORECASE | re.MULTILINE
        )

    if count > 0:
        lib_file.write_text(new_content, encoding="utf-8")
        return True
    return False


def find_mod_folder(slug: str, mods_dir: Optional[Any] = None) -> Optional[Path]:
    """
    Finds the directory in mods_dir corresponding to a mod slug.
    Checks exact slug name, lowercase match, and normalized mod key match.
    Returns Path or None.
    """
    mods_path = Path(mods_dir).resolve() if mods_dir else get_subscribed_mods_dir().resolve()
    if not mods_path.is_dir():
        return None

    # 1. Exact or lowercased direct match
    for candidate_name in (slug, slug.lower()):
        candidate = mods_path / candidate_name
        if candidate.is_dir() and candidate.resolve().parent == mods_path:
            return candidate

    # 2. Normalized key match
    slug_norm = normalize_mod_key(slug)
    if slug_norm:
        for child in sorted(mods_path.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                if normalize_mod_key(child.name) == slug_norm:
                    if child.resolve().parent == mods_path:
                        return child

    return None


def find_orphaned_folders(
    mods_dir: Optional[Any] = None, active_slugs: Sequence[str] = ()
) -> List[Path]:
    """
    Scans mods_dir for non-hidden directories that do not correspond to any active
    (subscribed or tracked in library.md) mod slug.
    Returns list of Path objects.
    """
    mods_path = Path(mods_dir).resolve() if mods_dir else get_subscribed_mods_dir().resolve()
    if not mods_path.is_dir():
        return []

    active_normalized = {normalize_mod_key(s) for s in active_slugs if s}
    active_lower = {s.lower() for s in active_slugs if s}

    orphans: List[Path] = []
    for child in sorted(mods_path.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.resolve().parent != mods_path:
            continue
        child_name = child.name
        if child_name.lower() in active_lower or normalize_mod_key(child_name) in active_normalized:
            continue
        orphans.append(child)

    return orphans


def safe_batch_delete_folders(
    folder_paths: Sequence[Any],
    mods_dir: Optional[Any] = None,
    dry_run: bool = False,
) -> List[Dict[str, str]]:
    """
    Safely deletes a collection of mod data directories with strict safety validations.
    Guarantees every folder is an existing direct child of mods_dir.
    Returns list of dicts with deletion results: [{"path": str, "name": str, "status": str, "message": str}]
    """
    mods_path = Path(mods_dir).resolve() if mods_dir else get_subscribed_mods_dir().resolve()
    results: List[Dict[str, str]] = []
    seen: Set[Path] = set()

    for p in folder_paths:
        path_obj = Path(p).resolve()
        if path_obj in seen:
            continue
        seen.add(path_obj)

        folder_name = path_obj.name

        if not path_obj.exists():
            results.append({
                "path": str(path_obj),
                "name": folder_name,
                "status": "not_found",
                "message": f"Folder '{folder_name}' does not exist on disk.",
            })
            continue

        if not path_obj.is_dir():
            results.append({
                "path": str(path_obj),
                "name": folder_name,
                "status": "error",
                "message": f"Path '{path_obj}' is not a directory; refusing to delete.",
            })
            continue

        if path_obj == mods_path or path_obj.parent != mods_path:
            results.append({
                "path": str(path_obj),
                "name": folder_name,
                "status": "error",
                "message": f"Refusing to delete '{path_obj}' because it is not a direct child of '{mods_path}'.",
            })
            continue

        rel_label = f"mods/{folder_name}"
        if dry_run:
            results.append({
                "path": str(path_obj),
                "name": folder_name,
                "status": "dry_run_deleted",
                "message": f"[DRY-RUN] Would delete mod data folder '{rel_label}'",
            })
        else:
            try:
                shutil.rmtree(path_obj)
                results.append({
                    "path": str(path_obj),
                    "name": folder_name,
                    "status": "deleted",
                    "message": f"Deleted mod data folder '{rel_label}'",
                })
            except Exception as e:
                results.append({
                    "path": str(path_obj),
                    "name": folder_name,
                    "status": "failed",
                    "message": f"Failed to delete '{folder_name}': {e}",
                })

    return results


EMPTY_LIBRARY_HEADER = (
    "# Baldur's Gate 3 Mod Library\n\n"
    "This library catalogs documented Baldur's Gate 3 mods, their in-game features, and specifications for build crafting.\n"
)


def purge_library_mods(
    mods_dir: Optional[Any] = None,
    library_path: Optional[Any] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Purges all mod subdirectories in mods_dir and resets mods/library.md
    to the canonical empty header.
    Guarantees safety: only direct subdirectories of mods_dir are removed.
    Returns a dict with:
      - "purged_count": int
      - "deleted_folders": list of dicts from safe_batch_delete_folders
      - "library_reset": bool
      - "library_path": str
      - "mods_dir": str
      - "dry_run": bool
    """
    mods_path = Path(mods_dir).resolve() if mods_dir else get_subscribed_mods_dir().resolve()
    if library_path is None:
        lib_file = (mods_path / "library.md").resolve()
    else:
        lib_file = Path(library_path).resolve()

    target_folders = []
    if mods_path.is_dir():
        for child in sorted(mods_path.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                target_folders.append(child)

    delete_results = safe_batch_delete_folders(
        target_folders, mods_dir=mods_path, dry_run=dry_run
    )

    library_reset = False
    if lib_file.exists() or not dry_run:
        if not dry_run:
            lib_file.parent.mkdir(parents=True, exist_ok=True)
            lib_file.write_text(EMPTY_LIBRARY_HEADER, encoding="utf-8")
        library_reset = True

    purged_count = sum(
        1
        for res in delete_results
        if res.get("status") in ("deleted", "dry_run_deleted")
    )

    return {
        "purged_count": purged_count,
        "deleted_folders": delete_results,
        "library_reset": library_reset,
        "library_path": str(lib_file),
        "mods_dir": str(mods_path),
        "dry_run": dry_run,
    }
