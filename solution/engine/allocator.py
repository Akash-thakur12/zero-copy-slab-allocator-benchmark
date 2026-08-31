"""Multi-Class Zero-Copy Slab Memory Allocator."""
from engine.slab import SlabArena
from engine.canary import MemoryCorruptionError, DoubleFreeError

SIZE_CLASSES = [32, 64, 128, 256, 512, 1024, 2048, 4096]


class SlabAllocator:
    def __init__(self, slab_page_size: int = 65536):
        self.slab_page_size = slab_page_size
        self.arenas: dict[int, list[SlabArena]] = {sc: [] for sc in SIZE_CLASSES}
        self.block_registry: dict[int, tuple[SlabArena, int, int]] = {}  # ptr -> (arena, slot_idx, size)
        self.next_arena_id = 1

    def _get_size_class(self, size: int) -> int:
        if size <= 0:
            raise ValueError("Allocation size must be strictly positive")
        for sc in SIZE_CLASSES:
            if sc >= size:
                return sc
        raise ValueError(f"Size {size} exceeds maximum slab size 4096")

    def allocate(self, size: int) -> int:
        sc = self._get_size_class(size)
        arena_list = self.arenas[sc]

        target_arena = None
        target_slot_idx = None

        for arena in arena_list:
            slot = arena.allocate(size)
            if slot is not None:
                target_arena = arena
                target_slot_idx = slot
                break

        if target_slot_idx is None:
            target_arena = SlabArena(class_size=sc, arena_id=self.next_arena_id, slab_page_size=self.slab_page_size)
            self.next_arena_id += 1
            target_slot_idx = target_arena.allocate(size)
            arena_list.append(target_arena)

        # Compute 64-byte aligned pointer handle: (arena_id * 65536) + (slot_idx * slot_size)
        # Both base offset and slot_size are multiples of 64 -> ptr % 64 == 0
        ptr = (target_arena.arena_id * self.slab_page_size) + (target_slot_idx * target_arena.slot_size)
        self.block_registry[ptr] = (target_arena, target_slot_idx, size)
        return ptr

    def write(self, block_id: int, data: bytes):
        if block_id not in self.block_registry:
            raise MemoryCorruptionError(f"Invalid pointer {block_id}")
        arena, slot_idx, _ = self.block_registry[block_id]
        arena.write(slot_idx, data)

    def read(self, block_id: int, size: int = None) -> bytes:
        if block_id not in self.block_registry:
            raise MemoryCorruptionError(f"Invalid pointer {block_id}")
        arena, slot_idx, _ = self.block_registry[block_id]
        return arena.read(slot_idx, size)

    def free(self, block_id: int) -> bool:
        if block_id not in self.block_registry:
            raise DoubleFreeError(f"Attempt to free invalid/freed pointer {block_id}")
        arena, slot_idx, _ = self.block_registry[block_id]
        res = arena.free(slot_idx)
        del self.block_registry[block_id]
        return res

    def compact(self) -> int:
        freed_pages = 0
        for sc in SIZE_CLASSES:
            retained = []
            for arena in self.arenas[sc]:
                if arena.is_empty():
                    freed_pages += 1
                else:
                    retained.append(arena)
            self.arenas[sc] = retained
        return freed_pages

    def get_stats(self) -> dict:
        total_arenas = sum(len(a) for a in self.arenas.values())
        total_payload_bytes = sum(sz for _, _, sz in self.block_registry.values())
        total_capacity_slots = sum(len(a.free_slots) + len(a.allocated_slots) for arena_list in self.arenas.values() for a in arena_list)
        active_count = len(self.block_registry)
        idle_slots = total_capacity_slots - active_count
        frag_ratio = float(idle_slots / total_capacity_slots) if total_capacity_slots > 0 else 0.0

        return {
            "total_allocated_bytes": total_payload_bytes,
            "active_blocks": active_count,
            "slab_count": total_arenas,
            "fragmentation_ratio": round(frag_ratio, 4)
        }
