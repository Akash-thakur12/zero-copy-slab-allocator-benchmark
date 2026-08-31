# Zero-Copy Memory Slab Allocator & Compactor Benchmark

## Objective
Implement a high-performance, memory-safe **Zero-Copy Slab Allocator & Fragmentation Compactor** supporting multi-class power-of-two sizing, 64-byte hardware cache-line alignment, canary corruption detection (`0xDEADBEEF`), and active memory defragmentation across a **1,000-state combinatorial permutation matrix**.

---

## Technical Specifications & Memory Layout

### 1. Multi-Class Power-of-Two Slab Sizing
The allocator must maintain dedicated slab arenas for discrete object sizes:
* **Size Classes:** `[32, 64, 128, 256, 512, 1024, 2048, 4096]` bytes.
* Requests for $S$ bytes must be routed to the smallest size class $C \ge S$.
* Objects larger than 4096 bytes must be rejected or allocated via contiguous page backing.

### 2. Cache-Line Alignment & Canary Safety Framing
Every allocated chunk must be enveloped with safety guards and aligned to a 64-byte cache boundary:
* **Canary Header (4 Bytes `uint32`):** `0xDEADBEEF`
* **Allocation Size (4 Bytes `uint32`):** Requested payload length.
* **Payload Buffer ($N$ Bytes):** Zero-copy aligned data storage.
* **Canary Footer (4 Bytes `uint32`):** `0xDEADBEEF`

### 3. Memory Safety Invariants
1. **Double-Free Detection:** Freeing an already freed memory pointer must raise an explicit exception or return an error flag.
2. **Buffer Overflow Detection:** If an out-of-bounds write overwrites either canary, `free()` or `validate()` must trap the corruption immediately.
3. **Use-After-Free Poisoning:** Upon deallocation, the payload buffer must be poisoned with pattern `0xAA` to catch stale readers.

### 4. Zero-Copy Fragmentation Compactor
* Partially occupied slabs must be coalesced when total cluster utilization drops below 50%.
* Empty slabs must be released back to the OS memory pool.

---

## Public API Contract

The candidate implementation must expose the following coordinator classes under `engine.allocator`:

### `SlabAllocator(slab_page_size: int = 65536)`
* `allocate(size: int) -> int`: Allocates a memory block and returns an opaque block ID / pointer.
* `write(block_id: int, data: bytes)`: Writes raw bytes into the allocated block with boundary enforcement.
* `read(block_id: int, size: int = None) -> bytes`: Zero-copy reads bytes from the block.
* `free(block_id: int) -> bool`: Validates canaries, poisons memory, and returns the block to the free-list.
* `compact() -> int`: Defragments sparse slabs and returns the number of freed slab pages.
* `get_stats() -> dict`: Returns `{total_allocated_bytes, active_blocks, slab_count, fragmentation_ratio}`.

---

## Grading, Scoring & Partial Credit

The evaluation pipeline (`tests/test_outputs.py`) executes a 4-tier evaluation suite:

| Tier | Component | Weight | Criteria |
|:---|:---|:---:|:---|
| **Tier 1** | **Slab Arena & Canary Guards** | `0.200` | Validates 64B alignment, canary magic checks, and double-free detection. |
| **Tier 2** | **Multi-Class Power-of-Two Sizing** | `0.300` | Validates allocation routing across 32B to 4096B classes without internal leaks. |
| **Tier 3** | **Fragmentation Compaction** | `0.300` | Validates page coalescing, defragmentation, and OS page release under churn. |
| **Tier 4** | **1,000-State Combinatorial Matrix** | `0.200` | Stress tests 1,000 randomized permutations of allocations, frees, and corruptions. |

* **Total Score:** $\sum 	ext{Tiers} = \mathbf{1.000}$
* **Passing Threshold:** $	ext{Score} \ge \mathbf{0.500}$
