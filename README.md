# Visual Direction Research Agent

A 5-agent system that turns a single brand-aesthetic keyword — e.g. `"quiet luxury wellness"` — into a structured visual direction report **and** an AI-generated moodboard. It combines live web research, retrieval over a curated design-theory knowledge base, multi-step synthesis, schema-validated reporting, and text-to-image generation, orchestrated with CrewAI.

> **Capstone project** — Generative AI & Agentic AI certification.
> Build is complete; current phase is demo preparation.

---

## The proof (read this first)

The honest test of "does this *automate* design thinking, or just *retrieve* a planted answer?" is a **de-leaked benchmark**. My own brand research (`auru_brand_research.txt`) lives in the knowledge base, so a normal run on `"quiet luxury wellness"` would just retrieve it. To avoid that circular claim, the evaluation harness removes that document from retrieval and measures how far the pipeline converges **without** the answer.

**Held-out AURU convergence: 4.5 / 5** — with my research removed from the system, the pipeline independently re-derived the cream `#F5F1E8` ground, a low-saturation sage, a taupe depth tone, an old-style-serif + humanist-sans pairing, the quiet-luxury/restraint thesis, negative space as material, and named Aesop as a benchmark.

Sub-scores: positioning 5, typography 5, palette 4, benchmark overlap 4. Honest divergences (good for Q&A): it chose a taupe anchor over near-black charcoal, named Susanne Kaufmann / Vintner's Daughter instead of Le Labo / Bamford (real brands, same positioning — not hallucinations), and preferred cool light to the ground truth's warm morning light.

---

## What it produces

For any aesthetic keyword, the system outputs:

- **Positioning statement** — what the brand *is* visually
- **Palette direction** — named colours with hex codes, roles, and rationale
- **Typography pairing** — display + body typefaces with classifications and tracking rules
- **Spatial direction** — layout ratios, negative-space rules, photography and material direction
- **Do / Don't rules** — concrete, actionable design decisions
- **Three benchmark brands** — real brands with specific reference notes
- **A 5-panel moodboard** — palette, material, photography, typographic mood, and brand atmosphere, generated as images

The report is rendered as text on the left of the UI, the moodboard as an image grid on the right.

---

## Architecture

```
keyword
  │
  ▼
Agent 01 — Trend Researcher        live web search (Tavily) → benchmark brands,
  │                                 visual codes, colour/typography signals
  ▼
Agent 02 — Design Theory Analyst   RAG retrieval (ChromaDB) → colour psychology,
  │                                 typography logic, spatial + positioning theory
  ▼
Agent 03 — Direction Synthesiser   merges 01 + 02, resolves trend/theory conflicts
  │                                 (no tools — reasons from context)
  ▼
Agent 04 — Report Writer           structures into a validated Pydantic schema
  │                                 (guardrail: retries on schema failure)
  ▼
Agent 05 — Moodboard Generator     crafts 5 dimension-specific prompts →
  │                                 HuggingFace FLUX.1-schnell → image files
  ▼
{ report, formatted_report, moodboard_panels }
```

The pipeline passes each agent's output to the next **explicitly** (rather than via CrewAI's native context) so that output caching stays intact, the data flow is visible, and mid-pipeline errors are trivial to debug.

### Tech stack

| Layer | Choice |
|-------|--------|
| Orchestration | CrewAI (`0.80.0`) |
| Web search | Tavily |
| Vector store | ChromaDB (persistent, local) |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` |
| LLMs | Claude (Haiku for research/retrieval/prompts, Sonnet for synthesis/reporting) via LiteLLM, with free-provider routing + fallback (see below) |
| Image generation | HuggingFace `FLUX.1-schnell` |
| Validation | Pydantic v2 |
| API | FastAPI (background task + polling) |
| UI | Streamlit |
| Observability | LangSmith |

---

## Why each model

- **Agents 01, 02, 05 → Haiku-class** — research, retrieval, and prompt-crafting are summarisation-style tasks; fast and cheap is the right call.
- **Agents 03, 04 → Sonnet-class** — synthesis (identify overlap, resolve conflict, construct a narrative) and structured extraction need multi-step reasoning. Haiku tends to miss nested fields.

LiteLLM requires a provider prefix on model strings (`anthropic/claude-sonnet-4-6`, not bare names) — bare names won't resolve.

---

## Model routing & resilience

LLM construction is centralised in `utils/llm.py` (`build_llm`), which adds two layers of resilience without changing the default path:

- **Automatic fallback** — every agent's primary LLM is built with a LiteLLM `fallbacks=[...]` so a provider failure (rate limit, 5xx, network) transparently retries the same request on a free NVIDIA NIM model instead of crashing the run.
- **Free-primary mode** — `FREE_PRIMARY=nvidia` (or `groq`) flips a free provider to primary, with the other free provider as fallback. Unset = original Claude-primary behaviour, byte-for-byte unchanged.
- **Provenance stamp** — each run records which model actually served it (`Served by: …` in the run banner and the exported report), so output is never mistaken for a different provider's quality.

> **Honest caveat:** the free fallbacks are open Llama-class models, **not** Claude. If a fallback fires, that agent's output quality differs from the Claude-validated eval scores. For a graded/quality run, use Claude as primary; treat the free path as live-demo insurance.

---

## RAG knowledge base

Six curated documents, ~89 chunks in ChromaDB:

| Document | Purpose |
|----------|---------|
| `colour_theory_principles.txt` | Itten/Albers colour theory, brand colour psychology |
| `typography_pairing_rules.txt` | Typeface pairing logic, hierarchy rules |
| `spatial_design_principles.txt` | Negative space, grid, visual weight |
| `brand_positioning_frameworks.txt` | Premium / accessible / clinical / warm signal frameworks |
| `aesthetic_territories_reference.txt` | 7 contrasting aesthetic territories across colour / typography / spatial dimensions |
| `auru_brand_research.txt` | AURU brand research (held out of retrieval during the de-leaked benchmark) |

Agent 02 runs four focused retrieval queries (colour, typography, spatial, positioning) rather than one broad query, then synthesises across all four.

---

## Guardrails

The guardrail is the **schema**. Agent 04 must emit JSON conforming to the `VisualDirectionReport` Pydantic model — hex codes in `#RRGGBB` format, minimum list lengths, required fields. On a parse or validation failure it retries (up to 3×), feeding the specific error back into the prompt each time. The system never delivers an incomplete report.

