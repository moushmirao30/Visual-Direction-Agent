# ui/app.py - Streamlit UI for the Visual Direction Research Agent
#
# Layout:
#   Sidebar: keyword input, options, generate button, progress
#   Left panel: formatted visual direction report
#   Right panel: moodboard image grid (5 panels)
#
# Run:
#   streamlit run ui/app.py
#   (from inside visual-direction-agent/ with venv active)

import time
import httpx
import streamlit as st

API_BASE = "http://localhost:8000"
POLL_INTERVAL_S = 3

# -- Page config ---------------------------------------------------------------

st.set_page_config(
    page_title="Visual Direction Agent",
    page_icon="o",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  /* ---- Background ---- */
  .stApp { background-color: #F5F1ED; }
  section[data-testid="stSidebar"] { background-color: #E8E3DC; }

  /* ---- Global text: force dark on cream background ---- */
  .stApp, .stApp p, .stApp li, .stApp label,
  .stApp .stMarkdown, .stApp .stText,
  div[data-testid="stMarkdownContainer"] p,
  div[data-testid="stMarkdownContainer"] li {
    color: #2A2520 !important;
  }

  /* ---- Headings ---- */
  .stApp h1, .stApp h2, .stApp h3 {
    color: #1A1714 !important;
    font-weight: 600;
    letter-spacing: 0.01em;
  }

  /* ---- Sidebar text ---- */
  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] .stMarkdown,
  section[data-testid="stSidebar"] span {
    color: #2A2520 !important;
  }

  /* ---- Input fields: visible on cream ---- */
  .stTextInput input {
    background-color: #FDFAF7 !important;
    color: #1A1714 !important;
    border: 1px solid #C8C0B5 !important;
    border-radius: 4px;
  }
  .stTextInput input::placeholder { color: #9A948C !important; }

  /* ---- Agent step cards in empty/running state ---- */
  .agent-card {
    background: #EDE8E2;
    border: 1px solid #D5CFC8;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
    color: #2A2520;
  }
  .agent-card strong { color: #1A1714; font-size: 0.95rem; }
  .agent-card span   { color: #5A5450; font-size: 0.85rem; }

  /* ---- Running step markers ---- */
  .step-done    { color: #4A7A5A; font-weight: 700; }
  .step-active  { color: #3A3A3A; font-weight: 700; }
  .step-pending { color: #A09890; }

  /* ---- Moodboard panel label ---- */
  .panel-label {
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #6A6460;
    text-align: center;
    margin-top: 0.5rem;
    font-weight: 500;
  }

  /* ---- Colour swatches ---- */
  .swatch-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 0.6rem 0 1.2rem 0; }
  .swatch {
    width: 56px; height: 56px;
    border-radius: 5px;
    border: 1px solid rgba(0,0,0,0.10);
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  .swatch-label {
    font-size: 0.67rem;
    color: #5A5450;
    text-align: center;
    margin-top: 4px;
    font-family: 'Courier New', monospace;
    line-height: 1.3;
  }
  .swatch-wrap { display: flex; flex-direction: column; align-items: center; }

  /* ---- Blockquote (positioning statement) ---- */
  blockquote {
    border-left: 3px solid #A8B5A1 !important;
    background: #EDE8E2 !important;
    padding: 0.8rem 1rem !important;
    border-radius: 0 4px 4px 0 !important;
    color: #2A2520 !important;
    font-style: italic;
  }

  /* ---- Dividers ---- */
  hr { border-color: #D5CFC8 !important; }

  /* ---- Caption text ---- */
  .stApp .stCaption, .stApp small {
    color: #6A6460 !important;
  }

  /* ---- Expander ---- */
  .streamlit-expanderHeader {
    color: #2A2520 !important;
    background: #EDE8E2 !important;
    border: 1px solid #D5CFC8 !important;
    border-radius: 4px;
  }
  .streamlit-expanderContent {
    background: #F0EDE8 !important;
    border: 1px solid #D5CFC8 !important;
    color: #2A2520 !important;
  }

  /* ---- Info / Success / Error boxes ---- */
  div[data-testid="stAlert"] {
    border-radius: 4px !important;
  }
</style>
""", unsafe_allow_html=True)

# -- Session state -------------------------------------------------------------

for _k, _v in {
    "job_id": None, "polling": False, "status": None,
    "current_step": "", "result": None, "error": None,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# -- Helpers ------------------------------------------------------------------

def _image_url(filename: str) -> str:
    return f"{API_BASE}/moodboard/{filename}"


def _is_done(agent_num: str, current_step: str) -> bool:
    try:
        current_num = int([c for c in current_step.split() if c.isdigit()][0])
        return int(agent_num) < current_num
    except (IndexError, ValueError):
        return False


def _render_panel(panels: list, idx: int, col) -> None:
    if idx >= len(panels):
        return
    p = panels[idx]
    filename = p.get("filename", "")
    label = p.get("panel", f"Panel {idx + 1}")
    with col:
        if filename:
            try:
                st.image(_image_url(filename), use_container_width=True)
            except Exception:
                st.warning(f"Could not load: {filename}")
        else:
            st.warning("⚠ Image generation unavailable (backend failed) — prompt below.")
        st.markdown(f'<p class="panel-label">{label}</p>', unsafe_allow_html=True)
        with st.expander("Prompt", expanded=False):
            st.caption(p.get("prompt", ""))


def _post_generate(keyword: str, use_cache: bool, skip_moodboard: bool):
    try:
        r = httpx.post(
            f"{API_BASE}/generate",
            json={"keyword": keyword, "use_cache": use_cache, "skip_moodboard": skip_moodboard},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("Cannot reach the API. Is `python api.py` running on port 8000?")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def _get_status(job_id: str):
    try:
        r = httpx.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _build_report_html(report: dict, keyword: str, langsmith_url: str | None = None,
                       served: list | None = None) -> str:
    """
    Builds a standalone HTML export of the visual direction report.
    Self-contained — no external dependencies, inline CSS only.
    """
    kw = keyword.upper()

    # Palette swatches — swatch + name/hex, with the schema-required role and
    # rationale beside it (they were validated; hiding them wasted the guardrail).
    palette_html = ""
    for sw in report.get("palette", []):
        hx = sw.get("hex_code", "#CCC")
        nm = sw.get("name", "")
        role = sw.get("role", "")
        why = sw.get("rationale", "")
        palette_html += (
            f'<div style="display:flex;align-items:flex-start;gap:14px;margin:0 0 0.9rem 0;">'
            f'<div style="flex-shrink:0;width:56px;height:56px;border-radius:5px;background:{hx};'
            f'border:1px solid rgba(0,0,0,0.12);box-shadow:0 1px 3px rgba(0,0,0,0.08);"></div>'
            f'<div><div style="font-size:0.9rem;color:#1A1714;font-weight:600;">{nm} '
            f'<span style="font-family:monospace;font-weight:400;color:#6A6460;">{hx}</span></div>'
            f'<div style="font-size:0.75rem;color:#6A6460;text-transform:uppercase;'
            f'letter-spacing:0.06em;margin:2px 0;">{role}</div>'
            f'<div style="font-size:0.85rem;color:#2A2520;">{why}</div></div></div>'
        )

    # Typography
    typo = report.get("typography", {})
    typo_html = (
        f'<p style="margin:0.2rem 0;color:#2A2520;">Display: {typo.get("display_typeface","")}</p>'
        f'<p style="margin:0.2rem 0;color:#2A2520;">Body: {typo.get("body_typeface","")}</p>'
        f'<p style="margin:0.2rem 0;color:#2A2520;">Tracking: {typo.get("display_tracking","")} (display) / '
        f'{typo.get("body_tracking","")} (body)</p>'
        + (f'<p style="margin:0.2rem 0;color:#5A5450;font-size:0.88rem;">{typo.get("hierarchy_notes","")}</p>'
           if typo.get("hierarchy_notes") else "")
    ) if typo else ""

    # Photography
    photo_items = "".join(
        f'<p style="margin:0.25rem 0;color:#2A2520;">{i}. {d}</p>'
        for i, d in enumerate(report.get("photography_direction", []), 1)
    )

    # Do / Don't
    do_items = "".join(
        f'<p style="margin:0.2rem 0;color:#2A2520;font-size:0.9rem;">&#10003; {r}</p>'
        for r in report.get("do_rules", [])
    )
    dont_items = "".join(
        f'<p style="margin:0.2rem 0;color:#2A2520;font-size:0.9rem;">&#10005; {r}</p>'
        for r in report.get("dont_rules", [])
    )

    # Benchmark brands
    brands_html = "".join(
        f'<p style="font-weight:600;color:#1A1714;margin:0.5rem 0 0.1rem 0;">{b["name"]}</p>'
        f'<p style="font-size:0.88rem;color:#2A2520;margin:0 0 0.6rem 0;">{b["reference_note"]}</p>'
        for b in report.get("benchmark_brands", [])
    )

    conflicts = report.get("conflicts_resolved", "")
    conflicts_section = (
        f'<h3 style="color:#1A1714;margin-top:2rem;">Conflicts Resolved</h3>'
        f'<p style="color:#2A2520;">{conflicts}</p>'
    ) if conflicts else ""

    # Provenance stamp — which model(s) actually served this run
    served_line = f'<br>Served by {", ".join(served)}' if served else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Visual Direction — {kw}</title>
<style>
  body {{ font-family: Georgia, serif; background: #F5F1ED; color: #2A2520;
          max-width: 820px; margin: 0 auto; padding: 3rem 2rem; }}
  h1   {{ font-size: 2rem; letter-spacing: 0.08em; color: #1A1714; margin-bottom: 0.3rem; }}
  h2   {{ font-size: 1.15rem; font-weight: 700; color: #1A1714; margin: 2rem 0 0.5rem 0;
          text-transform: uppercase; letter-spacing: 0.05em; }}
  hr   {{ border: none; border-top: 1px solid #D5CFC8; margin: 1.5rem 0; }}
  blockquote {{ border-left: 3px solid #A8B5A1; background: #EDE8E2; padding: 0.8rem 1rem;
                border-radius: 0 4px 4px 0; font-style: italic; margin: 0 0 1.5rem 0; }}
  .swatch-row {{ display: flex; flex-direction: column; margin: 0.8rem 0 1.5rem 0; }}
  .do-dont {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }}
  .label {{ font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase;
             color: #6A6460; margin-bottom: 0.5rem; }}
  footer {{ margin-top: 3rem; font-size: 0.75rem; color: #9A948C; text-align: center; }}
</style>
</head>
<body>
  <h1>{kw}</h1>
  <p style="color:#6A6460;font-size:0.8rem;margin-bottom:2rem;">Visual Direction Report — Generated by Visual Direction Research Agent</p>

  <blockquote>{report.get("positioning_statement","")}</blockquote>
  <hr>

  <h2>Palette</h2>
  <div class="swatch-row">{palette_html}</div>
  <hr>

  <h2>Typography</h2>
  {typo_html}
  <hr>

  <h2>Spatial</h2>
  <p>{report.get("layout_approach","")}</p>
  <p style="color:#5A5450;font-size:0.88rem;">{report.get("negative_space_rule","")}</p>
  <hr>

  <h2>Photography</h2>
  {photo_items}
  <hr>

  <h2>Do / Don't</h2>
  <div class="do-dont">
    <div><div class="label">Do</div>{do_items}</div>
    <div><div class="label">Don't</div>{dont_items}</div>
  </div>
  <hr>

  <h2>Benchmark Brands</h2>
  {brands_html}
  <hr>

  <h2>Visual Narrative</h2>
  <p style="line-height:1.9;font-style:italic;">{report.get("visual_narrative","")}</p>

  {conflicts_section}

  <footer>
    Visual Direction Research Agent &mdash; Capstone 2026
    {"&nbsp;&nbsp;|&nbsp;&nbsp;<a href='" + langsmith_url + "' style='color:#6A6460;'>LangSmith trace ↗</a>" if langsmith_url else ""}
    {served_line}
  </footer>
</body>
</html>"""

# -- Sidebar ------------------------------------------------------------------

with st.sidebar:
    st.markdown("## Visual Direction\nResearch Agent")
    st.divider()

    keyword = st.text_input(
        "Aesthetic keyword",
        placeholder="e.g. quiet luxury wellness",
        help="Enter a brand aesthetic. The agent runs live web search + RAG retrieval.",
    )

    use_cache = st.checkbox(
        "Use cached outputs", value=True,
        help="Reuse Agent 01–04 cached results (24hr TTL). Uncheck to force a completely fresh run.",
    )

    with st.expander("Advanced options"):
        skip_moodboard = st.checkbox(
            "Skip moodboard generation", value=False,
            help="Skip Agent 05 image generation. Faster (~220s) — text report only.",
        )

    st.divider()

    generate_btn = st.button(
        "Generate",
        type="primary",
        disabled=st.session_state.polling,
        use_container_width=True,
    )

    if st.session_state.polling or st.session_state.status == "running":
        st.info(f"**{st.session_state.current_step}**")
        st.caption("Full pipeline ~4-5 min. Cached run ~2 min.")
        if st.button(
            "↻ Check progress",
            use_container_width=True,
            help="Tab was backgrounded? Click to manually refresh status.",
        ):
            st.rerun()

    if st.session_state.status == "complete" and st.session_state.result:
        timings = st.session_state.result.get("timings", {})
        st.success(f"Done in {timings.get('total', '?')}s")
        with st.expander("Agent timings"):
            for k, v in timings.items():
                if k != "total":
                    st.caption(f"{k}: {v}s")
        ls_url = st.session_state.result.get("langsmith_url")
        if ls_url:
            st.markdown(f"[LangSmith trace]({ls_url})")
        served = st.session_state.result.get("served_models") or []
        if served:
            st.caption("Served by: " + ", ".join(served))

    if st.session_state.status == "error":
        st.error("Pipeline failed. See error below.")

    st.divider()
    if st.button("Reset", use_container_width=True):
        for k in ["job_id", "polling", "status", "current_step", "result", "error"]:
            st.session_state[k] = False if k == "polling" else None
        st.rerun()

# -- Generate handler ---------------------------------------------------------

if generate_btn:
    if not keyword.strip():
        st.error("Enter an aesthetic keyword first.")
    else:
        resp = _post_generate(keyword.strip(), use_cache, skip_moodboard)
        if resp:
            st.session_state.job_id = resp["job_id"]
            st.session_state.polling = True
            st.session_state.status = "queued"
            st.session_state.current_step = "Queued"
            st.session_state.result = None
            st.session_state.error = None
            st.rerun()

# -- Polling ------------------------------------------------------------------

if st.session_state.polling and st.session_state.job_id:
    data = _get_status(st.session_state.job_id)
    if data:
        st.session_state.status = data["status"]
        st.session_state.current_step = data.get("current_step", "")
        if data["status"] == "complete":
            st.session_state.result = data["result"]
            st.session_state.polling = False
            st.rerun()
        elif data["status"] == "error":
            st.session_state.error = data.get("error", "Unknown error")
            st.session_state.polling = False
            st.rerun()
        else:
            time.sleep(POLL_INTERVAL_S)
            st.rerun()

# -- Main area ----------------------------------------------------------------

# Empty state
if st.session_state.status is None:
    st.markdown("## Visual Direction Research Agent")
    st.markdown(
        '<p style="color:#2A2520;font-size:1.05rem;line-height:1.7;">'
        "Enter an aesthetic keyword in the sidebar &mdash; e.g. <strong>quiet luxury wellness</strong>, "
        "<strong>bold brutalist tech</strong>, <strong>coastal minimal resort</strong> &mdash; and click <strong>Generate</strong>.<br><br>"
        "The 5-agent pipeline runs live web search, retrieves design theory from a curated "
        "knowledge base, synthesises a unified visual direction, validates it against a Pydantic "
        "schema, and generates a 5-panel AI moodboard."
        "</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    agents = [
        ("01", "Trend Researcher",      "Live web search via Tavily"),
        ("02", "Design Theory Analyst", "RAG over curated design knowledge"),
        ("03", "Direction Synthesiser", "Merges trend + theory outputs"),
        ("04", "Report Writer",         "Validated Pydantic schema output"),
        ("05", "Moodboard Generator",   "HuggingFace FLUX image generation"),
    ]
    row1 = st.columns(3)
    row2 = st.columns(2)
    cols = row1 + row2
    for col, (num, name, detail) in zip(cols, agents):
        with col:
            st.markdown(
                f'<div class="agent-card">'
                f'<strong>{num} &mdash; {name}</strong><br>'
                f'<span>{detail}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# Running state
elif st.session_state.status in ("queued", "running"):
    st.markdown(f'<h2 style="color:#1A1714;">Running: <em>{keyword}</em></h2>', unsafe_allow_html=True)
    steps = [
        ("01", "Trend Researcher",      "Live web search via Tavily"),
        ("02", "Design Theory Analyst", "RAG retrieval over knowledge base"),
        ("03", "Direction Synthesiser", "Merging trend + theory outputs"),
        ("04", "Report Writer",         "Structuring into validated schema"),
        ("05", "Moodboard Generator",   "Generating images via HuggingFace FLUX"),
    ]
    current = st.session_state.current_step
    for num, name, detail in steps:
        if f"Agent {num}" in current:
            css_class, marker = "step-active", "&#8594;"   # →
        elif _is_done(num, current):
            css_class, marker = "step-done",   "&#10003;"  # ✓
        else:
            css_class, marker = "step-pending", "&#9675;"  # ○
        st.markdown(
            f'<div class="agent-card" style="margin-bottom:0.4rem;">'
            f'<span class="{css_class}" style="font-size:1rem;margin-right:0.7rem;">{marker}</span>'
            f'<strong style="color:#1A1714;">{num} &mdash; {name}</strong>'
            f'<span style="color:#5A5450;margin-left:0.5rem;font-size:0.88rem;">{detail}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# Error state
elif st.session_state.status == "error":
    st.error("Pipeline failed.")
    if st.session_state.error:
        with st.expander("Error details"):
            st.code(st.session_state.error)

# Complete state
elif st.session_state.status == "complete" and st.session_state.result:
    result = st.session_state.result
    report = result.get("report", {})
    panels = result.get("moodboard_panels", [])
    TH = "#1A1714"   # headings
    TC = "#2A2520"   # body text
    TS = "#5A5450"   # secondary

    kw = result.get("keyword", "").upper()
    st.markdown(
        '<h2 style="color:' + TH + ';letter-spacing:0.06em;margin-bottom:1rem;">' + kw + '</h2>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown('<h3 style="color:' + TH + ';">Visual Direction Report</h3>', unsafe_allow_html=True)

        if report:
            pos = report.get("positioning_statement", "")
            st.markdown(
                '<div style="border-left:3px solid #A8B5A1;background:#EDE8E2;padding:0.8rem 1rem;'
                'border-radius:0 4px 4px 0;color:' + TC + ';font-style:italic;margin-bottom:1rem;">'
                + pos + '</div>',
                unsafe_allow_html=True,
            )
            st.divider()

            # Palette
            st.markdown('<p style="color:' + TH + ';font-weight:700;margin-bottom:0.4rem;">Palette</p>', unsafe_allow_html=True)
            palette = report.get("palette", [])
            if palette:
                swatch_html = '<div class="swatch-row">'
                for sw in palette:
                    hx = sw.get("hex_code", "#CCC")
                    nm = sw.get("name", "")[:14]
                    swatch_html += (
                        '<div class="swatch-wrap">'
                        '<div class="swatch" style="background:' + hx + '"></div>'
                        '<div class="swatch-label">' + hx + '<br>' + nm + '</div>'
                        '</div>'
                    )
                swatch_html += "</div>"
                st.markdown(swatch_html, unsafe_allow_html=True)
            st.divider()

            # Typography
            typo = report.get("typography", {})
            if typo:
                st.markdown('<p style="color:' + TH + ';font-weight:700;margin-bottom:0.3rem;">Typography</p>', unsafe_allow_html=True)
                lines_html = (
                    '<p style="color:' + TC + ';margin:0.15rem 0;">Display: ' + typo.get("display_typeface", "") + '</p>'
                    '<p style="color:' + TC + ';margin:0.15rem 0;">Body: ' + typo.get("body_typeface", "") + '</p>'
                    '<p style="color:' + TC + ';margin:0.15rem 0 0.8rem 0;">Tracking: ' + typo.get("display_tracking", "") + '</p>'
                )
                st.markdown(lines_html, unsafe_allow_html=True)
                st.divider()

            # Spatial
            st.markdown('<p style="color:' + TH + ';font-weight:700;margin-bottom:0.3rem;">Spatial</p>', unsafe_allow_html=True)
            st.markdown('<p style="color:' + TC + ';">' + report.get("layout_approach", "") + '</p>', unsafe_allow_html=True)
            st.markdown('<p style="color:' + TS + ';font-size:0.88rem;">' + report.get("negative_space_rule", "") + '</p>', unsafe_allow_html=True)
            st.divider()

            # Photography
            st.markdown('<p style="color:' + TH + ';font-weight:700;margin-bottom:0.3rem;">Photography</p>', unsafe_allow_html=True)
            photo_items = report.get("photography_direction", [])
            photo_html = "".join('<p style="color:' + TC + ';margin:0.3rem 0;">' + str(i) + '. ' + d + '</p>' for i, d in enumerate(photo_items, 1))
            st.markdown(photo_html, unsafe_allow_html=True)
            st.divider()

            # Do / Dont
            cd, cn = st.columns(2)
            with cd:
                st.markdown('<p style="color:' + TH + ';font-weight:700;">Do</p>', unsafe_allow_html=True)
                do_html = "".join('<p style="color:' + TC + ';font-size:0.88rem;margin:0.25rem 0;">&#10003; ' + r + '</p>' for r in report.get("do_rules", []))
                st.markdown(do_html, unsafe_allow_html=True)
            with cn:
                st.markdown('<p style="color:' + TH + ';font-weight:700;">Don\'t</p>', unsafe_allow_html=True)
                dont_html = "".join('<p style="color:' + TC + ';font-size:0.88rem;margin:0.25rem 0;">&#10005; ' + r + '</p>' for r in report.get("dont_rules", []))
                st.markdown(dont_html, unsafe_allow_html=True)
            st.divider()

            # Benchmark brands
            st.markdown('<p style="color:' + TH + ';font-weight:700;margin-bottom:0.3rem;">Benchmark Brands</p>', unsafe_allow_html=True)
            brands_html = "".join(
                '<p style="color:' + TH + ';font-weight:600;margin:0.5rem 0 0.1rem 0;">' + b["name"] + '</p>'
                '<p style="color:' + TC + ';font-size:0.88rem;margin:0 0 0.6rem 0;">' + b["reference_note"] + '</p>'
                for b in report.get("benchmark_brands", [])
            )
            st.markdown(brands_html, unsafe_allow_html=True)
            st.divider()

            # Visual narrative
            st.markdown('<p style="color:' + TH + ';font-weight:700;margin-bottom:0.3rem;">Visual Narrative</p>', unsafe_allow_html=True)
            narrative = report.get("visual_narrative", "")
            st.markdown('<p style="color:' + TC + ';line-height:1.8;font-style:italic;">' + narrative + '</p>', unsafe_allow_html=True)

            conflicts = report.get("conflicts_resolved")
            if conflicts:
                with st.expander("Conflicts resolved"):
                    st.markdown('<p style="color:' + TC + ';">' + conflicts + '</p>', unsafe_allow_html=True)

            # ── Export ──────────────────────────────────────────────────────
            st.divider()
            html_export = _build_report_html(
                report,
                result.get("keyword", ""),
                langsmith_url=result.get("langsmith_url"),
                served=result.get("served_models"),
            )
            st.download_button(
                label="⬇ Download Report (HTML)",
                data=html_export.encode("utf-8"),
                file_name=f"visual_direction_{result.get('keyword','report').replace(' ','_')}.html",
                mime="text/html",
                use_container_width=True,
                help="Standalone HTML file — open in any browser for the demo side-by-side.",
            )
        else:
            st.markdown(result.get("formatted_report", ""))

    with right:
        st.markdown('<h3 style="color:' + TH + ';">Moodboard</h3>', unsafe_allow_html=True)
        if panels:
            r1a, r1b = st.columns(2)
            _render_panel(panels, 0, r1a)
            _render_panel(panels, 1, r1b)
            r2a, r2b = st.columns(2)
            _render_panel(panels, 2, r2a)
            _render_panel(panels, 3, r2b)
            _, mid, _ = st.columns([0.15, 0.7, 0.15])
            _render_panel(panels, 4, mid)
        else:
            st.info("No moodboard panels generated. Re-run with skip_moodboard unchecked.")
