# Session Handoff — Visual Direction Research Agent
## Capstone Project — Generative AI & Agentic AI Certification

---

## PROJECT IDENTITY
- **What:** 5-agent Visual Direction Research System
- **Framework:** CrewAI for orchestration, ChromaDB + sentence-transformers for RAG, HuggingFace FLUX.1-schnell for image generation
- **Due:** July 4, 2026 (Capstone Day). Orientation: June 28, 2026
- **Workspace folder:** `C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent\`
- **venv activation:** `.\venv\Scripts\Activate.ps1` (run from inside the project folder)
- **Run from:** Always run commands from inside `visual-direction-agent\` with venv active

---

## BUILD STATUS — EVERYTHING IS COMPLETE

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| Agent 01 — Trend Researcher | `agents/agent_01_trend_researcher.py` | ✅ Done + tested | Tavily web search, output validation, 24hr cache |
| Agent 02 — Design Theory Analyst | `agents/agent_02_design_theory_analyst.py` | ✅ Done + tested | RAG retrieval, deduplication, 24hr cache |
| Agent 03 — Direction Synthesiser | `agents/agent_03_direction_synthesiser.py` | ✅ Done + tested | Sonnet, conflict resolution, no tools |
| Agent 04 — Report Writer | `agents/agent_04_report_writer.py` | ✅ Done + tested | Pydantic schema validation, JSON output |
| Agent 05 — Moodboard Generator | `agents/agent_05_moodboard_generator.py` | ✅ Done + tested | HF FLUX images, saved to moodboard_cache/ |
| RAG pipeline | `rag/ingest.py` + `rag/retriever.py` | ✅ Done | 64 chunks in ChromaDB, all-MiniLM-L6-v2 |
| Full pipeline | `crew.py` | ✅ End-to-end tested | 275s fresh / ~120s cached. All 5 agents chain correctly |
| FastAPI layer | `api.py` | ✅ Built + working | Background task + polling, moodboard image serving |
| Streamlit UI | `ui/app.py` | ✅ Built + working | Cream theme, report left, moodboard grid right |

---

## HOW TO RUN THE FULL SYSTEM

You need **two PowerShell terminals**, both with venv active.

### Terminal 1 — Start the API first
```powershell
cd "C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent"
.\venv\Scripts\Activate.ps1
python api.py
```
Wait until you see: `Uvicorn running on http://127.0.0.1:8000`

### Terminal 2 — Start the Streamlit UI
```powershell
cd "C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent"
.\venv\Scripts\Activate.ps1
streamlit run ui/app.py
```
Streamlit opens `http://localhost:8501` in your browser automatically.

**Only interact with `localhost:8501`** — that is the UI. Do not open `localhost:8000` (that is the API endpoint, not a browser interface).

### To run the pipeline from CLI (no UI)
```powershell
python crew.py "quiet luxury wellness"
python crew.py "quiet luxury wellness" --no-cache      # force fresh run
python crew.py "quiet luxury wellness" --no-moodboard  # skip image generation
```

---

## API ENDPOINTS (for reference)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/generate` | Start pipeline — returns `job_id` immediately |
| GET | `/status/{job_id}` | Poll for progress and final result |
| GET | `/moodboard/{filename}` | Serve generated PNG images via HTTP |
| GET | `/health` | Liveness check |
| GET | `/jobs` | List all jobs this session (debug) |

---

## KEY FILES AND THEIR ROLES

```
visual-direction-agent/
├── crew.py                             MAIN ENTRY POINT — tested end-to-end
├── api.py                              FastAPI — background task + polling
├── agents/
│   ├── agent_01_trend_researcher.py    Tavily web search, caching
│   ├── agent_02_design_theory_analyst.py  RAG retrieval, dedup, caching
│   ├── agent_03_direction_synthesiser.py  Merge + conflict resolution
│   ├── agent_04_report_writer.py       Pydantic schema output + guardrails
│   └── agent_05_moodboard_generator.py HF FLUX image generation
├── tools/
│   ├── search_tool.py                  Tavily @tool
│   ├── rag_tool.py                     ChromaDB @tool
│   └── image_gen_tool.py               HF FLUX @tool
├── rag/
│   ├── ingest.py                       Run once to populate ChromaDB
│   ├── retriever.py                    Session dedup logic
│   └── knowledge_base/                 5 .txt docs — 64 chunks in ChromaDB
│       ├── auru_brand_research.txt
│       ├── colour_theory_principles.txt
│       ├── typography_pairing_rules.txt
│       ├── spatial_design_principles.txt
│       └── brand_positioning_frameworks.txt
├── schemas/
│   ├── report_schema.py                VisualDirectionReport Pydantic model
│   └── trend_schema.py                 Agent 01 output validation
├── utils/
│   ├── llm.py                          build_llm() — FREE_PRIMARY routing + NVIDIA/Groq fallback + served-model stamp
│   ├── observability.py                LangSmith setup (tool spans only — see Jun 22 update)
│   ├── run_logger.py                   Tees each run's console output to logs/run_*.log
│   └── cache.py                        24hr JSON cache for Agent 01 + 02
├── ui/
│   └── app.py                          Streamlit UI — complete and working
├── moodboard_cache/                    Generated PNG images (.gitignore)
├── cache/                              Agent 01+02 JSON cache (.gitignore)
└── logs/                               Per-run console logs: run_<ts>_<slug>.log (.gitignore)
```

---

## ENV VARIABLES (.env is configured and working)

