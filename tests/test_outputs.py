"""Harbor Benchmark Verification Test for Slab Allocator (Location-Independent)."""
import os
import sys
import pytest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TASK_ROOT = SCRIPT_DIR.parent

# Ensure TASK_ROOT is in sys.path
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from tests.test_grader import run_grader


def emit_reward_file(score: float):
    reward_text = f"{score:.4f}\n"
    reward_json = f'{{"score": {score:.4f}}}\n'

    candidate_paths = [
        "/logs/verifier/reward.txt",
        "/logs/verifier/reward.json",
        str(TASK_ROOT / "verifier" / "reward.txt"),
        str(TASK_ROOT / "verifier" / "reward.json"),
        str(TASK_ROOT / "reward.txt"),
        str(TASK_ROOT / "reward.json"),
        "/app/reward.txt",
        "/app/reward.json",
        os.path.join(os.getcwd(), "reward.txt"),
        os.path.join(os.getcwd(), "reward.json")
    ]

    for p in candidate_paths:
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
    target_engine = os.environ.get("TARGET_ENGINE", "")
    if not target_engine or not os.path.exists(target_engine):
        target_engine = str(TASK_ROOT / "environment" / "engine")

    target_engine_path = Path(target_engine).resolve()

    score = 0.0
    res = {}
    try:
        for mod_name in list(sys.modules.keys()):
            if mod_name == "engine" or mod_name.startswith("engine."):
                del sys.modules[mod_name]

        res = run_grader(str(target_engine_path))
        score = res.get("score", 0.0)
    finally:
        emit_reward_file(score)

    assert score >= 0.50, f"Benchmark score {score:.4f} below passing threshold 0.50 (Matrix passed: {res.get('matrix_passed', 0)}/1000)"
