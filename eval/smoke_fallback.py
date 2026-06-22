"""
eval/smoke_fallback.py
Proves the NVIDIA NIM fallback actually FIRES when Anthropic fails.

Why a dedicated test:
  build_llm() is wired and unit-tested for *shape* (it returns an LLM with a
  fallbacks=[...] kwarg). But "the kwarg is present" is not "failover actually
  works end to end". This forces the real failure and checks NVIDIA served the
  request — the only proof that counts.

How it works (non-destructive):
  1. Confirms a real NVIDIA key is present.
  2. Sabotages ANTHROPIC_API_KEY *for this process only* (your .env file is never
     touched) so the PRIMARY Anthropic call is guaranteed to fail.
  3. Makes a tiny completion through the exact model+fallback config build_llm uses.
  4. Reads back which model actually answered. If it's a Llama/NVIDIA model, the
     fallback works.

Requires: a real NVIDIA key in .env  (NVIDIA_API_KEY=nvapi-...  or NVIDIA_NIM_API_KEY)

Run from visual-direction-agent/ with venv active:
  python -m eval.smoke_fallback
  python -m eval.smoke_fallback --tier strong   # test the sonnet-tier fallback model
"""

import os
import argparse
from dotenv import load_dotenv

load_dotenv()


def main():
    ap = argparse.ArgumentParser(description="Prove the NVIDIA NIM fallback fires")
    ap.add_argument("--tier", choices=["fast", "strong"], default="fast",
                    help="which fallback model to test (fast=llama-3.3-70b, strong=llama-3.1-405b)")
    args = ap.parse_args()

    # 1) Need a real NVIDIA key. Accept either name; mirror into NVIDIA_NIM_API_KEY
    #    (what litellm's nvidia_nim provider reads) — same logic as utils/llm.py.
    nv_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
    if not nv_key:
        print("[STOP] No NVIDIA key found. Add NVIDIA_API_KEY=nvapi-... to .env, then re-run.")
        raise SystemExit(1)
    os.environ["NVIDIA_NIM_API_KEY"] = nv_key

    # 2) Sabotage the PRIMARY provider — process-only, your .env file is untouched.
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-INVALID-deliberately-broken-to-force-fallback"

    # 3) Sanity-check the integration object build_llm produces with a key present.
    from utils.llm import build_llm
    llm_obj = build_llm("anthropic/claude-haiku-4-5-20251001", tier=args.tier)
    fb = getattr(llm_obj, "kwargs", {}).get("fallbacks") if not isinstance(llm_obj, str) else None
    if isinstance(llm_obj, str) or not fb:
        print(f"[FAIL] build_llm returned no fallback (got {type(llm_obj).__name__}).")
        print("  Likely causes, in order:")
        print("   1. Not in the venv. Run .\\venv\\Scripts\\Activate.ps1 and check:")
        print("      python -c \"import sys; print(sys.executable)\"  (must end venv\\Scripts\\python.exe)")
        print("   2. No NVIDIA key visible to this process (NVIDIA_API_KEY in .env).")
        print("   (build_llm degrades to Anthropic-only on construction failure — see its [WARN] above.)")
        raise SystemExit(1)
    primary = "anthropic/claude-haiku-4-5-20251001"
    fallback = fb[0]
    print(f"Primary (sabotaged): {primary}")
    print(f"Fallback           : {fallback}")
    print("Calling with a broken Anthropic key — if this returns text, failover fired.\n")

    # 4) Live call through the SAME path crewai uses (LLM.call -> litellm.completion).
    import litellm
    msgs = [{"role": "user", "content": "Reply with exactly one word: OK"}]
    try:
        resp = litellm.completion(model=primary, messages=msgs,
                                  fallbacks=[fallback], max_tokens=10)
    except Exception as e:
        print(f"[FAIL] Even the fallback errored: {type(e).__name__}: {e}")
        print("  Check: NVIDIA key valid? fallback model id correct? network up?")
        raise SystemExit(1)

    served = (resp.get("model") if isinstance(resp, dict) else None) or getattr(resp, "model", "?")
    content = resp["choices"][0]["message"]["content"].strip()

    print(f"[OK] Completion succeeded despite the broken Anthropic key.")
    print(f"     Served by : {served}")
    print(f"     Reply     : {content!r}")

    looks_nvidia = any(t in str(served).lower() for t in ("llama", "nvidia", "nim", "nemotron", "qwen"))
    print("\n" + "=" * 56)
    if looks_nvidia:
        print("  RESULT: FALLBACK WORKS ✓  — NVIDIA served the request.")
    else:
        print(f"  RESULT: request completed, but served model '{served}'")
        print("          doesn't obviously look like NVIDIA — eyeball it.")
    print("=" * 56)


if __name__ == "__main__":
    main()
