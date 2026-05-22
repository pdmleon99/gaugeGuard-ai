"""GR&R analysis endpoints."""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.grr_engine import run_grr_anova, run_grr_range, GRRResult
from ..models.db_models import GRRStudy
from ..schemas.grr_schemas import GRRAnalyzeRequest, GRRStudySummary, GRRStudyList
from ..services.alert_manager import alert_manager
from ..services.audit_service import audit
from ..services.report_service import generate_grr_html_report
from .datasets import get_dataset_df

router = APIRouter(prefix="/grr", tags=["grr"])


def _result_to_dict(r: GRRResult) -> dict:
    return dataclasses.asdict(r)


@router.post("/analyze")
def analyze_grr(req: GRRAnalyzeRequest, db: Session = Depends(get_db)) -> dict:
    audit.log("GRR_ANALYSIS_STARTED", "GRRStudy", req.dataset_id,
              f"method={req.method} equipment={req.equipment_id}")
    try:
        df = get_dataset_df(req.dataset_id)
        thresholds = req.thresholds or {}

        if req.method == "Range":
            result = run_grr_range(df, req.equipment_id, thresholds or None)
        else:
            result = run_grr_anova(df, req.equipment_id, thresholds or None)

    except ValueError as exc:
        audit.log("GRR_ANALYSIS_FAILED", "GRRStudy", req.dataset_id, str(exc), status="error")
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        audit.log("GRR_ANALYSIS_FAILED", "GRRStudy", req.dataset_id, str(exc), status="error")
        raise HTTPException(500, str(exc)) from exc

    study = GRRStudy(
        id=result.study_id,
        created_at=datetime.utcnow(),
        equipment_id=result.equipment_id,
        status=result.status,
        percent_grr=result.percent_grr,
        ndc=result.ndc,
        n_parts=result.n_parts,
        n_operators=result.n_operators,
        n_trials=result.n_trials,
        method=result.method,
        result_json=json.dumps(_result_to_dict(result)),
        calculation_time_ms=result.calculation_time_ms,
        dataset_name=req.dataset_id,
    )
    db.add(study)
    db.commit()

    audit.log("GRR_ANALYSIS_COMPLETE", "GRRStudy", result.study_id,
              f"status={result.status} %GRR={result.percent_grr:.2f}%")
    alert_manager.process_grr_result(result)

    return _result_to_dict(result)


@router.get("/studies", response_model=GRRStudyList)
def list_studies(
    skip: int = 0, limit: int = 50, db: Session = Depends(get_db)
) -> GRRStudyList:
    rows = db.query(GRRStudy).order_by(GRRStudy.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(GRRStudy).count()
    items = [
        GRRStudySummary(
            id=r.id,
            created_at=r.created_at.isoformat(),
            equipment_id=r.equipment_id,
            status=r.status,
            percent_grr=r.percent_grr,
            ndc=r.ndc,
            method=r.method,
            dataset_name=r.dataset_name,
        )
        for r in rows
    ]
    return GRRStudyList(items=items, total=total)


@router.get("/studies/{study_id}")
def get_study(study_id: str, db: Session = Depends(get_db)) -> dict:
    study = db.get(GRRStudy, study_id)
    if not study:
        raise HTTPException(404, f"Study {study_id} not found.")
    return json.loads(study.result_json)


@router.get("/studies/{study_id}/report")
def get_report(study_id: str, db: Session = Depends(get_db)) -> dict:
    study = db.get(GRRStudy, study_id)
    if not study:
        raise HTTPException(404, f"Study {study_id} not found.")
    result_data = json.loads(study.result_json)

    from ..engines.grr_engine import GRRResult
    result = GRRResult(**result_data)
    html = generate_grr_html_report(result, study.dataset_name)
    audit.log("REPORT_GENERATED", "GRRStudy", study_id, "HTML report generated")
    return {"study_id": study_id, "html": html}