```
ANTHROPIC_API_KEY     set — STILL OUT OF CREDITS (confirmed again Jun 22, every call 400s "credit balance too low"). With FREE_PRIMARY=groq set, Anthropic is no longer called at all.
FREE_PRIMARY          = groq  ← runs ALL agents on Groq 70B primary, NVIDIA NIM auto-fallback. NO Anthropic spend. Unset = Anthropic-primary; set "nvidia" to swap primary/fallback. (Added Jun 20, turned on Jun 22 — see SESSION UPDATE June 22.)
GROQ_API_KEY          working (free, daily-reset tier — current primary LLM provider)
NVIDIA_API_KEY        working (free NIM tier — automatic fallback if Groq errors / rate-limits)
TAVILY_API_KEY        working
HF_TOKEN              working (FLUX image generation)
LANGCHAIN_API_KEY     set (LangSmith — traces TOOL spans only; LLM-call tracing not viable, see Jun 22 update)
LANGCHAIN_TRACING_V2  = true
LANGCHAIN_PROJECT     = visual-direction-agent
GEMINI_API_KEY        set but NOT used (free tier quota is 0 for image model)
```

---

## CRITICAL TECHNICAL FACTS (hardwon — do not repeat these mistakes)

### Model strings — LiteLLM requires provider prefix
```
anthropic/claude-haiku-4-5-20251001   Agents 01, 02, 05
anthropic/claude-sonnet-4-6           Agents 03, 04
```
Do NOT use bare model names like `claude-3-5-haiku-20241022` — they will not resolve.

### NVIDIA NIM fallback for agents (added June 19, 2026) — `utils/llm.py`
Every agent's LLM is now built via `build_llm(model, tier)` instead of a bare string.
This adds an automatic NVIDIA NIM fallback so an Anthropic failure (credit balance,
5xx, overload, network) doesn't crash a run — LiteLLM transparently retries the same
request on a free NVIDIA model.

- **Mechanism:** crewai 0.80.0 `LLM.call()` forwards `**kwargs` into
  `litellm.completion()`, which natively accepts `fallbacks=[...]`. `build_llm` returns
  a crewai `LLM(model=..., fallbacks=["nvidia_nim/..."])`. No monkey-patching.
- **Zero-change guarantee:** if NO NVIDIA key is set, `build_llm` returns the plain
  model STRING — byte-for-byte the old behaviour. Fallback only activates when a key
  is present. The demo path is untouched unless you opt in.
- **Setup:** add to `.env`: `NVIDIA_API_KEY=nvapi-xxxx` (or `NVIDIA_NIM_API_KEY`).
  `build_llm` mirrors `NVIDIA_API_KEY` → `NVIDIA_NIM_API_KEY` because litellm's
  nvidia_nim provider reads the latter. Get a free key at build.nvidia.com.
- **Tiers / default fallback models** (override via env `NVIDIA_FALLBACK_FAST` /
  `NVIDIA_FALLBACK_STRONG`):
  - fast (Agents 01, 02, 05) → `nvidia_nim/meta/llama-3.3-70b-instruct`
  - strong (Agents 03, 04)   → `nvidia_nim/meta/llama-3.3-70b-instruct`  (was `llama-3.1-405b-instruct` — RETIRED from NIM, returns 404; fixed Jun 20 — see SESSION UPDATE June 20)
- **HONEST CAVEAT — availability, not quality parity.** The NVIDIA fallbacks are open
  Llama-class models, NOT Claude. If a fallback fires, that agent's output quality will
  differ from the Claude-validated eval scores (4.25/5 convergence etc.). The point is
  "the run completes" not "identical quality". Agent 04's JSON schema + retry guardrail
  still validate whatever the fallback produces. **For a graded eval run, use Anthropic;
  treat the fallback as live-demo insurance.**
- **Judge is deliberately NOT given a fallback.** `eval/judge.py` stays Claude-only —
  judging with a weaker/different model would bias the scores.
- **VERIFIED working June 20, 2026** via `python -m eval.smoke_fallback` (run inside the
  venv). With a deliberately-broken `ANTHROPIC_API_KEY`, the call failed over and was
  served by `nvidia_nim/meta/llama-3.3-70b-instruct` (fast tier). The verbose litellm
  traceback during this test is just litellm LOGGING the intended primary failure — not
  an error; the script prints `FALLBACK WORKS ✓` on success. To verify the strong tier
  (Llama 3.1 405B, agents 03/04): `python -m eval.smoke_fallback --tier strong`.
- **Must run inside the venv (crewai 0.80.0).** System Python has a newer crewai that
  needs the `crewai[anthropic]` extra and errors on LLM construction. `build_llm` now
  degrades to Anthropic-only (with a `[WARN]`) rather than crashing if that happens.

### SESSION UPDATE — June 20, 2026 (debugging a looping eval run)
Triggered by an eval run that appeared to "loop again and again". Root cause was NOT a code
bug in the agents — it was two stacked failures. All fixes below are applied and verified.

1. **Anthropic out of credits (the real blocker).** Every LLM call 400s `credit balance is
   too low`. Ops fix only — top up at console.anthropic.com → Plans & Billing. Until then the
   pipeline completes entirely on the NVIDIA fallback, which is Llama-70B quality, NOT Claude.
   Evidence: a Jun 20 full run produced grey "taupe" `#666666`, a sky-blue accent, and
   Lululemon/Headspace as benchmarks — exactly the mass-market output the KB says to avoid.
   Do not judge the system on a no-credit run.

2. **Strong-tier fallback was a dead model.** `nvidia_nim/meta/llama-3.1-405b-instruct` was
   retired from NVIDIA NIM and 404s, so Agents 03/04 had NO working failover — that's what
   turned a billing error into a whole-pipeline retry loop. Fixed in `utils/llm.py`:
   `NVIDIA_FALLBACK_STRONG` now defaults to `llama-3.3-70b-instruct`.
   - **Nemotron-3-ultra-550b REJECTED on data**, not vibes. `eval/compare_strong_fallback.py`
     (new file) ran both through LiteLLM: 70B answered "OK" in 2.9s; nemotron took 48.5s and
     leaked 240 chars of `reasoning_content` onto the channel CrewAI's ReAct parser reads.
     A reasoning model is the wrong tool for a ReAct fallback. Do NOT put it in `.env`.

