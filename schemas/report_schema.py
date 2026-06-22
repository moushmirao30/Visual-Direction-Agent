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

from pydantic import BaseModel, Field, field_validator
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
        description="Tracking rule for display text (e.g. '140–160% letterspacing')"
    )
    body_tracking: str = Field(
        description="Tracking rule for body text"
    )
    hierarchy_notes: str = Field(
        description="Additional hierarchy or weight rules"
    )


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
        description="One-sentence design direction statement (not a tagline)"
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
        description="Grid type and content-to-space ratio"
    )
    negative_space_rule: str = Field(
        description="Negative space principle for this aesthetic"
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
