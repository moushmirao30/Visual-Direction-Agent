# Demo Runbook — Visual Direction Research Agent
### Capstone · Gen AI & Agentic AI · Demo target: June 28, 2026 (Orientation) · Final due July 4

This is the run-of-show for the live demo. Read it once end-to-end the day before, then drive from the **Run-of-show** section on the day. The single proof you lead with is the **held-out 4.5/5**, not the planted "quiet luxury wellness" run.

---

## 0. The one slide of framing (say this out loud, don't skip it)

> "My own brand research, AURU, lives in the knowledge base. So a normal run on *quiet luxury wellness* would just **retrieve** my answer — that proves nothing about automation. So I removed AURU from retrieval and measured how far the agent re-derives the same direction **without** it. It converged at **4.5 out of 5** — same cream, same sage, same taupe, same serif+sans logic, same restraint thesis, and it independently named Aesop. *That* is the proof. The live run you're about to see is the showcase."

If you only get one sentence out before something breaks: it's the held-out 4.5/5.

---

## 1. Pre-flight — the evening before (do NOT skip)

The Gemini free tier throws frequent 503 "high demand" errors that don't fail the run but balloon it. **Measured on this machine (June 23 dry run): a genuinely fresh run takes 11–15 minutes** (`quiet luxury wellness` 648s, `boho luxury resort` 907s) — dominated by Gemini 503 retries + a slow NVIDIA Agent 01 (400–525s). A **cached** run is ~25s. So warming the cache the night before is **mandatory, not optional** — a cold run live is unwatchable. Budget ~40 min for the warm-up itself.

Night-before checklist:

