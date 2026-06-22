"""
agent_01_trend_researcher.py
Agent 01: Trend Researcher

Role: Takes a brand aesthetic keyword and returns a structured visual
      pattern summary — competitor brands, campaigns, editorial references,
      and the dominant visual codes emerging from live web data.

Why this agent exists:
  Agent 02 (Design Theory Analyst) works from static knowledge (colour theory,
  typography rules). Agent 01 provides the live, cultural layer — what's
  actually happening in the market RIGHT NOW for this aesthetic. Together they
  give Agent 03 both timeless principles and current signals.

Output contract (dict keys Agent 03 will depend on):
  - aesthetic_keyword: str
  - benchmark_brands: list[str]  (3–5 brands actively using this aesthetic)
  - visual_codes: list[str]      (dominant visual patterns found)
  - colour_signals: list[str]    (colour directions observed)
  - typography_signals: list[str](type styles/faces observed)
  - editorial_references: list[str] (campaigns, shoots, publications)
  - raw_summary: str             (full text synthesis for Agent 03)
"""

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process

from tools.search_tool import get_search_tool
from schemas.trend_schema import validate_trend_output
from utils.cache import load_from_cache, save_to_cache
from utils.llm import build_llm

load_dotenv()

AGENT_NAME = "agent_01"


# ── Agent definition ──────────────────────────────────────────────────────────

def build_trend_researcher() -> Agent:
    """
    Constructs the Trend Researcher CrewAI agent.

    The role/goal/backstory strings are not just metadata — CrewAI injects
    them directly into the system prompt. Specificity here = better output.
    """
    search_tool = get_search_tool()  # returns the @tool decorated function

    return Agent(
        role="Visual Trend Researcher",
        goal=(
            "Research live market trends for a given brand aesthetic keyword. "
            "Identify benchmark brands, dominant visual codes, colour directions, "
            "typography patterns, and editorial references from current campaigns "
            "and publications. Return findings as a structured summary."
        ),
        backstory=(
            "You are a senior visual trend researcher with 10 years experience "
            "tracking aesthetic movements across luxury, wellness, and lifestyle "
            "brands. You have a trained eye for visual language — you can identify "
            "what makes a brand's palette feel 'quiet luxury' vs 'clinical wellness' "
            "vs 'accessible premium'. You work systematically: search first, "
            "synthesise second, and always back claims with specific brand examples.\n\n"
            "Your professional reputation rests on accuracy. You NEVER invent a "
            "campaign title, launch year, photographer credit, collaboration, or "
            "publication name. If your searches did not surface a specific campaign, "
            "you simply name the real brand and describe its visual language — that "
            "is more credible than a fabricated reference. You only name brands you "
            "are confident actually exist and genuinely use this aesthetic. A made-up "
            "'Tom Ford Black Orchid Reserve 2025 campaign' or invented boutique brand "
            "would end your credibility — a real brand with an honest visual "
            "description never will. When unsure, you say less, not more."
        ),
        tools=[search_tool],
        llm=build_llm("anthropic/claude-haiku-4-5-20251001", tier="fast"),  # Haiku: fast + cheap; NVIDIA NIM fallback if key set
        verbose=True,
        allow_delegation=False,  # Agent 01 works alone — no sub-agents
        max_iter=3,              # Limits LLM loops; 3 is enough for 2–3 searches
    )


# ── Task definition ───────────────────────────────────────────────────────────

