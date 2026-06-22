"""
test_agent_04.py
Isolated test for Agent 04 — Report Writer + Schema Validation.

Run from the visual-direction-agent/ folder with venv active:
  python -m tests.test_agent_04

Uses SAMPLE_SYNTHESIS from agent_04 — does not require Agents 01–03 to run.
Cost: ~1000 tokens on Claude Sonnet = ~$0.003
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_schema_import():
    try:
        from schemas.report_schema import VisualDirectionReport, ColourSwatch, validate_report
        print("[PASS] Schema imports correctly")
        return True
    except Exception as e:
        print(f"[FAIL] Schema import error: {e}")
        return False


def test_schema_validation_pass():
    """Test that a valid dict passes schema validation."""
    from schemas.report_schema import validate_report
    valid_data = {
        "aesthetic_keyword": "quiet luxury wellness",
        "positioning_statement": "This brand communicates quality through deliberate absence.",
        "palette": [
            {"name": "Charcoal", "hex_code": "#2B2B2B", "role": "Primary", "rationale": "Restraint"},
            {"name": "Warm Cream", "hex_code": "#F5F1E8", "role": "Background", "rationale": "Warmth"},
        ],
        "photography_tones": "Warm-neutral, diffuse light",
        "typography": {
            "display_typeface": "EB Garamond (Old Style Serif)",
            "body_typeface": "Jost Light (Humanist Sans)",
            "display_tracking": "140–160% letterspacing",
            "body_tracking": "100–110% letterspacing",
            "hierarchy_notes": "Body never exceeds Regular weight",
        },
        "layout_approach": "Asymmetrical grid, 35–45% content / 55–65% whitespace",
        "negative_space_rule": "Whitespace is a material, not a gap",
        "photography_direction": ["Single subject per frame", "Neutral ground only", "Diffuse light"],
        "materials": "Uncoated paper, stone, patinated metal",
        "do_rules": ["Use tone shifts not hue shifts", "Let negative space carry authority", "Photograph surfaces not people"],
        "dont_rules": ["Never high-saturation botanical green", "Never Raleway or Montserrat", "Never lifestyle staging"],
        "benchmark_brands": [
            {"name": "Aesop", "reference_note": "Dark glass, matte label restraint"},
            {"name": "Le Labo", "reference_note": "Laboratory aesthetic, monospace labels"},
        ],
        "visual_narrative": "The visual system operates as a study in refusal. Every decision is a removal — colour that does not perform, type that does not shout, photography that does not aspire to lifestyle.",
        "conflicts_resolved": None,
    }
    report, error = validate_report(valid_data)
    if error:
        print(f"[FAIL] Valid data failed schema: {error}")
        return False
    print("[PASS] Valid data passes schema validation")
    return True


def test_schema_validation_fail():
    """Test that an invalid dict (bad hex code) fails schema validation correctly."""
    from schemas.report_schema import validate_report
    invalid_data = {
        "aesthetic_keyword": "test",
        "positioning_statement": "A test positioning statement for validation.",
        "palette": [
            {"name": "Bad", "hex_code": "not-a-hex", "role": "test", "rationale": "test"},
        ],
        "photography_tones": "test",
        "typography": {
            "display_typeface": "Test", "body_typeface": "Test",
            "display_tracking": "test", "body_tracking": "test", "hierarchy_notes": "test"
        },
        "layout_approach": "test", "negative_space_rule": "test",
        "photography_direction": ["test"], "materials": "test",
        "do_rules": ["rule"], "dont_rules": ["rule"],
        "benchmark_brands": [{"name": "Brand", "reference_note": "note"}],
        "visual_narrative": "test visual narrative for validation purposes here",
    }
    report, error = validate_report(invalid_data)
    if report is not None:
        print("[FAIL] Invalid data should have failed validation but passed")
        return False
    print(f"[PASS] Invalid data correctly rejected: hex validation triggered")
    return True


def test_agent_build():
    try:
        from agents.agent_04_report_writer import build_report_writer
        agent = build_report_writer()
        print(f"[PASS] Agent built: role='{agent.role}'")
        return True
    except Exception as e:
        print(f"[FAIL] Agent build error: {e}")
        return False


def test_live_run():
    from agents.agent_04_report_writer import run_report_writer, SAMPLE_SYNTHESIS

    print("\n[INFO] Running live report writing test with sample synthesis...")

    report, formatted, error = run_report_writer("quiet luxury wellness", SAMPLE_SYNTHESIS)

    if error:
        print(f"[FAIL] {error}")
        return False

    print("[PASS] Schema validation passed")
    print(f"[INFO] Palette swatches: {len(report.palette)}")
    print(f"[INFO] DO rules: {len(report.do_rules)}")
    print(f"[INFO] DON'T rules: {len(report.dont_rules)}")
    print(f"[INFO] Benchmark brands: {len(report.benchmark_brands)}")
    print(f"[INFO] Hex codes: {[s.hex_code for s in report.palette]}")
    print(f"\n--- FORMATTED REPORT PREVIEW (first 600 chars) ---")
    print(formatted[:600])
    print("...")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Agent 04 — Report Writer: Test Suite")
    print("=" * 60)

    results = []
    results.append(("schema_import", test_schema_import()))
    results.append(("schema_validation_pass", test_schema_validation_pass()))
    results.append(("schema_validation_fail", test_schema_validation_fail()))
    results.append(("agent_build", test_agent_build()))

    if all(r[1] for r in results):
        results.append(("live_run", test_live_run()))
    else:
        print("\n[SKIP] Live test skipped — fix setup issues first")

    print("\n" + "=" * 60)
    print("RESULTS:")
    for name, passed in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    all_passed = all(r[1] for r in results)
    print(f"\n{'All tests passed.' if all_passed else 'Some tests failed — see above.'}")
    sys.exit(0 if all_passed else 1)