A second guardrail addresses hallucination: Agent 01's prompt carries an explicit anti-fabrication mandate (name only real, well-known brands; never invent campaign titles, years, or credits), and Agent 04's schema rules drop any fabricated specifics at the output gate.

---

## Evaluation

The `eval/` harness scores the system on a fixed dataset (13 keyword cases across positioning archetypes + the AURU held-out ground truth) with an LLM-as-judge on a 5-dimension weighted rubric (positioning fit, specificity, benchmark validity, coherence, actionability) plus two auto-fail flags (hallucinated brands, internal contradiction). The judge defaults to a *different, stronger* model than the generator to avoid self-preference bias.

```powershell
python -m eval.run_eval --limit 2 --no-benchmark   # quick smoke test first
python -m eval.run_eval                             # full sweep + held-out benchmark
python -m eval.run_eval --benchmark-only            # just the de-leaked AURU proof
```

**Results (June 2026):**

- **Held-out AURU convergence: 4.5 / 5** (the headline — see top of this README).
- First clean full sweep: 12 / 13 cases scored. Per-dimension means were senior-grade (positioning 4.75, specificity 5.0, coherence 4.75, actionability 5.0), but the overall mean was dragged to 3.4 / 5 because the auto-fail cap correctly nuked 6 cases — **the eval caught a real benchmark-fabrication bug before a reviewer could.** That defect is now fixed via the two-layer grounding guardrail; re-running to capture the post-fix mean is the next evaluation step.
- Measured economics: ~$0.15 / run text-only, ~190s / run (full 13-case sweep ≈ 40 min, ≈ $2).

---

## Setup

See [`SETUP.md`](SETUP.md) for the full Windows / PowerShell setup (venv, dependencies, `.env`). In short:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m rag.ingest --reset        # build the ChromaDB knowledge base
```

Create a `.env` with your keys (`.env` is gitignored — never commit it):

```
ANTHROPIC_API_KEY=...     # primary LLM (omit + set FREE_PRIMARY to run free)
TAVILY_API_KEY=...        # web search (Agent 01)
HF_TOKEN=...              # image generation (Agent 05)
LANGCHAIN_API_KEY=...     # LangSmith observability
NVIDIA_API_KEY=...        # free fallback / free-primary
GROQ_API_KEY=...          # free fallback / free-primary
FREE_PRIMARY=nvidia       # optional: run with no Anthropic spend
```

---

## Running

### Full system (API + UI — two PowerShell terminals, venv active in both)

```powershell
# Terminal 1 — API (start first; wait for "Uvicorn running on http://127.0.0.1:8000")
python api.py

# Terminal 2 — UI
streamlit run ui/app.py
```

Use **`localhost:8501`** (the UI). `localhost:8000` is the API, not a browser interface.

### CLI (no UI)

```powershell
python crew.py "quiet luxury wellness"
python crew.py "quiet luxury wellness" --no-cache       # force fresh run
python crew.py "quiet luxury wellness" --no-moodboard   # text-only, skip images
```

---

## Project structure

```
visual-direction-agent/
├── crew.py            Pipeline orchestrator (main entry point)
├── api.py             FastAPI — background task + polling, image serving
├── agents/            Agents 01–05
├── tools/             Tavily search, ChromaDB RAG, HF FLUX image gen (@tool)
├── rag/               ingest + retriever + knowledge_base/ + chroma_db/
├── schemas/           Pydantic report schema + trend-output validation
├── utils/             llm routing, caching, observability, run logging
├── ui/                Streamlit app
├── eval/              Evaluation harness, rubric, judge, results
└── tests/             Per-agent isolation tests
```

---

## Known limitations

- **Free-model quality gap** — when running on the free fallback (no Claude credit), output is weaker than Claude: looser colour naming and thinner narratives. Fine for a working demo; use Claude for a graded run.
- **Free-tier rate limits** — Groq's free tier has a small token-per-day cap that one or two full runs can exhaust; NVIDIA NIM's limits fit a token-heavy iterative workflow better, so it's the default free primary.
- **LangSmith** traces tool spans, not individual LLM calls (a sync-CrewAI / LiteLLM constraint); model provenance comes from the run's `Served by:` stamp instead.
- **Image cold start** — the first FLUX call per session takes 30–60s; `api.py` pre-warms it on startup to avoid this during a demo.

---

## Credits

Built on CrewAI, ChromaDB, sentence-transformers, Tavily, FastAPI, Streamlit, LiteLLM, LangSmith, and HuggingFace FLUX.1-schnell. Design-theory knowledge base curated from established colour theory (Itten, Albers), editorial typography, Swiss grid systems, and brand-positioning frameworks.
