"""Shared Larian Studios format parsers, Version64 encoding, functor tokenizers, and binary .loca compilers."""

import re
import struct
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HANDLE_PATTERN = re.compile(r"(?<![a-zA-Z0-9_])(h[0-9a-fA-F]{32}|h[a-zA-Z0-9_]{30,40})(?:;\d+)?")

PATCH_8_VERSION = {"major": "4", "minor": "8", "revision": "0", "build": "700"}


def generate_larian_handle() -> str:
    """Generates a standard Larian localization handle (h...g...g...g...g...)."""
    u_str = str(uuid.uuid4()).replace("-", "g")
    return f"h{u_str}"


def format_patch8_lsx_header() -> str:
    """Returns the standardized Patch 8 XML version header element."""
    return f'<version major="{PATCH_8_VERSION["major"]}" minor="{PATCH_8_VERSION["minor"]}" revision="{PATCH_8_VERSION["revision"]}" build="{PATCH_8_VERSION["build"]}"/>'


# ----------------------------------------------------------------------
# Version64 Encoding & Decoding
# ----------------------------------------------------------------------
def calculate_version64(major: int = 1, minor: int = 0, revision: int = 0, build: int = 0) -> int:
    """Encode major.minor.revision.build into Larian Version64 integer."""
    return (major << 55) | (minor << 47) | (revision << 31) | (build & 0x7FFFFFFF)


def decode_version64(v: int) -> Tuple[int, int, int, int]:
    """Decode Larian Version64 integer into (major, minor, revision, build)."""
    major = (v >> 55) & 0x1FF
    minor = (v >> 47) & 0xFF
    revision = (v >> 31) & 0xFFFF
    build = v & 0x7FFFFFFF
    return major, minor, revision, build


def format_version_tuple(tup: Tuple[int, int, int, int]) -> str:
    return f"{tup[0]}.{tup[1]}.{tup[2]}.{tup[3]}"


def parse_version_str(ver_str: str) -> Tuple[int, int, int, int]:
    parts = ver_str.strip().split(".")
    if len(parts) == 1:
        return int(parts[0]), 0, 0, 0
    elif len(parts) == 2:
        return int(parts[0]), int(parts[1]), 0, 0
    elif len(parts) == 3:
        return int(parts[0]), int(parts[1]), int(parts[2]), 0
    elif len(parts) == 4:
        return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    else:
        raise ValueError(
            f"Invalid version string format: '{ver_str}' (expected major.minor.revision.build)"
        )


# ----------------------------------------------------------------------
# Parenthesis-Aware Larian Property / Functor Splitting
# ----------------------------------------------------------------------
def split_larian_items(
    raw: str, separators: Tuple[str, ...] = (",", ";")
) -> List[str]:
    """Split a string on commas/semicolons ONLY at top level (outside parentheses and quotes)."""
    if not raw or not raw.strip():
        return []

    items: List[str] = []
    buf: List[str] = []
    depth = 0
    in_quote: Optional[str] = None

    for ch in raw:
        if in_quote:
            buf.append(ch)
            if ch == in_quote:
                in_quote = None
            continue

        if ch in ('"', "'"):
            in_quote = ch
            buf.append(ch)
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif depth == 0 and ch in separators:
            token = "".join(buf).strip()
            if token:
                items.append(token)
            buf = []
        else:
            buf.append(ch)

    trailing = "".join(buf).strip()
    if trailing:
        items.append(trailing)
    return items


def has_balanced_parens(text: str) -> bool:
    """Return True if parentheses in a Larian boost/passive/spell expression are balanced."""
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


# ----------------------------------------------------------------------
# Localization (.xml & Binary .loca) Parsing and Compilation
# ----------------------------------------------------------------------
def clean_loc_text(text: str) -> str:
    """Strip Larian markup tags like <LSTag ...>text</LSTag> from localized text."""
    if not text:
        return ""
    return re.sub(r"</?LSTag[^>]*>", "", text).strip()


def parse_localization_xml(xml_bytes: bytes, strip_tags: bool = True) -> Dict[str, str]:
    """Parse Larian <contentList> XML bytes into a handle -> text dictionary."""
    loc_dict: Dict[str, str] = {}
    if not xml_bytes:
        return loc_dict
    try:
        root = ET.fromstring(xml_bytes.decode("utf-8", errors="ignore"))
        for elem in root.findall(".//content"):
            handle = elem.get("contentuid")
            text = elem.text or ""
            if handle:
                loc_dict[handle] = clean_loc_text(text) if strip_tags else text
    except Exception:
        pass
    return loc_dict


