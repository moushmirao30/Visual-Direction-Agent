"""
utils/color_validator.py
Deterministic semantic validation for palette colours and harmony claims.

Why this exists:
  The schema gate (Pydantic) proves STRUCTURE — hex format, field presence.
  It cannot prove TRUTH. Three real runs shipped palettes like:
      #FF9900 labeled "Burnt Orange"   (that's pure web orange; burnt ≈ #BF5700)
      #F5DEB3 labeled "Golden Brown"   (that's CSS `wheat`, a pale cream)
      #8BC34A labeled "Deep Teal"      (that's Material light GREEN, hue 88°)
  ...and a Do-rule claiming "analogous colours" over a near-complementary pair.

  Every one of those claims is checkable in code: convert hex → HSL, compare
  against what the colour's own name implies. Rule: any claim that CAN be
  checked deterministically must never be left to a prompt.

How it plugs in:
  agent_04's _parse_and_validate() calls validate_report_semantics() after the
  schema passes. Errors are returned as text and fed into the existing retry
  loop, so the LLM gets specific, actionable feedback ("#8BC34A has hue 88°
  (green); 'teal' requires 160–200°").

Design choices:
  - stdlib only (colorsys) — no new dependencies.
  - Conservative: unknown colour names (brand-invented, e.g. 'AURU Dawn') are
    NOT validated. We only fail on confident contradictions, never on gaps in
    the lexicon. False negatives are acceptable; false positives are not.
"""

import re
import colorsys

# ── Hex → HSL ────────────────────────────────────────────────────────────────

def hex_to_hsl(hex_code: str) -> tuple[float, float, float]:
    """#RRGGBB → (hue 0–360, saturation 0–1, lightness 0–1)."""
    h = hex_code.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return hue * 360.0, sat, light


# ── Colour-term lexicon ──────────────────────────────────────────────────────
# term: (hue_ranges_or_None, s_min, s_max, l_min, l_max)
# hue_ranges is a list of (lo, hi) in degrees; None = achromatic (any hue,
# but saturation must be low). Ranges are deliberately GENEROUS — this is a
# contradiction detector, not a taste enforcer.

