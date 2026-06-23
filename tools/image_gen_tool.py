"""
tools/image_gen_tool.py
Image generation tool for Agent 05 (Moodboard Generator).

Uses HuggingFace Inference API with FLUX.1-schnell via InferenceClient.
Returns local .png file paths saved to moodboard_cache/.
Streamlit displays these via st.image(path).

Required env var:
  HF_TOKEN — from https://huggingface.co/settings/tokens (free Read token)
"""

import os
import hashlib
from pathlib import Path

from crewai.tools import tool

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "moodboard_cache"
CACHE_DIR.mkdir(exist_ok=True)

# ── Config ─────────────────────────────────────────────────────────────────────
HF_MODEL = "black-forest-labs/FLUX.1-schnell"

# Which backend generates images. HuggingFace FLUX now returns 402 (paid) on this token,
# so this is the single swap-point for a free replacement (cloudflare / nvidia / pollinations
# / together) once a key is wired. Select via IMAGE_BACKEND in .env.
IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "huggingface").strip().lower()

# Cloudflare Workers AI (free tier ~100k images/day) — flux-1-schnell, the same model HF
# used. Needs CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN (token scoped to "Workers AI").
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CF_MODEL = os.getenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
CF_STEPS = int(os.getenv("CLOUDFLARE_IMAGE_STEPS", "6"))  # schnell max 8; higher = better/slower

# Seed counter — incremented per call for visual diversity across panels
_seed_counter = [42]


# ── Image generation ───────────────────────────────────────────────────────────

def generate_via_huggingface(prompt: str, seed: int = 42) -> str | None:
    """
    Generates an image via HuggingFace InferenceClient (FLUX.1-schnell).
    Saves the result to moodboard_cache/ and returns the file path.
    Returns None on failure.

    Uses huggingface_hub.InferenceClient — already installed as a
    dependency of sentence-transformers, no additional package needed.
    """
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("[WARN] HF_TOKEN not set — cannot generate images")
        return None

    # Deterministic filename — skip re-generation if already cached
    prompt_hash = hashlib.md5(f"{prompt}{seed}".encode()).hexdigest()[:10]
    output_path = CACHE_DIR / f"panel_{prompt_hash}.png"

    if output_path.exists():
        print(f"[INFO] Using cached: {output_path.name}")
        return str(output_path)

    try:
        from huggingface_hub import InferenceClient

        client = InferenceClient(
            model=HF_MODEL,
            token=hf_token,
            timeout=90,
        )

        image = client.text_to_image(
            prompt=prompt,
            width=1024,
            height=1024,
        )

        # InferenceClient returns a PIL Image object
        image.save(str(output_path))
        print(f"[INFO] Image saved: {output_path.name}")
        return str(output_path)

    except Exception as e:
        print(f"[WARN] Image generation error: {e}")
        return None


def generate_via_cloudflare(prompt: str, seed: int = 42) -> str | None:
    """
    Generate an image via Cloudflare Workers AI (FLUX.1-schnell), save to moodboard_cache/.
    Free tier ~100k requests/day. Returns the local PNG path, or None on failure.

    Cloudflare REST API returns base64 JPEG under result.image; we decode and re-save as
    PNG so the file matches its .png extension and serves cleanly through the API/UI.

    Needs env: CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN (token scoped to Workers AI).
    """
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        print("[WARN] CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN not set — cannot generate images")
        return None

    prompt_hash = hashlib.md5(f"cf{prompt}{seed}".encode()).hexdigest()[:10]
    output_path = CACHE_DIR / f"panel_{prompt_hash}.png"
    if output_path.exists():
        print(f"[INFO] Using cached: {output_path.name}")
        return str(output_path)

    try:
        import base64
        import io
        import requests
        from PIL import Image

        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_MODEL}"
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
            json={"prompt": prompt, "steps": CF_STEPS, "seed": seed},
            timeout=90,
        )
        if resp.status_code != 200:
            print(f"[WARN] Cloudflare image error: HTTP {resp.status_code} {resp.text[:200]}")
            return None

        b64 = (resp.json().get("result") or {}).get("image")
        if not b64:
            print(f"[WARN] Cloudflare returned no image: {str(resp.json())[:200]}")
            return None

        Image.open(io.BytesIO(base64.b64decode(b64))).save(str(output_path))
        print(f"[INFO] Image saved: {output_path.name}")
        return str(output_path)

    except Exception as e:
        print(f"[WARN] Cloudflare image generation error: {e}")
        return None


# ── Backend dispatcher ───────────────────────────────────────────────────────

def generate_image(prompt: str, seed: int = 42) -> str | None:
    """
    Single place to swap image providers. Returns a local PNG path, or None on failure.
    Select with IMAGE_BACKEND in .env.
    """
    if IMAGE_BACKEND