def parse_loca_bytes(data: bytes, strip_tags: bool = True) -> Dict[str, str]:
    """Parse binary Larian LOCA format into a handle -> text dictionary.

    LOCA Binary Layout:
      - Header (12 bytes): <4sII -> magic b'LOCA', uint32 num_entries, uint32 texts_offset
      - Entry records (num_entries * 70 bytes): <64sHI -> 64-byte null-padded ASCII handle, uint16 version, uint32 byte_len
      - Texts payload (starting at texts_offset): UTF-8 null-terminated strings of length `byte_len`
    """
    loc_dict: Dict[str, str] = {}
    if not data or len(data) < 12 or data[:4] != b"LOCA":
        return loc_dict

    sig, num_entries, texts_offset = struct.unpack_from("<4sII", data, 0)
    entry_pos = 12
    text_pos = texts_offset

    for _ in range(num_entries):
        if entry_pos + 70 > len(data):
            break
        raw_handle, _version, length = struct.unpack_from("<64sHI", data, entry_pos)
        entry_pos += 70
        handle = raw_handle.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        if text_pos + length > len(data):
            break
        raw_str = data[text_pos : text_pos + length]
        text_pos += length
        if raw_str.endswith(b"\x00"):
            raw_str = raw_str[:-1]
        decoded = raw_str.decode("utf-8", errors="replace")
        if handle:
            loc_dict[handle] = clean_loc_text(decoded) if strip_tags else decoded

    return loc_dict


def parse_localization_bytes(data: bytes, filename: str = "", strip_tags: bool = True) -> Dict[str, str]:
    """Parse either XML or binary LOCA localization bytes into a handle -> text dictionary."""
    if not data:
        return {}
    if data[:4] == b"LOCA" or filename.lower().endswith(".loca"):
        return parse_loca_bytes(data, strip_tags=strip_tags)
    return parse_localization_xml(data, strip_tags=strip_tags)


def compile_xml_bytes_to_loca(xml_bytes: bytes) -> bytes:
    """Compile Larian <contentList> XML bytes into binary LOCA bytes."""
    root = ET.fromstring(xml_bytes.decode("utf-8"))
    entries: List[Tuple[str, int, bytes]] = []
    for elem in root.findall(".//content"):
        handle = (elem.get("contentuid") or "").strip()
        if not handle:
            continue
        try:
            version = int(elem.get("version") or "1")
        except ValueError:
            version = 1
        text = elem.text or ""
        encoded_text = text.encode("utf-8") + b"\x00"
        entries.append((handle, version, encoded_text))

    num_entries = len(entries)
    texts_offset = 12 + num_entries * 70
    out = bytearray()
    out.extend(struct.pack("<4sII", b"LOCA", num_entries, texts_offset))

    for handle, version, encoded_text in entries:
        handle_bytes = handle.encode("ascii", errors="ignore")[:63]
        padded_handle = handle_bytes.ljust(64, b"\x00")
        out.extend(struct.pack("<64sHI", padded_handle, version, len(encoded_text)))

    for _handle, _version, encoded_text in entries:
        out.extend(encoded_text)

    return bytes(out)


def compile_xml_to_loca(xml_path: Path, loca_path: Optional[Path] = None) -> Path:
    """Compile a Localization/<Lang>/<Mod>.xml file into a binary .loca file on disk."""
    target = loca_path if loca_path is not None else xml_path.with_suffix(".loca")
    xml_bytes = xml_path.read_bytes()
    loca_bytes = compile_xml_bytes_to_loca(xml_bytes)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(loca_bytes)
    return target


def update_localization_xml(loc_file: Path, entries: List[Tuple[str, str]], dry_run: bool = False) -> None:
    """Appends content tags for handles and text to the Localization XML file."""
    if dry_run or not entries:
        return

    loc_file.parent.mkdir(parents=True, exist_ok=True)
    if loc_file.exists():
        content = loc_file.read_text(encoding="utf-8")
    else:
        content = '<?xml version="1.0" encoding="utf-8"?>\n<contentList xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n</contentList>\n'

    addition_lines = []
    for handle, text in entries:
        safe_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
        addition_lines.append(f'  <content contentuid="{handle}" version="1">{safe_text}</content>')

    addition_block = "\n".join(addition_lines) + "\n"
    if "</contentList>" in content:
        idx = content.rfind("</contentList>")
        new_content = content[:idx] + addition_block + content[idx:]
    else:
        new_content = content + "\n" + addition_block + "</contentList>\n"

    loc_file.write_text(new_content, encoding="utf-8")


