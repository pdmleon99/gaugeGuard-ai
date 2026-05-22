# GaugeGuard AI — Architecture

## Components

```
gaugeGuard/
├── backend/          FastAPI + SQLAlchemy
│   ├── engines/      GRR, SPC, Anomaly computation
│   ├── api/          Thin HTTP routes
│   ├── services/     Alert manager, audit, reports
│   └── models/       ORM models (SQLite/PostgreSQL)
├── frontend/         Streamlit + Plotly
│   └── pages/        Multi-page app
└── data/samples/     Generated CSVs
```

## Data Flow

1. CSV uploaded or generated → stored in `/data/samples/`
2. POST `/api/v1/grr/analyze` → grr_engine.py → GRRResult → persisted
3. Alert manager checks result → generates Alert → notifies Slack/email
4. Audit service logs every step to `audit_logs` table
5. Frontend polls API, renders Plotly charts

## Key Design Decisions

- **ANOVA default**: More robust than Range method; interaction detection
- **d2\* interpolation**: Exact AIAG MSA values + linear interpolation
- **Nelson rules**: All 8 implemented, each configurable per analysis
- **Alert deduplication**: Cooldown window (default 30 min) prevents spam
- **Singleton DB session**: SessionLocal factory, yielded per request
