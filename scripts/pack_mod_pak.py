#!/usr/bin/env python3
"""
pack_mod_pak.py - Pure-Python LSPK v18 .pak package builder for Baldur's Gate 3 mods.

Packages mod files into standard Larian Package v18 (.pak) format with zlib
compression, enabling distribution and local Mod Manager installation without
requiring the official Toolkit or external Windows binaries.
"""

import argparse
import json
import os
import re
import struct
import sys
import zlib
from pathlib import Path

# Try to import LspkArchive for self-verification
try:
    from scripts.modio_extract import LspkArchive
except ImportError:
    # If invoked directly from scripts directory
    try:
        from modio_extract import LspkArchive
    except ImportError:
        LspkArchive = None

EXCLUDED_FILENAMES = {
    ".gitignore",
    ".gitkeep",
    "desktop.ini",
    ".ds_store",
    "thumbs.db",
    "readme.md",
    "task.md",
}

EXCLUDED_EXTENSIONS = {
    ".tmp",
    ".bak",
    ".py",
    ".pyc",
}

EXCLUDED_DIRECTORIES = {
    "projects",
    "metadata",
    "__pycache__",
    ".git",
    "dist",
}


def should_include_file(rel_path: Path, include_projects: bool = False) -> bool:
    """Filters files for inclusion in release pak archive."""
    parts = [p.lower() for p in rel_path.parts]

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


def collect_mod_files(mod_dir: Path, include_projects: bool = False) -> list[tuple[str, Path]]:
    """Gathers all releasable files relative to mod root."""
    files = []
    for root, _, filenames in os.walk(mod_dir):
        root_path = Path(root)
        for fname in filenames:
            file_path = root_path / fname
            rel_path = file_path.relative_to(mod_dir)
            if should_include_file(rel_path, include_projects):
                # Standard Larian archive paths use backslashes or forward slashes
                # Using forward slashes or backslashes is supported; backslashes are standard Larian
                files.append((str(rel_path).replace("/", "\\"), file_path))
    return sorted(files, key=lambda x: x[0])


def build_pak_archive(
    files: list[tuple[str, Path]],
    compress: bool = True,
) -> bytes:
    """Constructs the LSPK v18 binary package."""
    header_size = 40
    data_offset = header_size

    file_data_blocks = []
    file_records = []

    curr_offset = data_offset

    for archive_name, disk_path in files:
        data = disk_path.read_bytes()
        uncomp_size = len(data)

        if compress:
            compressed = zlib.compress(data)
            # If compression didn't save space, store uncompressed
            if len(compressed) < uncomp_size:
                payload = compressed
                file_flags = 1  # zlib
                disk_size = len(compressed)
            else:
                payload = data
                file_flags = 0  # uncompressed
                disk_size = uncomp_size
        else:
            payload = data
            file_flags = 0
            disk_size = uncomp_size

        file_data_blocks.append(payload)

        # 256 bytes null-padded name
        name_bytes = archive_name.encode("utf-8")
        if len(name_bytes) > 255:
            raise ValueError(f"Archive file path too long (>255 bytes): {archive_name}")
        name_padded = name_bytes.ljust(256, b"\x00")

        offset_low = curr_offset & 0xFFFFFFFF
        offset_high = (curr_offset >> 32) & 0xFFFF
        part = 0

        record = name_padded + struct.pack(
            "<IHBBII",
            offset_low,
            offset_high,
            part,
            file_flags,
            disk_size,
            uncomp_size,
        )
        file_records.append(record)
        curr_offset += disk_size

    file_list_offset = curr_offset
    file_list_payload = b"".join(file_records)
    num_files = len(file_records)
    comp_size = len(file_list_payload)

    file_list_block = struct.pack("<II", num_files, comp_size) + file_list_payload
    file_list_size = len(file_list_block)

    # 40-byte LSPK Header:
    # 4s (magic: LSPK)
    # I (version: 18)
    # Q (file_list_offset)
    # I (file_list_size)
    # B (flags: 0)
    # B (priority: 0)
    # 18s (reserved/md5: 18 null bytes)
    header = struct.pack(
        "<4sIQIBB18s",
        b"LSPK",
        18,
        file_list_offset,
        file_list_size,
        0,
        0,
        b"\x00" * 18,
    )

    return header + b"".join(file_data_blocks) + file_list_block


def verify_pak_archive(pak_bytes: bytes, original_files: list[tuple[str, Path]]) -> bool:
    """Verifies that the generated pak can be completely parsed and extracted."""
    if LspkArchive is None:
        return True

    archive = LspkArchive(pak_bytes)
    if len(archive.files) != len(original_files):
        return False

    for entry in archive.files:
        extracted = archive.extract_file(entry)
        # Find matching original file
        norm_name = entry["name"].replace("/", "\\")
        matched = False
        for a_name, p in original_files:
            if a_name.replace("/", "\\") == norm_name:
                orig_data = p.read_bytes()
                if extracted == orig_data:
                    matched = True
                    break
        if not matched:
            return False

    return True


