"""
eval/compare_strong_fallback.py
Head-to-head test of candidate STRONG-tier NVIDIA NIM fallback models.

Why this exists:
  The strong fallback (Agents 03/04) was a dead model id (llama-3.1-405b → 404).
  Before trusting a replacement, prove it (a) resolves on YOUR NVIDIA account and
  (b) returns usable text quickly. This calls the SAME path crewai uses
  (litellm.completion against the nvidia_nim provider) — no OpenAI SDK, no fallback
  wrapper — so a pass here means the model string works as NVIDIA_FALLBACK_STRONG.

What it does NOT test:
  ReAct format-following inside a real CrewAI agent. That only shows up when the
  model drives Agents 03/04 live. A clean pass here is necessary, not sufficient.

Run from visual-direction-agent/ with the venv active:
  python -m eval.compare_strong_fallback
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

# Candidates to compare as the strong-tier fallback. Add/remove freely.
CANDIDATES = [
    "nvidia_nim/meta/llama-3.3-70b-instruct",            # current default (verified working in logs)
    "nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",      # the reasoning model you asked about
]

PROMPT = [{"role": "user", "content": "Reply with exactly one word: OK"}]
MAX_TOKENS = 64  # small: a reasoning model that burns this entirely on hidden
                 # "thinking" and returns empty content is itself a failure signal.


def main():
    # Mirror NVIDIA_API_KEY → NVIDIA_NIM_API_KEY exactly like utils/llm.py does,
    # because litellm's nvidia_nim provider reads NVIDIA_NIM_API_KEY specifically.
    nv = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
    if not nv:
        print("[STOP] No NVIDIA key in .env (NVIDIA_API_KEY=nvapi-...). Add it and re-run.")
        raise SystemExit(1)
    os.environ["NVIDIA_NIM_API_KEY"] = nv

    import litellm

    print("=" * 64)
    print("  STRONG-tier fallback comparison — via litellm (crewai's path)")
    print("=" * 64)

    results = []
    for model in CANDIDATES:
        print(f"\n→ {model}")
        t0 = time.time()
        try:
            resp = litellm.completion(model=model, messages=PROMPT, max_tokens=MAX_TOKENS)
            dt = round(time.time() - t0, 1)
            msg = resp["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            # Reasoning models sometimes return text on a separate channel and leave
            # content empty — capture that so an "empty but slow" result is visible.
            reasoning = getattr(msg, "reasoning_content", None) or (
                msg.get("reasoning_content") if isinstance(msg, dict) else None
            )
            served = resp.get("model", "?")
            ok = bool(content)
            print(f"   [{'PASS' if ok else 'EMPTY'}] {dt}s | served: {served}")
            print(f"   content : {content!r}")
            if reasoning:
                print(f"   (model also emitted {len(str(reasoning))} chars of separate "
                      f"reasoning_content — a sign it's a thinking model)")
            results.append((model, "PASS" if ok else "EMPTY (no content)", dt))
        except Exception as e:
            dt = round(time.time() - t0, 1)
            # Trim the giant litellm traceback to the first meaningful line.
            short = str(e).split("\n")[0][:160]
            print(f"   [FAIL] {dt}s | {type(e).__name__}: {short}")
            results.append((model, f"FAIL: {type(e).__name__}", dt))

    print("\n" + "=" * 64)
    print("  SUMMARY")
    print("=" * 64)
    for model, verdict, dt in results:
        print(f"  {verdict:<24} {dt:>6}s  {model}")
    print("\nGuidance: pick the fastest model that PASSES. A 404/FAIL means the id")
    print("doesn't resolve on your NVIDIA account. An EMPTY or very slow result on a")
    print("reasoning model confirms the ReAct mismatch — prefer the 70B for crewai.")


if __name__ == "__main__":
    main()
