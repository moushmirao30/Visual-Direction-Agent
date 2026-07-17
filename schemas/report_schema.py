"""
schemas/report_schema.py
Pydantic schema for the validated visual direction report output.

Why Pydantic validation here?
  Agent 04 is the output gate. Before anything renders in the UI or gets
  passed to Agent 05, the report must be structurally complete. Pydantic
  enforces this at runtime — missing fields or wrong types raise validation
  errors immediately, which is far better than discovering incomplete output
  in the Streamlit UI during a live demo.

  This schema IS the guardrail. Every field has:
  - A type annotation (enforced at validation time)
  - A description (used in the agent's output instructions)
  - Constraints where relevant (min_length, min_items)
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
import re


class ColourSwatch(BaseModel):
    """A single colour in the brand palette."""
    name: str = Field(description="Colour name (e.g. 'Warm Cream', 'Deep Charcoal')")
    hex_code: str = Field(description="Hex colour code (e.g. '#F5F1E8')")
    role: str = Field(description="Role in the colour system (e.g. 'Primary background')")
    rationale: str = Field(description="Why this colour for this aesthetic")

    @field_validator("hex_code")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError(f"hex_code must be in #RRGGBB format, got: {v}")
        return v.upper()


class TypographyDirection(BaseModel):
    """Typography system for the brand."""
    display_typeface: str = Field(
        description="Display/heading typeface name and classification"
    )
    body_typeface: str = Field(
        description="Body/label typeface name and classification"
    )
    display_tracking: str = Field(
        description=(
            "LETTERSPACING rule for display text with an explicit unit — "
            "e.g. '140–160% letterspacing' or '0.05em tracking'. "
            "This is tracking (space between letters), NOT line-height."
        )
    )
    body_tracking: str = Field(
        description=(
            "LETTERSPACING rule for body text with an explicit unit "
            "(%, em, pt or px). NOT line-height."
        )
    )
    hierarchy_notes: str = Field(
        description="Additional hierarchy or weight rules (line-height guidance belongs here)"
    )

    @field_validator("display_tracking", "body_tracking")
    @classmethod
    def validate_tracking(cls, v: str) -> str:
        """
        Tracking fields shipped real failures: 'Tight line height (0.9x of font
        size)' (that's line-height, not tracking) and '50-75 units' (units of
        what?). Both are deterministically rejectable.
        """
        low = v.lower()
        if re.search(r"line[\s-]?height", low):
            raise ValueError(
                f"tracking field contains a line-height rule ({v!r}) — tracking is "
                f"letterspacing. Put line-height guidance in hierarchy_notes."
            )
        if not re.search(r"\d+\s*(%|em\b|pt\b|px\b)", low):
            raise ValueError(
                f"tracking must state a number with a real unit (%, em, pt or px), "
                f"got: {v!r} — e.g. '140–160% letterspacing' or '0.05em'."
            )
        return v


class BenchmarkBrand(BaseModel):
    """A reference brand for the visual direction."""
    name: str = Field(description="Brand name")
    reference_note: str = Field(
        description="What specifically to reference from this brand"
    )


class VisualDirectionReport(BaseModel):
    """
    The complete validated visual direction report.
    This is the final output of the 4-agent pipeline before Agent 05.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    aesthetic_keyword: str = Field(
        description="The input aesthetic keyword (e.g. 'quiet luxury wellness')"
    )
    positioning_statement: str = Field(
        min_length=20,
        description=(
            "One-sentence design direction THESIS — a specific stance the brand "
            "takes visually. Must NOT restate the aesthetic keyword back as "
            "adjectives; it must add a decision the keyword doesn't contain."
        )
    )

    # ── Colour ────────────────────────────────────────────────────────────────
    palette: list[ColourSwatch] = Field(
        min_length=2,
        max_length=5,
        description="Brand colour palette — 2 to 5 swatches"
    )
    photography_tones: str = Field(
        description="Photography colour/tone direction"
    )

    # ── Typography ────────────────────────────────────────────────────────────
    typography: TypographyDirection = Field(
        description="Typography system"
    )

    # ── Spatial ───────────────────────────────────────────────────────────────
    layout_approach: str = Field(
        description=(
            "Grid type and ONE content-to-space ratio (e.g. '40% content / 60% "
            "space'). Do not state a second, different ratio anywhere else."
        )
    )
    negative_space_rule: str = Field(
        description=(
            "Negative space principle for this aesthetic. Must be CONSISTENT "
            "with the ratio in layout_approach — do not introduce a "
            "contradictory percentage."
        )
    )
    photography_direction: list[str] = Field(
        min_length=2,
        max_length=5,
        description="Photography directives (2–5 specific rules)"
    )
    materials: str = Field(
        description="Surface and material direction"
    )

    # ── Rules ─────────────────────────────────────────────────────────────────
    do_rules: list[str] = Field(
        min_length=3,
        max_length=6,
        description="Concrete design DOs (3–6 items)"
    )
    dont_rules: list[str] = Field(
        min_length=3,
        max_length=6,
        description="Concrete design DON'Ts (3–6 items)"
    )

    # ── References ────────────────────────────────────────────────────────────
    benchmark_brands: list[BenchmarkBrand] = Field(
        min_length=2,
        max_length=4,
        description="Benchmark brands with specific reference notes (2–4)"
    )

    # ── Narrative ─────────────────────────────────────────────────────────────
    visual_narrative: str = Field(
        min_length=80,
        description="Cohesive 100–150 word visual direction paragraph"
    )

    # ── Optional ─────────────────────────────────────────────────────────────
    conflicts_resolved: Optional[str] = Field(
        default=None,
        description="Any trend/theory conflicts that were resolved, and how"
    )

    @model_validator(mode="after")
    def positioning_must_not_echo_keyword(self) -> "VisualDirectionReport":
        """
        Real failure: keyword 'fusion, flavorful food truck' produced
        'Visuals for this fusion, flavorful food truck are...' — circular,
        adds nothing. Verbatim echo is deterministically rejectable.
        """
        kw = self.aesthetic_keyword.strip().lower()
        if kw and kw in self.positioning_statement.lower():
            raise ValueError(
                f"positioning_statement restates the aesthetic keyword verbatim "
                f"({self.aesthetic_keyword!r}). Write a thesis about HOW the brand "
                f"achieves this aesthetic (what it refuses, what it privileges), "
                f"not a paraphrase of the keyword."
            )
        return self


def validate_report(data: dict) -> tuple[VisualDirectionReport | None, str | None]:
    """
    Validates a dict against the VisualDirectionReport schema.

    Returns:
        (report, None)       on success
        (None, error_string) on validation failure
    """
    try:
        report = VisualDirectionReport(**data)
        return report, None
    except Exception as e:
        return None, str(e)
