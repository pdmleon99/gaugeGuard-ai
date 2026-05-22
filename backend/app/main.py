"""GaugeGuard AI — FastAPI backend entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables, seed_default_settings
from .api import grr, spc, alerts, audit, datasets, settings


def _ensure_samples() -> None:
    """Generate sample CSVs on first startup if they don't exist."""
    from .config import SAMPLES_DIR
    from .data.generators import generate_grr_samples, generate_spc_samples
    needed = [
        "grr_pass.csv", "grr_marginal.csv", "grr_fail.csv",
        "spc_stable.csv", "spc_shift.csv", "spc_drift.csv", "spc_anomalies.csv",
    ]
    if not all((SAMPLES_DIR / f).exists() for f in needed):
        print("[GaugeGuard] Generating sample datasets...")
        try:
            generate_grr_samples()
            generate_spc_samples()
            print("[GaugeGuard] Sample datasets ready.")
        except Exception as exc:
            print(f"[GaugeGuard] Warning: sample generation failed — {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    seed_default_settings()
    _ensure_samples()
    yield


app = FastAPI(
    title="GaugeGuard AI",
    version="1.0.0",
    description="Manufacturing measurement system analysis — GR&R and SPC monitoring.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(datasets.router, prefix=PREFIX)
app.include_router(grr.router, prefix=PREFIX)
app.include_router(spc.router, prefix=PREFIX)
app.include_router(alerts.router, prefix=PREFIX)
app.include_router(audit.router, prefix=PREFIX)
app.include_router(settings.router, prefix=PREFIX)


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
