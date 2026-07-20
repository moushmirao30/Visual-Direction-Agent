# CASE STUDY PAGE — FULL CONTENT + PLACEMENT GUIDE
### Visual Direction Research Agent · Moushmi Rao
Paste order = page order. `[IMAGE]` / `[ELEMENT]` blocks tell you exactly what goes where.

---

## PAGE DESIGN SYSTEM (apply globally)

| Token | Value | Use |
|---|---|---|
| Background | `#F5F1E8` (cream) | whole page — it's your AURU-derived ground; the page itself demonstrates your taste |
| Ink | `#1A1714` | headings, body |
| Muted | `#6A6460` | captions, labels |
| Accent | `#8A9B84` (sage) | links, section markers, buttons |
| Card | `#FFFFFF` at 60% / border `#D5CFC8` | eval cards, agent cards |
| Display font | Fraunces (Google Fonts) | headlines — old-style serif, echoes the report's own typography logic |
| Body font | Inter | everything else |
| Max width | 880px single column; full-bleed only for moodboard strip + replay |

Rhythm: generous whitespace, thin `1px #D5CFC8` rules between sections. No shadows heavier than `0 1px 3px`. The page should *look like an output of the agent* — that's the meta-trick that makes designers and engineers both nod.

---
---

## 1 — HERO

**[IMAGE — full-bleed strip, top of page]** A horizontal row of 5 of your best moodboard panels from `moodboard_cache/` (pick the quiet-luxury run panels — cream/sage ones so they blend into the page background). ~240px tall, edge to edge, slight 8px gap between panels.

# I built an agent system that does a brand designer's research week in 11 minutes.

**Visual Direction Research Agent** — a 5-agent pipeline that turns one aesthetic keyword — *"quiet luxury wellness"* — into a schema-validated visual direction report and an AI-generated 5-panel moodboard. Live web research, RAG over design theory, multi-step synthesis, deterministic guardrails. Built end-to-end on **$0 infrastructure**.

**And here's the honest part most portfolios skip:** I benchmarked it against my own manual brand research — with my research *removed* from the system so it couldn't cheat — and it scored **4.5/5 convergence**.

**[ELEMENT — button row, directly under subhead]**
`▶ Watch the 2-min demo` (scrolls to §6) · `⚙ Run the pipeline replay` (scrolls to §3) · `⌥ View code on GitHub` → https://github.com/moushmirao30/Visual-Direction-Agent

**[ELEMENT — stat bar: 4 numbers in a row, big Fraunces numerals, small muted labels]**
**4.5/5** held-out eval convergence · **5** specialised agents · **648s** full cold run · **$0.00** infra cost per run

---

## 2 — THE PROBLEM

Before a brand designer touches a logo, they spend days on *visual direction*: what the category looks like right now, which colour and type moves signal the intended positioning, what the spatial language should be, who the benchmarks are. It's research → theory → synthesis → a defensible recommendation.

That workflow has a shape. Shapes can be automated.

The hard question isn't "can an LLM write design-sounding prose?" — it obviously can. The hard questions are:

1. Can a pipeline produce direction that's **specific enough to act on** — hex codes, typeface pairings, layout ratios, named benchmarks — not adjectives?
2. Can it be **trusted** — grounded in real search and real theory, schema-validated, with provenance?
3. Can you **prove** it's reasoning rather than retrieving?

This project is my answer to all three. Question 3 is the interesting one — jump to §4 if you only read one section.

---

## 3 — WHAT IT PRODUCES + HOW IT WORKS

For any keyword, the system outputs a positioning statement, a palette with hex codes and rationale, a display/body typography pairing, spatial and photography direction, ten concrete Do/Don't rules, three real benchmark brands — and a 5-panel generated moodboard (palette, material, photography, typographic mood, atmosphere).

**[ELEMENT — INTERACTIVE PIPELINE REPLAY — the centrepiece. Full-bleed section, slightly darker bg `#EDE8E2`]**
Build: a keyword picker with 2–3 chips (`quiet luxury wellness`, `artisanal spicy food truck`, + one more cached run). On click, the 5 agent nodes light up in sequence with a ~1.5s stagger and one-line status text ("Searching Tavily… 4 sources", "Retrieving 89-chunk theory base…", "Validating schema… pass"). Then the **real cached report** renders on the left and the **real 5 panels** fade in on the right. All static JSON + images — feels live, costs nothing, can't break in an interview.
Caption under it: *"This replay uses real, unedited outputs from cached runs. Nothing is mocked."*

**[ELEMENT — CLICKABLE ARCHITECTURE DIAGRAM — directly below the replay]**
Build: your existing ASCII architecture as a clean SVG — 5 nodes, keyword in top, JSON out bottom, agents 01+02 side-by-side (they run concurrently — label that). Clicking a node opens a side card with: role · model · tools · one real input/output excerpt.

Card copy for each node:

- **01 · Trend Researcher** — Llama-3.3-70B (NVIDIA NIM) + Tavily live search. Finds current visual codes and real benchmark brands. Grounding rule: refuses to fabricate brands.
- **02 · Design Theory Analyst** — Llama-3.3-70B + RAG (ChromaDB, sentence-transformers, 89 curated chunks). Retrieves colour psychology, typography logic, spatial theory. Runs concurrently with 01 — independent inputs, no reason to wait.
- **03 · Direction Synthesiser** — Gemini 2.5 Flash, **no tools**. Merges trend and theory, resolves conflicts explicitly. Conflicts are surfaced in the final report, not silently swallowed.
- **04 · Report Writer** — Gemini 2.5 Flash → Pydantic schema with a guardrail gate: invalid JSON triggers up to 3 structured retries. The report is a data contract, not prose.
- **05 · Moodboard Generator** — Llama-3.3-70B crafts 5 dimension-specific prompts; images generated concurrently via Cloudflare Workers AI `flux-1-schnell`.

Under the diagram, one line: *Serving: FastAPI → Streamlit. Observability: LangSmith tool-span tracing. Two LLM providers routed by task type — synthesis to Gemini, research/tooling to Llama — all on free tiers.*

---

## 4 — THE PROOF (the section that gets you hired)

**[ELEMENT — pull this section into a bordered card, sage left-border, slightly larger type]**

## Did it automate design thinking, or just retrieve a planted answer?

There was a trap in my own setup. My manual brand research for AURU — a real quiet-luxury wellness brand identity I developed — lives in the agent's knowledge base. So a normal run on *"quiet luxury wellness"* would just… find my answer and hand it back. Impressive-looking. Circular. Worthless as evidence.

**So the eval harness de-leaks the benchmark: it removes my research document from retrieval entirely, runs the pipeline blind, and scores how far it converges on what took me weeks to develop manually.**

**[ELEMENT — score display: one huge Fraunces "4.5 / 5" + four sub-score bars]**
Positioning **5/5** · Typography **5/5** · Palette **4/5** · Benchmark overlap **4/5**

With my research removed, the pipeline independently re-derived: the cream `#F5F1E8` ground (this page's background — you're looking at it), a low-saturation sage, a taupe depth tone, an old-style-serif + humanist-sans pairing, the quiet-luxury restraint thesis, negative space as material, and named Aesop as a benchmark.

**[ELEMENT — two-column side-by-side table: "My manual research (weeks)" vs "Agent, blind (11 minutes)" — rows: ground colour, accent, type pairing, core thesis, benchmark. Pull exact values from DEMO_RUNBOOK.md §5]**

**Where it diverged — and why I report that too:** it chose a taupe anchor over my near-black charcoal, named Susanne Kaufmann and Vintner's Daughter instead of Le Labo and Bamford (real brands, identical positioning — verified, not hallucinated), and preferred cool light to my warm morning light. Reasonable alternative judgments, not errors. An eval that only reports agreement is marketing; this one reports divergence.

---

## 5 — THE FAILURE THAT MADE IT BETTER

