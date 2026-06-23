r"""
eval/compare_gemini_vs_70b.py

Head-to-head: does Gemini 2.5 Flash actually beat the Llama-3.3-70B free fallback on
the two quality complaints in HANDOFF.md, namely
  (1) loose colour naming  (e.g. #663300 called "terracotta"/"deep red" when it's brown)
  (2) thin ~50-word visual_narrative (intent is 100-150 words)?

This is NOT the full CrewAI pipeline — it is a single, cheap, isolated LLM call to each
provider on a representative prompt, so you can read the quality difference before
committing the demo to FREE_PRIMARY=gemini. Run the full pipeline separately (crew.py)
once this looks good.

Run (inside the venv, from visual-direction-agent/):
    .\venv\Scripts\Activate.ps1
    python -m eval.compare_gemini_vs_70b
    python -m eval.compare_gemini_vs_70b "clinical skincare lab"   # any keyword

Needs in .env: a REAL GEMINI_API_KEY (starts "AIza", ~39 chars — get one at
aistudio.google.com) and NVIDIA_API_KEY (nvapi-...). Both providers are free-tier.
Token-light by design: strict JSON out, max_tokens capped, one call each.
"""
import json
import os
import re
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# litellm's nvidia_nim provider reads NVIDIA_NIM_API_KEY; mirror NVIDIA_API_KEY into it
# (same trick utils/llm.py uses) so this script works with either env name.
_nv = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
if _nv and not os.getenv("NVIDIA_NIM_API_KEY"):
    os.environ["NVIDIA_NIM_API_KEY"] = _nv

import litellm  # noqa: E402  (after env mirroring)

GEMINI_MODEL = os.getenv("GEMINI_FAST", "gemini/gemini-2.5-flash")
LLAMA_MODEL = os.getenv("NVIDIA_FALLBACK_FAST", "nvidia_nim/meta/llama-3.3-70b-instruct")

KEYWORD = sys.argv[1] if len(sys.argv) > 1 else "quiet luxury wellness"

PROMPT = (
    f'You are a brand visual-direction analyst. For the aesthetic "{KEYWORD}", return '
    "STRICT JSON only (no prose, no markdown fences) with this exact shape:\n"
    '{"palette": [{"hex": "#RRGGBB", "name": "<specific colour name>"}, ... 5 swatches],'
    ' "visual_narrative": "<100-150 words describing the visual direction>"}\n'
    "Name each colour precisely and honestly — the name must match what the hex actually is."
)

# Minimal reference palette for an objective colour-naming sanity check. Heuristic, not
# ground truth: we map each returned hex to its nearest basic family and flag when the
# model's own name sits in a clearly different family. Catches gross mislabels (brown
# called "deep red") without pretending to be a colour-science oracle.
_BASIC = {
    "white": (245, 245, 245), "cream": (245, 241, 232), "beige": (225, 210, 180),
    "tan": (210, 180, 140), "taupe": (139, 133, 120), "brown": (120, 72, 30),
    "terracotta": (200, 110, 75), "rust": (165, 78, 42), "olive": (110, 110, 60),
    "sage": (170, 180, 150), "green": (70, 130, 80), "charcoal": (54, 54, 58),
    "black": (20, 20, 20), "grey": (140, 140, 140), "slate": (69, 90, 100),
    "bluegrey": (96, 108, 116), "navy": (40, 50, 90), "blue": (70, 110, 190),
    "red": (190, 50, 50), "pink": (220, 160, 175), "purple": (120, 80, 150),
    "yellow": (220, 200, 90), "orange": (220, 140, 50),
}
# "slate"/"bluegrey" anchors stop dark blue-greys (#455A64) being mislabelled green;
# brown/rust anchors retuned so true browns (#964B00) don't read as rust. Still a
# heuristic — borderline names (taupe vs beige) may flag; trust it for gross misses only.


