"""Pure-Python LZ4 block/frame decompressor, Zstandard ctypes helper, and Larian LSPK v18 (.pak / .lsv) archive reader."""

import ctypes
import io
import struct
import zlib
from pathlib import Path
from typing import Any, Union

_LIBZSTD = None
for _libname in ("libzstd.so.1", "libzstd.so", "libzstd.dylib", "libzstd.dll"):
    try:
        _lib = ctypes.CDLL(_libname)
        _lib.ZSTD_decompress.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_char_p,
            ctypes.c_size_t,
        ]
        _lib.ZSTD_decompress.restype = ctypes.c_size_t
        _LIBZSTD = _lib
        break
    except Exception:
        continue

_LIBLZ4 = None
for _libname in ("liblz4.so.1", "liblz4.so", "liblz4.dylib", "liblz4.dll"):
    try:
        _lib = ctypes.CDLL(_libname)
        _lib.LZ4_compress_default.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_int,
        ]
        _lib.LZ4_compress_default.restype = ctypes.c_int
        _lib.LZ4_compressBound.argtypes = [ctypes.c_int]
        _lib.LZ4_compressBound.restype = ctypes.c_int
        _LIBLZ4 = _lib
        break
    except Exception:
        continue


def lz4_block_compress(data: bytes) -> bytes:
    """Compress data using standard LZ4 raw block format.
    
    Uses system liblz4 via ctypes if available, otherwise falls back to a valid
    pure-Python LZ4 literal block.
    """
    if _LIBLZ4 is not None and len(data) > 0:
        max_dst = _LIBLZ4.LZ4_compressBound(len(data))
        dst = ctypes.create_string_buffer(max_dst)
        comp_len = _LIBLZ4.LZ4_compress_default(data, dst, len(data), max_dst)
        if comp_len > 0:
            return dst.raw[:comp_len]

    # Pure-Python fallback: encodes a single LZ4 block containing literals without match tokens
    l = len(data)
    if l == 0:
        return b""
    token_lit = min(15, l)
    out = bytearray([token_lit << 4])
    rem = l - 15
    while rem >= 0:
        if rem >= 255:
            out.append(255)
            rem -= 255
        else:
            out.append(rem)
            break
    out.extend(data)
    return bytes(out)


def zstd_decompress(compressed_data: bytes, uncompressed_size: int) -> bytes:
    """Decompress Zstandard frame data using system libzstd via stdlib ctypes."""
    if _LIBZSTD is None or uncompressed_size <= 0:
        return compressed_data
    buf = ctypes.create_string_buffer(uncompressed_size)
    res = _LIBZSTD.ZSTD_decompress(buf, uncompressed_size, compressed_data, len(compressed_data))
    if res > uncompressed_size:
        raise ValueError(f"ZSTD_decompress error code: {res}")
    return buf.raw[:res]


def lz4_block_decompress(compressed_data: bytes, uncompressed_size: int) -> bytes:
    """Decompress standard LZ4 raw block data without external C libraries."""
    src = io.BytesIO(compressed_data)
    dst = bytearray()

    while len(dst) < uncompressed_size:
        token_b = src.read(1)
        if not token_b:
            break
        token = token_b[0]

        # 1. Literals
        literal_len = (token >> 4) & 0x0F
        if literal_len == 15:
            while True:
                extra = src.read(1)
                if not extra:
                    break
                b = extra[0]
                literal_len += b
                if b != 255:
                    break

        lit = src.read(literal_len)
        dst.extend(lit)

        if len(dst) >= uncompressed_size:
            break

        # 2. Match offset
        offset_b = src.read(2)
        if not offset_b or len(offset_b) < 2:
            break
        offset = struct.unpack("<H", offset_b)[0]
        if offset == 0:
            break

        # 3. Match length
        match_len = (token & 0x0F) + 4
        if match_len == 19:
            while True:
                extra = src.read(1)
                if not extra:
                    break
                b = extra[0]
                match_len += b
                if b != 255:
                    break

        for _ in range(match_len):
            dst.append(dst[-offset])

    return bytes(dst)


