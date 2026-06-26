"""
test_batch_order.py
Self-check for the concurrent generate_images_batch (image_gen_tool.py).

The optimization runs the N image calls in a thread pool instead of a loop.
The one property that must hold despite concurrency: results stay in INPUT
order with the correct deterministic seed per index (42 + i*7). If ordering
ever broke, prompts would be silently mismatched to panels.

This stubs generate_image so it returns its seed and sleeps LONGER for earlier
indices — so completion order is the reverse of input order. If pool.map didn't
re-order results back to input order, the assertions below would fail.

Run: python tests/test_batch_order.py   (no framework needed)
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.image_gen_tool as ig


def _fake_generate_image(prompt: str, seed: int = 42) -> str:
    # Earlier indices (smaller seed) sleep longer → finish last. If results
    # weren't re-ordered to input order, index 0 would land at the end.
    time.sleep((300 - seed) / 1000.0)
    return f"/tmp/img_seed_{seed}.png"


def main() -> None:
    ig.generate_image = _fake_generate_image

    prompts = [f"prompt {i}" for i in range(5)]
    results = ig.generate_images_batch(prompts)

    assert len(results) == 5, f"expected 5 results, got {len(results)}"
    for i, res in enumerate(results):
        assert res["prompt"] == prompts[i], (
            f"order broken at {i}: {res['prompt']!r} != {prompts[i]!r}"
        )
        expected_seed = 42 + i * 7
        assert res["path"] == f"/tmp/img_seed_{expected_seed}.png", (
            f"seed/index mismatch at {i}: {res['path']!r} (want seed {expected_seed})"
        )

    # Empty input must not raise (ThreadPoolExecutor(max_workers=0) would).
    assert ig.generate_images_batch([]) == [], "empty prompts should return []"

    print("OK — batch preserves input order, seeds, and handles empty input")


if __name__ == "__main__":
    main()
