"""1,000-State Combinatorial Vector Generator for Slab Allocator."""

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
            sizes = [32, 64, 128, 256, 512, 1024, 2048]
            data = TestMatrixGenerator.get_data_variant(x, y * 10 + z)
            req_size = max(sizes[(y + z) % len(sizes)], len(data))

            # Allocate
            b1 = alloc.allocate(req_size)
            alloc.write(b1, data)

            # Read parity
            read_data = alloc.read(b1, len(data))
            if read_data != data:
                return False

            # Optional multi allocation & compaction
            if y >= 5:
                b2 = alloc.allocate(req_size)
                alloc.free(b1)
                alloc.compact()
                alloc.free(b2)
            else:
                alloc.free(b1)

            return True
        except Exception:
            return False