def build_research_task(agent: Agent, aesthetic_keyword: str) -> Task:
    """
    Constructs the research task for Agent 01.

    The description is the actual prompt the agent receives.
    The expected_output tells the LLM exactly what format to return.
    Being explicit here = fewer hallucinated or incomplete responses.
    """
    return Task(
        description=(
            f"Research the brand aesthetic: '{aesthetic_keyword}'.\n\n"
            "Run 2–3 targeted web searches to find:\n"
            "1. Which brands currently embody this aesthetic (name 3–5 specific brands)\n"
            "2. What visual codes define this aesthetic (colours, textures, composition style)\n"
            "3. What typography or lettering styles appear consistently\n"
            "4. Recent campaigns, editorials, or publications using this aesthetic\n\n"
            "Search query suggestions (adapt as needed):\n"
            f"- '{aesthetic_keyword} brand visual identity 2024 2025'\n"
            f"- '{aesthetic_keyword} campaign editorial design'\n"
            f"- '{aesthetic_keyword} colour palette typography examples'\n\n"
            "GROUNDING RULES (mandatory — fabrication fails this task):\n"
            "1. Only name a brand if it is real, well-known, and genuinely uses this "
            "aesthetic. When in doubt, choose the safer, more recognisable brand.\n"
            "2. Do NOT invent campaign titles, launch years, photographer or art-director "
            "credits, collaborations, or publication features. If your searches did not "
            "return a specific named campaign, name the brand and describe what it does "
            "visually instead — that is the preferred form.\n"
            "3. A real brand with an honest visual description is always better than a "
            "specific-sounding but unverifiable campaign reference. Specificity about "
            "VISUAL CODES (colour, type, layout) is rewarded; invented proper nouns are not.\n"
            "4. If you cannot support an editorial reference from your search results, "
            "omit it rather than fabricate one — fewer, real references beat more, fake ones."
        ),
        expected_output=(
            "A structured visual trend summary containing:\n"
            "- BENCHMARK BRANDS: 3–5 specific brands (with brief note on what they do visually)\n"
            "- VISUAL CODES: 4–6 dominant visual patterns (e.g. 'muted earth tones', "
            "'generous negative space', 'editorial portrait photography')\n"
            "- COLOUR SIGNALS: 3–5 colour directions (e.g. 'warm taupe', 'sage green', "
            "'off-white parchment')\n"
            "- TYPOGRAPHY SIGNALS: 2–4 type patterns (e.g. 'serif headline with generous "
            "tracking', 'lowercase wordmarks')\n"
            "- EDITORIAL REFERENCES: 0–3 references you can actually support from your "
            "searches. A real brand named with its visual approach is acceptable here — "
            "do NOT invent campaign titles, years, or credits to fill this section. "
            "If you have none you can support, write 'None verifiable from search' and move on.\n"
            "- SYNTHESIS: A 2–3 sentence narrative summarising the visual language of "
            "this aesthetic as a coherent direction\n\n"
            "Format each section with clear headers. Be precise about VISUAL CODES; never "
            "fabricate proper nouns (brands, campaigns, people) to sound specific."
        ),
        agent=agent,
    )


# ── Runner (for isolated testing) ────────────────────────────────────────────

def run_trend_research(aesthetic_keyword: str, use_cache: bool = True) -> str:
    """
    Runs Agent 01 in isolation.
    Call this directly to test before wiring into crew.py.

    Args:
        aesthetic_keyword: e.g. "quiet luxury wellness"
        use_cache: If True, returns cached output when available (default True).
                   Pass False to force a fresh run regardless of cache.

    Returns:
        Validated string output from the agent (structured trend summary).
    """
    # ── Cache check ────────────────────────────────────────────────────────
    if use_cache:
        cached = load_from_cache(AGENT_NAME, aesthetic_keyword)
        if cached:
            return cached

    # ── Run agent ──────────────────────────────────────────────────────────
    agent = build_trend_researcher()
    task  = build_research_task(agent, aesthetic_keyword)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = str(crew.kickoff())

    # ── Validate output ────────────────────────────────────────────────────
    validation = validate_trend_output(result)
    validation.print_report("Agent 01")

    if not validation.is_valid:
        print(
            "[WARN] Agent 01 output failed validation. "
            "Agent 03 synthesis may be degraded. Consider re-running."
        )

    # ── Cache valid output only ────────────────────────────────────────────
    if validation.is_valid and use_cache:
        save_to_cache(AGENT_NAME, aesthetic_keyword, result)

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    keyword = "quiet luxury wellness"
    print(f"\n{'='*60}")
    print(f"Running Agent 01 — Trend Researcher")
    print(f"Aesthetic keyword: '{keyword}'")
    print(f"{'='*60}\n")

    output = run_trend_research(keyword)

    print(f"\n{'='*60}")
    print("AGENT 01 OUTPUT:")
    print(f"{'='*60}")
    print(output)
