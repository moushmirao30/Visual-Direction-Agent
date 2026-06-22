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


# ── CrewAI Tool ────────────────────────────────────────────────────────────────

@tool("generate_moodboard_image")
def generate_moodboard_image(prompt: str) -> str:
    """
    Generates a moodboard image from a visual design prompt.
    Returns a local file path to the generated PNG image.

    Craft a specific, visual prompt using this structure:
      [subject], [surface/material], [lighting], [colour palette], [composition], [mood/style]

    Example:
      "single amber glass vessel on raw limestone surface, diffuse morning light,
       deep charcoal and warm cream colour palette, extreme negative space,
       matte finish, minimal editorial photography, luxury wellness brand aesthetic"

    Be specific — name surfaces, describe lighting, reference palette colours.
    Avoid generic terms like 'beautiful' or 'luxury' alone without specifics.
    """
    seed = _seed_counter[0]
    _seed_counter[0] += 7

    result = generate_via_huggingface(prompt, seed=seed)
    if result:
        return f"FILE::{result}"

    return f"ERROR::Image generation failed for prompt: {prompt[:80]}..."


def get_image_gen_tool():
    """Returns the generate_moodboard_image tool for use in agent definitions."""
    return generate_moodboard_image


# ── Batch utility (used by crew.py) ───────────────────────────────────────────

def generate_images_batch(prompts: list[str]) -> list[dict]:
    """
    Generates multiple images from a list of prompts.
    Called by crew.py after Agent 05 has crafted the prompts.

    Returns list of:
      {"prompt": str, "path": str, "source": "huggingface" | "error"}
    """
    results = []
    for i, prompt in enumerate(prompts):
        seed = 42 + (i * 7)
        path = generate_via_huggingface(prompt, seed=seed)
        if path:
            results.append({"prompt": prompt, "path": path, "source": "huggingface"})
        else:
            results.append({"prompt": prompt, "path": "", "source": "error"})
    return results
