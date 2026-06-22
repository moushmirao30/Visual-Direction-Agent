"""
eval/ab_image_backends.py
A/B test: HuggingFace FLUX.1-schnell (current) vs NVIDIA FLUX.2-klein-4B.

Why this script exists:
  We are deciding whether to swap the moodboard image backend. The honest way to
  decide is NOT to trust release notes — it's to render the SAME prompts through
  both models and look at them side by side. This produces a contact sheet you
  judge by eye, plus per-image latency, so the choice is evidence-based.

What it does:
  1. Takes a fixed list of moodboard prompts (controlled + repeatable — no LLM
     cost, so the comparison isolates the image models only).
  2. Renders each through BOTH backends:
       - HF: reuses the EXACT production path (tools.image_gen_tool) so what you
         see is what the pipeline actually produces today.
       - NVIDIA: calls the FLUX.2-klein-4b serverless endpoint.
  3. Saves PNGs to eval/ab_images/ and writes comparison.html — rows = prompts,
     columns = [schnell | klein] — for a direct side-by-side, with latencies.

Requirements:
  HF_TOKEN          (already in your .env — current backend)
  NVIDIA_API_KEY    (or NVIDIA_NIM_API_KEY) — get a free nvapi-... key at build.nvidia.com

IMPORTANT — endpoint may need a one-line tweak:
  The hosted invoke URL and which optional fields (width/height/cfg_scale) the
  serverless endpoint accepts can change. Defaults below follow NVIDIA's documented
  shape. If a call 4xx's, the script prints NVIDIA's raw error body — copy the exact
  invoke_url + payload from your model's "Python" sample on
  https://build.nvidia.com/black-forest-labs/flux_2-klein-4b and adjust NVIDIA_INVOKE_URL
  / _nvidia_payload() below. Nothing else needs to change.

Run from visual-direction-agent/ with venv active:
  python -m eval.ab_image_backends                 # all prompts, both backends
  python -m eval.ab_image_backends --limit 2       # quick smoke (first 2 prompts)
  python -m eval.ab_image_backends --nvidia-only   # only render klein (debug the endpoint)
  python -m eval.ab_image_backends --steps 6       # klein steps (default 4)
"""

import os
import sys
import time
import base64
import shutil
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

OUT_DIR = Path(__file__).resolve().parent / "ab_images"

# ── NVIDIA endpoint config (edit here if NVIDIA changes the shape) ──────────────
# Hosted serverless invoke URL for FLUX.2-klein-4b. Override with env if needed.
NVIDIA_INVOKE_URL = os.getenv(
    "NVIDIA_FLUX_URL",
    "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b",
)


# ── Fixed comparison prompts ───────────────────────────────────────────────────
# Built from the quiet-luxury-wellness direction (the flagship demo case) so the
# comparison stresses exactly what your Agent 05 prompts encode: specific surfaces,
# diffuse light, restrained warm-neutral palette, matte materials, negative space.
PROMPTS = [
    "single amber glass apothecary vessel on raw limestone surface, diffuse morning "
    "light, warm cream and deep charcoal palette, extreme negative space, matte finish, "
    "minimal editorial product photography, quiet luxury wellness aesthetic",

    "close-up of hands holding a smooth ceramic bowl, linen fabric background, soft "
    "natural side light, taupe and sage grey-green tones, generous empty space, "
    "tactile matte texture, restrained editorial photography",

    "flat lay of folded undyed linen and a matte stone tile on warm cream paper, "
    "overhead diffuse light, low-saturation neutral palette, no gloss, no props, "
    "spacious composition, premium minimalist still life",

    "a single dried branch casting a soft shadow on a textured plaster wall, warm "
    "neutral light, sand and charcoal palette, vast negative space, calm and "
    "unhurried mood, fine-art minimal photography",

    "matte glass serum bottle on brushed stone, shallow depth of field, warm diffuse "
    "studio light, cream/taupe/charcoal palette, no text, no people, editorial "
    "luxury skincare aesthetic, generous margins",
]


# ── HF backend (reuse the production path verbatim) ─────────────────────────────

