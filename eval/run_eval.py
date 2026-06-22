"""
eval/run_eval.py
The runner. Ties the pieces together into one reproducible command.

What it does, in order:
  1. Held-out AURU benchmark (the headline result):
       - removes auru_brand_research.txt from retrieval (EVAL_EXCLUDE_SOURCES)
       - runs the pipeline on "quiet luxury wellness" (text only, no moodboard)
       - judges convergence against the AURU ground truth
     This is the de-leaked proof: did the agent re-derive AURU WITHOUT the answer.
  2. Rubric sweep:
       - runs the pipeline on each eval keyword (text only)
       - scores each report against the 5-dimension rubric with an LLM-as-judge
  3. Captures latency (per-agent, from crew.py timings) and best-effort token/USD
     cost (LiteLLM callback) for every run.
  4. Writes a machine-readable JSON and a human-readable Markdown summary to
     eval/results/.

Why text-only (skip_moodboard=True):
  We are evaluating the REASONING — positioning, palette, type, benchmarks. Image
  generation is slow, costs the most, and is judged by eye, not by this harness.
  Skipping it makes the sweep affordable and fast enough to run before a demo.

Why --no-cache is forced:
  A cached run returns a frozen prior answer and would measure the cache, not the
  system. Every eval run is fresh.

Run from the visual-direction-agent/ folder with venv active:
  python -m eval.run_eval                 # full sweep + held-out benchmark
  python -m eval.run_eval --benchmark-only
  python -m eval.run_eval --limit 3       # first 3 keywords only (quick smoke)
  python -m eval.run_eval --no-benchmark  # rubric sweep only
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from eval.eval_dataset import (
    KEYWORDS, HELD_OUT_KEYWORD, HELD_OUT_EXCLUDE_SOURCE, AURU_GROUND_TRUTH,
)
from eval.rubric import DIMENSIONS
from eval.judge import judge_report, judge_auru_convergence, DEFAULT_JUDGE_MODEL
from eval.cost_tracker import CostTracker

RESULTS_DIR = Path(__file__).resolve().parent / "results"


# ── Preflight: fail in 1 second, not 13 tracebacks ─────────────────────────────

def _preflight() -> None:
    """
    Confirms the runtime dependencies the pipeline needs are importable BEFORE we
    start a 40-minute sweep. The classic failure is running with the venv not
    activated: every package is installed, but the wrong interpreter can't see it,
    so all 13 cases fail identically with 'No module named tavily'. This catches
    that in one second with a plain instruction instead of 13 stack traces.
    """
    required = ["tavily", "crewai", "chromadb", "litellm"]
    missing = []
    for mod in required:
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)

    if missing:
        print("\n" + "!" * 64)
        print("  PREFLIGHT FAILED — required packages not importable:")
        print(f"    missing: {', '.join(missing)}")
        print(f"    python:  {sys.executable}")
        venv_ok = "visual-direction-agent" in sys.executable and "venv" in sys.executable
        if not venv_ok:
            print("\n  This is almost certainly the venv not being active. Fix:")
            print('    cd "C:\\Users\\Moushmi Rao\\Claude\\Projects\\Capstone Project - Gen AI\\visual-direction-agent"')
            print("    .\\venv\\Scripts\\Activate.ps1")
            print("  Then confirm the interpreter:")
            print('    python -c "import sys; print(sys.executable)"   # must end in venv\\Scripts\\python.exe')
        else:
            print("\n  venv looks active but packages are missing. Reinstall:")
            print("    pip install -r requirements.txt")
        print("!" * 64 + "\n")
        sys.exit(1)


# ── Single pipeline run with instrumentation ───────────────────────────────────

# Markers of a TRANSIENT failure — a dropped connection, DNS hiccup, provider
# overload, or rate limit — as opposed to a real bug in the report logic. A single
# network blip should not waste a 40-minute sweep, so these are retried with
# backoff. A schema/validation error is NOT here: that is a real failure we want to
# see, not paper over.
_TRANSIENT_MARKERS = (
    "getaddrinfo",          # DNS resolution failed (the 12-case wipeout we just saw)
    "internalservererror",  # provider 500
    "overloaded",           # Anthropic 529
    "rate limit", "ratelimit", "429",
    "timeout", "timed out",
    "connection", "econnreset", "remote end closed",
    "service unavailable", "503", "bad gateway", "502",
)
# Markers of a FATAL failure — billing, auth, or a dead/unknown model. These NEVER
# succeed on retry, so retrying just triples wasted time and Tavily/API calls. They
# take precedence over _TRANSIENT_MARKERS because the exception TYPE can be
# misleading: an out-of-credit Anthropic 400 surfaces through crewai as
# APIConnectionError (whose name contains "connection"), which would otherwise be
# wrongly treated as a transient network blip and retried.
_FATAL_MARKERS = (
    "credit balance",        # Anthropic out of credits
    "invalid_request_error", # Anthropic 400 (billing, bad request)
    "invalid x-api-key", "authentication", "401", "permission",
    "404", "not found",      # dead/unknown fallback model id (e.g. retired NIM model)
)
_MAX_PIPELINE_ATTEMPTS = 3
_BACKOFF_SECONDS = (5, 15)  # waits before retry 2 and retry 3


def _is_transient(err: Exception) -> bool:
    blob = f"{type(err).__name__} {err}".lower()
    if any(m in blob for m in _FATAL_MARKERS):
        return False  # fail fast — retrying a billing/auth/dead-model error is futile
    return any(m in blob for m in _TRANSIENT_MARKERS)


def _run_pipeline(keyword: str, exclude_source: str | None) -> dict:
    """
    Runs the pipeline once (text only, no cache) with cost + latency capture.
    exclude_source: if set, that KB document is removed from retrieval for this run.

    Transient failures (network drop, DNS, provider overload, rate limit) are
    retried up to _MAX_PIPELINE_ATTEMPTS times with backoff. Non-transient failures
    (e.g. schema validation) fail fast — those are real signal, not noise.

    Returns {"report": dict|None, "timings": dict, "cost": dict, "error": str|None,
             "attempts": int}.
    """
    # Set/clear the de-leak lever BEFORE importing/calling the pipeline.
    if exclude_source:
        os.environ["EVAL_EXCLUDE_SOURCES"] = exclude_source
    else:
        os.environ.pop("EVAL_EXCLUDE_SOURCES", None)

    tracker = CostTracker()

    try:
        last_err = None
        for attempt in range(1, _MAX_PIPELINE_ATTEMPTS + 1):
            tracker.reset()        # fresh cost count per attempt (a failed attempt ~$0)
            tracker.register()
            try:
                from crew import run_visual_direction_pipeline
                result = run_visual_direction_pipeline(
                    keyword, use_cache=False, skip_moodboard=True,
                )
                report_dict = result["report"].model_dump()
                return {
                    "report": report_dict,
                    "timings": result.get("timings", {}),
                    "cost": tracker.snapshot(),
                    "error": None,
                    "attempts": attempt,
                }
            except Exception as e:
                last_err = e
                tracker.unregister()
                if _is_transient(e) and attempt < _MAX_PIPELINE_ATTEMPTS:
                    wait = _BACKOFF_SECONDS[min(attempt - 1, len(_BACKOFF_SECONDS) - 1)]
                    print(f"  [TRANSIENT] {type(e).__name__} — retry {attempt}/"
                          f"{_MAX_PIPELINE_ATTEMPTS - 1} in {wait}s...")
                    time.sleep(wait)
                    continue
                break  # non-transient, or out of attempts

        return {"report": None, "timings": {}, "cost": tracker.snapshot(),
                "error": f"{type(last_err).__name__}: {last_err}",
                "attempts": _MAX_PIPELINE_ATTEMPTS}
    finally:
        tracker.unregister()
        os.environ.pop("EVAL_EXCLUDE_SOURCES", None)  # never leak the lever past a run


# ── Stage 1: held-out AURU benchmark ───────────────────────────────────────────

def run_held_out_benchmark() -> dict:
    print("\n" + "=" * 64)
    print("  HELD-OUT BENCHMARK — AURU removed from knowledge base")
    print(f"  keyword: '{HELD_OUT_KEYWORD}'  |  excluding: {HELD_OUT_EXCLUDE_SOURCE}")
    print("=" * 64)

    run = _run_pipeline(HELD_OUT_KEYWORD, exclude_source=HELD_OUT_EXCLUDE_SOURCE)
    if run["error"]:
        print(f"  [ERROR] pipeline failed: {run['error']}")
        return {"keyword": HELD_OUT_KEYWORD, "pipeline_error": run["error"]}

    print("  Pipeline done. Judging convergence vs AURU ground truth...")
    conv = judge_auru_convergence(run["report"], AURU_GROUND_TRUTH)

    out = {
        "keyword": HELD_OUT_KEYWORD,
        "excluded_source": HELD_OUT_EXCLUDE_SOURCE,
        "convergence": conv,
        "timings": run["timings"],
        "cost": run["cost"],
        "report": run["report"],
    }
    if conv.get("error"):
        print(f"  [WARN] convergence judge error: {conv['error']}")
    else:
        print(f"  Convergence: {conv['convergence_overall']}/5  "
              f"(palette {conv['palette_match']}, type {conv['typography_match']}, "
              f"positioning {conv['positioning_match']}, brands {conv['benchmark_overlap']})")
    return out


# ── Stage 2: rubric sweep ──────────────────────────────────────────────────────

def run_rubric_sweep(limit: int | None) -> list[dict]:
    cases = KEYWORDS[:limit] if limit else KEYWORDS
    results = []
    for i, case in enumerate(cases, 1):
        kw, signal = case["keyword"], case["signal"]
        print(f"\n[{i}/{len(cases)}] '{kw}'  (expected: {signal})")
        run = _run_pipeline(kw, exclude_source=None)

        if run["error"]:
            print(f"  [ERROR] pipeline failed: {run['error']}")
            results.append({"keyword": kw, "signal": signal,
                            "pipeline_error": run["error"], "cost": run["cost"],
                            "timings": run["timings"]})
            continue

        verdict = judge_report(kw, signal, run["report"])
        if verdict["error"]:
            print(f"  [WARN] judge error: {verdict['error']}")
        else:
            print(f"  overall {verdict['overall']}/5  "
                  f"| {', '.join(f'{k}={v}' for k, v in verdict['scores'].items())}")
            if any(verdict["flags"].values()):
                tripped = [f for f, v in verdict["flags"].items() if v]
                print(f"  [AUTO-FAIL] {', '.join(tripped)}")

        results.append({
            "keyword": kw, "signal": signal,
            "verdict": verdict, "timings": run["timings"], "cost": run["cost"],
            "report": run["report"],
        })
    return results


# ── Aggregation + reporting ────────────────────────────────────────────────────

def _avg(values: list) -> float | None:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 2) if vals else None


def aggregate(sweep: list[dict]) -> dict:
    scored = [r for r in sweep if r.get("verdict") and not r["verdict"].get("error")]
    overalls = [r["verdict"]["overall"] for r in scored]
    per_dim = {k: _avg([r["verdict"]["scores"][k] for r in scored]) for k in DIMENSIONS}
    latencies = [r["timings"].get("total") for r in sweep if r.get("timings", {}).get("total")]
    costs = [r["cost"].get("cost_usd") for r in sweep if r.get("cost", {}).get("cost_usd") is not None]
    tokens = [r["cost"].get("total_tokens") for r in sweep if r.get("cost", {}).get("total_tokens")]
    judge_errors = sum(1 for r in sweep if r.get("verdict") and r["verdict"].get("error"))
    auto_fails = sum(1 for r in scored if any(r["verdict"]["flags"].values()))
    pipeline_errors = sum(1 for r in sweep if r.get("pipeline_error"))

    # The mean is only trustworthy if most cases actually scored. One network drop
    # that wipes 12/13 cases must NOT surface a confident "4.5/5" — that misleads
    # you and any reviewer. Require >=80% scored AND at least 3 data points.
    n_cases, n_scored = len(sweep), len(scored)
    reliable = n_cases > 0 and n_scored >= max(3, int(0.8 * n_cases + 0.999))

    return {
        "n_cases": n_cases,
        "n_scored": n_scored,
        "pipeline_errors": pipeline_errors,
        "judge_errors": judge_errors,
        "reliable": reliable,
        "mean_overall": _avg(overalls),
        "per_dimension_mean": per_dim,
        "auto_fail_count": auto_fails,
        "mean_latency_s": _avg(latencies),
        "mean_cost_usd": _avg(costs) if costs else None,
        "mean_total_tokens": _avg(tokens) if tokens else None,
    }


def write_markdown(path: Path, benchmark: dict | None, sweep: list[dict], agg: dict) -> None:
    L = []
    L.append("# Eval Run — Visual Direction Research Agent")
    L.append(f"\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Judge: {DEFAULT_JUDGE_MODEL}_\n")

    # Held-out benchmark
    if benchmark:
        L.append("## Held-out AURU benchmark (de-leaked)")
        L.append("\nAURU was removed from the knowledge base for this run. Convergence "
                 "measures how far the pipeline independently re-derived the manual direction.\n")
        conv = benchmark.get("convergence", {})
        if conv.get("error"):
            L.append(f"- **Status:** judge error — {conv['error']}")
        elif benchmark.get("pipeline_error"):
            L.append(f"- **Status:** pipeline error — {benchmark['pipeline_error']}")
        else:
            L.append(f"- **Convergence overall:** {conv['convergence_overall']} / 5")
            L.append(f"- Palette {conv['palette_match']}/5 · Typography {conv['typography_match']}/5 · "
                     f"Positioning {conv['positioning_match']}/5 · Benchmark overlap {conv['benchmark_overlap']}/5")
            L.append(f"- **Matched:** {', '.join(conv.get('matched_elements', [])) or '—'}")
            L.append(f"- **Missed:** {', '.join(conv.get('missed_elements', [])) or '—'}")
            L.append(f"- _{conv.get('justification', '')}_")
        L.append("")

    # Aggregate
    L.append("## Rubric sweep — aggregate")
    L.append("")
    if agg["n_cases"] == 0:
        L.append("_Sweep skipped (--benchmark-only). See held-out benchmark above._")
        L.append("")
        path.write_text("\n".join(L), encoding="utf-8")
        return  # nothing further to tabulate
    if not agg["reliable"]:
        L.append(f"> ⚠️ **NOT RELIABLE — only {agg['n_scored']} of {agg['n_cases']} cases scored "
                 f"({agg['pipeline_errors']} pipeline errors, {agg.get('judge_errors', 0)} judge errors).** "
                 "The mean below is over too few cases to trust — treat it as anecdotal, not a result. "
                 "Re-run on a stable connection (most failures are usually transient network drops).\n")
    L.append(f"- Cases: {agg['n_cases']} (scored {agg['n_scored']}, pipeline errors {agg['pipeline_errors']}, "
             f"judge errors {agg.get('judge_errors', 0)})")
    if agg["reliable"]:
        L.append(f"- **Mean overall: {agg['mean_overall']} / 5**")
    else:
        L.append(f"- Mean overall (UNRELIABLE, n={agg['n_scored']}): {agg['mean_overall']} / 5")
    L.append(f"- Auto-fails (hallucinated brand / contradiction): {agg['auto_fail_count']}")
    L.append(f"- Mean latency: {agg['mean_latency_s']} s/run")
    if agg["mean_cost_usd"] is not None:
        L.append(f"- Mean cost: ${agg['mean_cost_usd']}/run · mean tokens: {agg['mean_total_tokens']}")
    else:
        L.append("- Mean cost: n/a (LiteLLM cost callback unavailable in this environment)")
    L.append("\n**Per-dimension means:**\n")
    L.append("| Dimension | Mean |")
    L.append("|---|---|")
    for k, (label, _w, _why) in DIMENSIONS.items():
        L.append(f"| {label} | {agg['per_dimension_mean'][k]} |")
    L.append("")

    # Per-case table
    L.append("## Rubric sweep — per case")
    L.append("")
    L.append("| Keyword | Signal | Overall | Pos | Spec | Coh | Bench | Act | Flags | Latency | Cost |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sweep:
        kw, sig = r["keyword"], r["signal"]
        lat = r.get("timings", {}).get("total", "—")
        cost = r.get("cost", {}).get("cost_usd")
        cost_s = f"${cost}" if cost is not None else "—"
        if r.get("pipeline_error"):
            L.append(f"| {kw} | {sig} | PIPELINE ERR | | | | | | | {lat} | {cost_s} |")
            continue
        v = r["verdict"]
        if v.get("error"):
            L.append(f"| {kw} | {sig} | JUDGE ERR | | | | | | | {lat} | {cost_s} |")
            continue
        s = v["scores"]
        flags = ",".join(f for f, on in v["flags"].items() if on) or "—"
        L.append(f"| {kw} | {sig} | **{v['overall']}** | {s['positioning_fit']} | "
                 f"{s['specificity']} | {s['coherence']} | {s['benchmark_validity']} | "
                 f"{s['actionability']} | {flags} | {lat}s | {cost_s} |")
    L.append("")

    # Justifications
    L.append("## Judge justifications")
    L.append("")
    for r in sweep:
        if r.get("verdict") and not r["verdict"].get("error"):
            L.append(f"**{r['keyword']}** ({r['verdict']['overall']}/5): {r['verdict']['justification']}\n")

    path.write_text("\n".join(L), encoding="utf-8")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run the Visual Direction Agent eval harness")
    parser.add_argument("--benchmark-only", action="store_true", help="Only the held-out AURU benchmark")
    parser.add_argument("--no-benchmark", action="store_true", help="Skip the held-out AURU benchmark")
    parser.add_argument("--limit", type=int, default=None, help="Only the first N keywords (quick smoke test)")
    args = parser.parse_args()

    _preflight()  # exit fast with a clear message if the venv/deps aren't ready

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    started = time.time()

    benchmark = None
    if not args.no_benchmark:
        benchmark = run_held_out_benchmark()

    sweep: list[dict] = []
    if not args.benchmark_only:
        sweep = run_rubric_sweep(args.limit)

    agg = aggregate(sweep) if sweep else {
        "n_cases": 0, "n_scored": 0, "pipeline_errors": 0, "judge_errors": 0,
        "reliable": False, "mean_overall": None,
        "per_dimension_mean": {k: None for k in DIMENSIONS}, "auto_fail_count": 0,
        "mean_latency_s": None, "mean_cost_usd": None, "mean_total_tokens": None,
    }

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "judge_model": DEFAULT_JUDGE_MODEL,
        "wall_clock_s": round(time.time() - started, 1),
        "held_out_benchmark": benchmark,
        "aggregate": agg,
        "sweep": sweep,
    }

    json_path = RESULTS_DIR / f"eval_run_{stamp}.json"
    md_path = RESULTS_DIR / f"eval_run_{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(md_path, benchmark, sweep, agg)

    print("\n" + "=" * 64)
    print("  EVAL COMPLETE")
    if sweep:
        if agg["reliable"]:
            print(f"  Mean overall: {agg['mean_overall']}/5 over {agg['n_scored']} scored cases")
        else:
            print(f"  ⚠️  UNRELIABLE: only {agg['n_scored']}/{agg['n_cases']} cases scored "
                  f"({agg['pipeline_errors']} pipeline errors). Mean ({agg['mean_overall']}/5) is "
                  "anecdotal — re-run on a stable connection.")
        print(f"  Auto-fails: {agg['auto_fail_count']} | Mean latency: {agg['mean_latency_s']}s")
        if agg["mean_cost_usd"] is not None:
            print(f"  Mean cost: ${agg['mean_cost_usd']}/run")
    if benchmark and benchmark.get("convergence", {}).get("convergence_overall") is not None:
        print(f"  Held-out AURU convergence: {benchmark['convergence']['convergence_overall']}/5")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")
    print("=" * 64)


if __name__ == "__main__":
    main()
