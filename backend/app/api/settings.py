"""Settings endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Settings
from ..services.audit_service import audit

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    grr_acceptable_pct: float | None = None
    grr_marginal_pct: float | None = None
    ndc_minimum: int | None = None
    study_k: int | None = None
    alpha_interaction: float | None = None
    baseline_n_spc: int | None = None
    cooldown_minutes: int | None = None
    slack_webhook_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    demo_mode: bool | None = None


def _to_dict(s: Settings) -> dict:
    return {
        "id": s.id,
        "grr_acceptable_pct": s.grr_acceptable_pct,
        "grr_marginal_pct": s.grr_marginal_pct,
        "ndc_minimum": s.ndc_minimum,
        "study_k": s.study_k,
        "alpha_interaction": s.alpha_interaction,
        "baseline_n_spc": s.baseline_n_spc,
        "cooldown_minutes": s.cooldown_minutes,
        "slack_webhook_url": s.slack_webhook_url,
        "smtp_host": s.smtp_host,
        "smtp_port": s.smtp_port,
        "demo_mode": s.demo_mode,
        "updated_at": s.updated_at.isoformat(),
    }


@router.get("")
def get_settings(db: Session = Depends(get_db)) -> dict:
    s = db.get(Settings, 1) or Settings()
    return _to_dict(s)


@router.put("")
def update_settings(req: SettingsUpdate, db: Session = Depends(get_db)) -> dict:
    s = db.get(Settings, 1)
    if not s:
        s = Settings(id=1)
        db.add(s)

    for field, val in req.model_dump(exclude_none=True).items():
        setattr(s, field, val)
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    audit.log("SETTINGS_UPDATED", "Settings", "1", "Settings updated", req.model_dump(exclude_none=True))
    return _to_dict(s)
