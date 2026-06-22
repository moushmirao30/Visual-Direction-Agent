"""
schemas/trend_schema.py
Lightweight validation for Agent 01 (Trend Researcher) output.

Agent 01 returns freeform text (not JSON), so full Pydantic validation
isn't applicable. Instead we check for required section headers and
minimum content signals — enough to catch malformed or incomplete outputs
before they propagate to Agent 03 as garbage inputs.

Why validate Agent 01?
  Agent 03 (Direction Synthesiser) receives Agent 01's output directly.
  If Agent 01 produced a truncated or off-format response (which can
  happen with Haiku on unusual keywords), Agent 03 gets incomplete
  market signals and may hallucinate or produce weak synthesis.
  Catching it here means we can retry or warn before it cascades.
"""

from dataclasses import dataclass


@dataclass
class TrendOutputValidation:
    is_valid: bool
    warnings: list[str]
    errors: list[str]

    @property
    def has_issues(self) -> bool:
        return bool(self.warnings or self.errors)

    def print_report(self, agent_name: str = "Agent 01") -> None:
        if not self.has_issues:
            print(f"[VALIDATION] {agent_name} output: OK")
            return
        for e in self.errors:
            print(f"[VALIDATION] ERROR — {agent_name}: {e}")
        for w in self.warnings:
            print(f"[VALIDATION] WARN  — {agent_name}: {w}")


# Required section headers — Agent 01's expected_output specifies these
REQUIRED_SECTIONS = [
    "BENCHMARK BRANDS",
    "VISUAL CODES",
    "COLOUR SIGNALS",
    "TYPOGRAPHY SIGNALS",
    "SYNTHESIS",
]

# Soft checks — warn if absent but don't hard-fail
RECOMMENDED_SECTIONS = [
    "EDITORIAL REFERENCES",
]

# Minimum output length — anything shorter is likely truncated
MIN_OUTPUT_LENGTH = 300


def validate_trend_output(text: str) -> TrendOutputValidation:
    """
    Validates Agent 01's freeform text output.

    Returns a TrendOutputValidation with errors (hard failures) and
    warnings (soft issues that may degrade downstream quality).
    """
    errors = []
    warnings = []
    text_upper = text.upper()

    # Hard checks — required sections
    for section in REQUIRED_SECTIONS:
        if section not in text_upper:
            errors.append(f"Missing required section: {section}")

    # Soft checks — recommended sections
    for section in RECOMMENDED_SECTIONS:
        if section not in text_upper:
            warnings.append(f"Missing recommended section: {section}")

    # Length check — truncated output
    if len(text.strip()) < MIN_OUTPUT_LENGTH:
        errors.append(
            f"Output too short ({len(text.strip())} chars). "
            f"Expected at least {MIN_OUTPUT_LENGTH}. Likely truncated."
        )

    # Brand count check — need at least 2 brands mentioned
    import re
    benchmark_match = re.search(r'BENCHMARK BRANDS(.*?)(?=VISUAL CODES|$)', text_upper, re.DOTALL)
    if benchmark_match:
        brand_section = benchmark_match.group(1)
        # Count lines that look like brand entries (start with - or number)
        brand_lines = [l for l in brand_section.split('\n') if re.match(r'^\s*[-•\d]', l.strip())]
        if len(brand_lines) < 2:
            warnings.append(
                f"Only {len(brand_lines)} benchmark brand(s) found. "
                "Agent 03 needs at least 3 for reliable synthesis."
            )

    return TrendOutputValidation(
        is_valid=len(errors) == 0,
        warnings=warnings,
        errors=errors,
    )
