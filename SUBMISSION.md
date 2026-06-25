# Capstone Submission — Visual Direction Research Agent
### Generative AI & Agentic AI certification · Submitted by Moushmi Rao

**Repository:** https://github.com/moushmirao30/Visual-Direction-Agent
**One line:** A 5-agent CrewAI system that turns a brand-aesthetic keyword (e.g. *"quiet luxury wellness"*) into a schema-validated visual-direction report + a 5-panel AI moodboard, on entirely free infrastructure.

---

## 1. The proof (read this first)

The honest test of "does it *automate* design thinking or just *retrieve* a planted answer?" is a **de-leaked benchmark**. My own brand research (`auru_brand_research.txt`) is in the knowledge base, so a normal run on *quiet luxury wellness* would just retrieve it. The eval harness **removes that document from retrieval** and measures how far the pipeline converges without it.

**Held-out AURU convergence: 4.5 / 5** (run `eval_run_20260619_011326`). With my research removed, the agent independently re-derived the cream `#F5F1E8` ground, low-saturation sage, a taupe depth tone, an old-style-serif + humanist-sans pairing, the quiet-luxury/restraint thesis, negative space as material, and named Aesop as a benchmark. Sub-scores: positioning 5, typography 5, palette 4, benchmark overlap 4.

Full manual-vs-agent side-by-side: `DEMO_RUNBOOK.md` §5.

---

## 2. Architecture

5 agents orchestrated by CrewAI:

1. **Trend Researcher** — Tavily web search → visual pattern summary (grounded; refuses to fabricate brands)
2. **Design Theory Analyst** — RAG retrieval (ChromaDB + sentence-transformers, 89 chunks) → colour/type/spatial principles
3. **Direction Synthesiser** — merges 01+02, resolves conflicts
4. **Report Writer** — Pydantic-validated JSON report + guardrail schema gate (3 retries)
5. **Moodboard Generator** — crafts 5 image prompts; images generated in code via Cloudflare Workers AI `flux-1-schnell`

**Serving:** FastAPI endpoint → Streamlit UI (report left, moodboard grid right).
**LLMs (free, hybrid):** Gemini 2.5 Flash on synthesis agents 03/04; NVIDIA Llama-3.3-70B on 01/02/05.
**Observability:** LangSmith (tool-span tracing).

---

## 3. LangSmith evidence

**Important:** this setup traces **tool spans only** (web_search / design_knowledge_retrieval / generate_moodboard_image), not LLM calls — litellm's LangSmith logger crashes in the sync CrewAI path. Model provenance comes from the in-run `Served by:` stamp instead. The trace proves the **tool machinery executed**; the proof of *automation* is the de-leaked eval in §1.

- **Public trace link:** _(paste the LangSmith **Share** link here — the raw `/o/<org>/…` URL is private and time-filtered, so a grader can't open it)_
- **Screenshots (durable, can't expire):**
  - `submission_assets/langsmith_quiet_luxury_spans.png` — span list (Tavily + RAG + moodboard, all green)
  - `submission_assets/langsmith_web_search_detail.png` — one `web_search` span: real query in, real sourced summary out
- Captured run: `quiet luxury wellness`, 2026-06-23 ~23:11 IST.

---

## 4. Verified end-to-end runs (2026-06-23 dry run)

| Input | Routing | Images | Report | Time |
|-------|---------|--------|--------|------|
| quiet luxury wellness | hybrid (Gemini + NVIDIA) | 5/5 Cloudflare | valid, Aesop benchmark | 648s fresh |
| floral cute cafe | NVIDIA (cache hit) | 5/5 | valid | 25s cached |
| boho luxury resort | hybrid | 5/5 | valid, 3 real brands (Aman/Rosewood/Bisma) | 907s fresh |

All five agents ran clean; hybrid routing confirmed via `Served by:` stamp; Agent 01 web search grounded in real URLs (no fabrication). Fresh runs are slow (Gemini free-tier 503 retries) → demo runs from a pre-warmed cache.

---

## 5. How to run

See `README.md` (full) / `DEMO_RUNBOOK.md` (demo). Quick CLI:
```powershell
python crew.py "quiet luxury wellness"
```

---

## 6. Submission asset checklist

- [x] GitHub repo (public, `.env` excluded — verified)
- [x] README.md
- [x] DEMO_RUNBOOK.md (run-of-show + AURU side-by-side + Q&A)
- [x] Held-out eval result (4.5/5) — `eval/results/eval_run_20260619_011326.md`
- [ ] LangSmith **public share** link (replace private URL above)
- [ ] LangSmith screenshots saved to `submission_assets/`
- [ ] One exported HTML report (UI export, footer embeds trace URL)
- [ ] UI screenshot (report + moodboard grid)
