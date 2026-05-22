"""SPC engine tests."""
from __future__ import annotations

import pandas as pd
import pytest

from app.engines.spc_engine import run_spc_analysis


def test_stable_no_critical(spc_df_stable):
    result = run_spc_analysis(spc_df_stable, "PROC", subgroup_size=5)
    assert result.n_critical == 0


def test_shift_triggers_warning(spc_df_shift):
    result = run_spc_analysis(spc_df_shift, "PROC", subgroup_size=5)
    assert result.n_critical + result.n_warning > 0
    rule2 = [v for v in result.violations if "Rule 2" in v.rule_triggered]
    assert len(rule2) > 0, "Rule 2 (9-point run) should trigger after shift"


def test_drift_triggers_trend(spc_df_drift):
    result = run_spc_analysis(spc_df_drift, "PROC", subgroup_size=1)
    rule3 = [v for v in result.violations if "Rule 3" in v.rule_triggered]
    assert len(rule3) > 0, "Rule 3 (trend) should trigger on drift dataset"


def test_anomalies_detected(spc_df_anomalies):
    result = run_spc_analysis(spc_df_anomalies, "PROC", subgroup_size=1)
    critical = [v for v in result.violations if v.severity == "critical"]
    assert len(critical) >= 5, f"Expected ≥5 critical violations, got {len(critical)}"


def test_stable_zero_variance():
    """Perfectly stable process — zero variance, no violations."""
    n = 50
    rows = [
        {
            "measurement_value": 25.0,
            "subgroup_id": i // 5,
            "process_id": "PROC",
            "equipment_id": "EQ",
            "metric": "dim",
        }
        for i in range(n)
    ]
    df = pd.DataFrame(rows)
    result = run_spc_analysis(df, "PROC", subgroup_size=5)
    assert result.n_critical == 0


def test_nelson_rule1_boundary():
    """Rule 1 uses strict >: point at exactly 3σ must NOT trigger; just above must trigger."""
    from datetime import datetime
    from app.engines.spc_engine import check_nelson_rules, DEFAULT_RULES

    sigma = 0.05
    cl = 25.0
    ucl = cl + 3 * sigma
    lcl = cl - 3 * sigma
    ts = [datetime.utcnow()] * 10

    # Point at exactly 3σ — should NOT trigger Rule 1
    vals_at = [25.0] * 9 + [cl + 3 * sigma]
    v_at = check_nelson_rules(vals_at, cl, sigma, ucl, lcl, DEFAULT_RULES, "P", "E", "m", ts)
    r1_at = [v for v in v_at if v.rule_triggered == "Rule 1" and v.point_index == 9]
    assert len(r1_at) == 0, "Point at exactly 3σ should not trigger Rule 1 (strict >)"

    # Point just above 3σ — should trigger
    vals_over = [25.0] * 9 + [cl + 3 * sigma + 1e-6]
    v_over = check_nelson_rules(vals_over, cl, sigma, ucl, lcl, DEFAULT_RULES, "P", "E", "m", ts)
    r1_over = [v for v in v_over if v.rule_triggered == "Rule 1" and v.point_index == 9]
    assert len(r1_over) == 1, "Point just above 3σ should trigger Rule 1"


def test_process_status_out_of_control(spc_df_anomalies):
    result = run_spc_analysis(spc_df_anomalies, "PROC", subgroup_size=1)
    assert result.process_status == "OUT_OF_CONTROL"


def test_process_status_in_control(spc_df_stable):
    result = run_spc_analysis(spc_df_stable, "PROC", subgroup_size=5)
    assert result.process_status == "IN_CONTROL"
