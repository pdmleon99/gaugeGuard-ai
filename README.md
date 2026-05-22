# GaugeGuard AI

Manufacturing measurement system analysis — GR&R (Gauge R&R) and SPC (Statistical Process Control) monitoring with automated alerting.

## Quick Start

```bash
# Install backend dependencies
cd backend && pip install -r requirements.txt

# Generate sample data
python -m app.data.generators

# Start backend
uvicorn app.main:app --reload --port 8000

# Start frontend (separate terminal)
cd frontend && streamlit run app.py
```

## Docker

```bash
docker-compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:8501
- API docs: http://localhost:8000/docs

## Run Tests

```bash
cd backend && python -m pytest tests/ -v
```

## Features

- **GR&R Analysis**: ANOVA and Range methods per AIAG MSA 4th Edition
- **SPC Monitoring**: X-bar/R, I-MR charts with all 8 Nelson rules
- **Alert Management**: Real-time alerts with Slack/email notification
- **Audit Trail**: Complete event log for all system actions
- **Reports**: Professional HTML GR&R reports

## Sample Data

| File | %GRR | Classification |
|------|------|----------------|
| grr_pass.csv | ~6% | ACCEPTABLE |
| grr_marginal.csv | ~25% | MARGINAL |
| grr_fail.csv | ~42% | NOT_ACCEPTABLE |
| spc_stable.csv | 0 violations | IN_CONTROL |
| spc_shift.csv | Rule 2 triggered | OUT_OF_CONTROL |
| spc_drift.csv | Rule 3 triggered | OUT_OF_CONTROL |
| spc_anomalies.csv | 5 Rule 1 violations | OUT_OF_CONTROL |
