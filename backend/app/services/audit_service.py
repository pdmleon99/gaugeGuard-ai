"""Singleton audit service — every major action calls audit.log()."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from ..database import SessionLocal
from ..models.db_models import AuditLog

VALID_EVENTS = {
    "DATASET_UPLOADED", "GRR_ANALYSIS_STARTED", "GRR_ANALYSIS_COMPLETE",
    "GRR_ANALYSIS_FAILED", "SPC_ANALYSIS_STARTED", "SPC_ANALYSIS_COMPLETE",
    "ALERT_GENERATED", "ALERT_ACKNOWLEDGED", "ALERT_FEEDBACK_ADDED",
    "REPORT_GENERATED", "SETTINGS_UPDATED", "DATASET_GENERATED",
}


class AuditService:
    def log(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str = "",
        message: str = "",
        metadata: dict | None = None,
        status: str = "success",
        user_source: str = "system",
    ) -> None:
        entry = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_source=user_source,
            status=status,
            message=message,
            metadata_json=json.dumps(metadata or {}),
        )
        with SessionLocal() as db:
            db.add(entry)
            db.commit()


audit = AuditService()
