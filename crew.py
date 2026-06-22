"""
crew.py
Visual Direction Research Agent — Full Pipeline Orchestrator

Entry point for the entire 5-agent system. Called by:
  - api.py (FastAPI endpoint)
  - ui/app.py (Streamlit UI)
  - Direct CLI: python crew.py "quiet luxury wellness"

Pipeline flow:
  keyword
    → Agent 01 (Trend Researcher)    — live web search, Tavily
    → Agent 02 (Design Theory)       — RAG retrieval, ChromaDB
    → Agent 03 (Synthesiser)         — merge 01+02, resolve conflicts
    → Agent 04 (Report Writer)       — structure into validated Pydantic schema
    → Agent 05 (Moodboard Generator) — craft prompts + generate images via HF FLUX
    → {report, formatted_report, moodboard_panels}

Why explicit sequential passing (not CrewAI native context)?
  Agents 01 and 02 have output caching. CrewAI's internal context mechanism
  bypasses those runners and would re-run both agents every time. Explicit
  passing keeps caching intact, makes the data flow visible, and makes
  mid-pipeline errors trivially debuggable.
"""

import sys
import time
import hashlib
from dotenv import load_dotenv

from utils.observability import setup_langsmith
from utils.cache import load_from_cache, save_to_cache
from utils.llm import served_models, reset_served_models
from schemas.report_schema import VisualDirectionReport

load_dotenv()


# ── Input validation ──────────────────────────────────────────────────────────

