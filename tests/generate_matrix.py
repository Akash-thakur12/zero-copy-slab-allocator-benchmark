"""1,600-State Combinatorial Vector Generator for Slab Allocator.
Covers 16 distinct memory allocation, fragmentation, and churn scenarios.
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

            if y == 0:
                # Scenario 0: Monotonic Single Allocation & Verification
                req_size = max(sizes[z % len(sizes)], len(data))
                ptr = alloc.allocate(req_size)
                if not isinstance(ptr, int) or ptr % 64 != 0:
                    return False
                alloc.write(ptr, data)
                if alloc.read(ptr, len(data)) != data:
                    return False
                if not alloc.free(ptr):
                    return False

            elif y == 1:
                # Scenario 1: Interleaved Dual Allocation & LIFO Deallocation
                s1 = max(sizes[z % len(sizes)], len(data))
                s2 = max(sizes[(z + 1) % len(sizes)], len(data))
                p1 = alloc.allocate(s1)
                p2 = alloc.allocate(s2)
                alloc.write(p1, data)
                alloc.write(p2, data)
                if alloc.read(p1, len(data)) != data or alloc.read(p2, len(data)) != data:
                    return False
                if not alloc.free(p2) or not alloc.free(p1):
                    return False

            elif y == 2:
                # Scenario 2: Maximum Boundary Size Class (4096B)
                ptr = alloc.allocate(4096)
                if ptr % 64 != 0:
                    return False
                alloc.write(ptr, data)
                if alloc.read(ptr, len(data)) != data:
                    return False
                if not alloc.free(ptr):
                    return False

            elif y == 3:
                # Scenario 3: Rapid Allocate-Free Reuse Cycle
                req_size = max(sizes[z % len(sizes)], len(data))
                p1 = alloc.allocate(req_size)
                alloc.write(p1, data)
                if not alloc.free(p1):
                    return False
                p2 = alloc.allocate(req_size)
                alloc.write(p2, data)
                if alloc.read(p2, len(data)) != data:
                    return False
                if not alloc.free(p2):
                    return False

            elif y == 4:
                # Scenario 4: Sparse Fragmentation & Multi-Stage Compaction
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
                # Scenario 5: Multi-Class Power-of-Two Burst
                batch = []
                for s in [32, 128, 512, 2048]:
                    p = alloc.allocate(max(s, len(data)))
                    alloc.write(p, data)
                    batch.append(p)
                for p in batch:
                    if alloc.read(p, len(data)) != data:
                        return False
                    if not alloc.free(p):
                        return False

            elif y == 6:
                # Scenario 6: Telemetry & Stats Consistency Check
                p1 = alloc.allocate(128)
                alloc.write(p1, data)
                stats = alloc.get_stats()
                if stats.get("active_blocks") != 1:
                    return False
                if not alloc.free(p1):
                    return False

            elif y == 7:
                # Scenario 7: Out-of-Bound Size Class Exception Check
                try:
                    alloc.allocate(4097)
                    return False
                except ValueError:
                    pass
                p1 = alloc.allocate(32)
                if not alloc.free(p1):
                    return False

            elif y == 8:
                # Scenario 8: Double-Free Exception Handling Check
                p1 = alloc.allocate(64)
                if not alloc.free(p1):
                    return False
                try:
                    alloc.free(p1)
                    return False
                except Exception:
                    pass

            elif y == 9:
                # Scenario 9: High-Churn Coalescing Cycle
                p_list = [alloc.allocate(32) for _ in range(8)]
                for p in p_list:
                    if not alloc.free(p):
                        return False
                freed = alloc.compact()
                if freed < 1:
                    return False

            elif y == 10:
                # Scenario 10: Ascending Slab Sweep (32 to 2048)
                sweep = []
                for s in [32, 64, 128, 256, 512, 1024, 2048]:
                    p = alloc.allocate(s)
                    alloc.write(p, b"Z" * min(s, len(data)))
                    sweep.append((p, min(s, len(data))))
                for p, sz in sweep:
                    if alloc.read(p, sz) != b"Z" * sz:
                        return False
                    if not alloc.free(p):
                        return False

            elif y == 11:
                # Scenario 11: Alternating Allocation & Compaction
                p1 = alloc.allocate(64)
                p2 = alloc.allocate(128)
                alloc.free(p1)
                alloc.compact()
                p3 = alloc.allocate(256)
                alloc.free(p2)
                alloc.free(p3)
                if alloc.compact() < 1:
                    return False

            elif y == 12:
                # Scenario 12: Overwrite Buffer Boundary Trap
                p = alloc.allocate(32)
                try:
                    alloc.write(p, b"A" * 64)
                    return False
                except Exception:
                    pass
                if not alloc.free(p):
                    return False

            elif y == 13:
                # Scenario 13: Exact Boundary 4096 Chunk Allocation
                p = alloc.allocate(4096)
                alloc.write(p, b"END" * 10)
                if alloc.read(p, 9) != b"END" * 3:
                    return False
                if not alloc.free(p):
                    return False

            elif y == 14:
                # Scenario 14: Zero-Size Exception Guard
                try:
                    alloc.allocate(0)
                    return False
                except ValueError:
                    pass
                p = alloc.allocate(32)
                if not alloc.free(p):
                    return False

            else:
                # Scenario 15: Heavy Churn Flush
                ptrs = [alloc.allocate(128) for _ in range(6)]
                for p in ptrs:
                    alloc.write(p, data[:16])
                for p in ptrs:
                    if not alloc.free(p):
                        return False
                if alloc.compact() < 1:
                    return False

            return True
        except Exception:
            return False