_T = {
    # reds / warm
    "red":        ([(345, 360), (0, 15)], 0.35, 1.0, 0.20, 0.70),
    "crimson":    ([(335, 360), (0, 10)], 0.40, 1.0, 0.20, 0.60),
    "scarlet":    ([(350, 360), (0, 20)], 0.45, 1.0, 0.30, 0.65),
    "brick":      ([(0, 25)],             0.25, 0.85, 0.25, 0.55),
    "terracotta": ([(8, 32)],             0.25, 0.90, 0.30, 0.68),
    "rust":       ([(8, 35)],             0.35, 1.0, 0.22, 0.50),
    "coral":      ([(3, 25)],             0.40, 1.0, 0.55, 0.80),
    "salmon":     ([(3, 25)],             0.35, 1.0, 0.60, 0.85),
    "orange":     ([(15, 45)],            0.30, 1.0, 0.25, 0.75),
    "peach":      ([(18, 42)],            0.30, 1.0, 0.65, 0.92),
    "apricot":    ([(20, 45)],            0.30, 1.0, 0.60, 0.88),
    "amber":      ([(32, 52)],            0.40, 1.0, 0.35, 0.70),
    "gold":       ([(38, 56)],            0.30, 1.0, 0.35, 0.75),
    "golden":     ([(30, 56)],            0.30, 1.0, 0.30, 0.80),
    "honey":      ([(30, 50)],            0.30, 1.0, 0.45, 0.75),
    "caramel":    ([(22, 45)],            0.25, 0.90, 0.35, 0.68),
    "mustard":    ([(42, 60)],            0.35, 1.0, 0.32, 0.62),
    "yellow":     ([(45, 68)],            0.35, 1.0, 0.35, 0.85),
    # browns / earth
    "brown":      ([(10, 45)],            0.10, 1.0, 0.10, 0.48),
    "chocolate":  ([(10, 40)],            0.15, 1.0, 0.10, 0.40),
    "coffee":     ([(15, 45)],            0.10, 0.80, 0.10, 0.40),
    "espresso":   ([(10, 45)],            0.05, 0.80, 0.05, 0.28),
    "walnut":     ([(10, 45)],            0.10, 0.80, 0.12, 0.42),
    "mahogany":   ([(0, 30)],             0.15, 0.90, 0.12, 0.42),
    "copper":     ([(12, 40)],            0.30, 1.0, 0.30, 0.62),
    "bronze":     ([(20, 48)],            0.20, 0.90, 0.28, 0.58),
    "tan":        ([(24, 48)],            0.15, 0.75, 0.55, 0.82),
    "beige":      ([(28, 60)],            0.05, 0.55, 0.68, 0.92),
    "sand":       ([(32, 58)],            0.10, 0.65, 0.58, 0.86),
    "khaki":      ([(42, 72)],            0.10, 0.60, 0.45, 0.80),
    "cream":      ([(30, 62)],            0.05, 0.75, 0.84, 0.98),
    "ivory":      ([(35, 65)],            0.05, 0.75, 0.86, 0.99),
    "bone":       ([(30, 65)],            0.03, 0.55, 0.82, 0.97),
    "linen":      ([(25, 60)],            0.03, 0.55, 0.82, 0.97),
    "wheat":      ([(30, 55)],            0.20, 0.90, 0.70, 0.92),
    "taupe":      ([(18, 60)],            0.03, 0.32, 0.30, 0.68),
    # greens
    "lime":       ([(72, 108)],           0.40, 1.0, 0.35, 0.75),
    "green":      ([(72, 165)],           0.15, 1.0, 0.12, 0.80),
    "olive":      ([(52, 92)],            0.15, 0.90, 0.18, 0.50),
    "moss":       ([(62, 112)],           0.12, 0.75, 0.20, 0.55),
    "forest":     ([(88, 155)],           0.20, 1.0, 0.10, 0.38),
    "emerald":    ([(128, 168)],          0.40, 1.0, 0.22, 0.62),
    "mint":       ([(108, 172)],          0.25, 1.0, 0.60, 0.92),
    "sage":       ([(62, 172)],           0.03, 0.35, 0.22, 0.78),
    "seafoam":    ([(138, 182)],          0.20, 0.90, 0.60, 0.90),
    # teals / blues
    "teal":       ([(160, 202)],          0.25, 1.0, 0.12, 0.60),
    "turquoise":  ([(158, 192)],          0.30, 1.0, 0.30, 0.75),
    "aqua":       ([(168, 202)],          0.30, 1.0, 0.40, 0.85),
    "cyan":       ([(172, 202)],          0.35, 1.0, 0.40, 0.85),
    "sky":        ([(188, 216)],          0.30, 1.0, 0.58, 0.90),
    "azure":      ([(195, 225)],          0.35, 1.0, 0.40, 0.80),
    "blue":       ([(198, 252)],          0.20, 1.0, 0.15, 0.80),
    "denim":      ([(198, 232)],          0.18, 0.75, 0.25, 0.60),
    "cobalt":     ([(208, 240)],          0.45, 1.0, 0.25, 0.60),
    "navy":       ([(198, 252)],          0.25, 1.0, 0.08, 0.30),
    "midnight":   ([(198, 262)],          0.15, 1.0, 0.05, 0.25),
    "indigo":     ([(228, 278)],          0.30, 1.0, 0.15, 0.60),
    "slate":      ([(178, 262)],          0.03, 0.28, 0.22, 0.62),
    # purples / pinks
    "purple":     ([(258, 302)],          0.20, 1.0, 0.15, 0.75),
    "violet":     ([(258, 302)],          0.25, 1.0, 0.25, 0.80),
    "plum":       ([(275, 335)],          0.15, 0.85, 0.18, 0.52),
    "lavender":   ([(238, 292)],          0.15, 0.90, 0.62, 0.92),
    "lilac":      ([(255, 305)],          0.15, 0.90, 0.62, 0.92),
    "magenta":    ([(288, 332)],          0.40, 1.0, 0.30, 0.75),
    "fuchsia":    ([(288, 332)],          0.45, 1.0, 0.35, 0.75),
    "pink":       ([(312, 360), (0, 8)],  0.25, 1.0, 0.55, 0.92),
    "blush":      ([(335, 360), (0, 25)], 0.10, 0.75, 0.70, 0.94),
    "rose":       ([(315, 355)],          0.25, 1.0, 0.35, 0.85),
    "burgundy":   ([(320, 360), (0, 12)], 0.25, 1.0, 0.10, 0.35),
    "maroon":     ([(320, 360), (0, 15)], 0.25, 1.0, 0.10, 0.35),
    "wine":       ([(315, 360), (0, 12)], 0.25, 1.0, 0.12, 0.38),
    # achromatics (hue irrelevant; saturation must be LOW)
    "white":      (None, 0.0, 0.25, 0.92, 1.0),
    "black":      (None, 0.0, 0.60, 0.0, 0.14),
    "charcoal":   (None, 0.0, 0.22, 0.08, 0.30),
    # l_max 0.97 (not 0.82): real greyscale ramps run to near-white — Tailwind
    # gray-50 is #F9FAFB (98% L). #F7F7F7 "light grey" is standard, not "white".
    "grey":       (None, 0.0, 0.15, 0.22, 0.97),
    "gray":       (None, 0.0, 0.15, 0.22, 0.97),
    "silver":     (None, 0.0, 0.15, 0.62, 0.88),
    "ash":        (None, 0.0, 0.15, 0.35, 0.75),
    "stone":      (None, 0.0, 0.22, 0.38, 0.80),
    "graphite":   (None, 0.0, 0.20, 0.10, 0.35),
}

