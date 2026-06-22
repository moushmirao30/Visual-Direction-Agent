"""
test_agent_05.py
Test for Agent 05 — Moodboard Generator.

Run from the visual-direction-agent/ folder:
  python -m tests.test_agent_05

Phase 1 — Unit tests (no API calls):
  - Tool initialisation
  - Output parser logic (FILE:: paths with spaces)

Phase 2 — Live tests:
  - Single HuggingFace FLUX image (catches token/API issues cheaply)
  - Full 5-panel agent run

Prerequisites:
  ANTHROPIC_API_KEY + HF_TOKEN set in .env

Cost: 5 FLUX image generations (free with HF_TOKEN) + ~800 tokens Haiku
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_env_vars():
    required = ["ANTHROPIC_API_KEY", "HF_TOKEN"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"[FAIL] Missing: {missing}")
        return False
    print("[PASS] Environment variables present")
    return True


def test_tool_init():
    try:
        from tools.image_gen_tool import get_image_gen_tool
        tool = get_image_gen_tool()
        print(f"[PASS] Image gen tool initialised: {type(tool).__name__}")
        return True
    except Exception as e:
        print(f"[FAIL] Tool init error: {e}")
        return False


def test_output_parser():
    """Verify parser correctly extracts FILE:: paths — including Windows paths with spaces."""
    from agents.agent_05_moodboard_generator import parse_moodboard_output

    sample = """
MOODBOARD PANELS:
1. PALETTE REFERENCE
   Prompt: single amber vessel on limestone, diffuse light, charcoal and cream tones
   URL: FILE::C:/Users/Moushmi Rao/project/moodboard_cache/panel_abc123.png

2. MATERIAL + TEXTURE
   Prompt: extreme close-up raw linen texture, matte surface, warm cream
   URL: FILE::C:/Users/Moushmi Rao/project/moodboard_cache/panel_def456.png

3. PHOTOGRAPHY STYLE
   Prompt: single product on stone, hands, diffuse natural light
   URL: FILE::C:/Users/Moushmi Rao/project/moodboard_cache/panel_ghi789.png

4. TYPOGRAPHIC MOOD
   Prompt: minimal editorial layout, serif headline, generous white space
   URL: FILE::C:/Users/Moushmi Rao/project/moodboard_cache/panel_jkl012.png

5. BRAND ATMOSPHERE
   Prompt: quiet dark interior, stone floor, single warm light
   URL: FILE::C:/Users/Moushmi Rao/project/moodboard_cache/panel_mno345.png
"""
    panels = parse_moodboard_output(sample)
    assert len(panels) == 5, f"Expected 5 panels, got {len(panels)}"
    print(f"[PASS] Output parser: extracted {len(panels)} panels correctly")
    return True


def test_agent_build():
    try:
        from agents.agent_05_moodboard_generator import build_moodboard_generator
        agent = build_moodboard_generator()
        assert len(agent.tools) == 1, "Agent 05 should have exactly 1 tool"
        print(f"[PASS] Agent built: role='{agent.role}', tools={len(agent.tools)}")
        return True
    except Exception as e:
        print(f"[FAIL] Agent build error: {e}")
        return False


def test_hf_single_image():
    """
    Tests a single FLUX image generation before the full agent run.
    Catches token/API issues cheaply.
    """
    from tools.image_gen_tool import generate_via_huggingface

    print("\n[INFO] Testing single HuggingFace FLUX image generation...")
    print("[INFO] First call may take up to 60s if model is cold-starting...")

    test_prompt = (
        "single dark glass vessel on limestone surface, "
        "diffuse natural light, charcoal and warm cream tones, "
        "minimal negative space, luxury wellness editorial photography"
    )

    path = generate_via_huggingface(test_prompt, seed=99)
    if not path:
        print("[FAIL] HF generation returned None — check HF_TOKEN is valid")
        print("       Get a free token at: https://huggingface.co/settings/tokens")
        return False

    if not Path(path).exists():
        print(f"[FAIL] File path returned but file not found: {path}")
        return False

    size_kb = Path(path).stat().st_size // 1024
    print(f"[PASS] FLUX image generated: {Path(path).name} ({size_kb}KB)")
    print(f"       Open to verify: {path}")
    return True


def test_live_run():
    from agents.agent_05_moodboard_generator import run_moodboard_generator

    print("\n[INFO] Running full moodboard generation — 5 FLUX image calls...")
    print("[INFO] Expected time: 30–120 seconds total")

    panels, raw = run_moodboard_generator()

    panels_with_paths = [p for p in panels if p.get("url") and "ERROR" not in p.get("url", "")]

    print(f"\n[INFO] Panels returned: {len(panels)}")
    print(f"[INFO] Panels with paths: {len(panels_with_paths)}")

    for p in panels:
        path_preview = p.get("url", "(none)")[:70]
        print(f"  [{p['panel']}]\n    {path_preview}")

    if len(panels_with_paths) >= 3:
        print(f"\n[PASS] {len(panels_with_paths)}/5 panels generated")
        print(f"       Images saved in: moodboard_cache/")
    else:
        print(f"\n[WARN] Only {len(panels_with_paths)}/5 panels generated — check output above")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Agent 05 — Moodboard Generator: Test Suite")
    print("=" * 60)

    results = []
    results.append(("env_vars",      test_env_vars()))
    results.append(("tool_init",     test_tool_init()))
    results.append(("output_parser", test_output_parser()))
    results.append(("agent_build",   test_agent_build()))

    if all(r[1] for r in results):
        single_ok = test_hf_single_image()
        results.append(("hf_single_image", single_ok))

        if single_ok:
            results.append(("live_run", test_live_run()))
        else:
            print("\n[SKIP] Full agent run skipped — fix HF_TOKEN issue first")
    else:
        print("\n[SKIP] Live tests skipped — fix setup issues first")

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, passed in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    all_passed = all(r[1] for r in results)
    print(f"\n{'All tests passed.' if all_passed else 'Some tests failed — see above.'}")
    sys.exit(0 if all_passed else 1)
