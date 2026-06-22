"""
agent_04_report_writer.py
Agent 04: Report Writer

Role: Receives the synthesised visual direction from Agent 03 and structures
      it into a validated, presentation-ready report conforming to the
      VisualDirectionReport Pydantic schema.

Why this agent exists:
  Agent 03 produces a rich creative brief in prose + markdown.
  Agent 04 converts that into a validated, structured JSON-like output
  that the Streamlit UI can render predictably and Agent 05 can consume
  directly for moodboard generation.

  The guardrail is the schema: if a required field is missing or invalid
  (e.g. hex code in wrong format, too few benchmark brands), validation
  fails and the agent must produce a corrected output. This ensures the
  system never delivers an incomplete report to the user.

Why Sonnet:
  Structured extraction from complex prose + schema compliance checking
  requires careful, precise reasoning. Haiku tends to miss nested fields.

Output:
  A VisualDirectionReport Pydantic object (validated) + formatted string
  for the Streamlit UI.
"""

import os
import json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process

from schemas.report_schema import VisualDirectionReport, validate_report
from utils.llm import build_llm

load_dotenv()


# ── Agent definition ──────────────────────────────────────────────────────────

def build_report_writer() -> Agent:
    """Constructs the Report Writer CrewAI agent."""
    return Agent(
        role="Visual Direction Report Writer",
        goal=(
            "Extract and structure the key elements from a visual direction brief "
            "into a complete, validated report. Every required field must be present "
            "and specific. Hex codes must be in #RRGGBB format. Rules must be concrete "
            "and actionable. The output must be ready to present to a creative team "
            "and to feed directly into an image generation pipeline."
        ),
        backstory=(
            "You are a senior brand documentation specialist who translates creative "
            "director briefs into structured, executable design specifications. "
            "You have a precision mindset: vague direction is not useful, and "
            "missing information is not acceptable. When a brief says 'dark palette' "
            "you write '#2B2B2B'. When it says 'serif headline' you write "
            "'EB Garamond (Old Style Serif)'. Your output is what gets handed "
            "to junior designers, printed in brand guidelines, and fed into AI "
            "image generation systems — it must be complete and unambiguous."
        ),
        tools=[],
        llm=build_llm("anthropic/claude-sonnet-4-6", tier="strong"),  # NVIDIA NIM fallback if key set
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


# ── Schema instruction string (injected into task) ───────────────────────────

SCHEMA_INSTRUCTIONS = """
Output a single valid JSON object with EXACTLY these fields:

{
  "aesthetic_keyword": "string — the input aesthetic",
  "positioning_statement": "string — one sentence design direction (min 20 chars)",
  "palette": [
    {
      "name": "string — colour name",
      "hex_code": "string — must be #RRGGBB format e.g. #2B2B2B",
      "role": "string — role in the system",
      "rationale": "string — why this colour"
    }
    // 2 to 5 swatches
  ],
  "photography_tones": "string — photography colour/tone direction",
  "typography": {
    "display_typeface": "string — typeface name and classification",
    "body_typeface": "string — typeface name and classification",
    "display_tracking": "string — e.g. '140–160% letterspacing'",
    "body_tracking": "string — e.g. '100–110% letterspacing'",
    "hierarchy_notes": "string — additional weight/size rules"
  },
  "layout_approach": "string — grid type and content-to-space ratio",
  "negative_space_rule": "string — negative space principle",
  "photography_direction": [
    "string directive 1",
    "string directive 2",
    "string directive 3"
    // 2 to 5 items
  ],
  "materials": "string — surface and material direction",
  "do_rules": [
    "string rule 1",
    "string rule 2",
    "string rule 3"
    // 3 to 6 items
  ],
  "dont_rules": [
    "string rule 1",
    "string rule 2",
    "string rule 3"
    // 3 to 6 items
  ],
  "benchmark_brands": [
    {
      "name": "string — brand name",
      "reference_note": "string — what specifically to reference"
    }
    // 2 to 4 brands
  ],
  "visual_narrative": "string — 100 to 150 word paragraph (min 80 chars)",
  "conflicts_resolved": "string or null — conflicts and resolutions if any"
}

CRITICAL RULES:
- Every hex_code MUST be in #RRGGBB format (e.g. #2B2B2B, #F5F1E8)
- Output ONLY the JSON object — no markdown, no backticks, no explanation
- All list fields must meet minimum length requirements
- Be specific: name actual typefaces, give actual hex codes, state actual ratios
- benchmark_brands MUST be real, well-known brands that genuinely fit this aesthetic.
  In reference_note, describe the brand's visual approach — do NOT invent campaign
  titles, launch years, photographer/art-director credits, or collaborations. A real
  brand with an honest visual description beats a specific-sounding but unverifiable
  campaign reference. If the brief upstream contains such a fabricated specific, drop
  the specific and keep only what is credible.
"""


# ── Task definition ───────────────────────────────────────────────────────────

def build_report_task(
    agent: Agent,
    aesthetic_keyword: str,
    synthesis: str,
    error_feedback: str | None = None,
) -> Task:
    """
    Constructs the report writing task for Agent 04.
    error_feedback: if this is a retry, include the previous failure reason
                    so the agent can correct the specific problem.
    """
    feedback_section = ""
    if error_feedback:
        feedback_section = (
            f"\n\n--- PREVIOUS ATTEMPT FAILED — FIX THESE ISSUES ---\n"
            f"{error_feedback}\n"
            f"Produce corrected JSON that resolves the above errors.\n"
        )

    return Task(
        description=(
            f"Extract and structure this visual direction brief for '{aesthetic_keyword}' "
            f"into a validated JSON report.\n\n"
            f"--- VISUAL DIRECTION BRIEF (Agent 03 output) ---\n"
            f"{synthesis}\n\n"
            f"--- OUTPUT SCHEMA ---\n"
            f"{SCHEMA_INSTRUCTIONS}"
            f"{feedback_section}"
        ),
        expected_output=(
            "A single valid JSON object conforming exactly to the schema above. "
            "No markdown formatting. No backticks. No explanation text. "
            "Just the raw JSON object starting with { and ending with }."
        ),
        agent=agent,
    )


# ── Runner ────────────────────────────────────────────────────────────────────

def _parse_and_validate(raw_output: str) -> tuple[VisualDirectionReport | None, str | None]:
    """
    Strips markdown fences, parses JSON, and validates against the Pydantic schema.
    Returns (report, error) — error is None on success.
    """
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}. Output started: {cleaned[:200]}"

    report, error = validate_report(data)
    if error:
        return None, f"Schema validation error: {error}"

    return report, None


