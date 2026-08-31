"""Fixed-Size Slab Arena Implementation."""
from engine.canary import (
    pack_canary_header, pack_canary_footer, validate_block_canaries,
    MemoryCorruptionError, DoubleFreeError, POISON_BYTE
)


class SlabArena:
    def __init__(self, class_size: int, slab_page_size: int = 65536):
        self.class_size = class_size
        self.slot_size = ((8 + class_size + 4 + 63) // 64) * 64  # 64B cache line aligned
        self.capacity = slab_page_size // self.slot_size
        self.buffer = bytearray(self.capacity * self.slot_size)
        self.free_slots = list(range(self.capacity))
        self.allocated_slots: set[int] = set()

    def allocate(self, size: int) -> int | None:
        if not self.free_slots:
            return None
        slot_idx = self.free_slots.pop(0)
        self.allocated_slots.add(slot_idx)

        offset = slot_idx * self.slot_size
        header = pack_canary_header(size)
        footer = pack_canary_footer()

        self.buffer[offset : offset + 8] = header
        self.buffer[offset + 8 : offset + 8 + size] = b"\x00" * size
        self.buffer[offset + 8 + size : offset + 8 + size + 4] = footer
        return slot_idx

    def write(self, slot_idx: int, data: bytes):
        if slot_idx not in self.allocated_slots:
            raise MemoryCorruptionError("Attempt to write to unallocated/freed block")
        offset = slot_idx * self.slot_size
        import struct
        _, size = struct.unpack_from(">II", self.buffer, offset)
        if len(data) > size:
            raise MemoryCorruptionError(f"Buffer overflow: write size {len(data)} > allocated {size}")
        self.buffer[offset + 8 : offset + 8 + len(data)] = data

    def read(self, slot_idx: int, size: int = None) -> bytes:
        if slot_idx not in self.allocated_slots:
            raise MemoryCorruptionError("Use-after-free read detected")
        offset = slot_idx * self.slot_size
        import struct
        _, alloc_size = struct.unpack_from(">II", self.buffer, offset)
        read_len = alloc_size if size is None else min(size, alloc_size)
        return bytes(self.buffer[offset + 8 : offset + 8 + read_len])

    def free(self, slot_idx: int) -> bool:
        if slot_idx not in self.allocated_slots:
            raise DoubleFreeError(f"Double free detected on slot {slot_idx}")
        offset = slot_idx * self.slot_size
        import struct
        _, size = struct.unpack_from(">II", self.buffer, offset)
        if not validate_block_canaries(self.buffer[offset : offset + self.slot_size], size):
            raise MemoryCorruptionError(f"Canary corruption detected on slot {slot_idx}")

        # Poison slot buffer with 0xAA
        self.buffer[offset : offset + self.slot_size] = bytes([POISON_BYTE]) * self.slot_size
        self.allocated_slots.remove(slot_idx)
        self.free_slots.append(slot_idx)
        return True

    def is_empty(self) -> bool:
        return len(self.allocated_slots) == 0
