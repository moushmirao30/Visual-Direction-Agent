"""
test_agent_02.py
Isolated test for Agent 02 — Design Theory Analyst.

Run from the visual-direction-agent/ folder with venv active:
  python -m tests.test_agent_02

Prerequisites:
  - python -m rag.ingest must have been run first
  - ANTHROPIC_API_KEY must be set in .env

Cost: ~4 RAG queries (free, local) + ~3000 tokens on Claude Haiku = ~$0.002
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


def test_chromadb_populated():
    """Verify ChromaDB exists and has chunks before running the agent."""
    try:
        from rag.retriever import get_retriever
        retriever = get_retriever()
        count = retriever.collection.count()
        if count == 0:
            print("[FAIL] ChromaDB is empty. Run: python -m rag.ingest")
            return False
        print(f"[PASS] ChromaDB populated: {count} chunks")
        return True
    except FileNotFoundError as e:
        print(f"[FAIL] {e}")
        return False


def test_rag_tool_init():
    try:
        from tools.rag_tool import get_rag_tool
        tool = get_rag_tool()
        print(f"[PASS] RAG tool initialised: {type(tool).__name__}")
        return True
    except Exception as e:
        print(f"[FAIL] RAG tool init error: {e}")
        return False


def test_agent_build():
    try:
        from agents.agent_02_design_theory_analyst import build_design_theory_analyst
        agent = build_design_theory_analyst()
        print(f"[PASS] Agent built: role='{agent.role}'")
        return True
    except Exception as e:
        print(f"[FAIL] Agent build error: {e}")
        return False


def test_live_run():
    from agents.agent_02_design_theory_analyst import run_theory_analysis

    print("\n[INFO] Running live agent test — makes real API calls...")
    keyword = "quiet luxury wellness"

    try:
        output = run_theory_analysis(keyword)

        required_sections = ["COLOUR", "TYPOGRAPHY", "SPATIAL", "POSITIONING"]
        missing = [s for s in required_sections if s not in output.upper()]

        if missing:
            print(f"[WARN] Output missing sections: {missing}")
        else:
            print("[PASS] Output contains all four required sections")

        print("\n--- AGENT 02 OUTPUT PREVIEW (first 600 chars) ---")
        print(output[:600])
        print("...")
        return True

    except Exception as e:
        print(f"[FAIL] Live run error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Agent 02 — Design Theory Analyst: Test Suite")
    print("=" * 60)

    results = []
    results.append(("env_vars", test_env_vars()))
    results.append(("chromadb_populated", test_chromadb_populated()))
    results.append(("rag_tool_init", test_rag_tool_init()))
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