def validate_keyword(raw: str) -> tuple[bool, str]:
    """
    Validates and normalises the aesthetic keyword input.

    Returns (True, cleaned_keyword) on success.
    Returns (False, error_message) on failure.
    """
    keyword = raw.strip()

    if not keyword:
        return False, "Aesthetic keyword cannot be empty."

    if len(keyword) < 3:
        return False, f"Keyword too short ({len(keyword)} chars). Minimum 3 characters."

    if len(keyword) > 200:
        return False, (
            f"Keyword too long ({len(keyword)} chars). Keep it under 200 characters. "
            "Try something like: 'quiet luxury wellness' or 'bold brutalist tech'."
        )

    # Basic sanity — reject if it looks like code injection
    suspicious = ["<script", "SELECT ", "DROP TABLE", "{{", "}}"]
    for pattern in suspicious:
        if pattern.lower() in keyword.lower():
            return False, "Invalid input. Please enter a brand aesthetic description."

    return True, keyword


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_visual_direction_pipeline(
    aesthetic_keyword: str,
    use_cache: bool = True,
    skip_moodboard: bool = False,
) -> dict:
    """
    Runs the full 5-agent Visual Direction pipeline end-to-end.

    Args:
        aesthetic_keyword: Brand aesthetic input (e.g. "quiet luxury wellness")
        use_cache:         Use cached Agent 01 + 02 outputs when available (default True)
        skip_moodboard:    Skip Agent 05 image generation — useful for text-only runs

    Returns:
        {
            "keyword":          str,
            "report":           VisualDirectionReport,   # validated Pydantic object
            "formatted_report": str,                     # for Streamlit text panel
            "moodboard_panels": list[dict],              # for Streamlit image grid
            "langsmith_url":    str | None,              # trace URL if LangSmith active
            "timings":          dict,                    # per-agent run times (seconds)
        }

    Raises:
        ValueError: if keyword fails validation
        RuntimeError: if Agent 04 schema validation fails (malformed report)
    """
    # ── Setup ──────────────────────────────────────────────────────────────
    langsmith_active = setup_langsmith()
    reset_served_models()  # isolate provenance capture to this run

    valid, keyword = validate_keyword(aesthetic_keyword)
    if not valid:
        raise ValueError(keyword)

    timings = {}
    pipeline_start = time.time()

    _banner(f"Visual Direction Pipeline — '{keyword}'")

    # ── Agent 01 — Trend Researcher ───────────────────────────────────────
    _step("01", "Trend Researcher", "Live web search via Tavily")
    t0 = time.time()

    from agents.agent_01_trend_researcher import run_trend_research
    trend_output = run_trend_research(keyword, use_cache=use_cache)
    timings["agent_01"] = round(time.time() - t0, 1)
    _done("01", timings["agent_01"])

    # ── Agent 02 — Design Theory Analyst ─────────────────────────────────
    _step("02", "Design Theory Analyst", "RAG retrieval over knowledge base")
    t0 = time.time()

    from agents.agent_02_design_theory_analyst import run_theory_analysis
    theory_output = run_theory_analysis(keyword, use_cache=use_cache)
    timings["agent_02"] = round(time.time() - t0, 1)
    _done("02", timings["agent_02"])

    # ── Agent 03 — Direction Synthesiser ─────────────────────────────────
    _step("03", "Direction Synthesiser", "Merging trend + theory, resolving conflicts")
    t0 = time.time()

    from agents.agent_03_direction_synthesiser import run_synthesis

    # Cache key: hash of the two inputs — if 01+02 outputs haven't changed,
    # there's no reason to re-synthesise (saves ~1 Sonnet call per repeat run)
    _key_03 = _content_key(keyword, trend_output, theory_output)
    synthesis_output = load_from_cache("agent_03", _key_03) if use_cache else None
    if synthesis_output:
        timings["agent_03"] = 0.0
        print("[CACHE] Agent 03 hit — skipping synthesis")
    else:
        synthesis_output = run_synthesis(keyword, trend_output, theory_output)
        save_to_cache("agent_03", _key_03, synthesis_output)
        timings["agent_03"] = round(time.time() - t0, 1)
    _done("03", timings["agent_03"])

    # ── Agent 04 — Report Writer ──────────────────────────────────────────
    _step("04", "Report Writer", "Structuring into validated schema")
    t0 = time.time()

    from agents.agent_04_report_writer import run_report_writer

    # Cache key: hash of synthesis — if synthesis hasn't changed,
    # the validated report won't change either (saves ~1 Sonnet call per repeat run)
    _key_04 = _content_key(keyword, synthesis_output)
    _cached_report_raw = load_from_cache("agent_04", _key_04) if use_cache else None
    if _cached_report_raw:
        # Re-parse the cached JSON through the same validation path
        from agents.agent_04_report_writer import _parse_and_validate, format_report
        report, _err = _parse_and_validate(_cached_report_raw)
        if report:
            formatted_report = format_report(report)
            error = None
            timings["agent_04"] = 0.0
            print("[CACHE] Agent 04 hit — skipping report writing")
        else:
            # Cache entry corrupted — fall through to fresh run
            print(f"[CACHE] Agent 04 cache invalid ({_err}) — re-running")
            _cached_report_raw = None

    if not _cached_report_raw:
        report, formatted_report, error = run_report_writer(keyword, synthesis_output)
        if report:
            # Cache the raw JSON output for future runs
            import json as _json
            save_to_cache("agent_04", _key_04, _json.dumps(report.model_dump()))
        timings["agent_04"] = round(time.time() - t0, 1)

    if error:
        raise RuntimeError(
            f"Agent 04 schema validation failed: {error}\n"
            "This usually means the synthesis output was incomplete. "
            "Try re-running with use_cache=False to force fresh agent runs."
        )

    _done("04", timings["agent_04"])

    # ── Agent 05 — Moodboard Generator ───────────────────────────────────
    panels = []
    if not skip_moodboard:
        _step("05", "Moodboard Generator", "Crafting prompts + generating 5 images via FLUX")
        t0 = time.time()

        from agents.agent_05_moodboard_generator import run_moodboard_generator

        # Pass the formatted report as context (capped to avoid prompt overflow)
        report_summary = _build_report_summary(report)
        panels, _ = run_moodboard_generator(report_summary)
        timings["agent_05"] = round(time.time() - t0, 1)
        _done("05", timings["agent_05"])
    else:
        print("[PIPELINE] Agent 05 skipped (skip_moodboard=True)")

    # ── Summary ───────────────────────────────────────────────────────────
    total = round(time.time() - pipeline_start, 1)
    timings["total"] = total

    panels_generated = len([p for p in panels if p.get("url") and "ERROR" not in p.get("url", "")])
    served = served_models()
    _banner(
        f"Pipeline complete — '{keyword}'\n"
        f"  Palette swatches: {len(report.palette)}\n"
        f"  Do/Don't rules:   {len(report.do_rules)} / {len(report.dont_rules)}\n"
        f"  Benchmark brands: {len(report.benchmark_brands)}\n"
        f"  Moodboard panels: {panels_generated}/5\n"
        f"  Served by:        {', '.join(served) or 'unknown'}\n"
        f"  Total time:       {total}s"
    )

    from utils.observability import get_langsmith_run_url
    langsmith_url = get_langsmith_run_url() if langsmith_active else None

    return {
        "keyword":          keyword,
        "report":           report,
        "formatted_report": formatted_report,
        "moodboard_panels": panels,
        "langsmith_url":    langsmith_url,
        "served_models":    served,
        "timings":          timings,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_report_summary(report: VisualDirectionReport) -> str:
    """
    Builds a concise report summary for Agent 05's moodboard prompt context.
    Keeps token use low while giving the agent the essential visual direction.
    """
    palette_str = "\n".join(
        f"- {s.name} {s.hex_code} ({s.role})" for s in report.palette
    )
    brands_str = "\n".join(
        f"- {b.name}: {b.reference_note}" for b in report.benchmark_brands
    )
    photography_str = "\n".join(f"- {d}" for d in report.photography_direction)

    return (
        f"POSITIONING: {report.positioning_statement}\n\n"
        f"PALETTE:\n{palette_str}\n\n"
        f"TYPOGRAPHY:\n"
        f"- Display: {report.typography.display_typeface}\n"
        f"- Body: {report.typography.body_typeface}\n\n"
        f"SPATIAL:\n"
        f"- {report.layout_approach}\n"
        f"- {report.negative_space_rule}\n\n"
        f"PHOTOGRAPHY:\n{photography_str}\n\n"
        f"MATERIALS: {report.materials}\n\n"
        f"BENCHMARK BRANDS:\n{brands_str}\n\n"
        f"VISUAL NARRATIVE: {report.visual_narrative}"
    )


def _content_key(*parts: str) -> str:
    """
    Deterministic 16-char key from one or more content strings.
    Used to cache Agents 03+04 based on their actual input content,
    not just the keyword — so a cache hit only occurs when the upstream
    outputs genuinely haven't changed.
    """
    combined = "::".join(p.strip() for p in parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _banner(msg: str) -> None:
    print(f"\n{'='*60}")
    for line in msg.strip().split("\n"):
        print(f"  {line}")
    print(f"{'='*60}")


def _step(num: str, name: str, detail: str) -> None:
    print(f"\n[AGENT {num}] {name}")
    print(f"           {detail}")


def _done(num: str, elapsed: float) -> None:
    print(f"[AGENT {num}] Done ({elapsed}s)")


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Strip --flags before joining, otherwise "--no-moodboard"/"--no-cache" get
    # absorbed into the keyword and pollute every agent prompt + the cache keys.
    _args = [a for a in sys.argv[1:] if not a.startswith("--")]
    keyword = " ".join(_args) if _args else "quiet luxury wellness"

    print(f"Starting pipeline for: '{keyword}'")
    print("(Add --no-cache flag to bypass cached outputs)")
    print("(Add --no-moodboard flag to skip image generation)\n")

    use_cache = "--no-cache" not in sys.argv
    skip_moodboard = "--no-moodboard" in sys.argv

    from utils.run_logger import start_run_log, stop_run_log
    _log = start_run_log(keyword)
    try:
        result = run_visual_direction_pipeline(
            keyword,
            use_cache=use_cache,
            skip_moodboard=skip_moodboard,
        )

        print("\n" + "="*60)
        print("FORMATTED REPORT:")
        print("="*60)
        print(result["formatted_report"])

        if result["moodboard_panels"]:
            print("\n" + "="*60)
            print("MOODBOARD PANEL PATHS:")
            print("="*60)
            for p in result["moodboard_panels"]:
                print(f"  [{p['panel']}]\n  {p.get('url', '(none)')[:80]}")

        if result["langsmith_url"]:
            print(f"\nLangSmith trace: {result['langsmith_url']}")

        print(f"\nTimings: {result['timings']}")

    except (ValueError, RuntimeError) as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    finally:
        stop_run_log(_log)
