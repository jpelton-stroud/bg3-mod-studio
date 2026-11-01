#!/usr/bin/env python3
"""
scaffold_common.py
------------------
Foundational scaffolding primitives, XML pretty printing, path resolution,
and typed result contracts for Baldur's Gate 3 asset authoring.
"""

from __future__ import annotations

import collections.abc
import struct
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from bg3_core.env_paths import resolve_mod_dir
from bg3_core.larian_parsers import PATCH_8_VERSION

PATCH_8_VERSION_ATTRIBUTES = {
    "major": str(PATCH_8_VERSION["major"]),
    "minor": str(PATCH_8_VERSION["minor"]),
    "revision": str(PATCH_8_VERSION["revision"]),
    "build": str(PATCH_8_VERSION["build"]),
}


@dataclass
class ScaffoldResult(collections.abc.Mapping[str, Any]):
    """Standard typed result contract for all Baldur's Gate 3 asset scaffolding operations."""

    success: bool
    mod: str
    name: str
    asset_type: str
    status: str = "created"
    uuid: str | None = None
    file: str | None = None
    dry_run: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converts result into a standard serializable dictionary."""
        out: dict[str, Any] = {
            "success": self.success,
            "status": self.status,
            "mod": self.mod,
            "name": self.name,
            "asset_type": self.asset_type,
            "uuid": self.uuid,
            "file": self.file,
            "dry_run": self.dry_run,
        }
        # Populate specific aliases for callers expecting legacy/generator-specific keys
        if self.asset_type in ("class", "class-description"):
            out.setdefault("class_name", self.name)
            if self.uuid:
                out.setdefault("class_uuid", self.uuid)
        elif self.asset_type == "feat":
            out.setdefault("feat_name", self.name)
            if self.uuid:
                out.setdefault("feat_uuid", self.uuid)
        elif self.asset_type == "stat":
            out.setdefault("entry_name", self.name)
            out.setdefault("stat_file", self.file)
        elif self.asset_type == "action-resource":
            out.setdefault("resource_name", self.name)
            if self.uuid:
                out.setdefault("resource_uuid", self.uuid)
        elif self.asset_type in ("atlas", "icon-uvs"):
            out.setdefault("atlas_name", self.name)
            if self.uuid:
                out.setdefault("atlas_uuid", self.uuid)
        elif self.asset_type == "race":
            if self.uuid:
                out.setdefault("race_uuid", self.uuid)
        elif self.asset_type == "origin":
            if self.uuid:
                out.setdefault("origin_uuid", self.uuid)

        out.update(self.details)
        return out

    def __getitem__(self, key: str) -> Any:
        d = self.to_dict()
        if key in d:
            return d[key]
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


def prettify_xml(element: ET.Element) -> str:
    """Formats an ElementTree XML element with 4-space indentation and standard header."""
    rough_string = ET.tostring(element, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty = reparsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")
    lines = [line for line in pretty.splitlines() if line.strip()]
    if lines and lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return "\n".join(lines) + "\n"


def resolve_mod_paths(
    mod_name_or_path: str, _workspace_root: Path | None = None
) -> tuple[Path, Path, Path, str]:
    """Resolves mod root directory, Public/<ModFolder> directory, and English localization XML path."""
    candidate = resolve_mod_dir(mod_name_or_path, prefer_my_mods=True)
    if candidate is None or not candidate.is_dir():
        raise FileNotFoundError(f"Mod directory not found: '{mod_name_or_path}'")

    public_dir = candidate / "Public"
    if not public_dir.is_dir():
        raise FileNotFoundError(f"Missing 'Public/' directory in mod: '{candidate}'")

    subdirs = [d for d in public_dir.iterdir() if d.is_dir() and d.name != "Shared"]
    if not subdirs:
        raise FileNotFoundError(f"No mod folder found under '{public_dir}'")

    mod_folder_dir = subdirs[0]
    loc_file = candidate / "Localization" / "English" / f"{candidate.name}.xml"
    if not loc_file.exists():
        xml_files = (
            list((candidate / "Localization" / "English").glob("*.xml"))
            if (candidate / "Localization" / "English").is_dir()
            else []
        )
        if xml_files:
            loc_file = xml_files[0]

    return candidate, mod_folder_dir, loc_file, candidate.name


def create_empty_lsx(region_id: str, root_node_id: str = "root") -> ET.Element:
    """Creates a standard Larian v4.8 LSX root element with region and empty children."""
    root = ET.Element("save")
    ET.SubElement(root, "version", **PATCH_8_VERSION_ATTRIBUTES)
    reg = ET.SubElement(root, "region", id=region_id)
    r_node = ET.SubElement(reg, "node", id=root_node_id)
    ET.SubElement(r_node, "children")
    return root


def get_or_create_root_children(
    root: ET.Element, region_id: str, root_node_id: str = "root"
) -> ET.Element:
    """Safely traverses or builds the <region>/<node id='...'>/<children> hierarchy."""
    children = root.find(f".//region[@id='{region_id}']/node[@id='{root_node_id}']/children")
    if children is not None:
        return children

    children = root.find(f".//node[@id='{root_node_id}']/children")
    if children is not None:
        return children

    r_node = root.find(f".//node[@id='{root_node_id}']")
    if r_node is None:
        reg = root.find(f".//region[@id='{region_id}']")
        if reg is None:
            reg = ET.SubElement(root, "region", id=region_id)
        r_node = ET.SubElement(reg, "node", id=root_node_id)

    children = ET.SubElement(r_node, "children")
    return children


def generate_placeholder_png(
    width: int = 512, height: int = 512, r: int = 45, g: int = 52, b: int = 64
) -> bytes:
    """Generates a minimal valid uncompressed RGB PNG using standard library zlib."""

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = make_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))

    # Raw scanlines: each line starts with filter byte 0 (None) followed by RGB bytes
    row = b"\x00" + bytes([r, g, b]) * width
    raw_data = row * height
    compressed = zlib.compress(raw_data, level=6)
    idat = make_chunk(b"IDAT", compressed)
    iend = make_chunk(b"IEND", b"")

    return header + ihdr + idat + iend
