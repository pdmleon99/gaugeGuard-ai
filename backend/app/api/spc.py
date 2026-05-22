"""SPC analysis endpoints."""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.spc_engine import run_spc_analysis, SPCViolation
from ..models.db_models import SPCAnalysis
from ..schemas.spc_schemas import SPCAnalyzeRequest, SPCAnalysisSummary
from ..services.alert_manager import alert_manager
from ..services.audit_service import audit
from .datasets import get_dataset_df

router = APIRouter(prefix="/spc", tags=["spc"])


def _violation_to_dict(v: SPCViolation) -> dict:
    d = dataclasses.asdict(v)
    d["timestamp"] = d["timestamp"].isoformat() if hasattr(d["timestamp"], "isoformat") else str(d["timestamp"])
    return d


@router.post("/analyze")
def analyze_spc(req: SPCAnalyzeRequest, db: Session = Depends(get_db)) -> dict:
    audit.log("SPC_ANALYSIS_STARTED", "SPCAnalysis", req.dataset_id,
              f"process={req.process_id} n={req.subgroup_size}")
    try:
        df = get_dataset_df(req.dataset_id)
        result = run_spc_analysis(
            df,
            process_id=req.process_id,
            subgroup_size=req.subgroup_size,
            enabled_rules=req.enabled_rules,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

    violations_list = [_violation_to_dict(v) for v in result.violations]

    record = SPCAnalysis(
        id=result.analysis_id,
        created_at=datetime.utcnow(),
        process_id=result.process_id,
        chart_type=result.chart_type,
        n_violations=len(result.violations),
        process_status=result.process_status,
        result_json=json.dumps({
            **dataclasses.asdict(result),
            "violations": violations_list,
        }),
    )
    db.add(record)
    db.commit()

    audit.log("SPC_ANALYSIS_COMPLETE", "SPCAnalysis", result.analysis_id,
              f"status={result.process_status} violations={len(result.violations)}")
    alert_manager.process_spc_violations(result.violations, result.analysis_id)

    return {
        **dataclasses.asdict(result),
        "violations": violations_list,
    }


@router.get("/analyses")
def list_analyses(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)) -> dict:
    rows = db.query(SPCAnalysis).order_by(SPCAnalysis.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(SPCAnalysis).count()
    items = [
        SPCAnalysisSummary(
            id=r.id,
            created_at=r.created_at.isoformat(),
            process_id=r.process_id,
            chart_type=r.chart_type,
            n_violations=r.n_violations,
            process_status=r.process_status,
        )
        for r in rows
    ]
    return {"items": [i.model_dump() for i in items], "total": total}


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> dict:
    rec = db.get(SPCAnalysis, analysis_id)
    if not rec:
        raise HTTPException(404, f"Analysis {analysis_id} not found.")
    return json.loads(rec.result_json)
