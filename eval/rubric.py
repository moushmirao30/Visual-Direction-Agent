"""
eval/rubric.py
The scoring contract for the LLM-as-judge.

Why a written rubric at all?
  "Is the output good?" is not measurable. "Does it score >=4/5 on benchmark
  validity across 13 keywords?" is. The rubric turns taste into a number you can
  track across runs. It also makes the judge reproducible: the same dimensions,
  the same anchors, the same scale every time — so a score change reflects the
  SYSTEM changing, not the judge's mood.

Design choices:
  - 5 dimensions, each scored 1-5 with explicit anchors (1, 3, 5 defined).
  - Weighted, because the dimensions are not equally diagnostic. Positioning fit
    and benchmark validity are what separate a real direction from a plausible-
    sounding one, so they carry the most weight.
  - Two AUTO-FAIL flags (hallucinated brands, internal contradiction). These cap
    the overall score regardless of the other dimensions — a brief that invents a
    fake benchmark brand or contradicts itself is not shippable no matter how
    pretty the prose. This mirrors 2026 agent-eval practice: safety/hallucination
    is a gate, not just another averaged number.
"""

# dimension_key: (human label, weight, why it matters)
DIMENSIONS = {
    "positioning_fit": (
        "Positioning fit",
        0.30,
        "Does the direction land in the market territory the keyword implies "
        "(premium / clinical / accessible / warm / bold)? A premium brief that "
        "reads as budget — or vice versa — fails here.",
    ),
    "specificity": (
        "Specificity / non-genericness",
        0.20,
        "Are palette hexes, named typefaces, tracking values and rules concrete "
        "and committed, or boilerplate that would fit any brand ('use clean fonts', "
        "'a calming palette')?",
    ),
    "coherence": (
        "Internal coherence",
        0.15,
        "Do palette, typography, spatial, photography and do/don't rules reinforce "
        "ONE direction without contradicting each other?",
    ),
    "benchmark_validity": (
        "Benchmark validity",
        0.20,
        "Are the benchmark brands real, recognisable, and genuinely on-aesthetic "
        "for this keyword? Invented or off-territory brands score low.",
    ),
    "actionability": (
        "Actionability",
        0.15,
        "Could a junior designer execute from the do/don't rules and specs without "
        "coming back with questions?",
    ),
}

SCALE_ANCHORS = """
Score each dimension 1-5:
  5 = Excellent. Specific, correct, committed. A senior creative would sign off.
  4 = Strong with a minor gap.
  3 = Acceptable but generic or partially off — works for many briefs, not sharply this one.
  2 = Weak. Vague, partly wrong territory, or thin.
  1 = Fails the dimension. Wrong, empty, or boilerplate.
"""

# Auto-fail flags — when True, overall_score is capped at CAP regardless of dimensions.
AUTO_FAIL_FLAGS = {
    "hallucinated_brands": "One or more benchmark brands are invented, not real, or clearly do not exist.",
    "internal_contradiction": "The report contradicts itself (e.g. 'dark moody palette' but lists only pale pastels).",
}
AUTO_FAIL_CAP = 2.0  # overall score cannot exceed this if any auto-fail flag is set


def weighted_overall(scores: dict[str, int], flags: dict[str, bool]) -> float:
    """
    Computes the weighted 1-5 overall score from per-dimension scores,
    then applies the auto-fail cap if any safety flag is set.

    scores: {dimension_key: int 1-5}
    flags:  {flag_key: bool}
    """
    total = sum(scores[k] * DIMENSIONS[k][1] for k in DIMENSIONS)
    if any(flags.get(f, False) for f in AUTO_FAIL_FLAGS):
        return min(total, AUTO_FAIL_CAP)
    return round(total, 2)


def rubric_text_for_prompt() -> str:
    """Renders the rubric as a block to inject into the judge prompt."""
    lines = ["SCORING DIMENSIONS (weight in brackets):"]
    for key, (label, weight, why) in DIMENSIONS.items():
        lines.append(f"\n- {key} — {label} [{int(weight*100)}%]\n  {why}")
    lines.append("\n" + SCALE_ANCHORS)
    lines.append("AUTO-FAIL FLAGS (set true only when clearly warranted):")
    for flag, desc in AUTO_FAIL_FLAGS.items():
        lines.append(f"- {flag}: {desc}")
    return "\n".join(lines)
