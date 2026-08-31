# Zero-Copy Memory Slab Allocator & Compactor Benchmark

## Objective
Implement a high-performance, memory-safe **Zero-Copy Slab Allocator & Fragmentation Compactor** supporting multi-class power-of-two sizing, 64-byte hardware cache-line alignment, canary corruption detection (`0xDEADBEEF`), and active memory defragmentation across a **1,000-state combinatorial permutation matrix**.

---

## Technical Specifications & Memory Layout

### 1. Multi-Class Power-of-Two Slab Sizing
The allocator must maintain dedicated slab arenas for discrete object sizes:
* **Size Classes:** `[32, 64, 128, 256, 512, 1024, 2048, 4096]` bytes.
* Requests for $S$ bytes must be routed to the smallest size class $C \ge S$.
* Objects larger than 4096 bytes must raise `ValueError`.

### 2. Cache-Line Alignment & Canary Safety Framing
Every allocated chunk must be enveloped with safety guards and aligned to a 64-byte cache boundary:
* **Canary Header (4 Bytes `uint32`):** `0xDEADBEEF`
* **Allocation Size (4 Bytes `uint32`):** Requested payload length.
* **Payload Buffer ($N$ Bytes):** Zero-copy aligned data storage.
* **Canary Footer (4 Bytes `uint32`):** `0xDEADBEEF`

### 3. Memory Safety Invariants & Exceptions (`engine.canary`)
The `engine.canary` module must define and export:
1. `MemoryCorruptionError(Exception)`: Raised when a buffer overflow or corrupted canary header/footer is detected during read, write, or free.
2. `DoubleFreeError(Exception)`: Raised when deallocating an already freed or unallocated block pointer.
3. `POISON_BYTE = 0xAA`: Upon deallocation (`free`), the entire slot buffer must be poisoned with `0xAA` bytes to immediately trap stale readers.

### 4. Zero-Copy Fragmentation Compactor & Telemetry
* Partially occupied slabs must be coalesced and empty slabs released back to the pool.
* `get_stats()` must return an exact dictionary with keys:
  * `total_allocated_bytes`: Total active payload bytes.
  * `active_blocks`: Total currently allocated blocks.
  * `slab_count`: Total active slab pages retained in memory.
  * `fragmentation_ratio`: Float ratio of idle slots to total slots.

---

## Public API Contract

The candidate implementation must expose the following coordinator classes:

### `engine.allocator.SlabAllocator(slab_page_size: int = 65536)`
* `allocate(size: int) -> int`: Allocates a memory block and returns an opaque block ID.
* `write(block_id: int, data: bytes)`: Writes raw bytes into the allocated block with boundary enforcement.
* `read(block_id: int, size: int = None) -> bytes`: Zero-copy reads bytes from the block.
* `free(block_id: int) -> bool`: Validates canaries, poisons memory with `0xAA`, and returns the block to the free-list.
* `compact() -> int`: Defragments sparse slabs and returns the number of freed slab pages.
* `get_stats() -> dict`: Returns `{total_allocated_bytes, active_blocks, slab_count, fragmentation_ratio}`.

### `engine.canary`
* `MemoryCorruptionError`
* `DoubleFreeError`
* `POISON_BYTE = 0xAA`
* `validate_block_canaries(raw_block: bytearray, requested_size: int) -> bool`

---

## Grading, Scoring & Partial Credit

The evaluation pipeline (`tests/test_outputs.py`) executes a 4-tier evaluation suite:

| Tier | Component | Weight | Criteria |
|:---|:---|:---:|:---|
| **Tier 1** | **Canary Guards & Safety Traps** | `0.200` | Validates 64B alignment, canary corruption traps, 0xAA poisoning, and DoubleFreeError. |
| **Tier 2** | **Multi-Class Sizing & Telemetry** | `0.300` | Validates allocation routing across 32B to 4096B classes and get_stats() schema accuracy. |
| **Tier 3** | **Fragmentation Compaction** | `0.300` | Validates page coalescing, defragmentation, and OS page release under churn. |
| **Tier 4** | **1,000-State Combinatorial Matrix** | `0.200` | Stress tests 1,000 randomized permutations of allocations, frees, and corruptions. |

* **Total Score:** $\sum 	ext{Tiers} = \mathbf{1.000}$
* **Passing Threshold:** $	ext{Score} \ge \mathbf{0.500}$
