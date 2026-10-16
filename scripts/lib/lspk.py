"""Pure-Python LZ4 block decompressor and Larian LSPK v18 (.pak / .lsv) archive reader."""

import io
import struct
import zlib


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


def decompress_pak_file_data(
    pak_bytes: bytes, offset: int, disk_size: int, uncomp_size: int, flags: int
) -> bytes:
    """Decompress file data from pak archive based on compression flags."""
    raw = pak_bytes[offset : offset + disk_size]
    method = flags & 0x0F

    if method == 0 or disk_size == uncomp_size:
        return raw
    elif method == 1:
        return zlib.decompress(raw)
    elif method == 2:
        try:
            return lz4_block_decompress(raw, uncomp_size)
        except Exception:
            if len(raw) > 4:
                try:
                    return lz4_block_decompress(raw[4:], uncomp_size)
                except Exception:
                    pass
            return raw
    return raw


class LspkArchive:
    """LSPK v18 package reader supporting both .pak mod archives and .lsv save files."""

    def __init__(self, data_bytes: bytes):
        self.data = data_bytes
        self.files = []
        self._parse_header_and_filelist()

    def _parse_header_and_filelist(self) -> None:
        if len(self.data) < 40 or self.data[:4] != b"LSPK":
            raise ValueError("Not a valid LSPK package (magic mismatch)")

        version, file_list_offset, file_list_size, flags, priority = struct.unpack_from(
            "<IQIBB", self.data, 4
        )

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
