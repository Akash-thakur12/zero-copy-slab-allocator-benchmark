"""Memory Safety Guards & Canary Validation."""
import struct

CANARY_MAGIC = 0xDEADBEEF
POISON_BYTE = 0xAA


class MemoryCorruptionError(Exception):
    pass


class DoubleFreeError(Exception):
    pass


def pack_canary_header(size: int) -> bytes:
    return struct.pack(">II", CANARY_MAGIC, size)


def pack_canary_footer() -> bytes:
    return struct.pack(">I", CANARY_MAGIC)


def validate_block_canaries(raw_block: bytearray, requested_size: int) -> bool:
    if len(raw_block) < 8 + requested_size + 4:
        return False
    magic_hdr, size = struct.unpack_from(">II", raw_block, 0)
    magic_ftr = struct.unpack_from(">I", raw_block, 8 + requested_size)[0]
    return magic_hdr == CANARY_MAGIC and magic_ftr == CANARY_MAGIC and size == requested_size
