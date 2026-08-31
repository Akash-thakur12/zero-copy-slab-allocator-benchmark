# Zero-Copy Memory Slab Allocator & Compactor Benchmark

## Objective
Implement a high-performance, memory-safe **Zero-Copy Slab Allocator & Fragmentation Compactor** supporting multi-class power-of-two sizing, 64-byte hardware cache-line alignment, canary corruption detection (`0xDEADBEEF`), and active memory defragmentation across a **1,600-state combinatorial permutation matrix**.

---

## Technical Specifications & Memory Layout

### 1. Multi-Class Power-of-Two Slab Sizing
The allocator must maintain dedicated slab arenas for discrete object sizes:
* **Size Classes:** `[32, 64, 128, 256, 512, 1024, 2048, 4096]` bytes.
* Requests for $S$ bytes must be routed to the smallest size class $C \ge S$.
* Allocating an object size $\le 4096$ must succeed.
* Allocating an object size $> 4096$ or $\le 0$ must raise `ValueError`.

### 2. 64-Byte Cache-Line Alignment & Canary Safety Framing
Every allocated chunk must be enveloped with safety guards and aligned to a 64-byte cache boundary:
* **Canary Header (4 Bytes `uint32`):** `0xDEADBEEF`
* **Allocation Size (4 Bytes `uint32`):** Requested payload length.
* **Payload Buffer ($N$ Bytes):** Zero-copy aligned data storage.
* **Canary Footer (4 Bytes `uint32`):** `0xDEADBEEF`
* **Returned Pointer/Offset:** Must be an integer aligned to 64 bytes (`ptr % 64 == 0`).

### 3. Memory Safety Invariants & Exceptions (`engine.canary`)
The `engine.canary` module must export:
1. `MemoryCorruptionError(Exception)`: Raised when attempting to write beyond the allocated size (buffer overflow), write/read unallocated memory, or when corrupted canaries are detected.
2. `DoubleFreeError(Exception)`: Raised when calling `free()` on an already freed or invalid pointer.
3. `POISON_BYTE = 0xAA`: Upon deallocation (`free`), the slot buffer must be poisoned with `0xAA` bytes to immediately trap stale readers.

### 4. Zero-Copy Fragmentation Compactor & Telemetry
* `compact()` must coalesce partially occupied slabs and release empty slab pages back to the OS pool, returning the count of freed slab pages.
* `get_stats()` must return an exact dictionary with keys:
  * `total_allocated_bytes`: Sum of active allocated payload bytes.
  * `active_blocks`: Total currently active allocated blocks.
  * `slab_count`: Total active slab pages retained in memory.
  * `fragmentation_ratio`: Float ratio of idle slots to total capacity slots.

---

## Public API Contract

The candidate implementation must expose the following coordinator classes:

### `engine.allocator.SlabAllocator(slab_page_size: int = 65536)`
* `allocate(size: int) -> int`: Allocates a memory block and returns a 64-byte aligned opaque integer pointer/handle (`ptr % 64 == 0`). Raises `ValueError` if `size > 4096` or `size <= 0`.
* `write(block_id: int, data: bytes)`: Writes raw bytes into the allocated block with boundary enforcement. Raises `MemoryCorruptionError` on overflow.
* `read(block_id: int, size: int = None) -> bytes`: Zero-copy reads bytes from the block.
* `free(block_id: int) -> bool`: Validates canaries, poisons memory with `0xAA`, and returns the block to the free-list. Raises `DoubleFreeError` on double-free.
* `compact() -> int`: Defragments sparse slabs and returns the number of freed slab pages.
* `get_stats() -> dict`: Returns `{total_allocated_bytes, active_blocks, slab_count, fragmentation_ratio}`.

### `engine.canary`
* `MemoryCorruptionError`
* `DoubleFreeError`
* `POISON_BYTE = 0xAA`

---

## Grading, Scoring & Partial Credit

The evaluation pipeline (`tests/test_outputs.py`) executes a 4-tier evaluation suite:

| Tier | Component | Weight | Criteria |
|:---|:---|:---:|:---|
| **Tier 1** | **Canary Guards & Alignment** | `0.200` | Validates 64B alignment, canary protection, ValueError on >4096, and DoubleFreeError. |
| **Tier 2** | **Multi-Class Sizing & Telemetry** | `0.300` | Validates allocation routing across 32B to 4096B classes and get_stats() telemetry. |
| **Tier 3** | **Fragmentation Compaction** | `0.300` | Validates page coalescing, defragmentation, and OS page release under churn. |
| **Tier 4** | **1,600-State Combinatorial Matrix** | `0.200` | Stress tests 1,600 randomized permutations across 16 distinct memory access topologies. |

* **Total Score:** $\sum 	ext{Tiers} = \mathbf{1.000}$
* **Passing Threshold:** $	ext{Score} \ge \mathbf{0.500}$
