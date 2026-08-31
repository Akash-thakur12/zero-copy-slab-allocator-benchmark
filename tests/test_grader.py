"""4-Tier Deterministic Grader Pipeline for Slab Allocator Benchmark."""
import os
import sys
import ast
import json
import importlib
from pathlib import Path


def scan_anti_cheat(engine_dir: str) -> tuple[bool, str]:
    disallowed_imports = {"ctypes", "mmap", "sqlite3", "lmdb", "leveldb", "requests", "urllib3"}
    for root, _, files in os.walk(engine_dir):
        for file in files:
            if file.endswith(".py"):
                fpath = os.path.join(root, file)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=file)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name.split(".")[0] in disallowed_imports:
                                    return False, f"Prohibited library: {alias.name}"
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and node.module.split(".")[0] in disallowed_imports:
                                return False, f"Prohibited module: {node.module}"
                except Exception as e:
                    return False, f"AST parse error in {file}: {e}"
    return True, "Passed"


def eval_tier1_canary_and_alignment(SlabAllocator, MemoryCorruptionError, DoubleFreeError) -> float:
    try:
        alloc = SlabAllocator()

        # 1. 64-byte cache alignment check via public API
        ptr1 = alloc.allocate(32)
        if not isinstance(ptr1, int) or ptr1 % 64 != 0:
            return 0.0

        # 2. Maximum boundary checks: 4096 succeeds, 4097 raises ValueError
        ptr_4096 = alloc.allocate(4096)
        if not isinstance(ptr_4096, int) or ptr_4096 % 64 != 0:
            return 0.0

        try:
            alloc.allocate(4097)
            return 0.0  # Must raise ValueError
        except ValueError:
            pass
        except Exception:
            return 0.0

        # Negative / zero size raises ValueError
        try:
            alloc.allocate(0)
            return 0.0
        except ValueError:
            pass
        except Exception:
            return 0.0

        # 3. Write & read verification
        alloc.write(ptr1, b"aligned_payload")
        if alloc.read(ptr1, 15) != b"aligned_payload":
            return 0.0

        # 4. Buffer overflow detection on write
        try:
            alloc.write(ptr1, b"X" * 64)  # Exceeds allocated 32
            return 0.0  # Must raise MemoryCorruptionError
        except (MemoryCorruptionError, Exception):
            pass

        # 5. Clean free and DoubleFreeError
        alloc.free(ptr_4096)
        alloc.free(ptr1)
        try:
            alloc.free(ptr1)
            return 0.0  # Must raise DoubleFreeError
        except (DoubleFreeError, Exception):
            pass

        return 0.200
    except Exception:
        return 0.0


def eval_tier2_multiclass_sizing_and_stats(SlabAllocator) -> float:
    try:
        alloc = SlabAllocator()
        blocks = []
        classes = [32, 64, 128, 256, 512, 1024, 2048, 4096]

        for s in classes:
            ptr = alloc.allocate(s)
            if not isinstance(ptr, int) or ptr % 64 != 0:
                return 0.0
            alloc.write(ptr, b"K" * min(s, 16))
            blocks.append((ptr, min(s, 16)))

        # Read parity across all classes
        for ptr, sz in blocks:
            if alloc.read(ptr, sz) != b"K" * sz:
                return 0.0

        # Telemetry validation via public get_stats()
        stats = alloc.get_stats()
        required_keys = {"total_allocated_bytes", "active_blocks", "slab_count", "fragmentation_ratio"}
        if not required_keys.issubset(stats.keys()):
            return 0.0

        if stats["active_blocks"] != len(classes):
            return 0.0
        if stats["total_allocated_bytes"] != sum(classes):
            return 0.0
        if stats["slab_count"] < 1:
            return 0.0

        for ptr, _ in blocks:
            alloc.free(ptr)

        return 0.300
    except Exception:
        return 0.0


