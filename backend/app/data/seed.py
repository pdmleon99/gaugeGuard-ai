"""Demo seed — runs 6 analyses on first startup so the dashboard is never empty."""
from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime

log = logging.getLogger(__name__)


def seed_demo_data() -> None:
    """Populate DB with demo studies and alerts if the database is empty."""
    from ..database import SessionLocal
    from ..models.db_models import GRRStudy, SPCAnalysis
    from ..engines.grr_engine import run_grr_anova, run_grr_range
    from ..engines.spc_engine import run_spc_analysis, SPCViolation
    from ..services.alert_manager import alert_manager
    from ..services.audit_service import audit
    from ..api.datasets import get_dataset_df

    with SessionLocal() as db:
        if db.query(GRRStudy).count() > 0:
            return  # already seeded

    log.info("[GaugeGuard] Seeding demo data...")

    _seed_grr(get_dataset_df, alert_manager, audit)
    _seed_spc(get_dataset_df, alert_manager, audit)

    log.info("[GaugeGuard] Demo seed complete.")


# ── GR&R ─────────────────────────────────────────────────────────────────────

_GRR_SCENARIOS = [
    # (dataset_id, equipment_id, method)
    ("grr_pass",     "CMM-001",  "ANOVA"),
    ("grr_marginal", "CMM-002",  "ANOVA"),
    ("grr_fail",     "CMM-003",  "Range"),
]


def _seed_grr(get_df, alert_manager, audit) -> None:
    from ..database import SessionLocal
    from ..models.db_models import GRRStudy
    from ..engines.grr_engine import run_grr_anova, run_grr_range

    for dataset_id, equipment_id, method in _GRR_SCENARIOS:
        try:
            df = get_df(dataset_id)
            result = (
                run_grr_anova(df, equipment_id)
                if method == "ANOVA"
                else run_grr_range(df, equipment_id)
            )
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
                result_json=json.dumps(dataclasses.asdict(result)),
                calculation_time_ms=result.calculation_time_ms,
                dataset_name=dataset_id,
            )
            with SessionLocal() as db:
                db.add(study)
                db.commit()

            audit.log("GRR_ANALYSIS_COMPLETE", "GRRStudy", result.study_id,
                      f"[seed] status={result.status} %GRR={result.percent_grr:.2f}%")
            alert_manager.process_grr_result(result)

        except Exception as exc:
            log.warning("[GaugeGuard] GRR seed failed for %s: %s", dataset_id, exc)


# ── SPC ──────────────────────────────────────────────────────────────────────

_SPC_SCENARIOS = [
    # (dataset_id, process_id, subgroup_size)
    ("spc_anomalies", "LINE-A",    5),
    ("spc_shift",     "LINE-B",    5),
    ("spc_stable",    "LINE-C",    5),
]


def _seed_spc(get_df, alert_manager, audit) -> None:
    from ..database import SessionLocal
    from ..models.db_models import SPCAnalysis
    from ..engines.spc_engine import run_spc_analysis, SPCViolation

    for dataset_id, process_id, subgroup_size in _SPC_SCENARIOS:
        try:
            df = get_df(dataset_id)
            result = run_spc_analysis(df, process_id=process_id, subgroup_size=subgroup_size)

            def _v(v: SPCViolation) -> dict:
                d = dataclasses.asdict(v)
                d["timestamp"] = (
                    d["timestamp"].isoformat()
                    if hasattr(d["timestamp"], "isoformat")
                    else str(d["timestamp"])
                )
                return d

            violations_list = [_v(v) for v in result.violations]
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
            with SessionLocal() as db:
                db.add(record)
                db.commit()

            audit.log("SPC_ANALYSIS_COMPLETE", "SPCAnalysis", result.analysis_id,
                      f"[seed] status={result.process_status} violations={len(result.violations)}")
            alert_manager.process_spc_violations(result.violations, result.analysis_id)

        except Exception as exc:
            log.warning("[GaugeGuard] SPC seed failed for %s: %s", dataset_id, exc)
