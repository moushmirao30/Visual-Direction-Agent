"""
test_agent_03.py
Isolated test for Agent 03 — Direction Synthesiser.

Run from the visual-direction-agent/ folder with venv active:
  python -m tests.test_agent_03

Uses sample inputs from agent_03 constants — does NOT require
Agents 01 or 02 to run. This keeps the test fast and cheap.

Cost: ~1500 tokens on Claude Sonnet = ~$0.005
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_env_vars():
    missing = [k for k in ["ANTHROPIC_API_KEY"] if not os.getenv(k)]
    if missing:
        print(f"[FAIL] Missing: {missing}")
        return False
    print("[PASS] Environment variables present")
    return True


def test_agent_build():
    try:
        from agents.agent_03_direction_synthesiser import build_direction_synthesiser
        agent = build_direction_synthesiser()
        assert agent.tools == [], "Agent 03 should have no tools"
        print(f"[PASS] Agent built: role='{agent.role}', tools=none (correct)")
        return True
    except Exception as e:
        print(f"[FAIL] Agent build error: {e}")
        return False


def test_live_run():
    from agents.agent_03_direction_synthesiser import run_synthesis

    print("\n[INFO] Running live synthesis test with sample inputs...")
    keyword = "quiet luxury wellness"

    try:
        output = run_synthesis(keyword)  # uses SAMPLE_* constants

        required_sections = [
            "POSITIONING STATEMENT",
            "PALETTE DIRECTION",
            "TYPOGRAPHY DIRECTION",
            "SPATIAL DIRECTION",
            "DO RULES",
            "DON'T RULES",
            "BENCHMARK BRANDS",
            "VISUAL NARRATIVE",
        ]
        missing = [s for s in required_sections if s not in output.upper()]

        if missing:
            print(f"[WARN] Output missing sections: {missing}")
        else:
            print("[PASS] Output contains all required sections")

        # Check for hex codes (signals specific palette was produced)
        import re
        hex_codes = re.findall(r'#[0-9A-Fa-f]{6}', output)
        if hex_codes:
            print(f"[PASS] Palette specificity check: found hex codes {hex_codes[:3]}")
        else:
            print("[WARN] No hex codes found — palette may be too vague")

        print("\n--- AGENT 03 OUTPUT PREVIEW (first 800 chars) ---")
        print(output[:800])
        print("...")
        return True

    except Exception as e:
        print(f"[FAIL] Live run error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Agent 03 — Direction Synthesiser: Test Suite")
    print("=" * 60)

    results = []
    results.append(("env_vars", test_env_vars()))
    results.append(("agent_build", test_agent_build()))

    if all(r[1] for r in results):
        results.append(("live_run", test_live_run()))
    else:
        print("\n[SKIP] Live test skipped — fix setup issues first")

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, passed in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    all_passed = all(r[1] for r in results)
    print(f"\n{'All tests passed.' if all_passed else 'Some tests failed — see above.'}")
    sys.exit(0 if all_passed else 1)