# modifier: (s_min, s_max, l_min, l_max) — tightens the base term's window.
_MODS = {
    "deep":     (None, None, None, 0.40),
    "dark":     (None, None, None, 0.40),
    "burnt":    (None, None, None, 0.48),
    "light":    (None, None, 0.60, None),
    "pale":     (None, None, 0.62, None),
    "soft":     (None, None, 0.55, None),
    "powder":   (None, 0.60, 0.65, None),
    "muted":    (None, 0.55, None, None),
    "dusty":    (None, 0.50, None, None),
    "washed":   (None, 0.50, 0.55, None),
    "vibrant":  (0.48, None, 0.30, 0.68),
    "vivid":    (0.60, None, 0.30, 0.68),
    "bright":   (0.55, None, 0.35, 0.75),
    "bold":     (0.45, None, 0.20, 0.70),
    "electric": (0.70, None, 0.40, 0.70),
    "neon":     (0.80, None, 0.45, 0.68),
    "rich":     (0.30, None, 0.15, 0.60),
}

_ACHROMATIC_S = 0.12  # below this, hue is meaningless — skip hue checks


def _hue_in(hue: float, ranges) -> bool:
    return any(lo <= hue <= hi for lo, hi in ranges)


def _fmt(h, s, l) -> str:
    return f"hue {h:.0f}°, sat {s:.0%}, light {l:.0%}"


