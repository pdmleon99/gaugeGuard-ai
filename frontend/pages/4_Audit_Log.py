"""Audit Log — complete event history."""
from __future__ import annotations

import os
import requests
import pandas as pd
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

st.set_page_config(page_title="Audit Log — GaugeGuard AI", layout="wide", page_icon="📋")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: linear-gradient(135deg,#0f0c29,#302b63,#24243e); }
code { background:rgba(99,102,241,.15);color:#a78bfa;border-radius:4px;padding:1px 5px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 📋 Audit Log")
    st.divider()
    st.markdown("""
    **Why does this matter?**

    The audit trail records **every system action**:
    - When a dataset was uploaded or generated
    - Which analyses ran and when
    - Which alerts were fired
    - Who acknowledged each alert
    - Configuration changes

    **Use cases:**
    - Traceability for ISO 9001 / IATF 16949 audits
    - Debugging past analyses
    - Team accountability
    """)

st.markdown("# 📋 Audit Trail")
st.markdown("""
> Immutable log of all system actions. Supports traceability requirements for ISO 9001 / IATF 16949.
""")

event_types = [
    "", "DATASET_UPLOADED", "DATASET_GENERATED",
    "GRR_ANALYSIS_STARTED", "GRR_ANALYSIS_COMPLETE", "GRR_ANALYSIS_FAILED",
    "SPC_ANALYSIS_STARTED", "SPC_ANALYSIS_COMPLETE",
    "ALERT_GENERATED", "ALERT_ACKNOWLEDGED", "ALERT_FEEDBACK_ADDED",
    "REPORT_GENERATED", "SETTINGS_UPDATED",
]

col_et, col_lim = st.columns([2, 1])
event_filter = col_et.selectbox(
    "Filter by event type", event_types,
    format_func=lambda x: x if x else "— All events —",
)
limit = col_lim.number_input("Max rows", 10, 500, 100, step=10)

params: dict = {"limit": limit}
if event_filter:
    params["event_type"] = event_filter

r = requests.get(f"{API}/audit-logs", params=params, timeout=40)
items = r.json().get("items", []) if r.status_code == 200 else []

if not items:
    st.info("No audit log entries yet. Run an analysis first.")
else:
    st.caption(f"Showing {len(items)} events (total in DB: {r.json().get('total', '?')})")

    event_icon = {
        "DATASET_UPLOADED": "📁", "DATASET_GENERATED": "⚙️",
        "GRR_ANALYSIS_STARTED": "▶️", "GRR_ANALYSIS_COMPLETE": "✅", "GRR_ANALYSIS_FAILED": "❌",
        "SPC_ANALYSIS_STARTED": "▶️", "SPC_ANALYSIS_COMPLETE": "✅",
        "ALERT_GENERATED": "🔔", "ALERT_ACKNOWLEDGED": "✅", "ALERT_FEEDBACK_ADDED": "💬",
        "REPORT_GENERATED": "📄", "SETTINGS_UPDATED": "⚙️",
    }

    df = pd.DataFrame(items)
    df["icon"] = df["event_type"].map(lambda x: event_icon.get(x, "•"))
    df["Time"]    = df["timestamp"].str[:19].str.replace("T", " ")
    df["Event"]   = df["icon"] + " " + df["event_type"]
    df["Type"]    = df["entity_type"]
    df["Message"] = df["message"]
    df["Status"]  = df["status"]

    def _color_status(s):
        return ["color:#ef4444" if v == "error" else "color:#22c55e" for v in s]

    st.dataframe(
        df[["Time", "Event", "Type", "Message", "Status"]].style.apply(
            _color_status, subset=["Status"]
        ),
        use_container_width=True,
        height=500,
        hide_index=True,
    )