def _nearest_family(hex_str):
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", (hex_str or "").strip())
    if not m:
        return None
    h = m.group(1)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return min(_BASIC, key=lambda k: sum((c - v) ** 2 for c, v in zip((r, g, b), _BASIC[k])))


_TRANSIENT = ("503", "429", "unavailable", "overloaded", "high demand",
              "rate limit", "ratelimit", "timeout", "timed out")


def _ask(model, extra=None, attempts=3):
    # max_tokens 2048 (not 700): Gemini 2.5 Flash has thinking ON by default and burns
    # output budget on reasoning tokens — 700 truncated the JSON mid-palette. extra lets
    # the caller pass provider-specific kwargs (e.g. reasoning_effort="disable" for Gemini,
    # which zeroes the thinking budget so the whole allowance goes to the answer).
    base = dict(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=2048,
        temperature=0.4,
    )

    def _once():
        try:
            return litellm.completion(**base, **(extra or {}))
        except Exception as e:
            # Drop `extra` only if the kwarg itself was rejected (older litellm), NOT on a
            # transient outage — let the outer retry handle transient with extra intact.
            if extra and not any(m in str(e).lower() for m in _TRANSIENT):
                return litellm.completion(**base)
            raise

    last_err = None
    for i in range(attempts):
        try:
            t0 = time.time()
            resp = _once()
            dt = time.time() - t0
            text = resp.choices[0].message.content or ""
            # strip accidental ```json fences if a model adds them
            text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
            try:
                data = json.loads(text)
            except Exception:
                data = None
            return data, text, dt
        except Exception as e:
            last_err = e
            # Retry transient free-tier hiccups (Gemini 503 'high demand', 429, timeouts).
            if i < attempts - 1 and any(m in str(e).lower() for m in _TRANSIENT):
                wait = 4 * (i + 1)  # 4s, then 8s
                print(f"  transient ({type(e).__name__}); retry {i + 1}/{attempts - 1} in {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise last_err  # unreachable; satisfies linters


def _report(label, model, extra=None):
    print(f"\n{'='*70}\n{label}  ({model})\n{'='*70}")
    try:
        data, raw, dt = _ask(model, extra)
    except Exception as e:
        print(f"  CALL FAILED: {type(e).__name__}: {str(e)[:300]}")
        return
    print(f"  latency: {dt:.1f}s")
    if not data:
        print("  ⚠ output was not valid JSON — raw below:\n" + raw[:800])
        return
    print("  PALETTE — hex | model name | nearest family | flag")
    for sw in data.get("palette", []):
        hx, nm = sw.get("hex", "?"), sw.get("name", "?")
        fam = _nearest_family(hx)
        flag = ""
        if fam and fam.lower() not in nm.lower() and nm.lower() not in fam.lower():
            flag = f"  ⚠ name says '{nm}', hex is ~{fam}"
        print(f"    {hx:<9} | {nm:<22} | {fam or 'n/a':<11} |{flag}")
    narr = (data.get("visual_narrative") or "").strip()
    wc = len(narr.split())
    band = "✓ in 100-150 band" if 100 <= wc <= 150 else f"⚠ outside 100-150 band ({wc})"
    print(f"\n  visual_narrative: {wc} words  [{band}]")
    print("  " + narr[:600] + ("..." if len(narr) > 600 else ""))


if __name__ == "__main__":
    print(f'Keyword: "{KEYWORD}"')
    print("Reading both on: colour-name accuracy (⚠ = mislabel) + narrative word count.")
    # reasoning_effort="disable" turns off Gemini 2.5 Flash thinking for this structured
    # call — no truncation, faster, and representative of how the pipeline would use it.
    _report("GEMINI 2.5 FLASH", GEMINI_MODEL, extra={"reasoning_effort": "disable"})
    _report("LLAMA 3.3 70B (current free primary)", LLAMA_MODEL)
    print("\nDone. Fewer ⚠ flags + a narrative in the 100-150 band = the better engine here.")
