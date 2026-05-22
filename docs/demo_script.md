# GaugeGuard AI — Demo Script (15 minutes)

## Setup (before the demo)

```bash
# Terminal 1 — Backend
cd gaugeGuard/backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd gaugeGuard/frontend
streamlit run app.py
```

Open: **http://localhost:8501**

---

## Step 1 — Dashboard (2 min)

**What to show:**
- The hero banner and 4 KPI cards
- Say: *"This is the real-time status of all measurement equipment and production processes."*
- Expand the "What is GR&R and SPC?" accordion — point to the AIAG threshold tables

**Key message:**
> "If your measurement equipment is unreliable, every quality decision you make is compromised.
> GaugeGuard quantifies exactly how much of your measured variation comes from the gauge itself."

---

## Step 2 — GR&R: Passing gauge (3 min)

1. Go to **GR&R Analysis**
2. Select `grr_pass`, method `ANOVA`, equipment `CMM-001`
3. Click **Run GR&R Analysis**

**What to point out in the results:**
- Green badge **ACCEPTABLE**
- %GRR ~6.3% — well below AIAG's 10% threshold
- NDC = 22 — the gauge can distinguish 22 distinct part categories
- Pie chart: ~96% of variation comes from real part differences, not the gauge
- ANOVA table: interaction pooled → all 3 operators measure consistently

---

## Step 3 — GR&R: Failing gauge (2 min)

1. Switch to `grr_fail`, same equipment
2. Run analysis

**What to point out:**
- Red badge **NOT ACCEPTABLE** — %GRR ~42%
- Alert fires automatically → visible in the dashboard Recent Alerts
- Recommendation: *"Do not use this gauge for production decisions"*
- Compare the pie chart: gauge variation now dominates

---

## Step 4 — SPC: Anomaly detection (3 min)

1. Go to **SPC Monitoring**
2. Scenario: `anomalies`, subgroup size: 1
3. Run

**What to point out:**
- 5 red X marks on the X-bar chart at exactly indices 40, 80, 120, 160, 195
- Rule 1 violations table: "Immediate special cause — 0.27% probability event"
- Status: 🚨 OUT OF CONTROL

**Then show `shift`:**
- Mean jumps at point 100 (+3.6σ)
- Rule 2: 9 consecutive points on the same side detect the shift
- Real-world interpretation: shift change, new material batch, operator swap

---

## Step 5 — Alerts (2 min)

1. Go to **Alerts**
2. Show the list of automatically generated alerts with severity color coding
3. Click a critical alert → acknowledge it (✅)
4. Rate it as "Relevant"

**Key message:**
> "The system tracks whether alerts are actually actionable. If 20% turn out to be
> false positives, the team knows to tune the thresholds."

---

## Step 6 — Audit Log (1 min)

1. Go to **Audit Log**
2. Show the complete event trail
3. Filter by `GRR_ANALYSIS_COMPLETE`

**Key message:**
> "Every analysis, every alert, every acknowledgement is automatically logged.
> Full traceability for ISO 9001 / IATF 16949 audits — no manual record keeping."

---

## Common demo questions

**How fast is an analysis?**
< 50ms for both GR&R and SPC. Real-time.

**Can it connect to real plant data?**
Yes — any CSV matching the standard format, or via the REST API directly from the measurement system.

**What about historical data?**
Everything is persisted in SQLite (or PostgreSQL in production). Full study history is visible in the dashboard.

**Does it support multiple equipment and processes simultaneously?**
Yes — each GR&R study has an `equipment_id`, each SPC analysis has a `process_id`. Unlimited concurrent equipment.

**What's NDC?**
Number of Distinct Categories — how many different part groups the gauge can reliably tell apart. AIAG requires ≥ 5.
