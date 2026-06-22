"""
eval/verify_free_primary.py
Proves FREE_PRIMARY mode actually works END TO END — that a free provider can both
answer a request AND hold Agent 04's JSON schema. This is the test smoke_fallback.py
does NOT do.

Why a separate test:
  smoke_fallback.py proves the OLD path (Anthropic primary -> NVIDIA fallback) fires,
  and it only checks a one-word "OK" reply. Neither fact tells you the thing that
  actually breaks a no-credit demo:
    1. Does the free provider complete a real call with YOUR key?  (catches a missing
       or rate-limited GROQ_API_KEY — constructing an LLM object does not.)
    2. Can the free 70B return SCHEMA-VALID Agent 04 JSON, through the retry guardrail?
       (A model that says "OK" can still fail nested-field JSON extraction.)
  This script forces both, per provider, and fails loud if either misses.

How it works:
  utils/llm.py reads FREE_PRIMARY ONCE at import. To test "nvidia" and "groq" cleanly
  in one command we run each in its OWN subprocess with FREE_PRIMARY set in the child
  env — which is also exactly how you run the real pipeline (FREE_PRIMARY in .env).
  A provider with no key is SKIPPED (not failed): you may have NVIDIA set but not Groq.

  Per provider:
    Check A — liveness: call litellm directly on the primary free model (one token).
    Check B — schema:   run the real Agent 04 (run_report_writer) on the sample brief
                        and assert it returns a validated VisualDirectionReport.

Run from visual-direction-agent/ with venv active:
  python -m eval.verify_free_primary                 # tests nvidia + groq
  python -m eval.verify_free_primary --provider groq # one provider only
  python -m eval.verify_free_primary --skip-agent    # liveness only, no LLM-heavy run

Exit code: 0 if every tested provider passed (skips are OK), 1 if any failed.
"""

import os
import sys
import argparse
import subprocess

# Per-provider key requirement + the model build_llm will pick for the strong tier.
# Mirrors utils/llm.py defaults; both default to a 70B so the schema has enough model.
_PROVIDERS = {
    "nvidia": {
        "key_names": ("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"),
        "default_model": "nvidia_nim/meta/llama-3.3-70b-instruct",
    },
    "groq": {
        "key_names": ("GROQ_API_KEY",),
        "default_model": "groq/llama-3.3-70b-versatile",
    },
}

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


def _has_key(provider: str) -> bool:
    return any(os.getenv(n) for n in _PROVIDERS[provider]["key_names"])


def _primary_model(llm_obj) -> str | None:
    """build_llm returns either a plain string or a crewai LLM with a .model attr."""
    if isinstance(llm_obj, str):
        return llm_obj
    return getattr(llm_obj, "model", None)


def _check_liveness(provider: str) -> tuple[str, str]:
    """
    Check A: the primary free model actually answers with the configured key.
    Calls litellm directly on the primary model only (no fallback) so a green result
    means THIS provider — not a fallback — served the request.
    """
    from utils.llm import build_llm  # first import here -> captures FREE_PRIMARY from env
    import litellm

    # Ask for the same thing an agent would: build_llm in FREE_PRIMARY mode ignores the
    # Anthropic arg and routes to the free model.
    llm_obj = build_llm("anthropic/claude-sonnet-4-6", tier="strong")
    model = _primary_model(llm_obj)
    expected_prefix = "nvidia_nim/" if provider == "nvidia" else "groq/"
    if not model or not model.startswith(expected_prefix):
        # Defensive: the routed model isn't this provider's — config drift.
        return FAIL, f"build_llm routed to '{model}', not a {provider} model. Check FREE_PRIMARY/env."

    try:
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly one word: OK"}],
            max_tokens=8,
        )
    except Exception as e:
        name = type(e).__name__
        hint = ""
        if "auth" in name.lower() or "401" in str(e):
            hint = f"  -> key for {provider} missing/invalid in .env."
        elif "ratelimit" in name.lower() or "429" in str(e):
            hint = f"  -> {provider} free-tier rate limit hit. Wait and re-run."
        return FAIL, f"liveness call errored: {name}: {str(e)[:160]}{hint}"

    served = (resp.get("model") if isinstance(resp, dict) else None) or getattr(resp, "model", "?")
    reply = resp["choices"][0]["message"]["content"].strip()
    return PASS, f"served by {served!r}, reply {reply!r}"


