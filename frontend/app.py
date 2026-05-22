"""GaugeGuard AI — Main Dashboard."""
from __future__ import annotations

import os
import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
API = f"{BACKEND}/api/v1"

st.set_page_config(
    page_title="GaugeGuard AI",
    layout="wide",
    page_icon="🔬",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #e0e0e0;
}
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.04);
    border-right: 1px solid rgba(255,255,255,0.08);
}
.kpi-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 22px 24px;
    text-align: center;
    backdrop-filter: blur(8px);
    transition: transform .2s;
}
.kpi-card:hover { transform: translateY(-3px); }
.kpi-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #9ca3af;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 40px;
    font-weight: 800;
    background: linear-gradient(90deg,#60a5fa,#a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}
.kpi-sub { font-size: 12px; color: #6b7280; margin-top: 4px; }
.hero {
    background: linear-gradient(135deg,rgba(96,165,250,.15),rgba(167,139,250,.15));
    border: 1px solid rgba(96,165,250,.25);
    border-radius: 20px;
    padding: 36px 40px;
    margin-bottom: 28px;
}
.hero h1 { font-size:2.6rem; font-weight:900; margin:0 0 6px 0; color:#fff; }
.hero p  { font-size:1.05rem; color:#94a3b8; margin:0; }
.badge-ok   { background:#065f46; color:#6ee7b7; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }
.badge-warn { background:#7c2d12; color:#fcd34d; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }
.badge-bad  { background:#7f1d1d; color:#fca5a5; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }
.badge-info { background:#1e3a5f; color:#93c5fd; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e2e8f0;
    border-left: 3px solid #6366f1;
    padding-left: 12px;
    margin: 24px 0 12px 0;
}
.guide-step {
    background: rgba(99,102,241,.10);
    border: 1px solid rgba(99,102,241,.30);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.guide-num {
    display: inline-block;
    background: #6366f1;
    color: white;
    border-radius: 50%;
    width: 26px; height: 26px;
    text-align: center;
    line-height: 26px;
    font-size: 13px;
    font-weight: 800;
    margin-right: 10px;
}
.guide-text { font-size: 14px; color: #cbd5e1; }
hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 20px 0; }
</style>
""", unsafe_allow_html=True)


def _get(path: str) -> dict | None:
    try:
        r = requests.get(f"{API}{path}", timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def backend_ok() -> bool:
    try:
        return requests.get(f"{BACKEND}/health", timeout=3).status_code == 200
    except Exception:
        return False


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 GaugeGuard AI")
    st.markdown("*Intelligent measurement quality*")
    st.divider()

    alive = backend_ok()
    if alive:
        st.markdown("🟢 **Backend connected**")
    else:
        st.markdown("🔴 **Backend unavailable**  \nStart with `uvicorn app.main:app`")
    st.divider()

    st.markdown("### 📖 Demo walkthrough")
    steps = [
        ("1", "GR&R Analysis", "Load `grr_pass` and press **Analyze**. The gauge passes at ~6% GRR."),
        ("2", "GR&R Analysis", "Switch to `grr_fail`. System flags it ❌ NOT ACCEPTABLE and fires an alert."),
        ("3", "SPC Monitoring", "Select `anomalies`, subgroup=1. Chart shows 5 red-X spikes at known indices."),
        ("4", "SPC Monitoring", "Try `shift` — Rule 2 (9-point run) detects the process mean change at point 100."),
        ("5", "Alerts", "Go to Alerts, acknowledge one, mark it as *false positive* to train the system."),
        ("6", "Audit Log", "Review the full log — every action is automatically recorded for traceability."),
    ]
    for num, page, desc in steps:
        st.markdown(f"""
        <div class="guide-step">
          <span class="guide-num">{num}</span>
          <strong style="color:#a78bfa">{page}</strong><br>
          <span class="guide-text">{desc}</span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.caption("v1.0.0 · Python 3.12 · AIAG MSA 4th Ed.")


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🔬 GaugeGuard AI</h1>
  <p>
    Manufacturing measurement system analysis platform.<br>
    <strong style="color:#c4b5fd">GR&R (Gauge Repeatability &amp; Reproducibility) · SPC (Statistical Process Control) · Automated Alerts</strong>
  </p>
</div>
""", unsafe_allow_html=True)


# ── KPIs ──────────────────────────────────────────────────────────────────────
grr_data    = _get("/grr/studies?limit=10")
alert_data  = _get("/alerts?limit=200")
spc_data    = _get("/spc/analyses?limit=10")
alert_stats = _get("/alerts/stats")

studies_items = grr_data["items"]   if grr_data   else []
alerts_items  = alert_data["items"] if alert_data else []

total_studies  = grr_data["total"] if grr_data else 0
pass_count     = sum(1 for s in studies_items if s["status"] == "ACCEPTABLE")
pass_rate      = round(pass_count / len(studies_items) * 100, 1) if studies_items else 0.0
active_alerts  = sum(1 for a in alerts_items if not a["acknowledged"])
relevance_rate = round((alert_stats or {}).get("relevance_rate", 0) * 100, 1)

cols = st.columns(4)
kpis = [
    ("Total GR&R Studies",    total_studies,           "equipment systems analyzed",   "🏭"),
    ("Pass Rate",             f"{pass_rate}%",          "below 10% GRR threshold",      "✅"),
    ("Active Alerts",         active_alerts,            "unacknowledged",               "🔔"),
    ("Alert Relevance Rate",  f"{relevance_rate}%",     "confirmed by operator",        "🎯"),
]
for col, (label, value, sub, icon) in zip(cols, kpis):
    col.markdown(f"""
    <div class="kpi-card">
      <div style="font-size:28px;margin-bottom:4px">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Explainer accordion ───────────────────────────────────────────────────────
with st.expander("ℹ️  What is GR&R and SPC? — Click to understand the system before the demo", expanded=False):
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("""
        ### 📏 Gauge R&R (Repeatability & Reproducibility)

        **Problem it solves:**
        Can we trust our measurement equipment? Or does it introduce so much variation that our quality decisions are unreliable?

        **How it works:**
        - **10 parts** measured by **3 operators** with **3 repetitions** each = 90 readings
        - The system separates: true part-to-part variation vs. gauge + operator variation

        **AIAG MSA criteria (automotive industry standard):**
        | %GRR | Decision |
        |------|----------|
        | < 10% | ✅ **ACCEPTABLE** — reliable gauge |
        | 10–30% | ⚠️ **MARGINAL** — evaluate by criticality |
        | > 30% | ❌ **NOT ACCEPTABLE** — do not use in production |

        **NDC (Number of Distinct Categories):** must be ≥ 5 to adequately discriminate between parts.
        """)
    with col_r:
        st.markdown("""
        ### 📊 SPC (Statistical Process Control)

        **Problem it solves:**
        Is the process in statistical control? Or are there special causes requiring intervention?

        **How it works:**
        - Continuously monitors part dimensions
        - Calculates control limits (UCL/LCL) from historical baseline variation
        - Applies **8 Nelson Rules** to detect anomalous patterns

        **Key rules:**
        | Rule | What it detects |
        |------|-----------------|
        | Rule 1 | Point beyond ±3σ — immediate special cause |
        | Rule 2 | 9 consecutive points one side — mean shift |
        | Rule 3 | 6 points in trend — process drift |
        | Rule 5 | 2 of 3 points beyond ±2σ — early shift signal |

        **σ estimated using:** R̄/d₂ (exact AIAG constant per subgroup size)
        """)


# ── Data tables ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1.1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-title">📋 Recent GR&R Studies</div>', unsafe_allow_html=True)

    if studies_items:
        import pandas as pd

        def _status_badge(s: str) -> str:
            m = {"ACCEPTABLE": "badge-ok", "MARGINAL": "badge-warn", "NOT_ACCEPTABLE": "badge-bad"}
            css = m.get(s, "badge-info")
            return f'<span class="{css}">{s}</span>'

        for item in studies_items[:5]:
            badge = _status_badge(item["status"])
            pct = item["percent_grr"]
            bar_color = "#22c55e" if pct < 10 else "#f59e0b" if pct < 30 else "#ef4444"
            bar_w = min(int(pct * 2), 100)
            ts = item["created_at"][:16].replace("T", " ")
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                        border-radius:12px;padding:14px 18px;margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <div>
                  <strong style="font-size:15px">{item["equipment_id"]}</strong>
                  <span style="color:#64748b;font-size:12px;margin-left:8px">{ts}</span>
                </div>
                {badge}
              </div>
              <div style="display:flex;align-items:center;gap:12px">
                <div style="flex:1;background:rgba(255,255,255,0.08);border-radius:99px;height:6px">
                  <div style="width:{bar_w}%;background:{bar_color};border-radius:99px;height:6px"></div>
                </div>
                <span style="font-size:13px;color:#e2e8f0;font-weight:700">%GRR {pct:.1f}%</span>
                <span style="font-size:12px;color:#6b7280">NDC={item["ndc"]}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:40px;color:#4b5563;background:rgba(255,255,255,0.02);
                    border:1px dashed rgba(255,255,255,0.1);border-radius:12px">
          <div style="font-size:36px;margin-bottom:8px">🏭</div>
          <div>No studies yet.</div>
          <div style="font-size:13px;margin-top:4px">Go to <strong>GR&R Analysis</strong> and load a scenario.</div>
        </div>
        """, unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="section-title">🔔 Recent Alerts</div>', unsafe_allow_html=True)

    severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
    rule_desc = {
        "Rule 1": "Point beyond ±3σ",
        "Rule 2": "9 consecutive same side",
        "Rule 3": "6-point trend",
        "Rule 4": "14-point alternating",
        "Rule 5": "2/3 pts beyond 2σ",
        "Rule 6": "4/5 pts beyond 1σ",
        "Rule 7": "15 pts hugging CL",
        "Rule 8": "8 pts outside 1σ",
        "SPEC_VIOLATION": "Out of specification",
        "GRR_STATUS": "GR&R not acceptable",
    }

    if alerts_items:
        for a in alerts_items[:6]:
            sev = a["severity"]
            icon = severity_icon.get(sev, "⚪")
            rule = a["rule_triggered"]
            desc = rule_desc.get(rule, rule)
            ack_icon = "✅" if a["acknowledged"] else "⏳"
            ts = a["created_at"][:16].replace("T", " ")
            border = {"critical": "#ef4444", "warning": "#f59e0b", "info": "#3b82f6"}.get(sev, "#4b5563")
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
                        border-left:3px solid {border};border-radius:10px;padding:12px 16px;margin-bottom:8px">
              <div style="display:flex;justify-content:space-between">
                <span>{icon} <strong>{sev.upper()}</strong> — {desc}</span>
                <span style="font-size:11px;color:#64748b">{ack_icon} {ts}</span>
              </div>
              <div style="font-size:12px;color:#6b7280;margin-top:4px">
                Process: <code style="color:#94a3b8">{a["process_id"]}</code>
                · Value: <code style="color:#94a3b8">{a["observed_value"] if a["observed_value"] is not None else "—"}</code>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:40px;color:#4b5563;background:rgba(255,255,255,0.02);
                    border:1px dashed rgba(255,255,255,0.1);border-radius:12px">
          <div style="font-size:36px;margin-bottom:8px">🔔</div>
          <div>No alerts yet.</div>
          <div style="font-size:13px;margin-top:4px">They are generated automatically when anomalies are detected.</div>
        </div>
        """, unsafe_allow_html=True)


# ── System status ─────────────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="section-title">🖥️ System Status</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

last_spc_status = "N/A"
if spc_data and spc_data.get("items"):
    last_spc_status = spc_data["items"][0]["process_status"]

spc_color = {"IN_CONTROL": "#22c55e", "WARNING": "#f59e0b", "OUT_OF_CONTROL": "#ef4444"}.get(last_spc_status, "#4b5563")
spc_icon  = {"IN_CONTROL": "✅", "WARNING": "⚠️", "OUT_OF_CONTROL": "🚨"}.get(last_spc_status, "❓")

c1.markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Latest SPC process</div>
  <div style="font-size:32px">{spc_icon}</div>
  <div style="color:{spc_color};font-weight:700;font-size:14px">{last_spc_status.replace("_"," ")}</div>
</div>
""", unsafe_allow_html=True)

fp_rate = round((alert_stats or {}).get("fp_rate", 0) * 100, 1)
c2.markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">False Positive Rate</div>
  <div class="kpi-value" style="font-size:32px">{fp_rate}%</div>
  <div class="kpi-sub">of rated alerts</div>
</div>
""", unsafe_allow_html=True)

total_spc = spc_data["total"] if spc_data else 0
c3.markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">SPC Analyses</div>
  <div class="kpi-value" style="font-size:36px">{total_spc}</div>
  <div class="kpi-sub">processes monitored</div>
</div>
""", unsafe_allow_html=True)

backend_status = "🟢 Online" if alive else "🔴 Offline"
c4.markdown(f"""
<div class="kpi-card">
  <div class="kpi-label">Backend API</div>
  <div style="font-size:24px;font-weight:700;color:#e2e8f0;margin:8px 0">{backend_status}</div>
  <div class="kpi-sub">FastAPI · SQLite · {BACKEND}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.caption("GaugeGuard AI v1.0.0 · AIAG MSA 4th Edition · Nelson Rules · Python 3.12")
