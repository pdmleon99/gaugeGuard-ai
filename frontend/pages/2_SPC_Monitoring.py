"""SPC Monitoring page — with integrated explanations."""
from __future__ import annotations

import os
import sys
import requests
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from components.charts import spc_chart

def _backend_url() -> str:
    if url := os.getenv("BACKEND_URL"):
        return url
    try:
        return st.secrets["BACKEND_URL"]
    except Exception:
        return "http://localhost:8000"

BACKEND = _backend_url()
API = f"{BACKEND}/api/v1"

st.set_page_config(page_title="SPC Monitoring — GaugeGuard AI", layout="wide", page_icon="📊")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: linear-gradient(135deg,#0f0c29,#302b63,#24243e); }
.card { background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);
        border-radius:14px;padding:18px 22px;margin-bottom:14px; }
.viol-critical { border-left:4px solid #ef4444;background:rgba(239,68,68,.08); }
.viol-warning  { border-left:4px solid #f59e0b;background:rgba(245,158,11,.08); }
.viol-info     { border-left:4px solid #3b82f6;background:rgba(59,130,246,.08); }
.viol-row { border-radius:8px;padding:10px 14px;margin:5px 0;font-size:13px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 SPC Monitoring")
    st.divider()
    st.markdown("""
    **Available scenarios:**

    | Scenario | What to observe |
    |----------|-----------------|
    | `stable` | In-control process — no alerts |
    | `shift` | Mean shift at point 100 — Rule 2 |
    | `drift` | +0.003/point drift — Rule 3 |
    | `anomalies` | 5 spikes at ±5σ — Rule 1 |

    ---
    **Subgroup size:**
    - **1** → I-MR chart (individuals)
    - **2–8** → X̄-R chart (mean & range)
    - **>8** → X̄-S chart (mean & std dev)

    ---
    **Active Nelson Rules:** 8 of 8
    """)

    st.divider()
    st.markdown("**Configure your analysis:**")
    scenario = st.selectbox(
        "Scenario", ["stable", "shift", "drift", "anomalies"],
        format_func=lambda x: {
            "stable":    "✅ stable — in-control process",
            "shift":     "⚠️ shift — mean shift at pt 100",
            "drift":     "🔺 drift — gradual process drift",
            "anomalies": "🚨 anomalies — 5 injected outliers",
        }[x],
    )
    subgroup_size = st.slider("Subgroup size (n)", 1, 10, 5)
    process_id = st.text_input("Process ID", "LINE-A")
    run_btn = st.button("▶ Run SPC Analysis", type="primary", use_container_width=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📊 SPC — Statistical Process Control")
st.markdown("""
> Monitors whether your process is in **statistical control** by applying all 8 Nelson Rules.
> Control limits are calculated using exact AIAG constants (A₂, D₃, D₄, d₂) per subgroup size.
""")

if "spc_result" not in st.session_state:
    st.markdown("""
    <div class="card">
      <strong>How the analysis works:</strong><br><br>
      <ol style="color:#94a3b8;font-size:14px;line-height:2.2">
        <li>Generates <strong>200 measurements</strong> of part diameter (nominal=25.0mm, USL=25.3, LSL=24.7)</li>
        <li>Groups readings into subgroups of <strong>n points</strong> and computes means and ranges</li>
        <li>Estimates <strong>control limits UCL/LCL</strong> from the first 25 baseline subgroups</li>
        <li>Applies all <strong>8 Nelson Rules</strong> to detect special causes of variation</li>
        <li>Violations generate <strong>automatic alerts</strong> with CRITICAL / WARNING / INFO severity</li>
      </ol>
    </div>
    """, unsafe_allow_html=True)

if run_btn:
    with st.spinner(f"Generating SPC dataset '{scenario}'..."):
        r = requests.post(f"{API}/datasets/generate/spc", json={"scenario": scenario}, timeout=40)
    if r.status_code != 200:
        st.error(f"Error: {r.text}")
        st.stop()

    with st.spinner(f"Analyzing with subgroup n={subgroup_size} and 8 Nelson Rules..."):
        ar = requests.post(f"{API}/spc/analyze", json={
            "dataset_id": r.json()["dataset_id"],
            "process_id": process_id,
            "subgroup_size": subgroup_size,
        }, timeout=40)
    if ar.status_code != 200:
        st.error(f"Analysis error: {ar.text}")
        st.stop()

    st.session_state["spc_result"] = ar.json()

if "spc_result" in st.session_state:
    res = st.session_state["spc_result"]

    status = res.get("process_status", "UNKNOWN")
    status_config = {
        "IN_CONTROL":     ("✅", "#22c55e", "IN CONTROL",       "No special causes detected. Process is stable."),
        "WARNING":        ("⚠️", "#f59e0b", "WARNING",          "Patterns detected that require attention."),
        "OUT_OF_CONTROL": ("🚨", "#ef4444", "OUT OF CONTROL",   "Immediate corrective action required."),
    }
    icon, color, label, msg = status_config.get(status, ("❓", "#6b7280", "UNKNOWN", ""))

    st.markdown(f"""
    <div class="card" style="border-color:{color}">
      <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap">
        <div style="font-size:3rem">{icon}</div>
        <div>
          <div style="font-size:22px;font-weight:900;color:{color}">{label}</div>
          <div style="color:#94a3b8;font-size:14px;margin-top:4px">{msg}</div>
        </div>
        <div style="margin-left:auto;text-align:right">
          <div style="font-size:11px;color:#6b7280;text-transform:uppercase">Chart type</div>
          <div style="font-size:18px;font-weight:700;color:#e2e8f0">{res["chart_type"]}</div>
          <div style="font-size:11px;color:#6b7280">{res["n_subgroups"]} subgroups · σ̂={res["sigma_hat"]:.5f}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, (lbl, val, sub, clr) in zip([c1, c2, c3, c4, c5], [
        ("Critical",   res["n_critical"],              "Rule 1 / Spec",   "#ef4444"),
        ("Warnings",   res["n_warning"],               "Rules 2,3,5,8",   "#f59e0b"),
        ("Info",       res["n_info"],                  "Rules 4,6,7",     "#3b82f6"),
        ("X̄ Center",   f"{res['x_bar_bar']:.4f}",     "center line",     "#a78bfa"),
        ("σ̂",          f"{res['sigma_hat']:.5f}",     "estimated sigma", "#60a5fa"),
    ]):
        col.markdown(f"""
        <div class="card" style="text-align:center">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7280">{lbl}</div>
          <div style="font-size:2rem;font-weight:900;color:{clr}">{val}</div>
          <div style="font-size:11px;color:#6b7280;margin-top:2px">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    # SPC chart
    st.markdown('<div class="card">', unsafe_allow_html=True)
    violations_plain = [
        {**v, "timestamp": str(v.get("timestamp", ""))}
        for v in res.get("violations", [])
    ]
    fig = spc_chart(
        chart_data=res["chart_data"],
        ucl_x=res["ucl_x"], lcl_x=res["lcl_x"], cl_x=res["x_bar_bar"],
        ucl_r=res["ucl_r"], lcl_r=res["lcl_r"], cl_r=res["r_bar"],
        violations=violations_plain,
        title=f"SPC — {res['chart_type']} — {res['process_id']}",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,12,41,0.6)",
        font_color="#e2e8f0", height=580,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        xaxis2=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        yaxis2=dict(gridcolor="rgba(255,255,255,0.06)"),
        legend=dict(bgcolor="rgba(255,255,255,0.05)", bordercolor="rgba(255,255,255,0.1)"),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Violations table
    if res.get("violations"):
        st.markdown(f"### 🚨 Violations detected ({len(res['violations'])} total)")

        rule_explanations = {
            "Rule 1": "**Rule 1 — Beyond 3σ:** Immediate special cause. A point exceeded ±3σ — statistically a 0.27% probability event under normal conditions.",
            "Rule 2": "**Rule 2 — Mean shift:** 9 consecutive points on the same side of the center line indicate the process mean has shifted (e.g., new material batch, operator change).",
            "Rule 3": "**Rule 3 — Process drift:** 6 consecutive points in a monotonic trend suggest gradual drift — likely tool wear, temperature effects, or operator fatigue.",
            "Rule 4": "**Rule 4 — Alternating pattern:** 14 zigzag points may indicate sampling from two mixed process streams.",
            "Rule 5": "**Rule 5 — Early shift signal:** 2 of 3 consecutive points beyond ±2σ on the same side — an early warning before Rule 1 fires.",
            "Rule 6": "**Rule 6 — Subtle shift:** 4 of 5 consecutive points beyond ±1σ on the same side.",
            "Rule 7": "**Rule 7 — Stratification / hugging:** 15 points all within ±1σ of center line — possible stratified sampling or over-correction.",
            "Rule 8": "**Rule 8 — Bimodal process:** 8 consecutive points all beyond ±1σ from center line — two distinct process streams suspected.",
            "SPEC_VIOLATION": "**Spec Violation:** Measurement exceeded USL or LSL — potentially defective part requiring quarantine.",
        }

        rules_found: dict[str, list] = {}
        for v in res["violations"]:
            rules_found.setdefault(v["rule_triggered"], []).append(v)

        for rule, viols in sorted(rules_found.items()):
            sev = viols[0]["severity"]
            sev_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")
            with st.expander(
                f"{sev_icon} {rule} — {len(viols)} violation(s)", expanded=(sev == "critical")
            ):
                st.markdown(rule_explanations.get(rule, ""))
                df_v = pd.DataFrame([{
                    "Point": v["point_index"],
                    "Value": round(v["observed_value"], 4),
                    "CL":   round(v["cl_center"], 4),
                    "UCL":  round(v["ucl"], 4),
                    "LCL":  round(v["lcl"], 4),
                    "Severity": v["severity"],
                    "Action": v.get("recommended_action", "")[:60],
                } for v in viols])
                st.dataframe(df_v, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No violations detected — process is in statistical control.")
