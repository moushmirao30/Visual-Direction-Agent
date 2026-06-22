"""
agent_03_direction_synthesiser.py
Agent 03: Direction Synthesiser

Role: Receives the outputs of Agent 01 (live trend research) and Agent 02
      (design theory principles) and synthesises them into a single, coherent
      visual direction narrative.

Why this agent exists:
  Agent 01 = "what's happening in the market right now"
  Agent 02 = "what design theory says should work"
  These two sources can agree, partially overlap, or directly conflict.
  Agent 03's job is to reason across both, resolve conflicts explicitly,
  and produce a direction that is both culturally relevant AND theoretically sound.

Why Sonnet (not Haiku):
  Synthesis requires multi-step reasoning: identify overlap, identify conflict,
  apply judgment to resolve, then construct a coherent narrative. Haiku can
  summarise; Sonnet can reason. This is the reasoning agent.

Why no tools:
  Agent 03 works purely from context. Adding tools would tempt it to go back
  and search for more information rather than synthesising what it has. The
  discipline of working from provided inputs is intentional.

Conflict resolution rules (encoded in backstory + task):
  1. Theory governs long-term positioning decisions (colour, typography, tier)
  2. Trends govern cultural references and editorial specifics (which brands, which campaigns)
  3. When they conflict: note the conflict, apply theory as default, flag if trend
     signal is strong enough to warrant an exception

Output contract (what Agent 04 Report Writer expects):
  - aesthetic_keyword: str
  - positioning_statement: str        (1–2 sentences, the "what BRAND IS")
  - palette_direction: dict           (primary, secondary, accent + hex + rationale)
  - typography_direction: dict        (display, body, tracking rules)
  - spatial_direction: str            (layout + photography + material)
  - do_rules: list[str]               (3–5 concrete design DOs)
  - dont_rules: list[str]             (3–5 concrete design DON'Ts)
  - benchmark_brands: list[str]       (3 brands, sourced from Agent 01)
  - visual_narrative: str             (full synthesis paragraph, 100–150 words)
"""

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process

from utils.llm import build_llm

load_dotenv()


# ── Agent definition ──────────────────────────────────────────────────────────

def build_direction_synthesiser() -> Agent:
    """Constructs the Direction Synthesiser CrewAI agent."""
    return Agent(
        role="Visual Direction Synthesiser",
        goal=(
            "Synthesise live market trend research and design theory principles "
            "into a single, coherent visual direction for a brand aesthetic. "
            "Identify where trends and theory align, where they conflict, and "
            "resolve conflicts explicitly. Produce a direction that is both "
            "culturally relevant and theoretically grounded."
        ),
        backstory=(
            "You are a senior creative director with 15 years experience building "
            "brand visual identities across luxury, wellness, fashion, and tech. "
            "You have worked with brand strategists and design theorists and know "
            "how to hold both market intelligence and design principles simultaneously "
            "without letting either dominate inappropriately. Your superpower is "
            "conflict resolution: when the market is doing one thing and theory "
            "says another, you can make a clear, reasoned judgment about which "
            "signal should govern, and why. You write directions that creative "
            "teams can execute without asking follow-up questions."
        ),
        tools=[],           # No tools — synthesis from context only
        llm=build_llm("anthropic/claude-sonnet-4-6", tier="strong"),  # NVIDIA NIM fallback if key set
        verbose=True,
        allow_delegation=False,
        max_iter=2,         # Synthesis is one pass — no tool loops needed
    )


# ── Task definition ───────────────────────────────────────────────────────────

def build_synthesis_task(
    agent: Agent,
    aesthetic_keyword: str,
    trend_research: str,
    design_theory: str,
) -> Task:
    """
    Constructs the synthesis task for Agent 03.

    Args:
        aesthetic_keyword: The original input keyword
        trend_research:    String output from Agent 01
        design_theory:     String output from Agent 02
    """
    return Task(
        description=(
            f"Synthesise the following research into a unified visual direction "
            f"for the aesthetic: '{aesthetic_keyword}'.\n\n"
            f"--- MARKET TREND RESEARCH (Agent 01 output) ---\n"
            f"{trend_research}\n\n"
            f"--- DESIGN THEORY PRINCIPLES (Agent 02 output) ---\n"
            f"{design_theory}\n\n"
            "Instructions:\n"
            "1. Identify where trends and theory ALIGN — these become the core direction\n"
            "2. Identify where they CONFLICT — resolve each conflict explicitly with a "
            "judgment call (state which you're following and why)\n"
            "3. Construct the unified direction using the output format below\n"
            "4. Every claim must be traceable to either the trend research or the theory "
            "brief above — do not introduce new information\n"
            "5. Be specific: name colours with hex codes, name typefaces, give ratios"
        ),
        expected_output=(
            "A structured visual direction brief with these exact sections:\n\n"
            "POSITIONING STATEMENT: One sentence — what this brand IS visually. "
            "Not a tagline — a design direction statement.\n\n"
            "PALETTE DIRECTION:\n"
            "- Primary: [colour name] [hex] — [role in system]\n"
            "- Secondary: [colour name] [hex] — [role in system]\n"
            "- Accent: [colour name] [hex] — [role in system]\n"
            "- Photography tones: [brief description]\n\n"
            "TYPOGRAPHY DIRECTION:\n"
            "- Display: [typeface name] ([classification]) — [usage rule]\n"
            "- Body: [typeface name] ([classification]) — [usage rule]\n"
            "- Tracking: [display rule] / [body rule]\n\n"
            "SPATIAL DIRECTION:\n"
            "- Layout: [grid type + content-to-space ratio]\n"
            "- Negative space: [rule]\n"
            "- Photography: [3 specific directives]\n"
            "- Materials: [surface/material direction]\n\n"
            "DO RULES (5 items): Concrete, actionable design decisions\n\n"
            "DON'T RULES (5 items): Specific patterns to actively avoid\n\n"
            "BENCHMARK BRANDS (3): [Brand name] — [what specifically to reference]\n\n"
            "CONFLICTS RESOLVED (if any): Note any trend/theory conflicts and "
            "how you resolved them.\n\n"
            "VISUAL NARRATIVE (100–150 words): A cohesive paragraph a creative "
            "director would share with a design team to brief them on the direction. "
            "Written in present tense. Concrete and specific."
        ),
        agent=agent,
    )