def suggest_names(h: float, s: float, l: float, limit: int = 4) -> list[str]:
    """
    Returns base lexicon terms whose full HSL window contains (h, s, l).
    Gives the retry loop a concrete rename target instead of asking the LLM
    to reason about HSL — which is exactly where it thrashes. Base terms only
    (no modifiers), so suggestions are clean single words.
    """
    matches = []
    for term, (hue_ranges, s_min, s_max, l_min, l_max) in _T.items():
        if not (s_min <= s <= s_max and l_min <= l <= l_max):
            continue
        if hue_ranges is None:          # achromatic term
            if s <= _ACHROMATIC_S:
                matches.append(term)
        elif s < _ACHROMATIC_S or _hue_in(h, hue_ranges):
            matches.append(term)
    # Prefer terms whose hue-window centre is closest to the actual hue.
    def _centre_dist(term: str) -> float:
        ranges = _T[term][0]
        if ranges is None:
            return 999.0
        return min(_hue_dist(h, (lo + hi) / 2) for lo, hi in ranges)
    matches.sort(key=_centre_dist)
    return [t.title() for t in matches[:limit]]


def validate_colour_name(name: str, hex_code: str) -> str | None:
    """
    Checks that a colour's name is consistent with its hex value.
    Returns an error string on a confident contradiction, else None.
    Unknown names are skipped (never fail on lexicon gaps).
    """
    try:
        h, s, l = hex_to_hsl(hex_code)
    except Exception:
        return None  # hex format is the schema's job

    tokens = [t for t in re.split(r"[^a-z]+", name.lower()) if t]
    base = next((t for t in reversed(tokens) if t in _T), None)
    if base is None:
        return None  # brand-invented name — not validatable

    hue_ranges, s_min, s_max, l_min, l_max = _T[base]
    applied = [base]
    for t in tokens:
        if t in _MODS and t != base:
            m_smin, m_smax, m_lmin, m_lmax = _MODS[t]
            if m_smin is not None: s_min = max(s_min, m_smin)
            if m_smax is not None: s_max = min(s_max, m_smax)
            if m_lmin is not None: l_min = max(l_min, m_lmin)
            if m_lmax is not None: l_max = min(l_max, m_lmax)
            applied.append(t)

    problems = []
    if hue_ranges is not None:
        if s >= _ACHROMATIC_S and not _hue_in(h, hue_ranges):
            expect = " or ".join(f"{lo:.0f}–{hi:.0f}°" for lo, hi in hue_ranges)
            problems.append(f"hue is {h:.0f}° but '{base}' requires {expect}")
        if s < s_min:
            problems.append(f"saturation {s:.0%} is below the {s_min:.0%} '{'/'.join(applied)}' requires")
    else:
        if s > s_max:
            problems.append(f"'{base}' is a neutral but saturation is {s:.0%} (max {s_max:.0%})")
    if s > s_max and hue_ranges is not None:
        problems.append(f"saturation {s:.0%} exceeds the {s_max:.0%} '{'/'.join(applied)}' allows")
    if l < l_min:
        problems.append(f"lightness {l:.0%} is below the {l_min:.0%} '{'/'.join(applied)}' requires")
    if l > l_max:
        problems.append(f"lightness {l:.0%} exceeds the {l_max:.0%} '{'/'.join(applied)}' allows")

    if problems:
        msg = (f"Colour '{name}' = {hex_code} ({_fmt(h, s, l)}) contradicts its name: "
               + "; ".join(problems) + ". ")
        suggestions = suggest_names(h, s, l)
        if suggestions:
            msg += (f"For this hex, an accurate name would be one of: "
                    f"{', '.join(suggestions)}. Rename the colour to one of these "
                    f"(keep the same hex_code), or change the hex to match '{name}'.")
        else:
            msg += ("Either rename the colour to what the hex actually is, or "
                    "change the hex to match the name.")
        return msg
    return None


# ── Harmony claims vs actual palette geometry ────────────────────────────────

def _chromatic_hues(palette: list[dict]) -> list[tuple[str, float]]:
    out = []
    for sw in palette:
        try:
            h, s, l = hex_to_hsl(sw.get("hex_code", ""))
        except Exception:
            continue
        if s >= 0.20 and 0.10 <= l <= 0.90:  # neutrals don't participate in harmony
            out.append((sw.get("hex_code", ""), h))
    return out


