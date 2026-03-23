"""
app.py  —  Personal Lines Auto Rating Engine · Streamlit UI
────────────────────────────────────────────────────────────
Run locally:
    pip install streamlit plotly pandas numpy
    streamlit run app.py

Deploy to Streamlit Community Cloud:
    Push all files (app.py, rating_engine.py, generate_rate_table.py,
    rate_table.csv, requirements.txt) to a public GitHub repo, then
    connect via share.streamlit.io.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Bootstrap: ensure rate_table.csv exists ──────────────────────────────────
if not Path("rate_table.csv").exists():
    import generate_rate_table  # noqa: F401

from rating_engine import (
    RatingEngine,
    OutOfBoundsError,
    RatingError,
    QuoteResult,
)

# ══════════════════════════════════════════════════════════════════════════════
# Page config  (must be first Streamlit call)
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="ClearRate · Auto Insurance Pricer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# Global CSS — corporate blues/grays, refined typography
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ── Fonts ─────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── Root palette ───────────────────────────────────────────────────────── */
:root {
    --c-navy:     #0D2340;
    --c-blue:     #1557B0;
    --c-sky:      #2E86DE;
    --c-ice:      #E8F1FB;
    --c-slate:    #4A5568;
    --c-mist:     #F0F4F9;
    --c-white:    #FFFFFF;
    --c-positive: #0A7D4B;
    --c-negative: #C0392B;
    --c-warning:  #D97706;
    --c-border:   #D1DCE8;
    --radius:     10px;
    --shadow:     0 2px 12px rgba(13,35,64,0.10);
}

/* ── Global base ────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    color: var(--c-navy);
}

/* ── App background ─────────────────────────────────────────────────────── */
.stApp { background: var(--c-mist); }

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--c-navy) !important;
    border-right: none;
}
[data-testid="stSidebar"] * {
    color: #CBD5E1 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--c-white) !important;
}
[data-testid="stSidebar"] .stSlider > div > div > div {
    background: var(--c-sky) !important;
}
[data-testid="stSidebar"] label {
    color: #94A3B8 !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: var(--radius) !important;
    color: var(--c-white) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.12) !important;
}

/* ── Metric cards ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--c-white);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    padding: 1.1rem 1.4rem !important;
    box-shadow: var(--shadow);
}
[data-testid="stMetricLabel"] {
    font-size: 0.70rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--c-slate) !important;
}
[data-testid="stMetricValue"] {
    font-size: 2.1rem !important;
    font-weight: 600 !important;
    color: var(--c-navy) !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"] svg { display: none; }

/* ── Buttons ────────────────────────────────────────────────────────────── */
.stButton > button {
    background: var(--c-blue) !important;
    color: var(--c-white) !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    padding: 0.55rem 1.6rem !important;
    transition: background 0.18s, box-shadow 0.18s !important;
}
.stButton > button:hover {
    background: var(--c-sky) !important;
    box-shadow: 0 4px 14px rgba(46,134,222,0.35) !important;
}

/* ── Section cards ──────────────────────────────────────────────────────── */
.card {
    background: var(--c-white);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    padding: 1.5rem 1.8rem;
    box-shadow: var(--shadow);
    margin-bottom: 1.2rem;
}
.card-title {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: var(--c-slate);
    margin-bottom: 1rem;
}

/* ── Premium hero banner ────────────────────────────────────────────────── */
.premium-hero {
    background: linear-gradient(135deg, var(--c-navy) 0%, #1A3A6B 100%);
    border-radius: 14px;
    padding: 2rem 2.4rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 8px 32px rgba(13,35,64,0.22);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
}
.premium-hero .label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #7EB8F7;
    margin-bottom: 0.3rem;
}
.premium-hero .amount {
    font-size: 3.2rem;
    font-weight: 600;
    color: #FFFFFF;
    letter-spacing: -0.03em;
    line-height: 1.1;
}
.premium-hero .sub {
    font-size: 1.05rem;
    color: #94C6F5;
    margin-top: 0.2rem;
}
.premium-hero .badge {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.20);
    border-radius: 8px;
    padding: 0.7rem 1.2rem;
    text-align: center;
}
.premium-hero .badge .b-val {
    font-size: 1.5rem;
    font-weight: 600;
    color: #FFFFFF;
}
.premium-hero .badge .b-lbl {
    font-size: 0.65rem;
    color: #94C6F5;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── Factor table ───────────────────────────────────────────────────────── */
.factor-row {
    display: flex;
    align-items: center;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--c-border);
    font-size: 0.88rem;
}
.factor-row:last-child { border-bottom: none; }
.factor-name { flex: 0 0 160px; color: var(--c-slate); font-size: 0.78rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.factor-key  { flex: 0 0 120px; font-family: 'DM Mono', monospace; font-size: 0.82rem; color: var(--c-navy); }
.factor-rel  { flex: 0 0 70px;  text-align: right; font-family: 'DM Mono', monospace; font-weight: 500; }
.rel-up   { color: var(--c-negative); }
.rel-down { color: var(--c-positive); }
.rel-flat { color: var(--c-slate); }
.factor-amt  { flex: 1; text-align: right; font-family: 'DM Mono', monospace; color: var(--c-navy); font-weight: 500; }

/* ── Warning pills ──────────────────────────────────────────────────────── */
.warn-pill {
    background: #FEF3C7;
    border: 1px solid #F59E0B;
    border-radius: 8px;
    padding: 0.55rem 0.9rem;
    font-size: 0.82rem;
    color: #92400E;
    margin-top: 0.5rem;
}

/* ── Compare table ──────────────────────────────────────────────────────── */
.compare-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    padding: 0.6rem 0.4rem;
    border-bottom: 1px solid var(--c-border);
    font-size: 0.85rem;
    align-items: center;
}
.compare-header {
    font-size: 0.67rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--c-slate);
}
.pos-delta { color: var(--c-negative); font-weight: 600; }
.neg-delta { color: var(--c-positive); font-weight: 600; }
.zero-delta{ color: var(--c-slate); }

/* ── Divider ────────────────────────────────────────────────────────────── */
.section-div { border: none; border-top: 2px solid var(--c-border); margin: 1.4rem 0; }

/* ── Sidebar logo ───────────────────────────────────────────────────────── */
.sidebar-logo {
    font-size: 1.35rem;
    font-weight: 700;
    color: #FFFFFF !important;
    letter-spacing: -0.02em;
    padding: 0.5rem 0 1.5rem 0;
}
.sidebar-logo span { color: var(--c-sky) !important; }

/* ── Hide Streamlit chrome ──────────────────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Engine singleton
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def load_engine() -> RatingEngine:
    return RatingEngine("rate_table.csv")

engine = load_engine()

# ══════════════════════════════════════════════════════════════════════════════
# Sidebar — inputs
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<div class="sidebar-logo">Clear<span>Rate</span> &nbsp;🛡️</div>', unsafe_allow_html=True)
    st.markdown("**Auto Insurance Pricer**")
    st.markdown("*Personal Lines · Rating Engine v1.0*")
    st.divider()

    st.markdown("#### Driver")
    driver_age = st.slider("Driver Age", min_value=16, max_value=85, value=35, step=1)

    st.markdown("#### Vehicle")
    vehicle_value = st.slider(
        "Vehicle Value ($)",
        min_value=5_000, max_value=120_000,
        value=28_000, step=1_000,
        format="$%d",
    )
    safety = st.selectbox(
        "Safety Features",
        options=["none", "basic", "advanced", "full_adas"],
        index=2,
        format_func=lambda x: {
            "none":      "None",
            "basic":     "Basic (ABS + Airbags)",
            "advanced":  "Advanced ADAS",
            "full_adas": "Full ADAS + Telematics",
        }[x],
    )

    st.markdown("#### Location")
    territory = st.selectbox(
        "Territory",
        options=["urban", "suburban", "rural"],
        index=1,
        format_func=lambda x: x.title(),
    )

    st.markdown("#### Policy")
    deductible = st.selectbox(
        "Deductible",
        options=[250, 500, 1000, 2000],
        index=1,
        format_func=lambda x: f"${x:,}",
    )
    coverage = st.selectbox(
        "Coverage Type",
        options=["full_coverage", "liability_only"],
        index=0,
        format_func=lambda x: {
            "full_coverage":   "Full Coverage",
            "liability_only":  "Liability Only",
        }[x],
    )

    st.divider()
    st.markdown('<p style="font-size:0.68rem;color:#475569;line-height:1.5">Illustrative rating engine for portfolio demonstration. Not a licensed insurance product.</p>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Build inputs dict & calculate
# ══════════════════════════════════════════════════════════════════════════════

inputs: dict = {
    "driver_age":      driver_age,
    "vehicle_value":   vehicle_value,
    "territory":       territory,
    "safety_features": safety,
    "deductible":      deductible,
    "coverage_type":   coverage,
}

try:
    quote: QuoteResult = engine.calculate_premium(inputs)
    error_msg = None
except (OutOfBoundsError, RatingError) as exc:
    quote = None
    error_msg = str(exc)

# ══════════════════════════════════════════════════════════════════════════════
# Header row
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("## Auto Insurance Quote")
st.markdown('<p style="color:#4A5568;margin-top:-0.6rem;margin-bottom:1rem;font-size:0.92rem">Adjust the inputs in the sidebar — your quote updates in real time.</p>', unsafe_allow_html=True)

# ── Error state ───────────────────────────────────────────────────────────────
if error_msg:
    st.error(f"⚠️  **Rating Error:** {error_msg}")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# Premium hero banner
# ══════════════════════════════════════════════════════════════════════════════

monthly = quote.final_premium / 12
glm_pct  = (quote.glm_adjustment - 1) * 100

st.markdown(f"""
<div class="premium-hero">
  <div>
    <div class="label">Annual Premium</div>
    <div class="amount">${quote.final_premium:,.2f}</div>
    <div class="sub">${monthly:,.2f} / month</div>
  </div>
  <div style="display:flex;gap:0.8rem;flex-wrap:wrap;">
    <div class="badge">
      <div class="b-val">${quote.base_premium:,.0f}</div>
      <div class="b-lbl">Base Rate</div>
    </div>
    <div class="badge">
      <div class="b-val">{quote.multiplicative_factor:.3f}×</div>
      <div class="b-lbl">Combined Factor</div>
    </div>
    <div class="badge">
      <div class="b-val">{glm_pct:+.1f}%</div>
      <div class="b-lbl">GLM Adj</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Top metric strip
