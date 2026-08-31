"""Harbor Benchmark Verification Test for Slab Allocator."""
import os
import sys
import pytest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from tests.test_grader import run_grader


def emit_reward_file(score: float):
    reward_text = f"{score:.4f}\n"
    reward_json = f'{{"score": {score:.4f}}}\n'

    # Primary Harbor standard path
    primary_dir = "/logs/verifier"
    try:
        os.makedirs(primary_dir, exist_ok=True)
        with open(os.path.join(primary_dir, "reward.txt"), "w", newline="\n", encoding="utf-8") as f:
            f.write(reward_text)
        with open(os.path.join(primary_dir, "reward.json"), "w", newline="\n", encoding="utf-8") as f:
            f.write(reward_json)
    except Exception as e:
        print(f"Warning writing to primary verifier dir: {e}")

    # Fallback paths (including relative verifier/ paths)
    fallbacks = [
        os.path.join(os.getcwd(), "verifier", "reward.txt"),
        os.path.join(os.getcwd(), "verifier", "reward.json"),
        str(SCRIPT_DIR.parent / "verifier" / "reward.txt"),
        str(SCRIPT_DIR.parent / "verifier" / "reward.json"),
        "/app/reward.txt",
        "/app/reward.json",
        os.path.join(os.getcwd(), "reward.txt"),
        os.path.join(os.getcwd(), "reward.json"),
        str(SCRIPT_DIR.parent / "reward.txt"),
        str(SCRIPT_DIR.parent / "reward.json")
    ]

    for p in fallbacks:
        try:
            parent = os.path.dirname(p)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(p, "w", newline="\n", encoding="utf-8") as f:
                if p.endswith(".json"):
                    f.write(reward_json)
                else:
                    f.write(reward_text)
        except Exception:
            pass


def test_slab_allocator_benchmark():
    target_engine = os.environ.get("TARGET_ENGINE", "/app/engine")
    if not os.path.exists(target_engine):
        target_engine = str(SCRIPT_DIR.parent / "environment" / "engine")

    score = 0.0
    res = {}
    try:
        for mod_name in list(sys.modules.keys()):
            if mod_name == "engine" or mod_name.startswith("engine."):
                del sys.modules[mod_name]

        res = run_grader(target_engine)
        score = res.get("score", 0.0)
    finally:
        emit_reward_file(score)

    assert score >= 0.50, f"Benchmark score {score:.4f} below passing threshold 0.50 (Matrix passed: {res.get('matrix_passed', 0)}/1000)"