# ----------------------------------------------------------------------
# Stats, Meta, and Progressions Parsers
# ----------------------------------------------------------------------
def parse_stats_txt(txt_bytes: bytes, loc_dict: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
    """Parse Larian stats text (new entry / data lines)."""
    loc_dict = loc_dict or {}
    text = txt_bytes.decode("utf-8", errors="ignore")
    entries: Dict[str, Dict[str, Any]] = {}
    current_entry: Optional[Dict[str, Any]] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        entry_match = re.match(r'^new\s+entry\s+"([^"]+)"', line, re.I)
        if entry_match:
            name = entry_match.group(1)
            current_entry = {
                "name": name,
                "type": "",
                "using": "",
                "data": {},
            }
            entries[name] = current_entry
            continue

        if not current_entry:
            continue

        type_match = re.match(r'^type\s+"([^"]+)"', line, re.I)
        if type_match:
            current_entry["type"] = type_match.group(1)
            continue

        using_match = re.match(r'^using\s+"([^"]+)"', line, re.I)
        if using_match:
            current_entry["using"] = using_match.group(1)
            continue

        data_match = re.match(r'^data\s+"([^"]+)"\s+"([^"]*)"', line, re.I)
        if data_match:
            key, val = data_match.group(1), data_match.group(2)
            current_entry["data"][key] = val

    for _name, entry in entries.items():
        data = entry["data"]
        disp_handle = data.get("DisplayName", "").split(";")[0]
        desc_handle = data.get("Description", "").split(";")[0]
        entry["resolved_display_name"] = loc_dict.get(disp_handle, data.get("DisplayName", ""))
        entry["resolved_description"] = loc_dict.get(desc_handle, data.get("Description", ""))

    return entries


def parse_meta_lsx(lsx_bytes: bytes) -> Dict[str, str]:
    """Parse meta.lsx for mod UUID, author, version, and description."""
    meta: Dict[str, str] = {}
    if not lsx_bytes:
        return meta
    try:
        text = lsx_bytes.decode("utf-8", errors="ignore")
        root = ET.fromstring(text)
        for node in root.findall(".//node[@id='ModuleInfo']//attribute"):
            attr_id = node.get("id")
            val = node.get("value")
            if attr_id and val is not None:
                meta[attr_id] = val
    except Exception:
        pass
    return meta


def parse_progressions_lsx(lsx_bytes: bytes) -> List[Dict[str, str]]:
    """Parse Progressions.lsx for progression nodes."""
    progressions: List[Dict[str, str]] = []
    if not lsx_bytes:
        return progressions
    try:
        text = lsx_bytes.decode("utf-8", errors="ignore")
        root = ET.fromstring(text)
        for node in root.findall(".//node[@id='Progression']"):
            p: Dict[str, str] = {}
            for attr in node.findall("./attribute"):
                attr_id = attr.get("id")
                val = attr.get("value")
                if attr_id and val is not None:
                    p[attr_id] = val
            if p:
                progressions.append(p)
    except Exception:
        pass
    return progressions


def find_mod_meta_files(mod_dir: Path) -> List[Path]:
    """Find meta.lsx files in both Toolkit layout (Mods/*/meta.lsx) and unpacked layout (data/meta.lsx)."""
    results = list(mod_dir.glob("Mods/*/meta.lsx")) + list(mod_dir.glob("Projects/*/meta.lsx"))
    data_meta = mod_dir / "data" / "meta.lsx"
    if data_meta.is_file():
        results.append(data_meta)
    for extra in mod_dir.glob("data/**/meta.lsx"):
        if extra not in results:
            results.append(extra)
    return results


def find_mod_progression_files(mod_dir: Path) -> List[Path]:
    """Find Progressions.lsx files in both Toolkit layout and unpacked community layout."""
    results = list(mod_dir.glob("Public/*/Progressions/Progressions.lsx"))
    for p in mod_dir.glob("data/**/Progressions*.lsx"):
        if p not in results:
            results.append(p)
    return results
