"""Settings — system configuration."""
from __future__ import annotations

import os
from datetime import datetime
import requests
import streamlit as st

def _backend_url() -> str:
    if url := os.getenv("BACKEND_URL"):
        return url
    try:
        return st.secrets["BACKEND_URL"]
    except Exception:
        return "http://localhost:8000"

BACKEND = _backend_url()
API = f"{BACKEND}/api/v1"

st.set_page_config(page_title="Settings — GaugeGuard AI", layout="wide", page_icon="⚙️")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: linear-gradient(135deg,#0f0c29,#302b63,#24243e); }
.card { background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);
        border-radius:14px;padding:20px 24px;margin-bottom:16px; }
.section-title { font-size:1rem;font-weight:700;color:#a78bfa;text-transform:uppercase;
                 letter-spacing:1px;margin-bottom:12px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.divider()
    st.markdown("""
    **Configurable parameters:**

    **GR&R:**
    - Acceptable threshold: < 10% (AIAG)
    - Marginal threshold: < 30% (AIAG)
    - Minimum NDC: ≥ 5

    **SPC:**
    - Baseline n: first 25 subgroups
    - Alert cooldown: 30 min

    **Alert channels:**
    - Slack Webhook (optional)
    - SMTP Email (optional)
    - If not configured, alerts are simulated in server logs
    """)

st.markdown("# ⚙️ System Settings")
st.markdown("> Adjust AIAG thresholds, SPC parameters, and notification channels.")

r = requests.get(f"{API}/settings", timeout=40)
current = r.json() if r.status_code == 200 else {}
last_updated = current.get("updated_at", "—")[:16].replace("T", " ") if current else "—"
st.caption(f"Last updated: {last_updated}")

with st.form("settings_form"):
    st.markdown('<div class="section-title">📏 GR&R Thresholds (AIAG MSA 4th Ed.)</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    grr_acc  = c1.number_input(
        "Acceptable %GRR (< X)", 0.0, 100.0, float(current.get("grr_acceptable_pct", 10.0)), 0.5,
        help="Below this value the gauge is ACCEPTABLE. AIAG recommends 10%.",
    )
    grr_marg = c2.number_input(
        "Marginal %GRR (< X)", 0.0, 100.0, float(current.get("grr_marginal_pct", 30.0)), 0.5,
        help="Between acceptable and marginal, the gauge is MARGINAL. AIAG recommends 30%.",
    )
    ndc_min  = c3.number_input(
        "Minimum NDC", 1, 20, int(current.get("ndc_minimum", 5)),
        help="Minimum number of distinct categories. AIAG recommends ≥ 5.",
    )

    st.divider()
    st.markdown('<div class="section-title">📊 SPC Parameters</div>', unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    study_k    = c4.number_input(
        "Study factor k", 4, 8, int(current.get("study_k", 6)),
        help="Study variation multiplier. AIAG: 6 (99.73% coverage) or 5.15 (99%).",
    )
    alpha      = c5.number_input(
        "Interaction alpha", 0.01, 0.50, float(current.get("alpha_interaction", 0.25)), 0.01,
        help="p-value threshold for Part×Operator interaction. AIAG standard: 0.25.",
    )
    baseline_n = c6.number_input(
        "SPC baseline subgroups", 5, 100, int(current.get("baseline_n_spc", 25)),
        help="Number of initial subgroups used to estimate control limits.",
    )

    st.divider()
    st.markdown('<div class="section-title">🔔 Alert Channels</div>', unsafe_allow_html=True)
    cooldown  = st.number_input(
        "Alert cooldown (minutes)", 1, 480, int(current.get("cooldown_minutes", 30)),
        help="Minimum time between two alerts for the same process+rule combination.",
    )
    slack_url = st.text_input(
        "Slack Webhook URL", current.get("slack_webhook_url") or "",
        help="If not configured, alerts are printed to server logs with [SLACK SIMULATED].",
    )
    c_smtp, c_port = st.columns(2)
    smtp      = c_smtp.text_input("SMTP Host", current.get("smtp_host") or "")
    smtp_port = c_port.number_input("SMTP Port", 1, 65535, int(current.get("smtp_port", 587)))

    st.divider()
    st.markdown('<div class="section-title">🔧 System Mode</div>', unsafe_allow_html=True)
    demo = st.checkbox(
        "Demo Mode", value=bool(current.get("demo_mode", True)),
        help="In demo mode, sample data is always available and notifications are simulated.",
    )

    submitted = st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True)

if submitted:
    payload = {
        "grr_acceptable_pct": grr_acc,
        "grr_marginal_pct":   grr_marg,
        "ndc_minimum":        ndc_min,
        "study_k":            study_k,
        "alpha_interaction":  alpha,
        "baseline_n_spc":     baseline_n,
        "cooldown_minutes":   cooldown,
        "slack_webhook_url":  slack_url or None,
        "smtp_host":          smtp or None,
        "smtp_port":          smtp_port,
        "demo_mode":          demo,
    }
    sr = requests.put(f"{API}/settings", json=payload, timeout=40)
    if sr.status_code == 200:
        st.success("✅ Settings saved successfully.")
        st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    else:
        st.error(f"❌ Save failed: {sr.text}")
