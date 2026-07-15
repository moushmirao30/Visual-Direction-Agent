"""
tests/test_color_validator.py
Regression tests for the deterministic semantic guardrail.

Every "must fail" case below shipped in a REAL run before this guardrail
existed. If any of these start passing validation, the guardrail regressed.

Run:  pytest tests/test_color_validator.py -v
(No crewai/LLM dependency — pure validation logic.)
"""

import pytest

from utils.color_validator import (
    hex_to_hsl,
    validate_colour_name,
    validate_harmony_claims,
    validate_report_semantics,
)
from schemas.report_schema import TypographyDirection, VisualDirectionReport


# ── Real shipped failures: colour name vs hex ────────────────────────────────

class TestRealShippedFailures:
    def test_ff9900_is_not_burnt_orange(self):
        # Run 'artisanal soulful spicy food truck': #FF9900 is pure web orange.
        assert validate_colour_name("Burnt Orange", "#FF9900") is not None

    def test_f5deb3_is_not_golden_brown(self):
        # Same run: #F5DEB3 is CSS `wheat`, a pale cream — nowhere near brown.
        assert validate_colour_name("Golden Brown", "#F5DEB3") is not None

    def test_8bc34a_is_not_deep_teal(self):
        # Run 'fusion, flavorful food truck': #8BC34A is Material LIGHT GREEN
        # (hue ~88°); teal requires 160–200°. Double violation: not deep either.
        assert validate_colour_name("Deep Teal", "#8BC34A") is not None

    def test_1abc9c_is_not_deep_turquoise(self):
        # First run: right hue family, but 'deep' at 42% lightness + 76% sat
        # is a bright UI turquoise, not a deep one.
        assert validate_colour_name("Deep Turquoise", "#1ABC9C") is not None

    def test_ffc67d_is_not_vibrant_orange(self):
        # 'fusion' run: #FFC67D is peach (75% lightness) — 'vibrant orange' it is not.
        assert validate_colour_name("Vibrant Orange", "#FFC67D") is not None


# ── Valid palettes must pass (no false positives) ────────────────────────────

class TestValidNamesPass:
    @pytest.mark.parametrize("name,hex_code", [
        ("Warm Cream", "#F5F1E8"),        # AURU ground truth
        ("Deep Charcoal", "#2B2B2B"),     # AURU
        ("Deep Sage", "#4A5F56"),         # AURU
        ("Burnt Orange", "#BF5700"),      # actual burnt orange
        ("Golden Brown", "#996515"),      # actual golden brown
        ("Deep Teal", "#0F4C4C"),         # actual deep teal
        ("Terracotta", "#C1663E"),
        ("Navy", "#1B2A4A"),
        ("Blush", "#F2D5CE"),
    ])
    def test_correct_pairs_pass(self, name, hex_code):
        assert validate_colour_name(name, hex_code) is None

    def test_brand_invented_names_are_skipped(self):
        # No lexicon term → not validatable → must NOT fail.
        assert validate_colour_name("AURU Dawn", "#FF9900") is None

    def test_invalid_hex_is_schemas_job(self):
        assert validate_colour_name("Burnt Orange", "not-a-hex") is None


# ── Harmony claims vs actual hue geometry ────────────────────────────────────

class TestHarmonyClaims:
    def test_analogous_claim_with_complementary_pair_fails(self):
        # First food-truck run: claimed analogous, shipped orange (36°) +
        # turquoise (168°) — 132° apart.
        palette = [
            {"name": "Orange", "hex_code": "#FF9900"},
            {"name": "Turquoise", "hex_code": "#1ABC9C"},
        ]
        err = validate_harmony_claims("Employ analogous colours primarily", palette)
        assert err is not None and "analogous" in err.lower()

    def test_analogous_claim_with_analogous_palette_passes(self):
        palette = [
            {"name": "Terracotta", "hex_code": "#C1663E"},   # ~20°
            {"name": "Amber", "hex_code": "#D99A2B"},        # ~40°
        ]
        assert validate_harmony_claims("use analogous colours", palette) is None

    def test_neutrals_do_not_break_harmony_check(self):
        # Cream + charcoal are neutrals; only chromatic hues participate.
        palette = [
            {"name": "Warm Cream", "hex_code": "#F5F1E8"},
            {"name": "Deep Charcoal", "hex_code": "#2B2B2B"},
            {"name": "Deep Sage", "hex_code": "#4A5F56"},
        ]
        assert validate_harmony_claims("tonal, analogous restraint", palette) is None

    def test_no_claim_no_check(self):
        palette = [
            {"name": "Orange", "hex_code": "#FF9900"},
            {"name": "Turquoise", "hex_code": "#1ABC9C"},
        ]
        assert validate_harmony_claims("bold contrast is welcome", palette) is None