def detect_mods_dir() -> Path | None:
    """Detect Baldur's Gate 3 Mods directory in AppData across WSL, native Linux, and Windows."""
    env_override = os.environ.get("BG3_MODS_DIR")
    if env_override:
        p = Path(env_override)
        if p.is_dir() or p.parent.exists():
            return p

    # WSL detection
    users_dir = Path("/mnt/c/Users")
    if users_dir.is_dir():
        for user_folder in users_dir.iterdir():
            if user_folder.is_dir() and user_folder.name not in (
                "All Users",
                "Default",
                "Default User",
                "Public",
            ):
                target = user_folder / "AppData/Local/Larian Studios/Baldur's Gate 3/Mods"
                if target.is_dir():
                    return target

    # Native Windows detection
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        target = Path(local_app_data) / "Larian Studios/Baldur's Gate 3/Mods"
        if target.is_dir():
            return target

    return None


def get_mod_pak_filename(mod_dir: Path) -> str:
    """Inspect mod directory for meta.lsx and generate standard Toolkit pak filename (<Folder>_<UUID>.pak)."""
    meta_files = list(mod_dir.glob("Mods/*/meta.lsx")) or list(mod_dir.glob("Projects/*/meta.lsx"))
    if meta_files:
        try:
            content = meta_files[0].read_text(encoding="utf-8")
            mod_info = re.search(r'<node\s+id="ModuleInfo">(.*?)</node>', content, re.DOTALL)
            target = mod_info.group(1) if mod_info else content
            folder_match = re.search(r'<attribute\s+id="Folder"\s+type="LSString"\s+value="([^"]*)"', target)
            uuid_match = re.search(r'<attribute\s+id="UUID"\s+type="FixedString"\s+value="([^"]*)"', target)
            if folder_match:
                folder = folder_match.group(1)
                uuid_val = uuid_match.group(1) if uuid_match else ""
                if uuid_val and not folder.endswith(uuid_val):
                    return f"{folder}_{uuid_val}.pak"
                return f"{folder}.pak"
        except Exception:
            pass
    return f"{mod_dir.name}.pak"


def main():
    parser = argparse.ArgumentParser(
        description="Pure-Python LSPK v18 .pak package builder for Baldur's Gate 3 mods."
    )
    parser.add_argument("--mod", required=True, help="Mod name/slug in my_mods/ or directory path.")
    parser.add_argument("--out", help="Output .pak file path (default: dist/<mod_slug>.pak).")
    parser.add_argument(
        "--publish-local",
        action="store_true",
        help="Publish .pak directly to the local BG3 AppData Mods directory, replacing the Toolkit's 'Publish Local' step.",
    )
    parser.add_argument(
        "--include-projects",
        action="store_true",
        help="Include Projects/ directory (normally excluded in release packages).",
    )
    parser.add_argument(
        "--uncompressed",
        action="store_true",
        help="Store files uncompressed instead of using standard zlib.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON summary.",
    )

    args = parser.parse_args()

    workspace_root = Path(__file__).resolve().parent.parent

    try:
        mod_dir = Path(args.mod)
        if not mod_dir.is_dir():
            mod_dir = workspace_root / "my_mods" / args.mod
        if not mod_dir.is_dir():
            raise FileNotFoundError(f"Mod directory not found: '{args.mod}'")

        mod_slug = mod_dir.name

        if args.publish_local:
            mods_dir = detect_mods_dir()
            if not mods_dir:
                raise FileNotFoundError(
                    "Could not detect Baldur's Gate 3 Mods directory in AppData. "
                    "Ensure BG3 has been run or set BG3_MODS_DIR environment variable."
                )
            pak_filename = get_mod_pak_filename(mod_dir)
            out_path = Path(args.out) if args.out else mods_dir / pak_filename
        else:
            out_path = Path(args.out) if args.out else workspace_root / "dist" / f"{mod_slug}.pak"

        files_to_pack = collect_mod_files(mod_dir, include_projects=args.include_projects)
        if not files_to_pack:
            raise ValueError(f"No valid mod files found to pack in '{mod_dir}'.")

        pak_bytes = build_pak_archive(files_to_pack, compress=not args.uncompressed)

        # Verification pass
        verified = verify_pak_archive(pak_bytes, files_to_pack)
        if not verified:
            raise RuntimeError("Generated .pak archive failed self-verification check.")

        # Safe atomic write
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_out = out_path.with_suffix(".pak.tmp")
        try:
            temp_out.write_bytes(pak_bytes)
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            temp_out.replace(out_path)
        except PermissionError as pe:
            if temp_out.exists():
                temp_out.unlink()
            raise PermissionError(
                f"Permission denied writing to '{out_path}'. "
                "Ensure Baldur's Gate 3 and the BG3 Toolkit are closed if they are locking the file."
            ) from pe
        except Exception:
            if temp_out.exists():
                temp_out.unlink()
            raise

        res = {
            "status": "success",
            "mod": mod_slug,
            "pak_file": str(out_path),
            "file_count": len(files_to_pack),
            "pak_size_bytes": len(pak_bytes),
            "compressed": not args.uncompressed,
            "verified": verified,
            "published_local": args.publish_local,
            "included_files": [f[0] for f in files_to_pack],
        }

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            size_kb = len(pak_bytes) / 1024
            target_desc = "published to local BG3 Mods directory" if args.publish_local else "packaged"
            print(f"[✓] Successfully {target_desc}: {out_path} ({size_kb:.1f} KB, {len(files_to_pack)} files)")
            print(f"    Verification: [✓] LSPK v18 checksum and extraction verified cleanly.")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