def gen_hf(prompt: str, seed: int) -> tuple[str | None, float, str | None]:
    """Returns (saved_path, seconds, error). Reuses tools.image_gen_tool."""
    t0 = time.time()
    try:
        from tools.image_gen_tool import generate_via_huggingface
        path = generate_via_huggingface(prompt, seed=seed)
        dt = round(time.time() - t0, 1)
        if not path:
            return None, dt, "HF returned no image (check HF_TOKEN / model availability)"
        return path, dt, None
    except Exception as e:
        return None, round(time.time() - t0, 1), f"{type(e).__name__}: {e}"


# ── NVIDIA backend (FLUX.2-klein-4b) ───────────────────────────────────────────

def _nvidia_key() -> str | None:
    return os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")


def _nvidia_payload(prompt: str, seed: int, steps: int, width: int, height: int) -> dict:
    """
    Documented core fields are prompt/seed/steps. width/height/cfg_scale are commonly
    accepted by NVIDIA visual-genai endpoints; if the endpoint rejects an extra field
    its error body will name it — drop it here and re-run.
    """
    return {
        "prompt": prompt,
        "seed": seed,
        "steps": steps,
        "width": width,
        "height": height,
        # FLUX.2-klein is distilled: the endpoint enforces cfg_scale == 1.0 exactly
        # (guidance is baked in, like schnell). Any other value 422s.
        "cfg_scale": 1.0,
    }


def gen_nvidia(prompt: str, seed: int, steps: int, width: int, height: int,
               idx: int) -> tuple[str | None, float, str | None]:
    """Returns (saved_path, seconds, error). Calls FLUX.2-klein-4b, decodes base64."""
    key = _nvidia_key()
    if not key:
        return None, 0.0, "NVIDIA_API_KEY (or NVIDIA_NIM_API_KEY) not set"

    t0 = time.time()
    try:
        import requests
        resp = requests.post(
            NVIDIA_INVOKE_URL,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            json=_nvidia_payload(prompt, seed, steps, width, height),
            timeout=120,
        )
        dt = round(time.time() - t0, 1)

        if resp.status_code >= 400:
            # Loud, specific failure — show NVIDIA's own message so the fix is obvious.
            return None, dt, f"HTTP {resp.status_code}: {resp.text[:400]}"

        body = resp.json()
        # NVIDIA visual-genai returns artifacts[0].base64; tolerate a couple of shapes.
        b64, finish = None, None
        if isinstance(body, dict):
            arts = body.get("artifacts")
            if arts and isinstance(arts, list):
                b64 = arts[0].get("base64") or arts[0].get("b64_json")
                finish = arts[0].get("finishReason")
            b64 = b64 or body.get("image") or body.get("b64_json")
        # NVIDIA's hosted safety filter blocks some benign prompts (notably 'hands',
        # skin, bodies) and returns an empty image with finishReason=CONTENT_FILTERED.
        # Flag it distinctly — it's a coverage limitation of the backend, not a code bug.
        if finish and finish != "SUCCESS" and not b64:
            return None, dt, f"CONTENT_FILTERED by NVIDIA safety filter (finishReason={finish})"
        if not b64:
            return None, dt, f"unexpected response shape: {str(body)[:300]}"

        out = OUT_DIR / f"klein_{idx}.png"
        out.write_bytes(base64.b64decode(b64))
        return str(out), dt, None
    except Exception as e:
        return None, round(time.time() - t0, 1), f"{type(e).__name__}: {e}"


# ── Contact sheet ──────────────────────────────────────────────────────────────