def _hue_dist(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def validate_harmony_claims(rules_text: str, palette: list[dict]) -> str | None:
    """
    If the report CLAIMS a colour-harmony scheme, verify the palette's actual
    hue geometry supports it. Only fires when a claim is made.
    """
    text = rules_text.lower()
    hues = _chromatic_hues(palette)
    if len(hues) < 2:
        return None

    pairs = [(a, b) for i, a in enumerate(hues) for b in hues[i + 1:]]
    max_pair = max(pairs, key=lambda p: _hue_dist(p[0][1], p[1][1]))
    max_d = _hue_dist(max_pair[0][1], max_pair[1][1])

    if "analogous" in text and max_d > 70:
        return (f"A rule claims ANALOGOUS colours, but {max_pair[0][0]} (hue {max_pair[0][1]:.0f}°) and "
                f"{max_pair[1][0]} (hue {max_pair[1][1]:.0f}°) are {max_d:.0f}° apart — that is a "
                f"contrast/complementary relationship, not analogous (≤70°). Either fix the palette "
                f"or state the actual scheme (e.g. 'complementary accent').")
    if "monochromatic" in text and max_d > 25:
        return (f"A rule claims MONOCHROMATIC, but palette hues span {max_d:.0f}° "
                f"({max_pair[0][0]} vs {max_pair[1][0]}). Monochromatic requires one hue family (≤25°).")
    if "complementary" in text and "analogous" not in text:
        if not any(150 <= _hue_dist(a[1], b[1]) <= 210 for a, b in pairs):
            return (f"A rule claims COMPLEMENTARY colours, but no chromatic pair is 150–210° apart "
                    f"(max separation is {max_d:.0f}°).")
    return None


# ── Report-level entry point ─────────────────────────────────────────────────

def autocorrect_palette_names(report_dict: dict) -> tuple[dict, list[str]]:
    """
    Deterministically repairs colour NAME contradictions in place-safely.

    When a swatch's hex is valid but its name contradicts it, and the lexicon
    can name that hex, the name is rewritten to the top verified suggestion
    (every suggestion is guaranteed to pass validate_colour_name for that hex).
    The hex — the actual design intent — is never touched.

    Returns (new_report_dict, corrections) where corrections is a human-readable
    log. Issues code cannot repair (hex that no lexicon term fits, harmony-claim
    geometry) are left untouched for the LLM retry loop to handle.
    """
    palette = report_dict.get("palette", [])
    if not palette:
        return report_dict, []

    corrections: list[str] = []
    new_palette = []
    for sw in palette:
        name, hex_code = sw.get("name", ""), sw.get("hex_code", "")
        if validate_colour_name(name, hex_code) is not None:
            try:
                sug = suggest_names(*hex_to_hsl(hex_code))
            except Exception:
                sug = []
            if sug:
                sw = {**sw, "name": sug[0]}
                corrections.append(f"'{name}' → '{sug[0]}' for {hex_code}")
        new_palette.append(sw)

    if not corrections:
        return report_dict, []
    return {**report_dict, "palette": new_palette}, corrections


def validate_report_semantics(report_dict: dict) -> str | None:
    """
    Runs all deterministic semantic checks on a schema-valid report dict.
    Returns a combined error string (one issue per line) or None if clean.
    Called by agent_04 after Pydantic validation; errors feed the retry loop.
    """
    errors = []

    for sw in report_dict.get("palette", []):
        err = validate_colour_name(sw.get("name", ""), sw.get("hex_code", ""))
        if err:
            errors.append(err)

    rules_text = " ".join(
        report_dict.get("do_rules", []) + report_dict.get("dont_rules", [])
        + [report_dict.get("visual_narrative", ""), report_dict.get("conflicts_resolved") or ""]
    )
    harmony_err = validate_harmony_claims(rules_text, report_dict.get("palette", []))
    if harmony_err:
        errors.append(harmony_err)

    return "\n".join(errors) if errors else None