# ── Typography guardrails (schema-level) ─────────────────────────────────────

class TestTrackingValidation:
    def _typo(self, display_tracking, body_tracking="100–110% letterspacing"):
        return TypographyDirection(
            display_typeface="EB Garamond (Old Style Serif)",
            body_typeface="Jost Light (Humanist Sans)",
            display_tracking=display_tracking,
            body_tracking=body_tracking,
            hierarchy_notes="Display for heroes only",
        )

    def test_line_height_in_tracking_rejected(self):
        # Real shipped failure: 'Tight line height (0.9x of font size)'.
        with pytest.raises(Exception, match="line-height|line height"):
            self._typo("Tight line height (0.9x of font size)")

    def test_unitless_tracking_rejected(self):
        # Real shipped failure: '50-75 units' — units of what?
        with pytest.raises(Exception, match="unit"):
            self._typo("50-75 units")

    def test_valid_tracking_passes(self):
        assert self._typo("140–160% letterspacing") is not None
        assert self._typo("0.05em tracking") is not None


# ── Positioning must not echo the keyword ────────────────────────────────────

def _minimal_report(**overrides):
    base = dict(
        aesthetic_keyword="fusion, flavorful food truck",
        positioning_statement=(
            "The brand privileges hand-thrown texture and single-source spice "
            "narratives over generic street-food maximalism."
        ),
        palette=[
            {"name": "Terracotta", "hex_code": "#C1663E",
             "role": "Primary warmth anchor", "rationale": "Earthen, appetising"},
            {"name": "Deep Charcoal", "hex_code": "#2B2B2B",
             "role": "Type and contrast ground", "rationale": "Lets food colour lead"},
        ],
        photography_tones="Warm, natural, high-texture",
        typography={
            "display_typeface": "Fraunces (Old Style Serif)",
            "body_typeface": "Inter (Humanist Sans)",
            "display_tracking": "120–140% letterspacing",
            "body_tracking": "100% letterspacing",
            "hierarchy_notes": "Two weights maximum",
        },
        layout_approach="Asymmetric grid, 60% content / 40% space",
        negative_space_rule="Hold the 40% space budget; never fill below it",
        photography_direction=["Warm natural light", "Texture-first close-ups"],
        materials="Kraft paper, matte steel, worn timber",
        do_rules=["Use texture-led photography", "Keep two type weights", "Anchor with terracotta"],
        dont_rules=["No neon", "No stock-photo staging", "No gloss finishes"],
        benchmark_brands=[
            {"name": "Aesop", "reference_note": "Material restraint"},
            {"name": "Le Labo", "reference_note": "Utilitarian labelling"},
        ],
        visual_narrative=(
            "A texture-first system where earthen terracotta and charcoal ground "
            "vivid food photography; type stays quiet so the produce carries the "
            "energy, and every surface reads hand-made rather than franchised."
        ),
    )
    base.update(overrides)
    return base


class TestPositioningEcho:
    def test_verbatim_keyword_echo_rejected(self):
        # Real shipped failure: 'Visuals for this fusion, flavorful food truck are…'
        with pytest.raises(Exception, match="restates"):
            VisualDirectionReport(**_minimal_report(
                positioning_statement=(
                    "Visuals for this fusion, flavorful food truck are premium-casual, "
                    "vibrant, and inviting."
                )
            ))

    def test_thesis_statement_passes(self):
        assert VisualDirectionReport(**_minimal_report()) is not None


# ── End-to-end: the shipped food-truck palette must fail as a whole ──────────

def test_shipped_food_truck_report_fails_semantics():
    report = _minimal_report(
        palette=[
            {"name": "Burnt Orange", "hex_code": "#FF9900",
             "role": "Primary", "rationale": "Energy"},
            {"name": "Golden Brown", "hex_code": "#F5DEB3",
             "role": "Secondary", "rationale": "Warmth"},
            {"name": "Deep Turquoise", "hex_code": "#1ABC9C",
             "role": "Accent", "rationale": "Sophistication"},
        ],
        do_rules=["Employ analogous colours primarily",
                  "Use texture-led photography", "Keep two type weights"],
    )
    err = validate_report_semantics(report)
    assert err is not None
    # All three mislabeled colours AND the false harmony claim are caught.
    assert "#FF9900" in err and "#F5DEB3" in err and "#1ABC9C" in err
    assert "ANALOGOUS" in err or "analogous" in err