# ══════════════════════════════════════════════════════════════════════════════

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Annual Premium",  f"${quote.final_premium:,.2f}")
with m2:
    st.metric("Monthly Payment", f"${monthly:,.2f}")
with m3:
    impact = quote.final_premium - quote.base_premium
    st.metric("Factor Impact",   f"${impact:+,.2f}")
with m4:
    st.metric("GLM Credibility", f"{quote.glm_adjustment:.4f}×")

st.markdown("<div class='section-div'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Two-column layout: chart | factor breakdown
# ══════════════════════════════════════════════════════════════════════════════

col_chart, col_table = st.columns([3, 2], gap="large")

# ── Impact factor bar chart ───────────────────────────────────────────────────
with col_chart:
    st.markdown('<div class="card-title">📊 Premium Impact by Factor</div>', unsafe_allow_html=True)

    running = quote.base_premium
    bar_labels, bar_values, bar_colors = [], [], []

    BLUE   = "#1557B0"
    RED    = "#C0392B"
    GREEN  = "#0A7D4B"
    GRAY   = "#94A3B8"

    for f in quote.factors:
        dollar_impact = running * (f.relativity - 1.0)
        label = f"{f.variable.replace('_', ' ')}<br><span style='font-size:10px'>{f.key}</span>"
        bar_labels.append(f.variable.replace("_", " ") + f"  [{f.key}]")
        bar_values.append(round(dollar_impact, 2))
        if f.relativity > 1.005:
            bar_colors.append(RED)
        elif f.relativity < 0.995:
            bar_colors.append(GREEN)
        else:
            bar_colors.append(GRAY)
        running *= f.relativity

    # GLM row
    glm_dollar = running * (quote.glm_adjustment - 1.0)
    bar_labels.append("GLM Credibility  [model]")
    bar_values.append(round(glm_dollar, 2))
    bar_colors.append(BLUE if abs(glm_dollar) < 0.01 else (RED if glm_dollar > 0 else GREEN))

    fig = go.Figure(go.Bar(
        x=bar_values,
        y=bar_labels,
        orientation="h",
        marker=dict(
            color=bar_colors,
            line=dict(color="rgba(0,0,0,0.06)", width=0.5),
        ),
        text=[f"${v:+,.2f}" for v in bar_values],
        textposition="outside",
        textfont=dict(size=11, family="DM Mono", color="#0D2340"),
        cliponaxis=False,
    ))

    fig.add_vline(x=0, line_color="#CBD5E1", line_width=1.5)

    fig.update_layout(
        height=340,
        margin=dict(l=0, r=80, t=10, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            title="Dollar Impact ($)",
            titlefont=dict(size=11, color="#4A5568"),
            tickfont=dict(size=10, family="DM Mono"),
            gridcolor="#EDF2F7",
            zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(size=10.5, family="DM Sans"),
            autorange="reversed",
        ),
        font=dict(family="DM Sans"),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "🟥 Red = premium increase &nbsp;|&nbsp; 🟩 Green = premium discount &nbsp;|&nbsp; "
        "⬜ Gray = no change from base"
    )

# ── Factor breakdown table ────────────────────────────────────────────────────
with col_table:
    st.markdown('<div class="card-title">📋 Rating Step-Down</div>', unsafe_allow_html=True)

    running = quote.base_premium
    rows_html = ""

    # Base row
    rows_html += f"""
    <div class="factor-row">
      <span class="factor-name">Base</span>
      <span class="factor-key">—</span>
      <span class="factor-rel rel-flat">—</span>
      <span class="factor-amt">${running:,.2f}</span>
    </div>"""

    for f in quote.factors:
        running *= f.relativity
        if f.relativity > 1.005:
            rel_cls = "rel-up"
            arrow = "▲"
        elif f.relativity < 0.995:
            rel_cls = "rel-down"
            arrow = "▼"
        else:
            rel_cls = "rel-flat"
            arrow = "—"
        rows_html += f"""
    <div class="factor-row">
      <span class="factor-name">{f.variable.replace('_', ' ')}</span>
      <span class="factor-key">{f.key}</span>
      <span class="factor-rel {rel_cls}">{arrow} {f.relativity:.4f}</span>
      <span class="factor-amt">${running:,.2f}</span>
    </div>"""

    # GLM row
    running *= quote.glm_adjustment
    rel_cls = "rel-flat" if abs(quote.glm_adjustment - 1) < 0.001 else ("rel-up" if quote.glm_adjustment > 1 else "rel-down")
    rows_html += f"""
    <div class="factor-row" style="background:#F0F4F9;border-radius:6px;padding:0.55rem 0.4rem;">
      <span class="factor-name">GLM Model</span>
      <span class="factor-key">log-link</span>
      <span class="factor-rel {rel_cls}">× {quote.glm_adjustment:.4f}</span>
      <span class="factor-amt" style="font-weight:700;color:#0D2340">${running:,.2f}</span>
    </div>"""

    st.markdown(f'<div class="card">{rows_html}</div>', unsafe_allow_html=True)

    # Warnings
    if quote.warnings:
        for w in quote.warnings:
            st.markdown(f'<div class="warn-pill">⚠️ {w}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Sensitivity Analysis — full width
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div class='section-div'></div>", unsafe_allow_html=True)
st.markdown("### Sensitivity Analysis")
st.markdown('<p style="color:#4A5568;font-size:0.90rem;margin-top:-0.5rem;margin-bottom:1rem">See how changing a single variable affects your premium — all other inputs held constant.</p>', unsafe_allow_html=True)

sens_var = st.selectbox(
    "Analyse variable",
    options=["deductible", "territory", "coverage_type", "safety_features"],
    format_func=lambda x: {
        "deductible":      "Deductible",
        "territory":       "Territory",
        "coverage_type":   "Coverage Type",
        "safety_features": "Safety Features",
    }[x],
    key="sens_select",
)

SWEEP: dict[str, list] = {
    "deductible":      [250, 500, 1000, 2000],
    "territory":       ["urban", "suburban", "rural"],
    "coverage_type":   ["full_coverage", "liability_only"],
    "safety_features": ["none", "basic", "advanced", "full_adas"],
}

base_prem = quote.final_premium
sens_rows = []
for val in SWEEP[sens_var]:
    trial = {**inputs, sens_var: val}
    try:
        q2 = engine.calculate_premium(trial)
        sens_rows.append({
            "value": str(val),
            "premium": q2.final_premium,
            "delta": q2.final_premium - base_prem,
            "pct": (q2.final_premium - base_prem) / base_prem * 100,
            "is_current": val == inputs[sens_var],
        })
    except Exception:
        pass

# Sensitivity bar chart
s_labels = [r["value"] + ("  ◄" if r["is_current"] else "") for r in sens_rows]
s_values = [r["premium"] for r in sens_rows]
s_colors = ["#1557B0" if r["is_current"] else "#93C5FD" for r in sens_rows]

fig2 = go.Figure(go.Bar(
    x=s_labels,
    y=s_values,
    marker=dict(color=s_colors, line=dict(color="rgba(0,0,0,0.06)", width=0.5)),
    text=[f"${v:,.2f}" for v in s_values],
    textposition="outside",
    textfont=dict(size=11, family="DM Mono", color="#0D2340"),
))

fig2.add_hline(
    y=base_prem,
    line_dash="dot",
    line_color="#C0392B",
    line_width=1.8,
    annotation_text=f"Current  ${base_prem:,.2f}",
    annotation_position="top right",
    annotation_font=dict(size=10, color="#C0392B"),
)

fig2.update_layout(
    height=280,
    margin=dict(l=0, r=20, t=30, b=10),
    plot_bgcolor="white",
    paper_bgcolor="white",
    yaxis=dict(
        title="Annual Premium ($)",
        titlefont=dict(size=11, color="#4A5568"),
        tickfont=dict(size=10, family="DM Mono"),
        gridcolor="#EDF2F7",
    ),
    xaxis=dict(tickfont=dict(size=11, family="DM Sans")),
    font=dict(family="DM Sans"),
    showlegend=False,
)

st.plotly_chart(fig2, use_container_width=True)

# Sensitivity table
header_html = """
<div class="compare-row compare-header" style="margin-bottom:0.3rem">
  <span>Value</span><span>Annual Premium</span><span>Delta ($)</span><span>Delta (%)</span>
</div>"""

rows_html2 = ""
for r in sens_rows:
    weight = "font-weight:700;" if r["is_current"] else ""
    bg     = "background:#EFF6FF;border-radius:6px;" if r["is_current"] else ""
    d = r["delta"]
    p = r["pct"]
    delta_cls = "pos-delta" if d > 0.01 else ("neg-delta" if d < -0.01 else "zero-delta")
    rows_html2 += f"""
<div class="compare-row" style="{bg}">
  <span style="{weight}">{r['value']}{'  ◄ current' if r['is_current'] else ''}</span>
  <span style="font-family:'DM Mono';{weight}">${r['premium']:,.2f}</span>
  <span class="{delta_cls}" style="font-family:'DM Mono'">${d:+,.2f}</span>
  <span class="{delta_cls}" style="font-family:'DM Mono'">{p:+.1f}%</span>
</div>"""

st.markdown(f'<div class="card">{header_html}{rows_html2}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Scenario Comparison modal section
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div class='section-div'></div>", unsafe_allow_html=True)
st.markdown("### Scenario Comparison")
st.markdown('<p style="color:#4A5568;font-size:0.90rem;margin-top:-0.5rem;margin-bottom:1rem">Build a custom alternative quote and compare it side-by-side with your current selection.</p>', unsafe_allow_html=True)

with st.expander("⚙️  Configure Alternative Scenario", expanded=False):
    cx1, cx2, cx3 = st.columns(3)
    with cx1:
        alt_age = st.slider("Alt Driver Age", 16, 85, driver_age, key="alt_age")
        alt_territory = st.selectbox("Alt Territory", ["urban", "suburban", "rural"],
                                     index=["urban","suburban","rural"].index(territory), key="alt_terr",
                                     format_func=str.title)
    with cx2:
        alt_vehicle = st.slider("Alt Vehicle Value ($)", 5_000, 120_000, vehicle_value,
                                step=1_000, format="$%d", key="alt_veh")
        alt_deductible = st.selectbox("Alt Deductible", [250, 500, 1000, 2000],
                                      index=[250,500,1000,2000].index(deductible), key="alt_ded",
                                      format_func=lambda x: f"${x:,}")
    with cx3:
        alt_safety = st.selectbox("Alt Safety Features",
                                  ["none","basic","advanced","full_adas"],
                                  index=["none","basic","advanced","full_adas"].index(safety), key="alt_saf",
                                  format_func=lambda x: {"none":"None","basic":"Basic","advanced":"Advanced ADAS","full_adas":"Full ADAS"}[x])
        alt_coverage = st.selectbox("Alt Coverage", ["full_coverage","liability_only"],
                                    index=["full_coverage","liability_only"].index(coverage), key="alt_cov",
                                    format_func=lambda x: {"full_coverage":"Full Coverage","liability_only":"Liability Only"}[x])
    run_compare = st.button("🔁  Compare Scenarios", use_container_width=False)

if run_compare or st.session_state.get("compared"):
    st.session_state["compared"] = True

    alt_inputs = {
        "driver_age":      alt_age,
        "vehicle_value":   alt_vehicle,
        "territory":       alt_territory,
        "safety_features": alt_safety,
        "deductible":      alt_deductible,
        "coverage_type":   alt_coverage,
    }
    try:
        alt_quote = engine.calculate_premium(alt_inputs)
        diff      = alt_quote.final_premium - quote.final_premium
        diff_pct  = diff / quote.final_premium * 100

        ca, cb = st.columns(2)
        with ca:
            st.metric("Current Scenario", f"${quote.final_premium:,.2f}", f"${quote.final_premium/12:,.2f}/mo")
        with cb:
            st.metric("Alternative Scenario", f"${alt_quote.final_premium:,.2f}",
                      f"{diff_pct:+.1f}%  (${diff:+,.2f}/yr)",
                      delta_color="inverse")

        # Side-by-side bar chart
        fig3 = go.Figure()
        factor_names = [f.variable.replace("_", " ") for f in quote.factors] + ["GLM"]
        curr_vals = [f.relativity for f in quote.factors] + [quote.glm_adjustment]
        alt_vals  = [f.relativity for f in alt_quote.factors] + [alt_quote.glm_adjustment]

        fig3.add_trace(go.Bar(name="Current",     x=factor_names, y=curr_vals,
                              marker_color="#1557B0", opacity=0.85))
        fig3.add_trace(go.Bar(name="Alternative", x=factor_names, y=alt_vals,
                              marker_color="#2E86DE", opacity=0.85))
        fig3.add_hline(y=1.0, line_dash="dot", line_color="#94A3B8", line_width=1)
        fig3.update_layout(
            barmode="group", height=260,
            margin=dict(l=0, r=0, t=20, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(title="Relativity", gridcolor="#EDF2F7",
                       tickfont=dict(size=10, family="DM Mono")),
            xaxis=dict(tickfont=dict(size=10, family="DM Sans")),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    except (OutOfBoundsError, RatingError) as exc:
        st.error(f"Alternative scenario error: {exc}")

# ══════════════════════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<div class='section-div'></div>", unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;color:#94A3B8;font-size:0.72rem">'
    'ClearRate · Personal Lines Rating Engine v1.0 &nbsp;|&nbsp; '
    'Built with Streamlit + Plotly &nbsp;|&nbsp; '
    'Portfolio demonstration only — not a licensed insurance product'
    '</p>',
    unsafe_allow_html=True,
)
