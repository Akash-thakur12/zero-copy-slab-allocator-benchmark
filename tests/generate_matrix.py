"""1,000-State Combinatorial Vector Generator for Slab Allocator.
Varies allocation size classes, fragmentation topologies, and churn ordering.
"""

class TestMatrixGenerator:
    @staticmethod
    def get_data_variant(x: int, seq: int) -> bytes:
        if x == 0:
            return f"payload_{seq}".encode("ascii")
        elif x == 1:
            return bytes([(seq + i) % 256 for i in range(16)])
        elif x == 2:
            return b"\x00" * 32
        elif x == 3:
            return f"🔑_memory_{seq}_🚀".encode("utf-8")
        elif x == 4:
            return (f"large_blob_{seq}_" + "Z" * 128)[:128].encode("ascii")
        elif x == 5:
            return f"alpha_{seq}".encode("ascii")
        elif x == 6:
            return bytes([0xFF] * 64)
        elif x == 7:
            return b"A"
        elif x == 8:
            return f"asc_block_{seq:08d}".encode("ascii")
        else:
            return f"desc_block_{100000 - seq:08d}".encode("ascii")

    @staticmethod
    def run_case(allocator_cls, x: int, y: int, z: int) -> bool:
        try:
            alloc = allocator_cls()
            sizes = [32, 64, 128, 256, 512, 1024, 2048, 4096]
            data = TestMatrixGenerator.get_data_variant(x, y * 10 + z)

            # Scenario selection based on y topology
            if y == 0:
                # 1. Monotonic Single Allocation
                req_size = max(sizes[z % len(sizes)], len(data))
                ptr = alloc.allocate(req_size)
                if ptr % 64 != 0:
                    return False
                alloc.write(ptr, data)
                if alloc.read(ptr, len(data)) != data:
                    return False
                alloc.free(ptr)

            elif y == 1:
                # 2. Interleaved Dual Allocation & LIFO Deallocation
                s1 = max(sizes[z % len(sizes)], len(data))
                s2 = max(sizes[(z + 1) % len(sizes)], len(data))
                p1 = alloc.allocate(s1)
                p2 = alloc.allocate(s2)
                alloc.write(p1, data)
                alloc.write(p2, data)
                if alloc.read(p1, len(data)) != data or alloc.read(p2, len(data)) != data:
                    return False
                alloc.free(p2)
                alloc.free(p1)

            elif y == 2:
                # 3. Boundary Max-Size Allocation (4096B)
                ptr = alloc.allocate(4096)
                alloc.write(ptr, data)
                if alloc.read(ptr, len(data)) != data:
                    return False
                alloc.free(ptr)

            elif y == 3:
                # 4. Rapid Allocate-Free Reuse Cycle
                req_size = max(sizes[z % len(sizes)], len(data))
                p1 = alloc.allocate(req_size)
                alloc.write(p1, data)
                alloc.free(p1)
                p2 = alloc.allocate(req_size)
                alloc.write(p2, data)
                if alloc.read(p2, len(data)) != data:
                    return False
                alloc.free(p2)

            elif y == 4:
                # 5. Sparse Fragmentation & Active Compaction
                ptrs = [alloc.allocate(64) for _ in range(4)]
                if not all(isinstance(p, int) and p > 0 and p % 64 == 0 for p in ptrs):
                    return False
                if not alloc.free(ptrs[0]) or not alloc.free(ptrs[2]):
                    return False
                if not alloc.free(ptrs[1]) or not alloc.free(ptrs[3]):
                    return False
                if alloc.compact() < 1:
                    return False

            elif y == 5:
                # 6. Multi-Class Power-of-Two Burst
                batch = []
                for s in [32, 128, 512, 2048]:
                    p = alloc.allocate(max(s, len(data)))
                    alloc.write(p, data)
                    batch.append(p)
                for p in batch:
                    if alloc.read(p, len(data)) != data:
                        return False
                    alloc.free(p)

            elif y == 6:
                # 7. Telemetry & Stats Consistency Check
                p1 = alloc.allocate(128)
                alloc.write(p1, data)
                stats = alloc.get_stats()
                if stats["active_blocks"] != 1:
                    return False
                alloc.free(p1)

            elif y == 7:
                # 8. Boundary ValueError Validation
                try:
                    alloc.allocate(4097)
                    return False
                except ValueError:
                    pass
                p1 = alloc.allocate(32)
                alloc.free(p1)

            elif y == 8:
                # 9. Double-Free Exception Handling Check
                p1 = alloc.allocate(64)
                alloc.free(p1)
                try:
                    alloc.free(p1)
                    return False  # Must raise DoubleFreeError
                except Exception:
                    pass

            else:
                # 10. High-Churn Coalescing Cycle
                p_list = [alloc.allocate(32) for _ in range(8)]
                for p in p_list:
                    alloc.free(p)
                freed = alloc.compact()
                if freed < 1:
                    return False

            return True
        except Exception:
            return False
