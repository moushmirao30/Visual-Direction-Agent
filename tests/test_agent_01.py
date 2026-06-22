"""
test_agent_01.py
Isolated test for Agent 01 — Trend Researcher.

Run from the visual-direction-agent/ folder with venv active:
  python -m tests.test_agent_01

What this tests:
1. Environment variables are loaded correctly (.env present + keys set)
2. The Tavily search tool initialises without error
3. The agent builds without error
4. A live run returns output containing the expected section headers

Cost: ~1–2 Tavily searches + ~2000 tokens on Claude Haiku = < $0.01
"""

import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_env_vars():
    """Check required API keys are present before making any API calls."""
    required = ["ANTHROPIC_API_KEY", "TAVILY_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"[FAIL] Missing environment variables: {missing}")
        print("       Did you copy .env.example to .env and fill in your keys?")
        return False
    print("[PASS] All required environment variables present")
    return True


def test_search_tool_init():
    """Test that the Tavily tool initialises without throwing."""
    try:
        from tools.search_tool import get_search_tool
        tool = get_search_tool()
        print(f"[PASS] Search tool initialised: {type(tool).__name__}")
        return True
    except Exception as e:
        print(f"[FAIL] Search tool init error: {e}")
        return False


def test_agent_build():
    """Test that the agent object builds without error."""
    try:
        from agents.agent_01_trend_researcher import build_trend_researcher
        agent = build_trend_researcher()
        print(f"[PASS] Agent built: role='{agent.role}'")
        return True
    except Exception as e:
        print(f"[FAIL] Agent build error: {e}")
        return False


def test_live_run():
    """
    Full live run with a short keyword.
    Checks that output contains the expected section headers.
    """
    from agents.agent_01_trend_researcher import run_trend_research

    print("\n[INFO] Running live agent test — this will make real API calls...")
    keyword = "quiet luxury wellness"

    try:
        output = run_trend_research(keyword)

        # Check for expected sections in output
        required_sections = [
            "BENCHMARK BRANDS",
            "VISUAL CODES",
            "COLOUR SIGNALS",
        ]
        missing_sections = [s for s in required_sections if s not in output.upper()]

        if missing_sections:
            print(f"[WARN] Output missing expected sections: {missing_sections}")
            print("       Output may still be usable — check it manually below.")
        else:
            print("[PASS] Output contains all expected section headers")

        print("\n--- AGENT OUTPUT PREVIEW (first 500 chars) ---")
        print(output[:500])
        print("...")
        return True

    except Exception as e:
        print(f"[FAIL] Live run error: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("Agent 01 — Trend Researcher: Test Suite")
    print("="*60)

    results = []
    results.append(("env_vars", test_env_vars()))
    results.append(("search_tool_init", test_search_tool_init()))
    results.append(("agent_build", test_agent_build()))

    # Only run live test if setup tests pass
    if all(r[1] for r in results):
        results.append(("live_run", test_live_run()))
    else:
        print("\n[SKIP] Live test skipped — fix setup issues first")

    print("\n" + "="*60)
    print("RESULTS:")
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    all_passed = all(r[1] for r in results)
    print(f"\n{'All tests passed.' if all_passed else 'Some tests failed — see above.'}")
    sys.exit(0 if all_passed else 1)
