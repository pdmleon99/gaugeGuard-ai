"""Audit log endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
def list_audit_logs(
    event_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict:
    q = db.query(AuditLog)
    if event_type:
        q = q.filter(AuditLog.event_type == event_type)
    total = q.count()
    rows = q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "event_type": r.event_type,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "user_source": r.user_source,
                "status": r.status,
                "message": r.message,
                "metadata": r.metadata_json,
            }
            for r in rows
        ],
        "total": total,
    }