# ── Runner (for isolated testing) ────────────────────────────────────────────

# Sample outputs for isolated testing (avoids running Agents 01+02 every test)
SAMPLE_TREND_RESEARCH = """
BENCHMARK BRANDS:
- Aesop: Apothecary-informed aesthetic, dark glass bottles, minimalist typography, matte surfaces
- Le Labo: Ultra-minimalist, laboratory aesthetic, monospace type on labels, dark + warm contrast
- Bamford: Editorial wellness luxury, stone/neutral palette, generous negative space, lifestyle photography of hands and surfaces

VISUAL CODES: Matte dark surfaces, generous negative space, editorial photography, hands not faces, minimal text on packaging, warm light sources in photography

COLOUR SIGNALS: Deep charcoal dominant, warm cream or parchment as secondary, muted sage or stone as accent

TYPOGRAPHY SIGNALS: Serif display faces (editorial authority), clean sans for body/labels, generous tracking on display text, restrained weight range

EDITORIAL REFERENCES: Kinfolk magazine visual language, Wallpaper* wellness features 2024, The Slowdown editorial photography, Port Magazine beauty issues

SYNTHESIS: The quiet luxury wellness aesthetic is defined by restraint, materiality, and the deliberate removal of visual noise. Brands operating in this space use dark or neutral palettes, minimal type, and photography that prioritises texture and surface over lifestyle performance.
"""

SAMPLE_DESIGN_THEORY = """
## COLOUR THEORY
**Palette:**
- **Charcoal (#2B2B2B)** — Primary anchor, signals sophistication and restraint
- **Warm Cream (#F5F1E8)** — Secondary, prevents coldness, grounds wellness positioning
- **Deep Sage (#4A5F56)** — Accent, signals natural without botanical cliché

**Key Psychology Principle:** Quality is communicated through chromatic restraint and tone relationships rather than saturation; luxury is what you don't say in colour.

**Itten/Albers Principle:** Apply relativity of colour — the same grey reads differently against cream than against charcoal. Use tone and saturation shifts, not hue shifts, to create hierarchy.

**Avoid:** High-saturation botanical green — reads generic. Warm peach/coral — signals spa retail.

## TYPOGRAPHY THEORY
**Display:** Old Style Serif — EB Garamond or Cormorant Garamond. Heritage, craft, editorial authority.
**Body:** Humanist Sans — Jost or Source Sans Pro Light. Approachable intelligence.
**Tracking:** Display 140–160% letterspacing / Body 100–110%
**Avoid:** Warm rounded sans (Raleway, Montserrat) — reads generic wellness cliché.

## SPATIAL THEORY
**Layout:** Asymmetrical but intentional. 35–45% content / 55–65% whitespace.
**Negative Space:** Whitespace is expensive and intentional. 120–160px digital margins.
**Photography:** Single subject, neutral ground (stone, paper, fabric), diffuse natural light, no lifestyle staging.
**Materials:** Uncoated paper, textured fabric, stone, patinated metal. Matte metallics.

## POSITIONING THEORY
**Tier:** Ultra-premium / Quiet Luxury
**Visual codes:** Restrained palette, old style serif + humanist sans, strategic negative space dominance.
**Differentiate from:** Mainstream wellness (botanical, warm, cluttered), influencer brands (pastel, sans-serif only).
**Avoid:** Warm pastel palette, lifestyle imagery, sans-serif-only typography.

## THEORY SYNTHESIS
Quiet luxury wellness synthesises restraint (colour), authority (old style serif + humanist sans), and confidence (dominant negative space) to communicate quality through absence. The visual system refuses botanical cliché and lifestyle aspiration, instead privileging tone relationships, intentional placement, and materiality.
"""


def run_synthesis(
    aesthetic_keyword: str,
    trend_research: str = None,
    design_theory: str = None,
) -> str:
    """
    Runs Agent 03 in isolation for testing.

    If trend_research and design_theory are not provided, uses
    SAMPLE_* constants above (avoids running Agents 01+02 every test).
    """
    if trend_research is None:
        trend_research = SAMPLE_TREND_RESEARCH
        print("[INFO] Using sample Agent 01 output (not running live search)")
    if design_theory is None:
        design_theory = SAMPLE_DESIGN_THEORY
        print("[INFO] Using sample Agent 02 output (not running live RAG)")

    agent = build_direction_synthesiser()
    task = build_synthesis_task(agent, aesthetic_keyword, trend_research, design_theory)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    keyword = "quiet luxury wellness"
    print(f"\n{'='*60}")
    print(f"Running Agent 03 — Direction Synthesiser")
    print(f"Aesthetic keyword: '{keyword}'")
    print(f"{'='*60}\n")

    output = run_synthesis(keyword)

    print(f"\n{'='*60}")
    print("AGENT 03 OUTPUT:")
    print(f"{'='*60}")
    print(output)