def _check_schema(provider: str) -> tuple[str, str]:
    """
    Check B: the real Agent 04 returns a schema-valid report on the free model.
    Uses the agent's own sample Agent-03 brief + its retry guardrail — the exact path
    that runs in the demo. If the free model cannot hold the schema even with retries,
    report is None and this fails.
    """
    from agents.agent_04_report_writer import run_report_writer, SAMPLE_SYNTHESIS

    report, _formatted, error = run_report_writer("quiet luxury wellness", SAMPLE_SYNTHESIS)
    if error or report is None:
        return FAIL, f"Agent 04 did NOT produce schema-valid output. {error or 'report was None'}"

    # Spot-check a few guardrail-critical fields so a 'pass' is meaningful, not just non-None.
    facts = (
        f"{len(report.palette)} swatches, {len(report.do_rules)} do / "
        f"{len(report.dont_rules)} don't, {len(report.benchmark_brands)} brands, "
        f"narrative {len(report.visual_narrative.split())} words"
    )
    return PASS, f"schema valid ({facts})"


def _run_one(provider: str, skip_agent: bool) -> int:
    """Run all checks for ONE provider in this (clean) process. Returns exit code."""
    from dotenv import load_dotenv
    load_dotenv()                          # provides the provider keys from .env
    os.environ["FREE_PRIMARY"] = provider  # override .env's value for this run

    print(f"\n{'='*60}\n  VERIFY FREE_PRIMARY = {provider}\n{'='*60}")

    if not _has_key(provider):
        names = " or ".join(_PROVIDERS[provider]["key_names"])
        print(f"[{SKIP}] No key found ({names} not in .env). Skipping {provider}.")
        return 0  # a skip is not a failure

    status, detail = _check_liveness(provider)
    print(f"[{status}] liveness — {detail}")
    if status == FAIL:
        return 1

    if skip_agent:
        print(f"[{SKIP}] schema check skipped (--skip-agent).")
        return 0

    print(f"[..] running Agent 04 on '{provider}' (real call, may take ~10-40s)...")
    status, detail = _check_schema(provider)
    print(f"[{status}] Agent 04 schema — {detail}")
    return 0 if status == PASS else 1


def main():
    ap = argparse.ArgumentParser(description="Verify FREE_PRIMARY mode end to end.")
    ap.add_argument("--provider", choices=["nvidia", "groq", "both"], default="both",
                    help="which free provider to verify (default: both)")
    ap.add_argument("--skip-agent", action="store_true",
                    help="liveness only — skip the LLM-heavy Agent 04 schema run")
    # internal: marks a single-provider child process so we never recurse.
    ap.add_argument("--_child", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.provider != "both" or args._child:
        raise SystemExit(_run_one(args.provider, args.skip_agent))

    # 'both' -> one clean subprocess per provider (each re-imports utils.llm fresh).
    results: dict[str, int] = {}
    for prov in ("nvidia", "groq"):
        cmd = [sys.executable, "-m", "eval.verify_free_primary",
               "--provider", prov, "--_child"]
        if args.skip_agent:
            cmd.append("--skip-agent")
        results[prov] = subprocess.run(cmd).returncode

    print(f"\n{'='*60}\n  SUMMARY\n{'='*60}")
    for prov, code in results.items():
        print(f"  {prov:8s}: {'PASS / SKIP' if code == 0 else 'FAIL'}")
    overall = 0 if all(c == 0 for c in results.values()) else 1
    print(f"\n  OVERALL: {'OK' if overall == 0 else 'FAILURES PRESENT'}")
    raise SystemExit(overall)


if __name__ == "__main__":
    main()
