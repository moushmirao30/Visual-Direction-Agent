"""
eval/judge.py
LLM-as-judge. Scores a produced report against the rubric, and separately scores
how far a held-out run converged on the AURU ground truth.

Why LiteLLM and not the Anthropic SDK directly?
  The whole project already routes every model call through LiteLLM (CrewAI uses
  it, and the model-string convention is 'anthropic/...'). Reusing it means no new
  dependency and one consistent way to name models.

Why the judge model defaults to a DIFFERENT, stronger model than the generator:
  Agent 04 writes the report with claude-sonnet-4-6. If the same model grades its
  own output you get self-preference bias — models rate their own style highly.
  Judging with claude-opus-4-8 (a different, stronger tier) is the cheap, standard
  mitigation. Override with the JUDGE_MODEL env var if needed.

Robustness:
  The judge is told to emit ONLY JSON. We still strip fences and validate against a
  Pydantic schema. A judge that returns malformed JSON is retried once with the
  parse error fed back — the same guardrail pattern Agent 04 uses. If it still
  fails, the case is recorded as a judge error rather than silently scored 0, so a
  flaky judge call never masquerades as a bad system output.
"""

import os
import json
from pydantic import BaseModel, Field, field_validator

from eval.rubric import (
    DIMENSIONS,
    AUTO_FAIL_FLAGS,
    rubric_text_for_prompt,
    weighted_overall,
)

DEFAULT_JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "anthropic/claude-opus-4-8")


# ── Judge output schemas ───────────────────────────────────────────────────────

class RubricVerdict(BaseModel):
    """Validated structure for a single rubric judgement."""
    positioning_fit: int = Field(ge=1, le=5)
    specificity: int = Field(ge=1, le=5)
    coherence: int = Field(ge=1, le=5)
    benchmark_validity: int = Field(ge=1, le=5)
    actionability: int = Field(ge=1, le=5)
    hallucinated_brands: bool
    internal_contradiction: bool
    justification: str = Field(min_length=10)

    @field_validator("justification")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()


class ConvergenceVerdict(BaseModel):
    """Validated structure for the AURU held-out convergence judgement."""
    palette_match: int = Field(ge=1, le=5)
    typography_match: int = Field(ge=1, le=5)
    positioning_match: int = Field(ge=1, le=5)
    benchmark_overlap: int = Field(ge=1, le=5)
    matched_elements: list[str]
    missed_elements: list[str]
    justification: str = Field(min_length=10)


# ── LiteLLM call helper ────────────────────────────────────────────────────────

def _call_judge(system: str, user: str, model: str) -> str:
    """
    Single LiteLLM completion.

    Note: temperature is intentionally NOT sent. Newer Claude models (e.g.
    claude-opus-4-8, the default judge) reject `temperature` as deprecated and
    error the call. We omit it and rely on the model default + the strict rubric
    and JSON schema for stable grading. If you pin an older judge model that
    benefits from temperature=0, add it back behind a model check.
    """
    import litellm
    resp = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=1200,
    )
    return resp["choices"][0]["message"]["content"]


