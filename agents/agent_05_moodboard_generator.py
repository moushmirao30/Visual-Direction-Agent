"""
agent_05_moodboard_generator.py
Agent 05: Moodboard Generator

Role: Reads the validated visual direction report, crafts 4–6 precise
      image generation prompts, calls Pollinations.ai for each, and
      returns a structured list of image URLs for the Streamlit moodboard grid.

Why this is the last agent:
  Image generation prompts are only meaningful once the direction is fully
  resolved. If you generate images before the palette, typography, and
  spatial direction are locked, you're guessing. Agents 01–04 exist so
  that Agent 05's prompts are precise rather than generic.

Prompt engineering strategy:
  Each of the 4–6 prompts targets a DIFFERENT visual dimension:
    1. PALETTE — a colour/tone reference composition
    2. TYPOGRAPHY — a typographic layout or composition mood
    3. MATERIAL — surface, texture, material detail
    4. PHOTOGRAPHY — the brand photography style
    5. SPATIAL — layout/negative space reference
    6. MOOD — overall brand atmosphere / editorial feel (optional 6th)

  Why separate prompts per dimension?
    One generic "moodboard prompt" produces one image that represents
    everything at once, and therefore represents nothing well.
    Dimension-specific prompts give Agent 03 six precise reference points.

Output:
  List of image URLs ready for Streamlit grid rendering.
"""

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process

from tools.image_gen_tool import generate_images_batch, IMAGE_BACKEND
from utils.llm import build_llm

load_dotenv()


# ── Agent definition ──────────────────────────────────────────────────────────

def build_moodboard_generator() -> Agent:
    """Constructs the Moodboard Generator CrewAI agent (prompt-only — no tools)."""
    return Agent(
        role="Visual Moodboard Generator",
        goal=(
            "Craft 5 precise, dimension-specific image generation prompts from a "
            "validated visual direction report and return them in the exact structured "
            "format requested. Each prompt must target a different visual dimension. You "
            "do NOT generate images or produce URLs — generation happens downstream in code."
        ),
        backstory=(
            "You are a creative director who specialises in translating brand "
            "direction briefs into precise visual references. You know that a good "
            "moodboard image is not 'pretty' — it is SPECIFIC. A prompt that says "
            "'luxury wellness' is useless. A prompt that says 'single amber glass "
            "vessel on raw limestone surface, diffuse morning light, charcoal and "
            "warm cream tones, extreme negative space, matte finish, editorial "
            "photography style' generates a reference a designer can actually use. "
            "You craft prompts for five visual dimensions separately. You never combine "
            "multiple brand dimensions into one prompt, and you NEVER invent image URLs, "
            "links, or file paths — you output only the prompts."
        ),
        llm=build_llm("anthropic/claude-haiku-4-5-20251001", tier="fast"),  # NVIDIA NIM fallback if key set
        verbose=True,
        allow_delegation=False,
        max_iter=3,  # prompt-only: no tool loop needed
    )


# ── Task definition ───────────────────────────────────────────────────────────

def build_moodboard_task(agent: Agent, report_summary: str) -> Task:
    """Constructs the moodboard generation task for Agent 05."""
    return Task(
        description=(
            f"Generate a 5-panel moodboard from this visual direction brief:\n\n"
            f"{report_summary}\n\n"
            "Generate EXACTLY 5 images, one per visual dimension:\n\n"
            "PANEL 1 — PALETTE REFERENCE:\n"
            "  Prompt must show: the brand colour palette in a material/still-life composition.\n"
            "  Include the specific palette tones, surface, and lighting direction.\n\n"
            "PANEL 2 — MATERIAL + TEXTURE:\n"
            "  Prompt must show: a close-up detail of the key brand material surfaces.\n"
            "  Stone, linen, matte ceramic, uncoated paper — highly tactile.\n\n"
            "PANEL 3 — PHOTOGRAPHY STYLE:\n"
            "  Prompt must show: a brand photography scene with single subject.\n"
            "  Apply the exact photography direction: lighting, composition, subject, ground.\n\n"
            "PANEL 4 — TYPOGRAPHIC MOOD:\n"
            "  Prompt must show: a minimal typographic composition or editorial layout.\n"
            "  Evoke the typeface character without naming the actual typeface.\n\n"
            "PANEL 5 — BRAND ATMOSPHERE:\n"
            "  Prompt must show: the overall brand feeling in an abstract or environmental scene.\n"
            "  This is the mood image — not the product, not the type — the world the brand lives in.\n\n"
            "For each panel, write ONE prompt following this structure:\n"
            "   [subject], [material/surface], [lighting], [colour palette], [composition style], [mood]\n\n"
            "Do NOT call any tool. Do NOT invent URLs, links, or file paths — output ONLY the\n"
            "five prompts in the format below. Image generation happens downstream in code.\n"
            "Do not combine multiple panels into one prompt."
        ),
        expected_output=(
            "The 5 prompts in this exact format (NO URLs — prompts only):\n\n"
            "MOODBOARD PANELS:\n"
            "1. PALETTE REFERENCE\n"
            "   Prompt: [the exact prompt]\n\n"
            "2. MATERIAL + TEXTURE\n"
            "   Prompt: [the exact prompt]\n\n"
            "3. PHOTOGRAPHY STYLE\n"
            "   Prompt: [the exact prompt]\n\n"
            "4. TYPOGRAPHIC MOOD\n"
            "   Prompt: [the exact prompt]\n\n"
            "5. BRAND ATMOSPHERE\n"
            "   Prompt: [the exact prompt]"
        ),
        agent=agent,
    )


