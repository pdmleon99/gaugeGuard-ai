"""Alert endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Alert
from ..schemas.alert_schemas import AlertFeedbackRequest, AlertStats
from ..services.audit_service import audit

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    severity: str | None = None,
    acknowledged: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    q = db.query(Alert)
    if severity:
        q = q.filter(Alert.severity == severity)
    if acknowledged is not None:
        q = q.filter(Alert.acknowledged == acknowledged)
    total = q.count()
    rows = q.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "items": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "source_type": r.source_type,
                "source_id": r.source_id,
                "severity": r.severity,
                "rule_triggered": r.rule_triggered,
                "process_id": r.process_id,
                "observed_value": r.observed_value,
                "acknowledged": r.acknowledged,
                "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
                "feedback": r.feedback,
                "feedback_comment": r.feedback_comment,
            }
            for r in rows
        ],
        "total": total,
    }


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)) -> dict:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found.")
    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    audit.log("ALERT_ACKNOWLEDGED", "Alert", alert_id, "Alert acknowledged")
    return {"id": alert_id, "acknowledged": True}


@router.post("/{alert_id}/feedback")
def add_feedback(alert_id: str, req: AlertFeedbackRequest, db: Session = Depends(get_db)) -> dict:
    if req.feedback not in ("relevant", "false_positive"):
        raise HTTPException(400, "feedback must be 'relevant' or 'false_positive'")
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found.")
    alert.feedback = req.feedback
    alert.feedback_comment = req.comment
    alert.feedback_at = datetime.utcnow()
    db.commit()
    audit.log("ALERT_FEEDBACK_ADDED", "Alert", alert_id, f"Feedback: {req.feedback}")
    return {"id": alert_id, "feedback": req.feedback}


@router.get("/stats", response_model=AlertStats)
def alert_stats(db: Session = Depends(get_db)) -> AlertStats:
    total = db.query(Alert).count()
    relevant = db.query(Alert).filter(Alert.feedback == "relevant").count()
    fp = db.query(Alert).filter(Alert.feedback == "false_positive").count()
    rated = relevant + fp
    return AlertStats(
        total=total,
        relevant=relevant,
        false_positive=fp,
        relevance_rate=round(relevant / rated, 3) if rated > 0 else 0.0,
        fp_rate=round(fp / rated, 3) if rated > 0 else 0.0,
    )