def _extract_json(raw: str) -> dict:
    """Strips markdown fences and parses the first JSON object."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    # If the model wrapped prose around it, grab the outermost { ... }.
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


# ── Rubric judging ─────────────────────────────────────────────────────────────

_RUBRIC_SYSTEM = (
    "You are a senior creative director and brand strategist grading an AI-generated "
    "visual direction report. You are exacting and unsentimental. Generic, plausible-"
    "sounding output scores 3, not 5. You reward specificity and correct market "
    "positioning, and you punish invented benchmark brands and internal contradictions. "
    "Output ONLY a single JSON object, no markdown, no commentary."
)


def judge_report(keyword: str, signal: str, report: dict, model: str = DEFAULT_JUDGE_MODEL) -> dict:
    """
    Scores one report against the rubric.

    Returns:
      {
        "scores": {dim: int...},
        "flags": {flag: bool...},
        "overall": float,           # weighted, auto-fail-capped
        "justification": str,
        "judge_model": str,
        "error": str | None,
      }
    """
    user = (
        f"AESTHETIC KEYWORD: {keyword}\n"
        f"EXPECTED MARKET SIGNAL: {signal}\n\n"
        f"{rubric_text_for_prompt()}\n\n"
        f"--- REPORT UNDER REVIEW (JSON) ---\n"
        f"{json.dumps(report, indent=2)}\n\n"
        "Return ONLY this JSON shape:\n"
        "{\n"
        '  "positioning_fit": 1-5,\n'
        '  "specificity": 1-5,\n'
        '  "coherence": 1-5,\n'
        '  "benchmark_validity": 1-5,\n'
        '  "actionability": 1-5,\n'
        '  "hallucinated_brands": true/false,\n'
        '  "internal_contradiction": true/false,\n'
        '  "justification": "2-3 sentences citing specifics from the report"\n'
        "}"
    )

    last_err = None
    for attempt in range(2):
        try:
            retry_note = "" if attempt == 0 else f"\n\nYour previous reply did not parse: {last_err}. Return ONLY valid JSON."
            raw = _call_judge(_RUBRIC_SYSTEM, user + retry_note, model)
            verdict = RubricVerdict(**_extract_json(raw))
            scores = {k: getattr(verdict, k) for k in DIMENSIONS}
            flags = {f: getattr(verdict, f) for f in AUTO_FAIL_FLAGS}
            return {
                "scores": scores,
                "flags": flags,
                "overall": weighted_overall(scores, flags),
                "justification": verdict.justification,
                "judge_model": model,
                "error": None,
            }
        except Exception as e:
            last_err = str(e)[:300]

    return {
        "scores": None, "flags": None, "overall": None,
        "justification": None, "judge_model": model,
        "error": f"judge failed after retry: {last_err}",
    }


# ── AURU convergence judging (held-out benchmark) ──────────────────────────────

_CONVERGENCE_SYSTEM = (
    "You are comparing two visual directions for the same brief. One is a held-out "
    "human-researched ground truth (AURU). The other was produced by an AI pipeline "
    "that did NOT have access to the ground truth document. Score how far the AI "
    "independently converged on the same design decisions. Reward genuine convergence "
    "on palette character, typographic class, positioning thesis, and benchmark brands. "
    "Do not reward superficial keyword overlap. Output ONLY a single JSON object."
)


def judge_auru_convergence(report: dict, ground_truth: dict, model: str = DEFAULT_JUDGE_MODEL) -> dict:
    """
    Scores how far a held-out (de-leaked) report converged on the AURU ground truth.
    This is the honest version of the demo's central claim.
    """
    user = (
        "--- GROUND TRUTH (AURU, held out of the knowledge base) ---\n"
        f"{json.dumps(ground_truth, indent=2)}\n\n"
        "--- AI-PRODUCED REPORT (knowledge base had AURU REMOVED) ---\n"
        f"{json.dumps(report, indent=2)}\n\n"
        "Score 1-5 on each axis (5 = strong independent convergence):\n"
        "- palette_match: same colour CHARACTER (warm neutrals + sage + near-black, low saturation)?\n"
        "- typography_match: same class (editorial old-style serif display + clean humanist sans body)?\n"
        "- positioning_match: same thesis (quiet luxury / restraint / quality through absence)?\n"
        "- benchmark_overlap: did it name Aesop / Le Labo / Bamford, or brands of identical positioning?\n\n"
        "Return ONLY this JSON shape:\n"
        "{\n"
        '  "palette_match": 1-5,\n'
        '  "typography_match": 1-5,\n'
        '  "positioning_match": 1-5,\n'
        '  "benchmark_overlap": 1-5,\n'
        '  "matched_elements": ["..."],\n'
        '  "missed_elements": ["..."],\n'
        '  "justification": "2-3 sentences"\n'
        "}"
    )

    last_err = None
    for attempt in range(2):
        try:
            retry_note = "" if attempt == 0 else f"\n\nYour previous reply did not parse: {last_err}. Return ONLY valid JSON."
            raw = _call_judge(_CONVERGENCE_SYSTEM, user + retry_note, model)
            verdict = ConvergenceVerdict(**_extract_json(raw))
            axes = [verdict.palette_match, verdict.typography_match,
                    verdict.positioning_match, verdict.benchmark_overlap]
            return {
                "palette_match": verdict.palette_match,
                "typography_match": verdict.typography_match,
                "positioning_match": verdict.positioning_match,
                "benchmark_overlap": verdict.benchmark_overlap,
                "convergence_overall": round(sum(axes) / len(axes), 2),
                "matched_elements": verdict.matched_elements,
                "missed_elements": verdict.missed_elements,
                "justification": verdict.justification,
                "judge_model": model,
                "error": None,
            }
        except Exception as e:
            last_err = str(e)[:300]

    return {"convergence_overall": None, "judge_model": model,
            "error": f"convergence judge failed after retry: {last_err}"}