# ── Output parser ─────────────────────────────────────────────────────────────

def parse_moodboard_output(raw_output: str) -> list[dict]:
    """
    Parses Agent 05's text output into a structured list of panel dicts.

    Returns list of:
      {"panel": str, "prompt": str, "url": str}
    """
    import re
    panels = []

    panel_names = [
        "PALETTE REFERENCE",
        "MATERIAL + TEXTURE",
        "PHOTOGRAPHY STYLE",
        "TYPOGRAPHIC MOOD",
        "BRAND ATMOSPHERE",
    ]

    # Extract ONLY the prompts. We deliberately do NOT parse URLs from the model output:
    # the agent is prompt-only now, and trusting model-reported URLs is exactly what let it
    # fabricate fake links (e.g. https://moodboard.com/...). URLs are filled by code in
    # run_moodboard_generator after real image generation.
    prompt_pattern = re.compile(r'Prompt:\s*(.+?)(?=\n\s*URL:|\n\s*\d+\.|\Z)', re.DOTALL)
    prompts = [p.strip() for p in prompt_pattern.findall(raw_output)]

    for i, name in enumerate(panel_names):
        panels.append({
            "panel": name,
            "prompt": prompts[i] if i < len(prompts) else "",
            "url": "",          # filled by code after real generation
            "source": "pending",
        })

    return panels


# ── Runner ────────────────────────────────────────────────────────────────────

SAMPLE_REPORT_SUMMARY = """
POSITIONING: A visual system built on chromatic restraint, typographic authority,
and negative space dominance that communicates quality through deliberate absence.

PALETTE:
- Charcoal #2B2B2B (primary anchor)
- Warm Cream #F5F1E8 (canvas ground)
- Deep Sage #4A5F56 (accent, max 15%)

TYPOGRAPHY:
- Display: EB Garamond / Cormorant Garamond (Old Style Serif), 140–160% tracking
- Body: Jost Light / Source Sans Pro Light (Humanist Sans)

SPATIAL:
- 35–45% content / 55–65% whitespace
- Diffuse natural light, single subject per frame
- Stone, linen, uncoated paper surfaces

MOOD: Study in refusal. Matte surfaces. Quiet authority. No performance.
"""


def run_moodboard_generator(report_summary: str = None) -> tuple[list[dict], str]:
    """
    Runs Agent 05 in isolation.

    Returns:
        (panels_list, raw_output)
    """
    if report_summary is None:
        report_summary = SAMPLE_REPORT_SUMMARY
        print("[INFO] Using sample report summary for moodboard generation")

    agent = build_moodboard_generator()
    task = build_moodboard_task(agent, report_summary)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    raw_output = str(crew.kickoff())
    panels = parse_moodboard_output(raw_output)

    # Generate images in code from the agent's prompts — never trust the model to report
    # URLs (it fabricated fake links like https://moodboard.com/... when the backend failed).
    # Every panel URL now reflects reality: a real local path on success, or "" on failure
    # (the UI then shows an honest "generation unavailable" state instead of phantom panels).
    prompts = [p.get("prompt", "") for p in panels]
    results = generate_images_batch(prompts)
    for panel, res in zip(panels, results):
        panel["url"] = res.get("path", "")
        panel["source"] = res.get("source", "error")

    ok = sum(1 for p in panels if p["url"])
    print(f"[AGENT 05] Image generation: {ok}/{len(panels)} panels produced a file "
          f"(backend={IMAGE_BACKEND})")
    if ok == 0:
        print("[AGENT 05] ⚠ 0 images — the image backend is unavailable (e.g. HF 402). "
              "Prompts are still valid; wire a working IMAGE_BACKEND to render panels.")
    return panels, raw_output


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"Running Agent 05 — Moodboard Generator")
    print(f"{'='*60}\n")

    panels, raw = run_moodboard_generator()

    print(f"\n{'='*60}")
    print("GENERATED MOODBOARD PANELS:")
    print(f"{'='*60}")
    for p in panels:
        print(f"\n[{p['panel']}]")
        print(f"  Prompt: {p['prompt'][:100]}...")
        print(f"  URL: {p['url'][:80]}...")
