"""Alerts — management and rating of alerts."""
from __future__ import annotations

import os
import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
API = f"{BACKEND}/api/v1"

st.set_page_config(page_title="Alerts — GaugeGuard AI", layout="wide", page_icon="🔔")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: linear-gradient(135deg,#0f0c29,#302b63,#24243e); }
.card { background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:14px;padding:18px 22px;margin-bottom:12px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🔔 Alert System")
    st.divider()
    st.markdown("""
    **How it works:**

    GaugeGuard automatically generates alerts when:
    - A GR&R study returns MARGINAL or NOT ACCEPTABLE
    - A Nelson Rule fires during SPC analysis
    - A part measurement exceeds specification limits

    **Recommended workflow:**
    1. 👀 Review critical alerts first
    2. ✅ Acknowledge alerts you have seen
    3. 📝 Rate each as relevant or false positive
    4. 📊 The system tracks your FP rate over time

    **Anti-spam:** 30-minute cooldown per process+rule combination.
    """)

st.markdown("# 🔔 Alert Management")
st.markdown("> Review, acknowledge, and rate alerts generated automatically by the system.")

# Stats bar
stats_r = requests.get(f"{API}/alerts/stats")
if stats_r.status_code == 200:
    s = stats_r.json()
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, (lbl, val, color) in zip([c1, c2, c3, c4, c5], [
        ("Total Alerts",       s["total"],                        "#e2e8f0"),
        ("Relevant",           s["relevant"],                     "#22c55e"),
        ("False Positives",    s["false_positive"],               "#ef4444"),
        ("Relevance Rate",     f"{s['relevance_rate']*100:.0f}%", "#a78bfa"),
        ("FP Rate",            f"{s['fp_rate']*100:.0f}%",        "#f59e0b"),
    ]):
        col.markdown(f"""
        <div class="card" style="text-align:center">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7280">{lbl}</div>
          <div style="font-size:2.2rem;font-weight:900;color:{color}">{val}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

col_s, col_a = st.columns(2)
severity_filter = col_s.multiselect(
    "Filter by severity", ["critical", "warning", "info"],
    default=["critical", "warning", "info"],
)
show_unacked_only = col_a.checkbox("Show unacknowledged only", value=False)

r = requests.get(f"{API}/alerts", params={"limit": 200})
items = r.json().get("items", []) if r.status_code == 200 else []

if severity_filter:
    items = [i for i in items if i["severity"] in severity_filter]
if show_unacked_only:
    items = [i for i in items if not i["acknowledged"]]

if not items:
    st.markdown("""
    <div style="text-align:center;padding:60px;color:#4b5563;background:rgba(255,255,255,0.02);
                border:1px dashed rgba(255,255,255,0.1);border-radius:16px">
      <div style="font-size:48px">🔔</div>
      <div style="font-size:18px;margin-top:8px">No alerts to display</div>
      <div style="font-size:13px;margin-top:4px">Run a GR&R or SPC analysis to generate alerts.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    sev_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
    rule_desc = {
        "Rule 1": "Point beyond ±3σ", "Rule 2": "9 pts same side", "Rule 3": "6-pt trend",
        "Rule 5": "2/3 pts >2σ", "Rule 6": "4/5 pts >1σ", "Rule 7": "15-pt hugging",
        "Rule 8": "8 pts >1σ", "SPEC_VIOLATION": "Out of specification", "GRR_STATUS": "GR&R failed",
    }

    for alert in items:
        sev = alert["severity"]
        icon = sev_icon.get(sev, "⚪")
        rule = alert["rule_triggered"]
        desc = rule_desc.get(rule, rule)
        ack_str = "✅ Acknowledged" if alert["acknowledged"] else "⏳ Pending"
        ts = alert["created_at"][:16].replace("T", " ")
        fb_str = {
            "relevant": "✅ Relevant",
            "false_positive": "❌ False positive",
        }.get(alert["feedback"] or "", "Not rated")

        with st.expander(
            f"{icon}  [{sev.upper()}]  {desc}  ·  {alert['process_id']}  ·  {ts}  ·  {ack_str}",
            expanded=False,
        ):
            col_info, col_actions = st.columns([1.5, 1])
            with col_info:
                st.markdown(f"""
                **Rule triggered:** `{rule}`
                **Process:** `{alert['process_id']}`
                **Observed value:** `{alert['observed_value']}`
                **Source:** {alert['source_type']} · ID `{alert['source_id'][:8]}...`
                **Current rating:** {fb_str}
                """)
            with col_actions:
                if not alert["acknowledged"]:
                    if st.button("✅ Acknowledge", key=f"ack_{alert['id']}"):
                        requests.post(f"{API}/alerts/{alert['id']}/acknowledge")
                        st.rerun()
                st.markdown("**Rate this alert:**")
                fb = st.radio(
                    "", ["relevant", "false_positive"],
                    key=f"fb_{alert['id']}", horizontal=True,
                    index=0 if alert.get("feedback") != "false_positive" else 1,
                    format_func=lambda x: "✅ Relevant" if x == "relevant" else "❌ False positive",
                )
                comment = st.text_input("Comment (optional)", key=f"cmt_{alert['id']}")
                if st.button("Save rating", key=f"sfb_{alert['id']}"):
                    requests.post(
                        f"{API}/alerts/{alert['id']}/feedback",
                        json={"feedback": fb, "comment": comment or None},
                    )
                    st.rerun()