3. **`run_eval.py` retried a billing error as if transient.** `APIConnectionError` contains
   the substring "connection", which matched `_TRANSIENT_MARKERS` → the whole 5-agent pipeline
   re-ran 3× on an unrecoverable 400. Added `_FATAL_MARKERS` (credit balance / invalid_request
   / auth / 404 / not found), checked first in `_is_transient()` → billing/auth/dead-model now
   fail fast instead of looping.

4. **`crew.py` CLI bug — flags absorbed into the keyword.** `python crew.py "x" --no-moodboard`
   made the keyword literally `x --no-moodboard`, polluting every agent prompt and the cache
   keys. Fixed: `--flags` are stripped before building the keyword.

5. **smoke_fallback.py test gap noted.** It defaults to `--tier fast`, so it never exercised
   the strong-tier model and never caught the dead 405b. Run `--tier strong` after any
   fallback change.

**Verified Jun 20:** with the fixes in, `python crew.py "quiet luxury wellness" --no-moodboard`
ran Agents 01→04 to completion (valid JSON, schema passed) with no loop — but ENTIRELY on the
70B fallback because credits are still empty. Next clean checkpoint: top up credits, then
`python crew.py "quiet luxury wellness" --no-cache --no-moodboard` and confirm Aesop-tier
benchmarks + warm hexes return.

### SESSION UPDATE — June 22, 2026 (run for free without Anthropic credits + observability)
Anthropic is still out of credits and a top-up isn't happening before the demo. This session
made the system run cleanly on FREE providers, made every run self-identify which model served
it, and added real file logging. All changes are additive; the default (FREE_PRIMARY unset)
still behaves exactly as before.

1. **FREE_PRIMARY routing — run with ZERO Anthropic spend (`utils/llm.py`).** New opt-in env var:
   - `FREE_PRIMARY=groq` (now set in `.env`) → all agents run on `groq/llama-3.3-70b-versatile`
     as PRIMARY, with `nvidia_nim/meta/llama-3.3-70b-instruct` as automatic fallback. Anthropic
     is never called.
   - `FREE_PRIMARY=nvidia` → swaps them (NVIDIA primary, Groq fallback).
   - Unset → original Anthropic-primary behaviour, byte-for-byte unchanged (graded-eval path).
   - The OTHER free provider is attached as fallback only if its key is present, so we never
     point a fallback at an unauthenticated provider. Both keys are in `.env`.
   - **Why groq primary:** Groq's LPU inference is much faster, and its free tier is daily-reset
     (30 req/min, 14,400/day) vs NVIDIA's finite credit grant. Caveat: 30 RPM can trip on rapid
     demo re-runs — NVIDIA fallback then catches it. Demo habit: run once, cache, demo from cache.
   - Verified via `python -m eval.verify_free_primary` (new file): both providers pass liveness
     + a full Agent 04 schema run.