def write_html(rows: list[dict]) -> Path:
    """rows: [{prompt, hf_path, hf_t, hf_err, nv_path, nv_t, nv_err}]"""
    def cell(path, t, err):
        if path:
            # Reference by filename — HTML sits in the same folder as the images.
            return f'<img src="{Path(path).name}"><div class="t">{t}s</div>'
        return f'<div class="err">FAILED<br><small>{(err or "")[:200]}</small></div>'

    html = ["<!doctype html><meta charset=utf-8><title>FLUX A/B</title>",
            "<style>body{font-family:system-ui;background:#f5f1e8;color:#2b2b2b;margin:24px}"
            "h1{font-weight:600}table{border-collapse:collapse;width:100%}"
            "td,th{border:1px solid #d8c7ae;padding:10px;vertical-align:top}"
            "img{width:320px;height:320px;object-fit:cover;display:block;border-radius:4px}"
            ".p{max-width:320px;font-size:13px;color:#6f6a60}.t{font-size:12px;color:#9b8c7d;margin-top:4px}"
            ".err{color:#a33;font-size:12px;width:320px}th{background:#ece4d4}</style>",
            "<h1>FLUX.1-schnell (HF) vs FLUX.2-klein-4B (NVIDIA)</h1>",
            "<p>Judge by eye: prompt adherence (palette, surface, light), composition, "
            "and overall fit to the quiet-luxury-wellness brief.</p>",
            "<table><tr><th>Prompt</th><th>FLUX.1-schnell (current)</th>"
            "<th>FLUX.2-klein-4B (NVIDIA)</th></tr>"]
    for r in rows:
        html.append(
            f'<tr><td class="p">{r["prompt"]}</td>'
            f'<td>{cell(r["hf_path"], r["hf_t"], r["hf_err"])}</td>'
            f'<td>{cell(r["nv_path"], r["nv_t"], r["nv_err"])}</td></tr>'
        )
    html.append("</table>")
    path = OUT_DIR / "comparison.html"
    path.write_text("\n".join(html), encoding="utf-8")
    return path


# ── Runner ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="A/B test image backends")
    ap.add_argument("--limit", type=int, default=None, help="Only first N prompts")
    ap.add_argument("--steps", type=int, default=4, help="klein inference steps (default 4)")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--hf-only", action="store_true")
    ap.add_argument("--nvidia-only", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompts = PROMPTS[:args.limit] if args.limit else PROMPTS

    rows, hf_times, nv_times = [], [], []
    for i, p in enumerate(prompts):
        seed = 42 + i * 7
        print(f"\n[{i+1}/{len(prompts)}] {p[:60]}...")

        hf_path = hf_err = nv_path = nv_err = None
        hf_t = nv_t = "—"

        if not args.nvidia_only:
            hf_path, hf_t, hf_err = gen_hf(p, seed)
            # HF saves into moodboard_cache/, but the contact sheet lives in ab_images/
            # and references images by bare filename. Copy the HF render in so the sheet
            # is self-contained and the images actually display in the browser.
            if hf_path:
                local = OUT_DIR / f"schnell_{i}.png"
                try:
                    shutil.copyfile(hf_path, local)
                    hf_path = str(local)
                except Exception as e:
                    hf_err = f"render ok but copy failed: {e}"
                    hf_path = None
            print(f"  HF schnell : {'OK ' + str(hf_t) + 's' if hf_path else 'FAIL — ' + str(hf_err)}")
            if isinstance(hf_t, (int, float)): hf_times.append(hf_t)

        if not args.hf_only:
            nv_path, nv_t, nv_err = gen_nvidia(p, seed, args.steps, args.width, args.height, i)
            print(f"  NV klein   : {'OK ' + str(nv_t) + 's' if nv_path else 'FAIL — ' + str(nv_err)}")
            if isinstance(nv_t, (int, float)) and nv_path: nv_times.append(nv_t)

        rows.append({"prompt": p, "hf_path": hf_path, "hf_t": hf_t, "hf_err": hf_err,
                     "nv_path": nv_path, "nv_t": nv_t, "nv_err": nv_err})

    html_path = write_html(rows)

    def avg(x): return f"{round(sum(x) / len(x), 1)}s" if x else "n/a"
    print("\n" + "=" * 60)
    print("  A/B COMPLETE")
    print(f"  HF schnell: {sum(1 for r in rows if r['hf_path'])}/{len(rows)} ok"
          f" | avg {avg(hf_times)}")
    print(f"  NV klein  : {sum(1 for r in rows if r['nv_path'])}/{len(rows)} ok"
          f" | avg {avg(nv_times)}")
    print(f"  Open the contact sheet: {html_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
