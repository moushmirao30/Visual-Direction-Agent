"""
agent_02_design_theory_analyst.py
Agent 02: Design Theory Analyst

Role: Retrieves relevant design theory from the curated knowledge base
      and synthesises it into structured principles for the given aesthetic.

Why this agent exists:
  Agent 01 provides live market/cultural signals (what brands are doing now).
  Agent 02 provides timeless design theory (why certain visual choices work).
  Agent 03 merges both into a coherent, grounded visual direction.

  Without Agent 02, the system produces trend-following without principles.
  Without Agent 01, the system produces theory without cultural relevance.

Strategy — multiple focused RAG queries:
  One broad query returns average results. Four targeted queries (colour,
  typography, spatial, positioning) each pull the most relevant chunks
  for that specific design dimension. The agent synthesises across all four.

Output contract (what Agent 03 expects):
  - aesthetic_keyword: str
  - colour_theory: str         (colour psychology + palette direction)
  - typography_theory: str     (typeface pairing + hierarchy rules)
  - spatial_theory: str        (layout, negative space, composition)
  - positioning_theory: str    (brand positioning frameworks + signals)
  - raw_theory: str            (full synthesis for Agent 03)
"""

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process

from tools.rag_tool import get_rag_tool
from rag.retriever import get_retriever
from utils.cache import load_from_cache, save_to_cache
from utils.llm import build_llm

load_dotenv()

AGENT_NAME = "agent_02"


# ── Agent definition ──────────────────────────────────────────────────────────

def build_design_theory_analyst() -> Agent:
    """Constructs the Design Theory Analyst CrewAI agent."""
    rag_tool = get_rag_tool()

    return Agent(
        role="Design Theory Analyst",
        goal=(
            "Retrieve and synthesise relevant design theory principles from the "
            "knowledge base for a given brand aesthetic. Cover colour psychology, "
            "typography pairing logic, spatial design principles, and brand "
            "positioning frameworks. Ground every recommendation in established "
            "theory, not personal preference."
        ),
        backstory=(
            "You are a design theorist with deep expertise in colour psychology "
            "(Itten, Albers), editorial typography, Swiss grid systems, and brand "
            "positioning frameworks. You have studied how visual language signals "
            "brand tier, consumer emotion, and cultural belonging. You work "
            "systematically: run targeted retrieval queries for each design "
            "dimension, then synthesise findings into clear, actionable principles "
            "that a creative director could execute immediately."
        ),
        tools=[rag_tool],
        llm=build_llm("anthropic/claude-haiku-4-5-20251001", tier="fast"),  # NVIDIA NIM fallback if key set
        verbose=True,
        allow_delegation=False,
        max_iter=4,  # 4 RAG queries (colour / type / spatial / positioning) + synthesis
    )


# ── Task definition ───────────────────────────────────────────────────────────

def build_theory_task(agent: Agent, aesthetic_keyword: str) -> Task:
    """Constructs the design theory retrieval task for Agent 02."""
    return Task(
        description=(
            f"Retrieve design theory principles for the aesthetic: '{aesthetic_keyword}'.\n\n"
            "Run FOUR separate retrieval queries, one per design dimension:\n\n"
            f"Query 1 — COLOUR: '{aesthetic_keyword} colour palette psychology'\n"
            f"Query 2 — TYPOGRAPHY: '{aesthetic_keyword} typography pairing rules'\n"
            f"Query 3 — SPATIAL: '{aesthetic_keyword} layout negative space composition'\n"
            f"Query 4 — POSITIONING: '{aesthetic_keyword} brand positioning visual signals'\n\n"
            "For each dimension, synthesise the retrieved theory into specific, "
            "actionable design principles. Do not copy chunks verbatim — interpret "
            "them in the context of this specific aesthetic.\n\n"
            "Be precise. Name specific colours, typefaces, spacing ratios, and "
            "positioning signals rather than speaking in vague generalities."
        ),
        expected_output=(
            "A concise design theory brief. Each section: 4–6 bullet points maximum. "
            "No extended paragraphs. Be specific (name colours, typefaces, ratios) but brief.\n\n"
            "COLOUR THEORY:\n"
            "- Palette: 3 specific tones (name + hex if possible) + their role\n"
            "- Key psychology principle for this aesthetic (1 sentence)\n"
            "- One Itten/Albers principle to apply\n"
            "- Two colours/patterns to avoid + reason\n\n"
            "TYPOGRAPHY THEORY:\n"
            "- Display typeface: classification + 1–2 specific examples\n"
            "- Body typeface: classification + 1–2 specific examples\n"
            "- Tracking rule (display vs body)\n"
            "- One typography pattern that would undermine this aesthetic\n\n"
            "SPATIAL THEORY:\n"
            "- Layout type + content-to-space ratio\n"
            "- Negative space rule for this aesthetic\n"
            "- Photography direction (2–3 specifics)\n"
            "- Surface/material direction\n\n"
            "POSITIONING THEORY:\n"
            "- Brand tier this aesthetic maps to\n"
            "- 3 visual codes that signal the correct tier\n"
            "- Primary competitor territory to differentiate from\n"
            "- One visual choice that would undermine the positioning\n\n"
            "THEORY SYNTHESIS: 2–3 sentences only, connecting all four dimensions."
        ),
        agent=agent,
    )


# ── Runner (for isolated testing) ────────────────────────────────────────────

def run_theory_analysis(aesthetic_keyword: str, use_cache: bool = True) -> str:
    """
    Runs Agent 02 in isolation for testing.
    Requires ChromaDB to be populated (run python -m rag.ingest first).

    Args:
        aesthetic_keyword: e.g. "quiet luxury wellness"
        use_cache: If True, returns cached output when available (default True).
                   Pass False to force a fresh run regardless of cache.
    """
    # ── Cache check ────────────────────────────────────────────────────────
    if use_cache:
        cached = load_from_cache(AGENT_NAME, aesthetic_keyword)
        if cached:
            return cached

    # ── Reset RAG deduplication for this run ───────────────────────────────
    # Ensures the 4 sequential queries within this run deduplicate against
    # each other, but don't carry over state from previous runs.
    get_retriever().reset_session()

    # ── Run agent ──────────────────────────────────────────────────────────
    agent = build_design_theory_analyst()
    task  = build_theory_task(agent, aesthetic_keyword)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = str(crew.kickoff())

    # ── Cache output ───────────────────────────────────────────────────────
    if use_cache:
        save_to_cache(AGENT_NAME, aesthetic_keyword, result)

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    keyword = "quiet luxury wellness"
    print(f"\n{'='*60}")
    print(f"Running Agent 02 — Design Theory Analyst")
    print(f"Aesthetic keyword: '{keyword}'")
    print(f"{'='*60}\n")

    output = run_theory_analysis(keyword)

    print(f"\n{'='*60}")
    print("AGENT 02 OUTPUT:")
    print(f"{'='*60}")
    print(output)