def eval_tier3_compaction(SlabAllocator) -> float:
    try:
        alloc = SlabAllocator()
        b1 = alloc.allocate(64)
        b2 = alloc.allocate(64)
        alloc.free(b1)
        alloc.free(b2)

        # Verify compaction frees idle slab pages
        freed_pages = alloc.compact()
        if freed_pages >= 1:
            stats = alloc.get_stats()
            if stats["slab_count"] == 0 and stats["active_blocks"] == 0:
                return 0.300
        return 0.0
    except Exception:
        return 0.0


def eval_tier4_matrix_stress(SlabAllocator) -> tuple[float, int]:
    try:
        from tests.generate_matrix import TestMatrixGenerator
    except ImportError:
        from generate_matrix import TestMatrixGenerator

    passed = 0
    for x in range(10):
        for y in range(10):
            for z in range(10):
                if TestMatrixGenerator.run_case(SlabAllocator, x, y, z):
                    passed += 1
    score = (passed / 1000.0) * 0.200
    return score, passed


def run_grader(engine_dir: str) -> dict:
    is_clean, msg = scan_anti_cheat(engine_dir)
    if not is_clean:
        return {"tier1_canary": 0.0, "tier2_multiclass": 0.0, "tier3_compaction": 0.0, "tier4_matrix": 0.0, "matrix_passed": 0, "matrix_total": 1000, "score": 0.0, "error": msg}

    for mod_name in list(sys.modules.keys()):
        if mod_name == "engine" or mod_name.startswith("engine."):
            del sys.modules[mod_name]

    parent_dir = str(Path(engine_dir).parent)
    if parent_dir in sys.path:
        sys.path.remove(parent_dir)
    sys.path.insert(0, parent_dir)

    try:
        alloc_mod = importlib.import_module("engine.allocator")
        canary_mod = importlib.import_module("engine.canary")
        SlabAllocator = getattr(alloc_mod, "SlabAllocator")
        MemoryCorruptionError = getattr(canary_mod, "MemoryCorruptionError")
        DoubleFreeError = getattr(canary_mod, "DoubleFreeError")
    except Exception as e:
        return {"tier1_canary": 0.0, "tier2_multiclass": 0.0, "tier3_compaction": 0.0, "tier4_matrix": 0.0, "matrix_passed": 0, "matrix_total": 1000, "score": 0.0, "error": str(e)}

    print("=== EXECUTING 4-TIER SLAB ALLOCATOR GRADER PIPELINE ===")
    t1 = eval_tier1_canary_and_alignment(SlabAllocator, MemoryCorruptionError, DoubleFreeError)
    print(f"  [TIER 1] Canary Guards & 64B Alignment : {t1:.3f} / 0.200")

    t2 = eval_tier2_multiclass_sizing_and_stats(SlabAllocator)
    print(f"  [TIER 2] Multi-Class Sizing & Telemetry: {t2:.3f} / 0.300")

    t3 = eval_tier3_compaction(SlabAllocator)
    print(f"  [TIER 3] Fragmentation Compaction      : {t3:.3f} / 0.300")

    t4, m_passed = eval_tier4_matrix_stress(SlabAllocator)
    print(f"  [TIER 4] 1,000-State Matrix Stress     : {t4:.3f} / 0.200 ({m_passed}/1000 passed)")

    total_score = t1 + t2 + t3 + t4
    return {
        "tier1_canary": round(t1, 3),
        "tier2_multiclass": round(t2, 3),
        "tier3_compaction": round(t3, 3),
        "tier4_matrix": round(t4, 3),
        "matrix_passed": m_passed,
        "matrix_total": 1000,
        "score": round(total_score, 4)
    }


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "/app/engine"
    res = run_grader(target)
    print("\n" + json.dumps(res, indent=2))
    print(f"\n[REWARD] FINAL COMPOSITE SCORE: {res['score']:.4f}")


if __name__ == "__main__":
    main()
