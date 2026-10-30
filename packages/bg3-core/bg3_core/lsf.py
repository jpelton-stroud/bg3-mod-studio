"""packages/bg3-core/bg3_core/lsf.py.

Pure-Python, zero-dependency LSF (Larian Save/Serialization Format) v3-v7
binary parser and AST decompiler for Baldur's Gate 3 saves and mod assets.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from bg3_core.lspk import lz4_block_compress, lz4_block_decompress

# Magic identifier for LSF files
LSF_MAGIC = b"LSOF"

# Attribute Type IDs
TYPE_NONE = 0
TYPE_UINT8 = 1
TYPE_INT16 = 2
TYPE_UINT16 = 3
TYPE_INT32 = 4
TYPE_UINT32 = 5
TYPE_FLOAT = 6
TYPE_DOUBLE = 7
TYPE_IVEC2 = 8
TYPE_IVEC3 = 9
TYPE_IVEC4 = 10
TYPE_VEC2 = 11
TYPE_VEC3 = 12
TYPE_VEC4 = 13
TYPE_MAT2 = 14
TYPE_MAT3 = 15
TYPE_MAT3X4 = 16
TYPE_MAT4X3 = 17
TYPE_MAT4 = 18
TYPE_BOOL = 19
TYPE_STRING = 20
TYPE_PATH = 21
TYPE_FIXED_STRING = 22
TYPE_LS_STRING = 23
TYPE_WSTRING = 24
TYPE_LS_WSTRING = 25
TYPE_UUID = 26
TYPE_INT64 = 27
TYPE_UINT64 = 28
TYPE_TRANSLATED_STRING = 29


@dataclass
class LsfAttribute:
    """An attribute of an LSF node."""

    name: str
    type_id: int
    value: Any


@dataclass
class LsfNode:
    """An AST node within an LSF document tree."""

    name: str
    attributes: dict[str, LsfAttribute] = field(default_factory=dict)
    children: list[LsfNode] = field(default_factory=list)

    def get_attr_value(self, name: str, default: Any = None) -> Any:
        """Return the value of an attribute if present, else default."""
        attr = self.attributes.get(name)
        if attr is not None:
            return attr.value
        return default

    def find_first(self, name: str) -> Optional[LsfNode]:
        """Find the first descendant node matching name via depth-first search."""
        for child in self.children:
            if child.name == name:
                return child
            found = child.find_first(name)
            if found is not None:
                return found
        return None

    def find_all(self, name: str) -> list[LsfNode]:
        """Find all descendant nodes matching name."""
        matches: list[LsfNode] = []
        for child in self.children:
            if child.name == name:
                matches.append(child)
            matches.extend(child.find_all(name))
        return matches


@dataclass
class LsfDocument:
    """An LSF document representation containing root nodes and metadata."""

    root_nodes: list[LsfNode] = field(default_factory=list)
    version: int = 7
    engine_version: int = 0

    def find_first(self, name: str) -> Optional[LsfNode]:
        """Find the first matching node across all roots."""
        for root in self.root_nodes:
            if root.name == name:
                return root
            found = root.find_first(name)
            if found is not None:
                return found
        return None

    def find_all(self, name: str) -> list[LsfNode]:
        """Find all matching nodes across all roots."""
        matches: list[LsfNode] = []
        for root in self.root_nodes:
            if root.name == name:
                matches.append(root)
            matches.extend(root.find_all(name))
        return matches

    @classmethod
    def from_bytes(cls, data: bytes) -> LsfDocument:
        """Parse raw LSF binary data (versions 3 to 7) into an LsfDocument AST."""
        if len(data) < 16:
            raise ValueError(f"Data too short for LSF header: {len(data)} bytes")

        magic = data[:4]
        if magic != LSF_MAGIC:
            raise ValueError(f"Invalid LSF magic: {magic!r}, expected {LSF_MAGIC!r}")

        version, engine_version = struct.unpack_from("<Iq", data, 4)
        if version < 3 or version > 7:
            raise ValueError(f"Unsupported LSF version: {version}")

        hdr_size = 64 if version >= 7 else 56
        if len(data) < hdr_size:
            raise ValueError(f"Data too short for header size {hdr_size}: {len(data)} bytes")

        # Read 4 chunk descriptors: Strings, Nodes, Attributes, Values
        # Each has (uncompressed_size: uint32, compressed_size: uint32)
        chunk_descs: list[tuple[int, int]] = []
        off = 16
        for _ in range(4):
            uncomp_sz, comp_sz = struct.unpack_from("<II", data, off)
            chunk_descs.append((uncomp_sz, comp_sz))
            off += 8

        # Extract and decompress chunks
        chunks: list[bytes] = []
        current_offset = hdr_size
        for uncomp_sz, comp_sz in chunk_descs:
            if comp_sz == 0 or comp_sz == uncomp_sz:
                chunk_raw = data[current_offset : current_offset + uncomp_sz]
                chunks.append(chunk_raw)
                current_offset += uncomp_sz
            else:
                comp_data = data[current_offset : current_offset + comp_sz]
                uncomp_data = lz4_block_decompress(comp_data, uncomp_sz)
                chunks.append(uncomp_data)
                current_offset += comp_sz

        strings_chunk, nodes_chunk, attributes_chunk, values_chunk = chunks

        # 1. Parse string table
        strings = _parse_string_table(strings_chunk)

        # 2. Parse nodes table
        # Each node record: name_idx (uint32), parent_idx (int32), next_sibling_idx (int32), first_attr_idx (int32)
        raw_nodes: list[dict[str, Any]] = []
        node_rec_size = 16
        num_nodes = len(nodes_chunk) // node_rec_size
        for i in range(num_nodes):
            name_idx, parent_idx, next_sibling_idx, first_attr_idx = struct.unpack_from(
                "<Iiii", nodes_chunk, i * node_rec_size
            )
            node_name = strings[name_idx] if 0 <= name_idx < len(strings) else f"UnknownNode_{name_idx}"
            raw_nodes.append({
                "index": i,
                "name": node_name,
                "parent_idx": parent_idx,
                "next_sibling_idx": next_sibling_idx,
                "first_attr_idx": first_attr_idx,
                "node": LsfNode(name=node_name),
            })

        # 3. Parse attributes table
        # Each attribute record: name_idx (uint32), type_id (uint32), next_attr_idx (int32), value_offset (uint32), value_length (uint32)
        raw_attrs: list[dict[str, Any]] = []
        attr_rec_size = 20
        num_attrs = len(attributes_chunk) // attr_rec_size
        for i in range(num_attrs):
            name_idx, type_id, next_attr_idx, val_offset, val_length = struct.unpack_from(
                "<IIiII", attributes_chunk, i * attr_rec_size
            )
            attr_name = strings[name_idx] if 0 <= name_idx < len(strings) else f"UnknownAttr_{name_idx}"
            attr_val = _parse_attribute_value(values_chunk, val_offset, val_length, type_id)
            raw_attrs.append({
                "index": i,
                "name": attr_name,
                "type_id": type_id,
                "next_attr_idx": next_attr_idx,
                "attribute": LsfAttribute(name=attr_name, type_id=type_id, value=attr_val),
            })

        # 4. Attach attributes to nodes
        for r_node in raw_nodes:
            curr_attr_idx = r_node["first_attr_idx"]
            visited_attrs = set()
            while 0 <= curr_attr_idx < len(raw_attrs) and curr_attr_idx not in visited_attrs:
                visited_attrs.add(curr_attr_idx)
                attr_info = raw_attrs[curr_attr_idx]
                r_node["node"].attributes[attr_info["name"]] = attr_info["attribute"]
                curr_attr_idx = attr_info["next_attr_idx"]

        # 5. Build tree hierarchy
        root_nodes: list[LsfNode] = []
        for r_node in raw_nodes:
            parent_idx = r_node["parent_idx"]
            if parent_idx < 0 or parent_idx >= len(raw_nodes):
                root_nodes.append(r_node["node"])
            else:
                raw_nodes[parent_idx]["node"].children.append(r_node["node"])

        return cls(root_nodes=root_nodes, version=version, engine_version=engine_version)

    def to_bytes(self, compress: bool = True) -> bytes:
        """Serialize this LsfDocument into a binary LSF (LSOF v7) stream."""
        # 1. Flatten all nodes and gather unique strings
        all_nodes: list[LsfNode] = []
        node_parents: dict[int, int] = {}
        string_table: list[str] = []
        string_map: dict[str, int] = {}

        def get_string_idx(s: str) -> int:
            if s not in string_map:
                idx = len(string_table)
                string_map[s] = idx
                string_table.append(s)
                return idx
            return string_map[s]

        def traverse(node: LsfNode, parent_idx: int) -> int:
            idx = len(all_nodes)
            all_nodes.append(node)
            node_parents[idx] = parent_idx
            get_string_idx(node.name)
            for attr in node.attributes.values():
                get_string_idx(attr.name)
            for child in node.children:
                traverse(child, idx)
            return idx

        for root in self.root_nodes:
            traverse(root, -1)

        # 2. Serialize Strings chunk
        # Format: count (uint32) + each string prefixed with uint16 length (or null terminated)
        strings_buf = bytearray()
        strings_buf.extend(struct.pack("<I", len(string_table)))
        for s in string_table:
            encoded = s.encode("utf-8")
            strings_buf.extend(struct.pack("<H", len(encoded)))
            strings_buf.extend(encoded)

        # 3. Serialize Attributes and Values chunks
        values_buf = bytearray()
        attrs_buf = bytearray()
        all_attrs: list[tuple[int, int, int, int, int]] = []
        node_first_attr: dict[int, int] = {}

        for n_idx, node in enumerate(all_nodes):
            attr_items = list(node.attributes.values())
            if not attr_items:
                node_first_attr[n_idx] = -1
                continue
            first_idx = len(all_attrs)
            node_first_attr[n_idx] = first_idx
            for a_sub_idx, attr in enumerate(attr_items):
                attr_global_idx = first_idx + a_sub_idx
                is_last = a_sub_idx == len(attr_items) - 1
                next_idx = -1 if is_last else attr_global_idx + 1
                val_bytes = _serialize_attribute_value(attr.value, attr.type_id)
                val_offset = len(values_buf)
                val_length = len(val_bytes)
                values_buf.extend(val_bytes)
                name_idx = get_string_idx(attr.name)
                all_attrs.append((name_idx, attr.type_id, next_idx, val_offset, val_length))

        for name_idx, type_id, next_attr_idx, val_offset, val_length in all_attrs:
            attrs_buf.extend(struct.pack("<IIiII", name_idx, type_id, next_attr_idx, val_offset, val_length))

        # 4. Serialize Nodes chunk
        nodes_buf = bytearray()
        for n_idx, node in enumerate(all_nodes):
            name_idx = get_string_idx(node.name)
            p_idx = node_parents[n_idx]
            first_a = node_first_attr.get(n_idx, -1)
            # Find next sibling
            next_sib = -1
            for later_idx in range(n_idx + 1, len(all_nodes)):
                if node_parents.get(later_idx) == p_idx:
                    next_sib = later_idx
                    break
            nodes_buf.extend(struct.pack("<Iiii", name_idx, p_idx, next_sib, first_a))

        # 5. Pack chunks with optional compression
        raw_chunks = [bytes(strings_buf), bytes(nodes_buf), bytes(attrs_buf), bytes(values_buf)]
        chunk_descs: list[tuple[int, int]] = []
        final_chunks: list[bytes] = []

        for raw_c in raw_chunks:
            uncomp_sz = len(raw_c)
            if compress and uncomp_sz > 0:
                comp_c = lz4_block_compress(raw_c)
                comp_sz = len(comp_c)
                chunk_descs.append((uncomp_sz, comp_sz))
                final_chunks.append(comp_c)
            else:
                chunk_descs.append((uncomp_sz, 0))
                final_chunks.append(raw_c)

        # 6. Build Header
        # Magic (4) + Version (4) + EngineVersion (8) + 4 * (uncomp: 4, comp: 4) = 48 bytes
        # LSF v7 uses 64 bytes total header (16 bytes padding/reserved)
        header = bytearray()
        header.extend(LSF_MAGIC)
        header.extend(struct.pack("<Iq", self.version, self.engine_version))
        for uncomp_sz, comp_sz in chunk_descs:
            header.extend(struct.pack("<II", uncomp_sz, comp_sz))
        if self.version >= 7:
            # Pad to 64 bytes
            header.extend(b"\x00" * (64 - len(header)))

        for c_data in final_chunks:
            header.extend(c_data)

        return bytes(header)


def _parse_string_table(data: bytes) -> list[str]:
    """Parse strings chunk into a list of strings."""
    if len(data) < 4:
        return []
    count = struct.unpack_from("<I", data, 0)[0]
    strings: list[str] = []
    off = 4
    for _ in range(count):
        if off + 2 > len(data):
            break
        str_len = struct.unpack_from("<H", data, off)[0]
        off += 2
        if off + str_len > len(data):
            break
        s = data[off : off + str_len].decode("utf-8", errors="replace")
        strings.append(s)
        off += str_len
    return strings


def _parse_attribute_value(values_chunk: bytes, offset: int, length: int, type_id: int) -> Any:
    """Parse raw bytes from values chunk into typed Python object."""
    if offset >= len(values_chunk):
        return None
    raw = values_chunk[offset : offset + length]

    try:
        if type_id == TYPE_UINT8:
            return struct.unpack("<B", raw[:1])[0]
        elif type_id == TYPE_INT16:
            return struct.unpack("<h", raw[:2])[0]
        elif type_id == TYPE_UINT16:
            return struct.unpack("<H", raw[:2])[0]
        elif type_id == TYPE_INT32:
            return struct.unpack("<i", raw[:4])[0]
        elif type_id == TYPE_UINT32:
            return struct.unpack("<I", raw[:4])[0]
        elif type_id == TYPE_INT64:
            return struct.unpack("<q", raw[:8])[0]
        elif type_id == TYPE_UINT64:
            return struct.unpack("<Q", raw[:8])[0]
        elif type_id == TYPE_FLOAT:
            return struct.unpack("<f", raw[:4])[0]
        elif type_id == TYPE_DOUBLE:
            return struct.unpack("<d", raw[:8])[0]
        elif type_id == TYPE_BOOL:
            return raw[0] != 0 if raw else False
        elif type_id in (TYPE_STRING, TYPE_FIXED_STRING, TYPE_LS_STRING, TYPE_PATH):
            return raw.split(b"\x00")[0].decode("utf-8", errors="replace")
        elif type_id == TYPE_UUID:
            if len(raw) == 16:
                d1, d2, d3, d4, d5, d6, d7 = struct.unpack("<IHHHHHH", raw)
                return f"{d1:08x}-{d2:04x}-{d3:04x}-{d4:04x}-{d5:04x}{d6:04x}{d7:04x}"
            return raw.split(b"\x00")[0].decode("utf-8", errors="replace")
        else:
            return raw
    except Exception:
        return raw


def _serialize_attribute_value(val: Any, type_id: int) -> bytes:
    """Serialize a typed Python object into raw bytes."""
    if type_id == TYPE_UINT8:
        return struct.pack("<B", int(val))
    elif type_id == TYPE_INT16:
        return struct.pack("<h", int(val))
    elif type_id == TYPE_UINT16:
        return struct.pack("<H", int(val))
    elif type_id == TYPE_INT32:
        return struct.pack("<i", int(val))
    elif type_id == TYPE_UINT32:
        return struct.pack("<I", int(val))
    elif type_id == TYPE_INT64:
        return struct.pack("<q", int(val))
    elif type_id == TYPE_UINT64:
        return struct.pack("<Q", int(val))
    elif type_id == TYPE_FLOAT:
        return struct.pack("<f", float(val))
    elif type_id == TYPE_DOUBLE:
        return struct.pack("<d", float(val))
    elif type_id == TYPE_BOOL:
        return b"\x01" if val else b"\x00"
    elif type_id in (TYPE_STRING, TYPE_FIXED_STRING, TYPE_LS_STRING, TYPE_PATH):
        return str(val).encode("utf-8") + b"\x00"
    elif type_id == TYPE_UUID:
        uuid_str = str(val).replace("-", "")
        if len(uuid_str) == 32:
            try:
                b = bytes.fromhex(uuid_str)
                d1 = struct.unpack(">I", b[0:4])[0]
                d2 = struct.unpack(">H", b[4:6])[0]
                d3 = struct.unpack(">H", b[6:8])[0]
                d4 = struct.unpack(">H", b[8:10])[0]
                d5 = struct.unpack(">H", b[10:12])[0]
                d6 = struct.unpack(">H", b[12:14])[0]
                d7 = struct.unpack(">H", b[14:16])[0]
                return struct.pack("<IHHHHHH", d1, d2, d3, d4, d5, d6, d7)
            except ValueError:
                pass
        return str(val).encode("utf-8") + b"\x00"
    elif isinstance(val, (bytes, bytearray)):
        return bytes(val)
    return str(val).encode("utf-8")
