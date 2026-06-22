# Evaluation Harness

Turns "is the output good?" and "what does it cost?" into numbers you can track
across runs — and replaces the circular AURU demo with an honest, held-out proof.

## Why this exists

The original demo put `auru_brand_research.txt` **into** the knowledge base, then
"proved" the agent worked by showing it reproduced the AURU direction. That is
retrieval of a planted answer, not automation. The first interview question —
"what's in your knowledge base?" — collapses it.

This harness fixes two gaps a senior reviewer will probe:

1. **De-leaked proof.** AURU is removed from retrieval, and we measure whether the
   pipeline *independently re-derives* it.
2. **Measured quality + cost.** An LLM-as-judge scores every report on a fixed
   rubric; latency and token/USD cost are captured per run.

## What's here

| File | Role |
|---|---|
| `eval_dataset.py` | 13 fixed keyword cases (across positioning archetypes) + the AURU held-out ground truth |
| `rubric.py` | 5 weighted scoring dimensions, 1–5 anchors, two auto-fail safety flags |
| `judge.py` | LLM-as-judge (rubric) + AURU convergence judge, via LiteLLM, validated by Pydantic |
| `cost_tracker.py` | Best-effort token/USD accounting via a LiteLLM callback |
| `run_eval.py` | Runner: sweep + held-out benchmark → JSON + Markdown in `results/` |

## How to run

From `visual-direction-agent/` with the venv active:

```powershell
.\venv\Scripts\Activate.ps1

python -m eval.run_eval --limit 2 --no-benchmark   # ~2-case smoke test first
python -m eval.run_eval                             # full sweep + held-out benchmark
python -m eval.run_eval --benchmark-only            # just the de-leaked AURU proof
```

Outputs land in `eval/results/eval_run_<timestamp>.{json,md}`. Open the `.md` for
the tables; the `.json` is the full record (including every produced report).

> Runs are **fresh** (`use_cache=False`) and **text-only** (`skip_moodboard=True`).
> Caching would measure the cache, not the system; moodboards are slow, costly, and
> judged by eye, not by this harness.

## How scoring works

Each report is judged 1–5 on: **positioning fit** (30%), **specificity** (20%),
**benchmark validity** (20%), **coherence** (15%), **actionability** (15%). The
weighted mean is the overall. Two auto-fail flags — **hallucinated brands** and
**internal contradiction** — cap the overall at 2.0 regardless of the rest, because
a brief that invents a benchmark or contradicts itself is not shippable.

The judge defaults to `claude-opus-4-8` — deliberately a **different, stronger
model than the `claude-sonnet-4-6` generator** to avoid self-preference bias.
Override with the `JUDGE_MODEL` env var.

## The held-out benchmark (the headline result)

`run_eval` sets `EVAL_EXCLUDE_SOURCES=auru_brand_research.txt`, which makes the
retriever drop AURU at the DB level (see `rag/retriever.py`). The pipeline runs
`"quiet luxury wellness"` blind, and a convergence judge scores how far the result
matches the AURU ground truth on palette character, typographic class, positioning
thesis, and benchmark-brand overlap.

**This is the slide to show.** "With our own research removed from the system, the
agent independently converged on the same direction at X/5" is a real claim. The
old version was not.

### Live result (run 2026-06-19)

**Convergence 4.5 / 5** — palette 4, typography 5, positioning 5, benchmark overlap 4.
The pipeline (AURU removed) independently re-derived the exact cream `#F5F1E8`, the
low-saturation sage, the taupe depth tone, an old-style-serif + humanist-sans pairing,
the quiet-luxury/restraint thesis, and named Aesop. It diverged by dropping the near-black
charcoal anchor for taupe, naming Susanne Kaufmann / Vintner's Daughter instead of
Le Labo / Bamford (real, same positioning — not hallucinations), and choosing cool light
over the ground truth's warm light. Economics: ~$0.15/run text-only, ~190s/run.

## Robustness behaviours (added after live runs)

These exist because each was a real failure first:

- **Preflight check.** On start, the runner imports `tavily/crewai/chromadb/litellm`. If any
  fail it exits in ~1s with a plain "activate your venv" message and the interpreter path —
  not 13 identical `ModuleNotFoundError` tracebacks.
- **Transient-error retry.** `_run_pipeline` retries up to 3× (5s then 15s backoff) on
  transient failures: DNS `getaddrinfo`, provider 500/529, rate limit, timeout, connection
  reset. Non-transient failures (schema validation, missing module) fail fast — that's signal,
  not noise.
- **Honest aggregate.** A run is `reliable` only if ≥80% of cases scored AND ≥3 did. Otherwise
  the console and Markdown lead with "⚠️ NOT RELIABLE — only N/M scored" and refuse to present
  a confident mean. A single network drop must never surface a misleading "4.5/5" over n=1.
- **Judge model.** `claude-opus-4-8` rejects a `temperature` param, so the judge omits it.

## Troubleshooting

- **Every case fails with `No module named 'tavily'`** → the venv is not active (the package
  IS installed; the wrong interpreter can't see it). Run `.\venv\Scripts\Activate.ps1`, then
  `python -c "import sys; print(sys.executable)"` — the path must end in `venv\Scripts\python.exe`.
  If activation is blocked, `Set-ExecutionPolicy -Scope Process -Bypass` in that session.
- **Many cases fail with `getaddrinfo failed` / `InternalServerError`** → network/DNS drop.
  The retry absorbs brief blips; for a sustained outage, re-run on a stable connection.
- **Cost reads `n/a`** → the installed LiteLLM didn't expose a cost table for that call.
  Non-fatal; latency still stands.

## Honest limits

- 13 cases is a smoke test, not a verdict. 2026 practice is ≥500 before aggregate
  metrics are trustworthy; this is sized for a capstone.
- LLM-as-judge has variance and its own biases; treat scores as directional and
  always read the justifications, not just the number.
- Cost is best-effort and depends on the LiteLLM version exposing a cost table;
  if unavailable it reports `n/a` and latency still stands.
