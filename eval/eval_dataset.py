"""
eval/eval_dataset.py
The test set and the held-out ground truth.

Two things live here:

1. KEYWORDS — 13 aesthetic inputs spanning the positioning archetypes the system
   claims to handle (premium, clinical, accessible, warm, bold, dark). Each carries
   the *expected market signal* so the judge can check whether the produced
   direction actually lands in the right territory, not just whether it is
   internally pretty. A "quiet luxury wellness" brief that comes back looking like
   a budget supermarket own-brand is a failure even if every field validates.

   Why a fixed list and not random keywords?
     An eval set must be STABLE. The same inputs every run is what lets you compare
     today's score to last week's and call a change an improvement or a regression.
     13 is small for production (2026 practice is >=500 before aggregate metrics are
     trustworthy) but it is honest for a capstone and enough to surface real gaps.

2. AURU_GROUND_TRUTH — the manually-researched AURU visual direction, distilled to
   its load-bearing decisions. This is the HELD-OUT benchmark. We delete AURU from
   the knowledge base at query time (EVAL_EXCLUDE_SOURCES) and check whether the
   pipeline independently re-derives this direction. Convergence here is the only
   honest version of the demo's "the agent automates what I did by hand" claim —
   because the agent never saw the answer.
"""

# ── The evaluation keywords ────────────────────────────────────────────────────
# signal = the positioning territory a competent direction should land in.
# These are graded by the judge against the produced report.

KEYWORDS: list[dict] = [
    # The flagship case — also run separately as the held-out AURU benchmark.
    {"keyword": "quiet luxury wellness",        "signal": "premium",    "note": "Restraint, dark/neutral, editorial. Flagship demo case."},
    {"keyword": "clinical skincare science",    "signal": "clinical",   "note": "Cool, precise, lab-credible without feeling cold-dead."},
    {"keyword": "bold brutalist streetwear",    "signal": "bold",       "note": "High contrast, raw, oversized type. Opposite of quiet luxury."},
    {"keyword": "warm artisanal bakery",        "signal": "warm",       "note": "Hand-made, tactile, inviting. Warmth is correct here."},
    {"keyword": "affordable everyday essentials","signal": "accessible","note": "Friendly, clear, value-signalling. NOT premium."},
    {"keyword": "dark luxury fragrance",        "signal": "premium",    "note": "Moody, sensual, high-end. Should not read as cheap."},
    {"keyword": "playful kids edtech",          "signal": "accessible", "note": "Bright, rounded, energetic. Approachable."},
    {"keyword": "minimalist scandinavian home", "signal": "premium",    "note": "Light, airy, restrained, quality materials."},
    {"keyword": "high-energy fitness brand",    "signal": "bold",       "note": "Saturated, dynamic, motivational."},
    {"keyword": "heritage craft whiskey",       "signal": "premium",    "note": "Aged, considered, traditional, tactile."},
    {"keyword": "modern fintech app",           "signal": "accessible", "note": "Clean, trustworthy, tech-forward, not luxury."},
    {"keyword": "earthy sustainable fashion",   "signal": "warm",       "note": "Natural, muted, ethical, tactile materials."},
    {"keyword": "premium electric vehicle",     "signal": "premium",    "note": "Sleek, refined, quietly powerful, high-tech."},
]

# The held-out benchmark keyword (must match KEYWORDS[0]) and the source doc to drop.
HELD_OUT_KEYWORD = "quiet luxury wellness"
HELD_OUT_EXCLUDE_SOURCE = "auru_brand_research.txt"


# ── AURU ground truth — the held-out answer ────────────────────────────────────
# Distilled from rag/knowledge_base/auru_brand_research.txt. Only the load-bearing
# decisions are kept — the things a convergent run MUST rediscover to count as a hit.

AURU_GROUND_TRUTH = {
    "positioning_thesis": (
        "Quiet luxury through restraint — communicating quality through absence "
        "rather than excess. Evidence-forward wellness with tactile, humane design. "
        "Sits between lab-grade efficacy and boutique hospitality: never sterile, "
        "never loud."
    ),
    "palette_family": [
        "Warm Cream #F5F1E8 (background base)",
        "Stone/Sand #D8C7AE (structure)",
        "Taupe #9B8C7D (depth)",
        "Sage Grey-Green #6F7563 (secondary structure)",
        "Deep Charcoal #2B2B2B (type/near-black)",
    ],
    "palette_character": "Warm neutrals + muted sage + near-black anchor. Low saturation. No bright/botanical green, no peach/coral.",
    "typography": {
        "display": "Cormorant Garamond / DM Serif Display (editorial old-style serif)",
        "body": "DM Sans / Inter (clean humanist sans)",
        "tracking": "Generous on headings, tight on body",
    },
    "spatial": "Spacious grids, thin rules, generous margins. Negative space as a material.",
    "photography": "Hands and product on surface, close-up texture. No faces, no motion, no energy. Morning light on limestone/linen/glass.",
    "benchmark_brands_expected": ["Aesop", "Le Labo", "Bamford"],
    "must_avoid": [
        "High-saturation botanical green",
        "Warm rounded sans (Montserrat/Raleway)",
        "Peach/coral/blush",
        "Lifestyle/performative wellness photography",
        "Gloss/foil/lacquer finishes",
        "Clinical-pharmaceutical coldness",
    ],
}