def run_report_writer(
    aesthetic_keyword: str,
    synthesis: str,
    max_retries: int = 2,
) -> tuple[VisualDirectionReport | None, str, str | None]:
    """
    Runs Agent 04 and validates the output against the Pydantic schema.
    Retries up to max_retries times on JSON parse or schema validation failure,
    feeding the specific error back into the prompt each time.

    Returns:
        (report_object, formatted_string, error)
        - report_object: VisualDirectionReport if validation passed, else None
        - formatted_string: human-readable report for the UI
        - error: failure reason if all attempts exhausted, else None
    """
    agent = build_report_writer()
    last_error: str | None = None
    raw_output = ""

    total_attempts = max_retries + 1  # e.g. 3 total: 1 initial + 2 retries

    for attempt in range(1, total_attempts + 1):
        if attempt > 1:
            print(f"[INFO] Agent 04 retry {attempt - 1}/{max_retries} — previous error: {last_error}")

        task = build_report_task(
            agent,
            aesthetic_keyword,
            synthesis,
            error_feedback=last_error,  # None on first attempt
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        raw_output = str(crew.kickoff())
        report, error = _parse_and_validate(raw_output)

        if report is not None:
            # Success — format and return
            formatted = format_report(report)
            if attempt > 1:
                print(f"[INFO] Agent 04 succeeded on attempt {attempt}.")
            return report, formatted, None

        # Failed — store error for next retry
        last_error = error

    # All attempts exhausted
    return None, raw_output, (
        f"Agent 04 failed after {total_attempts} attempts. "
        f"Last error: {last_error}\n\nLast raw output:\n{raw_output[:500]}"
    )


def format_report(report: VisualDirectionReport) -> str:
    """Converts a validated VisualDirectionReport into a formatted string for the UI."""
    lines = [
        f"# VISUAL DIRECTION REPORT",
        f"## {report.aesthetic_keyword.upper()}",
        "",
        f"**POSITIONING**",
        report.positioning_statement,
        "",
        f"**PALETTE**",
    ]
    for swatch in report.palette:
        lines.append(f"- {swatch.name} {swatch.hex_code} — {swatch.role}")
    lines.append(f"Photography: {report.photography_tones}")
    lines += [
        "",
        f"**TYPOGRAPHY**",
        f"- Display: {report.typography.display_typeface}",
        f"- Body: {report.typography.body_typeface}",
        f"- Tracking: {report.typography.display_tracking} / {report.typography.body_tracking}",
        f"- Notes: {report.typography.hierarchy_notes}",
        "",
        f"**SPATIAL**",
        f"- Layout: {report.layout_approach}",
        f"- Space: {report.negative_space_rule}",
        f"- Materials: {report.materials}",
        "",
        f"**PHOTOGRAPHY**",
    ]
    for i, rule in enumerate(report.photography_direction, 1):
        lines.append(f"{i}. {rule}")
    lines += ["", "**DO**"]
    for rule in report.do_rules:
        lines.append(f"✓ {rule}")
    lines += ["", "**DON'T**"]
    for rule in report.dont_rules:
        lines.append(f"✗ {rule}")
    lines += ["", "**BENCHMARK BRANDS**"]
    for brand in report.benchmark_brands:
        lines.append(f"- {brand.name}: {brand.reference_note}")
    lines += ["", "**VISUAL NARRATIVE**", report.visual_narrative]
    if report.conflicts_resolved:
        lines += ["", "**CONFLICTS RESOLVED**", report.conflicts_resolved]
    return "\n".join(lines)


# ── Sample Agent 03 output for testing ───────────────────────────────────────

SAMPLE_SYNTHESIS = """
## POSITIONING STATEMENT
This brand communicates quality through deliberate absence — a visual system built on chromatic restraint, typographic authority, and negative space dominance that refuses both botanical wellness cliché and lifestyle performance.

## PALETTE DIRECTION
- Primary: Charcoal #2B2B2B — Dominant anchor across all surfaces
- Secondary: Warm Cream #F5F1E8 — Primary canvas ground
- Accent: Deep Sage #4A5F56 — Used sparingly, max 15% of any composition
- Photography tones: Warm-neutral, diffuse ambient light, stone and parchment surfaces

## TYPOGRAPHY DIRECTION
- Display: EB Garamond or Cormorant Garamond (Old Style Serif) — hero headlines only
- Body: Jost Light or Source Sans Pro Light (Humanist Sans) — all body copy
- Tracking: Display at 140–160% letterspacing / Body at 100–110%

## SPATIAL DIRECTION
- Layout: Asymmetrical grid, 35–45% content / 55–65% whitespace
- Negative space: Whitespace is a material. Digital margins min 120px.
- Photography: Single subject, neutral ground (stone/linen/paper), diffuse natural light only
- Materials: Uncoated paper, textured fabric, stone, patinated metal. Matte metallics only.

## DO RULES
1. Use tone/saturation shifts (not hue shifts) to create hierarchy
2. Let negative space carry authority — resist filling
3. Photograph surfaces and materials, not people performing wellness
4. Set display type at 140–160% tracking without exception
5. Restrict deep sage to accent function only (≤15% of any composition)

## DON'T RULES
1. Never use high-saturation botanical green
2. Never use warm rounded sans-serif typefaces (Raleway, Montserrat)
3. Never use warm peach, coral, or blush in the palette
4. Never stage lifestyle photography
5. Never use gloss finishes, foil stamping, or lacquer

## BENCHMARK BRANDS
- Aesop: Reference dark glass packaging, matte surface treatment, label restraint
- Le Labo: Reference laboratory aesthetic, monospace type on labels, dark/warm contrast
- Bamford: Reference editorial photography — hands on stone, generous negative space

## CONFLICTS RESOLVED
Photography warmth: Light remains diffuse (theory), warmth lives in surfaces not source (trend).
Typography weight: Light weight humanist sans as the execution of "restrained" (theory governs).

## VISUAL NARRATIVE
The visual system operates as a study in refusal. Every decision is a removal: colour that doesn't perform, type that doesn't shout, photography that doesn't aspire. The palette is built from three tones — charcoal #2B2B2B, warm cream #F5F1E8, and deep sage #4A5F56 — and their relationships do more work than their individual identities. EB Garamond or Cormorant Garamond carries all display work at generous tracking. Jost Light handles everything functional with quiet competence. Photography is surface and material: a single vessel on stone, diffuse light, no story, no performance. Layouts give 55 to 65 percent of every composition to space. The brand does not decorate. It curates, and then it stops.
"""


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    keyword = "quiet luxury wellness"
    print(f"\n{'='*60}")
    print(f"Running Agent 04 — Report Writer")
    print(f"Aesthetic keyword: '{keyword}'")
    print(f"{'='*60}\n")

    report, formatted, error = run_report_writer(keyword, SAMPLE_SYNTHESIS)

    if error:
        print(f"[ERROR] {error}")
    else:
        print("[SUCCESS] Schema validation passed")
        print(f"\n{'='*60}")
        print("FORMATTED REPORT:")
        print(f"{'='*60}")
        print(formatted)
