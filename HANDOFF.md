# Session Handoff — Visual Direction Research Agent
### Capstone — Generative AI & Agentic AI Certification

**Status:** Build complete and running end-to-end on FREE providers (no Anthropic credits).
**Due:** July 4, 2026 (Capstone Day) · Orientation June 28, 2026 · Today's baseline: June 23, 2026.
**Phase:** Demo prep (see [Remaining Work](#remaining-work)).

> Last verified: 3-input dry run on 2026-06-23 (~23:11–23:25) — quiet luxury wellness, floral cute cafe, boho luxury resort — all 5/5 moodboard images, valid reports, hybrid routing confirmed. Repo pushed; demo prep functionally complete (see §11).

---

## 1. Quick facts

- **What:** 5-agent system. Input = a brand aesthetic keyword → Output = a structured visual-direction report + a 5-panel AI moodboard.
- **Stack:** CrewAI (orchestration) · ChromaDB + sentence-transformers (RAG) · FastAPI + Streamlit (serving/UI) · LangSmith (tool-span tracing).
- **LLMs:** hybrid free routing — Gemini 2.5 Flash for Agents 03/04, NVIDIA Llama-3.3-70B for Agents 01/02/05. (Details §5.)
- **Images:** Cloudflare Workers AI `flux-1-schnell`. (Details §6.)
- **Project folder:** `C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent\`
- **Always** run from inside that folder with the venv active: `.\venv\Scripts\Activate.ps1`

---

## 2. The 5 agents

| # | Agent | File | Role | Tier→Provider |
|---|-------|------|------|---------------|
| 01 | Trend Researcher | `agents/agent_01_trend_researcher.py` | Tavily web search → visual pattern summary (+ anti-fabrication grounding) | fast → NVIDIA |
| 02 | Design Theory Analyst | `agents/agent_02_design_theory_analyst.py` | RAG retrieval over the KB → colour/type/spatial principles | fast → NVIDIA |
| 03 | Direction Synthesiser | `agents/agent_03_direction_synthesiser.py` | Merge 01+02, resolve conflicts → coherent direction | strong → Gemini |
| 04 | Report Writer | `agents/agent_04_report_writer.py` | Pydantic-validated JSON report + guardrails (3 retries) | strong → Gemini |
| 05 | Moodboard Generator | `agents/agent_05_moodboard_generator.py` | Crafts 5 image prompts (code generates the images) | fast → NVIDIA |

---

## 3. How to run

Two PowerShell terminals, both with the venv active.

**Terminal 1 — API (start first):**
```powershell
cd "C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent"
.\venv\Scripts\Activate.ps1
python api.py            # wait for: Uvicorn running on http://127.0.0.1:8000
```

**Terminal 2 — Streamlit UI:**
```powershell
cd "C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent"
.\venv\Scripts\Activate.ps1
streamlit run ui/app.py  # opens http://localhost:8501
```
Interact only with **localhost:8501** (the UI). `localhost:8000` is the API, not a browser page.

**CLI (no UI):**
```powershell
python crew.py "quiet luxury wellness"
python crew.py "quiet luxury wellness" --no-cache       # force fresh
python crew.py "quiet luxury wellness" --no-moodboard   # skip images
```

**API endpoints:** `POST /generate` (→ job_id) · `GET /status/{job_id}` · `GET /moodboard/{filename}` · `GET /health` · `GET /jobs`.

---

## 4. Environment (`.env`)

| Var | State | Used for |
|-----|-------|----------|
| `FREE_PRIMARY` | **`hybrid`** | LLM routing (§5) |
| `GEMINI_API_KEY` | valid (`AQ.A…`, ~53 chars) | Agents 03/04 (Gemini 2.5 Flash) |
| `NVIDIA_API_KEY` | working (free NIM) | Agents 01/02/05 (Llama-3.3-70B) |
| `GROQ_API_KEY` | working | available alt provider (not in active hybrid path) |
| `TAVILY_API_KEY` | working | Agent 01 web search |
| `IMAGE_BACKEND` | **`cloudflare`** | Agent 05 image backend (§6) |
| `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` | working | Cloudflare Workers AI image gen |
| `HF_TOKEN` | set but **402 (paid)** — no longer used for images | (legacy; see §6) |
| `ANTHROPIC_API_KEY` | set, **out of credits** — not called while `FREE_PRIMARY` is set | graded-eval path only |
| `LANGCHAIN_API_KEY` / `LANGCHAIN_TRACING_V2=true` / `LANGCHAIN_PROJECT` | set | LangSmith tool-span tracing |

> `.env` edits must reach the **Windows** file *and* not be overridden by a shell var: `load_dotenv()` does NOT override a `FREE_PRIMARY` already set in the PowerShell session. If a change doesn't "take," run `$env:FREE_PRIMARY="hybrid"` in the run terminal and re-check the `Served by:` banner.

---

## 5. LLM routing (`utils/llm.py`)

Every agent's LLM is built via `build_llm(model, tier)`. `FREE_PRIMARY` selects the provider:

- **`hybrid` (current):** strong tier (03, 04) → Gemini 2.5 Flash; fast tier (01, 02, 05) → NVIDIA Llama-3.3-70B. Per-tier override: `FREE_PRIMARY_FAST` / `FREE_PRIMARY_STRONG`. Logic in `_primary_for_tier()` (unit-tested 8/8).
- Other values: `gemini` (all agents on Gemini — **crashes a full run**, see quota below), `nvidia`, `groq`. Unset = Anthropic-primary (graded-eval path, needs credits).

**Why hybrid:** Gemini gives much better text (Agent 01 309s→81s when on Gemini; cleaner colour names, 100–150-word narratives) but its free quota is only **~20 requests/DAY per model** (`gemini-2.5-flash`) on this project — a full single-provider Gemini run exceeds 20 calls and dies with `429 RESOURCE_EXHAUSTED`. Hybrid puts only the two cheap, reviewer-visible agents (03/04, ~3–5 calls) on Gemini and the call-heavy ones on NVIDIA, so a run never hits the wall and Gemini quality lands where it matters.

**Resilience reality (important):**
- litellm's `fallbacks=[...]` does **NOT** reliably fire in this CrewAI sync path — confirmed: a Gemini 503 failed over to neither NVIDIA nor a 2nd Gemini model. Treat the `fallbacks` entries as documentation of intent, not guaranteed failover.
- What actually provides resilience: **CrewAI's own agent retry** (recovers transient 503s) + hybrid keeping Gemini calls low.
- **Gemini free-tier 503 "high demand" is frequent** and mainly costs TIME: `run_20260623_212303` hit 10× 503 on Agent 03, ballooning it to 188s (vs ~30s) before recovering. → For the demo, run from cache (warm-up the night before), not fresh.
- A hard Gemini outage/quota hit is only covered by an app-level try/except that rebuilds on NVIDIA — **deliberately not built** (system works without it; don't add pre-demo).

**Other facts:**
- Model strings need a litellm **provider prefix**: `gemini/gemini-2.5-flash`, `nvidia_nim/meta/llama-3.3-70b-instruct`, `anthropic/claude-sonnet-4-6`. Bare names won't resolve.
- NVIDIA key is mirrored `NVIDIA_API_KEY`→`NVIDIA_NIM_API_KEY` (litellm reads the latter). Default NVIDIA model is 70B for both tiers (the old `llama-3.1-405b` was retired → 404).
- **Provenance stamp:** every run prints `Served by:` (e.g. `gemini/… (configured), nvidia_nim/… (configured)`) via `served_models()` in `utils/llm.py` — this is the source of truth for which provider ran, since LangSmith does not capture LLM calls.

---

## 6. Image generation (`tools/image_gen_tool.py`)

**Backend: Cloudflare Workers AI `flux-1-schnell`** — free tier ~100k images/day. ✅ Verified on 2 keywords (5/5 panels, real PNGs 0.9–1.8 MB).

- Selected via `IMAGE_BACKEND` env; single swap-point is `generate_image()`. `generate_via_cloudflare()` POSTs to `accounts/{id}/ai/run/@cf/black-forest-labs/flux-1-schnell` (body: `prompt`, `steps`≤8, `seed`), decodes the base64 JPEG in `result.image` → saves PNG to `moodboard_cache/`.
- Needs `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` (token scoped "Workers AI"). Optional: `CLOUDFLARE_IMAGE_MODEL`, `CLOUDFLARE_IMAGE_STEPS` (default 6).

**Agent 05 is prompt-only (fabrication fix):** it crafts the 5 prompts; `run_moodboard_generator()` generates images in CODE via `generate_images_batch()`. The model can no longer report URLs — each panel URL is a real local path or `""`, and `""` shows an honest "⚠ Image generation unavailable" in the UI (previously the 70B fabricated `https://moodboard.com/...` links → phantom panels). `parse_moodboard_output()` parses prompts only.

**Rejected/dead backends (don't retry without reason):** HuggingFace FLUX → now **402 Payment Required**; Pollinations.ai → key-gated + rate-limited; Google Gemini *image* → 0 free quota (separate from the Gemini *text* tier we use); NVIDIA FLUX.2-klein-4B → rejected because its **content filter blocks benign prompts** (e.g. "hands holding a ceramic bowl"), which kills wellness/beauty imagery. (A/B evidence kept in `eval/ab_images/comparison.html`.)

---

## 7. RAG knowledge base (`rag/`)

`rag/ingest.py` populates ChromaDB (collection `visual_direction_kb`, embeddings `all-MiniLM-L6-v2`); `rag/retriever.py` does retrieval + session dedup. **Current: 89 chunks across 6 docs.**

| File | Purpose |
|------|---------|
| `auru_brand_research.txt` | AURU — quiet-luxury-wellness territory (the demo ground truth) |
| `colour_theory_principles.txt` | Itten/Albers, brand colour psychology |
| `typography_pairing_rules.txt` | Typeface pairing + hierarchy |
| `spatial_design_principles.txt` | Negative space, grid, visual weight |
| `brand_positioning_frameworks.txt` | Premium/accessible/clinical/warm signals |
| `aesthetic_territories_reference.txt` | 7 contrasting aesthetic territories |

**After any KB change, re-ingest:**
```powershell
python -m rag.ingest --reset
python -c "import chromadb; c=chromadb.PersistentClient(path='rag/chroma_db'); print(c.get_collection('visual_direction_kb').count())"
```

---

## 8. Evaluation harness (`eval/`) — the demo proof

**Why it exists:** AURU lives in the KB, so a normal "quiet luxury wellness" run *retrieves* a planted answer — not proof of automation. The eval removes AURU from retrieval (`EVAL_EXCLUDE_SOURCES` in `rag/retriever.py`; behaviour byte-for-byte unchanged when unset) and measures how far the pipeline converges WITHOUT it.

**HEADLINE (banked, run `eval_run_20260619_011326`): held-out AURU convergence = 4.5 / 5.** With AURU removed, the pipeline independently re-derived cream `#F5F1E8`, low-sat sage, a taupe depth tone, old-style-serif + humanist-sans pairing, the restraint thesis, negative-space-as-material, and named Aesop. Use this as the demo headline: *"With our own research removed, the agent independently converged on the same direction at 4.5/5."*

**Rubric sweep (13 keywords):** 5 weighted dimensions; positioning 4.75, specificity 5.0, coherence 4.75, actionability 5.0, benchmark validity 3.5. First clean sweep mean 3.4/5 — dragged down by an auto-fail cap that **caught Agent 01 fabricating benchmark brands** (fake campaign names). Fixed via grounding rules in Agent 01 + a schema gate in Agent 04. ~$0.15 + ~190s per text-only run; full sweep ≈ 40 min.

**Run it:**
```powershell
python -m eval.run_eval --limit 2 --no-benchmark   # quick smoke
python -m eval.run_eval                             # full sweep + held-out
python -m eval.run_eval --benchmark-only            # just the de-leaked AURU proof
```
Judge defaults to `claude-opus-4-8` (different/stronger than the generator, avoids self-bias) → **needs Anthropic credits**. The post-grounding-fix mean has NOT been re-measured (blocked on credits).

---

## 9. Gotchas / things to watch

- **venv must be active.** `ModuleNotFoundError: tavily` = wrong interpreter. Confirm: `python -c "import sys; print(sys.executable)"` ends in `venv\Scripts\python.exe`.
- **`crewai-tools` is NOT installed** (conflicts with `crewai==0.80.0`). Tools use the native `@tool` decorator + provider SDKs. Don't add it.
- **API binds `127.0.0.1`** — use `localhost:8000` / `localhost:8501`; `0.0.0.0` times out in a browser.
- **Cache TTL 24h** (Agents 01–04). Stale cache returns the same output regardless of keyword — force fresh with `--no-cache` or the UI "Use cached outputs" toggle.
- **LangSmith** traces TOOL spans only; LLM-call tracing is NOT viable in this sync CrewAI setup (litellm's LangsmithLogger needs an event loop → crashes). **Do not re-add** the litellm `"langsmith"` callback. Provenance comes from the `Served by:` stamp instead.
- **Windows path spaces** — always quote paths in PowerShell (handled throughout the code).
- **`api.py` FLUX warm-up — REMOVED (Jun 23).** It pre-warmed HuggingFace FLUX on startup; obsolete since the Cloudflare switch (hosted API, no cold start) and HF now 402s. The `_warmup_flux()` function and its `@app.on_event("startup")` hook are gone (breadcrumb comment left in `api.py`). `_executor`/`asyncio` remain — still used by the `/generate` background task.

---

## 10. Demo plan (June 28)

**Show:** the full pipeline live in the Streamlit UI, beside the manually-researched AURU direction.

**Prep:** start both terminals first; do a **warm-up run the evening before** to populate the cache (demo then runs from cache in ~120s and avoids the Gemini-503 time tax); have the AURU Miro board / PDF open for the side-by-side.

**Proof framing (critical):** do NOT claim the planted "quiet luxury wellness" run proves automation — AURU is in the KB. Lead with the **held-out benchmark** number instead (`python -m eval.run_eval --benchmark-only`): *"With our own research removed, the agent independently converged at 4.5/5,"* then show the live run as a visual showcase.

**LangSmith capture:** after a run, click the sidebar "LangSmith trace" link → screenshot the trace tree → copy the URL for the submission (also embedded in the HTML report export footer).

---

## 11. Remaining work

| Item | Status |
|------|--------|
| README.md | ✅ **done** — committed + pushed |
| Demo script (timed dry run) | ✅ **done** → `DEMO_RUNBOOK.md` (run-of-show, 3 inputs, recovery playbook); timings corrected to measured fresh-run numbers |
| AURU side-by-side assets | ✅ **done** → side-by-side table in `DEMO_RUNBOOK.md` §5 (manual vs de-leaked agent, 4.5/5) |
| Commit locally + push to GitHub | ✅ **done** — repo: https://github.com/moushmirao30/Visual-Direction-Agent · `.env` confirmed absent on remote · remote URL updated after repo rename |
| Test all 3 demo inputs end-to-end | ✅ **done** (2026-06-23 ~23:11–23:25): quiet luxury wellness 5/5 imgs / hybrid / 648s · floral cute cafe 5/5 / cache hit / 25s · boho luxury resort 5/5 / hybrid / 907s. All valid reports, web search grounded, no fabrication. ⚠ fresh runs 11–15 min → **warm cache before demo** |
| LangSmith trace captured for submission | ✅ **done** — screenshots + trace in `SUBMISSION.md`. ⚠ **TODO before July 4:** replace the private `/o/<org>/…` URL with a **public Share link** (private link won't open for graders + is 7d time-filtered) |
| `SUBMISSION.md` (graded-submission index) | ✅ **done** — added + pushed |
| Re-run `eval.run_eval` for post-grounding-fix mean (clear `cache/` first) | ⬜ **blocked on Anthropic credits** (judge is Claude) |
| Feature freeze + final push | ⬜ — code is demo-stable; freeze after final demo dry run |

**Open items only:** (1) swap LangSmith private URL → public Share link in `SUBMISSION.md`; (2) eval re-run (blocked on Anthropic credits); (3) optional UI screenshot + exported HTML report for submission; (4) night-before cache warm-up before the June 28 demo.

**Built + working:** all 5 agents, RAG (89 chunks), API, UI, hybrid LLM routing, Cloudflare images, file logging (`logs/run_<ts>_<slug>.log`), provenance stamp, eval harness (held-out 4.5/5 banked), README, **`DEMO_RUNBOOK.md` (run-of-show + AURU side-by-side + Q&A + recovery playbook)**.

---

## 12. Key decisions & lessons (compressed history)

- **Free-LLM journey → hybrid.** Groq free tier too small (12k tokens/min, 100k/day — exhausts in ~1 run). NVIDIA 70B completes but text is weaker (loose colour names, thin narratives). Gemini 2.5 Flash is strongest but 20 req/day. → **Hybrid** (Gemini on 03/04, NVIDIA on 01/02/05) is the resolution.
- **litellm `fallbacks` are unreliable** in CrewAI's sync path — proven by live 503s that didn't fail over. Resilience = CrewAI retry + low Gemini call count. (Flash-Lite fallback was added then removed as dead weight.)
- **Image backends keep dying free:** HF→402, Pollinations→gated, Gemini-image→0, NVIDIA-klein→content-filter. Cloudflare `flux-1-schnell` is the current free, reliable answer.
- **Agent 05 fabricated URLs** when image gen failed → refactored to prompt-only + code-side generation so failures are honest.
- **Agent 01 fabricated benchmark brands** → caught by the eval auto-fail, fixed with grounding rules (Agent 01) + schema gate (Agent 04). Post-fix mean not yet re-measured.
- **LangSmith LLM-call tracing not viable** here — tool spans only; provenance via the served-model stamp.

---

## 13. Paste into the next session

> "Continue from the HANDOFF. Build is complete; running free on hybrid LLM routing (Gemini 03/04, NVIDIA 01/02/05) + Cloudflare images. Phase is demo prep — see §11 Remaining Work and start with whatever's ⬜ and closest to today."