- [ ] `git status` clean-ish / committed (so a live edit can't break the demo).
- [ ] Confirm `.env` keys still valid: `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `TAVILY_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`.
- [ ] **Warm the cache** for all three demo inputs (fresh, so cache is populated):
  ```powershell
  python crew.py "quiet luxury wellness"
  python crew.py "boho luxury resort"
  python crew.py "floral cute cafe"
  ```
- [ ] Confirm each printed a `Served by:` banner with **both** `gemini/...` and `nvidia_nim/...`. If it says Anthropic, run `$env:FREE_PRIMARY="hybrid"` and re-run.
- [ ] Confirm `moodboard_cache/` got fresh `panel_*.png` for each (5 per run).
- [ ] Open the AURU side-by-side (Section 5 below, or your Miro/PDF) in a tab.
- [ ] Capture one LangSmith trace URL now (so submission isn't gated on the live run): run once, click sidebar "LangSmith trace", screenshot the tree, copy the URL.

---

## 2. Setup on the day — two terminals, both with venv active

```powershell
# Terminal 1 — API (start FIRST, wait for "Uvicorn running on http://127.0.0.1:8000")
cd "C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent"
.\venv\Scripts\Activate.ps1
python api.py

# Terminal 2 — UI
cd "C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent"
.\venv\Scripts\Activate.ps1
streamlit run ui/app.py     # opens http://localhost:8501
```

Interact only with **localhost:8501**. In the UI, keep **"Use cached outputs" ON** for the demo. Quick health check before you present: open `http://localhost:8000/health` once — expect `200`.

---

## 3. Run-of-show (target ~8 minutes)

| Time | What you do | What you say |
|------|-------------|--------------|
| 0:00 | Slide / verbal: the problem | "Brands pay agencies weeks for a visual direction. Can a multi-agent system do the first-draft thinking in two minutes?" |
| 0:45 | Show the architecture (README diagram) | "Five agents: web research, RAG over design theory, synthesis, a schema-validated report, and a moodboard generator. CrewAI orchestrates them." |
| 1:30 | **The proof first** — show Section 5 side-by-side | Deliver the Section 0 framing. Land the **held-out 4.5/5**. |
| 3:00 | Live run #1 in UI — `quiet luxury wellness` (cached) | "Now the live system. Report streams on the left, moodboard on the right." |
| 4:30 | Walk the output: positioning → palette hexes → type pairing → do/don'ts → 3 benchmark brands → 5 moodboard panels | "Notice it's concrete — named hexes, tracking values, real benchmark brands, not mush." |
| 6:00 | Live run #2 — `floral cute cafe` (cached) | "Different territory, to show range — warm, playful, totally different palette and type." |
| 7:00 | Show provenance + tracing | "`Served by:` proves which free providers ran; here's the LangSmith trace of the tool spans." |
| 7:30 | Close | "Removed my own answer, it re-derived it at 4.5/5, end to end, on free infrastructure. Questions?" |

Keep run #3 (`boho luxury resort`) in your pocket as a spare if asked for another.

---

## 4. The three demo inputs

| Input | Why it's in the demo | Expected output character |
|-------|----------------------|---------------------------|
| `quiet luxury wellness` | The proof anchor — maps to AURU side-by-side | Cream/taupe/sage, serif+humanist-sans, restraint, Aesop-adjacent benchmarks |
| `floral cute cafe` | Range + safe showcase (last verified 5/5 images, run `run_20260623_212303`) | Warm, soft, playful palette; rounded/script display; opposite of wellness |
| `boho luxury resort` | Spare / third territory if asked | Earthy, textural, sun-warm; rattan/linen materials |

All three already have warm cache + prior full runs in `logs/`. **Don't introduce a brand-new untested keyword live** — fresh keyword = no cache = full Gemini-503 time tax in front of the audience.

---

## 5. AURU side-by-side — manual vs. de-leaked agent (the proof asset)

Manual ground truth = `rag/knowledge_base/auru_brand_research.txt`. Agent column = held-out run `eval_run_20260619_011326` (AURU removed from retrieval).

| Dimension | My manual AURU direction | Agent (AURU removed) | Verdict |
|-----------|--------------------------|----------------------|---------|
| **Background base** | `#F5F1E8` Warm Cream | `#F5F1E8` Warm Cream — exact match, dominant ground | ✅ Exact |
| **Secondary / accent** | `#6F7563` Sage Grey-Green | Low-saturation sage as restrained secondary | ✅ Match |
| **Depth tone** | `#9B8C7D` Taupe | Taupe as depth/structure tone | ✅ Match |
| **Palette character** | Low-sat warm neutrals, no botanical green | Low-sat warm-neutral, explicitly avoids high-sat botanical green | ✅ Match |
| **Anchor / type colour** | `#2B2B2B` Deep Charcoal (near-black) | Replaced near-black with taupe — **weaker anchor** | ⚠ Divergence |
| **Typography** | Cormorant Garamond / DM Serif + DM Sans / Inter | Sabon (old-style serif) + Source Sans Pro (humanist sans) | ✅ Same class |
| **Type detail** | Generous heading tracking, lowercase wordmark | Generous heading tracking, restrained weights, lowercase wordmark | ✅ Match |
| **Thesis** | Quiet luxury, restraint, quality through absence | Quiet luxury / restraint / quality through absence | ✅ Match |
| **Space** | Negative space as material, spacious grids | Negative space as active material | ✅ Match |
| **Photography** | Hands, product on surface, close-up, no faces | Close-up product/hands/texture, no faces, no lifestyle | ✅ Match |
| **Materials** | Matte paper grain, brushed stone, no gloss | Uncoated/matte, no gloss/foil/metallic | ✅ Match |
| **Benchmarks** | Aesop-coded territory (Le Labo, Bamford implied) | Named Aesop ✓; substituted Susanne Kaufmann, Vintner's Daughter (real, same positioning) | ⚠ Partial |
| **Light** | Warm morning light on limestone/linen | Mandated cool-to-neutral light | ⚠ Divergence |

**Convergence: 4.5 / 5** (palette 4, typography 5, positioning 5, benchmark overlap 4).

The three ⚠ rows are your **best Q&A material** — they're principled divergences, not hallucinations (see below).

---

## 6. Anticipated Q&A (lead with the divergences — they make you look honest)

**"Isn't 4.5/5 just because your research is in the database?"**
No — that's exactly why I removed it. The 4.5 is the *de-leaked* run with AURU pulled from retrieval. The planted run isn't my proof.

**"Where did it disagree with you, and is that a failure?"**
Three places, all defensible: it chose a taupe anchor over my near-black charcoal; it named Susanne Kaufmann / Vintner's Daughter instead of Le Labo / Bamford (real brands, identical positioning — not invented); and it preferred cool light to my warm morning light. Different reasonable calls, not errors. The judge docked positioning a point for the aggressive dark-vs-warm read — fair.

**"How do you know it isn't hallucinating brands?"**
Two layers caught that early: a grounding rule in Agent 01 (web-search-backed, no invented campaigns) and a schema gate in Agent 04. The eval auto-fail for hallucinated brands reads **0** on the banked run.

**"What's it running on / what does it cost?"**
Entirely free infrastructure: Gemini 2.5 Flash on the two synthesis agents, NVIDIA Llama-3.3-70B on the research-heavy ones, Cloudflare Workers AI for images. ~$0.02–0.15 per text run in the eval, $0 in the live free path.

**"Why split the models (hybrid)?"**
Gemini gives the best text but only ~20 requests/day free. Hybrid puts only the 2 reviewer-visible agents on Gemini and the call-heavy ones on NVIDIA, so a full run never hits the quota wall.

**"Why CrewAI / why 5 agents not one prompt?"**
Separation of concerns + a critique boundary: research, theory, synthesis, validation, and generation are independently testable and independently fail-able. The schema gate on Agent 04 is the guardrail that the single-prompt version can't enforce.

**"Is the moodboard real or stock?"**
Generated text-to-image via Cloudflare FLUX-schnell from prompts Agent 05 writes. If generation fails, the panel honestly shows "image unavailable" — earlier it fabricated URLs, which I fixed by moving generation into code.

---

## 7. If something breaks — recovery playbook

| Symptom | Cause | Do this |
|---------|-------|---------|
| Run hangs ~3 min on Agent 03 | Gemini 503 time tax | You're on cache so this shouldn't happen; if it does, narrate it ("free-tier throttling") and wait — it recovers. |
| `Served by:` says Anthropic | shell var override | `$env:FREE_PRIMARY="hybrid"` then re-run. |
| `ModuleNotFoundError: tavily` | wrong interpreter | venv not active — `.\venv\Scripts\Activate.ps1`. |
| Browser times out on `localhost:8000` | that's the API, not the UI | Use **localhost:8501**. |
| Moodboard panel shows "unavailable" | Cloudflare hiccup | Honest by design — call it out, the report still stands; show a cached prior run's panels. |
| Stale/identical output across keywords | 24h cache returning same blob | Toggle "Use cached outputs" off for one run, or `--no-cache`. |
| Whole UI dead | API not up | Restart Terminal 1, wait for the Uvicorn line, refresh. |

**Ultimate fallback:** if live is hopeless, present Section 5 (the side-by-side) + a screenshot of a prior `run_20260623_212303` output. The proof is the 4.5/5, and that's a banked number — it does not depend on anything running on the day.

---

## 8. Submission capture (for July 4, grab during/after the demo)

- [ ] LangSmith trace URL (sidebar link + screenshot of the span tree).
- [ ] One exported HTML report (footer embeds the trace URL).
- [ ] Screenshot: UI with report + moodboard grid.
- [ ] Screenshot: a `Served by:` banner (provenance).
- [ ] This runbook + README + the side-by-side table.