**[ELEMENT — bordered card, muted styling. Do not bury this section — for a hiring manager it's worth more than a second clean demo.]**

## A run that looked fine and wasn't.

A later run — *"artisanal soulful spicy food truck"* — passed every gate. Valid schema, all sections present, confident prose. And the palette was wrong in a way only a human would catch: `#FF9900` labeled "Burnt Orange" (it's pure web orange — burnt orange is `#BF5700`), `#F5DEB3` labeled "Golden Brown" (it's CSS `wheat`, a pale cream). The model had reached for memorised stock hex values and attached aspirational names. Worse: the report told itself to "use analogous colours" while pairing orange with near-complementary turquoise.

**[IMAGE — small side-by-side graphic: swatch of #FF9900 labeled "what it said: Burnt Orange" next to swatch of #BF5700 labeled "what burnt orange actually is". Brutal and instantly legible. I can generate this.]**

**The lesson: schema validation proves structure, not truth.** My guardrail could verify the JSON was shaped correctly — it couldn't verify a colour name matched its hex value, even though that check is *deterministic and free*: convert hex → HSL, compare against a colour-name lexicon, reject and retry on mismatch. Same for the analogous-colour claim — hue angles are arithmetic.

That's the next guardrail on the roadmap, and it reframed how I think about agent reliability: **every claim that can be checked in code should never be checked by a prompt.**

---

## 6 — SEE IT RUN

**[ELEMENT — embedded demo video, 16:9, poster frame = the UI with report left / moodboard right. 2–3 min screen recording of one full run: keyword typed → agents streaming → report + panels render. Caption each phase; no narration needed.]**

**[IMAGE — below video, two LangSmith screenshots side by side from `submission_assets/`:]**
- `langsmith_quiet_luxury_spans.png` — caption: *"Tool-span trace of a full run: Tavily search, RAG retrieval, 5 image generations — all green."*
- `langsmith_web_search_detail.png` — caption: *"One web_search span opened: real query in, real sourced summary out."*

One honesty line under both (keep it — it reads as integrity, not weakness): *This setup traces tool spans, not LLM calls — litellm's LangSmith logger crashes in the sync CrewAI path, so model provenance comes from an in-run serving stamp instead. The trace proves the machinery executed; the proof of automation is the de-leaked eval above.* Link the public trace: https://smith.langchain.com/public/ee0cc220-f1bd-4157-a52a-024797e80853/r

---

## 7 — ENGINEERING DECISIONS

Written as decisions-with-reasons, because that's what a hiring manager actually screens for:

**Hybrid model routing.** Synthesis agents (03, 04) run on Gemini 2.5 Flash; research and tool-driven agents (01, 02, 05) run on Llama-3.3-70B via NVIDIA NIM. Routing by task type across two free providers — with fallback — instead of one paid model for everything. Result: $0 per run.

**Schema as a contract.** The report is a Pydantic model with a guardrail gate (3 structured retries on failure). Downstream consumers — the HTML renderer, the moodboard prompter — never parse prose.

**Concurrency where the DAG allows it.** Agents 01 and 02 have independent inputs, so they run in parallel; the 5 moodboard images generate concurrently. Cold run: 648s. Cached: seconds.

**Caching as a first-class layer.** Every agent's output is content-hash cached — reruns skip unchanged upstream work. This is also what makes this page's replay possible: real outputs, zero live calls.

**Evaluation before demo polish.** The de-leaked benchmark harness, rubric, and LLM-judge (`eval/`) were built before the UI was pretty. An agent you can't score is a demo, not a system.

**Stack:** Python · CrewAI · Gemini 2.5 Flash + Llama-3.3-70B (NVIDIA NIM) · Tavily · ChromaDB + sentence-transformers · Cloudflare Workers AI (flux-1-schnell) · Pydantic · FastAPI · Streamlit · LangSmith

**[ELEMENT — render the stack as small quiet text badges, not loud logo salad]**

---

## 8 — WHAT I'D BUILD NEXT

- **Deterministic truth guardrails** — the palette validator from §5; benchmark-brand verification via search with stored source URLs; hue-angle checks on colour-harmony claims.
- **Runtime provenance** — serving stamps from response metadata rather than configuration, per-agent.
- **Human-in-the-loop checkpoint** — a designer approves/edits the synthesis before report generation; direction is a conversation, not an oracle.
- **Wider eval set** — more de-leaked ground-truth briefs across categories, so the 4.5/5 becomes a distribution, not a point.

---

## 9 — CLOSER / CTA

**[ELEMENT — centered, generous top padding, Fraunces]**

## I like building agent systems that can prove they work.

If that's the kind of engineering you need — evaluation-first, honest about failure modes, shipped on real constraints — let's talk.

`moushmirao30@gmail.com` · `GitHub ↗` · `LinkedIn ↗` · `Full eval methodology ↗ (DEMO_RUNBOOK §5)`

**[FOOTER — muted, small]** Built as the capstone for a Generative AI & Agentic AI certification · 2026 · This page's palette and typography were derived by the agent itself.

---
---

# ASSET CHECKLIST (everything the page needs)

| # | Asset | Source | Status |
|---|---|---|---|
| 1 | 5 hero moodboard panels (cream/sage run) | `moodboard_cache/` — I'll shortlist the best set | ready |
| 2 | Replay data: 2–3 cached runs (report JSON + 5 panels each) | `cache/` + `moodboard_cache/` | ready |
| 3 | Architecture SVG (clickable) | I build from your ASCII diagram | to build |
| 4 | Eval side-by-side values | `DEMO_RUNBOOK.md` §5 | ready |
| 5 | Burnt-orange comparison graphic | I generate | to build |
| 6 | Demo video (2–3 min) | **you record** — `DEMO_RUNBOOK.md` has the script | ❗ only missing piece |
| 7 | LangSmith screenshots | `submission_assets/` | ready |
| 8 | Working public links: GitHub repo, LangSmith trace | verify repo is public + keys never committed | verify |

# WHY THIS STRUCTURE ATTRACTS EMPLOYERS (the logic, so you can defend it)

1. **Outcome in the first sentence, proof in the second.** Recruiters skim; engineers verify. Both are served in the first 5 seconds.
2. **The de-leaked eval is your differentiator.** Thousands of portfolios show CrewAI demos. Almost none show *"I removed the answer from my own system and measured convergence."* That's research-grade thinking; it's the section interviewers will ask about.
3. **The failure section signals seniority.** Juniors show wins. People worth hiring show a failure, the root cause, and the systemic fix. §5 turns your worst run into your best interview story.
4. **Decisions-with-reasons beat feature lists.** §7 is phrased the way engineering interviews are scored.
5. **The page is the product.** Cream ground, serif/sans pairing, negative space — the agent's own AURU-derived direction, applied to the page about the agent. Every designer notices; the footer line makes sure everyone else does too.
