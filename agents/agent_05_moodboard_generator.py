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

from tools.image_gen_tool import get_image_gen_tool
from utils.llm import build_llm

load_dotenv()


# ── Agent definition ──────────────────────────────────────────────────────────

def build_moodboard_generator() -> Agent:
    """Constructs the Moodboard Generator CrewAI agent."""
    image_tool = get_image_gen_tool()

    return Agent(
        role="Visual Moodboard Generator",
        goal=(
            "Craft 5 precise, dimension-specific image generation prompts from "
            "a validated visual direction report, generate each image, and return "
            "all 5 image URLs in a structured list. Each prompt must target a "
            "different visual dimension of the brand direction."
        ),
        backstory=(
            "You are a creative director who specialises in translating brand "
            "direction briefs into precise visual references. You know that a good "
            "moodboard image is not 'pretty' — it is SPECIFIC. A prompt that says "
            "'luxury wellness' is useless. A prompt that says 'single amber glass "
            "vessel on raw limestone surface, diffuse morning light, charcoal and "
            "warm cream tones, extreme negative space, matte finish, editorial "
            "photography style' generates a reference a designer can actually use. "
            "You craft prompts for five visual dimensions separately, then generate "
            "each one. You never combine multiple brand dimensions into a single prompt."
        ),
        tools=[image_tool],
        llm=build_llm("anthropic/claude-haiku-4-5-20251001", tier="fast"),  # NVIDIA NIM fallback if key set
        verbose=True,
        allow_delegation=False,
        max_iter=6,  # one tool call per image (5) + final answer
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
            "For each panel:\n"
            "1. Write the prompt following this structure:\n"
            "   [subject], [material/surface], [lighting], [colour palette], [composition style], [mood]\n"
            "2. Call generate_moodboard_image with that prompt\n"
            "3. Record the returned URL\n\n"
            "Do not combine multiple panels into one prompt. Generate each separately."
        ),
        expected_output=(
            "A structured list of 5 generated images in this exact format:\n\n"
            "MOODBOARD PANELS:\n"
            "1. PALETTE REFERENCE\n"
            "   Prompt: [the exact prompt used]\n"
            "   URL: [the returned URL]\n\n"
            "2. MATERIAL + TEXTURE\n"
            "   Prompt: [the exact prompt used]\n"
            "   URL: [the returned URL]\n\n"
            "3. PHOTOGRAPHY STYLE\n"
            "   Prompt: [the exact prompt used]\n"
            "   URL: [the returned URL]\n\n"
            "4. TYPOGRAPHIC MOOD\n"
            "   Prompt: [the exact prompt used]\n"
            "   URL: [the returned URL]\n\n"
            "5. BRAND ATMOSPHERE\n"
            "   Prompt: [the exact prompt used]\n"
            "   URL: [the returned URL]"
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

    # Extract panel names
    panel_names = [
        "PALETTE REFERENCE",
        "MATERIAL + TEXTURE",
        "PHOTOGRAPHY STYLE",
        "TYPOGRAPHIC MOOD",
        "BRAND ATMOSPHERE",
    ]

    # Extract prompt lines
    prompt_pattern = re.compile(r'Prompt:\s*(.+?)(?=\n\s*URL:|\n\s*\d+\.|\Z)', re.DOTALL)
    prompts = [p.strip() for p in prompt_pattern.findall(raw_output)]

    # Match all path formats the agent may write in its Final Answer:
    #   file:///C:\Users\Moushmi Rao\...\panel.png (browser-style file URL — most common)
    #   FILE::C:\Users\Moushmi Rao\...\panel.png   (tool output prefix)
    #   C:\Users\Moushmi Rao\...\panel.png          (bare Windows path)
    #   /home/user/.../panel.png                    (bare Unix path)
    url_line_pattern = re.compile(
        r'URL:\s*((?:FILE::|file:///)?(?:[A-Za-z]:[/\\]|/)[^\n"]+\.png)',
        re.IGNORECASE
    )
    url_lines = [u.strip() for u in url_line_pattern.findall(raw_output)]
    # Strip FILE:: or file:/// prefix so all entries are bare file paths
    url_lines = [re.sub(r'^(?:FILE::|file:///)', '', u, flags=re.IGNORECASE) for u in url_lines]

    # Also catch FILE:: paths that appear outside URL: lines (tool output sections)
    file_pattern = re.compile(r'FILE::([^\n"]+\.png)', re.IGNORECASE)
    file_paths = file_pattern.findall(raw_output)

    # Priority: url_lines from Final Answer (most reliable) > file_paths from tool output
    all_urls = url_lines if url_lines else file_paths

    for i, name in enumerate(panel_names):
        panel = {
            "panel": name,
            "prompt": prompts[i] if i < len(prompts) else "",
            "url": all_urls[i] if i < len(all_urls) else "",
        }
        panels.append(panel)

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
