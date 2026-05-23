"""GR&R Analysis page — with integrated guide."""
from __future__ import annotations

import os
import sys
import requests
import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from components.charts import grr_pie_chart

def _backend_url() -> str:
    if url := os.getenv("BACKEND_URL"):
        return url
    try:
        return st.secrets["BACKEND_URL"]
    except Exception:
        return "http://localhost:8000"

BACKEND = _backend_url()
API = f"{BACKEND}/api/v1"

st.set_page_config(page_title="GR&R Analysis — GaugeGuard AI", layout="wide", page_icon="📏")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: linear-gradient(135deg,#0f0c29,#302b63,#24243e); }
.card { background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
        border-radius:14px; padding:20px 24px; margin-bottom:16px; }
.metric-big { font-size:2.4rem; font-weight:900;
              background:linear-gradient(90deg,#60a5fa,#a78bfa);
              -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.metric-label { font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#6b7280; }
.badge-ok   { background:#065f46;color:#6ee7b7;padding:5px 16px;border-radius:99px;font-weight:700;font-size:13px;}
.badge-warn { background:#7c2d12;color:#fcd34d;padding:5px 16px;border-radius:99px;font-weight:700;font-size:13px;}
.badge-bad  { background:#7f1d1d;color:#fca5a5;padding:5px 16px;border-radius:99px;font-weight:700;font-size:13px;}
.warn-box   { background:rgba(245,158,11,.1);border-left:3px solid #f59e0b;
              border-radius:8px;padding:10px 14px;margin:6px 0;font-size:13px;color:#fde68a;}
.rec-box    { background:rgba(99,102,241,.1);border-left:3px solid #818cf8;
              border-radius:8px;padding:10px 14px;margin:6px 0;font-size:13px;color:#c7d2fe;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📏 GR&R Analysis")
    st.divider()
    st.markdown("""
    **What does this page do?**

    Runs a full Gauge R&R study to determine whether your measurement equipment is reliable.

    ---
    **Available methods:**

    🔬 **ANOVA** *(recommended)*
    Detects Part×Operator interaction.
    More accurate with 3+ operators.

    📐 **Range Method**
    Classic AIAG MSA method.
    Simpler, no interaction analysis.

    ---
    **Demo scenarios:**

    | Scenario | Expected %GRR | Result |
    |----------|---------------|--------|
    | `grr_pass` | ~6% | ✅ Acceptable |
    | `grr_marginal` | ~25% | ⚠️ Marginal |
    | `grr_fail` | ~42% | ❌ Rejected |

    ---
    **AIAG thresholds:**
    - ✅ < 10% → Approved
    - ⚠️ 10–30% → Marginal
    - ❌ > 30% → Not Acceptable
    """)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📏 Gauge R&R Analysis")
st.markdown("""
> Quantifies how much of your total measurement variation comes from the gauge and operators
> vs. actual part-to-part differences. Based on **AIAG MSA 4th Edition** — the automotive quality standard.
""")

tab_sample, tab_upload = st.tabs(["🧪 Load Demo Scenario", "📁 Upload CSV"])

# ── Tab: Demo scenario ────────────────────────────────────────────────────────
with tab_sample:
    st.markdown("""
    <div class="card">
      <strong>How to use:</strong> Select a scenario, choose the analysis method and press the button.
      Each scenario has 10 parts × 3 operators × 3 repetitions = 90 measurements.
    </div>
    """, unsafe_allow_html=True)

    col_s1, col_s2, col_s3 = st.columns([2, 1.5, 1.5])
    scenario = col_s1.selectbox(
        "Scenario",
        ["grr_pass", "grr_marginal", "grr_fail"],
        format_func=lambda x: {
            "grr_pass":     "✅ grr_pass — precise gauge (~6% GRR)",
            "grr_marginal": "⚠️ grr_marginal — marginal gauge (~25% GRR)",
            "grr_fail":     "❌ grr_fail — deficient gauge (~42% GRR)",
        }[x],
    )
    method_s = col_s2.selectbox("Analysis method", ["ANOVA", "Range"])
    equipment_s = col_s3.text_input("Equipment ID", "CMM-001")

    if st.button("▶ Run GR&R Analysis", type="primary", use_container_width=True):
        with st.spinner("Generating measurement data..."):
            r = requests.post(f"{API}/datasets/generate/grr",
                              json={"scenario": scenario.replace("grr_", "")},
                              timeout=40)
        if r.status_code != 200:
            st.error(f"Failed to generate dataset: {r.text}")
            st.stop()
        dataset_id = r.json()["dataset_id"]

        with st.spinner(f"Running AIAG MSA analysis using {method_s} method..."):
            ar = requests.post(f"{API}/grr/analyze",
                               json={"dataset_id": dataset_id, "method": method_s,
                                     "equipment_id": equipment_s}, timeout=40)
        if ar.status_code not in (200, 422):
            st.error(f"Analysis error: {ar.text}")
        else:
            st.session_state["grr_result"] = ar.json()
            st.session_state["grr_study_id"] = ar.json().get("study_id")

# ── Tab: Upload CSV ───────────────────────────────────────────────────────────
with tab_upload:
    st.markdown("""
    **Required CSV format:**

    | part_id | operator_id | trial | measurement_value | nominal_value | USL | LSL |
    |---------|-------------|-------|-------------------|---------------|-----|-----|
    | P01 | OP1 | 1 | 25.003 | 25.0 | 25.5 | 24.5 |
    | P01 | OP1 | 2 | 24.998 | … | … | … |

    Minimum: 2 parts × 2 operators × 2 repetitions.
    """)

    uploaded = st.file_uploader("Upload CSV file", type=["csv"])
    if uploaded:
        df_preview = pd.read_csv(uploaded)
        st.success(
            f"✅ File loaded: {len(df_preview)} rows, "
            f"{df_preview['part_id'].nunique()} parts, "
            f"{df_preview['operator_id'].nunique()} operators"
        )
        st.dataframe(df_preview.head(10), use_container_width=True)
        uploaded.seek(0)

        c1u, c2u = st.columns(2)
        equipment_u = c1u.text_input("Equipment ID", "MY-GAUGE", key="eq_u")
        method_u = c2u.selectbox("Method", ["ANOVA", "Range"], key="method_u")

        if st.button("▶ Analyze CSV", type="primary"):
            files = {"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
            up_r = requests.post(f"{API}/datasets/upload", files=files, timeout=40)
            if up_r.status_code != 200:
                st.error(f"Upload failed: {up_r.text}")
            else:
                did = up_r.json()["dataset_id"]
                ar = requests.post(f"{API}/grr/analyze",
                                   json={"dataset_id": did, "method": method_u,
                                         "equipment_id": equipment_u}, timeout=40)
                if ar.status_code == 200:
                    st.session_state["grr_result"] = ar.json()
                    st.session_state["grr_study_id"] = ar.json().get("study_id")


# ── Results ───────────────────────────────────────────────────────────────────
if "grr_result" in st.session_state:
    res = st.session_state["grr_result"]
    st.divider()
    st.markdown("## 📊 Analysis Results")

    status = res.get("status", "")
    badge = {
        "ACCEPTABLE":     '<span class="badge-ok">✅ ACCEPTABLE</span>',
        "MARGINAL":       '<span class="badge-warn">⚠️ MARGINAL</span>',
        "NOT_ACCEPTABLE": '<span class="badge-bad">❌ NOT ACCEPTABLE</span>',
    }.get(status, status)

    verdict = {
        "ACCEPTABLE":     "The measurement system is **reliable**. Approved for production use.",
        "MARGINAL":       "The system is in the grey zone. Evaluate based on **application criticality**.",
        "NOT_ACCEPTABLE": "⛔ **Do NOT use this gauge** for production decisions until corrected.",
    }.get(status, "")

    st.markdown(f"""
    <div class="card" style="border-color:{'#22c55e' if status=='ACCEPTABLE' else '#f59e0b' if status=='MARGINAL' else '#ef4444'}">
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <div>{badge}</div>
        <div style="color:#e2e8f0;font-size:15px">{verdict}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Main metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    metrics = [
        ("%GRR",              f"{res['percent_grr']:.1f}%", "< 10% = acceptable"),
        ("%EV (Repeatability)", f"{res['percent_ev']:.1f}%", "gauge variation"),
        ("%AV (Reproducibility)", f"{res['percent_av']:.1f}%", "operator variation"),
        ("%PV (Parts)",        f"{res['percent_pv']:.1f}%", "true part variation"),
        ("NDC",               str(res["ndc"]),               "≥ 5 = adequate discrimination"),
    ]
    for col, (label, value, sub) in zip([col1, col2, col3, col4, col5], metrics):
        col.markdown(f"""
        <div class="card" style="text-align:center">
          <div class="metric-label">{label}</div>
          <div class="metric-big">{value}</div>
          <div style="font-size:11px;color:#6b7280;margin-top:4px">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    # Pie chart + warnings
    col_pie, col_detail = st.columns([1, 1.2])
    with col_pie:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Variance Contribution**")
        st.caption("Percentages add in quadrature (not linearly): %EV² + %AV² ≈ %GRR²")
        fig = grr_pie_chart(res["percent_ev"], res["percent_av"], res["percent_pv"])
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0", height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_detail:
        if res.get("warnings"):
            st.markdown("**⚠️ Warnings**")
            for w in res["warnings"]:
                st.markdown(f'<div class="warn-box">⚠ {w}</div>', unsafe_allow_html=True)
        if res.get("recommendations"):
            st.markdown("**💡 Recommendations**")
            for r_text in res["recommendations"]:
                st.markdown(f'<div class="rec-box">→ {r_text}</div>', unsafe_allow_html=True)

    # ANOVA table
    if res.get("anova_table"):
        with st.expander("📐 Detailed ANOVA Table (variance components)", expanded=False):
            st.markdown("""
            The ANOVA table decomposes total variation into its sources.
            A **p-value < 0.25** on the Part×Operator interaction indicates that some operators
            measure certain parts differently — an important finding for training and calibration.
            """)
            t = res["anova_table"]
            df_anova = pd.DataFrame({
                "Source": t["source"],
                "SS":      [f"{v:.6f}" if v is not None else "—" for v in t["SS"]],
                "df":      t["df"],
                "MS":      [f"{v:.6f}" if v is not None else "—" for v in t["MS"]],
                "F":       [f"{v:.4f}"  if v is not None else "—" for v in t["F"]],
                "p-value": [f"{v:.4f}"  if v is not None else "—" for v in t["p_value"]],
            })
            st.dataframe(df_anova, use_container_width=True, hide_index=True)
            if res.get("interaction_pooled"):
                st.caption(
                    "✅ Interaction pooled (p > 0.25 — not significant). "
                    "All operators measure parts consistently."
                )
            else:
                st.caption(
                    "⚠️ Significant interaction detected. "
                    "Some operators may be measuring certain parts differently."
                )

    # Download report
    study_id = st.session_state.get("grr_study_id")
    if study_id:
        if st.button("📄 Generate HTML Report"):
            rr = requests.get(f"{API}/grr/studies/{study_id}/report", timeout=40)
            if rr.status_code == 200:
                st.download_button(
                    "⬇️ Download Report",
                    data=rr.json()["html"].encode(),
                    file_name=f"grr_report_{study_id[:8]}.html",
                    mime="text/html",
                )