def lz4_frame_or_block_decompress(compressed_data: bytes, uncompressed_size: int) -> bytes:
    """Decompress either an LZ4 Frame (magic 04 22 4D 18) or raw LZ4 block."""
    if len(compressed_data) >= 11 and compressed_data[:4] == b"\x04\x22\x4d\x18":
        flg = compressed_data[4]
        has_content_size = bool(flg & 0x08)
        has_dict_id = bool(flg & 0x01)
        has_block_checksum = bool(flg & 0x10)
        pos = 6 + (8 if has_content_size else 0) + (4 if has_dict_id else 0) + 1
        out = bytearray()
        while pos + 4 <= len(compressed_data) and len(out) < uncompressed_size:
            blk_hdr = struct.unpack_from("<I", compressed_data, pos)[0]
            pos += 4
            if blk_hdr == 0:
                break
            is_uncompressed = bool(blk_hdr & 0x80000000)
            blk_size = blk_hdr & 0x7FFFFFFF
            blk_data = compressed_data[pos : pos + blk_size]
            pos += blk_size + (4 if has_block_checksum else 0)
            if is_uncompressed:
                out.extend(blk_data)
            else:
                remaining = uncompressed_size - len(out)
                out.extend(lz4_block_decompress(blk_data, remaining))
        return bytes(out)
    return lz4_block_decompress(compressed_data, uncompressed_size)


def decompress_pak_file_data(
    pak_bytes: bytes, offset: int, disk_size: int, uncomp_size: int, flags: int
) -> bytes:
    """Decompress file data from pak archive based on compression flags."""
    raw = pak_bytes[offset : offset + disk_size]
    method = flags & 0x0F

    if method == 0 or (disk_size == uncomp_size and raw[:4] != b"\x28\xb5\x2f\xfd"):
        return raw
    elif method == 1:
        return zlib.decompress(raw)
    elif method == 2:
        try:
            return lz4_frame_or_block_decompress(raw, uncomp_size)
        except Exception:
            if len(raw) > 4:
                try:
                    return lz4_block_decompress(raw[4:], uncomp_size)
                except Exception:
                    pass
            return raw
    elif method == 3 or raw[:4] == b"\x28\xb5\x2f\xfd":
        try:
            return zstd_decompress(raw, uncomp_size)
        except Exception:
            return raw
    return raw


class LspkArchive:
    """LSPK v18 package reader supporting both .pak mod archives and .lsv save files."""

    @classmethod
    def open(cls, path: str | Path) -> "LspkArchive":
        """Read and construct an LspkArchive from a file path."""
        return cls(Path(path).read_bytes())

    def __init__(self, data_bytes: bytes):
        self.data = data_bytes
        self.files: list[dict[str, Any]] = []
        self._parse_header_and_filelist()

    def _parse_header_and_filelist(self) -> None:
        if len(self.data) < 40 or self.data[:4] != b"LSPK":
            raise ValueError("Not a valid LSPK package (magic mismatch)")

        version, file_list_offset, file_list_size, flags, priority, md5, num_parts = struct.unpack_from(
            "<IQIBB16sH", self.data, 4
        )
        self.version = version
        self.file_list_offset = file_list_offset
        self.file_list_size = file_list_size
        self.flags = flags
        self.priority = priority
        self.md5 = md5
        self.num_parts = num_parts

        file_list_raw = self.data[file_list_offset : file_list_offset + file_list_size]
        if len(file_list_raw) < 8:
            return

        num_files, comp_size = struct.unpack_from("<II", file_list_raw, 0)
        lz4_payload = file_list_raw[8 : 8 + comp_size]
        expected_size = num_files * 272

        try:
            decomp = lz4_block_decompress(lz4_payload, expected_size)
        except Exception:
            decomp = file_list_raw[8:]

        for i in range(num_files):
            entry_bytes = decomp[i * 272 : (i + 1) * 272]
            if len(entry_bytes) < 272:
                break
            name = entry_bytes[:256].split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
            offset_low, offset_high, part, file_flags, size_disk, size_uncomp = struct.unpack_from(
                "<IHBBII", entry_bytes, 256
            )
            offset = offset_low | (offset_high << 32)
            self.files.append(
                {
                    "name": name.replace("\\", "/"),
                    "offset": offset,
                    "disk_size": size_disk,
                    "uncomp_size": size_uncomp,
                    "flags": file_flags,
                }
            )

    def extract_file(self, entry: dict) -> bytes:
        return decompress_pak_file_data(
            self.data,
            entry["offset"],
            entry["disk_size"],
            entry["uncomp_size"],
            entry["flags"],
        )