2. **Provenance stamp — "which model actually served this run" (`utils/llm.py` + crew/api/ui).**
   LangSmith does NOT capture the LLM calls (see #4), so there was no way to tell whether a run
   used Anthropic, NVIDIA, or Groq — the configured model ≠ served model once a fallback fires.
   Fix: a litellm `CustomLogger` (`_ServedModelLogger`) records the actually-served model on BOTH
   sync and async success paths (CrewAI's fallback uses async `acompletion` — a plain sync
   callback missed it and logged "unknown"). Surfaced as `served_models()` / `reset_served_models()`,
   threaded through `crew.py` (banner `Served by:` line + returned `served_models`), `api.py`
   (`_serialise_result`), and `ui/app.py` (HTML export footer "Served by …" + sidebar caption).
   So every run and every exported report now self-identifies its provider.

3. **File logging — `logs/run_<ts>_<slug>.log` (`utils/run_logger.py`, NEW).** The pipeline only
   `print()`-ed to the terminal; nothing was saved, so "check the log" was impossible after a run.
   Now every CLI run (`crew.py`) and every API/UI run (`api.py`) tees stdout+stderr to a timestamped
   file under `logs/` — capturing the `Served by:` banner, per-agent timings, and any tracebacks.
   It's a tee (still prints to the terminal too) and always restores streams on exit. NOTE: `sys.stdout`
   is process-global, so this assumes runs are sequential (true for the single-user demo); parallel
   runs would interleave. Verified: stdout+stderr capture, slug sanitising, header/footer, stream
   restore all pass.

4. **LangSmith LLM-call tracing — ATTEMPTED then REVERTED. DO NOT RE-ADD.** Tried adding litellm's
   `"langsmith"` success_callback so model/token/cost would trace (currently only @traceable TOOL
   spans reach LangSmith — Tokens/Cost columns are empty in the Runs view). It does NOT work here:
   litellm's `LangsmithLogger.__init__` calls `asyncio.create_task()`, which needs a running event
   loop, but CrewAI runs litellm in sync threads → `RuntimeError: no running event loop` on EVERY
   call, zero traces, and it broke the provenance stamp. Reverted in `utils/observability.py` with an
   explanatory comment (litellm issue #6862). LLM-level LangSmith tracing isn't viable in this sync
   CrewAI setup; if ever needed, run the pipeline under an event loop / use acompletion throughout,
   or write a sync exporter — real work, not a one-liner. Tool spans still trace; provenance now
   comes from the stamp (#2), not LangSmith.

**Verified Jun 22 (artistic-cafe full run):** the complete 5-agent pipeline — including Agent 05 —
ran end-to-end on the free path and generated all 5 moodboard panels. Agent 02 hit a CrewAI ReAct
format wobble on the 70B ("missed the 'Action:' after 'Thought:'") but RECOVERED and produced valid
output — tool-calling on the free model works, just less cleanly than Claude. Quality caveat unchanged
from Jun 20: free-70B output is weaker than Claude (loose colour naming e.g. `#663300` called "deep
red"/"terracotta" when it's brown; thin, repetitive `visual_narrative` ~50 words vs the 100–150 intent).
For a graded/quality run, top up Anthropic and unset FREE_PRIMARY; for a no-cost working demo, groq is fine.

### ⏭️ PICK UP HERE — June 22 run results + corrected plan (groq backfired)
Ran `python crew.py "artistic cafe" --no-cache` after turning on `FREE_PRIMARY=groq`. The new
file logging captured everything (`logs/run_20260622_005204_artistic-cafe.log`, 1607 lines).
Mixed results — read before continuing:

**What worked:**
- **File logging works** — full run captured (banner, timings, tracebacks). This is how the
  below was diagnosed. `logs/` logging is DONE and verified live.
- **Anthropic cleanly out of the path** — ZERO "credit balance too low" errors. FREE_PRIMARY routing works.
- **LangSmith revert worked** — the 6 remaining "no running event loop" lines are now from
  litellm `asyncify.py` (benign internal fallback plumbing), NOT the LangsmithLogger crash.
  Don't chase them.

**What's broken — fix next session:**
1. **GROQ FREE TIER IS TOO SMALL FOR THIS PIPELINE — this is the headline.** The binding limit
   is TOKENS, not requests: **12,000 tokens/min + 100,000 tokens/day**. The run hit the per-minute
   wall 6× (429 RateLimitError) and the log shows `Used: 96,474 / 100,000` daily — i.e. one or two
   runs exhausts Groq's whole day. (The earlier "30 req/min, 14,400/day" figure was REQUEST counts,
   not the binding token caps — that recommendation was wrong.) This rate-limiting caused 27
   tracebacks, the slow muddling, AND broke Agent 05.
2. **Agent 05 → 0/5 panels this run** — collateral from the rate-limiting (the model got
   throttled into rambling non-prompts). NOT a new Agent 05 bug: a different run ~18 min earlier
   made 5/5 fine. Re-test on a non-rate-limited provider before treating as a separate issue.
3. **Provenance stamp STILL logs "Served by: unknown"** — even though the log proves Groq served
   every call. BOTH attempts failed: (a) plain sync `litellm.success_callback` fn, (b) async
   `CustomLogger`. litellm callbacks are not reliably firing in this crewai setup. STOP trying
   callbacks. Next approach: capture the CONFIGURED primary directly in `build_llm()` (it already
   knows the exact model string it hands each agent) → append to `_SERVED_MODELS` there.
   Deterministic, no litellm dependency. Won't reflect a post-fallback swap, but "groq/… (configured)"
   beats "unknown". (Optional: keep the callback too and let it override when it does fire.)

**CORRECTED RECOMMENDATION → switch `FREE_PRIMARY=groq` to `FREE_PRIMARY=nvidia`.** The earlier full
NVIDIA run (Jun 22, ~478s) completed with NO rate-limit spam — slower per call, but it never hit a
token wall mid-run and Agent 05 worked. For a token-heavy pipeline you iterate on during demo prep,
NVIDIA's limits fit; Groq's 100k/day doesn't. Keep Groq as the FALLBACK (cross-covers if NVIDIA hiccups).

**TODO next session — UPDATED June 22 (cont., Cowork session):**
- [x] Edit `.env`: `FREE_PRIMARY=groq` → `FREE_PRIMARY=nvidia`. DONE (`FREE_PRIMARY=nvidia` confirmed in `.env`).
- [x] Fix the stamp via the configured-primary method in `utils/llm.py` `build_llm()` (see #3 above). DONE —
      added `_CONFIGURED_MODELS`; `build_llm()` + `_build_free_primary()` now record the primary model they
      hand each agent; `served_models()` returns callback-confirmed models if any, else the configured ones
      tagged `(configured)`; `reset_served_models()` clears both. The litellm callback is kept as an override
      for when it does fire. ⚠️ NOT run-verified yet — needs the venv re-run below to confirm the banner reads
      `Served by: nvidia_nim/... (configured)` instead of `unknown`.
- [ ] Re-run `python crew.py "artistic cafe" --no-cache`; confirm: clean log, `Served by: nvidia_nim/...`,
      and **moodboard 5/5** (validates the 0/5 was rate-limit collateral, not an Agent 05 regression).
- [ ] Groq daily tokens reset at 24h — if testing Groq again, do it sparingly (≈2 full runs/day max).
- [Cowork June 22] GIT/SECRETS CHECK: no repo exists yet (no `.git` at `visual-direction-agent/` OR the parent
  `Capstone Project - Gen AI/`), so `.env` has NEVER been committed — keys are not leaked. `.gitignore` already
  lists `.env` (line 6) and a subdir `.gitignore` covers its subtree regardless of repo root, so `.env` stays
  ignored even if you init at the parent. Before the first push: `git init` INSIDE `visual-direction-agent/`,
  include `.gitignore` in the initial commit, then confirm `git status` does NOT list `.env` before pushing.
  (HANDOFF.md is safe to commit — it names env vars and statuses only, no key values.)
- Speed/quality note unchanged: free 70B output is weaker than Claude (loose colour naming, thin
  ~50-word narrative). Fine for a working free demo; for a graded/quality run, top up Anthropic + unset FREE_PRIMARY.

### crewai-tools is NOT installed
Conflicts with `crewai==0.80.0`. All tools use the native `@tool` decorator from `crewai.tools` + provider SDKs directly. Do not add crewai-tools.

### Image generation — HuggingFace FLUX only
- Pollinations.ai: removed — rate limited (free tier limit is 0)
- Google Gemini image: removed — free tier quota is 0
- Primary: `huggingface_hub.InferenceClient` with FLUX.1-schnell
- First call per session: 30–60s cold start. Subsequent calls faster.
- Images saved to `moodboard_cache/` as `.png` files

### DECISION (June 19, 2026): keep FLUX.1-schnell — rejected FLUX.2-klein-4B (NVIDIA)
**Decision:** Stay on HuggingFace FLUX.1-schnell. Do NOT migrate the moodboard backend
to NVIDIA-hosted FLUX.2-klein-4B. No production code changed.

**Why this came up:** Anthropic API hit a credit-balance error mid eval-run, which
prompted looking at NVIDIA NIM (free `nvapi-` tier) as an alternative provider — and
FLUX.2-klein-4B specifically as a newer image model.

**How it was decided — head-to-head A/B test, not vibes** (`eval/ab_image_backends.py`):
ran the same 5 quiet-luxury-wellness moodboard prompts through both backends, side by
side, judged by eye on prompt adherence.

| | FLUX.1-schnell (HF) | FLUX.2-klein-4B (NVIDIA) |
|---|---|---|
| Quality on passing prompts | Good | Good / arguably better, on-brief |
| Speed | ~5–24s | ~3s (faster) |
| **Content filter** | none | **blocks benign prompts** |

**The deciding factor — NVIDIA's hosted content filter.** klein returned
`finishReason=CONTENT_FILTERED` (empty image) on "close-up of hands holding a ceramic
bowl" — a perfectly benign prompt. This brief's photography direction is *literally*
"hands, not faces; hands on stone," so the filter blocks the exact imagery the wellness/
beauty moodboards depend on. A backend that silently refuses core prompts mid-demo is a
coverage risk we don't control. schnell has no such filter and always renders.

**Quality/speed were NOT the reason to stay** — klein was competitive-to-better and
faster. The rejection is purely about guaranteed coverage for this brief's subject matter.

**Demo framing:** present this as evidence-based engineering judgment, not "tried NVIDIA,
gave up": *"I benchmarked FLUX.2-klein-4B against FLUX.1-schnell head-to-head; klein was
faster and high-quality but its hosted content filter blocks the hands/skin imagery this
brief needs, so I chose schnell for guaranteed coverage."* The A/B script + contact sheet
(`eval/ab_images/comparison.html`) are kept as evidence.

**If revisited later:** the right architecture would be klein-primary + schnell-fallback-
on-`CONTENT_FILTERED` (best quality where allowed, full coverage everywhere). Not built —
deliberately deferred to avoid touching a working path before the demo. NVIDIA notes:
klein `cfg_scale` is a 0–1 scale (endpoint enforces ≤1.0), NOT the 3–7 Stability range;
invoke URL `https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b`.

### Agent 05 moodboard parser
The parser in `parse_moodboard_output()` handles three URL formats the agent may write:
- `file:///C:\Users\...` — standard browser-style file URI (most common)
- `FILE::C:\Users\...` — tool output prefix
- `C:\Users\...` — bare Windows path

The regex strips all prefixes and returns bare file paths. This was a bug that caused 0/5 panels — it is fixed.

### API — do NOT use `host="0.0.0.0"` in the browser
`api.py` binds to `127.0.0.1:8000`. Navigating to `0.0.0.0:8000` in a browser times out. Always use `localhost:8000` for the API and `localhost:8501` for the UI.

### ChromaDB must be re-populated after knowledge base update
A new document was added (`aesthetic_territories_reference.txt` — 25 chunks, 7 aesthetic territories).
Run with `--reset` to wipe and rebuild:
```powershell
python -m rag.ingest --reset
```
After reset the collection will have ~89 chunks (was 64). Verify with:
```powershell
python -c "import chromadb; c=chromadb.PersistentClient(path='rag/chroma_db'); print(c.get_collection('visual_direction_kb').count())"
```

### RAG knowledge base — current documents
| File | Purpose | Chunks (approx) |
|------|---------|-----------------|
| `auru_brand_research.txt` | AURU brand research — quiet luxury wellness territory | 9 |
| `colour_theory_principles.txt` | Itten/Albers colour theory, brand colour psychology | 13 |
| `typography_pairing_rules.txt` | Typeface pairing logic, hierarchy rules | 14 |
| `spatial_design_principles.txt` | Negative space, grid, visual weight | 15 |
| `brand_positioning_frameworks.txt` | Premium/accessible/clinical/warm signal frameworks | 13 |
| `aesthetic_territories_reference.txt` | 7 contrasting aesthetic territories (streetwear, clinical, maximalist, dark luxury, coastal, SaaS tech, artisanal) across colour / typography / spatial dimensions | 25 |
| **Total** | | **89** |

### Windows path spaces
Project folder name contains spaces. Always quote paths in PowerShell. This is already handled throughout the codebase.

---

## KNOWN ISSUES / THINGS TO WATCH

1. **LangSmith first run** — may print "project will be created on first run" — that is fine, it auto-creates.

2. **Cache TTL** — Agent 01 + 02 outputs cached for 24hrs. Stale cache produces the same trend/theory output regardless of keyword changes. Force fresh with `--no-cache`. The UI also has a "Use cached outputs" toggle (uncheck for fresh run).

3. **HF FLUX cold start** — FIXED. `api.py` now fires a 256×256 warm-up call to FLUX.1-schnell on startup via `@app.on_event("startup")`. Watch for `[INFO] FLUX warm-up complete` in Terminal 1 before running the demo. If warm-up fails (non-fatal warning), the first image will still take 30–60s.

4. **Streamlit + polling** — FIXED. A manual "↻ Check progress" button now appears in the sidebar during a run. If the tab is backgrounded and auto-poll pauses, click it to resume without restarting.

---

## POST-BUILD IMPROVEMENTS (June 9, 2026)

Four fixes applied after initial build — no architectural changes, all additive.

| # | What | File(s) changed | Detail |
|---|------|-----------------|--------|
| 1 | Manual polling fallback | `ui/app.py` | "↻ Check progress" button appears in sidebar during run. Prevents frozen UI if browser tab is backgrounded during demo. |
| 2 | FLUX pre-warm on startup | `api.py` | `@app.on_event("startup")` fires a 256×256 dummy FLUX call in the background thread pool. Eliminates 30–60s cold-start delay. Watch for `[INFO] FLUX warm-up complete` in Terminal 1. |
| 3 | HTML report export | `ui/app.py` | "⬇ Download Report (HTML)" button at bottom of report panel. Generates a self-contained HTML file (cream theme, palette swatches, do/don't, benchmark brands). Use for demo side-by-side with AURU Miro board. LangSmith trace URL embedded in HTML footer. |
| 4 | Agent 04 retry logic | `agents/agent_04_report_writer.py` | `run_report_writer()` now retries up to 3 times on JSON parse error or Pydantic schema validation failure. Each retry injects the specific error back into the task prompt. Prevents a single bad model response from crashing the demo. |
| 5 | Cache toggle visible | `ui/app.py` | "Use cached outputs" checkbox moved out of the hidden Options expander to the main sidebar — always visible. Help text updated to reflect Agent 03+04 caching. |
| 6 | Cache Agent 03 + 04 | `crew.py` | Agents 03 and 04 now use content-hash caching (SHA256 of upstream outputs). On a cached repeat run all 5 agents return from cache. Saves ~2 Sonnet calls per repeat keyword. `--no-cache` / UI toggle still forces full fresh run. |
| 8 | LangSmith run-specific URL | `utils/observability.py` | `get_langsmith_run_url()` now queries the LangSmith API after a 3s delay to fetch the most recent run ID and returns a direct public trace link. Falls back to `https://smith.langchain.com` on error. URL is shown in sidebar and embedded in HTML export footer. |

---

## EVALUATION HARNESS + DE-LEAKED BENCHMARK (added June 18, 2026)

**Why this was added:** The original demo proof was circular — `auru_brand_research.txt`
lives in the RAG knowledge base, so the agent "reproducing" the AURU direction was
retrieval of a planted answer, not automation. A reviewer's first question ("what's in
your knowledge base?") collapses it. This adds (a) a held-out, de-leaked proof and
(b) measured quality + cost, which is the 2026 dividing line between a tutorial project
and a shippable one.

### New files — `eval/`
| File | Role |
|------|------|
| `eval/eval_dataset.py` | 13 fixed keyword cases across positioning archetypes (premium/clinical/accessible/warm/bold) + the AURU held-out ground truth |
| `eval/rubric.py` | 5 weighted dimensions (positioning fit 30%, specificity 20%, benchmark validity 20%, coherence 15%, actionability 15%), 1–5 anchors, 2 auto-fail flags (hallucinated brands, internal contradiction) that cap overall at 2.0 |
| `eval/judge.py` | LLM-as-judge (rubric) + AURU convergence judge via LiteLLM, Pydantic-validated, one retry on bad JSON. Judge defaults to `claude-opus-4-8` — deliberately a different/stronger model than the `claude-sonnet-4-6` generator to avoid self-preference bias. Override with `JUDGE_MODEL` |
| `eval/cost_tracker.py` | Best-effort token + USD accounting via a LiteLLM success callback (degrades to `n/a` if cost table unavailable; latency always stands) |
| `eval/run_eval.py` | Runner → writes JSON + Markdown to `eval/results/` |
| `eval/README.md` | How to run + interpret + honest limits |

### One source change — `rag/retriever.py`
Added `EVAL_EXCLUDE_SOURCES` env-var support. When set (comma-separated KB filenames),
`query()` adds a ChromaDB `where={"source": {"$nin": [...]}}` filter so those docs can
never be retrieved. **When unset (the normal demo path and every non-eval run), behaviour
is byte-for-byte unchanged.** The eval runner sets it to `auru_brand_research.txt` only
for the held-out benchmark, then clears it. Zero changes to any agent code.

### How to run (from `visual-direction-agent/`, venv active)
```powershell
.\venv\Scripts\Activate.ps1
python -m eval.run_eval --limit 2 --no-benchmark   # quick smoke test FIRST (~2 cases)
python -m eval.run_eval                             # full sweep + held-out benchmark
python -m eval.run_eval --benchmark-only            # just the de-leaked AURU proof
```
Runs are fresh (`use_cache=False`) and text-only (`skip_moodboard=True`) — caching would
measure the cache, not the system; moodboards are slow/costly and judged by eye.

### HEADLINE RESULT — run live June 19 (run `eval_run_20260619_011326`)
**Held-out AURU convergence: 4.5 / 5** with AURU removed from the knowledge base.
Sub-scores: palette 4, typography 5, positioning 5, benchmark overlap 4. The pipeline
independently re-derived the exact cream `#F5F1E8`, low-saturation sage, taupe depth tone,
an old-style-serif + humanist-sans pairing, the quiet-luxury/restraint thesis, negative
space as material, and named Aesop. Divergences (honest, worth knowing for Q&A): it dropped
the near-black charcoal anchor for taupe, named Susanne Kaufmann / Vintner's Daughter instead
of Le Labo / Bamford (real brands, same positioning — NOT hallucinations), and chose cool
light vs the ground truth's warm morning light.

**This is the de-leaked proof — use it as the demo headline.** "With our own research removed
from the system, the agent independently converged on the same direction at 4.5/5." The full
13-keyword rubric sweep has NOT yet completed a clean pass (see below) — capture that mean
once it does, but the held-out 4.5/5 already stands on its own.

Measured economics from the held-out + 1 scored sweep case: ~$0.15/run text-only,
~190s/run. (Full 13-case sweep ≈ 40 min, ≈ $2.) LiteLLM `response_cost` IS exposed — cost
tracking works. ChromaDB `$nin` filter works — de-leak confirmed functional.

### Hardening applied June 19 (after three live run sessions)
Each came from a real failure, not speculation:
1. **Judge model fix** — `claude-opus-4-8` rejects the `temperature` param ("deprecated").
   `eval/judge.py` no longer sends temperature. (First run scored 0 cases because of this.)
2. **Transient-error retry** — `_run_pipeline` retries up to 3× with 5s/15s backoff on
   transient failures (DNS `getaddrinfo`, provider 500/529, rate limit, timeout, connection
   reset). A network drop once wiped 12/13 cases; now a blip costs 20s, not the sweep.
   Non-transient errors (schema, missing module) still fail fast — those are real signal.
3. **Honest aggregate** — a run is `reliable` only if ≥80% of cases scored AND ≥3 did.
   When not, console + Markdown lead with "⚠️ NOT RELIABLE — only N/M scored" and refuse to
   print a confident mean. (A network drop had surfaced a misleading "4.5/5" over n=1.)
4. **Preflight guard** — `run_eval.py` checks `tavily/crewai/chromadb/litellm` import up front
   and exits in ~1s with a plain "activate your venv" message + the interpreter path, instead
   of 13 identical `ModuleNotFoundError` tracebacks. (One run failed this way: venv not active.)
5. **Bugfix** — `--benchmark-only` path no longer KeyErrors on the new aggregate keys.

### FIRST CLEAN FULL SWEEP — June 19 (`eval_run_20260619_194409`) — and what it caught
Reliable run: **12 / 13 cases scored** (the 13th, `premium electric vehicle`, failed on
"credit balance is too low" — out of Anthropic credits, NOT a code bug; top up and it runs).

**Mean overall: 3.4 / 5 — but read past the number.** Per-dimension means tell the real story:
positioning fit **4.75**, specificity **5.0**, coherence **4.75**, actionability **5.0**,
benchmark validity **3.5**. The reasoning engine is senior-grade. The 3.4 is dragged down by
the auto-fail cap correctly nuking **6 cases to 2.0**:

- **5× `hallucinated_brands`** — Agent 01 fabricated specific campaign attributions with false
  precision: "Rick Owens FW26 TOWER Campaign", "Tom Ford Black Orchid Reserve 2025 / Lewis
  Mirrett still-life archive", invented bakeries "The Baker's Project" / "N.O.V.A LAB",
  Maker's Mark "Longshorte collaboration 2024", "Stella McCartney SS25 Designed for Tomorrow".
  Real brands (Aesop, Muji, Uniqlo, Stripe, N26, Duolingo, Khan Academy, Muuto, HAY, Barry's)
  scored a clean 5.0 — the defect is narrow: invented PROPER NOUNS, not bad reasoning.
- **1× `internal_contradiction`** (`modern fintech app`): `#FFFFFF` card surface vs `#F9FAFB`
  base; plus signalled "infrastructure-grade/control" against an "accessible" brief.

**The eval earned its keep here — it caught a real hallucination problem before a reviewer
could.** That before/after is a stronger capstone story than "it works".

### FIX APPLIED June 19 — benchmark grounding (defense-in-depth, two layers)
1. **Agent 01 (`agent_01_trend_researcher.py`)** — root cause. Backstory now carries an explicit
   anti-fabrication mandate; the task has mandatory GROUNDING RULES (name only real well-known
   brands; never invent campaign titles/years/credits/collaborations; describe a brand's visual
   approach instead; omit unsupported editorial refs rather than fabricate). The `EDITORIAL
   REFERENCES` requirement was softened from "2–4 specific campaigns" to "0–3 you can support,
   or 'None verifiable from search'" — it was the prompt itself that invited the fabrication.
2. **Agent 04 (`agent_04_report_writer.py`)** — output gate. Schema CRITICAL RULES now require
   `benchmark_brands` to be real and forbid inventing campaign specifics in `reference_note`,
   so an upstream fabrication gets dropped at the gate rather than printed.

**Not yet re-measured.** Re-run `python -m eval.run_eval` to confirm the fix moves the mean
(target: the 5 `hallucinated_brands` cases clear, mean climbs toward the ~4.75 the other
dimensions already hit). The eval forces `use_cache=False`, so the new prompts take effect
immediately in the sweep. NOTE: the normal demo/UI path DOES cache — delete `cache/` (or run
the UI with caching off) so the grounded prompts also apply there, otherwise the old
fabricating outputs persist for previously-run keywords.

### KNOWN GOTCHA — venv must be active
A run that fails every case with `ModuleNotFoundError: No module named 'tavily'` means the
venv is NOT active (the package IS installed; the wrong interpreter can't see it). The new
preflight catches this. Always confirm:
```powershell
.\venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"   # must end in venv\Scripts\python.exe
```

### Next action
Activate venv → `python -m eval.run_eval` for a clean full pass → record the rubric-sweep
mean next to the held-out 4.5/5 in the README/submission.

### Verification note
The `eval/` modules were verified by direct file read of every edited region. A machine
`py_compile` could not be run from the build environment (its Linux mount froze on a stale
pre-edit snapshot), but the harness has since executed live on Windows (producing the runs
above), which confirms the files are valid. The real green light is each fresh run.

---

## CURRENT PHASE — Demo Prep (reconciled June 20, 2026)

Build is complete. All 5 agents, API, and UI are working.

**RECONCILIATION NOTE (Jun 20):** The day-by-day plan below was written ~Jun 16 and has
slipped — the Jun 16–19 rows are still open and Jun 20 was spent debugging (see SESSION
UPDATE June 20), not on the README/dry-run track. What is genuinely DONE: the build, and the
eval harness (built + run live Jun 19, held-out AURU **4.5/5** banked). What is genuinely NOT
done and unchanged: README, GitHub push, demo script, AURU side-by-side assets, LangSmith URL
capture, and the post-fix eval re-run (blocked on Anthropic credits). Roughly 10 working
windows remain to Jul 4 (weekdays, 4–7pm IST). The specific date assignments below are stale —
re-sequence them from today; status flags are corrected to reflect reality.

**Remaining work before June 28 Orientation:**

Status legend: ✅ done · 🟡 partial · ⬜ not started. Dates are the ORIGINAL plan and have
slipped — treat the Task/Status columns as the source of truth and re-date from Jun 20.

| Orig. date | Task | Status |
|------|------|--------|
| Jun 16 | Verify pipeline runs end-to-end | ✅ Runs clean structurally (Jun 20); but last verified run was 100% on the NVIDIA fallback — a Claude-quality clean run still needs credits |
| Jun 16 | Start README.md | ⬜ Not started |
| Jun 17 | Finish README.md + push to GitHub + test 2 more inputs | ⬜ Not started |
| Jun 18 | AURU side-by-side prep + write demo script | ⬜ Not started |
| Jun 19 | First full demo dry run — timed, no notes | ⬜ Not started |
| — | Eval harness built + run live (held-out AURU 4.5/5 banked) | ✅ Done Jun 19 |
| — | Loop / fallback / CLI bugs fixed | ✅ Done Jun 20 (see SESSION UPDATE) |
| (was Jun 20–21: "course sessions, no project work") | Jun 20 was actually a debugging session — fixes applied. Confirm whether Jun 20–21 course sessions still apply. | 🟡 |
| TBD | Top up Anthropic credits → re-run `eval.run_eval` for post-fix mean + all-13 clean | ⬜ BLOCKER — gates the demo proof |
| TBD | Fix top dry-run issues + UI polish | ⬜ |
| TBD | Second dry run + capture LangSmith trace URL | ⬜ |
| TBD | Test all 3 inputs + confirm submission materials | ⬜ |
| TBD | **FEATURE FREEZE** — final GitHub push, all materials locked | ⬜ |
| Jun 27–28 | Orientation | — |
| Jun 29 | Apply orientation feedback only | ⬜ |
| Jun 30 | Final submission checks | ⬜ |
| Jul 4 | **CAPSTONE DAY** | 🎯 |

**Outstanding items (not yet confirmed done):**
- README.md — not yet written
- GitHub repo — not yet confirmed as pushed
- Demo script — not yet written
- AURU side-by-side comparison assets — not yet prepared
- LangSmith trace URL — not yet captured for submission
- **Eval harness — built + run live June 19.** Held-out AURU convergence **4.5/5** (banked).
  First clean full sweep: 12/13 scored, mean 3.4/5 — but it caught a benchmark-fabrication bug
  (6 auto-fails), now FIXED via Agent 01 + 04 grounding. **Re-run `python -m eval.run_eval` to
  capture the post-fix mean** (target ~4.5+) and top up Anthropic credits first so all 13 score.
- **Re-frame the demo proof** to use the held-out benchmark, not the planted AURU run (see DEMO PLAN).
- **Clear `cache/`** before the demo so the grounded (non-fabricating) prompts apply to cached keywords.

**TO-DO — Agent 01 benchmark-hallucination (fix implemented, NOT yet verified):**
Checked June 20 — the fix IS in the code, two layers: Agent 01 backstory + task GROUNDING
RULES, and Agent 04 schema CRITICAL RULE on `benchmark_brands`. So implementation is done.
What remains is proving it worked:
- [ ] **Re-run `python -m eval.run_eval`** (top up Anthropic credits first) and confirm the
  5 `hallucinated_brands` auto-fails clear and the mean climbs from 3.4 toward ~4.5+.
  Until this run exists, the fix is UNVERIFIED — do not claim it works in the demo.
- [ ] **If fabrication persists**, the prompt mandate is only a SOFT guardrail (LLMs ignore
  "don't fabricate"). Add a HARD guardrail: programmatically cross-check each named
  benchmark brand / campaign against Agent 01's Tavily search results, and drop any proper
  noun not found in the retrieved text. This is the real fix if prompting isn't enough — not
  yet built.
- [ ] Capture the post-fix per-case table as before/after evidence for the submission.

---

## DEMO PLAN — June 28, 2026

**What to show:** Run the full pipeline live on `"quiet luxury wellness"` in the Streamlit UI. Show the output alongside the manually researched AURU visual direction — proving the agent automates the same thinking done by hand.

**Preparation:**
1. Start both terminals (API + Streamlit) before the presentation
2. Do one warm-up run the evening before to populate the cache — demo will then run in ~120s
3. Have the AURU Miro board or PDF open in a separate tab for the side-by-side comparison

**IMPORTANT — fix the proof framing.** AURU lives in the knowledge base, so a normal demo
run on "quiet luxury wellness" is *retrieving* the planted answer, not independently deriving
it. Do NOT claim "the agent independently produced the same direction" off a normal run — that
is the circular claim a sharp reviewer will dismantle. Use the **held-out benchmark** instead:
`python -m eval.run_eval --benchmark-only` removes AURU from retrieval and scores how far the
pipeline converged WITHOUT the answer. The honest, defensible line is: *"With our own research
removed from the system, the agent independently converged on the same direction at X/5."*
Lead the demo with that number + the rubric sweep (mean overall, cost, latency), then show the
side-by-side. The live "quiet luxury wellness" run is still fine as a *visual* showcase — just
don't frame the planted run as proof of automation.

**Capturing the LangSmith trace for submission:**
After the demo run completes, the sidebar shows a "LangSmith trace" link. This is a direct public link to that specific run in LangSmith — it shows every LLM call, tool call, token count, and latency across all 5 agents. Steps:
1. Click the link in the sidebar (or open the URL printed in Terminal 1)
2. Screenshot the trace tree showing all 5 agents + tool calls
3. Copy the URL from your browser address bar — this is the permanent link to include in your submission
4. The downloaded HTML report also has the trace link in its footer

---

## WHAT TO PASTE INTO THE NEXT SESSION

Paste this entire document plus say:
> "Continue from the HANDOFF. Build is complete. Current phase is demo prep — see CURRENT PHASE section for what remains. Start with whatever is marked ⬜ and closest to today's date."
